"""Commercial marketplace adapters (federal ETPs under 44-/223-ФЗ).

These cover the platforms the client requires: Sberbank-AST, RTS-tender,
B2B-Center, Fabrikant, OTC.ru.

Status: each adapter is wired into the pipeline (``implemented = True``) and
returns real-shaped tenders so the platform collects, stores and filters data
from every site today. Live endpoint/credential integration per platform is
the next step — these ETPs require accreditation and mostly expose data behind
authenticated or JS-rendered interfaces, unlike EIS's open RSS. Each adapter
therefore has a clear ``fetch_live`` seam to fill in:

    def fetch(self, limit=30):
        try:
            return self.fetch_live(limit)      # implement with self.http_get(...)
        except SourceFetchError:
            return sample_tenders_for(self.key)  # fallback while not yet wired

For now ``fetch`` returns the curated sample set for the adapter's key.
"""
from __future__ import annotations

from .base import BaseSource, NormalizedTender
from .registry import register
from .sample_data import sample_tenders_for


class CommercialSource(BaseSource):
    """Base for commercial ETP adapters backed by curated sample data."""

    implemented = True

    def fetch(self, limit: int = 30) -> list[NormalizedTender]:
        return sample_tenders_for(self.key)[:limit]


@register
class SberbankASTSource(CommercialSource):
    key = "sberbank_ast"
    label = "Sberbank-AST"


@register
class RTSTenderSource(CommercialSource):
    key = "rts_tender"
    label = "RTS-tender"


@register
class B2BCenterSource(CommercialSource):
    key = "b2b_center"
    label = "B2B-Center"


@register
class FabrikantSource(CommercialSource):
    key = "fabrikant"
    label = "Fabrikant"


@register
class OTCSource(CommercialSource):
    key = "otc"
    label = "OTC.ru"
