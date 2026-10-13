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
# Set PUBLIC_DEPLOYMENT=1 on any internet-facing host, demo included. Admin cookies are
# then marked Secure and the app refuses to start with the default admin key.
PUBLIC_DEPLOYMENT = os.getenv("PUBLIC_DEPLOYMENT", "0") == "1"
DEFAULT_ADMIN_KEYS = {"", "change-me"}


def check_admin_key():
    if (IRB_APPROVED or PUBLIC_DEPLOYMENT) and ADMIN_KEY in DEFAULT_ADMIN_KEYS:
        raise RuntimeError("Set ADMIN_KEY to a long random string before any public deployment.")


check_admin_key()

# Commit the running code was built from (Vercel sets this); stored on every data row.
SOFTWARE_COMMIT = os.getenv("VERCEL_GIT_COMMIT_SHA") or os.getenv("SOFTWARE_COMMIT") or "unknown"

STIMULI_DIR = Path(os.getenv("STIMULI_DIR", ROOT / "stimuli" / "output"))
MANIFEST = STIMULI_DIR / "manifest.json"

# What one round contains: pictures per task (each must be even, half L1 and half
# L2). Every round has the same mix, so changes across rounds come from time on
# task. People keep going until they press "I'm exhausted"; the time it takes is
# the main fatigue measure. There are enough rounds for the safety limit below. Override with e.g. ROUND_MIX="search:4,scan:4,dice:4".
ROUND_MIX = {k: int(v) for k, v in (pair.split(":") for pair in
             os.getenv("ROUND_MIX", "search:2,scan:2,dice:2,corsi:2,reading:2,rule:2,ospan:2").split(","))}
ROUNDS = int(os.getenv("ROUNDS", "24"))
# Version stamp written into every data row; bump it whenever the study changes.
STUDY_VERSION = "2026.10.13-tasks7"
TRIAL_TIMEOUT_MS = int(os.getenv("TRIAL_TIMEOUT_MS", "30000"))
# Safety maximum (stated in the consent text): this many minutes after the first
# SCORED stimulus, every task screen ends at once and the person goes to the final
# questions (which are outside the cap). Consent, background, instructions and practice
# do not count. Change the consent wording in every language if you change this.
SESSION_LIMIT_MIN = float(os.getenv("SESSION_LIMIT_MIN", "60"))
# Youngest age accepted on the background form (protocol: 16+).
MIN_AGE = int(os.getenv("MIN_AGE", "16"))
# Upper bound for any time a browser reports (ms); anything larger is rejected as invalid.
MAX_REPORTED_MS = float(os.getenv("MAX_REPORTED_MS", str(4 * 60 * 60 * 1000)))
# A click counts as a hit if it lands within target radius * this factor.
HIT_TOLERANCE = float(os.getenv("HIT_TOLERANCE", "1.6"))
# Minimum self-rated reading level (1-7) in BOTH languages to be included.
MIN_READING = 3

GROUPS = ("high_school", "undergraduate", "adult", "phd_student", "professor",
          "physician", "radiologist", "other")
