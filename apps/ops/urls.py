from django.urls import path

from apps.comms import views as comms_views

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("ops/status/", views.status, name="job_status"),
    path("ops/outbox/", comms_views.outbox, name="outbox"),
    path("ops/templates/", comms_views.message_templates, name="message_templates"),
    path(
        "ops/templates/<str:key>/", comms_views.message_template_edit, name="message_template_edit"
    ),
]
