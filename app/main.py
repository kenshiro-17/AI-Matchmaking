import csv
import io
import os
import re
import time
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.database import Base, SessionLocal, engine, get_db
from app.models import AppUser, Attendee, AuditLog, ExternalSignal, Feedback, IntroRequest, MatchResult
from app.schemas import (
    AttendeeCreate,
    FeedbackCreate,
    IntroRequestCreate,
    IntroRequestUpdate,
    MatchView,
)
from app.services.audit import write_audit_log
from app.services.bootstrap import seed_demo_data_if_empty
from app.services.external_enrichment import extract_company_summary
from app.services.intro import create_intro_request, update_intro_request
from app.services.matching import (
    MAX_MATCHES,
    MIN_MATCHES,
    QUALITY_THRESHOLD,
    build_matches_for_attendee,
    organizer_metrics,
)
from app.services.scenarios import scenarios_for_attendee, strategic_scenarios
from app.services.security import (
    AUTH_SECRET,
    AUTH_COOKIE,
    CSRF_COOKIE,
    InMemoryRateLimiter,
    build_csrf_token,
    build_session_payload,
    decode_payload,
    hash_password,
    sign_payload,
    validate_password_policy,
    verify_csrf_token,
    verify_password,
)

app = FastAPI(title="Proof of Talk Matchmaking Prototype", version="0.5.0")
Base.metadata.create_all(bind=engine)
app.add_middleware(GZipMiddleware, minimum_size=1024)

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

ORGANIZER_EMAIL = os.getenv("ORGANIZER_EMAIL", "organizer@pot.local")
ORGANIZER_PASSWORD = os.getenv("ORGANIZER_PASSWORD", "organizer123")
ATTENDEE_BOOTSTRAP_PASSWORD = os.getenv("ATTENDEE_BOOTSTRAP_PASSWORD", "attendee123")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
FORCE_HTTPS = os.getenv("FORCE_HTTPS", "false").lower() == "true"
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "*").split(",") if h.strip()]
LOCKOUT_SECONDS = int(os.getenv("LOCKOUT_SECONDS", str(15 * 60)))
TRUST_PROXY_HEADERS = os.getenv("TRUST_PROXY_HEADERS", "false").lower() == "true"
APP_ENV = os.getenv("APP_ENV", "development").lower()
SEED_ON_STARTUP = os.getenv(
    "SEED_ON_STARTUP",
    "true" if os.getenv("VERCEL") == "1" else "false",
).lower() == "true"
HOME_PAGE_SIZE = int(os.getenv("HOME_PAGE_SIZE", "80"))
ORGANIZER_PAGE_SIZE = int(os.getenv("ORGANIZER_PAGE_SIZE", "100"))

if ALLOWED_HOSTS != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)
if FORCE_HTTPS:
    app.add_middleware(HTTPSRedirectMiddleware)

RBAC = {
    "organizer": {
        "view_overview",
        "view_organizer",
        "manage_attendees",
        "export_matches",
        "run_enrichment",
        "view_metrics",
        "view_matches_any",
        "submit_feedback_any",
        "request_intro_any",
        "respond_intro_any",
        "view_scenarios_any",
        "view_audit",
    },
    "attendee": {
        "view_own_attendee",
        "view_own_matches",
        "submit_own_feedback",
        "request_own_intro",
        "respond_own_intro",
        "view_own_scenarios",
    },
}

rate_limiter = InMemoryRateLimiter()


def enforce_production_security():
    if APP_ENV not in {"prod", "production"}:
        return
    insecure = []
    if AUTH_SECRET == "pot-dev-secret-change-me":
        insecure.append("AUTH_SECRET must be set")
    if ORGANIZER_PASSWORD == "organizer123":
        insecure.append("ORGANIZER_PASSWORD must be changed from default")
    if not COOKIE_SECURE:
        insecure.append("COOKIE_SECURE must be true")
    if not FORCE_HTTPS:
        insecure.append("FORCE_HTTPS must be true")
    if ALLOWED_HOSTS == ["*"]:
        insecure.append("ALLOWED_HOSTS must be explicit (not *)")
    if insecure:
        raise RuntimeError("Production security configuration error: " + "; ".join(insecure))


enforce_production_security()


if SEED_ON_STARTUP:
    db = SessionLocal()
    try:
        seed_demo_data_if_empty(db, ORGANIZER_EMAIL, ORGANIZER_PASSWORD, ATTENDEE_BOOTSTRAP_PASSWORD)
    finally:
        db.close()


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for", "")
    if TRUST_PROXY_HEADERS and xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _set_auth_cookie(response: RedirectResponse, payload: dict):
    response.set_cookie(
        key=AUTH_COOKIE,
        value=sign_payload(payload),
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        max_age=60 * 60 * 8,
    )


def _set_csrf_cookie(response: RedirectResponse, session_id: str):
    token = build_csrf_token(session_id)
    response.set_cookie(
        key=CSRF_COOKIE,
        value=token,
        httponly=False,
        samesite="strict",
        secure=COOKIE_SECURE,
        max_age=60 * 60 * 8,
    )


def current_user(request: Request) -> dict | None:
    token = request.cookies.get(AUTH_COOKIE)
    if not token:
        return None
    return decode_payload(token)


def has_permission(user: dict | None, permission: str) -> bool:
    if not user:
        return False
    role = user.get("role", "")
    return permission in RBAC.get(role, set())


def require_auth(request: Request):
    if not current_user(request):
        return RedirectResponse(url="/login", status_code=303)
    return None


def require_organizer(request: Request):
    user = current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not has_permission(user, "view_organizer"):
        return RedirectResponse(url="/", status_code=303)
    return None


def can_access_attendee(user: dict, attendee_id: int) -> bool:
    if user.get("role") == "organizer":
        return True
    return user.get("role") == "attendee" and user.get("attendee_id") == attendee_id


def api_user_or_401(request: Request) -> dict:
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def require_csrf_form(request: Request, submitted_token: str):
    user = current_user(request)
    sid = user.get("sid", "guest-session") if user else "guest-session"
    cookie_token = request.cookies.get(CSRF_COOKIE, "")
    if not verify_csrf_token(sid, submitted_token, cookie_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")


def require_csrf_api(request: Request):
    submitted_token = request.headers.get("x-csrf-token", "")
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    cookie_token = request.cookies.get(CSRF_COOKIE, "")
    if not verify_csrf_token(user.get("sid", ""), submitted_token, cookie_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")


def check_rate_limit(request: Request, bucket: str, limit: int, period_seconds: int):
    key = f"{bucket}:{_client_ip(request)}"
    if not rate_limiter.allow(key, limit, period_seconds):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")


def ensure_default_organizer_user(db: Session):
    existing = db.query(AppUser).filter(AppUser.email == ORGANIZER_EMAIL).first()
    if existing:
        return existing
    db.add(
        AppUser(
            email=ORGANIZER_EMAIL,
            role="organizer",
            password_hash=hash_password(ORGANIZER_PASSWORD),
            failed_attempts=0,
            locked_until=0,
        )
    )
    db.commit()
    return db.query(AppUser).filter(AppUser.email == ORGANIZER_EMAIL).first()


def ensure_attendee_user(db: Session, attendee: Attendee, email: str | None = None, raw_password: str | None = None):
    existing = db.query(AppUser).filter(AppUser.attendee_id == attendee.id, AppUser.role == "attendee").first()
    if existing:
        return existing
    user_email = email or f"attendee-{attendee.id}@pot.local"
    password = raw_password or f"{ATTENDEE_BOOTSTRAP_PASSWORD}-{attendee.id}"
    db.add(
        AppUser(
            email=user_email,
            role="attendee",
            attendee_id=attendee.id,
            password_hash=hash_password(password),
            failed_attempts=0,
            locked_until=0,
        )
    )
    db.commit()
    return db.query(AppUser).filter(AppUser.attendee_id == attendee.id, AppUser.role == "attendee").first()


def validate_text(value: str, field: str, max_len: int) -> str:
    cleaned = (value or "").strip()
    if "\x00" in cleaned:
        raise HTTPException(status_code=400, detail=f"{field} contains invalid characters")
    if len(cleaned) > max_len:
        raise HTTPException(status_code=400, detail=f"{field} exceeds max length {max_len}")
    return cleaned


def validate_email_or_blank(value: str, field: str = "email") -> str:
    cleaned = validate_text(value, field, 180).lower()
    if not cleaned:
        return ""
    if not re.fullmatch(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", cleaned):
        raise HTTPException(status_code=400, detail=f"{field} is not a valid email")
    return cleaned


def validate_password_or_blank(value: str, field: str = "password") -> str:
    cleaned = validate_text(value, field, 120)
    if not cleaned:
        return ""
    ok, err = validate_password_policy(cleaned)
    if not ok:
        raise HTTPException(status_code=400, detail=err)
    return cleaned


def parse_page(value: str | None, default: int = 1) -> int:
    try:
        parsed = int(value or default)
    except (TypeError, ValueError):
        return default
    return max(1, parsed)


def parse_page_size(value: str | None, default: int, min_size: int = 10, max_size: int = 200) -> int:
    try:
        parsed = int(value or default)
    except (TypeError, ValueError):
        return default
    return min(max(parsed, min_size), max_size)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
        "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )
    response.headers["Cache-Control"] = "no-store"
    if COOKIE_SECURE:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.get("/login")
def login_page(request: Request):
    if current_user(request):
        return RedirectResponse(url="/", status_code=303)

    csrf = request.cookies.get(CSRF_COOKIE, "")
    if not csrf or not verify_csrf_token("guest-session", csrf, csrf):
        csrf = build_csrf_token("guest-session")
    response = templates.TemplateResponse(request=request, name="login.html", context={"error": "", "csrf_token": csrf})
    response.set_cookie(
        CSRF_COOKIE,
        csrf,
        httponly=False,
        samesite="strict",
        secure=COOKIE_SECURE,
        max_age=60 * 30,
    )
    return response


@app.post("/login")
def login_submit(
    request: Request,
    role: str = Form(...),
    csrf_token: str = Form(""),
    email: str = Form(""),
    password: str = Form(""),
    attendee_id: int = Form(0),
    passcode: str = Form(""),
    db: Session = Depends(get_db),
):
    check_rate_limit(request, "login", limit=20, period_seconds=60)
    if len(email) > 240 or len(password) > 240 or len(passcode) > 240:
        raise HTTPException(status_code=400, detail="Invalid credential payload length")
    email = validate_email_or_blank(email, "email")
    password = validate_text(password, "password", 240)
    passcode = validate_text(passcode, "passcode", 240)
    require_csrf_form(request, csrf_token)
    ensure_default_organizer_user(db)

    if role == "organizer":
        user_row = db.query(AppUser).filter(AppUser.email == email, AppUser.role == "organizer").first()
        now = int(time.time())
        if not user_row:
            write_audit_log(db, None, "login", "auth", "organizer", "denied", {"email": email})
            return templates.TemplateResponse(request=request, name="login.html", context={"error": "Invalid organizer credentials", "csrf_token": csrf_token})
        if user_row.locked_until and user_row.locked_until > now:
            write_audit_log(db, None, "login", "auth", user_row.email, "denied", {"reason": "locked"})
            return templates.TemplateResponse(request=request, name="login.html", context={"error": "Account temporarily locked", "csrf_token": csrf_token})

        if verify_password(password, user_row.password_hash):
            user_row.failed_attempts = 0
            user_row.locked_until = 0
            db.commit()
            user = {"role": "organizer", "label": "Organizer"}
            session_payload = build_session_payload(user)
            write_audit_log(db, session_payload, "login", "auth", user_row.email, "success", {})
            response = RedirectResponse(url="/organizer", status_code=303)
            _set_auth_cookie(response, session_payload)
            _set_csrf_cookie(response, session_payload["sid"])
            return response

        user_row.failed_attempts += 1
        if user_row.failed_attempts >= 5:
            user_row.locked_until = now + LOCKOUT_SECONDS
            user_row.failed_attempts = 0
        db.commit()
        write_audit_log(db, None, "login", "auth", user_row.email, "denied", {"reason": "bad_password"})
        return templates.TemplateResponse(request=request, name="login.html", context={"error": "Invalid organizer credentials", "csrf_token": csrf_token})

    if role == "attendee":
        attendee = db.query(Attendee).filter(Attendee.id == attendee_id).first()
        attendee_user = (
            db.query(AppUser).filter(AppUser.attendee_id == attendee_id, AppUser.role == "attendee").first()
            if attendee
            else None
        )
        now = int(time.time())
        if attendee and attendee_user and attendee_user.locked_until and attendee_user.locked_until > now:
            write_audit_log(db, None, "login", "auth", str(attendee_id), "denied", {"reason": "locked"})
            return templates.TemplateResponse(
                request=request,
                name="login.html",
                context={"error": "Account temporarily locked", "csrf_token": csrf_token},
            )

        if attendee and attendee_user and verify_password(passcode, attendee_user.password_hash):
            attendee_user.failed_attempts = 0
            attendee_user.locked_until = 0
            db.commit()
            user = {
                "role": "attendee",
                "attendee_id": attendee.id,
                "label": attendee.name,
            }
            session_payload = build_session_payload(user)
            write_audit_log(db, session_payload, "login", "auth", str(attendee.id), "success", {})
            response = RedirectResponse(url=f"/attendees/{attendee.id}", status_code=303)
            _set_auth_cookie(response, session_payload)
            _set_csrf_cookie(response, session_payload["sid"])
            return response
        if attendee_user:
            attendee_user.failed_attempts += 1
            if attendee_user.failed_attempts >= 5:
                attendee_user.locked_until = now + LOCKOUT_SECONDS
                attendee_user.failed_attempts = 0
            db.commit()
        write_audit_log(db, None, "login", "auth", str(attendee_id), "denied", {})
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "Invalid attendee credentials (id/passcode). Contact organizer if account is not provisioned.",
                "csrf_token": csrf_token,
            },
        )

    return templates.TemplateResponse(request=request, name="login.html", context={"error": "Invalid role", "csrf_token": csrf_token})


@app.get("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    user = current_user(request)
    write_audit_log(db, user, "logout", "auth", "", "success", {})
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(AUTH_COOKIE)
    response.delete_cookie(CSRF_COOKIE)
    return response


@app.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    auth = require_auth(request)
    if auth:
        return auth

    user = current_user(request)
    if user and user.get("role") == "attendee":
        return RedirectResponse(url=f"/attendees/{user['attendee_id']}", status_code=303)

    page = parse_page(request.query_params.get("page"), default=1)
    page_size = parse_page_size(request.query_params.get("page_size"), default=HOME_PAGE_SIZE)
    total_attendees = db.query(Attendee).count()
    total_pages = max(1, (total_attendees + page_size - 1) // page_size)
    page = min(page, total_pages)
    offset = (page - 1) * page_size
    attendees = (
        db.query(Attendee)
        .order_by(Attendee.name.asc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    metrics = organizer_metrics(db)
    scenarios = strategic_scenarios(db.query(Attendee).all(), max_results=24)[:8]
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "attendees": attendees,
            "metrics": metrics,
            "scenarios": scenarios,
            "user": user,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "total_attendees": total_attendees,
        },
    )


@app.get("/organizer")
def organizer_view(request: Request, db: Session = Depends(get_db)):
    auth = require_organizer(request)
    if auth:
        return auth

    page = parse_page(request.query_params.get("page"), default=1)
    page_size = parse_page_size(request.query_params.get("page_size"), default=ORGANIZER_PAGE_SIZE)
    total_attendees = db.query(Attendee).count()
    total_pages = max(1, (total_attendees + page_size - 1) // page_size)
    page = min(page, total_pages)
    offset = (page - 1) * page_size
    attendees = (
        db.query(Attendee)
        .order_by(Attendee.name.asc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    metrics = organizer_metrics(db)
    message = request.query_params.get("message", "")
    return templates.TemplateResponse(
        request=request,
        name="organizer.html",
        context={
            "attendees": attendees,
            "metrics": metrics,
            "message": message,
            "user": current_user(request),
            "csrf_token": request.cookies.get(CSRF_COOKIE, ""),
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "total_attendees": total_attendees,
        },
    )


@app.get("/organizer/audit")
def organizer_audit(request: Request, db: Session = Depends(get_db)):
    auth = require_organizer(request)
    if auth:
        return auth
    user = current_user(request)
    if not has_permission(user, "view_audit"):
        return RedirectResponse(url="/", status_code=303)

    logs = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(200).all()
    return templates.TemplateResponse(
        request=request,
        name="organizer_audit.html",
        context={"logs": logs, "user": user},
    )


@app.get("/attendees/{attendee_id}")
def attendee_view(attendee_id: int, request: Request, db: Session = Depends(get_db)):
    auth = require_auth(request)
    if auth:
        return auth

    user = current_user(request)
    if not can_access_attendee(user, attendee_id):
        return RedirectResponse(url="/", status_code=303)

    attendee = db.query(Attendee).filter(Attendee.id == attendee_id).first()
    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")

    matches = build_matches_for_attendee(db, attendee_id, top_n=5)
    all_attendees = db.query(Attendee).all()
    attendee_scenarios = scenarios_for_attendee(attendee, all_attendees)
    incoming_requests = (
        db.query(IntroRequest).filter(IntroRequest.candidate_id == attendee.id).order_by(IntroRequest.id.desc()).all()
    )
    cards = []
    candidate_ids = [m.candidate_id for m in matches]
    candidate_map = {
        row.id: row
        for row in db.query(Attendee).filter(Attendee.id.in_(candidate_ids)).all()
    } if candidate_ids else {}
    for m in matches:
        candidate = candidate_map.get(m.candidate_id)
        if not candidate:
            continue
        cards.append(
            MatchView(
                match_id=m.id,
                candidate_id=candidate.id,
                candidate_name=candidate.name,
                candidate_role=candidate.role,
                candidate_company=candidate.company,
                score=m.score,
                exploration_flag=m.exploration_flag,
                reasons=[m.reason_1, m.reason_2, m.reason_3],
            )
        )

    return templates.TemplateResponse(
        request=request,
        name="attendee.html",
        context={
            "attendee": attendee,
            "cards": cards,
            "quality_threshold": QUALITY_THRESHOLD,
            "min_matches": MIN_MATCHES,
            "max_matches": MAX_MATCHES,
            "scenarios": attendee_scenarios,
            "incoming_requests": incoming_requests,
            "user": user,
            "csrf_token": request.cookies.get(CSRF_COOKIE, ""),
        },
    )


@app.post("/feedback")
def submit_feedback(
    request: Request,
    csrf_token: str = Form(""),
    attendee_id: int = Form(...),
    match_id: int = Form(...),
    rating: int = Form(...),
    outcome: str = Form("reviewed"),
    comment: str = Form(""),
    db: Session = Depends(get_db),
):
    auth = require_auth(request)
    if auth:
        return auth
    check_rate_limit(request, "feedback_form", limit=30, period_seconds=60)
    require_csrf_form(request, csrf_token)

    user = current_user(request)
    if not can_access_attendee(user, attendee_id):
        return RedirectResponse(url="/", status_code=303)

    payload = FeedbackCreate(
        attendee_id=attendee_id, match_id=match_id, rating=rating, outcome=outcome, comment=comment
    )
    match = db.query(MatchResult).filter(MatchResult.id == payload.match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    if match.attendee_id != payload.attendee_id:
        raise HTTPException(status_code=403, detail="Feedback target mismatch")
    row = Feedback(
        attendee_id=payload.attendee_id,
        match_id=payload.match_id,
        candidate_id=match.candidate_id,
        rating=payload.rating,
        outcome=payload.outcome,
        comment=payload.comment,
    )
    db.add(row)
    db.commit()
    write_audit_log(db, user, "submit_feedback", "match", str(match.id), "success", {"rating": rating})
    return RedirectResponse(url=f"/attendees/{attendee_id}", status_code=303)


@app.post("/organizer/attendees")
def create_attendee_form(
    request: Request,
    csrf_token: str = Form(""),
    name: str = Form(...),
    role: str = Form(...),
    company: str = Form(...),
    primary_goal: str = Form(...),
    availability: str = Form(""),
    language: str = Form("English"),
    secondary_goals: str = Form(""),
    seek_text: str = Form(""),
    offer_text: str = Form(""),
    focus_text: str = Form(""),
    login_email: str = Form(""),
    temp_password: str = Form(""),
    db: Session = Depends(get_db),
):
    auth = require_organizer(request)
    if auth:
        return auth
    check_rate_limit(request, "attendee_create_form", limit=20, period_seconds=60)
    require_csrf_form(request, csrf_token)

    user = current_user(request)
    safe_email = validate_email_or_blank(login_email, "login_email")
    safe_password = validate_password_or_blank(temp_password, "temp_password")
    if (safe_email and not safe_password) or (safe_password and not safe_email):
        raise HTTPException(status_code=400, detail="login_email and temp_password must be set together")
    if APP_ENV in {"prod", "production"} and not safe_password:
        raise HTTPException(status_code=400, detail="temp_password is required in production")

    row = Attendee(
        name=validate_text(name, "name", 120),
        role=validate_text(role, "role", 120),
        company=validate_text(company, "company", 120),
        primary_goal=validate_text(primary_goal, "primary_goal", 120),
        availability=validate_text(availability, "availability", 240),
        language=validate_text(language or "English", "language", 32) or "English",
        secondary_goals=validate_text(secondary_goals, "secondary_goals", 240),
        seek_text=validate_text(seek_text, "seek_text", 800),
        offer_text=validate_text(offer_text, "offer_text", 800),
        focus_text=validate_text(focus_text, "focus_text", 800),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    attendee_user = ensure_attendee_user(
        db,
        row,
        email=safe_email or None,
        raw_password=safe_password or None,
    )
    write_audit_log(db, user, "create_attendee", "attendee", str(row.id), "success", {})
    return RedirectResponse(
        url=f"/organizer?message=Attendee+created+(id={row.id},+login={attendee_user.email})",
        status_code=303,
    )


@app.post("/organizer/enrich")
def enrich_attendee_form(
    request: Request,
    csrf_token: str = Form(""),
    attendee_id: int = Form(...),
    source_url: str = Form(...),
    db: Session = Depends(get_db),
):
    auth = require_organizer(request)
    if auth:
        return auth
    require_csrf_form(request, csrf_token)
    check_rate_limit(request, "enrich", limit=10, period_seconds=60)

    user = current_user(request)
    attendee = db.query(Attendee).filter(Attendee.id == attendee_id).first()
    if not attendee:
        write_audit_log(db, user, "run_enrichment", "attendee", str(attendee_id), "denied", {"reason": "not_found"})
        return RedirectResponse(url="/organizer?message=Attendee+not+found", status_code=303)

    try:
        safe_source_url = validate_text(source_url, "source_url", 280)
        summary = extract_company_summary(safe_source_url)
    except Exception as exc:
        write_audit_log(db, user, "run_enrichment", "attendee", str(attendee_id), "failed", {"error": str(exc)[:120]})
        msg = f"Enrichment failed: {str(exc)[:120]}"
        return RedirectResponse(url=f"/organizer?message={msg}", status_code=303)

    db.add(
        ExternalSignal(
            attendee_id=attendee.id,
            source="company_website",
            source_url=safe_source_url,
            extracted_summary=summary,
        )
    )
    attendee.focus_text = f"{attendee.focus_text} {summary[:500]}".strip()
    db.commit()
    write_audit_log(
        db, user, "run_enrichment", "attendee", str(attendee.id), "success", {"source_url": safe_source_url}
    )
    return RedirectResponse(url="/organizer?message=Enrichment+completed", status_code=303)


@app.post("/intros/request")
def intro_request_form(
    request: Request,
    csrf_token: str = Form(""),
    requester_id: int = Form(...),
    candidate_id: int = Form(...),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    auth = require_auth(request)
    if auth:
        return auth
    check_rate_limit(request, "intro_form", limit=30, period_seconds=60)
    require_csrf_form(request, csrf_token)
    user = current_user(request)
    if not can_access_attendee(user, requester_id):
        return RedirectResponse(url="/", status_code=303)
    if requester_id == candidate_id:
        raise HTTPException(status_code=400, detail="Requester and candidate must be different")
    requester = db.query(Attendee).filter(Attendee.id == requester_id).first()
    candidate = db.query(Attendee).filter(Attendee.id == candidate_id).first()
    if not requester or not candidate:
        raise HTTPException(status_code=404, detail="Attendee not found")

    row = create_intro_request(db, requester_id, candidate_id, validate_text(note, "note", 280))
    write_audit_log(db, user, "request_intro", "intro_request", str(row.id), "success", {})
    return RedirectResponse(url=f"/attendees/{requester_id}", status_code=303)


@app.post("/intros/respond")
def intro_respond_form(
    request: Request,
    csrf_token: str = Form(""),
    intro_id: int = Form(...),
    actor_id: int = Form(...),
    action: str = Form(...),
    db: Session = Depends(get_db),
):
    auth = require_auth(request)
    if auth:
        return auth
    check_rate_limit(request, "intro_response_form", limit=40, period_seconds=60)
    require_csrf_form(request, csrf_token)

    user = current_user(request)
    if not can_access_attendee(user, actor_id):
        return RedirectResponse(url="/", status_code=303)

    action = validate_text(action, "action", 24).lower()
    row = update_intro_request(db, intro_id, actor_id, action)
    if not row:
        write_audit_log(db, user, "respond_intro", "intro_request", str(intro_id), "denied", {"action": action})
        raise HTTPException(status_code=400, detail="Invalid intro response")
    write_audit_log(db, user, "respond_intro", "intro_request", str(intro_id), "success", {"action": action})
    return RedirectResponse(url=f"/attendees/{actor_id}", status_code=303)


# API routes with RBAC and CSRF checks.
@app.post("/v1/attendees")
def create_attendee(payload: AttendeeCreate, request: Request, db: Session = Depends(get_db)):
    user = api_user_or_401(request)
    check_rate_limit(request, "attendee_create_api", limit=20, period_seconds=60)
    require_csrf_api(request)
    if not has_permission(user, "manage_attendees"):
        write_audit_log(db, user, "api_create_attendee", "attendee", "", "denied", {})
        raise HTTPException(status_code=403, detail="Forbidden")

    row = Attendee(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    ensure_attendee_user(db, row)
    write_audit_log(db, user, "api_create_attendee", "attendee", str(row.id), "success", {})
    return {"id": row.id, "login_email": f"attendee-{row.id}@pot.local"}


@app.get("/v1/matches/{attendee_id}")
def api_matches(attendee_id: int, request: Request, db: Session = Depends(get_db)):
    user = api_user_or_401(request)
    attendee = db.query(Attendee).filter(Attendee.id == attendee_id).first()
    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")
    if user.get("role") == "attendee" and user.get("attendee_id") != attendee_id:
        write_audit_log(db, user, "api_view_matches", "attendee", str(attendee_id), "denied", {})
        raise HTTPException(status_code=403, detail="Forbidden")

    matches = build_matches_for_attendee(db, attendee_id, top_n=5)
    candidate_ids = [m.candidate_id for m in matches]
    candidate_map = {
        row.id: row
        for row in db.query(Attendee).filter(Attendee.id.in_(candidate_ids)).all()
    } if candidate_ids else {}
    output = []
    for m in matches:
        candidate = candidate_map.get(m.candidate_id)
        if not candidate:
            continue
        output.append(
            {
                "match_id": m.id,
                "candidate_id": candidate.id,
                "candidate_name": candidate.name,
                "candidate_role": candidate.role,
                "candidate_company": candidate.company,
                "score": m.score,
                "exploration_flag": m.exploration_flag,
                "reasons": [m.reason_1, m.reason_2, m.reason_3],
            }
        )
    return {"attendee_id": attendee_id, "matches": output}


@app.post("/v1/feedback")
def api_feedback(payload: FeedbackCreate, request: Request, db: Session = Depends(get_db)):
    user = api_user_or_401(request)
    check_rate_limit(request, "feedback_api", limit=40, period_seconds=60)
    require_csrf_api(request)
    if user.get("role") == "attendee" and user.get("attendee_id") != payload.attendee_id:
        write_audit_log(db, user, "api_submit_feedback", "match", str(payload.match_id), "denied", {})
        raise HTTPException(status_code=403, detail="Forbidden")

    match = db.query(MatchResult).filter(MatchResult.id == payload.match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    if match.attendee_id != payload.attendee_id:
        raise HTTPException(status_code=403, detail="Feedback target mismatch")
    db.add(Feedback(**payload.model_dump(), candidate_id=match.candidate_id))
    db.commit()
    write_audit_log(db, user, "api_submit_feedback", "match", str(payload.match_id), "success", {})
    return {"ok": True}


@app.post("/v1/intros")
def api_intro_request(payload: IntroRequestCreate, request: Request, db: Session = Depends(get_db)):
    user = api_user_or_401(request)
    check_rate_limit(request, "intro_api", limit=40, period_seconds=60)
    require_csrf_api(request)
    if user.get("role") == "attendee" and user.get("attendee_id") != payload.requester_id:
        write_audit_log(db, user, "api_request_intro", "attendee", str(payload.requester_id), "denied", {})
        raise HTTPException(status_code=403, detail="Forbidden")

    requester = db.query(Attendee).filter(Attendee.id == payload.requester_id).first()
    candidate = db.query(Attendee).filter(Attendee.id == payload.candidate_id).first()
    if not requester or not candidate:
        raise HTTPException(status_code=404, detail="Attendee not found")
    if payload.requester_id == payload.candidate_id:
        raise HTTPException(status_code=400, detail="Requester and candidate must be different")
    row = create_intro_request(db, payload.requester_id, payload.candidate_id, validate_text(payload.note, "note", 280))
    write_audit_log(db, user, "api_request_intro", "intro_request", str(row.id), "success", {})
    return {"id": row.id, "status": row.status}


@app.post("/v1/intros/{intro_id}")
def api_intro_update(intro_id: int, payload: IntroRequestUpdate, request: Request, db: Session = Depends(get_db)):
    user = api_user_or_401(request)
    check_rate_limit(request, "intro_update_api", limit=40, period_seconds=60)
    require_csrf_api(request)
    if user.get("role") == "attendee" and user.get("attendee_id") != payload.actor_id:
        write_audit_log(db, user, "api_respond_intro", "intro_request", str(intro_id), "denied", {})
        raise HTTPException(status_code=403, detail="Forbidden")

    row = update_intro_request(db, intro_id, payload.actor_id, validate_text(payload.action, "action", 24).lower())
    if not row:
        write_audit_log(db, user, "api_respond_intro", "intro_request", str(intro_id), "denied", {})
        raise HTTPException(status_code=400, detail="Invalid intro action")
    write_audit_log(db, user, "api_respond_intro", "intro_request", str(intro_id), "success", {})
    return {"id": row.id, "status": row.status}


@app.post("/v1/enrich/company")
def api_company_enrichment(attendee_id: int, source_url: str, request: Request, db: Session = Depends(get_db)):
    user = api_user_or_401(request)
    require_csrf_api(request)
    check_rate_limit(request, "api_enrich", limit=10, period_seconds=60)
    if not has_permission(user, "run_enrichment"):
        write_audit_log(db, user, "api_enrich", "attendee", str(attendee_id), "denied", {})
        raise HTTPException(status_code=403, detail="Forbidden")

    attendee = db.query(Attendee).filter(Attendee.id == attendee_id).first()
    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")

    try:
        safe_source_url = validate_text(source_url, "source_url", 280)
        summary = extract_company_summary(safe_source_url)
    except Exception as exc:
        write_audit_log(db, user, "api_enrich", "attendee", str(attendee_id), "failed", {"error": str(exc)[:120]})
        raise HTTPException(status_code=400, detail=f"Enrichment failed: {exc}") from exc

    db.add(
        ExternalSignal(
            attendee_id=attendee.id,
            source="company_website",
            source_url=safe_source_url,
            extracted_summary=summary,
        )
    )
    attendee.focus_text = f"{attendee.focus_text} {summary[:500]}".strip()
    db.commit()
    write_audit_log(
        db, user, "api_enrich", "attendee", str(attendee.id), "success", {"source_url": safe_source_url}
    )
    return {"attendee_id": attendee.id, "source_url": safe_source_url, "summary": summary[:500]}


@app.get("/v1/organizer/metrics")
def api_metrics(request: Request, db: Session = Depends(get_db)):
    user = api_user_or_401(request)
    if not has_permission(user, "view_metrics"):
        write_audit_log(db, user, "api_view_metrics", "metrics", "", "denied", {})
        raise HTTPException(status_code=403, detail="Forbidden")
    return organizer_metrics(db)


@app.get("/v1/scenarios")
def api_scenarios(request: Request, attendee_id: int | None = None, db: Session = Depends(get_db)):
    user = api_user_or_401(request)
    attendees = db.query(Attendee).all()
    if user.get("role") == "organizer":
        if attendee_id is None:
            return {"scenarios": strategic_scenarios(attendees)}
        attendee = db.query(Attendee).filter(Attendee.id == attendee_id).first()
        if not attendee:
            raise HTTPException(status_code=404, detail="Attendee not found")
        return {"scenarios": scenarios_for_attendee(attendee, attendees)}

    own_id = user.get("attendee_id")
    if attendee_id is not None and attendee_id != own_id:
        write_audit_log(db, user, "api_view_scenarios", "attendee", str(attendee_id), "denied", {})
        raise HTTPException(status_code=403, detail="Forbidden")
    attendee = db.query(Attendee).filter(Attendee.id == own_id).first()
    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")
    return {"scenarios": scenarios_for_attendee(attendee, attendees)}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/organizer/export/matches.csv")
def export_matches_csv(request: Request, db: Session = Depends(get_db)):
    auth = require_organizer(request)
    if auth:
        return auth

    user = current_user(request)
    attendees = db.query(Attendee).order_by(Attendee.id.asc()).all()
    attendee_map = {row.id: row for row in attendees}
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["attendee_id", "attendee_name", "candidate_id", "candidate_name", "score", "reasons"])

    for attendee in attendees:
        matches = build_matches_for_attendee(db, attendee.id, top_n=5)
        for m in matches:
            candidate = attendee_map.get(m.candidate_id)
            if not candidate:
                continue
            reasons = " | ".join([x for x in [m.reason_1, m.reason_2, m.reason_3] if x])
            writer.writerow([attendee.id, attendee.name, candidate.id, candidate.name, m.score, reasons])

    buffer.seek(0)
    write_audit_log(db, user, "export_matches_csv", "matches", "all", "success", {})
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=matches_export.csv"},
    )
