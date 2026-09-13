from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserChangeForm as DjangoUserChangeForm
from django.contrib.auth.forms import UserCreationForm as DjangoUserCreationForm

from .models import (
    CallsignHistory,
    Guardianship,
    Invitation,
    NotificationPreference,
    PushSubscription,
    User,
)


class UserCreationForm(DjangoUserCreationForm):
    class Meta(DjangoUserCreationForm.Meta):
        model = User
        fields = ("email", "first_name", "last_name", "category", "access_level")


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
        "email",
        "first_name",
        "last_name",
        "callsign",
        "category",
        "access_level",
        "under_18",
    )
    list_filter = ("access_level", "category", "under_18")
    search_fields = ("email", "first_name", "last_name", "callsign")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
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
            {"fields": ("institution_email", "personal_email", "email_preference", "cell_phone")},
        ),
        ("Club", {"fields": ("callsign", "category", "club_position", "access_level", "under_18")}),
        ("Student", {"fields": ("student_level", "graduation_semester", "graduation_year")}),
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
                    "email",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                    "category",
                    "access_level",
                )
            },
        ),
    )
    readonly_fields = ("date_joined",)


admin.site.register(Guardianship)
admin.site.register(Invitation)
admin.site.register(CallsignHistory)
admin.site.register(NotificationPreference)
admin.site.register(PushSubscription)
