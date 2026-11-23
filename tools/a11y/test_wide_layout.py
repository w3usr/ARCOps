"""On a wide screen the page's content stands in the middle of the space beside the sidebar,
not against it (SK, 2026-11-23, from a 2,500 px screen): the column keeps its 72rem measure
and the space left over goes to both sides. A page marked wide still takes the whole width."""

import pytest
from playwright.sync_api import sync_playwright
from test_axe import ACCOUNTS, sign_in  # the sweep lives beside this file

CENTERS = """() => {
  const page = document.querySelector('.page').getBoundingClientRect();
  const main = document.querySelector('main').getBoundingClientRect();
  return {left: main.left - page.left, right: page.right - main.right, width: main.width};
}"""


@pytest.mark.parametrize("width", [1920, 2560])
def test_the_content_is_centered_beside_the_sidebar(live_server, engine, width):
    with sync_playwright() as p:
        browser = getattr(p, engine).launch()
        page = browser.new_page(viewport={"width": width, "height": 900})
        sign_in(page, live_server.url, ACCOUNTS["officer"])
        page.goto(f"{live_server.url}/events/")
        m = page.evaluate(CENTERS)
        browser.close()
    assert m["width"] < width - 400, f"the column keeps its measure: {m}"
    assert abs(m["left"] - m["right"]) <= 1, f"equal space each side: {m}"
