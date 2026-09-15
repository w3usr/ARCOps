"""URL configuration. The API (TR-8) is mounted at /api/v1/; everything else is server-rendered."""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView, TemplateView

from apps.accounts import views_entry, views_members
from apps.ops.api import api
from apps.ops.views import healthz, manifest

urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("manifest.webmanifest", manifest, name="manifest"),
    # The admin signs in through allauth, so its second-factor rules apply there too.
    path(
        "admin/login/", RedirectView.as_view(url="/accounts/login/?next=/admin/", permanent=False)
    ),
    path("admin/", admin.site.urls),
    # Invitation only (FR-1): the public signup route shows a closed page.
    path(
        "accounts/signup/",
        TemplateView.as_view(template_name="account/signup_closed.html"),
        name="account_signup",
    ),
    path("accounts/", include("allauth.urls")),
    path("api/v1/", api.urls),
    path("events/", include("apps.events.urls")),
    path("credentials/", include("apps.credentials.urls")),
    path("me/", include("apps.accounts.urls")),
    path("members/", views_members.members, name="members"),
    path("members/<int:pk>/", views_members.member_detail, name="member_detail"),
    path("members/hours/", views_members.hours, name="hours"),
    # Entry links (FR-119, FR-120, FR-123): public pages, gated by the link's own state.
    path("join/<str:token>/", views_entry.join, name="join"),
    path("join/<str:token>/form/", views_entry.join_form, name="join_form"),
    path("mentors/<str:token>/", views_entry.mentor_needs_page, name="mentor_needs"),
    path("verify/<str:token>/", views_entry.verify_email, name="verify_email"),
    path("", include("apps.ops.urls")),
]
