#!/usr/bin/env bash
# Requirement identifiers (FR-7, TR-28, §2.4) are how this project's documents refer to
# themselves. They mean nothing to a member reading a page, so they never appear in the
# interface. Code comments, docstrings, and template comments keep them: that is where they
# earn their place. This checks the text a browser renders and the strings a form shows.
set -uo pipefail
cd "$(dirname "$0")/.."
python3 - <<'PY'
import io, pathlib, re, sys, tokenize

PATTERN = re.compile(r"(FR|TR)-\d|§\d")
COMMENTS = re.compile(r"\{%\s*comment\s*%\}.*?\{%\s*endcomment\s*%\}|\{#.*?#\}|<!--.*?-->", re.S)
# The strings a person reads, rather than every string in the file.
FACING = re.compile(r"help_text=|label=|\.label =|\.help_text =|messages\.(success|error|info|warning)|ValidationError")
fail = False

for path in sorted(pathlib.Path("templates").rglob("*.html")):
    for n, line in enumerate(COMMENTS.sub("", path.read_text()).splitlines(), 1):
        if PATTERN.search(line):
            print(f"Requirement identifier in rendered text, {path}:{n}: {line.strip()[:120]}")
            fail = True

for path in sorted(pathlib.Path("apps").rglob("*.py")):
    if "migrations" in path.parts:  # a historical record, never shown to anyone
        continue
    src = path.read_text()
    try:  # drop comments, so an explanatory "# FR-115" beside a label is not a hit
        bare = tokenize.untokenize(
            t for t in tokenize.generate_tokens(io.StringIO(src).readline)
            if t.type != tokenize.COMMENT
        )
    except (tokenize.TokenError, IndentationError):
        bare = src
    for n, line in enumerate(bare.splitlines(), 1):
        if FACING.search(line) and PATTERN.search(line):
            print(f"Requirement identifier in a user-facing string, {path}: {line.strip()[:120]}")
            fail = True

if fail:
    sys.exit(1)
print("no-requirement-ids: ok")
PY
