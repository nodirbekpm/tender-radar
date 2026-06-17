"""Pluggable data-source adapters.

Add a new marketplace by subclassing :class:`BaseSource` and registering it
with :func:`register`. The collection task then picks it up automatically by
the Source's ``adapter_key``.
"""
from .base import BaseSource, NormalizedTender, SourceFetchError
from .registry import get_adapter, register, registered_keys

# Import concrete adapters for their registration side effects.
from . import eis  # noqa: F401
from . import stubs  # noqa: F401

__all__ = [
    "BaseSource",
    "NormalizedTender",
    "SourceFetchError",
    "get_adapter",
    "register",
    "registered_keys",
]
