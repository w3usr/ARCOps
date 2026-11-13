"""An empty slot is canceled only after the dialog's confirmation (#257); adding a period, a
location or a position, and closing or reopening one slot, are in the audit log (#259)."""

import pytest

from apps.events.models import Slot
from apps.ops.models import AuditLog

from .test_manage import _as, _build

pytestmark = pytest.mark.django_db


def test_an_empty_slot_is_canceled_only_once_confirmed(officer):
    c = _as(officer)
    ev = _build(c)
    s = Slot.objects.filter(position__location__event=ev, kind="operating").first()
    page = c.get(f"/events/{ev.pk}/slot/{s.pk}/").content.decode()
    assert "Cancel this slot?" in page and "Nobody is in it, so nobody is told." in page
    assert 'name="reason"' not in page
    c.post(f"/events/slot/{s.pk}/toggle/", {"what": "cancel"})
    s.refresh_from_db()
    assert not s.cancelled
    c.post(f"/events/slot/{s.pk}/toggle/", {"what": "cancel", "confirmed": "yes"})
    s.refresh_from_db()
    assert s.cancelled


def test_adding_and_closing_are_in_the_audit_log(officer):
    c = _as(officer)
    ev = _build(c)
    after = [a.after for a in AuditLog.objects.filter(action="event.edited")]
    assert {"period": "2026-06-27 18:00–2026-06-28 18:00 UTC"} in after
    assert {"location": "Club station", "position": "Run"} in after
    assert {"position": "Mult"} in after
    s = Slot.objects.filter(position__location__event=ev, kind="operating").first()
    c.post(f"/events/slot/{s.pk}/toggle/", {"what": "close"})
    c.post(f"/events/slot/{s.pk}/toggle/", {"what": "close"})
    assert list(
        AuditLog.objects.filter(action__in=["slot.close", "slot.reopen"])
        .order_by("pk")
        .values_list("action", flat=True)
    ) == ["slot.close", "slot.reopen"]
