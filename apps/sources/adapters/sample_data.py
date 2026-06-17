"""Fallback EIS sample tenders.

Used only by the demo seeder when a live EIS fetch returns nothing (e.g. the
container has no outbound network access to zakupki.gov.ru). These mirror the
shape of real EIS 44-/223-FZ notices so the demo dashboard is never empty.

In a networked environment the live RSS fetch runs first and these are ignored.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from .base import NormalizedTender


def _dt(days_ago: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days_ago)


def eis_sample_tenders() -> list[NormalizedTender]:
    return [
        NormalizedTender(
            external_id="0173100007724000123",
            number="0173100007724000123",
            title="Поставка серверного оборудования для нужд учреждения",
            customer="ФГБУ «Центр информационных технологий»",
            price=Decimal("4750000.00"),
            region="Москва",
            fz_type="44",
            url="https://zakupki.gov.ru/epz/order/notice/ea44/view/common-info.html?regNumber=0173100007724000123",
            published_at=_dt(1),
            deadline_at=_dt(-9),
            documents=[
                {"title": "Извещение.pdf", "url": "https://zakupki.gov.ru/example/notice.pdf"},
                {"title": "Техническое задание.docx", "url": "https://zakupki.gov.ru/example/tz.docx"},
            ],
        ),
        NormalizedTender(
            external_id="0356200005824001045",
            number="0356200005824001045",
            title="Выполнение работ по капитальному ремонту автомобильной дороги",
            customer="Департамент дорожного хозяйства",
            price=Decimal("128400000.00"),
            region="Республика Татарстан",
            fz_type="44",
            url="https://zakupki.gov.ru/epz/order/notice/ea44/view/common-info.html?regNumber=0356200005824001045",
            published_at=_dt(2),
            deadline_at=_dt(-12),
        ),
        NormalizedTender(
            external_id="32413987654",
            number="32413987654",
            title="Оказание услуг по техническому обслуживанию инженерных систем зданий",
            customer="ПАО «Энергосбыт»",
            price=Decimal("9650000.50"),
            region="Санкт-Петербург",
            fz_type="223",
            url="https://zakupki.gov.ru/epz/order/notice/notice223/common-info.html?noticeInfoId=32413987654",
            published_at=_dt(3),
            deadline_at=_dt(-7),
            documents=[
                {"title": "Документация о закупке.pdf", "url": "https://zakupki.gov.ru/example/doc223.pdf"},
            ],
        ),
        NormalizedTender(
            external_id="0173100012324000777",
            number="0173100012324000777",
            title="Поставка лекарственных препаратов (антибактериальные средства)",
            customer="ГБУЗ «Городская клиническая больница №1»",
            price=Decimal("2310000.00"),
            region="Новосибирская область",
            fz_type="44",
            url="https://zakupki.gov.ru/epz/order/notice/ea44/view/common-info.html?regNumber=0173100012324000777",
            published_at=_dt(4),
            deadline_at=_dt(-5),
        ),
        NormalizedTender(
            external_id="32413555001",
            number="32413555001",
            title="Закупка канцелярских товаров и расходных материалов",
            customer="АО «Промышленная группа»",
            price=Decimal("875000.00"),
            region="Свердловская область",
            fz_type="223",
            url="https://zakupki.gov.ru/epz/order/notice/notice223/common-info.html?noticeInfoId=32413555001",
            published_at=_dt(5),
            deadline_at=_dt(-3),
        ),
    ]
