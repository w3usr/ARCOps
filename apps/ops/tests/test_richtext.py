from apps.ops.templatetags.richtext import richtext, shift_headings


def test_shift_headings_one_level_each():
    assert shift_headings("<h1>A</h1><h2>B</h2><h3>C</h3>") == "<h2>A</h2><h3>B</h3><h4>C</h4>"


def test_richtext_sanitises_and_shifts():
    out = richtext(
        '<h1>T</h1><p onclick="x()">p</p><script>alert(1)</script><a href="https://e.org" target="_blank">l</a>'
    )
    assert (
        "<h2>T</h2>" in out
        and "script" not in out
        and "onclick" not in out
        and 'rel="noopener"' in out
    )
