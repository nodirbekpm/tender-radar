from decimal import Decimal

import pytest

from apps.sources.adapters import get_adapter, registered_keys
from apps.sources.adapters.base import SourceFetchError
from apps.sources.adapters.eis import EISSource

# Minimal HTML mirroring a real EIS search-results card (results.html).
SAMPLE_CARD = """
<div class="search-registry-entry-block">
  <div class="registry-entry__header">
    <div class="registry-entry__header-mid">
      <div class="registry-entry__header-mid__number">
        <a href="https://zakupki.gov.ru/epz/order/notice/ea44/view/common-info.html?regNumber=0145300025026000003">
          № 0145300025026000003
        </a>
      </div>
      <div class="registry-entry__header-mid__title">Закупка услуг</div>
    </div>
  </div>
  <div class="registry-entry__body">
    <div class="registry-entry__body-block">
      <div class="registry-entry__body-title">Объект закупки</div>
      <div class="registry-entry__body-value">Поставка расходных материалов</div>
    </div>
    <div class="registry-entry__body-block">
      <div class="registry-entry__body-title">Заказчик</div>
      <div class="registry-entry__body-href"><a href="/x">ГБУ «Центр»</a></div>
    </div>
  </div>
  <div class="price-block">
    <div class="price-block__title">Начальная цена</div>
    <div class="price-block__value">1 234 567,89 &#8381;</div>
  </div>
  <div class="data-block">
    <div class="row">
      <div class="col-6"><div class="data-block__title">Размещено</div><div class="data-block__value">10.06.2026</div></div>
      <div class="col-6"><div class="data-block__title">Обновлено</div><div class="data-block__value">18.06.2026</div></div>
    </div>
    <div class="data-block__title">Окончание подачи заявок</div>
    <div class="data-block__value">25.06.2026</div>
  </div>
  <div class="href-block">
    <a href="/epz/order/notice/zkp20/view/documents.html?regNumber=0145300025026000003">Документы</a>
  </div>
</div>
"""


def test_eis_parses_results_card():
    tenders = EISSource()._parse_results(SAMPLE_CARD, "44")
    assert len(tenders) == 1
    t = tenders[0]
    assert t.external_id == "0145300025026000003"
    assert t.number == "0145300025026000003"
    assert t.title == "Поставка расходных материалов"
    assert t.customer == "ГБУ «Центр»"
    assert t.price == Decimal("1234567.89")
    assert t.fz_type == "44"
    assert t.published_at.date().isoformat() == "2026-06-10"
    assert t.deadline_at.date().isoformat() == "2026-06-25"
    assert "common-info.html" in t.url
    assert "documents.html" in t.raw["documents_url"]


def test_eis_money_parsing_variants():
    assert EISSource._parse_money("1 234 567,89 ₽") == Decimal("1234567.89")
    assert EISSource._parse_money("189 680,00 ₽") == Decimal("189680.00")
    assert EISSource._parse_money("52500") == Decimal("52500")
    assert EISSource._parse_money("нет") is None


def test_eis_reg_number_extraction():
    url = "https://zakupki.gov.ru/x?regNumber=0145300025026000003"
    assert EISSource._reg_number(url) == "0145300025026000003"
    assert EISSource._reg_number("") == ""


def test_eis_clean_href_restores_notice_entity():
    # &not is an HTML entity (¬); the parser corrupts &noticeGuid → ¬iceGuid.
    assert EISSource._clean_href("a?purchaseNoticeNumber=1\xaciceGuid=2") == (
        "a?purchaseNoticeNumber=1&noticeGuid=2"
    )


def test_eis_skips_card_without_number():
    html = '<div class="search-registry-entry-block"><div class="price-block__value">10 ₽</div></div>'
    assert EISSource()._parse_results(html, "44") == []


def test_eis_empty_html_returns_empty():
    assert EISSource()._parse_results("<html></html>", "44") == []


def test_registry_has_eis_and_stubs():
    keys = registered_keys()
    assert "eis" in keys
    assert "b2b_center" in keys


def test_commercial_adapter_returns_sample_data():
    adapter_cls = get_adapter("b2b_center")
    assert adapter_cls.implemented is True
    tenders = adapter_cls().fetch(limit=10)
    assert len(tenders) >= 1
    assert all(t.external_id for t in tenders)
