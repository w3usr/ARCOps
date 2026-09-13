"""
Rendering authored rich text (FR-115, FR-116).

An agreement, a description, or a know-before-you-go text is written with its own heading
levels, starting at H1. Each is rendered inside a page that already has its title, so the
text's headings are shifted down one level at render time: h1 -> h2, h2 -> h3, h3 -> h4. The
page keeps a single H1 and an unbroken heading order, and authors still think in H1/H2/H3.

The HTML has already been sanitised on save (club_import, and the editor's save path); this
filter re-sanitises anyway, because rendering unsanitised HTML is the one mistake that must be
impossible to make by forgetting a step.
"""

import re

import nh3
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

ALLOWED_TAGS = {
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "p",
    "ol",
    "ul",
    "li",
    "strong",
    "em",
    "a",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "br",
    "blockquote",
    "details",
    "summary",
    "small",
}
ALLOWED_ATTRS = {"a": {"href"}, "th": {"scope"}}

_SHIFT = {"h4": "h5", "h3": "h4", "h2": "h3", "h1": "h2"}  # deepest first so nothing shifts twice


def shift_headings(html: str, levels: int = 1) -> str:
    for _ in range(levels):
        for src, dst in _SHIFT.items():
            html = re.sub(rf"<(/?){src}(\s|>)", rf"<\1{dst}\2", html, flags=re.I)
    return html


@register.filter(name="richtext")
def richtext(value: str) -> str:
    """Sanitise, shift headings one level, mark safe."""
    if not value:
        return ""
    clean = nh3.clean(value, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, link_rel="noopener")
    return mark_safe(shift_headings(clean))  # noqa: S308 - sanitised immediately above
