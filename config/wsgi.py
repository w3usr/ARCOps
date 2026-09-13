"""WSGI entry point; gunicorn loads `config.wsgi:application` (TR-3)."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
application = get_wsgi_application()
