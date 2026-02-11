from urllib.parse import unquote_plus

from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import AppUser, Attendee, ExternalSignal
from scripts.seed_data import seed


def _login_organizer(client: TestClient):
    client.get("/login")
    csrf = client.cookies.get("csrf_token")
    resp = client.post(
        "/login",
        data={
            "role": "organizer",
            "csrf_token": csrf,
            "email": "organizer@pot.local",
            "password": "organizer123",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303


def test_attendee_uses_per_attendee_passcode_pattern():
    seed()
    client = TestClient(app)

    client.get("/login")
    csrf = client.cookies.get("csrf_token")
    bad = client.post(
        "/login",
        data={
            "role": "attendee",
            "csrf_token": csrf,
            "attendee_id": 1,
            "passcode": "attendee123",
        },
    )
    assert bad.status_code == 200
    assert "Invalid attendee credentials" in bad.text

    csrf = client.cookies.get("csrf_token")
    good = client.post(
        "/login",
        data={
            "role": "attendee",
            "csrf_token": csrf,
            "attendee_id": 1,
            "passcode": "attendee123-1",
        },
        follow_redirects=False,
    )
    assert good.status_code == 303
    assert good.headers["location"] == "/attendees/1"


def test_feedback_rejects_cross_attendee_match_tampering():
    seed()
    client = TestClient(app)
    _login_organizer(client)

    match_resp = client.get("/v1/matches/2")
    assert match_resp.status_code == 200
    matches = match_resp.json()["matches"]
    assert matches
    target_match_id = matches[0]["match_id"]

    csrf = client.cookies.get("csrf_token")
    bad_feedback = client.post(
        "/v1/feedback",
        json={
            "attendee_id": 1,
            "match_id": target_match_id,
            "rating": 5,
            "outcome": "met",
            "comment": "tamper attempt",
        },
        headers={"x-csrf-token": csrf},
    )
    assert bad_feedback.status_code == 403
    assert bad_feedback.json()["detail"] == "Feedback target mismatch"


def test_linkedin_opt_in_requires_profile_url():
    seed()
    client = TestClient(app)
    _login_organizer(client)

    csrf = client.cookies.get("csrf_token")
    resp = client.post(
        "/organizer/attendees",
        data={
            "csrf_token": csrf,
            "name": "Test User",
            "role": "Founder & CEO",
            "company": "Demo Co",
            "primary_goal": "Investment",
            "language": "English",
            "availability": "day1_pm",
            "linkedin_opt_in": "on",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "linkedin_url is required when linkedin_opt_in is enabled"


def test_linkedin_opt_in_enrichment_is_persisted(monkeypatch):
    seed()
    client = TestClient(app)
    _login_organizer(client)

    monkeypatch.setattr("app.main.extract_linkedin_summary", lambda _url: "LinkedIn summary with investment thesis")

    csrf = client.cookies.get("csrf_token")
    resp = client.post(
        "/organizer/attendees",
        data={
            "csrf_token": csrf,
            "name": "LinkedIn OptIn User",
            "role": "Managing Partner",
            "company": "Alpha Capital",
            "primary_goal": "Investment",
            "language": "English",
            "availability": "day1_pm",
            "linkedin_opt_in": "on",
            "linkedin_url": "https://www.linkedin.com/in/test-profile",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "/organizer?message=" in resp.headers["location"]

    db = SessionLocal()
    try:
        attendee = (
            db.query(Attendee)
            .filter(Attendee.name == "LinkedIn OptIn User")
            .first()
        )
        assert attendee is not None
        assert attendee.linkedin_opt_in is True
        assert attendee.linkedin_url == "https://www.linkedin.com/in/test-profile"
        assert "LinkedIn summary with investment thesis" in attendee.focus_text

        signal = (
            db.query(ExternalSignal)
            .filter(
                ExternalSignal.attendee_id == attendee.id,
                ExternalSignal.source == "linkedin_profile",
            )
            .first()
        )
        assert signal is not None
    finally:
        db.close()


def test_organizer_delete_attendee_requires_confirmation_and_cleans_related_rows(monkeypatch):
    seed()
    client = TestClient(app)
    _login_organizer(client)
    monkeypatch.setattr("app.main.extract_linkedin_summary", lambda _url: "LinkedIn summary used for delete test")

    csrf = client.cookies.get("csrf_token")
    created = client.post(
        "/organizer/attendees",
        data={
            "csrf_token": csrf,
            "name": "Delete Me",
            "role": "Founder & CEO",
            "company": "DeleteCo",
            "primary_goal": "Investment",
            "language": "English",
            "availability": "day1_pm",
            "linkedin_opt_in": "on",
            "linkedin_url": "https://www.linkedin.com/in/delete-me",
        },
        follow_redirects=False,
    )
    assert created.status_code == 303

    db = SessionLocal()
    try:
        attendee = db.query(Attendee).filter(Attendee.name == "Delete Me").first()
        assert attendee is not None
        attendee_id = attendee.id
    finally:
        db.close()

    csrf = client.cookies.get("csrf_token")
    mismatch = client.post(
        f"/organizer/attendees/{attendee_id}/delete",
        data={
            "csrf_token": csrf,
            "confirm_name": "Wrong Name",
            "page": 1,
            "page_size": 100,
        },
        follow_redirects=False,
    )
    assert mismatch.status_code == 303
    assert f"confirm_delete={attendee_id}" in mismatch.headers["location"]

    db = SessionLocal()
    try:
        assert db.query(Attendee).filter(Attendee.id == attendee_id).first() is not None
    finally:
        db.close()

    csrf = client.cookies.get("csrf_token")
    deleted = client.post(
        f"/organizer/attendees/{attendee_id}/delete",
        data={
            "csrf_token": csrf,
            "confirm_name": "Delete Me",
            "page": 1,
            "page_size": 100,
        },
        follow_redirects=False,
    )
    assert deleted.status_code == 303
    assert "/organizer?" in deleted.headers["location"]

    db = SessionLocal()
    try:
        assert db.query(Attendee).filter(Attendee.id == attendee_id).first() is None
        assert db.query(AppUser).filter(AppUser.attendee_id == attendee_id).first() is None
        assert (
            db.query(ExternalSignal)
            .filter(ExternalSignal.attendee_id == attendee_id)
            .first()
            is None
        )
    finally:
        db.close()


def test_bulk_import_csv_creates_multiple_attendees():
    seed()
    client = TestClient(app)
    _login_organizer(client)

    csv_payload = (
        "name,role,company,primary_goal,availability,language,secondary_goals,seek_text,offer_text,focus_text\n"
        "Bulk User 1,Founder & CEO,Alpha Labs,Investment,day1_pm,English,Partnerships,investors,distribution,tokenization infra\n"
        "Bulk User 2,Managing Partner,Beta Capital,Partnerships,day2_am,English,Investment,founders,capital,institutional defi\n"
    )
    csrf = client.cookies.get("csrf_token")
    response = client.post(
        "/organizer/attendees/import",
        data={"csrf_token": csrf},
        files={"upload_file": ("attendees.csv", csv_payload, "text/csv")},
        follow_redirects=False,
    )
    assert response.status_code == 303
    decoded_location = unquote_plus(response.headers["location"])
    assert "created=2" in decoded_location
    assert "failed=0" in decoded_location

    db = SessionLocal()
    try:
        one = db.query(Attendee).filter(Attendee.name == "Bulk User 1").first()
        two = db.query(Attendee).filter(Attendee.name == "Bulk User 2").first()
        assert one is not None
        assert two is not None
        assert db.query(AppUser).filter(AppUser.attendee_id == one.id).first() is not None
        assert db.query(AppUser).filter(AppUser.attendee_id == two.id).first() is not None
    finally:
        db.close()


def test_bulk_import_partial_failure_reports_row_errors():
    seed()
    client = TestClient(app)
    _login_organizer(client)

    csv_payload = (
        "name,role,company,primary_goal\n"
        "Bulk Good,Founder & CEO,GoodCo,Investment\n"
        ",Managing Partner,BadCo,Investment\n"
    )
    csrf = client.cookies.get("csrf_token")
    response = client.post(
        "/organizer/attendees/import",
        data={"csrf_token": csrf},
        files={"upload_file": ("attendees.csv", csv_payload, "text/csv")},
        follow_redirects=False,
    )
    assert response.status_code == 303
    decoded_location = unquote_plus(response.headers["location"])
    assert "created=1" in decoded_location
    assert "failed=1" in decoded_location
    assert "row 3: name is required" in decoded_location

    db = SessionLocal()
    try:
        assert db.query(Attendee).filter(Attendee.name == "Bulk Good").first() is not None
        assert db.query(Attendee).filter(Attendee.company == "BadCo").first() is None
    finally:
        db.close()
