"""Collection orchestration + persistence.

Kept free of Celery so it can be driven from a management command, a test, or
the Celery task interchangeably.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from django.db import transaction

from apps.sources.adapters import NormalizedTender, SourceFetchError, get_adapter
from apps.sources.models import Source

from .models import Tender, TenderDocument

logger = logging.getLogger("apps.tenders")


@dataclass
class SourceResult:
    source_code: str
    created: int = 0
    updated: int = 0
    fetched: int = 0
    ok: bool = True
    error: str = ""


def upsert_tender(source: Source, item: NormalizedTender) -> bool:
    """Insert or update one tender. Returns True if newly created."""
    defaults = {
        "number": item.number or "",
        "title": item.title,
        "customer": item.customer or "",
        "price": item.price,
        "region": item.region or "",
        "fz_type": item.fz_type or "",
        "url": item.url or "",
        "published_at": item.published_at,
        "deadline_at": item.deadline_at,
        "raw": item.raw or {},
    }
    with transaction.atomic():
        tender, created = Tender.objects.update_or_create(
            source=source,
            external_id=item.external_id,
            defaults=defaults,
        )
        for doc in item.documents or []:
            url = (doc or {}).get("url")
            if not url:
                continue
            TenderDocument.objects.update_or_create(
                tender=tender,
                url=url,
                defaults={"title": (doc.get("title") or "")[:500]},
            )
    return created


def collect_from_source(source: Source, limit: int) -> SourceResult:
    """Fetch + persist a single source in isolation.

    Never raises: any failure is captured into the returned SourceResult so a
    broken source can't take down the whole collection run.
    """
    result = SourceResult(source_code=source.code)

    adapter_cls = None
    try:
        adapter_cls = get_adapter(source.resolved_adapter_key)
    except KeyError as exc:
        result.ok = False
        result.error = str(exc)
        logger.error("No adapter for source '%s': %s", source.code, exc)
        return result

    if not adapter_cls.implemented:
        result.ok = False
        result.error = "adapter not implemented (stub)"
        logger.info("Skipping stub source '%s'", source.code)
        return result

    try:
        adapter = adapter_cls(source=source)
        items = adapter.fetch(limit=limit)
        result.fetched = len(items)
        for item in items:
            try:
                if upsert_tender(source, item):
                    result.created += 1
                else:
                    result.updated += 1
            except Exception as exc:  # noqa: BLE001 — skip a bad record, keep going
                logger.exception("Failed to persist tender from '%s': %s", source.code, exc)
        logger.info(
            "Source '%s': fetched=%d created=%d updated=%d",
            source.code, result.fetched, result.created, result.updated,
        )
    except SourceFetchError as exc:
        result.ok = False
        result.error = str(exc)
        logger.error("Fetch failed for source '%s': %s", source.code, exc)
    except Exception as exc:  # noqa: BLE001 — total isolation guarantee
        result.ok = False
        result.error = repr(exc)
        logger.exception("Unexpected error collecting source '%s'", source.code)

    return result


def collect_all(limit: int) -> list[SourceResult]:
    """Collect every enabled, implemented source. Isolated per source."""
    results: list[SourceResult] = []
    sources = Source.objects.filter(is_enabled=True)
    logger.info("Starting collection run over %d enabled source(s)", sources.count())
    for source in sources:
        results.append(collect_from_source(source, limit))
    total_new = sum(r.created for r in results)
    logger.info("Collection run finished: %d new tender(s) across all sources", total_new)
    return results
