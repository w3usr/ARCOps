"""Test settings: in-memory SQLite, fast hashing, no email."""

from .dev import *  # noqa: F403

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
# One cache per test process, cleared by conftest before every test, database or not; the shared
# database cache is tested on its own (test_flows, private tracker 354).
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
