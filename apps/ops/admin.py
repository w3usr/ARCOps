from django.contrib import admin

from .models import AuditLog, ClubSetting, JobRun


@admin.register(ClubSetting)
class ClubSettingAdmin(admin.ModelAdmin):
    list_display = ("key", "value", "source", "updated")
    search_fields = ("key",)

    def save_model(self, request, obj, form, change):
        from .audit import record

        before = (
            ClubSetting.objects.filter(pk=obj.pk).values_list("value", flat=True).first()
            if change
            else None
        )
        obj.source = "interface"  # interface edits win over the file until --reset (TR-32)
        super().save_model(request, obj, form, change)
        record(
            request.user,
            "setting.changed",
            obj,
            before={"value": before},
            after={"value": obj.value},
        )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("at", "actor_label", "action", "subject_type", "subject_id")
    list_filter = ("action",)
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(JobRun)
class JobRunAdmin(admin.ModelAdmin):
    list_display = ("name", "started", "finished", "outcome")
    list_filter = ("name", "outcome")
