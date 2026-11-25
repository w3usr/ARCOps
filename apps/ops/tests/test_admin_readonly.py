"""Django admin cannot change what only the application's own paths may change."""

from django.contrib import admin
from django.test import RequestFactory

from apps.accounts.models import User
from apps.credentials.models import AgreementTemplate


def test_an_agreement_version_s_words_are_read_only_and_none_is_added_in_admin():
    model_admin = admin.site._registry[AgreementTemplate]
    request = RequestFactory().get("/")
    assert {"title", "html", "version"} <= set(model_admin.get_readonly_fields(request))
    assert not model_admin.has_add_permission(request)  # versions come from the import (FR-21)


def test_under_18_is_read_only_in_admin():
    request = RequestFactory().get("/")
    assert "under_18" in admin.site._registry[User].get_readonly_fields(request)  # FR-109
