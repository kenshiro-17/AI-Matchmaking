import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
from collections import defaultdict, deque


AUTH_SECRET = os.getenv("AUTH_SECRET", "pot-dev-secret-change-me")
PASSWORD_ITERATIONS = int(os.getenv("PASSWORD_ITERATIONS", "600000"))
TOKEN_TTL_SECONDS = int(os.getenv("TOKEN_TTL_SECONDS", str(60 * 60 * 8)))
CSRF_COOKIE = "csrf_token"
AUTH_COOKIE = "auth_token"
MAX_TOKEN_BYTES = 4096
MIN_PASSWORD_LENGTH = int(os.getenv("MIN_PASSWORD_LENGTH", "12"))


def hash_password(password: str, salt: bytes | None = None) -> str:
    if salt is None:
        salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        PASSWORD_ITERATIONS, base64.b64encode(salt).decode(), base64.b64encode(digest).decode()
    )


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        algo, iterations, salt_b64, digest_b64 = encoded_hash.split("$")
        if algo != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_b64.encode())
        expected = base64.b64decode(digest_b64.encode())
        trial = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(trial, expected)
    except Exception:
        return False


def validate_password_policy(password: str) -> tuple[bool, str]:
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
    if len(password) > 120:
        return False, "Password is too long"
    checks = [
        (r"[A-Z]", "one uppercase letter"),
        (r"[a-z]", "one lowercase letter"),
        (r"[0-9]", "one number"),
        (r"[^A-Za-z0-9]", "one special character"),
    ]
    for pattern, label in checks:
        if not re.search(pattern, password):
            return False, f"Password must include at least {label}"
    return True, ""


def sign_payload(payload: dict) -> str:
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode()
    sig = hmac.new(AUTH_SECRET.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"


def decode_payload(token: str) -> dict | None:
    try:
        if len(token.encode("utf-8")) > MAX_TOKEN_BYTES:
            return None
        payload_b64, sig = token.split(".")
        expected = hmac.new(AUTH_SECRET.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload_json = base64.urlsafe_b64decode(payload_b64.encode()).decode()
        payload = json.loads(payload_json)
        if not isinstance(payload, dict):
            return None
        role = payload.get("role")
        if role not in {"organizer", "attendee"}:
            return None
        sid = payload.get("sid")
        if not isinstance(sid, str) or len(sid) < 12:
            return None
        now = int(time.time())
        if payload.get("exp", 0) < now:
            return None
        return payload
    except Exception:
        return None


def build_session_payload(user: dict) -> dict:
    now = int(time.time())
    session_id = secrets.token_urlsafe(16)
    payload = {
        "sid": session_id,
        "role": user["role"],
        "label": user.get("label", ""),
        "attendee_id": user.get("attendee_id"),
        "iat": now,
        "exp": now + TOKEN_TTL_SECONDS,
    }
    return payload


def build_csrf_token(session_id: str) -> str:
    nonce = secrets.token_urlsafe(16)
    mac = hmac.new(AUTH_SECRET.encode(), f"{session_id}:{nonce}".encode(), hashlib.sha256).hexdigest()
    return f"{nonce}.{mac}"


def verify_csrf_token(session_id: str, submitted: str, cookie_value: str) -> bool:
    if not isinstance(session_id, str) or not session_id:
        return False
    if not submitted or not cookie_value:
        return False
    if not hmac.compare_digest(submitted, cookie_value):
        return False
    try:
        nonce, sig = submitted.split(".")
    except ValueError:
        return False
    expected = hmac.new(AUTH_SECRET.encode(), f"{session_id}:{nonce}".encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected)


class InMemoryRateLimiter:
    def __init__(self):
        self._events = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, period_seconds: int) -> bool:
        with self._lock:
            now = time.time()
            dq = self._events[key]
            while dq and dq[0] <= now - period_seconds:
                dq.popleft()
            if len(dq) >= limit:
                return False
            dq.append(now)
            return True
