"""The JSON API (TR-8): a thin client of the same service layer as the templates."""

from ninja import NinjaAPI, Schema
from ninja.security import django_auth

from apps.events.models import Event

api = NinjaAPI(title="Club Operations API", version="1", urls_namespace="api")


class EventOut(Schema):
    id: int
    title: str
    type: str
    state: str
    starts_at: str | None
    ends_at: str | None


@api.get("/ping")
def ping(request):
    return {"ok": True}


@api.get("/events", response=list[EventOut], auth=django_auth)
def list_events(request):
    out = []
    for e in Event.objects.filter(state__in=["published", "locked", "completed"]).order_by("id"):
        s, en = e.starts_at(), e.ends_at()
        out.append(
            EventOut(
                id=e.id,
                title=e.title,
                type=e.type,
                state=e.state,
                starts_at=s.isoformat() if s else None,
                ends_at=en.isoformat() if en else None,
            )
        )
    return out
