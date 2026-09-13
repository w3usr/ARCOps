"""
Navigation helpers for the application shell (templates/base.html).

`nav_active` marks the sidebar entry for the page being viewed, so the current place is
announced to assistive technology (aria-current) and highlighted for everyone else.
`icon` renders one of a small set of inline line icons: keeping them in the template tag
means no icon font, no external request, and a single place to keep them consistent (TR-5).
"""

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# 24x24 line icons, stroke 1.75, drawn to read at 20 px. Decorative: the label beside them
# carries the meaning, so they are aria-hidden.
_ICONS = {
    "home": '<path d="M3 11.5 12 4l9 7.5"/><path d="M5.5 10.5V20h13v-9.5"/><path d="M10 20v-5h4v5"/>',
    "calendar": '<rect x="3.5" y="5" width="17" height="15.5" rx="2"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
    "clock": '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    "signature": '<path d="M4 17.5c2.5-3 4-8 3-10.5s-3 1-2 5 4 7 6 5 1.5-6 .5-6-2 4 0 6 3.5-1 4.5-2"/><path d="M4 20.5h16"/>',
    "user": '<circle cx="12" cy="8.5" r="3.75"/><path d="M4.5 20a7.5 7.5 0 0 1 15 0"/>',
    "user-plus": '<circle cx="10" cy="8.5" r="3.75"/><path d="M2.5 20a7.5 7.5 0 0 1 15 0"/><path d="M19 8v6M16 11h6"/>',
    "check-circle": '<circle cx="12" cy="12" r="8.5"/><path d="m8.5 12.5 2.5 2.5 4.5-5.5"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M12 3v2.5M12 18.5V21M3 12h2.5M18.5 12H21M5.6 5.6l1.8 1.8M16.6 16.6l1.8 1.8M5.6 18.4l1.8-1.8M16.6 7.4l1.8-1.8"/>',
    "log-out": '<path d="M10 4H5.5A1.5 1.5 0 0 0 4 5.5v13A1.5 1.5 0 0 0 5.5 20H10"/><path d="M15 16.5 19.5 12 15 7.5M19.5 12H9"/>',
    "log-in": '<path d="M14 4h4.5A1.5 1.5 0 0 1 20 5.5v13a1.5 1.5 0 0 1-1.5 1.5H14"/><path d="m9 16.5 4.5-4.5L9 7.5M13.5 12H4"/>',
    "menu": '<path d="M4 7h16M4 12h16M4 17h16"/>',
    "close": '<path d="M6 6l12 12M18 6 6 18"/>',
    "chevrons-left": '<path d="m11 7-5 5 5 5M18 7l-5 5 5 5"/>',
    "chevrons-right": '<path d="m6 7 5 5-5 5M13 7l5 5-5 5"/>',
}


@register.simple_tag
def icon(name: str) -> str:
    body = _ICONS.get(name, "")
    # The markup is assembled from the constants above only; nothing from the request enters it.
    return mark_safe(  # noqa: S308
        '<svg class="icon" aria-hidden="true" focusable="false" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" '
        f'stroke-linejoin="round">{body}</svg>'
    )


@register.simple_tag(takes_context=True)
def nav_active(context, *url_names: str) -> str:
    """` aria-current="page"` when the resolved URL name is one of those given."""
    request = context.get("request")
    match = getattr(request, "resolver_match", None)
    if match and match.url_name in url_names:
        return mark_safe(' aria-current="page"')
    return ""
