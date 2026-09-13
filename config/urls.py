"""URL configuration. The API (TR-8) is mounted at /api/v1/; everything else is server-rendered."""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView, TemplateView

from apps.ops.api import api
from apps.ops.views import healthz

urlpatterns = [
    path("healthz", healthz, name="healthz"),
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
    path("", include("apps.ops.urls")),
]
