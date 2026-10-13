"""Database models. No names, emails, or IP addresses are ever stored."""
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import (JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer,
                        String, Text, create_engine, inspect, text)
from sqlalchemy.orm import (DeclarativeBase, Mapped, mapped_column,
                            relationship, sessionmaker)
from sqlalchemy.pool import NullPool

from .config import DATABASE_URL

log = logging.getLogger(__name__)


def make_engine(url: str, **connect_args):
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False, **connect_args})
    # Postgres behind a transaction pooler (Supabase), used from short-lived serverless
    # functions: no client-side pool and no prepared statements.
    return create_engine(url.replace("postgresql://", "postgresql+psycopg://", 1),
                         poolclass=NullPool, connect_args={"prepare_threshold": None, **connect_args})


engine = make_engine(DATABASE_URL)
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
    ui_lang: Mapped[str] = mapped_column(String(5), default="en")

    # Background questionnaire
    group: Mapped[str | None] = mapped_column(String(20))
    age: Mapped[int | None] = mapped_column(Integer)
    education_years: Mapped[int | None] = mapped_column(Integer)
    years_reading_images: Mapped[float | None] = mapped_column(Float)
    native_lang: Mapped[str | None] = mapped_column(String(10))
    l2_age_acquired: Mapped[int | None] = mapped_column(Integer)
    l1: Mapped[str | None] = mapped_column(String(5))  # most comfortable reading language
    l2: Mapped[str | None] = mapped_column(String(5))  # the other language they read
    l1_reading: Mapped[int | None] = mapped_column(Integer)  # 1-7 self-rating
    l2_reading: Mapped[int | None] = mapped_column(Integer)  # 1-7 self-rating
    # Protocol inclusion rule: reads both languages at 3+ on the 1-7 scale.
    # Ineligible people can still finish; they are flagged and excluded in analysis.
    eligible: Mapped[bool | None] = mapped_column(Boolean)
    # True when the person says both languages are equally comfortable; L1/L2 then
    # only mark which language they listed first, and analysis keeps the tie.
    equal_comfort: Mapped[bool] = mapped_column(Boolean, default=False)
    # End-of-session word recognition: [{"word", "lang", "cond", "seen", "checked"}, ...]
    retention: Mapped[list | None] = mapped_column(JSON)

    # Assignment
    counterbalance: Mapped[int | None] = mapped_column(Integer)
    # Version stamps taken when the plan was assigned (study, commit, stimuli, the
    # translation and task-text files in use). Exports read these, never today's files.
    versions: Mapped[dict | None] = mapped_column(JSON)
    # What the current trial page showed and when (index, UTC time, version stamps),
    # so the stored row describes what was presented even across a redeploy.
    presented: Mapped[dict | None] = mapped_column(JSON)
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
    # Time on task: elapsed_s counts from the first image (the surprise trial).
    task_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # The hard session cap counts from the first SCORED stimulus (consent, background,
    # instructions and practice are outside it). The deadline is written once and never
    # renewed, so refreshing a page cannot buy more time.
    cap_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    time_capped: Mapped[bool] = mapped_column(Boolean, default=False)
    # How the session ended, if it was stopped before the plan ran out:
    # "exhausted" / "withdrawn" (the person), "time_cap" / "stale_request" /
    # "technical_failure" (administrative). None = plan finished, or unknown ending
    # (page closed). Written once; a second stop request changes nothing.
    stop_reason: Mapped[str | None] = mapped_column(String(32))
    stop_requested: Mapped[str | None] = mapped_column(String(32))  # what the browser asked for
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # server UTC
    stop_elapsed_s: Mapped[float | None] = mapped_column(Float)  # seconds since cap_started_at
    stop_clock_basis: Mapped[str | None] = mapped_column(String(64))
    # Kept for continuity: quit_early is True only for "I'm exhausted".
    quit_early: Mapped[bool] = mapped_column(Boolean, default=False)
    quit_elapsed_s: Mapped[float | None] = mapped_column(Float)
    quit_trial: Mapped[int | None] = mapped_column(Integer)  # trial in progress when stopped
    final_skipped: Mapped[bool] = mapped_column(Boolean, default=False)
    overall_difficulty: Mapped[int | None] = mapped_column(Integer)

    trials: Mapped[list["TrialResult"]] = relationship(back_populates="participant")


class TrialResult(Base):
    __tablename__ = "trial_results"
    # One row per trial position: a double submit or a second tab cannot add another.
    __table_args__ = (Index("uq_trial_results_participant_trial", "participant_id", "trial_index",
                            unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    participant_id: Mapped[str] = mapped_column(ForeignKey("participants.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    trial_index: Mapped[int] = mapped_column(Integer)
    task: Mapped[str] = mapped_column(String(64))        # "surprise", "search", or a library task id
    round: Mapped[int | None] = mapped_column(Integer)   # 1..ROUNDS; None for surprise/practice
    elapsed_s: Mapped[float | None] = mapped_column(Float)  # seconds since the first image
    image_id: Mapped[str] = mapped_column(String(64))
    target_object: Mapped[str | None] = mapped_column(String(64))  # e.g. "fish"; varies per picture
    clue_lang: Mapped[str] = mapped_column(String(16))   # language code, e.g. "en", "tr", "ja"
    condition: Mapped[str] = mapped_column(String(2))    # "L1" or "L2"
    practice: Mapped[bool] = mapped_column(Boolean, default=False)
    rt_ms: Mapped[float | None] = mapped_column(Float)   # time to the response, hit or not
    hit: Mapped[bool] = mapped_column(Boolean, default=False)
    # Click tasks (search, scan, dice, surprise), scored on the server from the click list.
    first_click_ms: Mapped[float | None] = mapped_column(Float)
    first_click_correct: Mapped[bool | None] = mapped_column(Boolean)
    wrong_clicks: Mapped[int | None] = mapped_column(Integer)
    timed_out: Mapped[bool] = mapped_column(Boolean, default=False)
    false_clicks: Mapped[int] = mapped_column(Integer, default=0)
    effort: Mapped[int | None] = mapped_column(Integer)  # Paas 1-9
    reloads: Mapped[int] = mapped_column(Integer, default=0)  # page reloads before answering
    focus_lost: Mapped[int] = mapped_column(Integer, default=0)  # times the tab was hidden mid-trial
    # The complete raw response as JSON (never truncated): clicks, choices, event lists.
    response: Mapped[str | None] = mapped_column(Text)
    # Task-library tasks: full response and summary scores (JSON); can be long.
    metrics: Mapped[str | None] = mapped_column(Text)
    # Browser timing envelope (JSON): instructions, start, first response, completion.
    timing: Mapped[str | None] = mapped_column(Text)
    presented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # server UTC
    # Received after the session deadline (kept, but flagged).
    late: Mapped[bool] = mapped_column(Boolean, default=False)
    # Saved by a stop (exhausted, withdrawn, time cap...) while the trial was in progress.
    partial: Mapped[bool] = mapped_column(Boolean, default=False)
    # Version stamps from when the trial was presented; None on rows from before they existed.
    study_version: Mapped[str | None] = mapped_column(String(64))
    software_commit: Mapped[str | None] = mapped_column(String(64))
    stimuli_version: Mapped[str | None] = mapped_column(String(64))
    translation_version: Mapped[str | None] = mapped_column(String(64))
    task_text_version: Mapped[str | None] = mapped_column(String(64))
    clue_text: Mapped[str | None] = mapped_column(Text)  # the clue exactly as it was shown

    participant: Mapped[Participant] = relationship(back_populates="trials")


class FatigueRating(Base):
    """'How mentally tired do you feel right now?' 0-100, at the start, after each
    round, and at the end. Same wording every time."""
    __tablename__ = "fatigue_ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    participant_id: Mapped[str] = mapped_column(ForeignKey("participants.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    point: Mapped[str] = mapped_column(String(32))  # "baseline", "after_round_3", "final"
    value: Mapped[int] = mapped_column(Integer)
    elapsed_s: Mapped[float | None] = mapped_column(Float)  # seconds since the first image
    late: Mapped[bool] = mapped_column(Boolean, default=False)  # after the session deadline
    study_version: Mapped[str | None] = mapped_column(String(64))
    software_commit: Mapped[str | None] = mapped_column(String(64))


class AllocationCounter(Base):
    """Next counterbalance slot per pool ("real:<group>" or "test:<group>"). Incremented
    with one UPDATE inside the enrolment transaction, so simultaneous enrolments get
    different slots and demo sessions never shift the real-study rotation."""
    __tablename__ = "allocation_counters"

    pool: Mapped[str] = mapped_column(String(64), primary_key=True)
    next_index: Mapped[int] = mapped_column(Integer, default=0)


def init_db(eng=None):
    eng = eng or engine
    Base.metadata.create_all(eng)
    _add_missing_columns(eng)
    _widen_columns(eng)
    _add_unique_trial_index(eng)


def _add_missing_columns(eng):
    """Tiny migration: when a new version adds columns, add them to an existing
    database instead of failing. Old columns are left alone, so no data is lost."""
    insp = inspect(eng)
    with eng.begin() as conn:
        for table in Base.metadata.sorted_tables:
            have = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name not in have:
                    ddl = col.type.compile(dialect=eng.dialect)
                    conn.execute(text(f'ALTER TABLE {table.name} ADD COLUMN "{col.name}" {ddl}'))


def _widen_columns(eng):
    """Older databases declared short VARCHARs (task ids were String(10), responses were
    String(200)). PostgreSQL enforces those lengths, so long library-task ids failed to
    insert. Widen any column whose declared type is now longer, keeping every value.
    SQLite never enforces VARCHAR lengths, so there is nothing to do there."""
    if eng.dialect.name != "postgresql":
        return
    insp = inspect(eng)
    with eng.begin() as conn:
        for table in Base.metadata.sorted_tables:
            have = {c["name"]: c["type"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                old = have.get(col.name)
                want = getattr(col.type, "length", None)
                old_len = getattr(old, "length", None)
                if old is None or old_len is None:
                    continue  # already TEXT / not a sized string
                if isinstance(col.type, Text) or (want is not None and want > old_len):
                    ddl = col.type.compile(dialect=eng.dialect)
                    conn.execute(text(f'ALTER TABLE {table.name} ALTER COLUMN "{col.name}" TYPE {ddl}'))


def _add_unique_trial_index(eng):
    """One trial row per (participant, trial_index). If an existing database already
    holds duplicates, nothing is deleted: the index is skipped and a warning logged so
    a person can review the rows (analysis should keep the earliest)."""
    name = "uq_trial_results_participant_trial"
    if any(ix["name"] == name for ix in inspect(eng).get_indexes("trial_results")):
        return
    with eng.begin() as conn:
        dupes = conn.execute(text(
            "SELECT participant_id, trial_index, COUNT(*) FROM trial_results "
            "GROUP BY participant_id, trial_index HAVING COUNT(*) > 1")).all()
        if dupes:
            log.warning("trial_results has %d duplicated (participant, trial_index) pairs; "
                        "unique index %s not added. Review them; nothing was deleted.", len(dupes), name)
            return
        conn.execute(text(f"CREATE UNIQUE INDEX IF NOT EXISTS {name} "
                          "ON trial_results (participant_id, trial_index)"))
