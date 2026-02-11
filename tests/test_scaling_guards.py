from app.models import Attendee
from app.services.scenarios import MAX_SCENARIO_RESULTS, strategic_scenarios


def test_strategic_scenarios_is_bounded_for_large_inputs():
    attendees = []
    idx = 1
    for _ in range(80):
        attendees.append(
            Attendee(
                id=idx,
                name=f"CTO {idx}",
                role="CTO",
                company="Layer 2 Protocol",
                primary_goal="Partnerships",
                focus_text="l2 zk compliance infrastructure",
                seek_text="bank partnerships",
                offer_text="architecture",
            )
        )
        idx += 1
        attendees.append(
            Attendee(
                id=idx,
                name=f"Bank {idx}",
                role="Head of Digital Assets",
                company="European Bank",
                primary_goal="Partnerships",
                focus_text="institutional custody compliant deployment",
                seek_text="tech partners",
                offer_text="distribution",
            )
        )
        idx += 1
        attendees.append(
            Attendee(
                id=idx,
                name=f"Founder {idx}",
                role="Founder & CEO",
                company="Tokenization Startup",
                primary_goal="Investment",
                focus_text="raising series B investment",
                seek_text="investor introductions",
                offer_text="product velocity",
            )
        )
        idx += 1
        attendees.append(
            Attendee(
                id=idx,
                name=f"GP {idx}",
                role="General Partner",
                company="Crypto VC Capital",
                primary_goal="Investment",
                focus_text="deal flow",
                seek_text="founders",
                offer_text="capital",
            )
        )
        idx += 1
        attendees.append(
            Attendee(
                id=idx,
                name=f"LP {idx}",
                role="Managing Director",
                company="Institutional Fund",
                primary_goal="Investment",
                focus_text="allocation",
                seek_text="managers",
                offer_text="institutional context",
            )
        )
        idx += 1

    scenarios = strategic_scenarios(attendees)
    assert len(scenarios) <= MAX_SCENARIO_RESULTS
