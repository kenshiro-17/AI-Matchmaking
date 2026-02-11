from app.models import Attendee
from app.services.scenarios import strategic_scenarios


def test_strategic_scenarios_surface_pair_and_triad():
    attendees = [
        Attendee(
            id=1,
            name="Sarah Chen",
            role="Managing Director",
            company="Sovereign Wealth Fund",
            primary_goal="Investment",
            focus_text="institutional allocation",
            seek_text="lp exposure",
            offer_text="capital",
        ),
        Attendee(
            id=2,
            name="Marcus Weber",
            role="CEO & Founder",
            company="Tokenization Platform",
            primary_goal="Investment",
            focus_text="raising series B",
            seek_text="institutional investors fundraising",
            offer_text="growth",
        ),
        Attendee(
            id=3,
            name="Aisha Patel",
            role="General Partner",
            company="Crypto VC Fund",
            primary_goal="Investment",
            focus_text="deal flow",
            seek_text="co-investors",
            offer_text="capital",
        ),
        Attendee(
            id=4,
            name="Kenji Nakamura",
            role="CTO",
            company="Layer 2 Protocol",
            primary_goal="Partnerships",
            focus_text="compliance infrastructure zk l2",
            seek_text="bank partners",
            offer_text="architecture",
        ),
        Attendee(
            id=5,
            name="Elena Rossi",
            role="Head of Digital Assets",
            company="European Bank",
            primary_goal="Partnerships",
            focus_text="institutional custody compliant rollout",
            seek_text="tech partners",
            offer_text="bank distribution",
        ),
    ]

    scenarios = strategic_scenarios(attendees)
    pair_hits = [s for s in scenarios if s["type"] == "pair_synergy"]
    triad_hits = [s for s in scenarios if s["type"] == "triad_synergy"]

    assert any("Kenji Nakamura" in s["participants"] and "Elena Rossi" in s["participants"] for s in pair_hits)
    assert any(
        set(["Marcus Weber", "Aisha Patel", "Sarah Chen"]).issubset(set(s["participants"]))
        for s in triad_hits
    )
