"""backup:nightly (TR-22). A stand-in `age` that passes the tar through unencrypted lets the test
open what was written; the real `age` is proved by the restore rehearsal on the server."""

import hashlib
import io
import os
import sqlite3
import tarfile
from datetime import UTC, datetime

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from apps.accounts.models import User
from apps.ops.models import JobRun

pytestmark = pytest.mark.django_db

FAKE_AGE = '#!/bin/sh\n[ "$3" = age1fixture ] || exit 9\ncat\n'


@pytest.fixture
def fake_age(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "age").write_text(FAKE_AGE)
    (bin_dir / "age").chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ['PATH']}")
    out = tmp_path / "backup"
    out.mkdir()
    media = tmp_path / "media"
    (media / "agreements").mkdir(parents=True)
    (media / "agreements" / "signed.pdf").write_bytes(b"%PDF-fixture")
    with override_settings(
        BACKUP_DIR=out,
        BACKUP_AGE_RECIPIENT="age1fixture",
        BACKUP_NAME="ops_fixture_backup",
        MEDIA_ROOT=media,
    ):
        yield out


@pytest.mark.django_db(
    transaction=True
)  # VACUUM INTO refuses to run in a transaction; the job runs in none
def test_the_archive_holds_the_database_and_media_verifies_and_old_ones_go(fake_age, tmp_path):
    User.objects.create_user(email="kept@example.org", password="x" * 16)
    old = fake_age / "20260101_0230UT_ops_fixture_backup.tar.age"
    old.write_bytes(b"old")
    (fake_age / (old.name + ".sha256")).write_text("x")
    other = fake_age / "20260101_notes.txt"  # not ours: left alone
    other.write_text("")

    call_command("backup_nightly", now="2026-11-13T02:30:00+00:00")

    name = "20261113_0230UT_ops_fixture_backup.tar.age"
    archive = fake_age / name
    assert sorted(p.name for p in fake_age.iterdir()) == sorted(
        [name, name + ".sha256", other.name]
    )
    digest, listed = (fake_age / (name + ".sha256")).read_text().split()
    assert listed == name and digest == hashlib.sha256(archive.read_bytes()).hexdigest()
    assert archive.stat().st_mode & 0o777 == 0o640
    with tarfile.open(fileobj=io.BytesIO(archive.read_bytes())) as tar:
        assert tar.extractfile("media/agreements/signed.pdf").read() == b"%PDF-fixture"
        tar.extract("ops.sqlite3", tmp_path / "restore", filter="data")
    with sqlite3.connect(tmp_path / "restore" / "ops.sqlite3") as db:
        tables = {r[0] for r in db.execute("select name from sqlite_master where type='table'")}
    assert User._meta.db_table in tables
    run = JobRun.objects.get(name="backup:nightly")
    assert run.outcome == "ok" and run.detail["removed"] == 2


def test_no_recipient_fails_the_job_and_writes_nothing(fake_age):
    with override_settings(BACKUP_AGE_RECIPIENT=""), pytest.raises(CommandError):
        call_command("backup_nightly")
    assert list(fake_age.iterdir()) == []
    assert JobRun.objects.get(name="backup:nightly").outcome != "ok"


def test_a_failed_encryption_leaves_no_partial_file(fake_age):
    with override_settings(BACKUP_AGE_RECIPIENT="age1wrong"), pytest.raises(CommandError):
        call_command("backup_nightly", now=datetime(2026, 11, 13, tzinfo=UTC).isoformat())
    assert list(fake_age.iterdir()) == []
