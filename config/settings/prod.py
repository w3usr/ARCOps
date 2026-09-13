"""
Production settings. Everything variable comes from the environment file the deploy writes
(TR-19); the application refuses to start without a SECRET_KEY.
"""

import os

from .base import *  # noqa: F403

DEBUG = False
if not SECRET_KEY:  # noqa: F405
    raise RuntimeError("SECRET_KEY is not set; the deploy's env file is missing (TR-19)")

ALLOWED_HOSTS = [h for h in os.environ.get("ALLOWED_HOSTS", "").split(",") if h]
CSRF_TRUSTED_ORIGINS = [f"https://{h}" for h in ALLOWED_HOSTS]

# Behind nginx, behind Cloudflare: TLS terminates in front of us.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"
# HSTS and the HTTP-to-HTTPS redirect are nginx's job (deploy/nginx/ in the private repository),
# so Django's two checks for them are silenced deliberately rather than duplicated here.
SILENCED_SYSTEM_CHECKS = ["security.W004", "security.W008"]
