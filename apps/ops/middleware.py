"""An htmx request that is redirected anywhere but to a slot leaves the dialog for that page.

htmx follows a redirect itself and swaps what it finds into the roster's slot dialog. That is
right when the redirect leads back to the slot, whose view answers htmx with the slot alone, and
wrong for any other page: a whole page would land inside the dialog. The roster after a slot is
canceled, a minor's adults page after signing up, the sign-in page after a session ends: each
becomes a full page load instead (htmx's HX-Redirect), and the flash messages, not yet shown,
are shown there (#139).
"""

from urllib.parse import urlsplit

from django.http import HttpResponse
from django.urls import Resolver404, resolve

STAYS_IN_PLACE = {"slot_detail"}


class HtmxRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not request.headers.get("HX-Request") or response.status_code not in (301, 302, 303):
            return response
        location = response["Location"]
        try:
            if resolve(urlsplit(location).path).url_name in STAYS_IN_PLACE:
                return response
        except Resolver404:
            pass
        page = HttpResponse()
        page["HX-Redirect"] = location
        return page
