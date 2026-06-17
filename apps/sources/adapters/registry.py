"""A tiny registry mapping adapter keys to adapter classes."""
from __future__ import annotations

from .base import BaseSource

_REGISTRY: dict[str, type[BaseSource]] = {}


def register(adapter_cls: type[BaseSource]) -> type[BaseSource]:
    """Class decorator that registers an adapter under its ``key``."""
    key = adapter_cls.key
    if not key:
        raise ValueError(f"{adapter_cls.__name__} must define a non-empty `key`")
    if key in _REGISTRY:
        raise ValueError(f"Adapter key '{key}' is already registered")
    _REGISTRY[key] = adapter_cls
    return adapter_cls


def get_adapter(key: str) -> type[BaseSource]:
    try:
        return _REGISTRY[key]
    except KeyError as exc:
        raise KeyError(
            f"No adapter registered for key '{key}'. "
            f"Known keys: {sorted(_REGISTRY)}"
        ) from exc


def registered_keys() -> list[str]:
    return sorted(_REGISTRY)
