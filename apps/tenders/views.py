"""HTML views for the dashboard, tender list and tender detail.

Every view scopes its queryset to the sources the current user is allowed to
see (``visible_sources``), so a user can never view a tender from a source they
lack permission for — enforced at the queryset level, not just the template.
"""
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, render

from apps.sources.permissions import visible_sources

from .filters import TenderFilter
from .models import Tender

VALID_ORDERING = {
    "published_at", "-published_at",
    "price", "-price",
    "deadline_at", "-deadline_at",
}


def _visible_tenders(user):
    return Tender.objects.filter(source__in=visible_sources(user)).select_related("source")


@login_required
def tender_list(request):
    sources = visible_sources(request.user)
    base_qs = _visible_tenders(request.user)

    tender_filter = TenderFilter(
        request.GET,
        queryset=base_qs,
        visible_sources=sources,
    )
    qs = tender_filter.qs

    ordering = request.GET.get("ordering", "-published_at")
    if ordering not in VALID_ORDERING:
        ordering = "-published_at"
    qs = qs.order_by(ordering, "-first_seen_at")

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    # Preserve current filters across pagination/sort links.
    querydict = request.GET.copy()
    querydict.pop("page", None)
    base_query = querydict.urlencode()

    context = {
        "filter": tender_filter,
        "page_obj": page_obj,
        "paginator": paginator,
        "ordering": ordering,
        "base_query": base_query,
        "total_count": paginator.count,
        "visible_source_count": sources.count(),
    }
    return render(request, "tenders/list.html", context)


@login_required
def tender_detail(request, pk: int):
    tender = get_object_or_404(
        _visible_tenders(request.user).prefetch_related("documents"),
        pk=pk,
    )
    return render(request, "tenders/detail.html", {"tender": tender})


@login_required
def dashboard(request):
    sources = visible_sources(request.user)
    qs = _visible_tenders(request.user)
    by_source = list(
        qs.values("source_id", "source__name").annotate(n=Count("id")).order_by("-n")
    )
    stats = {
        "total": qs.count(),
        "by_source": by_source,
        "max_source_n": max((row["n"] for row in by_source), default=1),
        "by_fz": list(qs.values("fz_type").annotate(n=Count("id")).order_by("-n")),
        "total_value": qs.aggregate(s=Sum("price"))["s"],
        "sources": sources,
        "latest": qs.order_by("-first_seen_at")[:10],
    }
    return render(request, "tenders/dashboard.html", {"stats": stats})
