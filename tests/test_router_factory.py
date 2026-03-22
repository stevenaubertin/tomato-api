"""Tests for the router adapter factory."""

import pytest

from src.routers import get_router_adapter
from src.routers.tomato import TomatoAdapter


class TestGetRouterAdapter:
    def test_tomato_returns_tomato_adapter(self):
        adapter = get_router_adapter("tomato", "192.168.1.1", "admin", "pass")
        assert isinstance(adapter, TomatoAdapter)

    def test_asus_alias_returns_tomato_adapter(self):
        adapter = get_router_adapter("asus", "192.168.1.1", "admin", "pass")
        assert isinstance(adapter, TomatoAdapter)

    def test_case_insensitive(self):
        adapter = get_router_adapter("Tomato", "192.168.1.1", "admin", "pass")
        assert isinstance(adapter, TomatoAdapter)

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown router type"):
            get_router_adapter("linksys", "192.168.1.1", "admin", "pass")

    def test_netgear_stub_raises_not_implemented(self):
        adapter = get_router_adapter("netgear", "192.168.1.1", "admin", "pass")
        with pytest.raises(NotImplementedError):
            adapter.get_statics()

    def test_tplink_stub_raises_not_implemented(self):
        adapter = get_router_adapter("tplink", "192.168.1.1", "admin", "pass")
        with pytest.raises(NotImplementedError):
            adapter.get_leases()

    def test_pfsense_stub_raises_not_implemented(self):
        adapter = get_router_adapter("pfsense", "192.168.1.1", "admin", "pass")
        with pytest.raises(NotImplementedError):
            adapter.get_arp_table()
