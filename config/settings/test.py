"""Test settings: in-memory SQLite, fast hashing, no email."""

from .dev import *  # noqa: F403

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
# One cache per test process, cleared by conftest before every test, database or not; the shared
# database cache is tested on its own (test_flows).
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
# Tests never call Have I Been Pwned; its validator is tested with the network faked
# (apps/accounts/tests/test_pwned.py).
AUTH_PASSWORD_VALIDATORS = [
    v
    for v in AUTH_PASSWORD_VALIDATORS  # noqa: F405
    if not v["NAME"].endswith("PwnedPasswordValidator")
]
