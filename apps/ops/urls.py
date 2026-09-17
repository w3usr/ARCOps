from django.urls import path

from apps.comms import views as comms_views
from apps.comms import views_announce

from . import views, views_groups, views_settings

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("ops/status/", views.status, name="job_status"),
    path("ops/settings/", views_settings.settings_page, name="settings_page"),
    path("ops/groups/", views_groups.groups_page, name="groups_page"),
    path("ops/outbox/", comms_views.outbox, name="outbox"),
    path("announce/", views_announce.announce_view, name="announce_all"),
    path("announcements/", views_announce.announcements, name="announcements"),
    path("unsubscribe/<str:token>/", views_announce.unsubscribe, name="unsubscribe"),
    path("ops/templates/", comms_views.message_templates, name="message_templates"),
    path(
        "ops/templates/<str:key>/", comms_views.message_template_edit, name="message_template_edit"
    ),
]
