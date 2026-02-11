import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import SessionLocal
from app.models import AppUser, Attendee, Base
from app.database import engine
from app.services.security import hash_password

ORGANIZER_EMAIL = os.getenv("ORGANIZER_EMAIL", "organizer@pot.local")
ORGANIZER_PASSWORD = os.getenv("ORGANIZER_PASSWORD", "organizer123")
ATTENDEE_BOOTSTRAP_PASSWORD = os.getenv("ATTENDEE_BOOTSTRAP_PASSWORD", "attendee123")


def seed():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.query(AppUser).delete()
        db.query(Attendee).delete()
        db.commit()

        source = Path("data/seed/attendees.json")
        rows = json.loads(source.read_text())
        for row in rows:
            db.add(Attendee(**row))
        db.commit()

        attendees = db.query(Attendee).order_by(Attendee.id.asc()).all()
        db.add(
            AppUser(
                email=ORGANIZER_EMAIL,
                role="organizer",
                password_hash=hash_password(ORGANIZER_PASSWORD),
                failed_attempts=0,
                locked_until=0,
            )
        )
        for attendee in attendees:
            db.add(
                AppUser(
                    email=f"attendee-{attendee.id}@pot.local",
                    role="attendee",
                    attendee_id=attendee.id,
                    password_hash=hash_password(f"{ATTENDEE_BOOTSTRAP_PASSWORD}-{attendee.id}"),
                    failed_attempts=0,
                    locked_until=0,
                )
            )
        db.commit()
        print(
            f"Seeded {len(rows)} attendees and {len(attendees) + 1} users "
            "(organizer + per-attendee login credentials)."
        )
    finally:
        db.close()


if __name__ == "__main__":
    seed()
