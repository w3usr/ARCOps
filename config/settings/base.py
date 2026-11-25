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
    "django.forms",  # its widget templates, for FORM_RENDERER below
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
    # TinyMCE 7 self-hosted under its GPL-2.0-or-later option (TR-9, technical addendum A26).
    "license_key": "gpl",
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
    "apps.ops.middleware.RequestLogMiddleware",  # outermost, so it times and sees every answer
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    # Outermost of the app's own, so it sees every redirect, the sign-in gate's included.
    "apps.ops.middleware.HtmxRedirectMiddleware",
    "apps.ops.middleware.ViewerZoneMiddleware",  # pages in the viewer's own zone (A38)
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

# Forms render through TEMPLATES, so templates/django/forms/ can restyle a form's own markup:
# an error about the whole form is a Problem message, like any other.
FORM_RENDERER = "django.forms.renderers.TemplatesSetting"

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
                "apps.ops.branding.product_context",
                "apps.accounts.acting.context",
                "apps.comms.context_processors.unread",
                "apps.credentials.context_processors.approvals_waiting",
                "apps.credentials.context_processors.computer_password_entry",
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


def _cache_key(key: str, key_prefix: str, version: int) -> str:
    """allauth's rate-limit keys carry the client's IP address, which is kept only with a
    signature (REQUIREMENTS §4.2); keyed with SECRET_KEY, so a backup alone cannot reverse it."""
    import hashlib
    import hmac

    from django.conf import settings

    raw = f"{key_prefix}:{version}:{key}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), raw, hashlib.sha256).hexdigest()


# One cache in the database every web worker shares, so a sign-in limit counts across all of
# them and survives a restart (FR-99, TR-18). The table is made by a
# migration (ops 0011). Its `add` is atomic under IMMEDIATE transactions, which allauth's lock needs.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "cache",
        "KEY_FUNCTION": _cache_key,
    }
}

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
    {"NAME": "apps.accounts.pwned.PwnedPasswordValidator"},  # TR-15; last, as it asks the network
]
LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "dashboard"
ACCOUNT_LOGOUT_REDIRECT_URL = "account_login"

# allauth (TR-15, TR-16). Invitation-only: signup is closed in the adapter (FR-1).
ACCOUNT_ADAPTER = "apps.accounts.adapter.AccountAdapter"
ACCOUNT_LOGIN_METHODS = {"email"}
# Confirm Access takes a password or a passkey (§2.6). The library also offers a code by mail
# unless told otherwise; a mailed code proves the mailbox, not the person.
ACCOUNT_REAUTHENTICATION_METHODS = ["password", "mfa"]
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
TIME_ZONE = "UTC"  # storage and logic in UTC (TR-14); pages print the viewer's zone (A38)
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
    # One JSON object per line (TR-33): the journal keeps them, and each field can be searched.
    "formatters": {"json": {"()": "config.logjson.JsonFormatter"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "json"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    # Django's own line for a 4xx names the path, and a path can carry a token; the request line
    # above already records the status by route. A 5xx still logs here, with its traceback.
    "loggers": {"django.request": {"level": "ERROR"}},
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
# Nightly backup (TR-22): age-encrypted to a public key whose private half is held offline, so
# the server cannot read its own backups. No recipient means the job fails rather than skip.
BACKUP_DIR = Path(os.environ.get("BACKUP_DIR", VAR_DIR / "backup"))
BACKUP_AGE_RECIPIENT = os.environ.get("BACKUP_AGE_RECIPIENT", "")
BACKUP_NAME = os.environ.get("BACKUP_NAME", "ops_backup")  # the file name after the date
BACKUP_KEEP_DAYS = 7  # the server's share; the puller keeps the long history
# Absolute origin for links in messages composed outside a request (jobs). ALLOWED_HOSTS' first
# entry in production; the dev server otherwise.
SITE_URL = os.environ.get("SITE_URL", "")
