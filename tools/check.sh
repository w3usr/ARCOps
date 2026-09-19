#!/usr/bin/env bash
# Everything CI will run, in about two minutes.
#
# The two test suites are independent of each other, and inside each one the tests are
# independent too: the application tests share nothing, and the accessibility sweep is one
# browser per role, each mostly waiting rather than computing. So both fan out across cores
# (pytest-xdist), and the two run at the same time as each other.
#
#   tools/check.sh          everything
#   tools/check.sh quick    lint, guards, and the application tests; no browser
set -uo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin
QUICK="${1:-}"
fail=0

step() { printf '\n\033[1;35m==> %s\033[0m\n' "$1"; }

step "Lint and format"
$PY/ruff check . && $PY/ruff format --check . || fail=1

step "Repository guards"
for g in check_club_neutral check_no_requirement_ids check_interface; do
    bash "tools/$g.sh" || fail=1
done

step "Migrations are in step with the models"
$PY/python manage.py makemigrations --check --dry-run --settings=config.settings.test || fail=1

if [[ "$QUICK" == "quick" ]]; then
    step "Application tests"
    $PY/python -m pytest apps -q -p no:warnings -n auto || fail=1
else
    step "Application tests and the accessibility sweep, together"
    $PY/python -m pytest apps -q -p no:warnings -n auto > /tmp/arcops-apps.$$ 2>&1 &
    apps=$!
    $PY/python -m pytest tools/a11y -q -p no:warnings -n auto > /tmp/arcops-a11y.$$ 2>&1 &
    a11y=$!
    wait $apps || fail=1
    tail -3 "/tmp/arcops-apps.$$"; rm -f "/tmp/arcops-apps.$$"
    wait $a11y || fail=1
    tail -3 "/tmp/arcops-a11y.$$"; rm -f "/tmp/arcops-a11y.$$"
fi

if (( fail )); then printf '\n\033[1;31msomething failed\033[0m\n'; exit 1; fi
printf '\n\033[1;32mall clear\033[0m\n'
