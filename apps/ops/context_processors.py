"""Makes the club's identity (`club`, TR-40) and the product's (`product`, NAME.md) available
to every template."""

from .branding import product_context
from .config import branding, setting


def product(request):
    return product_context()


def club(request):
    return {
        "email_delivery_on": str(setting("defaults.email_delivery", "off")).lower() == "on",
        "club": {
            "name": setting("club.name", "Amateur Radio Club"),
            "short_name": setting("club.short_name", "Club"),
            "callsign": setting("club.callsign", ""),
            "contact_email": setting("club.contact_email", ""),
            "public_page": setting("club.public_page", ""),
            "timezone": setting("club.timezone", "UTC"),
            "branding": branding(),
        },
    }
