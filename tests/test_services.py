import pytest

from apps.sources.adapters.base import NormalizedTender, SourceFetchError
from apps.tenders.services import collect_all, collect_from_source

pytestmark = pytest.mark.django_db


def test_collect_skips_stub(commercial_source):
    # b2b_center is a real registered stub (implemented=False).
    result = collect_from_source(commercial_source, limit=5)
    assert result.ok is False
    assert "stub" in result.error.lower()
    assert result.created == 0


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


def test_collect_all_continues_after_one_failure(eis_source, commercial_source, monkeypatch):
    from apps.sources.adapters.eis import EISSource

    def fake_fetch(self, limit=30):
        return [NormalizedTender(external_id="A", title="One")]

    monkeypatch.setattr(EISSource, "fetch", fake_fetch)
    results = collect_all(limit=5)
    by_code = {r.source_code: r for r in results}
    assert by_code["eis"].ok is True          # EIS worked
    assert by_code["b2b_center"].ok is False   # stub failed, but didn't stop the run
