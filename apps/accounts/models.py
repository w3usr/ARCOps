"""People: members, guardians, invitations (REQUIREMENTS §2, FR-1 to FR-13, FR-102, FR-109)."""

from __future__ import annotations

import secrets
from uuid import uuid4

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models, transaction
from django.utils import timezone

# FR-67: the class after a name; a station letter where the FCC issues no class, U when there
# is no license on file.
MATCHED_STATUSES = frozenset({"active", "expired", "cancelled"})  # the FCC has a record
# The FCC's applicant type (EN24 in its file) for the licensees that are not a person, and the
# letter each one gets. A person's letter is their operator class; these have none to hold.
STATION_LETTERS = {"B": "C", "R": "R", "M": "M"}  # club, RACES, military recreation
LICENSE_LETTERS = {
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

    def create_user(self, email: str = "", password: str | None = None, **extra):
        """`email` is the first address on the account, if there is one. A member under 18 may
        hold none: their guardians are written to instead (FR-70), and the account is its key."""
        confirmed = extra.pop("confirmed", True)  # the path that made the account vouches for it
        groups = extra.pop("groups", None)  # the access groups this account starts in
        # All of it or none of it. Adding the address can be refused (another account has
        # already confirmed it), and without this the account row was already saved by then:
        # three accounts with no address at all survived three refused attempts on 2026-09-19,
        # each in a group, each in the directory, none able to sign in.
        with transaction.atomic(using=self._db):
            user = self.model(**extra)
            user.set_password(password)
            user.save(using=self._db)
            if groups:
                from django.contrib.auth.models import Group

                user.groups.set(Group.objects.filter(name__in=list(groups)))
            if email:
                from .addresses import add

                add(user, self.normalize_email(email).lower(), confirmed=confirmed)
        return user

    def with_access(self):
        """Accounts that can be used: in a group, or a superuser. What "no access" means now is
        belonging to no group at all."""
        from django.db.models import Q

        return (
            self.filter(is_active=True)
            .filter(Q(groups__isnull=False) | Q(is_superuser=True))
            .distinct()
        )

    def by_address(self, address: str, confirmed_only: bool = False):
        """Accounts holding this address. Sign-in and reset ask for confirmed ones only; a
        lookup by contact details (an officer searching) does not care."""
        qs = self.filter(addresses__address__iexact=(address or "").strip())
        if confirmed_only:
            qs = qs.filter(addresses__confirmed=True)
        return qs.distinct()

    def create_superuser(self, email: str, password: str | None = None, **extra):
        """A sysadmin: every capability, without being in any group (apps.ops.capabilities)."""
        extra.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    """A person with an account.

    What the account *is* is `public_id`, a key that never changes and is never shown. What a
    person *signs in with* is any address they have confirmed, held in `Address` rows. Where club
    mail *goes* is each address's own delivery switch. Those were one field once, which forced a
    fabricated address on a minor with no mailbox and another on a deleted account; identity as a
    key removes both (the advisor, 2026-09-17).
    """

    public_id = models.UUIDField(default=uuid4, unique=True, editable=False)
    first_name = models.CharField(max_length=80)
    middle_name = models.CharField(max_length=80, blank=True)
    last_name = models.CharField(max_length=80)
    preferred_name = models.CharField(max_length=80, blank=True)
    name_from_uls = models.BooleanField(default=False)  # FR-4: read-only to the member when true
    # FR-16: a ULS name awaiting the member's confirmation after a callsign was added or changed:
    # {"first": ..., "last": ..., "callsign": ..., "previous": ...}. Empty when nothing is pending.
    pending_uls_name = models.JSONField(default=dict, blank=True)
    callsign = models.CharField(max_length=12, blank=True, db_index=True)
    cell_phone = models.CharField(max_length=30, blank=True)
    push_enabled = models.BooleanField(default=True)  # FR-112: browser notifications, on by default
    # Closure, archiving, and deletion (FR-11, FR-118, FR-125, §4.3). A closed account is No
    # access; an archived one is the club's record of a former member, kept whole and read by the
    # faculty advisor and the sysadmins; a deleted one is anonymised in place so past rosters and
    # counts stay right.
    # When the account was closed, and by whom when it was not the member themselves: a faculty
    # advisor closes the account of somebody who has left without suspending them first (the
    # advisor, 2026-09-19). Null `closed_by` with a date means they asked for it (FR-11).
    closure_requested_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    # Suspension is an officer's act and a faculty advisor's to lift (§2.3, 2026-09-19). It is a
    # fact on the account rather than an inference from an empty group list, because the two
    # ways of losing access lead back in through different doors.
    suspended_at = models.DateTimeField(null=True, blank=True)
    suspended_by = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    suspended_reason = models.CharField(max_length=200, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    archived_reason = models.CharField(max_length=200, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    legal_hold = models.BooleanField(default=False)  # TR-28: retention never touches this account
    category = models.CharField(max_length=30, blank=True)  # key from club config (FR-8)
    club_position = models.CharField(max_length=40, blank=True)  # key from club config
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
    verification_deadline = models.DateTimeField(null=True, blank=True)  # class links: seven days
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()
    USERNAME_FIELD = "public_id"  # identity, never typed by anyone; sign-in is by address
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.callsign})" if self.callsign else self.full_name

    # Django's admin is the sysadmin's tool, and a sysadmin is a superuser. It follows the view
    # the session is acting at, so a sysadmin acting lower cannot reach it either.
    @property
    def is_staff(self) -> bool:
        return self.is_superuser and getattr(self, "acting_capabilities", None) is None

    def has_perm(self, perm, obj=None) -> bool:
        """What this account may do *right now*, which is the view its session is acting at
        (apps.accounts.acting). Everything asks this: `may`, the pages, and Django itself, so a
        lowered view refuses a request rather than merely hiding the button that makes it."""
        acting = getattr(self, "acting_capabilities", None)
        if acting is not None:
            app, _, codename = perm.partition(".")
            from apps.ops.capabilities import APP_LABEL

            return app == APP_LABEL and codename in acting
        return super().has_perm(perm, obj)

    def may(self, capability: str) -> bool:
        """Whether this account holds a capability (apps.ops.capabilities). Every permission
        decision in the application asks this and nothing else, so what a person may do is one
        list, read the same way everywhere."""
        from apps.ops.capabilities import holds

        return holds(self, capability)

    def in_group(self, key: str) -> bool:
        return self.groups.filter(name=key).exists()

    @property
    def has_access(self) -> bool:
        """Whether the account may be used at all. An account in no group can do nothing, which
        is what losing access means now; a superuser always can.

        A group with no capabilities in it still counts, which is how a Provisional account signs
        in and sees the club's events while holding nothing. Deliberately not cached on the
        instance: the code that takes access away asks this before and after, and a cached answer
        made the second one wrong."""
        return bool(self.is_superuser or self.groups.exists())

    @property
    def is_sysadmin(self) -> bool:
        """Kept as the name the pages use for a superuser: the person who answers for the site."""
        return self.is_superuser

    @property
    def email(self) -> str:
        """The address to show where one is wanted. Read-only on purpose: an account is its
        `public_id`, not an address, and a person may hold several."""
        from .addresses import display

        return display(self)

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
        return self.may("manage_events") or event.captaincies.filter(user=self).exists()

    @property
    def reminders_off(self) -> bool:
        """FR-71: the member switched reminder email off; shown on the roster to captains so an
        unconfirmed slot is read correctly. Uses the prefetched preferences when present."""
        return any(
            p.category == "reminder" and not p.email for p in self.notification_preferences.all()
        )

    # Where this account stands with the club, in the order the directory sorts them. Archiving
    # is a flag beside this rather than a value of it: an archived record keeps everything,
    # including the status it had when it was put away (the advisor, 2026-09-19).
    STATUSES = [
        ("provisional", "Provisional"),
        ("active", "Active"),
        ("closed", "Closed"),
        ("suspended", "Suspended"),
        ("deleted", "Deleted"),
    ]
    STATUS_LABELS = dict(STATUSES)

    @property
    def status(self) -> str:
        """One of STATUSES. `archived` is asked separately, because it is a flag."""
        if self.deleted_at:
            return "deleted"
        if self.suspended_at:
            return "suspended"
        if self.closure_requested_at:
            return "closed"
        if self.is_provisional:
            return "provisional"
        if self.has_access:
            return "active"
        # No groups and neither flag: access was taken away before suspension was a fact of its
        # own, or by a path that did not record it. It is a suspension all the same.
        return "suspended"

    @property
    def status_label(self) -> str:
        """Where they stand. Whether the record is archived is a flag beside this, with a
        column of its own (the advisor, 2026-09-19)."""
        return self.STATUS_LABELS[self.status]

    @property
    def is_provisional(self) -> bool:
        """Joined through a community link and not yet reviewed. A group with no capability in
        it: they can sign in and see the club's events, and nothing else."""
        return self.in_group("provisional")

    @property
    def is_member(self) -> bool:
        """Holds the capability that the member directory and the agreements hang on."""
        return self.may("view_directory")

    @property
    def license_letter(self) -> str:
        """The class after a name (FR-67): N, T, G, A, E for a person, C, R, or M for a station,
        U where there is no license on file.

        **The FCC issues an operator class to a person only.** A club, a RACES station, and a
        military recreation station each hold a callsign with the class field empty, so the
        letter comes from the applicant type on the record instead: C a club, R a RACES station,
        M a military recreation station. The advisor asked for the three letters on 2026-09-19,
        starting from the club callsign W2FSR reading U: "It's not technically true... that is a
        Club call sign."

        An empty class is also what "the FCC has no record of this callsign" looks like, so a
        station letter needs a matched record; everything else is U. A matched record with no
        class and no applicant type reads C, which is what the great majority of them are and
        what every row held before the applicant type was imported.
        """
        lic = getattr(self, "license", None)
        if lic is None:
            return "U"
        cls = (getattr(lic, "effective_class", "") or "").strip()
        if cls:
            return LICENSE_LETTERS.get(cls.lower(), cls[:1].upper())
        if lic.effective_status not in MATCHED_STATUSES:
            return "U"
        return STATION_LETTERS.get((getattr(lic, "licensee_type", "") or "").strip().upper(), "C")

    @property
    def license_class(self) -> str:
        """The class in full ("Extra"), or empty for a station and for no license at all.

        `license_letter` abbreviates the same fact for a roster badge, where space is tight.
        A column has room for the word.
        """
        lic = getattr(self, "license", None)
        return ((getattr(lic, "effective_class", "") or "") if lic else "").strip()

    @property
    def short_name_lettered(self) -> str:
        return f"{self.short_name} ({self.license_letter})"

    @property
    def full_name_lettered(self) -> str:
        call = f" {self.callsign}" if self.callsign else ""
        return f"{self.full_name}{call} ({self.license_letter})"

    @property
    def access_label(self) -> str:
        """What this account holds, for a table cell: the groups it is in, or what having none
        means. A sysadmin is a superuser and holds everything without being in a group."""
        if self.is_superuser:
            return "Sysadmin"
        names = [g.name.replace("_", " ").capitalize() for g in self.groups.all()]
        return ", ".join(sorted(names)) or "No access"

    @property
    def is_archived(self) -> bool:
        """A former member, kept as club record. They cannot sign in, they are out of the
        directory and every audience, and the archive is where they are read."""
        return self.archived_at is not None

    @property
    def has_confirmed_address(self) -> bool:
        """Whether anything on this account has been proved. A page reads it to decide whether
        to show the unconfirmed badge, and the verification deadline is measured against it."""
        return self.addresses.filter(confirmed=True).exists()

    @property
    def verification_overdue(self) -> bool:
        """A class link asks the member to confirm an address within a few days; past the
        deadline with nothing confirmed, sign-in pauses until they do or an officer says so."""
        return bool(
            self.verification_deadline
            and not self.addresses.filter(confirmed=True).exists()
            and self.verification_deadline < timezone.now()
        )


class Address(models.Model):
    """An email address on an account.

    A person may hold more than one. Each says what kind it is, whether the person has proved it,
    and whether club mail goes there. Any confirmed address signs its owner in; an unconfirmed
    one still receives mail, so nothing a member relies on waits for delivery. A confirmed
    address belongs to one account, which the constraint below enforces.
    """

    class Kind(models.TextChoices):
        INSTITUTION = "institution", "Institution"
        PERSONAL = "personal", "Personal"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    address = models.EmailField()
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.PERSONAL)
    confirmed = models.BooleanField(default=False)
    delivery = models.BooleanField(default=True)  # club mail goes here
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["kind", "address"]
        constraints = [
            models.UniqueConstraint(fields=["user", "address"], name="one_row_per_address"),
            models.UniqueConstraint(
                fields=["address"],
                condition=models.Q(confirmed=True),
                name="a_confirmed_address_belongs_to_one_account",
            ),
        ]

    def __str__(self) -> str:
        return self.address


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

    email = models.EmailField(blank=True)  # blank only for a minor with no address (§2.4)
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

    label = models.CharField(max_length=80)  # the course or the organization
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
            return (
                "This link is paused for the moment; try again later or ask the person who sent it."
            )
        if self.expires_at <= timezone.now():
            return "This link has expired."
        if self.cap is not None and self.joined_count >= self.cap:
            return "This link has been used as many times as it allows."
        return ""

    @property
    def is_open(self) -> bool:
        return not self.why_closed()
