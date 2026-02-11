from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Attendee(Base):
    __tablename__ = "attendees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(120), nullable=False)
    company: Mapped[str] = mapped_column(String(120), nullable=False)
    language: Mapped[str] = mapped_column(String(32), default="English")
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Paris")
    primary_goal: Mapped[str] = mapped_column(String(120), nullable=False)
    secondary_goals: Mapped[str] = mapped_column(String(240), default="")
    exclusions: Mapped[str] = mapped_column(String(240), default="")
    availability: Mapped[str] = mapped_column(String(240), default="")
    focus_text: Mapped[str] = mapped_column(Text, default="")
    seek_text: Mapped[str] = mapped_column(Text, default="")
    offer_text: Mapped[str] = mapped_column(Text, default="")
    seed_confidence: Mapped[float] = mapped_column(Float, default=0.7)

class MatchResult(Base):
    __tablename__ = "matches"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    attendee_id: Mapped[int] = mapped_column(ForeignKey("attendees.id"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("attendees.id"), index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    exploration_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    reason_1: Mapped[str] = mapped_column(String(280), default="")
    reason_2: Mapped[str] = mapped_column(String(280), default="")
    reason_3: Mapped[str] = mapped_column(String(280), default="")


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), index=True)
    attendee_id: Mapped[int] = mapped_column(ForeignKey("attendees.id"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("attendees.id"), index=True)
    rating: Mapped[int] = mapped_column(Integer)  # 1-5
    outcome: Mapped[str] = mapped_column(String(80), default="reviewed")
    comment: Mapped[str] = mapped_column(String(280), default="")


class IntroRequest(Base):
    __tablename__ = "intro_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("attendees.id"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("attendees.id"), index=True)
    status: Mapped[str] = mapped_column(String(40), default="pending_candidate")
    note: Mapped[str] = mapped_column(String(280), default="")


class ExternalSignal(Base):
    __tablename__ = "external_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    attendee_id: Mapped[int] = mapped_column(ForeignKey("attendees.id"), index=True)
    source: Mapped[str] = mapped_column(String(80), default="company_website")
    source_url: Mapped[str] = mapped_column(String(280), default="")
    extracted_summary: Mapped[str] = mapped_column(Text, default="")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    actor_role: Mapped[str] = mapped_column(String(40), default="anonymous")
    actor_label: Mapped[str] = mapped_column(String(120), default="")
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    target_type: Mapped[str] = mapped_column(String(80), default="")
    target_id: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(40), default="success")
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AppUser(Base):
    __tablename__ = "app_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(180), unique=True, nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(40), nullable=False)
    attendee_id: Mapped[int | None] = mapped_column(
        ForeignKey("attendees.id"), nullable=True, unique=True, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(280), nullable=False)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[int] = mapped_column(Integer, default=0)
