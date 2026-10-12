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

# Scored trials per task per participant (split evenly between languages).
TRIALS_PER_TASK = int(os.getenv("TRIALS_PER_TASK", "12"))
TRIAL_TIMEOUT_MS = int(os.getenv("TRIAL_TIMEOUT_MS", "60000"))
# A click counts as a hit if it lands within target radius * this factor.
HIT_TOLERANCE = float(os.getenv("HIT_TOLERANCE", "1.6"))
# Minimum self-rated reading level (1-7) in BOTH languages to be included.
MIN_READING = 3

LANGUAGES = ("en", "tr")
GROUPS = ("high_school", "undergraduate", "phd_student", "radiologist", "professor", "other")
