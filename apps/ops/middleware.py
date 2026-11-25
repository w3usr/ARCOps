"""An htmx request that is redirected anywhere but to a slot leaves the dialog for that page.

htmx follows a redirect itself and swaps what it finds into the roster's slot dialog. That is
right when the redirect leads back to the slot, whose view answers htmx with the slot alone, and
wrong for any other page: a whole page would land inside the dialog. The roster after a slot is
canceled, a minor's adults page after signing up, the sign-in page after a session ends: each
becomes a full page load instead (htmx's HX-Redirect), and the flash messages, not yet shown,
are shown there.
"""

import logging
import time
from urllib.parse import urlsplit

from django.http import HttpResponse
from django.urls import Resolver404, resolve

STAYS_IN_PLACE = {"slot_detail", "event_step"}  # event_step: a step's own forms


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


class ViewerZoneMiddleware:
    """Pages read in the viewer's own time zone (functional addendum A38): the browser names it
    in the `tz` cookie (static/js/app.js); before it has, or for a name this server does not
    know, the club's zone. Storage and logic stay UTC; only what a page prints moves."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from zoneinfo import ZoneInfo

        from django.utils import timezone

        from .config import setting

        zone = ZoneInfo("UTC")
        for name in (request.COOKIES.get("tz", "")[:64], setting("club.timezone", "UTC")):
            try:
                zone = ZoneInfo(name)
                break
            except Exception:  # noqa: BLE001, S112 - an unknown or malformed name: try the next
                continue
        with timezone.override(zone):
            return self.get_response(request)


request_log = logging.getLogger("ops.request")


class RequestLogMiddleware:
    """One JSON line per request (TR-33). It names the route a request matched, not its path: a
    path can carry an invitation's or a sign-up's token, and a log line holds no more about a
    person than their account id. A request no route matched (a static file, a stray URL) gives
    its path, which carries no token."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = time.monotonic()
        response = self.get_response(request)
        match = getattr(request, "resolver_match", None)
        user = getattr(request, "user", None)
        fields = {
            "method": request.method,
            "route": f"/{match.route}" if match else request.path,
            "status": response.status_code,
            "ms": round((time.monotonic() - started) * 1000),
            "user": user.pk if user is not None and user.is_authenticated else None,
        }
        request_log.info("request", extra={"fields": fields})
        return response
