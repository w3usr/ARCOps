from django.contrib import admin

from .models import (
    Captaincy,
    EligibilityRule,
    Event,
    Location,
    Opening,
    OperatingLimit,
    OperatingPeriod,
    Position,
    ResponsibleAdult,
    RoleCapacity,
    SignUp,
    Slot,
)


class PeriodInline(admin.TabularInline):
    model = OperatingPeriod
    extra = 1


class LocationInline(admin.TabularInline):
    model = Location
    extra = 0


class CaptaincyInline(admin.TabularInline):
    model = Captaincy
    extra = 0


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "type", "state", "min_license_class", "created_by")
    list_filter = ("state", "type")
    search_fields = ("title",)
    inlines = [PeriodInline, LocationInline, CaptaincyInline]


class PositionInline(admin.TabularInline):
    model = Position
    extra = 0


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "event", "is_club_station", "is_private_residence")
    inlines = [PositionInline]


class CapacityInline(admin.TabularInline):
    model = RoleCapacity
    extra = 0


class SignUpInline(admin.TabularInline):
    model = SignUp
    extra = 0
    autocomplete_fields = ("user",)


@admin.register(Slot)
class SlotAdmin(admin.ModelAdmin):
    list_display = ("__str__", "kind", "closed", "cancelled")
    list_filter = ("kind", "position__location__event")
    inlines = [CapacityInline, SignUpInline]


@admin.register(SignUp)
class SignUpAdmin(admin.ModelAdmin):
    list_display = ("user", "slot", "role", "confirmed_at", "checked_in_at")
    list_filter = ("role",)
    autocomplete_fields = ("user",)


admin.site.register(OperatingLimit)
admin.site.register(EligibilityRule)
admin.site.register(Opening)
admin.site.register(ResponsibleAdult)
admin.site.register(Position)
