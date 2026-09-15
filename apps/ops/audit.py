"""The one function every privileged action calls to write the audit log (FR-92, TR-21)."""

from __future__ import annotations

from typing import Any

from .models import AuditLog


def record(actor, action: str, subject=None, before: Any = None, after: Any = None) -> AuditLog:
    guardian = getattr(actor, "acting_guardian", None)  # §2.4: a guardian acting for a minor
    label = f"{guardian} acting for {actor}" if guardian else (str(actor) if actor else "system")
    if guardian:
        actor = guardian
    return AuditLog.objects.create(
        actor=actor if getattr(actor, "pk", None) else None,
        actor_label=label,
        action=action,
        subject_type=subject.__class__.__name__ if subject is not None else "",
        subject_id=str(getattr(subject, "pk", "")) if subject is not None else "",
        before=before,
        after=after,
    )
