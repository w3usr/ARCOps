"""Development settings: SQLite under ./var, console email, debug on. Never used on a server."""

from .base import *  # noqa: F403

DEBUG = True
SECRET_KEY = SECRET_KEY or "dev-only-not-secret"  # noqa: F405
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]", "testserver"]
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
STORAGES["staticfiles"] = {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}  # noqa: F405
MFA_WEBAUTHN_ALLOW_INSECURE_ORIGIN = True  # localhost over http
SITE_URL = "http://localhost:8000"
