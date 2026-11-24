"""Compare two page snapshots (test_page_snapshot.py): every page that draws differently.

    python tools/a11y/compare_snapshots.py BEFORE_DIR AFTER_DIR

Text that differs between any two runs (clock times, the test server's port, tokens, "n minutes
ago") is normalized first. A box that moved on a page whose raw text differs is counted apart,
since a longer time or token can move what follows it. Exits 1 when any page differs.
"""

import difflib
import json
import re
import sys
from pathlib import Path

NOISE = [
    (re.compile(r"\b\d{1,2}:\d\d(\s?[AP]M)?\b"), "T"),
    (re.compile(r"localhost:\d+"), "HOST"),
    (re.compile(r"[A-Za-z0-9_-]{25,}"), "TOKEN"),
    (re.compile(r"\b\d+ (minute|second)s? ago\b"), "AGO"),
]


def norm(text: str) -> str:
    for rx, sub in NOISE:
        text = rx.sub(sub, text)
    return text


def compare(a: Path, b: Path) -> int:
    pages = real = 0
    noisy = []
    for fa in sorted(a.glob("*.json")):
        before = json.loads(fa.read_text())
        after = json.loads((b / fa.name).read_text())
        for key in sorted(set(before) | set(after)):
            pages += 1
            x, y = before.get(key), after.get(key)
            if x is None or y is None:
                real += 1
                print(f"{fa.stem} {key}: on one side only")
                continue
            why = []
            nx, ny = norm(x["text"]), norm(y["text"])
            if nx != ny:
                lines = difflib.unified_diff(nx.splitlines(), ny.splitlines(), lineterm="", n=0)
                d = [ln for ln in lines if ln[:1] in "+-" and ln[:3] not in ("+++", "---")]
                why.append("text: " + " | ".join(d[:4]))
            if len(x["els"]) != len(y["els"]):
                why.append(f"elements {len(x['els'])} vs {len(y['els'])}")
            else:
                pairs = list(zip(x["els"], y["els"], strict=True))
                style = [e[0] for e, f in pairs if e[1] != f[1]]
                box = [(e[0], e[2], f[2]) for e, f in pairs if e[2] != f[2]]
                if style:
                    why.append(f"style {len(style)}, first {style[0]}")
                if box and x["text"] == y["text"]:
                    why.append(f"box {len(box)}, first {box[0]}")
                elif box:
                    noisy.append(f"{fa.stem} {key} ({len(box)})")
            if why:
                real += 1
                print(f"{fa.stem} {key}: " + "; ".join(why)[:500])
    print(f"{real} of {pages} pages differ; {len(noisy)} more moved beside changed text")
    for n in noisy:
        print(f"  moved beside changed text: {n}")
    return 1 if real else 0


if __name__ == "__main__":
    sys.exit(compare(Path(sys.argv[1]), Path(sys.argv[2])))
