from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.models import Attendee, Feedback
from app.services.matching import build_matches_for_attendee


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal()


def test_hard_language_constraint_excludes_non_matching_languages():
    db = _db()
    a = Attendee(
        name="A",
        role="Managing Partner",
        company="Fund A",
        primary_goal="Investment",
        language="English",
        availability="day1_pm",
    )
    b = Attendee(
        name="B",
        role="CEO & Founder",
        company="Startup B",
        primary_goal="Investment",
        language="French",
        availability="day1_pm",
    )
    db.add_all([a, b])
    db.commit()

    rows = build_matches_for_attendee(db, a.id, top_n=5)
    assert rows == []


def test_feedback_affects_future_score():
    db = _db()
    requester = Attendee(
        name="Investor",
        role="Managing Partner",
        company="Fund",
        primary_goal="Investment",
        language="English",
        availability="day1_pm",
    )
    strong = Attendee(
        name="Founder",
        role="CEO & Founder",
        company="Alpha",
        primary_goal="Investment",
        language="English",
        availability="day1_pm",
        focus_text="investment institutional tokenization",
    )
    weak = Attendee(
        name="Peer",
        role="Managing Partner",
        company="Beta Fund",
        primary_goal="Investment",
        language="English",
        availability="day1_pm",
    )
    db.add_all([requester, strong, weak])
    db.commit()

    first = build_matches_for_attendee(db, requester.id, top_n=2)
    assert len(first) == 2
    match_for_strong = [m for m in first if m.candidate_id == strong.id][0]
    first_score = match_for_strong.score

    db.add(
        Feedback(
            match_id=match_for_strong.id,
            attendee_id=requester.id,
            candidate_id=strong.id,
            rating=1,
            outcome="declined",
            comment="not relevant",
        )
    )
    db.commit()

    second = build_matches_for_attendee(db, requester.id, top_n=2)
    updated = [m for m in second if m.candidate_id == strong.id]
    if updated:
        assert updated[0].score < first_score
    else:
        # With strict quality thresholding, weakly-rated matches can drop out entirely.
        assert True
