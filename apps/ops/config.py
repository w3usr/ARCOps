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


def _read(directory: Path) -> dict[str, Any] | None:
    for name in ("club.yaml", "club.example.yaml"):
        path = directory / name
        if path.exists():
            with path.open(encoding="utf-8") as fh:
                return yaml.safe_load(fh) or {}
    return None


def _under(defaults: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """The overlay's answers, with the shipped ones filling the gaps.

    Dictionaries are merged key by key; a list or a value the overlay states is taken whole,
    because a club that lists its own categories, groups or agreements means *those* and not
    those plus ours.
    """
    merged = dict(defaults)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _under(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_yaml(directory: Path | None = None) -> dict[str, Any]:
    """The club's configuration: an overlay laid over the shipped defaults (TR-41).

    It is an overlay rather than a replacement, so a setting added to the application reaches an
    installation that has its own club.yaml. Without this, `security.two_factor_required_groups`
    was invisible on the club's own server on the day it was added (2026-09-20).
    """
    directory = directory or config_dir()
    overlay = _read(directory)
    if overlay is None:
        raise FileNotFoundError(f"no club.yaml or club.example.yaml in {directory}")
    defaults = _read(dj.CLUB_DEFAULTS_DIR) if directory != dj.CLUB_DEFAULTS_DIR else None
    return _under(defaults, overlay) if defaults else overlay


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


def _relative_luminance(hex_color: str) -> float:
    def channel(v: int) -> float:
        c = v / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast_with_white(hex_color: str) -> float:
    """WCAG contrast ratio of white text on the color."""
    return 1.05 / (_relative_luminance(hex_color) + 0.05)


def accent_color() -> str:
    """The club's accent (branding.accent) if it is a six-digit hex color that carries white
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


BRANDING_IMAGES = (
    "logo",
    "logo_monochrome",
    "favicon",
    "apple_touch_icon",
    "maskable_icon",
    "qsl_card",
)


def branding_url(value: str | None) -> str | None:
    """A branding setting is either a path in the club's static overlay (served hashed through
    the static storage) or, when uploaded from Settings, a file under MEDIA_ROOT/branding/
    served by `ops.views.branding_file`. Either way the templates get a URL."""
    if not value:
        return None
    if value.startswith("media/branding/"):
        from django.urls import reverse

        name = value[len("media/branding/") :]
        path = dj.MEDIA_ROOT / "branding" / name
        stamp = int(path.stat().st_mtime) if path.exists() else 0
        return reverse("branding_file", args=[name]) + f"?v={stamp}"
    from django.templatetags.static import static

    try:
        return static(normalise_static_path(value))
    except ValueError:  # not in the collected manifest: a wrong path in the configuration
        return None


def branding() -> dict[str, str | None]:
    out = {key: branding_url(setting(f"branding.{key}")) for key in BRANDING_IMAGES}
    out["accent"] = accent_color()
    return out


def institution_email_domain() -> str:
    """The email domain of the first member category that declares one (the university's, in
    practice), used to label the institution-address field in the member's own terms."""
    for c in setting("member_categories", []) or []:
        if isinstance(c, dict) and c.get("email_domain"):
            return str(c["email_domain"])
    return ""
