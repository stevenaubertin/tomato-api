"""Tomato API - Python CLI tool to fetch device information from Tomato Router firmware."""

from .devlist import get_devices, main
from .find_device import search_devices
from .hostname_lookup import find_hostname
from .routers import RouterAdapter, TomatoAdapter, get_router_adapter
from .staticlist import get_static_list
from .unknown_devices import find_unknown_devices

__all__ = [
    "get_devices",
    "get_static_list",
    "find_unknown_devices",
    "search_devices",
    "find_hostname",
    "RouterAdapter",
    "TomatoAdapter",
    "get_router_adapter",
    "main",
]
