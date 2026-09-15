"""People: members, guardians, invitations (REQUIREMENTS §2, FR-1 to FR-13, FR-102, FR-109)."""

from __future__ import annotations

import secrets

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class AccessLevel(models.TextChoices):
    SYSADMIN = "sysadmin", "Sysadmin"
    OFFICER = "officer", "Club officer"
    MEMBER = "member", "Member"
    PROVISIONAL = "provisional", "Provisional"  # joined through a community link, awaiting review (FR-121)
    NONE = "none", "No access"


LICENSE_LETTERS = {  # FR-67: the class after a name; U when there is no license
    "novice": "N",
    "technician": "T",
    "technician plus": "T",
    "general": "G",
    "advanced": "A",
    "extra": "E",
    "amateur extra": "E",
}


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email: str, password: str | None = None, **extra):
        if not email:
            raise ValueError("an email address is required")
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str | None = None, **extra):
        extra.setdefault("access_level", AccessLevel.SYSADMIN)
        extra.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    """A person with an account. The login identifier is the email address (§2.6)."""

    email = models.EmailField(unique=True)
    # Two contact addresses of equal standing, each with its own delivery switch (FR-70). When
    # neither is switched on, club mail falls back to the sign-in address so no member is
    # unreachable. NAF, 2026-09-13: "Neither should be considered primary."
    institution_email = models.EmailField(blank=True)  # the university address, in practice
    institution_email_delivery = models.BooleanField(default=True)
    personal_email = models.EmailField(blank=True)
    personal_email_delivery = models.BooleanField(default=True)
    first_name = models.CharField(max_length=80)
    middle_name = models.CharField(max_length=80, blank=True)
    last_name = models.CharField(max_length=80)
    preferred_name = models.CharField(max_length=80, blank=True)
    name_from_uls = models.BooleanField(default=False)  # FR-4: read-only to the member when true
    callsign = models.CharField(max_length=12, blank=True, db_index=True)
    cell_phone = models.CharField(max_length=30, blank=True)
    category = models.CharField(max_length=30, blank=True)  # key from club config (FR-8)
    club_position = models.CharField(max_length=40, blank=True)  # key from club config
    access_level = models.CharField(
        max_length=12, choices=AccessLevel.choices, default=AccessLevel.NONE
    )
    under_18 = models.BooleanField(default=False)  # a flag, never a date (§2.4)
    student_level = models.CharField(
        max_length=14,
        blank=True,
        choices=[("undergraduate", "Undergraduate"), ("graduate", "Graduate")],
    )
    graduation_semester = models.CharField(
        max_length=6,
        blank=True,
        choices=[("spring", "Spring"), ("summer", "Summer"), ("fall", "Fall")],
    )
    graduation_year = models.PositiveSmallIntegerField(null=True, blank=True)
    password_is_temporary = models.BooleanField(default=False)  # FR-7
    temporary_password_expires = models.DateTimeField(null=True, blank=True)
    # Entry links (FR-119, FR-120): which link the account came through, and address verification.
    joined_via = models.ForeignKey(
        "EntryLink", null=True, blank=True, on_delete=models.SET_NULL, related_name="joined"
    )
    email_verified_at = models.DateTimeField(null=True, blank=True)
    verification_deadline = models.DateTimeField(null=True, blank=True)  # class links: seven days
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.callsign})" if self.callsign else self.full_name

    # Django admin access follows the access level; there is no separate staff flag.
    @property
    def is_staff(self) -> bool:
        return self.access_level == AccessLevel.SYSADMIN

    @property
    def is_sysadmin(self) -> bool:
        return self.access_level == AccessLevel.SYSADMIN

    @property
    def is_officer(self) -> bool:
        return self.access_level in (AccessLevel.SYSADMIN, AccessLevel.OFFICER)

    @property
    def full_name(self) -> str:
        return " ".join(p for p in (self.first_name, self.middle_name, self.last_name) if p)

    @property
    def display_first(self) -> str:
        return self.preferred_name or self.first_name

    @property
    def short_name(self) -> str:
        """What members see of each other (FR-67): first name and callsign, or first name and
        last initial when there is no callsign."""
        if self.callsign:
            return f"{self.display_first} {self.callsign}"
        initial = f" {self.last_name[0]}." if self.last_name else ""
        return f"{self.display_first}{initial}"

    def can_captain(self, event) -> bool:
        return self.is_officer or event.captaincies.filter(user=self).exists()

    @property
    def is_provisional(self) -> bool:
        return self.access_level == AccessLevel.PROVISIONAL

    @property
    def is_member(self) -> bool:
        """Member or above: sees other members' short names, the directory, the agreements."""
        return self.access_level in (AccessLevel.SYSADMIN, AccessLevel.OFFICER, AccessLevel.MEMBER)

    @property
    def license_letter(self) -> str:
        """N, T, G, A, E, or U (FR-67), from the license record when there is one."""
        lic = getattr(self, "license", None)
        cls = (getattr(lic, "effective_class", "") or "") if lic else ""
        return LICENSE_LETTERS.get(cls.strip().lower(), "U" if not cls else cls[:1].upper())

    @property
    def short_name_lettered(self) -> str:
        return f"{self.short_name} ({self.license_letter})"

    @property
    def full_name_lettered(self) -> str:
        call = f" {self.callsign}" if self.callsign else ""
        return f"{self.full_name}{call} ({self.license_letter})"

    @property
    def verification_overdue(self) -> bool:
        return bool(
            self.verification_deadline
            and not self.email_verified_at
            and self.verification_deadline < timezone.now()
        )


class Guardianship(models.Model):
    """A guardian account acting for a minor (§2.4). A minor may have several."""

    minor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="guardianships")
    guardian = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wards")
    relationship = models.CharField(max_length=40, blank=True)
    active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    ended = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("minor", "guardian")]


class Invitation(models.Model):
    """A single-use, expiring invitation (FR-2, FR-3, FR-104)."""

    class State(models.TextChoices):
        CREATED = "created", "Created"
        COMPLETED = "completed", "Completed"
        REVOKED = "revoked", "Revoked"

    email = models.EmailField()
    category = models.CharField(max_length=30)
    is_minor = models.BooleanField(default=False)
    guardian_email = models.EmailField(blank=True)
    token = models.CharField(max_length=64, unique=True, default=secrets.token_urlsafe)
    issued_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="invitations_issued"
    )
    created = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    emailed_at = models.DateTimeField(
        null=True, blank=True
    )  # FR-104: the issuer knows if the system sent it
    opened_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    state = models.CharField(max_length=10, choices=State.choices, default=State.CREATED)
    accepted_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="invitation"
    )

    def is_valid(self) -> bool:
        return self.state == self.State.CREATED and self.expires_at > timezone.now()

    def __str__(self) -> str:
        return f"invitation to {self.email} ({self.state})"


class CallsignHistory(models.Model):
    """Previous callsigns, so past rosters still read correctly (FR-102)."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="callsign_history")
    callsign = models.CharField(max_length=12)
    held_from = models.DateTimeField(null=True, blank=True)
    held_until = models.DateTimeField(auto_now_add=True)


class NotificationPreference(models.Model):
    """Per category, per channel (FR-71). Absence means the default (on)."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notification_preferences"
    )
    category = models.CharField(max_length=40)
    email = models.BooleanField(default=True)
    push = models.BooleanField(default=True)

    class Meta:
        unique_together = [("user", "category")]


class PushSubscription(models.Model):
    """One browser on one device (FR-112)."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="push_subscriptions")
    endpoint = models.URLField(max_length=1000, unique=True)
    p256dh = models.CharField(max_length=200)
    auth = models.CharField(max_length=100)
    user_agent = models.CharField(max_length=200, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    last_success = models.DateTimeField(null=True, blank=True)
    failures = models.PositiveSmallIntegerField(default=0)


def settings_user_model():  # convenience for type hints elsewhere
    return settings.AUTH_USER_MODEL


class EntryLink(models.Model):
    """A multi-use way in that an officer created (FR-119): a class link admits members of the
    club's institution at once; a community link admits outsiders as Provisional for review.
    Every account records the link it came through, so "are they FRC or Murgas?" is a column."""

    class Kind(models.TextChoices):
        CLASS = "class", "Class (institution addresses, admitted at once)"
        COMMUNITY = "community", "Community (anyone, admitted as Provisional)"

    class State(models.TextChoices):
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        REVOKED = "revoked", "Revoked"

    label = models.CharField(max_length=80)  # the course or the organisation
    kind = models.CharField(max_length=10, choices=Kind.choices)
    required_domain = models.CharField(max_length=120, blank=True)  # class links only
    token = models.CharField(max_length=64, unique=True, default=secrets.token_urlsafe)
    expires_at = models.DateTimeField()
    cap = models.PositiveSmallIntegerField(null=True, blank=True)  # accounts; null = no cap
    landing_event = models.ForeignKey(
        "events.Event", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    state = models.CharField(max_length=8, choices=State.choices, default=State.ACTIVE)
    created_by = models.ForeignKey(
        User, null=True, on_delete=models.SET_NULL, related_name="entry_links_created"
    )
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self) -> str:
        return f"{self.get_kind_display().split(' ')[0].lower()} link {self.label}"

    @property
    def joined_count(self) -> int:
        return self.joined.count()

    def why_closed(self) -> str:
        """Empty when the link admits people; otherwise the reason, in the words shown to them."""
        if self.state == self.State.REVOKED:
            return "This link has been withdrawn."
        if self.state == self.State.PAUSED:
            return "This link is paused for the moment; try again later or ask the person who sent it."
        if self.expires_at <= timezone.now():
            return "This link has expired."
        if self.cap is not None and self.joined_count >= self.cap:
            return "This link has been used as many times as it allows."
        return ""

    @property
    def is_open(self) -> bool:
        return not self.why_closed()
