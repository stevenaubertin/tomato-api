"""Tomato API - Python CLI tool to fetch device information from Tomato Router firmware."""

from .devlist import get_devices, main

__all__ = ['get_devices', 'main']
