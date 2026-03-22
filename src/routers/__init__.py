"""Router adapter factory for multi-router support."""

from typing import TYPE_CHECKING

from .base import RouterAdapter
from .tomato import TomatoAdapter

if TYPE_CHECKING:
    pass

_ADAPTERS: dict[str, type[RouterAdapter]] = {
    "tomato": TomatoAdapter,
    "asus": TomatoAdapter,  # Alias — Tomato firmware runs on Asus routers
}


def get_router_adapter(router_type: str, host: str, username: str, password: str) -> RouterAdapter:
    """Create a router adapter by type name.

    Supported types: tomato (alias: asus), netgear, tplink, pfsense
    """
    key = router_type.lower()
    if key not in _ADAPTERS:
        _load_stubs()

    cls = _ADAPTERS.get(key)
    if cls is None:
        supported = ", ".join(sorted(_ADAPTERS.keys()))
        raise ValueError(f"Unknown router type: {router_type}. Supported: {supported}")
    return cls(host, username, password)


def _load_stubs() -> None:
    from .netgear import NetgearAdapter
    from .pfsense import PfSenseAdapter
    from .tplink import TPLinkAdapter

    _ADAPTERS.update(
        {
            "netgear": NetgearAdapter,
            "tplink": TPLinkAdapter,
            "pfsense": PfSenseAdapter,
        }
    )


__all__ = ["RouterAdapter", "TomatoAdapter", "get_router_adapter"]
