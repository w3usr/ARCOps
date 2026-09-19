"""Every path into the club links the notice it asks people to agree to.

The advisor, 2026-09-19, on the invitation page: "We need to link to the privacy notice if we are
going to ask people to agree to it." The footer link does not count: it is not part of what the
person is ticking.
"""

from datetime import timedelta

import pytest
from django.core.management import call_command
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import EntryLink, Invitation, User

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def club():
    call_command("club_import")


def _consent_is_linked(body: str) -> bool:
    """The privacy link sits inside the consent box's own label, not merely on the page."""
    url = reverse("privacy")
    start = body.find("I have read the")
    if start == -1:
        return False
    label = body[start : start + 400]
    return f'href="{url}"' in label and "privacy notice</a>" in label


def test_the_invitation_page_links_the_notice_it_asks_agreement_to():
    officer = User.objects.create_user(
        "off@example.org", "pw-Testing-123", groups=["officer"], first_name="A", last_name="B"
    )
    inv = Invitation.objects.create(
        email="new@example.org",
        category="student",
        issued_by=officer,
        expires_at=timezone.now() + timedelta(days=14),
    )
    body = Client().get(f"/me/invite/{inv.token}/", follow=True).content.decode()
    assert _consent_is_linked(body), "the consent box does not carry the privacy link"
    assert 'target="_blank"' in body  # a half-filled form is not lost to reading it


def test_the_guardian_page_links_it_too():
    officer = User.objects.create_user(
        "off2@example.org", "pw-Testing-123", groups=["officer"], first_name="A", last_name="B"
    )
    inv = Invitation.objects.create(
        email="kid@example.org",
        category="student",
        issued_by=officer,
        is_minor=True,
        guardian_email="parent@example.org",
        expires_at=timezone.now() + timedelta(days=14),
    )
    body = Client().get(f"/me/invite/{inv.token}/", follow=True).content.decode()
    assert _consent_is_linked(body)
    assert "consent on the member" in body and "behalf" in body


def test_the_entry_link_page_links_it_too():
    officer = User.objects.create_user(
        "off3@example.org", "pw-Testing-123", groups=["officer"], first_name="A", last_name="B"
    )
    link = EntryLink.objects.create(
        label="Physics 101",
        kind=EntryLink.Kind.CLASS,
        created_by=officer,
        expires_at=timezone.now() + timedelta(days=7),
    )
    body = Client().get(f"/join/{link.token}/", follow=True).content.decode()
    assert _consent_is_linked(body)
