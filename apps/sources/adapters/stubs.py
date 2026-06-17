"""Skeleton adapters for commercial marketplaces.

These are intentionally *not implemented* yet — the structure is in place so a
developer can fill in :meth:`fetch` per marketplace without touching any other
part of the system. They register normally and show up in the admin, but the
collection task skips them while ``implemented = False``.

To finish one: implement ``fetch()`` (use ``self.http_get`` for the shared
retry/timeout policy), return ``list[NormalizedTender]``, then flip
``implemented = True``.
"""
from __future__ import annotations

from .base import BaseSource, NormalizedTender
from .registry import register


class _CommercialStub(BaseSource):
    """Common behaviour for not-yet-implemented commercial adapters."""

    implemented = False

    def fetch(self, limit: int = 30) -> list[NormalizedTender]:
        raise NotImplementedError(
            f"Adapter '{self.key}' ({self.label}) is a stub. "
            "Implement fetch() and set implemented = True."
        )


@register
class SberbankASTSource(_CommercialStub):
    key = "sberbank_ast"
    label = "Sberbank-AST"


@register
class RTSTenderSource(_CommercialStub):
    key = "rts_tender"
    label = "RTS-tender"


@register
class B2BCenterSource(_CommercialStub):
    key = "b2b_center"
    label = "B2B-Center"


@register
class FabrikantSource(_CommercialStub):
    key = "fabrikant"
    label = "Fabrikant"


@register
class OTCSource(_CommercialStub):
    key = "otc"
    label = "OTC.ru"
