"""Buttons that look like buttons (#225, D2 and D3): every button in the page content is at least
24 px each way (WCAG 2.5.8), and a neutral outline reads at 3:1 against what it stands on
(WCAG 1.4.11), measured in a real browser in each engine on the pages that carry the most."""

from playwright.sync_api import sync_playwright
from test_axe import ACCOUNTS, sign_in  # the sweep lives beside this file

PAGES = (
    "/events/1/",
    "/events/1/manage/slots/",
    "/events/1/manage/locations/",
    "/events/1/manage/publish/",
    "/members/",
    "/me/",
)

# A button in a line of text (.linklike) is exempt from the size, as 2.5.8 allows for inline
# targets; everything else is measured. The outline's contrast is against the first ancestor
# with a background of its own.
MEASURE = """() => {
  // Any CSS color (an oklab() from color-mix included) to [r, g, b, alpha] through one pixel.
  const px = document.createElement('canvas').getContext('2d', {willReadFrequently: true});
  const rgb = s => { px.clearRect(0, 0, 1, 1); px.fillStyle = s; px.fillRect(0, 0, 1, 1);
                     const d = px.getImageData(0, 0, 1, 1).data; return [d[0], d[1], d[2], d[3] / 255]; };
  const lum = ([r, g, b]) => [r, g, b].map(v => { v /= 255; return v <= .03928 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4; })
                                     .reduce((t, v, i) => t + v * [.2126, .7152, .0722][i], 0);
  const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + .05) / (y + .05); };
  const ground = el => { for (let e = el.parentElement; e; e = e.parentElement) {
      const c = rgb(getComputedStyle(e).backgroundColor); if (c[3] > 0) return c; }
    return [255, 255, 255]; };
  const bad = [];
  for (const b of document.querySelectorAll('main a.button, main button:not(.linklike)')) {
    if (b.offsetParent === null) continue;
    const r = b.getBoundingClientRect(), name = b.textContent.trim().replace(/\\s+/g, ' ') || b.getAttribute('aria-label');
    if (r.width < 24 || r.height < 24) bad.push(`${name}: ${Math.round(r.width)}x${Math.round(r.height)}`);
    const s = getComputedStyle(b);
    if (b.matches('.secondary, .danger-outline') && parseFloat(s.borderTopWidth) > 0) {
      const k = ratio(rgb(s.borderTopColor), ground(b));
      if (k < 3) bad.push(`${name}: outline ${k.toFixed(2)}:1`);
    }
  }
  return bad;
}"""


def test_buttons_are_big_enough_and_their_outlines_read(live_server, engine):
    with sync_playwright() as p:
        browser = getattr(p, engine).launch()
        found = {}
        for scheme in ("light", "dark"):
            page = browser.new_page(viewport={"width": 1280, "height": 900}, color_scheme=scheme)
            sign_in(page, live_server.url, ACCOUNTS["officer"])
            for path in PAGES:
                page.goto(live_server.url + path)
                if bad := page.evaluate(MEASURE):
                    found[f"{scheme} {path}"] = bad
            page.close()
        browser.close()
    assert not found, found
