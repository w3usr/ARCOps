"""The privacy notice, linked from the box that consents to it.

The advisor, 2026-09-19, looking at the invitation page: *"We need to link to the privacy notice
if we are going to ask people to agree to it."* Asking somebody to agree to a document without
giving them the document is not consent, and the link in the page footer does not count: it is
not part of what they are ticking.

So the link lives in the label of the consent box itself, on every path into the club. It opens
in a new tab, because the alternative is that somebody reading it loses the form they had half
filled in.
"""

from __future__ import annotations

from django import forms
from django.urls import reverse
from django.utils.html import escape
from django.utils.safestring import mark_safe


class PrivacyConsentMixin:
    """Put the linked privacy notice into a form's `consent` label.

    Built in `__init__` rather than at import, because reversing a URL needs the URL
    configuration loaded, and a form class is defined before that is true.
    """

    consent_before = "I have read the"
    consent_after = ""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")  # the house style puts no colon after a label
        super().__init__(*args, **kwargs)
        field = self.fields.get("consent")
        if field is None:
            return
        url = reverse("privacy")
        after = f" {escape(self.consent_after)}" if self.consent_after else ""
        field.label = mark_safe(  # noqa: S308 - every part is escaped or a reversed URL
            f"{escape(self.consent_before)} "
            f'<a href="{url}" target="_blank" rel="noopener">privacy notice</a>{after}'
        )
        field.help_text = "It opens in a new tab, so you keep what you have typed here."


def consent_field(**kwargs) -> forms.BooleanField:
    """The box itself. Its label is filled in by the mixin above."""
    kwargs.setdefault("label", "I have read the privacy notice")
    return forms.BooleanField(**kwargs)
