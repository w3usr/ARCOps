"""TR-19, TR-20: production refuses to start without its two keys, rather
than failing the first time the shared password is saved or shown."""

import os
import subprocess
import sys
from pathlib import Path

from cryptography.fernet import Fernet

ROOT = Path(__file__).resolve().parents[3]


def _start(field_key):
    env = {k: v for k, v in os.environ.items() if k != "FIELD_ENCRYPTION_KEY"}
    env["SECRET_KEY"] = "test-only"
    if field_key is not None:
        env["FIELD_ENCRYPTION_KEY"] = field_key
    return subprocess.run(
        [sys.executable, "-c", "import config.settings.prod"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


def test_production_settings_refuse_a_missing_or_malformed_field_key():
    for key in (None, "", "not-a-fernet-key"):
        r = _start(key)
        assert r.returncode != 0 and "FIELD_ENCRYPTION_KEY" in r.stderr, key
    assert _start(Fernet.generate_key().decode()).returncode == 0
