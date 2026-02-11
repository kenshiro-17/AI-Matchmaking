import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import AppUser, Attendee
from app.services.security import hash_password


def _seed_file_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "seed" / "attendees.json"


def _ensure_organizer_user(db: Session, organizer_email: str, organizer_password: str):
    existing = db.query(AppUser).filter(AppUser.email == organizer_email, AppUser.role == "organizer").first()
    if existing:
        return
    db.add(
        AppUser(
            email=organizer_email,
            role="organizer",
            password_hash=hash_password(organizer_password),
            failed_attempts=0,
            locked_until=0,
        )
    )
    db.commit()


def _ensure_attendee_users(db: Session, attendee_bootstrap_password: str):
    attendees = db.query(Attendee).order_by(Attendee.id.asc()).all()
    for attendee in attendees:
        existing = (
            db.query(AppUser).filter(AppUser.attendee_id == attendee.id, AppUser.role == "attendee").first()
        )
        if existing:
            continue
        db.add(
            AppUser(
                email=f"attendee-{attendee.id}@pot.local",
                role="attendee",
                attendee_id=attendee.id,
                password_hash=hash_password(f"{attendee_bootstrap_password}-{attendee.id}"),
                failed_attempts=0,
                locked_until=0,
            )
        )
    db.commit()


def seed_demo_data_if_empty(
    db: Session, organizer_email: str, organizer_password: str, attendee_bootstrap_password: str
) -> bool:
    attendee_count = db.query(Attendee).count()
    if attendee_count > 0:
        _ensure_organizer_user(db, organizer_email, organizer_password)
        _ensure_attendee_users(db, attendee_bootstrap_password)
        return False

    seed_path = _seed_file_path()
    rows = json.loads(seed_path.read_text())
    for row in rows:
        db.add(Attendee(**row))
    db.commit()

    _ensure_organizer_user(db, organizer_email, organizer_password)
    _ensure_attendee_users(db, attendee_bootstrap_password)
    return True
