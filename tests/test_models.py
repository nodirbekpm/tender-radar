from decimal import Decimal

import pytest

from apps.sources.adapters import NormalizedTender
from apps.tenders.models import Tender, TenderDocument
from apps.tenders.services import upsert_tender

pytestmark = pytest.mark.django_db


def _item(**overrides):
    base = dict(
        external_id="REG-1",
        title="Test tender",
        number="REG-1",
        price=Decimal("100.00"),
        fz_type="44",
        documents=[{"title": "Doc", "url": "https://example.com/d.pdf"}],
    )
    base.update(overrides)
    return NormalizedTender(**base)


def test_upsert_creates_then_updates(eis_source):
    created = upsert_tender(eis_source, _item(title="First"))
    assert created is True
    assert Tender.objects.count() == 1

    # Same source + external_id → update, not insert.
    created_again = upsert_tender(eis_source, _item(title="Updated"))
    assert created_again is False
    assert Tender.objects.count() == 1
    assert Tender.objects.get().title == "Updated"


def test_documents_deduplicated(eis_source):
    upsert_tender(eis_source, _item())
    upsert_tender(eis_source, _item())  # same doc url again
    assert TenderDocument.objects.count() == 1


def test_same_external_id_different_source_not_duplicate(eis_source, commercial_source):
    upsert_tender(eis_source, _item(external_id="X"))
    upsert_tender(commercial_source, _item(external_id="X"))
    assert Tender.objects.count() == 2


def test_normalized_tender_requires_external_id():
    with pytest.raises(ValueError):
        NormalizedTender(external_id="", title="x")
