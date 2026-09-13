from django.contrib import admin

from .models import Announcement, MessageTemplate, Outbox


@admin.register(Outbox)
class OutboxAdmin(admin.ModelAdmin):
    list_display = ("created", "user", "category", "subject", "state")
    list_filter = ("state", "category")
    readonly_fields = ("created", "sent_at")


admin.site.register(MessageTemplate)
admin.site.register(Announcement)
