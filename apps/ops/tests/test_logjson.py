"""Logs are one JSON object per line, per request and per job (TR-33)."""

import json
import logging
import sys

import pytest
from django.core.management import call_command

from apps import factories as f
from config.logjson import JsonFormatter

pytestmark = pytest.mark.django_db


def _lines(caplog, logger):
    return [json.loads(JsonFormatter().format(r)) for r in caplog.records if r.name == logger]


def test_a_line_is_one_json_object_with_its_fields_and_any_exception():
    try:
        raise ValueError("boom")
    except ValueError:
        record = logging.getLogger("x").makeRecord(
            "x", logging.ERROR, __file__, 1, "went %s", ("wrong",), sys.exc_info()
        )
    record.fields = {"job": "selfcheck"}
    line = JsonFormatter().format(record)
    assert "\n" not in line.split('"exc"')[0]
    data = json.loads(line)
    assert data["msg"] == "went wrong" and data["level"] == "ERROR" and data["job"] == "selfcheck"
    assert "ValueError: boom" in data["exc"]


def test_a_request_is_logged_by_its_route_so_a_token_never_reaches_the_log(client, caplog):
    caplog.set_level(logging.INFO, logger="ops.request")
    client.get("/verify/secret-token-123/")
    (line,) = _lines(caplog, "ops.request")
    assert line["route"] == "/verify/<str:token>/" and line["status"] == 410
    assert line["method"] == "GET" and line["user"] is None and isinstance(line["ms"], int)
    assert "secret-token-123" not in json.dumps(line)


def test_a_signed_in_request_carries_the_account_id_and_nothing_else_about_them(client, caplog):
    u = f.UserFactory(first_name="Robin")
    client.force_login(u)
    caplog.set_level(logging.INFO, logger="ops.request")
    client.get("/events/")
    (line,) = _lines(caplog, "ops.request")
    assert line["user"] == u.pk and line["status"] == 200
    assert "Robin" not in json.dumps(line) and u.email not in json.dumps(line)


def test_a_job_leaves_one_json_line_with_its_outcome(caplog):
    caplog.set_level(logging.INFO, logger="apps.ops.jobs")
    call_command("selfcheck")
    (line,) = _lines(caplog, "apps.ops.jobs")
    assert line["job"] == "selfcheck" and line["outcome"] == "ok" and "detail" in line
