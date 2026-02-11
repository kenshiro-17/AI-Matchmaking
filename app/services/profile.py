from dataclasses import dataclass

from app.models import Attendee


ROLE_TAGS = {
    "investor": {"capital", "allocation", "funding", "thesis"},
    "founder": {"fundraising", "distribution", "partnerships", "growth"},
    "cto": {"infrastructure", "architecture", "integration", "security"},
    "bank": {"compliance", "custody", "institutional", "risk"},
    "policy": {"regulation", "framework", "public-private", "governance"},
}


@dataclass
class ProfileSignals:
    seek_tags: set[str]
    offer_tags: set[str]
    focus_tags: set[str]


def _infer_role_family(role: str) -> str:
    role_lower = role.lower()
    if "invest" in role_lower or "partner" in role_lower:
        return "investor"
    if "founder" in role_lower or "ceo" in role_lower:
        return "founder"
    if "cto" in role_lower or "engineer" in role_lower:
        return "cto"
    if "bank" in role_lower or "digital assets" in role_lower:
        return "bank"
    if "policy" in role_lower or "regulation" in role_lower:
        return "policy"
    return "founder"


def _tokenize(text: str) -> set[str]:
    return {tok.strip(".,").lower() for tok in text.split() if tok}


def build_profile(attendee: Attendee) -> ProfileSignals:
    family = _infer_role_family(attendee.role)
    base = ROLE_TAGS.get(family, set())

    focus_tags = base | _tokenize(attendee.focus_text) | _tokenize(attendee.primary_goal)
    seek_tags = _tokenize(attendee.seek_text) | _tokenize(attendee.secondary_goals) | {
        attendee.primary_goal.lower()
    }
    offer_tags = _tokenize(attendee.offer_text) | base
    return ProfileSignals(seek_tags=seek_tags, offer_tags=offer_tags, focus_tags=focus_tags)
