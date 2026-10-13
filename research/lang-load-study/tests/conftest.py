"""Every test module shares one app process. Point it at a throwaway SQLite file and a
test admin key before anything imports app.config."""
import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["ADMIN_KEY"] = "test-key"
os.environ.pop("PUBLIC_DEPLOYMENT", None)
os.environ.pop("IRB_APPROVED", None)
