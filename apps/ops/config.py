"""
Reading club configuration (TR-32, TR-40, TR-41).

Two layers: the files (an overlay directory if configured, else the shipped defaults in
config/) and the database (ClubSetting rows, which `club_import` seeds from the files and
sysadmins edit afterwards). Code asks `setting("club.name")` and never cares which.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import yaml
from django.conf import settings as dj

log = logging.getLogger(__name__)


def config_dir() -> Path:
    """The directory whose club.yaml applies: the overlay if set, else the defaults."""
    if dj.CLUB_OVERLAY_DIR and (dj.CLUB_OVERLAY_DIR / "club.yaml").exists():
        return dj.CLUB_OVERLAY_DIR
    return dj.CLUB_DEFAULTS_DIR


def load_yaml(directory: Path | None = None) -> dict[str, Any]:
    directory = directory or config_dir()
    for name in ("club.yaml", "club.example.yaml"):
        path = directory / name
        if path.exists():
            with path.open(encoding="utf-8") as fh:
                return yaml.safe_load(fh) or {}
    raise FileNotFoundError(f"no club.yaml or club.example.yaml in {directory}")


def flatten(data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """{"club": {"name": x}} -> {"club.name": x}. Lists stay whole under their key."""
    out: dict[str, Any] = {}
    for key, value in data.items():
        dotted = f"{prefix}{key}"
        if isinstance(value, dict):
            out.update(flatten(value, dotted + "."))
        else:
            out[dotted] = value
    return out


def normalise_static_path(value: str | None) -> str | None:
    """Branding paths in club.yaml are written relative to the config directory
    ("static/club/logo.png" in an overlay, "assets/club-logo.svg" in the defaults); the
    application serves both under the static prefix "club/"."""
    if not value:
        return None
    if value.startswith("static/"):
        return value[len("static/") :]
    if value.startswith("assets/"):
        return "club/" + value[len("assets/") :]
    return value


def setting(key: str, default: Any = None) -> Any:
    """A configuration value from the database, falling back to the files, then `default`."""
    from .models import ClubSetting

    try:
        return ClubSetting.objects.get(key=key).value
    except ClubSetting.DoesNotExist:
        pass
    except Exception:  # noqa: BLE001 - before migrations, during checks
        return default
    try:
        return flatten(load_yaml()).get(key, default)
    except FileNotFoundError:
        return default


def set_setting(actor, key: str, value: Any):
    """Change one value from the interface, audited (FR-89, FR-105). The row is marked as an
    interface edit so `club_import` keeps it unless run with --reset."""
    from .audit import record
    from .models import ClubSetting

    row, _ = ClubSetting.objects.get_or_create(key=key)
    before = row.value
    row.value, row.source = value, "interface"
    row.save(update_fields=["value", "source", "updated"])
    record(actor, "setting.changed", row, before={"value": before}, after={"value": value})
    return row


DEFAULT_ACCENT = "#1f3a5f"
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def _relative_luminance(hex_colour: str) -> float:
    def channel(v: int) -> float:
        c = v / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (int(hex_colour[i : i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast_with_white(hex_colour: str) -> float:
    """WCAG contrast ratio of white text on the colour."""
    return 1.05 / (_relative_luminance(hex_colour) + 0.05)


def accent_colour() -> str:
    """The club's accent (branding.accent) if it is a six-digit hex colour that carries white
    text at AA (4.5:1, FR-116); otherwise the application's default. The accent is used as a
    background for the footer, buttons, and the sign-in panel, and as link text on white, so
    the same threshold covers both uses."""
    value = setting("branding.accent")
    if not value or not _HEX.match(str(value)):
        return DEFAULT_ACCENT
    value = str(value).lower()
    if contrast_with_white(value) < 4.5:
        log.warning("branding.accent %s fails AA contrast with white; using the default", value)
        return DEFAULT_ACCENT
    return value


def branding() -> dict[str, str | None]:
    return {
        "logo": normalise_static_path(setting("branding.logo")),
        "logo_monochrome": normalise_static_path(setting("branding.logo_monochrome")),
        "favicon": normalise_static_path(setting("branding.favicon")),
        "apple_touch_icon": normalise_static_path(setting("branding.apple_touch_icon")),
        "qsl_card": normalise_static_path(setting("branding.qsl_card")),
        "accent": accent_colour(),
    }


def institution_email_domain() -> str:
    """The email domain of the first member category that declares one (the university's, in
    practice), used to label the institution-address field in the member's own terms."""
    for c in setting("member_categories", []) or []:
        if isinstance(c, dict) and c.get("email_domain"):
            return str(c["email_domain"])
    return ""
