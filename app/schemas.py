from pydantic import BaseModel, Field


class AttendeeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=120)
    company: str = Field(min_length=1, max_length=120)
    language: str = Field(default="English", min_length=1, max_length=32)
    timezone: str = Field(default="Europe/Paris", min_length=1, max_length=64)
    primary_goal: str = Field(min_length=1, max_length=120)
    secondary_goals: str = Field(default="", max_length=240)
    exclusions: str = Field(default="", max_length=240)
    availability: str = Field(default="", max_length=240)
    focus_text: str = Field(default="", max_length=800)
    seek_text: str = Field(default="", max_length=800)
    offer_text: str = Field(default="", max_length=800)
    seed_confidence: float = 0.7


class FeedbackCreate(BaseModel):
    match_id: int
    attendee_id: int
    rating: int = Field(ge=1, le=5)
    outcome: str = Field(default="reviewed", max_length=80)
    comment: str = Field(default="", max_length=280)


class MatchView(BaseModel):
    match_id: int
    candidate_id: int
    candidate_name: str
    candidate_role: str
    candidate_company: str
    score: float
    exploration_flag: bool
    reasons: list[str]


class IntroRequestCreate(BaseModel):
    requester_id: int
    candidate_id: int
    note: str = Field(default="", max_length=280)


class IntroRequestUpdate(BaseModel):
    actor_id: int
    action: str = Field(min_length=1, max_length=24)  # accept | decline
