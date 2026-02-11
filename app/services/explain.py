from app.models import Attendee


def make_reasons(requester: Attendee, candidate: Attendee, score_parts: dict[str, float]) -> list[str]:
    reasons = []
    if score_parts["goal"] > 20:
        reasons.append(
            f"Your primary goal ({requester.primary_goal}) aligns with {candidate.name}'s current focus."
        )
    if score_parts["complementarity"] > 14:
        reasons.append(
            f"You bring complementary value: {requester.role} and {candidate.role}."
        )
    if requester.availability and candidate.availability:
        reasons.append("You both have overlapping declared availability windows.")

    if len(reasons) < 3:
        reasons.append(
            f"Strategic fit is high for {requester.primary_goal.lower()} outcomes."
        )
    return reasons[:3]
