"""Helpers for resolving which sources a user is allowed to see.

Single source of truth used by both the HTML views and the API so the
permission rule can never drift between them.
"""
from django.db.models import QuerySet

from .models import Source


def visible_source_ids(user) -> set[int]:
    """Return the set of Source ids the given user may view.

    Rules:
    * Anonymous users see nothing.
    * Superusers and staff see every *enabled* source.
    * Regular users see enabled sources for which they hold a
      ``UserSourcePermission`` with ``can_view=True``.
    """
    if not user or not user.is_authenticated:
        return set()

    enabled = Source.objects.filter(is_enabled=True)
    if user.is_superuser or user.is_staff:
        return set(enabled.values_list("id", flat=True))

    return set(
        enabled.filter(
            user_permissions__user=user,
            user_permissions__can_view=True,
        ).values_list("id", flat=True)
    )


def visible_sources(user) -> QuerySet[Source]:
    """QuerySet of Source objects the user may view (enabled only)."""
    return Source.objects.filter(id__in=visible_source_ids(user))
