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


@pytest.mark.django_db
def test_a_club_overlay_is_laid_over_the_shipped_defaults(tmp_path, settings):
    """TR-41 calls it an overlay, and it had been a replacement: a setting added to the
    application never reached an installation with its own club.yaml. Found on 2026-09-20, when
    the two-step verification settings were invisible on the club's own server.
    """
    from apps.ops.config import load_yaml

    (tmp_path / "club.yaml").write_text(
        "club:\n  name: Overlay Radio Club\nmember_categories:\n  - { key: only, label: Only }\n",
        encoding="utf-8",
    )
    settings.CLUB_OVERLAY_DIR = tmp_path
    data = load_yaml(tmp_path)

    assert data["club"]["name"] == "Overlay Radio Club", "the overlay's own answer wins"
    assert "short_name" in data["club"], "and the shipped answer fills the gap beside it"
    assert data["member_categories"] == [{"key": "only", "label": "Only"}], (
        "a list the club states is taken whole, not added to ours"
    )
    assert "security" in data, "a namespace the overlay has never heard of still arrives"


def test_a_re_sign_date_lives_beside_the_agreement_and_survives_the_deploy_order(tmp_path):
    """FR-30. The deploy imports first, writing the new version with no re-sign date; a later
    `club_import --resign-by` found the file unchanged and did nothing, silently (T40 step 4,
    2026-10-21). The date now lives in club.yaml beside the agreement, and the option works on an
    unchanged file too. SK, 2026-10-26."""
    import io

    (tmp_path / "agreements").mkdir()
    page = tmp_path / "agreements" / "sa.html"

    def setup(text, resign_by=""):
        page.write_text(f"<h1>Station</h1><p>{text}</p>", encoding="utf-8")
        extra = f"\n    resign_by: {resign_by}" if resign_by else ""
        (tmp_path / "club.yaml").write_text(
            "agreements:\n  - key: sa\n    credential: station_access\n    audience: [student]\n"
            f'    file: "agreements/sa.html"\n    title: Station{extra}\n',
            encoding="utf-8",
        )

    def run(*args):
        out = io.StringIO()
        call_command("club_import", str(tmp_path), *args, stdout=out)
        return out.getvalue()

    def current():
        return AgreementTemplate.objects.get(key="sa", is_current=True)

    setup("one", resign_by="2030-01-01")
    out = run()
    assert current().version == 1 and current().resign_by is None, "nothing earlier to re-sign"
    assert "version 1 has nothing earlier to re-sign" in out

    setup("two")  # the deploy: the text changed, and no date given yet
    run()
    assert current().version == 2 and current().resign_by is None

    setup("two", resign_by="2030-01-01")  # the date added beside it, deployed again
    out = run()
    assert current().version == 2 and str(current().resign_by) == "2030-01-01"
    assert "sa version 2: re-sign by 2030-01-01" in out
    assert "sa version 2" not in run(), "set once; an unchanged import says nothing"

    # The option fills in a date where a republished version has none, on an unchanged file too,
    # and says so; it never replaces a date the configuration gave.
    setup("three")
    run()
    assert current().version == 3 and current().resign_by is None
    out = run("--resign-by", "2031-02-03")
    assert str(current().resign_by) == "2031-02-03" and "sa version 3: re-sign by 2031-02-03" in out
    setup("three", resign_by="2032-04-05")
    run("--resign-by", "2031-02-03")
    assert str(current().resign_by) == "2032-04-05", "the configuration's own date stands"
