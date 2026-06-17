"""Representative sample tenders, per source.

Used to populate the demo across every marketplace (EIS + commercial ETPs) so
the multi-source UI, per-site filtering and dashboard are fully functional even
without live network access to the platforms.

* EIS: live RSS fetch runs first; these are the offline fallback.
* Commercial ETPs (Sberbank-AST, RTS-tender, B2B-Center, Fabrikant, OTC.ru):
  real endpoint/credential integration is the next step within stage 1; until
  then their adapters serve this curated, real-shaped data so the platform
  demonstrably collects and filters tenders from all required sites.

Several entries include ТЗ / documentation links so the document-download
pipeline has something to exercise.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from .base import NormalizedTender


def _dt(days_ago: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days_ago)


# Keyed by Source.code. Each value is a list of NormalizedTender.
_SAMPLES: dict[str, list[dict]] = {
    "eis": [
        {
            "external_id": "0173100007724000123",
            "number": "0173100007724000123",
            "title": "Поставка серверного оборудования для нужд учреждения",
            "customer": "ФГБУ «Центр информационных технологий»",
            "price": Decimal("4750000.00"),
            "region": "Москва",
            "fz_type": "44",
            "days": 1,
            "deadline": -9,
            "docs": [
                ("Извещение о закупке.pdf", "https://zakupki.gov.ru/sample/eis/notice-123.pdf"),
                ("Техническое задание.docx", "https://zakupki.gov.ru/sample/eis/tz-123.docx"),
            ],
        },
        {
            "external_id": "0356200005824001045",
            "number": "0356200005824001045",
            "title": "Выполнение работ по капитальному ремонту автомобильной дороги",
            "customer": "Департамент дорожного хозяйства",
            "price": Decimal("128400000.00"),
            "region": "Республика Татарстан",
            "fz_type": "44",
            "days": 2,
            "deadline": -12,
            "docs": [],
        },
        {
            "external_id": "32413987654",
            "number": "32413987654",
            "title": "Оказание услуг по техническому обслуживанию инженерных систем зданий",
            "customer": "ПАО «Энергосбыт»",
            "price": Decimal("9650000.50"),
            "region": "Санкт-Петербург",
            "fz_type": "223",
            "days": 3,
            "deadline": -7,
            "docs": [("Документация о закупке.pdf", "https://zakupki.gov.ru/sample/eis/doc-223.pdf")],
        },
    ],
    "sberbank_ast": [
        {
            "external_id": "SBAST-2024-778120",
            "number": "778120",
            "title": "Поставка медицинского оборудования (аппараты ИВЛ)",
            "customer": "ГБУЗ «Краевая клиническая больница»",
            "price": Decimal("23150000.00"),
            "region": "Краснодарский край",
            "fz_type": "44",
            "days": 1,
            "deadline": -10,
            "docs": [("Техническое задание.pdf", "https://www.sberbank-ast.ru/sample/tz-778120.pdf")],
        },
        {
            "external_id": "SBAST-2024-778544",
            "number": "778544",
            "title": "Закупка электротехнической продукции",
            "customer": "АО «Региональная сетевая компания»",
            "price": Decimal("5400000.00"),
            "region": "Самарская область",
            "fz_type": "223",
            "days": 4,
            "deadline": -6,
            "docs": [],
        },
    ],
    "rts_tender": [
        {
            "external_id": "RTS-0866200-000412",
            "number": "0866200000412",
            "title": "Поставка продуктов питания для образовательных учреждений",
            "customer": "Управление образования администрации города",
            "price": Decimal("3120000.00"),
            "region": "Новосибирская область",
            "fz_type": "44",
            "days": 2,
            "deadline": -8,
            "docs": [("Техническое задание.docx", "https://www.rts-tender.ru/sample/tz-000412.docx")],
        },
        {
            "external_id": "RTS-0866200-000587",
            "number": "0866200000587",
            "title": "Выполнение строительно-монтажных работ",
            "customer": "МКУ «Управление капитального строительства»",
            "price": Decimal("89700000.00"),
            "region": "Свердловская область",
            "fz_type": "44",
            "days": 5,
            "deadline": -14,
            "docs": [],
        },
    ],
    "b2b_center": [
        {
            "external_id": "B2B-3120045",
            "number": "3120045",
            "title": "Поставка запасных частей для промышленного оборудования",
            "customer": "ООО «Металлургический комбинат»",
            "price": Decimal("14250000.00"),
            "region": "Челябинская область",
            "fz_type": "223",
            "days": 1,
            "deadline": -9,
            "docs": [("Техническое задание.pdf", "https://www.b2b-center.ru/sample/tz-3120045.pdf")],
        },
        {
            "external_id": "B2B-3120399",
            "number": "3120399",
            "title": "Оказание транспортно-логистических услуг",
            "customer": "АО «Торговый дом»",
            "price": Decimal("6800000.00"),
            "region": "Ростовская область",
            "fz_type": "223",
            "days": 3,
            "deadline": -5,
            "docs": [],
        },
    ],
    "fabrikant": [
        {
            "external_id": "FBR-9921450",
            "number": "9921450",
            "title": "Закупка спецодежды и средств индивидуальной защиты",
            "customer": "ПАО «Горно-обогатительный комбинат»",
            "price": Decimal("2980000.00"),
            "region": "Кемеровская область",
            "fz_type": "223",
            "days": 2,
            "deadline": -7,
            "docs": [("Техническое задание.docx", "https://www.fabrikant.ru/sample/tz-9921450.docx")],
        },
    ],
    "otc": [
        {
            "external_id": "OTC-5540127",
            "number": "5540127",
            "title": "Поставка офисной мебели",
            "customer": "ООО «Управляющая компания»",
            "price": Decimal("1245000.00"),
            "region": "Пермский край",
            "fz_type": "223",
            "days": 1,
            "deadline": -4,
            "docs": [],
        },
        {
            "external_id": "OTC-5540588",
            "number": "5540588",
            "title": "Оказание услуг по уборке помещений",
            "customer": "АО «Бизнес-центр»",
            "price": Decimal("3760000.00"),
            "region": "Воронежская область",
            "fz_type": "223",
            "days": 4,
            "deadline": -11,
            "docs": [],
        },
    ],
}


def _build(entry: dict) -> NormalizedTender:
    return NormalizedTender(
        external_id=entry["external_id"],
        number=entry.get("number", ""),
        title=entry["title"],
        customer=entry.get("customer", ""),
        price=entry.get("price"),
        region=entry.get("region", ""),
        fz_type=entry.get("fz_type", ""),
        url=f"https://example.local/tender/{entry['external_id']}",
        published_at=_dt(entry.get("days", 1)),
        deadline_at=_dt(entry.get("deadline", -7)),
        documents=[{"title": t, "url": u} for (t, u) in entry.get("docs", [])],
    )


def sample_tenders_for(code: str) -> list[NormalizedTender]:
    return [_build(e) for e in _SAMPLES.get(code, [])]


def eis_sample_tenders() -> list[NormalizedTender]:
    """Backwards-compatible helper for the EIS offline fallback."""
    return sample_tenders_for("eis")
