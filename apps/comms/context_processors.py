"""The unread-message count for the sidebar badge (FR-108)."""

from .models import Outbox


def unread(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    return {"unread_count": Outbox.objects.filter(user=user, read_at__isnull=True).count()}
