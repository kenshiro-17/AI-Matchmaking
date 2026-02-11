from sqlalchemy.orm import Session

from app.models import IntroRequest


def create_intro_request(db: Session, requester_id: int, candidate_id: int, note: str = "") -> IntroRequest:
    if requester_id == candidate_id:
        raise ValueError("Requester and candidate must be different")
    existing = (
        db.query(IntroRequest)
        .filter(
            IntroRequest.requester_id == requester_id,
            IntroRequest.candidate_id == candidate_id,
            IntroRequest.status.in_(["pending_candidate", "introduced"]),
        )
        .first()
    )
    if existing:
        return existing

    row = IntroRequest(
        requester_id=requester_id, candidate_id=candidate_id, status="pending_candidate", note=note
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_intro_request(db: Session, intro_id: int, actor_id: int, action: str) -> IntroRequest | None:
    row = db.query(IntroRequest).filter(IntroRequest.id == intro_id).first()
    if not row:
        return None
    if actor_id != row.candidate_id:
        return None
    if row.status != "pending_candidate":
        return None

    if action == "accept":
        row.status = "introduced"
    elif action == "decline":
        row.status = "declined"
    else:
        return None
    db.commit()
    db.refresh(row)
    return row
