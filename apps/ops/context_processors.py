"""Makes the club's identity available to every template as `club` (TR-40)."""

from .config import branding, setting


def club(request):
    return {
        "club": {
            "name": setting("club.name", "Amateur Radio Club"),
            "short_name": setting("club.short_name", "Club"),
            "callsign": setting("club.callsign", ""),
            "contact_email": setting("club.contact_email", ""),
            "public_page": setting("club.public_page", ""),
            "timezone": setting("club.timezone", "UTC"),
            "branding": branding(),
        }
    }
