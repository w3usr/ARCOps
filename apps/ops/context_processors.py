"""Makes the club's identity (`club`, TR-40) available to every template."""

from django.conf import settings as dj

from .config import branding, institution_email_domain, setting


def club(request):
    return {
        "email_delivery_on": str(setting("defaults.email_delivery", "off")).lower() == "on",
        "vapid_public_key": getattr(dj, "VAPID_PUBLIC_KEY", ""),
        "club": {
            "name": setting("club.name", "Amateur Radio Club"),
            "short_name": setting("club.short_name", "Club"),
            "callsign": setting("club.callsign", ""),
            "contact_email": setting("club.contact_email", ""),
            "public_page": setting("club.public_page", ""),
            "timezone": setting("club.timezone", "UTC"),
            "institution_email_domain": institution_email_domain(),
            "branding": branding(),
        },
    }
