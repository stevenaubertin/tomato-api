"""Tomato API - Python CLI tool to fetch device information from Tomato Router firmware."""

from .devlist import get_devices, main
from .staticlist import get_static_list

__all__ = ["get_devices", "get_static_list", "main"]
