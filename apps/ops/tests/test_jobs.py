"""The job runner (TR-11), pings (TR-33), the watchdog, /healthz, and the status page (FR-93)."""

from datetime import timedelta
from unittest import mock

import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.ops import jobs
from apps.ops.models import AuditLog, ClubSetting, JobRun

pytestmark = pytest.mark.django_db


def test_selfcheck_records_an_ok_run_and_pings_with_create():
    with override_settings(
        HEALTHCHECKS_PING_KEY="k123", HEALTHCHECKS_PING_URL="https://hc.example"
    ):
        with mock.patch("apps.ops.jobs.urllib.request.urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value.status = 200
            call_command("selfcheck")
            (url,), kwargs = urlopen.call_args[0], urlopen.call_args[1]
    assert url == "https://hc.example/k123/ops-selfcheck?create=1" and kwargs["timeout"] == 10
    run = JobRun.objects.get(name="selfcheck")
    assert run.outcome == "ok" and run.finished and run.detail["db"] == "ok"


def test_no_ping_key_means_no_network_and_a_failed_job_is_recorded_and_pinged_fail():
    class Boom(jobs.ScheduledCommand):
        job_name = "selfcheck"

        def run_job(self, now, **options):
            raise RuntimeError("kaput")

    with mock.patch("apps.ops.jobs.urllib.request.urlopen") as urlopen:
        call_command("selfcheck")
        urlopen.assert_not_called()  # no key configured in tests
    with override_settings(HEALTHCHECKS_PING_KEY="k"):
        with mock.patch("apps.ops.jobs.urllib.request.urlopen") as urlopen:
            with pytest.raises(CommandError):
                Boom().handle(now=None)
            assert urlopen.call_args[0][0].endswith("/k/ops-selfcheck/fail?create=1")
    run = JobRun.objects.filter(name="selfcheck").order_by("-started").first()
    assert run.outcome == "failed" and "kaput" in run.detail["error"]


def test_now_option_is_parsed_and_rejected_when_malformed():
    seen = {}

    class Probe(jobs.ScheduledCommand):
        job_name = "selfcheck"

        def run_job(self, now, **options):
            seen["now"] = now
            return {}

    Probe().handle(now="2026-10-10T16:00:00+00:00")
    assert seen["now"].isoformat() == "2026-10-10T16:00:00+00:00"
    with pytest.raises(CommandError):
        Probe().handle(now="yesterday")


def test_stale_detection_uses_period_plus_grace_and_the_watchdog_reports_it():
    now = timezone.now()
    assert jobs.stale_jobs(now) == []  # nothing has ever run: not stale
    ok = JobRun.objects.create(name="selfcheck", outcome="ok")
    JobRun.objects.filter(pk=ok.pk).update(
        started=now - timedelta(hours=2), finished=now - timedelta(hours=2)
    )
    assert "selfcheck" in jobs.stale_jobs(now)  # 2 h old against 5 min + 10 min
    call_command("jobs_stale", "--now", now.isoformat())
    watchdog = JobRun.objects.get(name="jobs:stale")
    assert "selfcheck" in watchdog.detail["stale"] and "jobs:stale" not in watchdog.detail["stale"]
    # a job that has never succeeded becomes stale once the table is older than its allowance
    assert "jobs:stale" in jobs.stale_jobs(now + timedelta(hours=3))
    body = Client().get("/healthz").json()
    assert "selfcheck" in body["stale_jobs"] and body["jobs"]["jobs:stale"]


def test_status_page_is_sysadmin_only_and_shows_jobs_and_mail():
    call_command("selfcheck")
    ClubSetting.objects.update_or_create(key="defaults.email_delivery", defaults={"value": "on"})
    o = User.objects.create_user("o@example.org", "pw-Testing-123")
    o.groups.set(Group.objects.filter(name="officer"))
    o.save()
    c = Client()
    c.force_login(o)
    assert c.get("/ops/status/").status_code == 404
    s = User.objects.create_user("s@example.org", "pw-Testing-123")
    s.is_superuser = True
    s.save()
    c.force_login(s)
    body = c.get("/ops/status/").content.decode()
    assert "ops-selfcheck" in body and "jobs:stale" in body and "Email delivery" in body
    assert "<strong>on</strong>" in body


def test_setting_change_from_the_admin_is_audited():
    from django.contrib.admin.sites import AdminSite
    from django.test import RequestFactory

    from apps.ops.admin import ClubSettingAdmin
    from apps.ops.config import set_setting

    s = User.objects.create_user("s@example.org", "pw-Testing-123")
    s.is_superuser = True
    s.save()
    row = set_setting(s, "defaults.email_delivery", "off")
    assert row.source == "interface"
    row.value = "on"
    req = RequestFactory().post("/admin/")
    req.user = s
    ClubSettingAdmin(ClubSetting, AdminSite()).save_model(req, row, None, change=True)
    entries = AuditLog.objects.filter(action="setting.changed", subject_id=str(row.pk)).order_by(
        "at"
    )
    assert entries.count() == 2
    assert entries.last().before == {"value": "off"} and entries.last().after == {"value": "on"}
