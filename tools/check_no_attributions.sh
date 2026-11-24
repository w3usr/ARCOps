#!/usr/bin/env bash
# Comments and docstrings state what the code does and why, and cite only the project's public
# records (FR-n, TR-n, an addendum's A-n, docs/INTERFACE.md). Who decided, when, and in what
# words belongs to the decision record, not to the code: a club that installs ARCOps reads the
# rule, and the record keeps the reasoning. This refuses the forms an attribution takes: initials
# or a role with a date, a dated note, a private tracker's number, a bare issue number, a test-plan scenario.
set -uo pipefail
cd "$(dirname "$0")/.."
python3 - <<'PY'
import pathlib, re, sys

RULES = [
    ("an attribution", re.compile(r"\b(?:[A-Z]{2,4}|[Tt]he advisor)(?:'s)?,? (?:on )?20\d\d-\d\d-\d\d")),
    ("a dated note", re.compile(
        r"\([^()]*\b20\d\d-\d\d-\d\d\)"
        r"|\b(?:[Ss]ince|[Uu]ntil|[Bb]efore|[Ff]ound|[Oo]bserved|[Rr]eported|amended) 20\d\d-\d\d-\d\d")),
    ("a private tracker", re.compile(r"[Pp]rivate tracker")),
    ("an issue number", re.compile(r"(?<![\w&#'\"])#\d{2,4}\b(?![;'\"])")),
    ("a test-plan scenario", re.compile(r"\bT[1-9]\d{0,2}(?= step|,|:| to T\d|\))")),
]
ROOTS = ["apps", "config", "templates", "static", "tools", ".github", "pyproject.toml"]
SKIP = {"static/js/vendor", "tools/a11y/axe.min.js", "tools/check_no_attributions.sh"}
TYPES = {".py", ".html", ".css", ".js", ".sh", ".yml", ".yaml", ".toml", ".txt"}
fail = False

for root in ROOTS:
    base = pathlib.Path(root)
    for path in [base] if base.is_file() else sorted(base.rglob("*")):
        rel = path.as_posix()
        if path.suffix not in TYPES or any(rel.startswith(s) for s in SKIP):
            continue
        if "migrations" in path.parts:  # the schema's history, written as it was
            continue
        for n, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            if re.search(r":\s*#[0-9a-fA-F]{3,8}\b", line):  # a CSS color, not an issue
                continue
            for what, pattern in RULES:
                if pattern.search(line):
                    print(f"{rel}:{n}: {what}: {line.strip()[:110]}")
                    fail = True
                    break

if fail:
    print("State the rule, and cite the FR, TR or addendum entry instead.")
    sys.exit(1)
print("no-attributions: ok")
PY
