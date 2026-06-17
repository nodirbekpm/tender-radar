"""EIS (zakupki.gov.ru) adapter — the primary, fully-implemented source.

Strategy: the EIS extended-search page exposes a public **RSS** export
(``.../epz/order/extendedsearch/rss.html``). RSS is a stable, documented,
captcha-free surface — far more robust to parse than the JS-heavy HTML pages.
We pull the 44-FZ and 223-FZ feeds separately so each tender is correctly
tagged, then normalize each RSS ``<item>`` into a :class:`NormalizedTender`.

Every parsing step is defensive: a malformed item is logged and skipped,
never crashing the whole fetch.
"""
from __future__ import annotations

import html
import logging
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qs, urlparse
from xml.etree import ElementTree as ET

from .base import BaseSource, NormalizedTender, SourceFetchError
from .registry import register

logger = logging.getLogger("apps.sources")

RSS_BASE = "https://zakupki.gov.ru/epz/order/extendedsearch/rss.html"

# Labels EIS uses inside the RSS <description> block (best-effort extraction).
_PRICE_LABELS = ("Начальная цена контракта", "Начальная (максимальная) цена", "Цена")
_CUSTOMER_LABELS = ("Заказчик", "Организация, осуществляющая размещение")
_REGION_LABELS = ("Регион", "Место нахождения")


@register
class EISSource(BaseSource):
    key = "eis"
    label = "ЕИС (zakupki.gov.ru)"
    implemented = True

    # Which FZ feeds to pull. Each maps to the RSS query flag EIS expects.
    _FEEDS = (("44", "fz44"), ("223", "fz223"))

    def fetch(self, limit: int = 30) -> list[NormalizedTender]:
        per_feed = max(1, limit // len(self._FEEDS))
        tenders: list[NormalizedTender] = []
        errors: list[str] = []

        for fz_type, flag in self._FEEDS:
            try:
                tenders.extend(self._fetch_feed(fz_type, flag, per_feed))
            except SourceFetchError as exc:
                # Isolate failures per-feed so 223-FZ still works if 44-FZ breaks.
                logger.warning("EIS feed %s-FZ failed: %s", fz_type, exc)
                errors.append(str(exc))

        if not tenders and errors:
            raise SourceFetchError(
                "All EIS feeds failed: " + "; ".join(errors)
            )
        logger.info("EIS fetch: %d tenders collected", len(tenders))
        return tenders[:limit]

    # ------------------------------------------------------------------ #

    def _fetch_feed(self, fz_type: str, flag: str, count: int) -> list[NormalizedTender]:
        url = (
            f"{RSS_BASE}?{flag}=on&pageNumber=1&sortDirection=false"
            f"&recordsPerPage=_{count}&sortBy=UPDATE_DATE&searchString="
        )
        response = self.http_get(url)
        return self._parse_rss(response.content, fz_type)

    def _parse_rss(self, content: bytes, fz_type: str) -> list[NormalizedTender]:
        try:
            root = ET.fromstring(content)
        except ET.ParseError as exc:
            raise SourceFetchError(f"EIS returned non-XML payload: {exc}") from exc

        items = root.findall(".//item")
        result: list[NormalizedTender] = []
        for item in items:
            try:
                tender = self._parse_item(item, fz_type)
                if tender is not None:
                    result.append(tender)
            except Exception as exc:  # noqa: BLE001 — one bad item must not kill the feed
                logger.warning("Skipping malformed EIS item: %s", exc)
        return result

    def _parse_item(self, item: ET.Element, fz_type: str) -> NormalizedTender | None:
        title = self._text(item, "title")
        link = self._text(item, "link")
        guid = self._text(item, "guid")
        description = html.unescape(self._text(item, "description"))
        pub_raw = self._text(item, "pubDate")

        reg_number = self._extract_reg_number(link) or self._extract_reg_number(guid)
        external_id = reg_number or guid or link
        if not external_id:
            return None

        return NormalizedTender(
            external_id=external_id,
            number=reg_number or "",
            title=self._clean_title(title) or "(без названия)",
            customer=self._extract_label(description, _CUSTOMER_LABELS),
            price=self._extract_price(description),
            region=self._extract_label(description, _REGION_LABELS),
            fz_type=fz_type,
            url=link,
            published_at=self._parse_date(pub_raw),
            deadline_at=None,  # EIS RSS rarely exposes deadline; left for detail enrichment
            documents=[],
            raw={"title": title, "description": description, "link": link},
        )

    # ------------------------- parsing helpers ------------------------- #

    @staticmethod
    def _text(item: ET.Element, tag: str) -> str:
        el = item.find(tag)
        return (el.text or "").strip() if el is not None and el.text else ""

    @staticmethod
    def _extract_reg_number(url: str) -> str:
        if not url:
            return ""
        params = parse_qs(urlparse(url).query)
        for key in ("regNumber", "regnumber", "noticeInfoId"):
            if key in params and params[key]:
                return params[key][0]
        # Sometimes the number appears as a long digit run in the path.
        match = re.search(r"(\d{11,})", url)
        return match.group(1) if match else ""

    @staticmethod
    def _clean_title(title: str) -> str:
        # Titles often start with "№ 0123... " — keep it, just collapse whitespace.
        return re.sub(r"\s+", " ", html.unescape(title)).strip()

    @staticmethod
    def _extract_label(description: str, labels: tuple[str, ...]) -> str:
        for label in labels:
            # Match "Label: value" up to the next label-like break or line end.
            pattern = rf"{re.escape(label)}\s*[:：]\s*(.+?)(?:<br|\n|;|$)"
            match = re.search(pattern, description, flags=re.IGNORECASE)
            if match:
                value = re.sub(r"<[^>]+>", "", match.group(1)).strip()
                if value:
                    return value[:500]
        return ""

    @classmethod
    def _extract_price(cls, description: str) -> Decimal | None:
        """Parse a Russian-formatted money string into a Decimal.

        Russian locale: space/dot are thousand separators, comma is the
        decimal separator, e.g. "1 234 567,89 руб." → 1234567.89.
        """
        raw = cls._extract_label(description, _PRICE_LABELS)
        if not raw:
            return None
        cleaned = raw.replace("\xa0", " ")
        # Grab the first number-like run (digits/spaces/dots, optional ,decimals);
        # this naturally stops before trailing units like "руб.".
        match = re.search(r"\d[\d .]*(?:,\d+)?", cleaned)
        if not match:
            return None
        num = match.group(0).replace(" ", "")
        if "," in num:
            num = num.replace(".", "").replace(",", ".")  # dots = thousands, comma = decimal
        else:
            num = num.replace(".", "")  # only thousand separators present
        if not num:
            return None
        try:
            return Decimal(num)
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def _parse_date(raw: str) -> datetime | None:
        if not raw:
            return None
        try:
            dt = parsedate_to_datetime(raw)
        except (TypeError, ValueError):
            return None
        if dt is not None and dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
