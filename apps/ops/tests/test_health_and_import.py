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


def test_service_worker_is_served_at_the_root_uncached(client):
    r = client.get("/sw.js")
    assert r.status_code == 200 and b"ops-shell-v" in r.content
    assert "no-cache" in r["Cache-Control"] and r["Service-Worker-Allowed"] == "/"


@pytest.mark.django_db
def test_the_manifest_declares_each_icon_at_its_real_size():
    """A browser decides whether a site can be installed, and which icon to put on the home
    screen, from the sizes a manifest declares. "any" means scalable, which a PNG is not, so the
    club's 512px logo was being passed over for the smaller one (2026-09-19)."""
    import json

    from django.core.management import call_command
    from django.test import Client

    call_command("club_import")
    body = json.loads(Client().get("/manifest.webmanifest", HTTP_HOST="testserver").content)
    icons = {i["src"]: i for i in body["icons"]}
    assert icons, "a manifest with no icon cannot be installed"
    for icon in icons.values():
        assert icon["type"] in ("image/png", "image/svg+xml")
        if icon["type"] == "image/png":
            width, _, height = icon["sizes"].partition("x")
            assert width.isdigit() and height.isdigit(), icon
    big_enough = [
        i
        for i in icons.values()
        if i["type"] == "image/svg+xml" or int(i["sizes"].split("x")[0]) >= 192
    ]
    assert big_enough, "one icon at least as large as a launcher wants, or a scalable one"


@pytest.mark.django_db
def test_an_installed_icon_is_offered_for_the_phones_own_mask():
    """NAF, 2026-09-20, of the club seal on his home screen: "Can we have less whitespace on the
    app icon?" A launcher shrinks an icon of unknown shape onto a white tile. One declared
    maskable is drawn to the edge and cropped to the launcher's shape instead."""
    import json

    from django.core.management import call_command
    from django.test import Client

    call_command("club_import")
    body = json.loads(Client().get("/manifest.webmanifest", HTTP_HOST="testserver").content)
    purposes = {i.get("purpose") for i in body["icons"]}
    assert "maskable" in purposes, "without one the phone pads the icon itself"
    assert "any" in purposes, "and one that is not cropped, for everywhere else"
