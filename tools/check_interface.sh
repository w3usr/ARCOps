#!/usr/bin/env bash
# The parts of docs/INTERFACE.md a grep can check.
#
# Four rules, each of which was a real fault before it was a rule: a table cell with no
# data-label loses its meaning when the table stacks on a phone; a title attribute is invisible
# on a phone and to the keyboard, so it is never the only explanation; an inline event handler
# is dead under the content security policy; and a British spelling is not the house spelling.
# A fifth keeps type to its five sizes and two weights, and corners to their three.
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
# proofread. The same goes for the HTML attribute aria-labelledby. Each identifier is blanked
# out of the line before the line is checked, so a line carrying both a state key and visible
# text is still checked for the visible text. Exempting the whole line let
# <span class="tag">Cancelled</span> sit beside state == 'cancelled' unseen.
IDENTIFIER = re.compile(
    r"'cancelled'|\"cancelled\"|\bcancelled\s*=|\.cancelled\b|\bcancelled__|labelledby"
)

fail = []

for path in sorted(pathlib.Path("templates").rglob("*.html")):
    raw = path.read_text()
    text = COMMENTS.sub("", raw)

    # A page stacks on a phone; a document rendered to paper does not, and a data-label in one
    # would be noise nobody ever sees (the signed agreement's record of decisions, 2026-09-20).
    prints_only = path.name.endswith("_pdf.html")

    for table in TABLE.finditer(text):
        body = table.group(0)
        if prints_only or "<thead" not in body:
            continue  # no header row for a stacked cell to lose, or nothing that stacks
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

# A choice's label reaches the page through get_<field>_display, which no template
# spells out, so the models' labels are read too.
LABEL = re.compile(r'^\s*[A-Z_]+\s*=\s*"[^"]*",\s*"([^"]*)"')
for path in sorted(pathlib.Path("apps").glob("*/models.py")):
    for n, line in enumerate(path.read_text().splitlines(), 1):
        label = LABEL.match(line)
        hit = label and BRITISH.search(label.group(1))
        if hit:
            fail.append(f"{path}:{n}: {hit.group(0)!r}; the house spelling is American")

# A field with a default shows it filled in, never help text saying a blank box means it.
# Templates and the application's Python, not tests or old migrations.
BLANK_MEANS = re.compile(r"Left blank|Blank uses|Nothing set means", re.I)
for path in sorted(pathlib.Path("templates").rglob("*.html")) + sorted(pathlib.Path("apps").rglob("*.py")):
    if "tests" in path.parts or "migrations" in path.parts:
        continue
    for n, line in enumerate(path.read_text().splitlines(), 1):
        hit = BLANK_MEANS.search(line)
        if hit:
            fail.append(f"{path}:{n}: {hit.group(0)!r}; show the default filled in instead")

# Five sizes of type and two weights (docs/INTERFACE.md, "Type"). A sixth size crept in one
# rule at a time until the stylesheet had seventeen.
SIZE = re.compile(r"font-size:\s*([^;}]+)")
WEIGHT = re.compile(r"font-weight:\s*([^;}]+)")
SIZES = {f"var(--t-{t})" for t in ("small", "body", "lede", "h2", "h1")} | {"inherit"}
WEIGHTS = {"400", "700", "inherit"}
# Three corners by hierarchy (docs/INTERFACE.md, "Shape"), and a circle.
RADIUS = re.compile(r"border-radius:\s*([^;}]+)")
RADII = {f"var(--r-{t})" for t in ("field", "button", "card")} | {"50%"}
# The one exception, the navigation's pill (2026-11-11): its entries, and a switch's
# choices, whose current one is where you are (2026-11-12).
PILL, PILL_RULE = "var(--r-pill)", (".navlist a, .navbtn {", ".switch a {")
for path in [*sorted(pathlib.Path("static/css").glob("*.css")), *sorted(pathlib.Path("templates").rglob("*.html"))]:
    if "email" in path.parts or path.name.endswith("_pdf.html"):
        continue  # mail and PDFs have their own type; neither loads the stylesheets
    rule = ""  # the selector of the rule a line sits in, all of its lines joined
    parts = []  # a selector list's lines before the one with "{"
    for n, line in enumerate(path.read_text().splitlines(), 1):
        if "{" in line:
            rule, parts = " ".join([*parts, line.strip()]), []
        elif line.rstrip().endswith(","):
            parts.append(line.strip())
        else:
            parts = []
        for m in SIZE.finditer(line):
            if m.group(1).strip() not in SIZES:
                fail.append(f"{path}:{n}: font-size {m.group(1).strip()}; use one of var(--t-small|body|lede|h2|h1)")
        for m in WEIGHT.finditer(line):
            if m.group(1).strip() not in WEIGHTS:
                fail.append(f"{path}:{n}: font-weight {m.group(1).strip()}; the face has 400 and 700")
        for m in RADIUS.finditer(line):
            # One corner token, or a list of the same tokens and 0: a panel's footer rounds only
  # its foot, and a part set flush inside a panel is square.
            pill = {PILL} if rule.startswith(PILL_RULE) else set()
            if not set(m.group(1).split()) <= RADII | {"0"} | pill:
                fail.append(f"{path}:{n}: border-radius {m.group(1).strip()}; use var(--r-field|button|card), or 50% for a circle")

# Nine steps of space on a 4px grid (docs/INTERFACE.md, "Shape"): every
# margin, padding and gap is a --space token, 0 or auto. em is allowed, being space relative to
# the text beside it; so are vw and % (a share of the window, as in a clamp()) and env() for a
# phone's safe areas. A whole declaration is read, since
# Prettier wraps a long one over two lines.
SPACING = re.compile(r"(?<![\w-])((?:margin|padding)(?:-[a-z-]+)?|(?:row-|column-)?gap)\s*:\s*([^;{}]+);")
SPACE_OK = re.compile(r"var\(--space-[1-9]\)|env\([^()]*\)|-?\d*\.?\d+(?:em|vw|vh|svh|%)(?![\w-])|\bauto\b|\bcalc\b|\bclamp\b|\b0\b|-1|[()*+,\s]")
# The one exception: the 2px between the coverage strip's hour marks, a hairline rather than space.
SPACE_EXCEPT = {("roster.css", ".strip-marks", "2px")}
for path in sorted(pathlib.Path("static/css").glob("*.css")):
    text = re.sub(r"/\*.*?\*/", lambda c: re.sub(r"[^\n]", " ", c.group(0)), path.read_text(), flags=re.S)
    for m in SPACING.finditer(text):
        rest = SPACE_OK.sub("", m.group(2)).strip()
        if not rest:
            continue
        n = text.count("\n", 0, m.start()) + 1
        rule = text[: m.start()].rsplit("}", 1)[-1].split("{", 1)[0].strip()
        rule = " ".join(rule.split())
        if (path.name, rule, m.group(2).strip()) in SPACE_EXCEPT:
            continue
        fail.append(f"{path}:{n}: {m.group(1)}: {m.group(2).strip()}; use var(--space-1..9), 0 or auto")

# One form for every UTC date and time (#274; apps/ops/when.py): a template or a module writing
# its own with a clock in it drifts from the rest, as a dozen of them had. ISO 8601 for machines
# (value=, CSV, the calendar feed, the audit log), a line marked "# machine", and one marked
# "# allowed:" with its reason are let through.
DATE_TIME = re.compile(r"""\|date:(["'])([^"']*H:i[^"']*)\1""")
for path in sorted(pathlib.Path("templates").rglob("*.html")):
    for n, line in enumerate(path.read_text().splitlines(), 1):
        for m in DATE_TIME.finditer(line):
            if not m.group(2).startswith("Y-m-d"):
                fail.append(f"{path}:{n}: |date:\"{m.group(2)}\"; use |utc_time, |utc_time_short or {{% utc_span %}}")
for path in sorted(pathlib.Path("apps").rglob("*.py")):
    if "/tests/" in str(path) or "/migrations/" in str(path) or path.name == "when.py":
        continue
    for n, line in enumerate(path.read_text().splitlines(), 1):
        if "%H:%M" in line and "%Y" not in line and "# machine" not in line and "# allowed:" not in line:
            fail.append(f"{path}:{n}: a hand-written time format; use apps/ops/when.py")

for line in dict.fromkeys(fail):
    print(line)
if fail:
    sys.exit(1)
print("interface: ok")
PY
