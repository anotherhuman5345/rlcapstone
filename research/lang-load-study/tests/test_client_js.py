"""Browser-side session controller, run under Node with a fake DOM and clock
(tests/client_js_check.mjs): one start transition per plugin task, the deadline freeze,
both stop buttons, and retrying a failed save. Skipped where Node is not installed."""
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_session_controller_in_node():
    script = Path(__file__).with_name("client_js_check.mjs")
    r = subprocess.run(["node", str(script)], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.count("ok ") == 5, r.stdout
