from rest_framework import viewsets

from apps.sources.permissions import visible_sources

from .filters import TenderFilter
from .models import Tender
from .serializers import TenderSerializer


class TenderViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only tender API, scoped to the requesting user's visible sources."""

    serializer_class = TenderSerializer
    filterset_class = TenderFilter
    search_fields = ["title", "customer", "number"]
    ordering_fields = ["published_at", "price", "deadline_at", "first_seen_at"]
    ordering = ["-published_at"]

    def get_queryset(self):
        return (
            Tender.objects.filter(source__in=visible_sources(self.request.user))
            .select_related("source")
            .prefetch_related("documents")
        )

    def get_filterset_kwargs(self):
        # Restrict the source filter choices to the user's visible sources.
        return {"visible_sources": visible_sources(self.request.user)}

    def filter_queryset(self, queryset):
        # DRF's DjangoFilterBackend won't pass our custom kwarg, so apply the
        # filterset manually with the scoped source choices, then let the
        # remaining backends (search, ordering) run.
        tender_filter = self.filterset_class(
            self.request.GET,
            queryset=queryset,
            visible_sources=visible_sources(self.request.user),
        )
        queryset = tender_filter.qs
        for backend in (b() for b in self.filter_backends):
            if backend.__class__.__name__ == "DjangoFilterBackend":
                continue
            queryset = backend.filter_queryset(self.request, queryset, self)
        return queryset
