from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserChangeForm as DjangoUserChangeForm
from django.contrib.auth.forms import UserCreationForm as DjangoUserCreationForm

from .models import (
    Address,
    CallsignHistory,
    Guardianship,
    Invitation,
    NotificationPreference,
    PushSubscription,
    User,
)


class AddressInline(admin.TabularInline):
    """An account's addresses, edited beside it. The rules (a confirmed address belongs to one
    account, an account keeps at least one) are enforced by the model and the pages, so an admin
    editing here is deliberately working below them."""

    model = Address
    extra = 0


class UserCreationForm(DjangoUserCreationForm):
    class Meta(DjangoUserCreationForm.Meta):
        model = User
        fields = ("first_name", "last_name", "category")


class UserChangeForm(DjangoUserChangeForm):
    class Meta(DjangoUserChangeForm.Meta):
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    add_form = UserCreationForm
    form = UserChangeForm
    ordering = ("last_name", "first_name")
    list_display = (
        "addresses_shown",
        "first_name",
        "last_name",
        "callsign",
        "category",
        "access_shown",
        "under_18",
    )
    list_filter = ("groups", "is_superuser", "category", "under_18", "archived_at")
    search_fields = ("addresses__address", "first_name", "last_name", "callsign")
    fieldsets = (
        (None, {"fields": ("public_id", "password")}),
        (
            "Name",
            {
                "fields": (
                    "first_name",
                    "middle_name",
                    "last_name",
                    "preferred_name",
                    "name_from_uls",
                )
            },
        ),
        (
            "Contact",
            {"fields": ("cell_phone",)},
        ),
        ("Club", {"fields": ("callsign", "category", "club_positions", "under_18")}),
        ("Student", {"fields": ("student_level", "graduation_semester", "graduation_year")}),
        (
            "Leaving",
            {
                "fields": ("archived_at", "archived_reason", "closure_requested_at", "legal_hold"),
                "description": "A former member is archived rather than deleted; the archive is "
                "read by a faculty advisor or a sysadmin at /members/archive/.",
            },
        ),
        (
            "Account",
            {
                "fields": (
                    "is_active",
                    "is_superuser",
                    "password_is_temporary",
                    "date_joined",
                    "groups",
                    "user_permissions",
                )
            },
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                    "category",
                    "groups",
                )
            },
        ),
    )
    readonly_fields = ("date_joined", "public_id")
    inlines = (AddressInline,)

    @admin.display(description="Permission level")
    def access_shown(self, obj) -> str:
        if obj.is_superuser:
            return "sysadmin"
        return ", ".join(g.name for g in obj.groups.all()) or "none"

    @admin.display(description="Addresses")
    def addresses_shown(self, obj) -> str:
        return ", ".join(a.address for a in obj.addresses.all()) or "(none)"


admin.site.register(Guardianship)
admin.site.register(Invitation)
admin.site.register(CallsignHistory)
admin.site.register(NotificationPreference)
admin.site.register(PushSubscription)


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    """Addresses are rows, not fields: an account is its key, and a person may hold several."""

    list_display = ("address", "user", "kind", "confirmed", "delivery", "created")
    list_filter = ("kind", "confirmed", "delivery")
    search_fields = ("address", "user__first_name", "user__last_name", "user__callsign")
