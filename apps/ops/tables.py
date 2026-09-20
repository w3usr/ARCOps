"""Sorting and narrowing a table, the way the members directory does it.

The directory grew a sortable heading, filter panels whose summaries say what is narrowed, and a
query string that survives both. The access rosters then needed the same, and the approvals log
after that, so the three or four lines that are genuinely shared live here rather than being
copied a third time.

What is deliberately **not** here: which columns a page has, what its filters mean, and how a row
is fetched. Those are the page's own, and a generic table builder that tried to own them would be
harder to read than the pages it replaced.

Everything is plain GET, so sorting and narrowing work without JavaScript and survive a bookmark
(TR-4).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable


def chosen(request, *names: str) -> dict[str, list[str]]:
    """What each filter panel has ticked, as `{name: [values]}`.

    An empty list means the filter is off, which is the convention every panel follows: a panel
    nobody has touched narrows nothing (`docs/INTERFACE.md`).
    """
    return {name: request.GET.getlist(name) for name in names}


def summary(choices: Iterable[tuple[str, str]], ticked: Iterable[str], label: str) -> str:
    """What a filter panel says while it is shut, so a narrowed table says so unopened."""
    choices = list(choices)
    names = [text for key, text in choices if key in set(ticked)]
    if not names or len(names) == len(choices):
        return f"Any {label}"
    return ", ".join(names) if len(names) < 3 else f"{len(names)} {label}s"


def sorted_columns(
    request,
    columns: list[dict],
    keys: dict[str, Callable],
    default: str,
) -> tuple[str, bool, list[dict]]:
    """Read `?sort=` and `?dir=`, and build the heading links.

    Returns the column key in force, whether it is descending, and the columns with the `url`,
    `here` and `aria` the heading template needs. Each link carries the **whole** query string
    forward, so clicking a heading keeps the search and every filter; `page` is dropped, because
    a re-sorted table starts again at the top.
    """
    sort = request.GET.get("sort", default)
    if sort not in keys or sort not in {c["key"] for c in columns}:
        sort = default
    descending = request.GET.get("dir") == "desc"

    built = []
    for column in columns:
        here = column["key"] == sort
        params = request.GET.copy()
        params["sort"] = column["key"]
        # Clicking the column you are already sorted by turns it round.
        params["dir"] = "desc" if here and not descending else "asc"
        params.pop("page", None)
        built.append(
            {
                **column,
                "url": f"?{params.urlencode()}",
                "here": here,
                "aria": ("descending" if descending else "ascending") if here else "none",
            }
        )
    return sort, descending, built


def export_url(request, **extra: str) -> str:
    """The same query string with `format=csv` on it, so a download is what is on screen.

    Hand-built export links quietly ignored every filter but the one somebody remembered to put
    in the template (found on the access rosters, 2026-09-20).
    """
    params = request.GET.copy()
    params.pop("page", None)
    for key, value in extra.items():
        params[key] = value
    params["format"] = "csv"
    return f"?{params.urlencode()}"
