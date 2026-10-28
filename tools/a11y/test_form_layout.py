"""A label sits above its field, and the inputs of a row of fields line up (#140, #141).

Found on the contact sheet: on Manage event a label that wrapped to two lines pushed its input a
line below the rest of the row, and the slot page put some labels beside their fields and others
above them. Measured in a real browser, at desktop width, where both showed.
"""

import pytest
from playwright.sync_api import sync_playwright
from test_axe import ACCOUNTS, sign_in  # the sweep lives beside this file

pytestmark = pytest.mark.django_db(transaction=True)

# A label beside its field ends below the field's top edge. Checkboxes and radios are the
# exception INTERFACE.md allows: the box goes before its label. A label only a screen reader
# reads, and a field an editor stands in for, have no place on the page to compare.
BESIDE = """() => [...document.querySelectorAll('main label[for]:not(.sr-only)')].filter(l => l.offsetParent).flatMap(l => {
    const f = document.getElementById(l.htmlFor);
    if (!f || !f.offsetParent || f.matches('[type=checkbox], [type=radio]')) return [];
    return l.getBoundingClientRect().bottom > f.getBoundingClientRect().top + 1 ? [l.textContent.trim()] : [];
})"""

# In a row of fields that are each a label and an input (a row with help or checkboxes stays
# top-aligned, as app.css says), the inputs on one line share a middle:
# an engine draws a select shorter than a text box, so their edges need not meet.
UNEVEN = """() => [...document.querySelectorAll('main .row:not(:has(.helptext, .check, .errorlist))')].filter(r => r.offsetParent).flatMap(r => {
    const lines = [];  // the fields of one wrapped line overlap each other from top to bottom
    for (const f of r.children) {
        const input = f.querySelector('input:not([type=checkbox]):not([type=radio]), select, textarea');
        if (!input) continue;
        const box = f.getBoundingClientRect(), i = input.getBoundingClientRect();
        let line = lines.find(l => box.top < l.bottom && box.bottom > l.top);
        if (!line) lines.push(line = {top: box.top, bottom: box.bottom, fields: []});
        line.fields.push([f.querySelector('label')?.textContent.trim(), Math.round((i.top + i.bottom) / 2)]);
    }
    return lines.map(l => l.fields).filter(fs => Math.max(...fs.map(f => f[1])) - Math.min(...fs.map(f => f[1])) > 4);
})"""


# A select is as tall as a text box. WebKit drew a select at 23px beside a 44px text box until the
# page drew it instead of the system.
SHORT = """() => {
    const box = document.querySelector('main input[type=text]:not([hidden]), main input:not([type])');
    const h = box && box.getBoundingClientRect().height;
    return h ? [...document.querySelectorAll('main select:not([multiple])')].filter(s => s.offsetParent)
        .map(s => [s.id || s.name, Math.round(s.getBoundingClientRect().height)]).filter(s => Math.abs(s[1] - h) > 2) : [];
}"""


def test_labels_above_fields_and_rows_level(live_server, engine):
    from apps.events.models import Event, Slot

    ev = Event.objects.order_by("pk").first()
    slot = Slot.objects.filter(position__location__event=ev, kind="operating").order_by("start")
    urls = [f"/events/{ev.pk}/manage/", f"/events/{ev.pk}/slot/{slot.first().pk}/"]
    found = []
    with sync_playwright() as p:
        browser = getattr(p, engine).launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        sign_in(page, live_server.url, ACCOUNTS["officer"])
        for url in urls:
            page.goto(f"{live_server.url}{url}")
            found += [(url, "beside", t) for t in page.evaluate(BESIDE)]
            found += [(url, "uneven", r) for r in page.evaluate(UNEVEN)]
            found += [(url, "short select", s) for s in page.evaluate(SHORT)]
        browser.close()

    assert not found, f"labels beside their fields, rows not level, or short selects: {found}"
