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

    @property
    def effective_class(self) -> str:
        return self.override_class or self.operator_class

    @property
    def effective_status(self) -> str:
        return self.override_status or self.status

    @property
    def effective_expiry(self):
        return self.override_expiry or self.expiry_date

    def __str__(self) -> str:
        return f"{self.callsign} {self.effective_class} ({self.effective_status})"


class UlsLicense(models.Model):
    """The local table built from the FCC's bulk files (TR-13): one row per callsign."""

    callsign = models.CharField(max_length=12, primary_key=True)
    licensee_name = models.CharField(max_length=160, blank=True)
    operator_class = models.CharField(max_length=20, blank=True)
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

    class Meta:
        ordering = ["-signed_at"]

    def __str__(self) -> str:
        return f"{self.user} {self.credential.key} {self.state}"


class SharedSecret(models.Model):
    """The shared computer account password, Fernet-encrypted (FR-32, TR-20)."""

    name = models.CharField(max_length=60, unique=True, default="computer_account")
    ciphertext = models.BinaryField()
    effective_date = models.DateField()
    set_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    set_at = models.DateTimeField(auto_now=True)
