"""Collection orchestration + persistence.

Kept free of Celery so it can be driven from a management command, a test, or
the Celery task interchangeably.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from urllib.parse import unquote, urlparse

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from apps.sources.adapters import NormalizedTender, SourceFetchError, get_adapter
from apps.sources.models import Source

from .models import Tender, TenderDocument

logger = logging.getLogger("apps.tenders")


def _filename_from(url: str, fallback: str) -> str:
    name = os.path.basename(urlparse(unquote(url)).path) or fallback
    return name[:200]


def download_document(document: TenderDocument) -> bool:
    """Download a document's file into our own storage. Best-effort, never raises.

    Returns True if a file was stored. Skips if already downloaded, oversized,
    or unreachable (recording the error for visibility).
    """
    if document.is_downloaded and document.file:
        return False
    try:
        proxy = getattr(settings, "HTTP_PROXY_URL", "")
        resp = requests.get(
            document.url,
            timeout=settings.HTTP_TIMEOUT_SECONDS,
            stream=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ),
            },
            proxies={"http": proxy, "https": proxy} if proxy else None,
        )
        resp.raise_for_status()

        max_bytes = settings.DOCUMENT_MAX_BYTES
        chunks, total = [], 0
        for chunk in resp.iter_content(chunk_size=65536):
            total += len(chunk)
            if total > max_bytes:
                raise ValueError(f"document exceeds {max_bytes} bytes")
            chunks.append(chunk)
        content = b"".join(chunks)

        filename = _filename_from(document.url, fallback=f"doc-{document.pk}")
        document.file.save(filename, ContentFile(content), save=False)
        document.is_downloaded = True
        document.content_type = resp.headers.get("Content-Type", "")[:200]
        document.file_size = total
        document.fetched_at = timezone.now()
        document.download_error = ""
        document.save(update_fields=[
            "file", "is_downloaded", "content_type", "file_size",
            "fetched_at", "download_error",
        ])
        logger.info("Downloaded document %s (%d bytes)", document.url, total)
        return True
    except (requests.RequestException, ValueError, OSError) as exc:
        document.download_error = str(exc)[:300]
        document.save(update_fields=["download_error"])
        logger.warning("Document download failed for %s: %s", document.url, exc)
        return False


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


def _download_pending_documents(source: Source, cap: int = 100) -> None:
    """Download documents for this source that haven't been fetched yet.

    Only touches docs with no prior error so a permanently-broken link isn't
    retried every run. Isolated: a failed download never breaks collection.
    """
    pending = TenderDocument.objects.filter(
        tender__source=source, is_downloaded=False, download_error=""
    )[:cap]
    for document in pending:
        try:
            download_document(document)
        except Exception as exc:  # noqa: BLE001 — total isolation
            logger.exception("Unexpected document download error: %s", exc)


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

        if settings.DOWNLOAD_DOCUMENTS:
            _download_pending_documents(source)

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
