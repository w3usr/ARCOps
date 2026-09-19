"""
The product's own name and provenance (docs/NAME.md).

This is the one place in the code that names W3USR, and it is deliberate: it is the software's
attribution, shown in the footer of every installation ("Powered by ARCOps, free software from
W3USR"), the way any free-software project credits its authors. Everything that describes the
*club running an installation* comes from club.yaml or the overlay (TR-40, TR-41) and never
from here. tools/check_club_neutral.sh excludes this file for that reason.
"""

PRODUCT_NAME = "ARCOps"
PRODUCT_LONG_NAME = "Amateur Radio Club Operations"  # spelled out where the name is first met
PRODUCT_TAGLINE = "operations software for amateur radio clubs"
PRODUCT_URL = "https://github.com/w3usr/ARCOps"
PRODUCT_CREDIT = "free software from W3USR"
SCHEDULE_FEATURE_NAME = "Sked"  # the schedule and roster inside the application


def product_context() -> dict:
    return {
        "product": {
            "name": PRODUCT_NAME,
            "long_name": PRODUCT_LONG_NAME,
            "tagline": PRODUCT_TAGLINE,
            "url": PRODUCT_URL,
            "credit": PRODUCT_CREDIT,
            "sked": SCHEDULE_FEATURE_NAME,
        }
    }
