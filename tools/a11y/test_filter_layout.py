"""The filter panels: every row starting at the same edge, box beside word.

NAF, 2026-09-19, on the members list: "Can we get all of these boxes and lists left-justified
like a normal, sane UI?" Measured in a real browser, because this is a layout question and the
markup alone cannot answer it.
"""

from playwright.sync_api import sync_playwright
from test_axe import ACCOUNTS, sign_in  # the sweep lives beside this file


def test_the_filter_rows_line_up_on_the_left(live_server):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        sign_in(page, live_server.url, ACCOUNTS["advisor"])
        page.goto(f"{live_server.url}/members/")
        panels = page.query_selector_all("details.filter")
        assert len(panels) >= 4, "the list carries its filters"
        measured = []
        for n in range(len(panels)):
            page.click(f"details.filter summary >> nth={n}")
            page.wait_for_timeout(50)
            measured.append(
                page.eval_on_selector_all(
                    "details.filter[open] .check",
                    """rows => rows.map(r => {
                        const box = r.querySelector('input').getBoundingClientRect();
                        const label = r.querySelector('label').getBoundingClientRect();
                        return {box: box.x, wide: box.width, label: label.x,
                                beside: label.y - box.y};
                    })""",
                )
            )
        browser.close()

    for rows in measured:
        assert len(rows) >= 2, "each panel opened and holds rows"
        lefts = {round(r["box"]) for r in rows}
        assert len(lefts) == 1, f"every checkbox starts at the same edge, got {sorted(lefts)}"
        # A checkbox stretched by a flex rule is what pushed the labels into a ragged right
        # edge; its own width is the thing to watch (2026-09-19).
        assert all(r["wide"] < 30 for r in rows), "a checkbox is a checkbox, not a stretched box"
        starts = {round(r["label"]) for r in rows}
        assert len(starts) == 1, f"and every label starts at the same edge, got {sorted(starts)}"
        assert all(abs(r["beside"]) < 12 for r in rows), "the label is beside its box, not under"
