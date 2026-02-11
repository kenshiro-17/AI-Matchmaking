from fastapi.testclient import TestClient

from app.main import app
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
