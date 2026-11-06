"""Which tone a state's badge takes (#226), in one place: `{{ event.state|tone:"event" }}` gives the
class to put beside `tag`. The word is always the state's own label; the tone only repeats it.
A slot's tone is the roster's (`services/roster.py`, `Presentation.tone`), which this does not
duplicate."""

from django import template

register = template.Library()

TONES = {
    "event": {
        "draft": "",
        "published": "ok",
        "locked": "info",
        "completed": "",
        "cancelled": "bad",
    },
    "member": {
        "provisional": "warn",
        "active": "ok",
        "closed": "",
        "suspended": "bad",
        "deleted": "",
        "under_18": "info",
    },
    "agreement": {
        "signed": "info",
        "approved": "ok",
        "declined": "warn",
        "expired": "warn",
        "revoked": "bad",
    },
}


@register.filter
def tone(state, kind: str) -> str:
    """The badge class for `state` of `kind`; neutral (no class) for anything not listed."""
    return TONES.get(kind, {}).get(str(state), "")
