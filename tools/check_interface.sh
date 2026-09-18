#!/usr/bin/env bash
# The parts of docs/INTERFACE.md a grep can check.
#
# Four rules, each of which was a real fault before it was a rule: a table cell with no
# data-label loses its meaning when the table stacks on a phone; a title attribute is invisible
# on a phone and to the keyboard, so it is never the only explanation; an inline event handler
# is dead under the content security policy; and a British spelling is not the house spelling.
set -uo pipefail
cd "$(dirname "$0")/.."
python3 - <<'PY'
import pathlib, re, sys

COMMENTS = re.compile(r"\{%\s*comment\s*%\}.*?\{%\s*endcomment\s*%\}|\{#.*?#\}|<!--.*?-->", re.S)
TABLE = re.compile(r"<table\b[^>]*>.*?</table>", re.S)
ROW = re.compile(r"<tr\b[^>]*>.*?</tr>", re.S)
CELL = re.compile(r"<td\b([^>]*)>")
INLINE_HANDLER = re.compile(r'\son[a-z]+\s*=\s*"')
# Django's {# #} is a single line. Spread over two it is not a comment at all: the opening
# brace and every word of it render onto the page.
OPEN_COMMENT = re.compile(r"\{#(?![^\n]*#\})")
TITLE = re.compile(r'\stitle\s*=\s*"')
BRITISH = re.compile(
    r"\b(colour|licence|organis\w*|authoris\w*|recognis\w*|behaviour|cancelled|cancelling"
    r"|whilst|programme|defence|analyse|grey)\b",
    re.I,
)
# Identifiers keep the spelling they were created with: renaming one is a migration, not a
# proofread. The same goes for the HTML attribute aria-labelledby.
# Identifiers keep the spelling they were created with: renaming one is a migration, not a
# proofread. Each identifier is blanked out of the line before the line is checked, so a line
# carrying both a state key and visible text is still checked for the visible text. Exempting
# the whole line let <span class="tag">Cancelled</span> sit beside state == 'cancelled' unseen.
IDENTIFIER = re.compile(
    r"'cancelled'|\"cancelled\"|\bcancelled\s*=|\.cancelled\b|\bcancelled__|labelledby"
)

fail = []

for path in sorted(pathlib.Path("templates").rglob("*.html")):
    raw = path.read_text()
    text = COMMENTS.sub("", raw)

    for table in TABLE.finditer(text):
        body = table.group(0)
        if "<thead" not in body:
            continue  # no header row for a stacked cell to lose
        for row in ROW.finditer(body[body.index("</thead>"):] if "</thead>" in body else ""):
            for cell in CELL.finditer(row.group(0)):
                attrs = cell.group(1)
                if "data-label" not in attrs and "colspan" not in attrs:
                    fail.append(f"{path}: a <td> with no data-label; it loses its column on a phone")
                    break

    for n, line in enumerate(raw.splitlines(), 1):
        if OPEN_COMMENT.search(line):
            fail.append(f"{path}:{n}: a {{# #}} comment running past one line; it renders as text")

    for n, line in enumerate(text.splitlines(), 1):
        if INLINE_HANDLER.search(line):
            fail.append(f"{path}:{n}: an inline event handler, which the policy blocks")
        if TITLE.search(line) and "block title" not in line:
            fail.append(f"{path}:{n}: a title attribute; put the words on the page instead")
        hit = BRITISH.search(IDENTIFIER.sub("", line))
        if hit:
            fail.append(f"{path}:{n}: {hit.group(0)!r}; the house spelling is American")

for path in sorted(pathlib.Path("static/css").rglob("*.css")) + sorted(
    pathlib.Path("static/js").rglob("*.js")
):
    if path.name.endswith(".min.js"):
        continue  # vendored
    for n, line in enumerate(path.read_text().splitlines(), 1):
        hit = BRITISH.search(IDENTIFIER.sub("", line))
        if hit:
            fail.append(f"{path}:{n}: {hit.group(0)!r}; the house spelling is American")

for line in dict.fromkeys(fail):
    print(line)
if fail:
    sys.exit(1)
print("interface: ok")
PY
