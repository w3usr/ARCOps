"""
One HTML layout for every mail the site sends (the club's own messages and the sign-in
library's), built for the mail clients members use. Outlook's desktop renderer ignores much of
CSS (padding on inline elements, border-radius, max-width on divs), so the frame is tables with
inline styles and cell attributes, and the call-to-action is a table cell with a background,
which every client honours. The club's accent color comes from branding.accent.
"""

from __future__ import annotations

import re
from html import escape

from apps.ops.config import accent_color, setting

FONT = "font-family: Arial, Helvetica, sans-serif;"


def wrap(body_html: str, *, footer_html: str = "") -> str:
    """The frame around a message body: a thin band in the club color with the club's short
    name, the body at a readable measure, and the club's name and contact address beneath."""
    accent = accent_color()
    short = escape(str(setting("club.short_name", "Club")))
    name = escape(str(setting("club.name", short)))
    contact = str(setting("club.contact_email", "") or "")
    contact_html = (
        f' &middot; <a href="mailto:{escape(contact)}" style="color:{accent};">{escape(contact)}</a>'
        if contact
        else ""
    )
    body = _style_links(body_html, accent)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{short}</title></head>
<body style="margin:0;padding:0;background:#f4f4f6;{FONT}">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f4f4f6;">
<tr><td align="center" style="padding:16px 8px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%;background:#ffffff;">
<tr><td bgcolor="{accent}" style="background:{accent};padding:10px 24px;{FONT}font-size:14px;font-weight:bold;color:#ffffff;letter-spacing:.02em;">{short} Operations</td></tr>
<tr><td style="padding:24px 24px 8px 24px;{FONT}font-size:16px;line-height:1.5;color:#1a1a1a;">{body}</td></tr>
<tr><td style="padding:8px 24px 24px 24px;{FONT}font-size:13px;line-height:1.5;color:#555555;border-top:1px solid #e5e5ea;">{name}{contact_html}{footer_html}</td></tr>
</table>
</td></tr>
</table>
</body></html>"""


def button(href: str, label: str) -> str:
    """A call-to-action every mail client draws as a filled block: a table cell with a
    background color and padding, the link inside it. Use it for the one thing the message
    asks the reader to do; ordinary links stay as links."""
    accent = accent_color()
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:16px 0;">'
        f'<tr><td bgcolor="{accent}" style="background:{accent};padding:11px 20px;">'
        # Outlook recolors the anchor with its own link color; the inner span (and the old
        # font tag) carry the white the button needs.
        f'<a href="{escape(href, quote=True)}" style="{FONT}font-size:16px;font-weight:bold;color:#ffffff;text-decoration:none;display:inline-block;">'
        f'<font color="#ffffff"><span style="color:#ffffff;text-decoration:none;">{escape(label)}</span></font></a>'
        "</td></tr></table>"
    )


def _style_links(html: str, accent: str) -> str:
    """Give plain anchors the club color and an underline, inline, since Outlook ignores a
    stylesheet for them; anchors that already carry a style (the button) are left alone."""
    return re.sub(
        r"<a (?![^>]*style=)([^>]*href=)",
        rf'<a style="color:{accent};text-decoration:underline;" \1',
        html,
    )
