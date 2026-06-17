import pytest

from apps.sources.adapters.base import NormalizedTender, SourceFetchError
from apps.tenders.services import collect_all, collect_from_source

pytestmark = pytest.mark.django_db


def test_collect_commercial_source(commercial_source, settings):
    # b2b_center adapter is implemented and returns curated sample tenders.
    settings.DOWNLOAD_DOCUMENTS = False  # avoid network during the test
    result = collect_from_source(commercial_source, limit=5)
    assert result.ok is True
    assert result.fetched >= 1
    assert result.created >= 1


def test_collect_isolates_fetch_error(eis_source, monkeypatch):
    from apps.sources.adapters.eis import EISSource

    def boom(self, limit=30):
        raise SourceFetchError("network down")

    monkeypatch.setattr(EISSource, "fetch", boom)
    result = collect_from_source(eis_source, limit=5)
    assert result.ok is False
    assert "network down" in result.error


def test_collect_persists_results(eis_source, monkeypatch):
    from apps.sources.adapters.eis import EISSource

    def fake_fetch(self, limit=30):
        return [
            NormalizedTender(external_id="A", title="One", fz_type="44"),
            NormalizedTender(external_id="B", title="Two", fz_type="223"),
        ]

    monkeypatch.setattr(EISSource, "fetch", fake_fetch)
    result = collect_from_source(eis_source, limit=5)
    assert result.ok is True
    assert result.created == 2
    assert result.fetched == 2


def test_collect_all_continues_after_one_failure(eis_source, commercial_source, monkeypatch, settings):
    from apps.sources.adapters.eis import EISSource

    settings.DOWNLOAD_DOCUMENTS = False

    def boom(self, limit=30):
        raise SourceFetchError("EIS down")

    # EIS fails, but the commercial source must still be collected.
    monkeypatch.setattr(EISSource, "fetch", boom)
    results = collect_all(limit=5)
    by_code = {r.source_code: r for r in results}
    assert by_code["eis"].ok is False          # EIS failed
    assert by_code["b2b_center"].ok is True     # isolated — still collected
