"""Turn a stored key into the words the club chose for it.

Roles, slot kinds, member categories, club positions, and credentials are all stored as short
keys and configured with a label beside them. A page that renders the key shows the reader the
inside of the program: "operator" where the club wrote "Operator", "not_found" where it means
"no FCC record". These filters are the one place that translation happens.
"""

from __future__ import annotations

from datetime import timedelta

from django import template

from apps.ops.config import setting

register = template.Library()


def _label(kind: str, key) -> str:
    """The configured label for a key, or a readable fallback when the club has removed it."""
    if not key:
        return ""
    key = str(key)
    for row in setting(kind, []) or []:
        if str(row.get("key")) == key:
            return str(row.get("label") or key)
    return key.replace("_", " ").capitalize()


@register.filter
def role_label(key) -> str:
    return _label("slot_roles", key)


@register.filter
def kind_label(key) -> str:
    """A slot's kind. "operating" is the ordinary case and is configured nowhere."""
    if str(key) == "operating":
        return "Operating"
    return _label("non_operating_slot_kinds", key)


@register.filter
def category_label(key) -> str:
    return _label("member_categories", key)


@register.filter
def position_labels(keys) -> str:
    """Every office a member holds, in the club's configured order rather than tick order."""
    held = set(keys or [])
    labels = [p["label"] for p in (setting("club_positions", []) or []) if p.get("key") in held]
    return ", ".join(labels)


@register.filter
def credential_label(key) -> str:
    return _label("credential_types", key)


@register.filter
def role_labels(keys) -> str:
    """A list of role keys, as a sentence: "Operator, Mentor, and Observer"."""
    words = [role_label(k) for k in keys or []]
    if len(words) < 2:
        return words[0] if words else ""
    if len(words) == 2:
        return f"{words[0]} and {words[1]}"
    return ", ".join(words[:-1]) + ", and " + words[-1]


@register.filter
def message_category(key) -> str:
    """The short name for a message's category, for the outbox column."""
    from apps.comms.categories import name

    return name(key)


@register.filter
def phone(value) -> str:
    """A phone number written the way its own country writes it.

    Google's libphonenumber, through `phonenumbers`, rather than a regular expression of our
    own: the club is at a US university but its community members are not all in it, and a
    home-made formatter would put brackets round a London number. What the member typed is
    stored untouched; this is only how it is shown.

    A number the library cannot make sense of is shown exactly as typed. Guessing at it would
    be worse than leaving it alone, because somebody has to dial it.
    """
    import phonenumbers

    raw = str(value or "").strip()
    if not raw:
        return ""
    region = str(setting("club.phone_region", "US") or "US").upper()
    try:
        parsed = phonenumbers.parse(raw, region)
    except phonenumbers.NumberParseException:
        return raw
    if not phonenumbers.is_valid_number(parsed):
        return raw
    at_home = phonenumbers.region_code_for_number(parsed) == region
    style = (
        phonenumbers.PhoneNumberFormat.NATIONAL
        if at_home
        else phonenumbers.PhoneNumberFormat.INTERNATIONAL
    )
    return phonenumbers.format_number(parsed, style)


@register.filter
def duration(value) -> str:
    """A timedelta in words. The job page showed "0:15:00", which is a Python repr."""
    if not isinstance(value, timedelta):
        return value or ""
    seconds = int(value.total_seconds())
    if seconds <= 0:
        return "never"
    for size, singular in ((86400, "day"), (3600, "hour"), (60, "minute")):
        if seconds % size == 0:
            n = seconds // size
            return f"{n} {singular}{'' if n == 1 else 's'}"
    if seconds < 60:
        return f"{seconds} second{'' if seconds == 1 else 's'}"
    minutes = seconds // 60
    return f"{minutes} minute{'' if minutes == 1 else 's'}"
