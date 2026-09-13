"""The one function every privileged action calls to write the audit log (FR-92, TR-21)."""

from __future__ import annotations

from typing import Any

from .models import AuditLog


def record(actor, action: str, subject=None, before: Any = None, after: Any = None) -> AuditLog:
    return AuditLog.objects.create(
        actor=actor if getattr(actor, "pk", None) else None,
        actor_label=str(actor) if actor else "system",
        action=action,
        subject_type=subject.__class__.__name__ if subject is not None else "",
        subject_id=str(getattr(subject, "pk", "")) if subject is not None else "",
        before=before,
        after=after,
    )
