"""Manage's small forms, each a page of its own that Manage opens in a dialog (#168).

A button on a Manage tab is a link to the form's page. With JavaScript, htmx fetches the same URL
into Manage's dialog instead (`HX-Request`), and the form posts back to it there: a refusal comes
back inside the dialog with everything typed, and a save tells htmx to load the tab (`HX-Redirect`),
so the tab shows the change and its message just as it does without JavaScript, where the link
opens the page, the form posts, and the page redirects (docs/INTERFACE.md, In place, with htmx).
"""

from __future__ import annotations

from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.cache import patch_vary_headers


def tab_url(pk, tab) -> str:
    return reverse("event_manage_tab", args=[pk, tab])


def form_page(
    request,
    event,
    form,
    *,
    heading,
    submit,
    tab,
    fields="events/forms/_fields.html",
    actions=None,
    **extra,
):
    """The form on its own page, or, for htmx, only what goes inside the dialog."""
    partial = bool(request.headers.get("HX-Request"))
    response = render(
        request,
        "events/manage_form.html",
        {
            "event": event,
            "form": form,
            "heading": heading,
            "submit": submit,
            "back": tab_url(event.pk, tab),
            "fields_template": fields,
            "actions_template": actions,
            "partial": partial,
            "base_template": "events/_dialog_base.html" if partial else "base.html",
            **extra,
        },
    )
    patch_vary_headers(response, ["HX-Request"])  # one URL, two answers: never cache one for both
    return response


def done(request, url):
    """After a save, back to `url`: a redirect, or from the dialog an instruction to htmx to load
    it, so the page behind shows what changed."""
    if request.headers.get("HX-Request"):
        response = HttpResponse()
        response["HX-Redirect"] = url
        return response
    return redirect(url)
