"""Credentials: licenses, agreements, the shared secret (FR-14 to FR-35, TR-13, TR-20)."""

from django.conf import settings
from django.db import models


class CredentialType(models.Model):
    """A verified fact a slot may require (FR-18). Configured, not coded."""

    key = models.CharField(max_length=40, unique=True)
    label = models.CharField(max_length=80)
    established_by = models.CharField(
        max_length=20,
        choices=[
            ("fcc_uls", "FCC ULS lookup"),
            ("agreement", "Signed agreement plus approval"),
            ("assertion", "Sysadmin assertion"),
        ],
    )
    graded = models.BooleanField(default=False)  # license classes compare on the ladder
    default_expiry = models.CharField(max_length=40, default="one_year")  # rule key, see services

    def __str__(self) -> str:
        return self.label


class LicenseRecord(models.Model):
    """What the FCC says about a member's license (FR-14), plus any sysadmin override (FR-15)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="license"
    )
    callsign = models.CharField(max_length=12)
    licensee_name = models.CharField(max_length=120, blank=True)
    operator_class = models.CharField(max_length=20, blank=True)
    # What kind of licensee this is, from the FCC record (UlsLicense.applicant_type): B a club,
    # R a RACES station, M a military recreation station, I a person. Blank until the import
    # has seen the callsign, or for a license from outside the United States.
    licensee_type = models.CharField(max_length=2, blank=True)
    status = models.CharField(
        max_length=20, default="unverified"
    )  # active | expired | cancelled | not_found | unverified
    grant_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    frn = models.CharField(max_length=20, blank=True)
    source = models.CharField(max_length=40, blank=True)
    retrieved_at = models.DateTimeField(null=True, blank=True)
    override_class = models.CharField(max_length=20, blank=True)
    override_status = models.CharField(max_length=20, blank=True)
    override_expiry = models.DateField(null=True, blank=True)
    override_name = models.CharField(max_length=120, blank=True)
    override_reason = models.TextField(blank=True)
    override_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    override_country = models.CharField(max_length=60, blank=True)  # FR-20: a non-US license
    # FR-17: which expiry notice has gone out for the expiry currently on record.
    expiry_notice_stage = models.PositiveSmallIntegerField(default=0)  # 0 none, 90, 30, 1 = expired
    expiry_notice_for = models.DateField(null=True, blank=True)

    @property
    def has_override(self) -> bool:
        return bool(
            self.override_class
            or self.override_status
            or self.override_expiry
            or self.override_name
        )

    @property
    def effective_source(self) -> str:
        if self.has_override:
            return "sysadmin override" + (
                f", {self.override_country}" if self.override_country else ""
            )
        return self.source or "unverified"

    @property
    def effective_class(self) -> str:
        return self.override_class or self.operator_class

    @property
    def effective_status(self) -> str:
        return self.override_status or self.status

    # What a page shows. The stored values are keys ("not_found", "unverified"); a person
    # reading a member's page should see a sentence, not a column value.
    STATUS_WORDS = {
        "active": "active",
        "expired": "expired",
        "cancelled": "canceled by the FCC",
        "not_found": "no FCC record under this callsign",
        "unverified": "not checked against the FCC yet",
    }

    # The FCC issues an operator class to a person only. Where the class field is empty, what
    # the applicant type says the licensee is, is the honest thing to show in its place.
    LICENSEE_WORDS = {
        "B": "club station",
        "R": "RACES station",
        "M": "military recreation station",
    }

    @property
    def licensee(self) -> str:
        """The name on the license, which is not always the name the person uses.

        The advisor, 2026-09-19: "we should print out the license name in the License box." It
        is what an officer checks a callsign against, and where a member's own name comes from
        while they hold a callsign (FR-4, FR-8).
        """
        return (self.override_name or self.licensee_name or "").strip()

    @property
    def class_label(self) -> str:
        """The operator class in words, or what kind of station holds the callsign instead."""
        if self.effective_class:
            return self.effective_class
        if self.effective_status in {"active", "expired", "cancelled"}:
            return self.LICENSEE_WORDS.get(
                (self.licensee_type or "").strip().upper(), "club station"
            )
        return "class unknown"

    @property
    def status_label(self) -> str:
        status = self.effective_status
        return self.STATUS_WORDS.get(status, status.replace("_", " "))

    # `source` is a stored key and never reaches a page as one (TR-44). `fcc_uls_local` is what
    # the import writes; `uls` is the name it had before the local table, kept for rows written
    # then. A key with no words here is a fault in this map, so the line goes rather than the
    # key: the advisor met "Fcc_uls_local." on his own member page (2026-09-20).
    SOURCE_WORDS = {
        "fcc_uls_local": "from the FCC",
        "uls": "from the FCC",
        "unverified": "not checked yet",
        "manual": "entered here",
    }

    @property
    def source_label(self) -> str:
        if self.has_override:
            return "set by a sysadmin" + (
                f", {self.override_country}" if self.override_country else ""
            )
        return self.SOURCE_WORDS.get(self.source or "unverified", "")

    @property
    def effective_expiry(self):
        return self.override_expiry or self.expiry_date

    def __str__(self) -> str:
        return f"{self.callsign} {self.effective_class} ({self.effective_status})"


class UlsLicense(models.Model):
    """The local table built from the FCC's bulk files (TR-13): one row per callsign."""

    callsign = models.CharField(max_length=12, primary_key=True)
    licensee_name = models.CharField(max_length=160, blank=True)
    first_name = models.CharField(max_length=80, blank=True)
    middle_initial = models.CharField(max_length=2, blank=True)  # EN10: "L" of MARY L WEST
    last_name = models.CharField(max_length=80, blank=True)
    operator_class = models.CharField(max_length=20, blank=True)
    # EN24 in the FCC file: B a club, R a RACES station, M a military recreation station, I a
    # person. It is what tells a station apart from a person where there is no operator class,
    # because the FCC issues a class to a person only.
    applicant_type = models.CharField(max_length=2, blank=True)
    status = models.CharField(max_length=20, blank=True)
    grant_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    frn = models.CharField(max_length=20, blank=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "ULS license"


class AgreementTemplate(models.Model):
    """One version of an agreement's text (FR-21). Never edited after publication."""

    key = models.CharField(max_length=60, db_index=True)
    credential = models.ForeignKey(
        CredentialType, on_delete=models.PROTECT, related_name="templates"
    )
    title = models.CharField(max_length=160)
    audience = models.JSONField(default=list)  # category keys that see it
    version = models.PositiveIntegerField()
    content_hash = models.CharField(max_length=64)
    html = models.TextField()
    effective_date = models.DateField()
    is_current = models.BooleanField(default=True)
    # FR-30: when this version was published, the publisher chose whether approvals of the
    # earlier versions stand until their own expiry (null) or must be re-signed by a date.
    resign_by = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = [("key", "version")]
        ordering = ["key", "-version"]

    def __str__(self) -> str:
        return f"{self.title} v{self.version}"

    @property
    def is_example(self) -> bool:
        return self.key.endswith(".example")


class SignedAgreement(models.Model):
    """A member's signature on a template version, and what became of it (FR-22, FR-25, FR-26)."""

    class State(models.TextChoices):
        SIGNED = "signed", "Signed, awaiting approval"
        APPROVED = "approved", "Approved"
        DECLINED = "declined", "Declined"
        EXPIRED = "expired", "Expired"
        REVOKED = "revoked", "Revoked"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="agreements"
    )
    template = models.ForeignKey(
        AgreementTemplate,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="signatures",
    )
    credential = models.ForeignKey(
        CredentialType, on_delete=models.PROTECT, related_name="signatures"
    )
    signer_name = models.CharField(max_length=160)
    signed_by_guardian = models.BooleanField(default=False)
    signed_at = models.DateTimeField(auto_now_add=True)
    signer_ip = models.GenericIPAddressField(null=True, blank=True)
    content_hash = models.CharField(max_length=64, blank=True)
    state = models.CharField(max_length=10, choices=State.choices, default=State.SIGNED)
    expires_on = models.DateField(null=True, blank=True)
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approvals_given",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    decision_reason = models.TextField(blank=True)
    pdf = models.FileField(upload_to="agreements/%Y/", blank=True)
    notice_30_sent_on = models.DateField(null=True, blank=True)  # FR-28
    notice_expiry_sent_on = models.DateField(null=True, blank=True)  # FR-28
    revoked_at = models.DateTimeField(null=True, blank=True)  # FR-29

    class Meta:
        ordering = ["-signed_at"]

    def __str__(self) -> str:
        return f"{self.user} {self.credential.key} {self.state}"


class CredentialDecision(models.Model):
    """Every act that changed whether somebody holds access, kept in the order they happened.

    `SignedAgreement` carries only the latest one: approving after a decline overwrites the
    decline, so the mistake and its correction leave a single row saying "approved". The audit
    log (FR-92) is the wrong shape for a page — it names its subject by two strings with no key
    and no index — and the wrong readership, being a sysadmin's to read, while the person who
    works the approvals page is the faculty advisor.

    > I think we need a searchable, filterable, sortable log on this page of what approval
    > actions have been taken. — NAF, 2026-09-20

    Append-only by use rather than by constraint: nothing in the application updates a row, and
    a decision that was wrong is corrected by making another one.
    """

    class Action(models.TextChoices):
        APPROVED = "approved", "Approved"
        APPROVED_AFTER_DECLINE = "approved_after_decline", "Approved after a decline"
        DECLINED = "declined", "Declined"
        REVOKED = "revoked", "Revoked"
        EXPIRED = "expired", "Expired"
        SUPERSEDED = "superseded", "Superseded by a new version"

    # The tone each action is drawn in, so the page never prints the stored key (TR-44).
    TONES = {
        "approved": "ok",
        "approved_after_decline": "ok",
        "declined": "warn",
        "expired": "warn",
        "superseded": "warn",
        "revoked": "bad",
    }

    agreement = models.ForeignKey(
        "credentials.SignedAgreement", on_delete=models.CASCADE, related_name="decisions"
    )
    action = models.CharField(max_length=24, choices=Action.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    # Frozen, the way the audit log freezes it: a decision outlives the account that made it,
    # and "system" is the nightly job.
    actor_label = models.CharField(max_length=200, blank=True)
    at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)  # the reason given, or what superseded it
    expires_on = models.DateField(null=True, blank=True)  # the date an approval set

    class Meta:
        ordering = ["-at"]
        indexes = [
            models.Index(fields=["-at"]),
            models.Index(fields=["agreement", "at"]),
        ]

    @property
    def tone(self) -> str:
        return self.TONES.get(self.action, "note")

    def __str__(self) -> str:
        return f"{self.agreement_id} {self.action} {self.at:%Y-%m-%d}"


class SharedSecret(models.Model):
    """The shared computer account password, Fernet-encrypted (FR-32, TR-20)."""

    name = models.CharField(max_length=60, unique=True, default="computer_account")
    ciphertext = models.BinaryField()
    effective_date = models.DateField()
    set_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    set_at = models.DateTimeField(auto_now=True)


class UlsStaging(models.Model):
    """Scratch rows for one import run (TR-13): the HD, AM, and EN records of the FCC file joined
    on the unique system identifier before the winner per callsign is written to UlsLicense.
    Emptied at the start of every run; never read by the application."""

    usi = models.CharField(max_length=12, primary_key=True)
    callsign = models.CharField(max_length=12, db_index=True)
    status_code = models.CharField(max_length=2, blank=True)
    grant_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    class_code = models.CharField(max_length=2, blank=True)
    applicant_type = models.CharField(max_length=2, blank=True)
    entity_name = models.CharField(max_length=160, blank=True)
    first_name = models.CharField(max_length=80, blank=True)
    middle_initial = models.CharField(max_length=2, blank=True)
    last_name = models.CharField(max_length=80, blank=True)
    frn = models.CharField(max_length=20, blank=True)
