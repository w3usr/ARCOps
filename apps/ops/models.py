"""Club configuration, the audit log, and job runs (TR-21, TR-26, TR-32)."""

from django.conf import settings
from django.db import models


class ClubSetting(models.Model):
    """One configuration value. Keys are dotted paths into club.yaml ("club.name",
    "defaults.slot_length_minutes"). Seeded by `club_import`; edited in the interface (FR-89)."""

    key = models.CharField(max_length=120, unique=True)
    value = models.JSONField(null=True, blank=True)  # JSON null is a legitimate value
    source = models.CharField(max_length=20, default="import")  # import | interface
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]

    def __str__(self) -> str:
        return self.key


class AuditLog(models.Model):
    """Append-only (FR-92). SQLite triggers created in a migration raise on UPDATE and DELETE."""

    at = models.DateTimeField(auto_now_add=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    actor_label = models.CharField(max_length=200, blank=True)  # survives actor deletion
    action = models.CharField(max_length=80)
    subject_type = models.CharField(max_length=80, blank=True)
    subject_id = models.CharField(max_length=40, blank=True)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["-at"]

    def __str__(self) -> str:
        return f"{self.at:%Y-%m-%d %H:%M} {self.action} {self.subject_type}:{self.subject_id}"


class JobRun(models.Model):
    """One run of a scheduled job (TR-11); the status page (FR-93) reads these."""

    name = models.CharField(max_length=60)
    started = models.DateTimeField(auto_now_add=True)
    finished = models.DateTimeField(null=True, blank=True)
    outcome = models.CharField(max_length=20, default="running")  # running | ok | failed
    detail = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-started"]

    def __str__(self) -> str:
        return f"{self.name} {self.started:%Y-%m-%d %H:%M} {self.outcome}"
