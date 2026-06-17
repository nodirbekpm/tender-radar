from decimal import Decimal

import pytest

from apps.sources.adapters import get_adapter, registered_keys
from apps.sources.adapters.base import SourceFetchError
from apps.sources.adapters.eis import EISSource

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>EIS</title>
    <item>
      <title>&#8470; 0173100007724000123 Поставка серверного оборудования</title>
      <link>https://zakupki.gov.ru/epz/order/notice/ea44/view/common-info.html?regNumber=0173100007724000123</link>
      <guid>0173100007724000123</guid>
      <description>Заказчик: ФГБУ Центр; Начальная цена контракта: 4 750 000,00 руб.; Регион: Москва</description>
      <pubDate>Mon, 16 Jun 2026 09:00:00 +0300</pubDate>
    </item>
    <item>
      <title>Без номера</title>
      <link>https://zakupki.gov.ru/epz/order/notice/ea44/view/common-info.html?regNumber=0356200005824001045</link>
      <description>Заказчик: Департамент; Цена: 128400000 руб.; Регион: Татарстан</description>
      <pubDate>Sun, 15 Jun 2026 12:30:00 +0300</pubDate>
    </item>
  </channel>
</rss>"""

SAMPLE_RSS_BYTES = SAMPLE_RSS.encode("utf-8")


def test_eis_parses_rss_items():
    tenders = EISSource()._parse_rss(SAMPLE_RSS_BYTES, "44")
    assert len(tenders) == 2

    first = tenders[0]
    assert first.external_id == "0173100007724000123"
    assert first.number == "0173100007724000123"
    assert "Поставка серверного оборудования" in first.title
    assert first.customer.startswith("ФГБУ")
    assert first.price == Decimal("4750000.00")
    assert first.region == "Москва"
    assert first.fz_type == "44"
    assert first.published_at is not None


def test_eis_price_parsing_variants():
    assert EISSource._extract_price("Цена: 1 234 567,89 руб.") == Decimal("1234567.89")
    assert EISSource._extract_price("Начальная цена контракта: 128400000 руб.") == Decimal("128400000")
    assert EISSource._extract_price("нет цены") is None


def test_eis_reg_number_extraction():
    url = "https://zakupki.gov.ru/x?regNumber=0173100007724000123"
    assert EISSource._extract_reg_number(url) == "0173100007724000123"
    assert EISSource._extract_reg_number("") == ""


def test_eis_malformed_xml_raises():
    with pytest.raises(SourceFetchError):
        EISSource()._parse_rss(b"<not-xml", "44")


def test_eis_skips_bad_item_keeps_good():
    rss = b"""<rss><channel>
      <item><description>no id no link</description></item>
      <item><link>https://x?regNumber=999</link><title>ok</title></item>
    </channel></rss>"""
    tenders = EISSource()._parse_rss(rss, "44")
    # First item has no external id and is skipped; second survives.
    assert len(tenders) == 1
    assert tenders[0].external_id == "999"


def test_registry_has_eis_and_stubs():
    keys = registered_keys()
    assert "eis" in keys
    assert "b2b_center" in keys


def test_stub_not_implemented():
    adapter_cls = get_adapter("b2b_center")
    assert adapter_cls.implemented is False
    with pytest.raises(NotImplementedError):
        adapter_cls().fetch()


def test_eis_fetch_uses_http(monkeypatch):
    """fetch() should pull both FZ feeds via http_get and combine results."""
    calls = []

    class FakeResponse:
        content = SAMPLE_RSS_BYTES

    def fake_get(self, url, **kwargs):
        calls.append(url)
        return FakeResponse()

    monkeypatch.setattr(EISSource, "http_get", fake_get)
    tenders = EISSource().fetch(limit=10)
    assert len(calls) == 2  # 44-FZ + 223-FZ feeds
    assert len(tenders) == 4  # 2 items per feed
