"""Base adapter contract shared by every data source."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

import requests
from django.conf import settings
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger("apps.sources")


class SourceFetchError(Exception):
    """Raised when an adapter cannot retrieve data from its remote source."""


@dataclass
class NormalizedTender:
    """Source-agnostic representation of one tender.

    Adapters convert whatever raw payload they receive into this shape; the
    persistence layer only ever sees normalized tenders, which keeps the
    Tender model decoupled from any single marketplace's quirks.
    """

    external_id: str
    title: str
    number: str = ""
    customer: str = ""
    price: Decimal | None = None
    region: str = ""
    fz_type: str = ""  # "44", "223" or ""
    url: str = ""
    published_at: datetime | None = None
    deadline_at: datetime | None = None
    # Each document: {"title": str, "url": str}
    documents: list[dict] = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.external_id:
            raise ValueError("NormalizedTender requires a non-empty external_id")
        self.external_id = str(self.external_id)


class BaseSource(ABC):
    """Abstract adapter. Subclasses implement :meth:`fetch`.

    Subclasses must set the class attributes ``key`` and ``label``. Stub
    adapters set ``implemented = False`` so the collection task can skip them
    cleanly while still appearing in the registry / admin.
    """

    key: str = ""
    label: str = ""
    implemented: bool = True

    def __init__(self, source=None):
        # ``source`` is the optional Source model instance, handy for adapters
        # that need per-source config later. Not required for fetching.
        self.source = source

    # -- HTTP helpers (shared retry/timeout policy) -------------------------

    # Browser-like headers — EIS and most ETPs drop unknown/bot clients.
    BROWSER_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    }

    def _proxies(self) -> dict | None:
        """Optional proxy (e.g. a Russia-exit proxy) from settings.

        Lets the collector reach geo-restricted platforms when the host itself
        has no direct route (browser-only VPN, foreign server, etc.).
        """
        proxy = getattr(settings, "HTTP_PROXY_URL", "")
        return {"http": proxy, "https": proxy} if proxy else None

    def _session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update(self.BROWSER_HEADERS)
        proxies = self._proxies()
        if proxies:
            session.proxies.update(proxies)
        return session

    def http_get(self, url: str, **kwargs) -> requests.Response:
        """GET with browser headers, optional proxy, timeout + retry policy.

        Retries only on transient network/5xx errors. Raises
        :class:`SourceFetchError` after retries are exhausted so callers have
        a single exception type to guard against.
        """
        timeout = kwargs.pop("timeout", settings.HTTP_TIMEOUT_SECONDS)
        max_attempts = max(1, settings.HTTP_MAX_RETRIES)

        @retry(
            reraise=True,
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(requests.RequestException),
        )
        def _do_get() -> requests.Response:
            session = self._session()
            try:
                response = session.get(url, timeout=timeout, **kwargs)
                response.raise_for_status()
                return response
            finally:
                session.close()

        try:
            return _do_get()
        except requests.RequestException as exc:
            raise SourceFetchError(f"GET {url} failed: {exc}") from exc

    # -- Adapter contract ---------------------------------------------------

    @abstractmethod
    def fetch(self, limit: int = 30) -> list[NormalizedTender]:
        """Return up to ``limit`` recently published tenders.

        Must raise :class:`SourceFetchError` on failure (never return partial
        garbage). Returning an empty list is valid.
        """
        raise NotImplementedError
