"""Agreement notices (FR-76): submitted to approvers, approved and declined to the signer; and
the invitation-completed and welcome notices (FR-5, FR-76)."""

import pytest
from django.contrib.auth.models import Group
from django.test import Client

from apps.accounts.models import User
from apps.accounts.services import admit_from_invitation, create_invitation
from apps.comms.models import Outbox
from apps.credentials.models import AgreementTemplate, CredentialType, SignedAgreement
from apps.credentials.services import approve
from apps.ops.models import ClubSetting

pytestmark = pytest.mark.django_db


def _user(email, level, position="", **kw):
    u = User.objects.create_user(email, "pw-Testing-123", **kw)
    if level == "sysadmin":  # a sysadmin is a superuser, not a member of a group
        u.is_superuser = True
    else:
        u.groups.set(Group.objects.filter(name=level))
    u.club_position = position
    u.category = kw.get("category", "student")
    u.save()
    return u


def test_agreement_lifecycle_notices():
    ClubSetting.objects.update_or_create(
        key="club_positions",
        defaults={"value": [{"key": "advisor", "label": "Advisor"}]},
    )
    ClubSetting.objects.update_or_create(
        key="member_categories", defaults={"value": [{"key": "student", "label": "Student"}]}
    )
    advisor = _user("adv@example.org", "advisor", "advisor", first_name="Ad", last_name="Visor")
    mem = _user("mem@example.org", "member", first_name="Mo", last_name="Member")
    ct = CredentialType.objects.create(
        key="station_access", label="Station", established_by="agreement"
    )
    t = AgreementTemplate.objects.create(
        key="sa",
        credential=ct,
        title="Station Agreement",
        audience=["student"],
        version=1,
        content_hash="h",
        html="<p>x</p>",
        effective_date="2026-01-01",
        is_current=True,
    )
    c = Client()
    c.force_login(mem)
    c.post(f"/credentials/agreements/{t.pk}/sign/", {"affirm": "on", "signer_name": "Mo Member"})
    a = SignedAgreement.objects.get(user=mem)
    m = Outbox.objects.get(user=advisor, category="agreement")
    assert "Agreement to review" in m.subject and "Mo Member" in m.subject
    approve(advisor, a)
    m = Outbox.objects.filter(user=mem, category="agreement").latest("created")
    assert m.subject == "Approved: Station Agreement" and "Ad Visor" in m.body_html
    a2 = SignedAgreement.objects.create(
        user=mem, template=t, credential=ct, signer_name="Mo Member", content_hash="h"
    )
    c.force_login(advisor)
    c.post(
        f"/credentials/approvals/{a2.pk}/decide/", {"decision": "decline", "reason": "wrong name"}
    )
    m = Outbox.objects.filter(user=mem, category="agreement").latest("created")
    assert m.subject == "Not approved: Station Agreement" and "wrong name" in m.body_html


def test_invitation_completion_tells_inviter_and_officers_and_welcomes_the_member():
    off = _user("off@example.org", "officer", first_name="Ann", last_name="Officer")
    other = _user("o2@example.org", "officer", first_name="Bo", last_name="Officer")
    inv = create_invitation(off, "new@example.org", "student", base_url="https://ops.example")
    user = admit_from_invitation(
        inv, "pw-Testing-123", first_name="New", last_name="Person", callsign="N0NEW"
    )
    for o in (off, other):
        m = Outbox.objects.get(user=o, category="account", subject__contains="joined")
        assert (
            "New Person" in m.subject
            and "N0NEW" in m.body_html
            and "new@example.org" in m.body_html
        )
    w = Outbox.objects.get(user=user, category="account")
    assert w.subject.startswith("Welcome to")
