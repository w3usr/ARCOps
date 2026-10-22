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


def pytest_addoption(parser):
    parser.addoption(
        "--contact-sheet",
        action="store_true",
        default=False,
        help="write a screenshot of every page into var/contact-sheet/ for review by eye",
    )


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


# Every check runs in the three engines people actually use: Chromium (Chrome, Edge), Firefox,
# and WebKit (Safari). A page can pass in one and fail in another: Skip to content moved focus
# in none of them until <main> could take it, and SK found that with VoiceOver in Firefox
# (2026-10-22: "everyone uses different browsers, and it's important that it works across all
# of them"). `playwright install chromium firefox webkit` once.
ENGINES = ("chromium", "firefox", "webkit")


@pytest.fixture(params=ENGINES)
def engine(request):
    """The name of a Playwright browser type; `getattr(p, engine).launch()` starts it."""
    return request.param


@pytest.fixture(autouse=True)
def demo(db):
    from django.core.management import call_command

    call_command("club_import", verbosity=0)
    call_command("seed_demo", verbosity=0)
    yield
    # The live server empties every table after each test, and the audit log refuses a DELETE
    # (TR-21). Its triggers go from this throwaway database only; nothing here tests the log.
    import importlib

    from django.db import connection

    with connection.cursor() as cursor:
        for sql in importlib.import_module("apps.ops.migrations.0010_auditlog_append_only").DROP:
            cursor.execute(sql)
