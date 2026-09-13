"""
Reading club configuration (TR-32, TR-40, TR-41).

Two layers: the files (an overlay directory if configured, else the shipped defaults in
config/) and the database (ClubSetting rows, which `club_import` seeds from the files and
sysadmins edit afterwards). Code asks `setting("club.name")` and never cares which.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from django.conf import settings as dj


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


def branding() -> dict[str, str | None]:
    return {
        "logo": normalise_static_path(setting("branding.logo")),
        "logo_monochrome": normalise_static_path(setting("branding.logo_monochrome")),
        "favicon": normalise_static_path(setting("branding.favicon")),
        "apple_touch_icon": normalise_static_path(setting("branding.apple_touch_icon")),
        "qsl_card": normalise_static_path(setting("branding.qsl_card")),
    }
