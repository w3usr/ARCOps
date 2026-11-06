"""Every icon a template names is drawn (#224): `{% icon %}` falls back to an empty square, which
no test of a page would notice."""

import re
from pathlib import Path

from apps.ops.templatetags.nav import _ICONS, icon

TEMPLATES = Path(__file__).resolve().parents[3] / "templates"


def test_every_icon_a_template_names_exists():
    named = {
        m
        for path in TEMPLATES.rglob("*.html")
        for m in re.findall(r"""\{%\s*icon\s+['"]([a-z-]+)['"]""", path.read_text())
    }
    assert named and not named - set(_ICONS), sorted(named - set(_ICONS))


def test_the_small_size_and_the_default():
    assert 'class="icon small"' in icon("plus", "small")
    assert 'class="icon"' in icon("plus") and 'aria-hidden="true"' in icon("plus")
