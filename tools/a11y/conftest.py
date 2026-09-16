"""Pytest wiring for the accessibility check: Django's live server with the demo seeded before
every test (the live server flushes the database between tests), and static files served
from the source tree so the pages are checked with their real styling."""

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")


def pytest_configure():
    import tempfile

    from django.conf import settings

    settings.WHITENOISE_USE_FINDERS = True
    settings.WHITENOISE_AUTOREFRESH = True
    # The live server answers a browser's parallel requests from several threads. SQLite's shared
    # in-memory test database misreads rows under that concurrency (seen on CI as an IndexError
    # deep in the session lookup); a file on disk does not.
    db = settings.DATABASES["default"]
    db.setdefault("TEST", {})["NAME"] = str(Path(tempfile.mkdtemp(prefix="a11y-")) / "test.sqlite3")
    db.setdefault("OPTIONS", {})["timeout"] = 60


@pytest.fixture(autouse=True)
def demo(db):
    from django.core.management import call_command

    call_command("club_import", verbosity=0)
    call_command("seed_demo", verbosity=0)
