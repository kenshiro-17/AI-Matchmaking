import random
import statistics
import sys
import time
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import Base
from app.models import Attendee
from app.services.matching import build_matches_for_attendee


ROLES = [
    "Managing Director",
    "General Partner",
    "Founder & CEO",
    "CTO",
    "Head of Digital Assets",
    "Policy Advisor",
]
COMPANIES = [
    "Sovereign Fund",
    "Crypto VC",
    "Tokenization Platform",
    "Layer 2 Protocol",
    "European Bank",
    "Digital Finance Forum",
]
GOALS = ["Investment", "Partnerships", "Hiring", "Regulation", "Learning"]
SLOTS = ["day1_am", "day1_pm", "day2_am", "day2_pm"]


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal()


def seed_attendees(db: Session, count: int = 2500):
    for i in range(1, count + 1):
        role = random.choice(ROLES)
        company = random.choice(COMPANIES)
        goal = random.choice(GOALS)
        availability = ",".join(random.sample(SLOTS, k=2))
        row = Attendee(
            name=f"Attendee {i}",
            role=role,
            company=company,
            language="English",
            primary_goal=goal,
            availability=availability,
            secondary_goals="Partnerships,Learning",
            focus_text="institutional allocation tokenization compliance infrastructure",
            seek_text="investors partners policy guidance",
            offer_text="capital distribution product expertise",
        )
        db.add(row)
    db.commit()


def run_benchmark():
    db = _db()
    try:
        seed_attendees(db, 2500)
        ids = [row.id for row in db.query(Attendee.id).limit(30).all()]
        durations = []
        for attendee_id in ids:
            start = time.perf_counter()
            build_matches_for_attendee(db, attendee_id, top_n=5)
            durations.append((time.perf_counter() - start) * 1000)

        p50 = statistics.median(durations)
        p95 = sorted(durations)[max(0, int(len(durations) * 0.95) - 1)]
        avg = statistics.mean(durations)
        print(f"Benchmark with 2500 attendees over {len(durations)} runs")
        print(f"avg={avg:.2f}ms p50={p50:.2f}ms p95={p95:.2f}ms")
    finally:
        db.close()


if __name__ == "__main__":
    run_benchmark()
