import pytest
from django.core.management import call_command
from django.test import Client

from apps.credentials.models import AgreementTemplate
from apps.ops.models import ClubSetting

pytestmark = pytest.mark.django_db


def test_healthz_ok():
    r = Client().get("/healthz")
    assert r.status_code == 200 and r.json()["db"] == "ok"


def test_generic_import_is_idempotent_and_versions_by_hash():
    call_command("club_import")
    assert ClubSetting.objects.get(key="club.name").value == "Example Amateur Radio Club"
    first = AgreementTemplate.objects.get(key="station_access.example", is_current=True)
    call_command("club_import")
    assert AgreementTemplate.objects.filter(key="station_access.example").count() == 1
    assert (
        AgreementTemplate.objects.get(key="station_access.example", is_current=True).pk == first.pk
    )
    assert first.is_example


def test_interface_edit_survives_import_unless_reset():
    call_command("club_import")
    s = ClubSetting.objects.get(key="club.short_name")
    s.value, s.source = "Edited", "interface"
    s.save()
    call_command("club_import")
    assert ClubSetting.objects.get(key="club.short_name").value == "Edited"
    call_command("club_import", "--reset")
    assert ClubSetting.objects.get(key="club.short_name").value == "Example ARC"


def test_signin_page_renders_for_anonymous():
    r = Client().get("/accounts/login/")
    assert r.status_code == 200 and b"Sign in" in r.content or b"Sign In" in r.content


def test_dashboard_requires_login():
    r = Client().get("/")
    assert r.status_code == 302 and "/accounts/login/" in r["Location"]


def test_manifest_carries_the_installations_name_not_the_products():
    ClubSetting.objects.update_or_create(key="club.short_name", defaults={"value": "Test ARC"})
    ClubSetting.objects.update_or_create(
        key="club.name", defaults={"value": "Test Amateur Radio Club"}
    )
    r = Client().get("/manifest.webmanifest", HTTP_HOST="testserver")
    body = r.json()
    assert r["Content-Type"].startswith("application/manifest+json")
    assert body["name"] == "Test ARC Operations (testserver)" and body["short_name"] == "Test ARC"
    assert "ARCOps" not in body["name"] and body["start_url"] == "/"
