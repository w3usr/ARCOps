from django.contrib import admin

from .models import (
    AgreementTemplate,
    CredentialType,
    LicenseRecord,
    SharedSecret,
    SignedAgreement,
    UlsLicense,
)

admin.site.register(CredentialType)


@admin.register(LicenseRecord)
class LicenseRecordAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "callsign",
        "effective_class",
        "effective_status",
        "effective_expiry",
        "source",
    )
    search_fields = ("callsign", "user__last_name")


@admin.register(UlsLicense)
class UlsLicenseAdmin(admin.ModelAdmin):
    list_display = ("callsign", "licensee_name", "operator_class", "status", "expiry_date")
    search_fields = ("callsign", "licensee_name")


@admin.register(AgreementTemplate)
class AgreementTemplateAdmin(admin.ModelAdmin):
    list_display = ("key", "version", "title", "credential", "is_current", "effective_date")
    # A version's words are what a member signed; a new version comes only from the club import
    # (FR-21), so the admin shows them and cannot change or add them.
    readonly_fields = ("key", "version", "title", "html", "content_hash")

    def has_add_permission(self, request):
        return False


@admin.register(SignedAgreement)
class SignedAgreementAdmin(admin.ModelAdmin):
    list_display = ("user", "credential", "state", "signed_at", "expires_on", "approver")
    list_filter = ("state", "credential")


@admin.register(SharedSecret)
class SharedSecretAdmin(admin.ModelAdmin):
    list_display = ("name", "effective_date", "set_by", "set_at")
    exclude = ("ciphertext",)
