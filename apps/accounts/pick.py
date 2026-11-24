"""Choosing one member by typing part of a name or callsign.

A drop-down of the whole membership does not last as the club grows, so a form that asks for a
member carries `templates/_member_pick.html`: a search box, and the few people who match as
choices. The page that holds the form answers `?q=` with those matches. Without script, **Find**
posts, and the view sends the browser back to its page with `?q=`; with script, htmx asks for
the same page as the officer types and keeps only the matches. One server path serves both.
"""

from __future__ import annotations

from urllib.parse import urlencode

from django.db.models import Q
from django.db.models.functions import Lower
from django.shortcuts import redirect

SHOWN = 8


def matches(people, q: str, keep=None):
    """Up to SHOWN of `people` holding every typed word in a name or the callsign, any case,
    and whether more match. `keep`, if given, is a test each must also pass (a role's rule)."""
    words = q.split()
    if not words:
        return [], False
    for w in words:
        people = people.filter(
            Q(first_name__icontains=w)
            | Q(last_name__icontains=w)
            | Q(preferred_name__icontains=w)
            | Q(callsign__icontains=w)
        )
    found = []
    for person in people.order_by(Lower("last_name"), Lower("first_name"), "pk"):
        if keep is None or keep(person):
            found.append(person)
            if len(found) > SHOWN:
                break
    return found[:SHOWN], len(found) > SHOWN


def find_redirect(request, url: str, *keep: str):
    """Find, pressed with script off: back to the form's page with what was typed (and `keep`,
    e.g. the role), so the page lists the matches."""
    params = {k: request.POST[k] for k in ("q", *keep) if request.POST.get(k)}
    return redirect(f"{url}?{urlencode(params)}")
