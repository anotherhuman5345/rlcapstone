"""Settings, read from environment variables so nothing secret lives in the repo."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{ROOT / 'study.db'}")
ADMIN_KEY = os.getenv("ADMIN_KEY", "change-me")

# IRB gate. Until the study has ethics approval, every session is stored as
# TEST data and every page shows a "demo only" banner. Set IRB_APPROVED=1
# and IRB_NUMBER=... only after approval is in writing.
IRB_APPROVED = os.getenv("IRB_APPROVED", "0") == "1"
IRB_NUMBER = os.getenv("IRB_NUMBER", "PENDING")

if IRB_APPROVED and ADMIN_KEY == "change-me":
    raise RuntimeError("Set ADMIN_KEY to a long random string before collecting real data.")

STIMULI_DIR = Path(os.getenv("STIMULI_DIR", ROOT / "stimuli" / "output"))
MANIFEST = STIMULI_DIR / "manifest.json"

# Scored trials per task per participant, split into identical rounds so
# performance can be followed over time on task (12 rounds x 4 per task).
# That is more than most people finish: the time limit below ends the session,
# so the rounds fill the whole 15 minutes for fast and slow people alike.
TRIALS_PER_TASK = int(os.getenv("TRIALS_PER_TASK", "48"))
ROUNDS = int(os.getenv("ROUNDS", "12"))
TRIAL_TIMEOUT_MS = int(os.getenv("TRIAL_TIMEOUT_MS", "30000"))
# Promise to participants: the whole session takes no more than 15 minutes.
# After this many minutes from the start page, remaining trials are skipped
# and the person goes straight to the short final questions.
SESSION_LIMIT_MIN = float(os.getenv("SESSION_LIMIT_MIN", "14"))
# A click counts as a hit if it lands within target radius * this factor.
HIT_TOLERANCE = float(os.getenv("HIT_TOLERANCE", "1.6"))
# Minimum self-rated reading level (1-7) in BOTH languages to be included.
MIN_READING = 3

LANGUAGES = ("en", "tr")
GROUPS = ("high_school", "undergraduate", "adult", "phd_student", "professor",
          "physician", "radiologist", "other")
