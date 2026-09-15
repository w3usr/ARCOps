"""FR-37: the fields the WA7BNM Contest Calendar publishes for each contest, verified against the
site on 2026-09-12. Free text except the reference number and the URLs. Entered by hand on the
Manage page until the calendar import (FR-40) is authorised; they inform the know-before-you-go
text and are otherwise for people to read."""

CONTEST_FIELDS: list[tuple[str, str, str]] = [
    # key, label, kind (text | url | email | int)
    ("status", "Status", "text"),
    ("geographic_focus", "Geographic focus", "text"),
    ("participation", "Participation", "text"),
    ("awards", "Awards", "text"),
    ("mode", "Mode", "text"),
    ("bands", "Bands", "text"),
    ("classes", "Classes", "text"),
    ("max_power", "Max power", "text"),
    ("exchange", "Exchange", "text"),
    ("work_stations", "Work stations", "text"),
    ("qso_points", "QSO points", "text"),
    ("multipliers", "Multipliers", "text"),
    ("score_calculation", "Score calculation", "text"),
    ("log_email", "Log submission: e-mail", "email"),
    ("log_upload_url", "Log submission: upload URL", "url"),
    ("log_postal", "Log submission: postal address", "text"),
    ("log_deadline", "Log deadline", "text"),
    ("cabrillo_name", "Cabrillo name", "text"),
    ("cabrillo_aliases", "Cabrillo aliases", "text"),
]

KEYS = [k for k, _, _ in CONTEST_FIELDS]
LABELS = {k: label for k, label, _ in CONTEST_FIELDS}


def present(fields: dict) -> list[tuple[str, str, str]]:
    """(label, value, kind) for the fields with a value, in the calendar's order."""
    return [
        (LABELS[k], str(fields.get(k, "")).strip(), kind)
        for k, _, kind in CONTEST_FIELDS
        if str(fields.get(k, "")).strip()
    ]
