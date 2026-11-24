"""Events, locations, positions, slots, sign-ups (FR-36 to FR-68, FR-110 to FR-113)."""

from __future__ import annotations

from django.conf import settings
from django.db import models


class Event(models.Model):
    class State(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        LOCKED = "locked", "Locked"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Canceled"  # the label is shown; the stored key keeps its spelling

    type = models.CharField(max_length=20, default="contest")  # key from config
    title = models.CharField(max_length=200)
    description_html = models.TextField(blank=True)
    state = models.CharField(max_length=10, choices=State.choices, default=State.DRAFT)
    display_timezone = models.CharField(max_length=60, blank=True)  # falls back to club.timezone
    # The event's start and end, its whole span in UTC (FR-38 as functional addendum A32: one per
    # event; a split contest's break is time outside the on-air hours). Empty until set.
    start = models.DateTimeField(null=True, blank=True)
    end = models.DateTimeField(null=True, blank=True)
    min_license_class = models.CharField(  # the *preferred* class (FR-36, FR-61)
        max_length=20, blank=True, verbose_name="preferred license class"
    )
    rules_url = models.URLField(blank=True)
    contest_fields = models.JSONField(default=dict, blank=True)  # FR-37, by page label
    calendar_ref = models.PositiveIntegerField(null=True, blank=True)  # FR-40
    kbyg_html = models.TextField(blank=True)  # know-before-you-go (FR-77)
    reminder_hours_before = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Empty follows the club's default."
    )
    checkin_opens_minutes_before = models.PositiveSmallIntegerField(  # FR-113, per event
        null=True, blank=True, help_text="Empty follows the club's default."
    )
    display_only = models.BooleanField(default=False)  # FR-45: on the calendar, no roster
    # When a display-only event meets, in fields (services/meets.py): the
    # pattern, its weekday (0 Monday), which week (1 to 4, -1 the last) or day of the month, and
    # the time in the event's own zone. The note says what the fields cannot.
    repeats = models.CharField(max_length=16, blank=True)
    repeat_weekday = models.PositiveSmallIntegerField(null=True, blank=True)
    repeat_week = models.SmallIntegerField(null=True, blank=True)
    repeat_day = models.PositiveSmallIntegerField(null=True, blank=True)
    meets_at = models.TimeField(null=True, blank=True)
    meets_until = models.TimeField(null=True, blank=True)
    meeting_note = models.CharField(max_length=200, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)  # FR-44
    published_at = models.DateTimeField(null=True, blank=True)
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    duplicated_from = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="copies"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="events_created",
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return self.title

    def signups_ahead(self):
        """Sign-ups on slots that have not started yet: what marking the event completed early
        leaves without a slot to run."""
        from django.utils import timezone

        return SignUp.objects.filter(
            slot__position__location__event=self,
            slot__start__gt=timezone.now(),
            slot__cancelled=False,
        )

    def people_ahead(self) -> int:
        return self.signups_ahead().values("user").distinct().count()

    @property
    def visible_to_members(self) -> bool:
        return self.state in (self.State.PUBLISHED, self.State.LOCKED, self.State.COMPLETED)


class OnAirRange(models.Model):
    """The club's on-air hours inside the event's start and end (functional addendum A15):
    a stretch the club means to be on the air. With no range at all, the club is on the air for
    the whole span; a split contest's break is the time between two ranges (A32). Stored merged,
    in UTC."""

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="on_air_ranges")
    start = models.DateTimeField()
    end = models.DateTimeField()

    class Meta:
        ordering = ["start"]


class OperatingLimit(models.Model):
    """Advisory hour limits (FR-39), e.g. School Club Roundup's 6 of 24 and 24 of 107."""

    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name="limit")
    max_hours_per_day = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    day_basis = models.CharField(
        max_length=5, default="utc", choices=[("utc", "UTC day"), ("local", "Local day")]
    )
    max_total_hours = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    min_break_minutes = models.PositiveSmallIntegerField(null=True, blank=True)


class Location(models.Model):
    """A place (FR-51). The viability rule can differ per location."""

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="locations")
    name = models.CharField(max_length=120)
    is_club_station = models.BooleanField(default=True)
    address = models.CharField(max_length=200, blank=True)
    is_private_residence = models.BooleanField(default=False)
    directions_html = models.TextField(blank=True)
    kbyg_html = models.TextField(blank=True)
    viability_rule = models.JSONField(null=True, blank=True)  # None -> club default (FR-61)
    order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.name


class Position(models.Model):
    """An operating station at a location (FR-51)."""

    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="positions")
    name = models.CharField(max_length=60, default="Station")
    order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ["location__order", "order", "id"]

    def __str__(self) -> str:
        return f"{self.location.name}: {self.name}"


class Slot(models.Model):
    """A bookable interval (FR-46, FR-47)."""

    position = models.ForeignKey(Position, on_delete=models.CASCADE, related_name="slots")
    start = models.DateTimeField()
    end = models.DateTimeField()
    kind = models.CharField(
        max_length=20, default="operating"
    )  # operating | setup | breakdown | training ...
    closed = models.BooleanField(default=False)
    cancelled = models.BooleanField(default=False)
    control_operator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )  # captain's override of the default (FR-63)

    class Meta:
        ordering = ["start", "position__location__order", "position__order"]

    def __str__(self) -> str:
        from apps.ops.when import utc_span

        return f"{self.position} {utc_span(self.start, self.end, year=False)}"

    @property
    def event(self) -> Event:
        return self.position.location.event

    @property
    def kept(self) -> str:
        """Why this slot cannot be canceled, as a sentence; "" when it can. Hours and participation
        skip a canceled slot, and canceling one with people deletes their sign-ups, so a slot
        holding a sign-up that stays in the record (SignUp.kept) stays as well."""
        if any(su.kept for su in self.signups.all()):
            return (
                "Someone in this slot has attendance recorded, or the slot has ended, "
                "so it stays in the record and cannot be canceled."
            )
        return ""


class RoleCapacity(models.Model):
    """How many of each role a slot takes (FR-49)."""

    slot = models.ForeignKey(Slot, on_delete=models.CASCADE, related_name="capacities")
    role = models.CharField(max_length=20)
    capacity = models.PositiveSmallIntegerField(default=1)

    class Meta:
        unique_together = [("slot", "role")]


class EligibilityRule(models.Model):
    """Who may take a role (FR-53); event-level default, overridable per slot."""

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="eligibility_rules")
    slot = models.ForeignKey(
        Slot, null=True, blank=True, on_delete=models.CASCADE, related_name="eligibility_rules"
    )
    role = models.CharField(max_length=20)
    categories = models.JSONField(default=list, blank=True)  # empty -> any
    min_license_class = models.CharField(max_length=20, blank=True)
    required_credentials = models.JSONField(default=list, blank=True)
    minors_allowed = models.BooleanField(default=True)


class Opening(models.Model):
    """When a role opens to an audience (FR-54); per role, per event."""

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="openings")
    role = models.CharField(max_length=20)
    opens_at = models.DateTimeField()
    categories = models.JSONField(default=list, blank=True)  # empty -> everyone
    announce = models.BooleanField(default=False)
    announced_at = models.DateTimeField(null=True, blank=True)  # FR-80: once

    class Meta:
        ordering = ["opens_at"]


class SignUp(models.Model):
    """One person, one slot, one role (FR-55, FR-110, FR-113)."""

    slot = models.ForeignKey(Slot, on_delete=models.CASCADE, related_name="signups")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="signups"
    )
    role = models.CharField(max_length=20)
    note = models.TextField(blank=True)  # to the captains (FR-110)
    # When the member last changed it; a note given at sign-up dates from `created`.
    note_at = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)  # FR-72
    checked_in_at = models.DateTimeField(null=True, blank=True)  # FR-113
    no_show = models.BooleanField(default=False)  # FR-124: a captain removes the slot's credit
    checked_in_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    reminder_sent_at = models.DateTimeField(null=True, blank=True)  # FR-72: once per sign-up
    no_show_notified_at = models.DateTimeField(null=True, blank=True)  # FR-113: once per sign-up

    class Meta:
        unique_together = [("slot", "user")]
        ordering = ["created"]

    def __str__(self) -> str:
        return f"{self.user.short_name} as {self.role} in {self.slot}"

    @property
    def kept(self) -> str:
        """Why nobody can give this sign-up up, as a sentence; "" when it can go.
        Attendance cannot be undone, so once it is recorded, once the slot has ended,
        or once the event is over, the sign-up stays in the record: hours and participation are
        counted from it (FR-86, FR-113, FR-124)."""
        from django.utils import timezone

        if self.slot.event.state in (Event.State.COMPLETED, Event.State.CANCELLED):
            return "The event is over, so this sign-up stays in the record."
        # A later slot of a run checked in with one tap has not started:
        # leaving early drops it, as FR-113 says.
        if self.no_show or (self.checked_in_at and self.slot.start <= timezone.now()):
            return "Attendance is recorded for this sign-up, so it stays in the record."
        if self.slot.end <= timezone.now():
            return "This slot has ended, so the sign-up stays in the record."
        return ""

    def checkin_run(self) -> list[SignUp]:
        """This sign-up and the same member's later ones in the same event that follow on with
        no gap, whatever the position: one tap checks them all in (A42). A canceled slot is not
        there, so it ends the run like any gap."""
        run = [self]
        later = (
            SignUp.objects.filter(
                user_id=self.user_id,
                slot__position__location__event=self.slot.position.location.event_id,
                slot__cancelled=False,
                slot__start__gte=self.slot.end,
            )
            .select_related("slot")
            .order_by("slot__start")
        )
        for su in later:
            if su.slot.start != run[-1].slot.end:
                break
            run.append(su)
        return run


class ResponsibleAdult(models.Model):
    """The adult accompanying a minor for one sign-up (FR-64). A member named here is a link, not
    a copy: their email and phone stay on their own account, shown only to those who may see them
    (FR-67). `email` and `phone` are what the guardian typed for anyone else."""

    signup = models.ForeignKey(SignUp, on_delete=models.CASCADE, related_name="responsible_adults")
    name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    present_at = models.DateTimeField(null=True, blank=True)  # recorded at check-in
    # Named because a guardian holds a sign-up on the same slot (A40); it
    # counts only while they do, and goes when they leave.
    automatic = models.BooleanField(default=False)

    @property
    def contact_email(self) -> str:
        return self.member.email if self.member_id else self.email

    @property
    def contact_phone(self) -> str:
        return self.member.cell_phone if self.member_id else self.phone


class Captaincy(models.Model):
    """A per-event grant of officer-equivalent powers (§2.2)."""

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="captaincies")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="captaincies"
    )

    class Meta:
        unique_together = [("event", "user")]


class SlotWarning(models.Model):
    """One at-risk warning sent for a slot in a given state (FR-73). The state key is the status
    plus what is missing, so a change of state earns a new warning and the same state does not
    repeat within the rate limit (12 hours)."""

    slot = models.ForeignKey(Slot, on_delete=models.CASCADE, related_name="warnings")
    state_key = models.CharField(max_length=200)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sent_at"]


class Waitlist(models.Model):
    """FR-57: a member waiting for a full role in a slot. When a place opens, the first pending
    entry is offered it by message and has a window to accept before it passes to the next."""

    class State(models.TextChoices):
        PENDING = "pending", "Waiting"
        OFFERED = "offered", "Offered"
        ACCEPTED = "accepted", "Accepted"
        EXPIRED = "expired", "Offer expired"
        WITHDRAWN = "withdrawn", "Withdrawn"

    slot = models.ForeignKey(Slot, on_delete=models.CASCADE, related_name="waitlist")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="waitlist_entries"
    )
    role = models.CharField(max_length=20)
    state = models.CharField(max_length=10, choices=State.choices, default=State.PENDING)
    created = models.DateTimeField(auto_now_add=True)
    offered_at = models.DateTimeField(null=True, blank=True)
    offer_expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created"]
        unique_together = [("slot", "user", "role")]
