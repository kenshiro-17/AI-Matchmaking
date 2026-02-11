from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models import Attendee, Feedback, MatchResult
from app.services.explain import make_reasons
from app.services.profile import build_profile


def _overlap_csv(a: str, b: str) -> bool:
    if not a or not b:
        return True
    a_set = {x.strip().lower() for x in a.split(",") if x.strip()}
    b_set = {x.strip().lower() for x in b.split(",") if x.strip()}
    return bool(a_set.intersection(b_set))


def _passes_hard_constraints(a: Attendee, b: Attendee) -> bool:
    if a.id == b.id:
        return False
    if a.language.lower() != b.language.lower():
        return False
    if not _overlap_csv(a.availability, b.availability):
        return False
    exclusions = {x.strip().lower() for x in a.exclusions.split(",") if x.strip()}
    if b.company.lower() in exclusions or b.name.lower() in exclusions:
        return False
    return True


def _goal_alignment(a: Attendee, b: Attendee, b_profile) -> float:
    goal = a.primary_goal.lower()
    pool = b_profile.focus_tags | b_profile.offer_tags
    return 35.0 if goal in pool else 12.0


def _complementarity(a: Attendee, b: Attendee) -> float:
    a_role = a.role.lower()
    b_role = b.role.lower()
    pairs = [
        ("invest", "founder"),
        ("founder", "invest"),
        ("bank", "cto"),
        ("cto", "bank"),
        ("policy", "founder"),
        ("founder", "policy"),
    ]
    for left, right in pairs:
        if left in a_role and right in b_role:
            return 25.0
    if a_role == b_role:
        return 8.0
    return 14.0


def _domain_relevance(a_profile, b_profile) -> float:
    shared = len((a_profile.focus_tags | a_profile.seek_tags).intersection(b_profile.focus_tags))
    return min(20.0, float(shared * 2))


def _decision_level(a: Attendee, b: Attendee) -> float:
    senior_markers = ("chief", "ceo", "cto", "partner", "head", "director", "managing")
    a_senior = any(token in a.role.lower() for token in senior_markers)
    b_senior = any(token in b.role.lower() for token in senior_markers)
    return 10.0 if a_senior and b_senior else 5.0


def _feedback_prior_map(db: Session, requester_id: int) -> dict[int, float]:
    rows = (
        db.query(Feedback.candidate_id, func.avg(Feedback.rating))
        .filter(Feedback.attendee_id == requester_id)
        .group_by(Feedback.candidate_id)
        .all()
    )
    return {candidate_id: float((avg_rating / 5.0) * 10.0) for candidate_id, avg_rating in rows}


MIN_MATCHES = 3
MAX_MATCHES = 7
QUALITY_THRESHOLD = 65.0


def build_matches_for_attendee(db: Session, attendee_id: int, top_n: int = 5) -> list[MatchResult]:
    requester = db.query(Attendee).filter(Attendee.id == attendee_id).first()
    if not requester:
        return []

    candidates = db.query(Attendee).all()
    profile_map = {candidate.id: build_profile(candidate) for candidate in candidates}
    requester_profile = profile_map[requester.id]
    feedback_map = _feedback_prior_map(db, requester.id)

    scored = []
    for candidate in candidates:
        if not _passes_hard_constraints(requester, candidate):
            continue
        cp = profile_map[candidate.id]
        parts = {
            "goal": _goal_alignment(requester, candidate, cp),
            "complementarity": _complementarity(requester, candidate),
            "domain": _domain_relevance(requester_profile, cp),
            "decision": _decision_level(requester, candidate),
            "feedback": feedback_map.get(candidate.id, 5.0),
        }
        score = sum(parts.values())
        reasons = make_reasons(requester, candidate, parts)
        scored.append((candidate, score, parts, reasons))

    scored.sort(key=lambda x: x[1], reverse=True)
    primary = scored[: top_n + 2]
    top_n = max(MIN_MATCHES, min(MAX_MATCHES, top_n))
    qualified = [row for row in scored if row[1] > QUALITY_THRESHOLD]
    primary = qualified[: top_n + 2]
    final = primary[:top_n]

    # Diversity injection: replace last slot with first eligible outside top range.
    if len(final) >= MIN_MATCHES and len(primary) > top_n:
        exploration_candidate = primary[top_n]
        if exploration_candidate[1] > QUALITY_THRESHOLD:
            final[-1] = exploration_candidate

    db.query(MatchResult).filter(MatchResult.attendee_id == attendee_id).delete(synchronize_session=False)

    stored: list[MatchResult] = []
    exploration_slot_candidate_id = primary[top_n][0].id if len(primary) > top_n else None
    for candidate, score, _parts, reasons in final:
        exploration = candidate.id == exploration_slot_candidate_id
        rec = MatchResult(
            attendee_id=attendee_id,
            candidate_id=candidate.id,
            score=round(score, 2),
            exploration_flag=exploration,
            reason_1=reasons[0] if len(reasons) > 0 else "",
            reason_2=reasons[1] if len(reasons) > 1 else "",
            reason_3=reasons[2] if len(reasons) > 2 else "",
        )
        db.add(rec)
        stored.append(rec)

    db.commit()
    for rec in stored:
        db.refresh(rec)
    return stored


def organizer_metrics(db: Session) -> dict[str, float]:
    total = db.query(func.count(Feedback.id)).scalar() or 0
    if total == 0:
        return {
            "feedback_count": 0,
            "avg_rating": 0.0,
            "positive_rate": 0.0,
            "meeting_rate": 0.0,
        }
    avg_rating = db.query(func.avg(Feedback.rating)).scalar() or 0.0
    positive_count = (
        db.query(func.sum(case((Feedback.rating >= 4, 1), else_=0))).scalar() or 0
    )
    met_count = (
        db.query(
            func.sum(
                case(
                    (
                        func.lower(Feedback.outcome).in_(["met", "follow_up"]),
                        1,
                    ),
                    else_=0,
                )
            )
        ).scalar()
        or 0
    )
    positive = positive_count / total
    met = met_count / total
    return {
        "feedback_count": total,
        "avg_rating": round(avg_rating, 2),
        "positive_rate": round(positive, 2),
        "meeting_rate": round(met, 2),
    }


def ranking_snapshot(db: Session, attendee_id: int) -> dict[int, float]:
    rows = db.query(MatchResult).filter(MatchResult.attendee_id == attendee_id).all()
    return {r.candidate_id: r.score for r in rows}
