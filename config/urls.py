"""URL configuration. The API (TR-8) is mounted at /api/v1/; everything else is server-rendered."""

from django.contrib import admin
from django.urls import include, path

from apps.ops.api import api
from apps.ops.views import healthz

urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("api/v1/", api.urls),
    path("events/", include("apps.events.urls")),
    path("credentials/", include("apps.credentials.urls")),
    path("me/", include("apps.accounts.urls")),
    path("", include("apps.ops.urls")),
]
