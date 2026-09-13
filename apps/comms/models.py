"""Messages: templates, the outbox (FR-105), announcements (FR-75)."""

from django.conf import settings
from django.db import models


class MessageTemplate(models.Model):
    key = models.CharField(max_length=60, unique=True)
    subject = models.CharField(max_length=200)
    body_html = models.TextField()
    variables = models.JSONField(default=list, blank=True)  # documented beside the template (FR-78)

    def __str__(self) -> str:
        return self.key


class Outbox(models.Model):
    """Every message the system composes, whether or not email delivery is on (FR-82, FR-105)."""

    class State(models.TextChoices):
        NOT_SENT = "not_sent", "Not sent (email off)"
        QUEUED = "queued", "Queued"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        OUTSIDE = "outside", "Sent outside the system"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="messages"
    )
    to_addresses = models.JSONField(default=list)
    channel = models.CharField(max_length=10, default="email")
    category = models.CharField(
        max_length=40
    )  # reminder | warning | announcement | account | agreement ...
    subject = models.CharField(max_length=200)
    body_html = models.TextField()
    body_text = models.TextField(blank=True)
    state = models.CharField(max_length=10, choices=State.choices, default=State.NOT_SENT)
    error = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created"]
        verbose_name_plural = "outbox"


class Announcement(models.Model):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    event = models.ForeignKey(
        "events.Event",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="announcements",
    )
    audience = models.JSONField(default=dict)
    recipient_count = models.PositiveIntegerField(default=0)
    subject = models.CharField(max_length=200)
    body_html = models.TextField()
    sent_outside = models.BooleanField(default=False)  # FR-106
    created = models.DateTimeField(auto_now_add=True)
