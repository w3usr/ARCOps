"""TR-21: the audit log is append-only in the database, whatever code or shell reaches it.

The model said so from the start, but no migration made the triggers, so an UPDATE or DELETE
went through until T22 tried one (2026-10-21).
"""

import pytest
from django.db import IntegrityError, transaction

from apps.accounts.models import User
from apps.ops.audit import record
from apps.ops.models import AuditLog

pytestmark = pytest.mark.django_db


def _row():
    actor = User.objects.create_user("a@example.org", "pw-Testing-123", first_name="Ada")
    return actor, record(actor, "member.edited", actor, before={"x": 1}, after={"x": 2})


@pytest.mark.parametrize(
    "change",
    [{"action": "tampered"}, {"after": {"x": 3}}, {"actor_label": "someone else"}, {"at": None}],
)
def test_no_entry_can_be_changed(change):
    _, row = _row()
    with pytest.raises(IntegrityError, match="append-only"), transaction.atomic():
        AuditLog.objects.filter(pk=row.pk).update(**change)
    assert AuditLog.objects.get(pk=row.pk).action == "member.edited"


def test_no_entry_can_be_deleted():
    _, row = _row()
    with pytest.raises(IntegrityError, match="append-only"), transaction.atomic():
        AuditLog.objects.filter(pk=row.pk).delete()
    assert AuditLog.objects.filter(pk=row.pk).exists()


def test_an_entry_cannot_be_moved_to_another_actor():
    _, row = _row()
    other = User.objects.create_user("b@example.org", "pw-Testing-123", first_name="Ben")
    with pytest.raises(IntegrityError, match="append-only"), transaction.atomic():
        AuditLog.objects.filter(pk=row.pk).update(actor=other)


def test_deleting_an_account_outright_still_works_and_keeps_its_entries():
    """The one change allowed: the Django admin's delete clears the actor (on_delete=SET_NULL),
    and the label still says who it was."""
    actor, row = _row()
    actor.delete()
    row = AuditLog.objects.get(pk=row.pk)
    assert row.actor_id is None and row.actor_label == str(actor)
