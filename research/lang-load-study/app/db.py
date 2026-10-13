"""Database models. No names, emails, or IP addresses are ever stored."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (JSON, Boolean, DateTime, Float, ForeignKey, Integer,
                        String, create_engine)
from sqlalchemy.orm import (DeclarativeBase, Mapped, mapped_column,
                            relationship, sessionmaker)

from .config import DATABASE_URL

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def now():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    is_test: Mapped[bool] = mapped_column(Boolean, default=True)
    consented: Mapped[bool] = mapped_column(Boolean, default=False)
    ui_lang: Mapped[str] = mapped_column(String(2), default="en")

    # Background questionnaire
    group: Mapped[str | None] = mapped_column(String(20))
    age: Mapped[int | None] = mapped_column(Integer)
    education_years: Mapped[int | None] = mapped_column(Integer)
    years_reading_images: Mapped[float | None] = mapped_column(Float)
    native_lang: Mapped[str | None] = mapped_column(String(10))
    l2_age_acquired: Mapped[int | None] = mapped_column(Integer)
    en_reading: Mapped[int | None] = mapped_column(Integer)  # 1-7 self-rating
    tr_reading: Mapped[int | None] = mapped_column(Integer)  # 1-7 self-rating
    l1: Mapped[str | None] = mapped_column(String(2))  # most comfortable reading language
    l2: Mapped[str | None] = mapped_column(String(2))  # less comfortable
    # Protocol inclusion rule: reads both languages at 3+ on the 1-7 scale.
    # Ineligible people can still finish; they are flagged and excluded in analysis.
    eligible: Mapped[bool | None] = mapped_column(Boolean)

    # Assignment
    counterbalance: Mapped[int | None] = mapped_column(Integer)
    plan: Mapped[list | None] = mapped_column(JSON)
    current_trial: Mapped[int] = mapped_column(Integer, default=0)
    # How many times the current trial page has been loaded. More than once means
    # the person saw the image before the clock restarted, so the trial is flagged.
    trial_views: Mapped[int] = mapped_column(Integer, default=0)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    attention_ok: Mapped[bool | None] = mapped_column(Boolean)
    # Surprise (inattentional blindness) questions, asked right after the first image.
    noticed_unusual: Mapped[bool | None] = mapped_column(Boolean)
    saw_gorilla: Mapped[bool | None] = mapped_column(Boolean)
    knew_gorilla_study: Mapped[bool | None] = mapped_column(Boolean)
    # Time on task: clock starts when the first image is shown.
    task_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    time_capped: Mapped[bool] = mapped_column(Boolean, default=False)
    # "I'm exhausted" button: when and where the person chose to stop.
    quit_early: Mapped[bool] = mapped_column(Boolean, default=False)
    quit_elapsed_s: Mapped[float | None] = mapped_column(Float)
    quit_trial: Mapped[int | None] = mapped_column(Integer)
    overall_difficulty: Mapped[int | None] = mapped_column(Integer)

    trials: Mapped[list["TrialResult"]] = relationship(back_populates="participant")


class TrialResult(Base):
    __tablename__ = "trial_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    participant_id: Mapped[str] = mapped_column(ForeignKey("participants.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    trial_index: Mapped[int] = mapped_column(Integer)
    task: Mapped[str] = mapped_column(String(10))        # "surprise", "search" or "scan"
    round: Mapped[int | None] = mapped_column(Integer)   # 1..ROUNDS; None for surprise/practice
    elapsed_s: Mapped[float | None] = mapped_column(Float)  # seconds since the first image
    image_id: Mapped[str] = mapped_column(String(40))
    target_object: Mapped[str | None] = mapped_column(String(20))  # e.g. "fish"; varies per picture
    clue_lang: Mapped[str] = mapped_column(String(2))    # "en" or "tr"
    condition: Mapped[str] = mapped_column(String(2))    # "L1" or "L2"
    practice: Mapped[bool] = mapped_column(Boolean, default=False)
    rt_ms: Mapped[float | None] = mapped_column(Float)   # time to correct click
    hit: Mapped[bool] = mapped_column(Boolean, default=False)
    timed_out: Mapped[bool] = mapped_column(Boolean, default=False)
    false_clicks: Mapped[int] = mapped_column(Integer, default=0)
    effort: Mapped[int | None] = mapped_column(Integer)  # Paas 1-9
    reloads: Mapped[int] = mapped_column(Integer, default=0)  # page reloads before answering

    participant: Mapped[Participant] = relationship(back_populates="trials")


def init_db():
    Base.metadata.create_all(engine)
