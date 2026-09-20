"""
Base settings for ops.w3usr.org (TR-1). dev.py, test.py, and prod.py import from here.

Everything club-specific comes from the configuration directory (config/) or an overlay
(TR-40, TR-41), never from these settings. Secrets come from the environment (TR-19).
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ------------------------------------------------------------------ overlay ---
# A directory laid out like config/ (club.yaml, static/club/, agreements/) that a club lays
# over the shipped defaults. Unset means "the generic club".
CLUB_OVERLAY_DIR = (
    Path(os.environ["CLUB_OVERLAY_DIR"]) if os.environ.get("CLUB_OVERLAY_DIR") else None
)
CLUB_DEFAULTS_DIR = BASE_DIR / "config"

SECRET_KEY = os.environ.get("SECRET_KEY", "")
DEBUG = False
ALLOWED_HOSTS: list[str] = []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "allauth",
    "allauth.account",
    "allauth.mfa",
    "apps.ops",
    "apps.accounts",
    "apps.credentials",
    "apps.events",
    "apps.comms",
    "tinymce",  # TR-6, FR-115: the WYSIWYG editor, served from this origin
]

# FR-115: headings at three levels, paragraphs, bold and italic, lists, links, simple tables; the
# editor's H1 renders as the page's next level down (the richtext filter shifts headings). No
# inline scripts: django-tinymce initialises from a data attribute (CSP script-src 'self').
TINYMCE_DEFAULT_CONFIG = {
    "height": 320,
    "menubar": False,
    "plugins": "lists link table",
    "toolbar": "blocks | bold italic | bullist numlist | link table | removeformat",
    "block_formats": "Paragraph=p; Heading 1=h1; Heading 2=h2; Heading 3=h3",
    "valid_elements": "h1,h2,h3,p,ol,ul,li,strong/b,em/i,a[href|title],table,thead,tbody,tr,th[scope],td,br,blockquote",
    "branding": False,
    "statusbar": False,  # its path items carry ARIA that fails axe (aria-allowed-attr); FR-117
    "promotion": False,
    "convert_urls": False,
    "content_style": "body { font-family: system-ui, sans-serif; font-size: 16px; }",
    "a11y_advanced_options": True,
}
TINYMCE_JS_URL = "/static/tinymce/tinymce.min.js"
TINYMCE_COMPRESSOR = False

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    # After messages and allauth, because it posts a message and may sign the user out.
    "apps.accounts.middleware.AccountGateMiddleware",
    # The view the session is acting at, which decides what this account may do right now. Before
    # impersonation, so that dropping to a lower view also takes away the power to impersonate.
    "apps.accounts.acting.ActingViewMiddleware",
    # FR-94: a sysadmin viewing as a member, read-only; after the gate, so the gate sees the
    # sysadmin and this sees the member.
    "apps.accounts.impersonate.ImpersonationMiddleware",
    "apps.accounts.guardian.ActingForMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

_template_dirs = [BASE_DIR / "templates"]
if CLUB_OVERLAY_DIR and (CLUB_OVERLAY_DIR / "templates").is_dir():
    _template_dirs.insert(0, CLUB_OVERLAY_DIR / "templates")  # overlay wins (TR-41)

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": _template_dirs,
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.ops.context_processors.club",
                "apps.ops.context_processors.product",
                "apps.accounts.acting.context",
                "apps.comms.context_processors.unread",
                "apps.credentials.context_processors.approvals_waiting",
                "apps.accounts.impersonate.context",
                "apps.accounts.guardian.context",
            ],
        },
    },
]

# ---------------------------------------------------------------- database ---
# SQLite in WAL mode, one file (TR-2). VAR_DIR is outside the checkout in production.
VAR_DIR = Path(os.environ.get("VAR_DIR", BASE_DIR / "var"))
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": VAR_DIR / "ops.sqlite3",
        "OPTIONS": {
            "init_command": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA foreign_keys=ON;",
            "transaction_mode": "IMMEDIATE",
            # One writer at a time in SQLite: a long import must wait for a web request's write,
            # and a request must wait for one import batch, not fail after five seconds.
            "timeout": 60,
        },
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -------------------------------------------------------------------- auth ---
AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",  # TR-15
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "dashboard"
ACCOUNT_LOGOUT_REDIRECT_URL = "account_login"

# allauth (TR-15, TR-16). Invitation-only: signup is closed in the adapter (FR-1).
ACCOUNT_ADAPTER = "apps.accounts.adapter.AccountAdapter"
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
# Addresses live in their own rows (apps.accounts.models.Address), mirrored into the library's
# table; the user row has no address field for it to consult.
ACCOUNT_USER_MODEL_EMAIL_FIELD = None
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = "none"  # nothing may depend on email delivery (FR-103)
ACCOUNT_SESSION_REMEMBER = None  # the user chooses (TR-17)
ACCOUNT_LOGOUT_ON_PASSWORD_CHANGE = False
ACCOUNT_PREVENT_ENUMERATION = True  # FR-107
ACCOUNT_FORMS = {
    "reset_password": "apps.accounts.forms.ResetPasswordForm"
}  # any address on file; no mail to unknown ones
ACCOUNT_RATE_LIMITS = {"login_failed": "5/5m/ip,10/5m/key", "reset_password": "5/5m/ip"}
MFA_SUPPORTED_TYPES = ["totp", "recovery_codes", "webauthn"]
MFA_PASSKEY_LOGIN_ENABLED = True
MFA_TOTP_ISSUER = "ARCOps"

SESSION_COOKIE_AGE = 14 * 24 * 3600  # "remember this device" (TR-17)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# ------------------------------------------------------------- i18n / time ---
LANGUAGE_CODE = "en-us"
# The club's own words for strings a dependency words differently (locale/en/LC_MESSAGES/django.po,
# TR-45): a passkey is a passkey, whatever the sign-in library calls it.
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "UTC"  # storage and logic in UTC (TR-14); display zones come from the event
USE_I18N = True
USE_TZ = True

# ----------------------------------------------------------------- static ---
STATIC_URL = "/static/"
STATIC_ROOT = Path(os.environ.get("STATIC_ROOT", BASE_DIR / "staticfiles"))
_static_dirs: list = []
if CLUB_OVERLAY_DIR and (CLUB_OVERLAY_DIR / "static").is_dir():
    _static_dirs.append(CLUB_OVERLAY_DIR / "static")  # overlay's club/ wins (TR-41)
_static_dirs.append(BASE_DIR / "static")
_static_dirs.append(("club", CLUB_DEFAULTS_DIR / "assets"))  # generic club/ files (TR-40)
STATICFILES_DIRS = _static_dirs
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", VAR_DIR / "media"))
MEDIA_URL = "/media/"

# ------------------------------------------------------------------ email ---
# The outbox (FR-105) decides whether anything is actually sent; this is only the transport.
EMAIL_BACKEND = "apps.comms.backends.GatedSMTPBackend"  # honours defaults.email_delivery
EMAIL_HOST = "localhost"
EMAIL_PORT = 25
EMAIL_USE_TLS = False

# ---------------------------------------------------------------- logging ---
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"line": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "line"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}

# ------------------------------------------------------------ application ---
FIELD_ENCRYPTION_KEY = os.environ.get("FIELD_ENCRYPTION_KEY", "")  # Fernet key, TR-20
VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
VAPID_CLAIMS_EMAIL = os.environ.get(
    "VAPID_CLAIMS_EMAIL", ""
)  # the `sub` claim push services may contact
APP_VERSION = os.environ.get("APP_VERSION", "dev")
# Scheduled-job pings (TR-11, TR-33): the healthchecks.io project ping key, from the env file.
# Empty means no pings (development). Checks are created on first ping (?create=1).
HEALTHCHECKS_PING_KEY = os.environ.get("HEALTHCHECKS_PING_KEY", "")
HEALTHCHECKS_PING_URL = os.environ.get("HEALTHCHECKS_PING_URL", "https://hc-ping.com")
# Absolute origin for links in messages composed outside a request (jobs). ALLOWED_HOSTS' first
# entry in production; the dev server otherwise.
SITE_URL = os.environ.get("SITE_URL", "")
