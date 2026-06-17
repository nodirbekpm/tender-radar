"""EIS (zakupki.gov.ru) adapter — primary, fully-implemented source.

Pipeline (verified against the live site):

1. **Search results page** ``/epz/order/extendedsearch/results.html`` returns
   static HTML cards (``.search-registry-entry-block``) for 44-/223-FZ. Each
   card carries the real fields: registry number + notice URL, object/title,
   customer (Заказчик), initial price (Начальная цена), publish/deadline dates
   and a link to the documents tab.
2. **Documents page** ``.../view/documents.html?regNumber=…`` lists real
   attachments (ТЗ, contract draft, NMC justification) as ``filestore``
   download links — these are the actual files we then store locally.

Everything is defensive: a malformed card/attachment is logged and skipped,
never crashing the whole fetch.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup

from .base import BaseSource, NormalizedTender, SourceFetchError
from .registry import register

logger = logging.getLogger("apps.sources")

BASE = "https://zakupki.gov.ru"
RESULTS_URL = f"{BASE}/epz/order/extendedsearch/results.html"


@register
class EISSource(BaseSource):
    key = "eis"
    label = "ЕИС (zakupki.gov.ru)"
    implemented = True

    # Each FZ maps to the results-page query flag.
    _FEEDS = (("44", "fz44"), ("223", "fz223"))

    # Enrich each tender with its real attachment files (extra request/tender).
    enrich_documents = True

    def fetch(self, limit: int = 30) -> list[NormalizedTender]:
        per_feed = max(1, limit // len(self._FEEDS))
        tenders: list[NormalizedTender] = []
        errors: list[str] = []

        for fz_type, flag in self._FEEDS:
            try:
                tenders.extend(self._fetch_feed(fz_type, flag, per_feed))
            except SourceFetchError as exc:
                logger.warning("EIS feed %s-FZ failed: %s", fz_type, exc)
                errors.append(str(exc))

        if not tenders and errors:
            raise SourceFetchError("All EIS feeds failed: " + "; ".join(errors))

        if self.enrich_documents:
            for tender in tenders:
                self._enrich_documents(tender)

        logger.info("EIS fetch: %d tenders collected", len(tenders))
        return tenders[:limit]

    # ------------------------------------------------------------------ #

    def _fetch_feed(self, fz_type: str, flag: str, count: int) -> list[NormalizedTender]:
        url = (
            f"{RESULTS_URL}?{flag}=on&pageNumber=1&sortDirection=false"
            f"&recordsPerPage=_{count}&sortBy=UPDATE_DATE&searchString="
        )
        html = self.http_get(url).text
        return self._parse_results(html, fz_type)

    def _parse_results(self, html: str, fz_type: str) -> list[NormalizedTender]:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(".search-registry-entry-block")
        result: list[NormalizedTender] = []
        for card in cards:
            try:
                tender = self._parse_card(card, fz_type)
                if tender is not None:
                    result.append(tender)
            except Exception as exc:  # noqa: BLE001 — one bad card mustn't kill the feed
                logger.warning("Skipping malformed EIS card: %s", exc)
        return result

    def _parse_card(self, card, fz_type: str) -> NormalizedTender | None:
        number_link = card.select_one(".registry-entry__header-mid__number a")
        notice_url = self._clean_href(number_link.get("href", "").strip()) if number_link else ""
        reg_number = self._reg_number(notice_url) or (
            self._text(number_link).replace("№", "").strip() if number_link else ""
        )
        if not reg_number:
            return None

        title = (
            self._block_value(card, "Объект закупки")
            or self._text(card.select_one(".registry-entry__header-mid__title"))
            or "(без названия)"
        )
        customer = self._customer(card)
        price = self._parse_money(self._text(card.select_one(".price-block__value")))
        published_at = self._card_date(card, "Размещено")
        deadline_at = self._card_date(card, "Окончание подачи заявок")
        documents_url = self._documents_url(card)

        return NormalizedTender(
            external_id=reg_number,
            number=reg_number,
            title=title,
            customer=customer,
            price=price,
            region="",  # not on the results card; can be enriched from detail later
            fz_type=fz_type,
            url=urljoin(BASE, notice_url) if notice_url else "",
            published_at=published_at,
            deadline_at=deadline_at,
            documents=[],
            raw={"documents_url": documents_url, "notice_url": notice_url},
        )

    def _enrich_documents(self, tender: NormalizedTender) -> None:
        """Fetch the documents tab and attach real file links. Best-effort."""
        documents_url = (tender.raw or {}).get("documents_url")
        if not documents_url:
            return
        try:
            html = self.http_get(urljoin(BASE, documents_url)).text
        except SourceFetchError as exc:
            logger.info("Documents fetch failed for %s: %s", tender.external_id, exc)
            return
        soup = BeautifulSoup(html, "html.parser")
        docs: list[dict] = []
        for link in soup.select(".attachment a[href*='filestore']"):
            href = link.get("href", "").strip()
            if not href:
                continue
            name = (link.get("title") or self._text(link) or "").strip()
            docs.append({"title": name[:500], "url": urljoin(BASE, href)})
        if docs:
            tender.documents = docs

    # ------------------------- parsing helpers ------------------------- #

    @staticmethod
    def _text(node) -> str:
        return re.sub(r"\s+", " ", node.get_text()).strip() if node else ""

    @staticmethod
    def _reg_number(url: str) -> str:
        if not url:
            return ""
        params = parse_qs(urlparse(url).query)
        for key in ("regNumber", "regnumber", "noticeInfoId"):
            if params.get(key):
                return params[key][0]
        return ""

    def _block_value(self, card, title: str) -> str:
        """Return the value of a body-block whose title matches ``title``."""
        for block in card.select(".registry-entry__body-block"):
            t = block.select_one(".registry-entry__body-title")
            if t and self._text(t) == title:
                value = block.select_one(".registry-entry__body-value")
                return self._text(value)
        return ""

    def _customer(self, card) -> str:
        for block in card.select(".registry-entry__body-block"):
            t = block.select_one(".registry-entry__body-title")
            if t and self._text(t) == "Заказчик":
                href = block.select_one(".registry-entry__body-href")
                return self._text(href)
        return ""

    def _card_date(self, card, label: str):
        # Pair each title node with the next value node in document order;
        # this handles both column-wrapped and bare title/value layouts.
        for title in card.select(".data-block__title"):
            if self._text(title) == label:
                value = title.find_next(class_="data-block__value")
                if value is not None:
                    return self._parse_date(self._text(value))
        return None

    def _documents_url(self, card) -> str:
        link = card.select_one("a[href*='/documents.html']")
        return self._clean_href(link.get("href", "").strip()) if link else ""

    @staticmethod
    def _clean_href(href: str) -> str:
        """Undo HTML entity decoding inside query strings.

        The HTML parser turns ``&notice...`` into ``¬ice...`` (``&not`` is the
        ¬ entity), corrupting 223-FZ document links. Restore the literal text.
        """
        return href.replace("\xac", "&not") if href else href

    @staticmethod
    def _parse_money(text: str) -> Decimal | None:
        """Parse Russian money like '1 234 567,89 ₽' → Decimal('1234567.89')."""
        if not text:
            return None
        cleaned = text.replace("\xa0", " ")
        match = re.search(r"\d[\d .]*(?:,\d+)?", cleaned)
        if not match:
            return None
        num = match.group(0).replace(" ", "")
        num = num.replace(".", "").replace(",", ".") if "," in num else num.replace(".", "")
        try:
            return Decimal(num) if num else None
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def _parse_date(text: str):
        if not text:
            return None
        match = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", text)
        if not match:
            return None
        day, month, year = (int(g) for g in match.groups())
        try:
            return datetime(year, month, day, tzinfo=timezone.utc)
        except ValueError:
            return None

    # Back-compat alias used by the offline price test.
    _extract_price = _parse_money
