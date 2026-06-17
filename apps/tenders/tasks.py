"""Celery tasks for scheduled tender collection."""
from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings

from apps.sources.models import Source

from .services import collect_all, collect_from_source

logger = logging.getLogger("apps.tenders")


@shared_task(name="tenders.collect_all_sources")
def collect_all_sources() -> dict:
    """Beat-scheduled entrypoint: collect from every enabled source.

    Returns a small summary dict (useful in the result backend / flower).
    Failures are isolated inside ``collect_all`` so this task itself does not
    raise on a single broken source.
    """
    limit = settings.TENDER_FETCH_PAGE_SIZE
    results = collect_all(limit=limit)
    summary = {
        "sources": len(results),
        "ok": sum(1 for r in results if r.ok),
        "failed": sum(1 for r in results if not r.ok),
        "created": sum(r.created for r in results),
        "updated": sum(r.updated for r in results),
        "details": [
            {
                "source": r.source_code,
                "ok": r.ok,
                "fetched": r.fetched,
                "created": r.created,
                "updated": r.updated,
                "error": r.error,
            }
            for r in results
        ],
    }
    logger.info("collect_all_sources summary: %s", summary)
    return summary


@shared_task(
    name="tenders.collect_single_source",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=3,
)
def collect_single_source(self, source_id: int) -> dict:
    """Collect one source by id (used for on-demand admin triggers / testing).

    Note: ``collect_from_source`` already isolates expected fetch errors into
    a result object; autoretry here is a safety net for truly unexpected
    infrastructure errors (e.g. transient DB issues).
    """
    source = Source.objects.get(id=source_id)
    result = collect_from_source(source, limit=settings.TENDER_FETCH_PAGE_SIZE)
    return {
        "source": result.source_code,
        "ok": result.ok,
        "fetched": result.fetched,
        "created": result.created,
        "updated": result.updated,
        "error": result.error,
    }
