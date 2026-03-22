"""Tests for the router adapter base class."""

import json

from src.routers.base import RouterAdapter


class ConcreteAdapter(RouterAdapter):
    """Concrete implementation for testing the base class."""

    def __init__(self, statics=None, leases=None, arp=None):
        super().__init__("192.168.1.1", "admin", "pass")
        self._statics = statics or []
        self._leases = leases or []
        self._arp = arp or {}

    def get_statics(self):
        return self._statics

    def get_leases(self):
        return self._leases

    def get_arp_table(self):
        return self._arp


class TestRouterAdapter:
    def test_find_hostname_by_mac_found(self):
        adapter = ConcreteAdapter(
            statics=[{"name": "server", "mac": "AA:BB:CC:DD:EE:01", "ip": "192.168.1.50"}]
        )
        assert adapter.find_hostname_by_mac("AA:BB:CC:DD:EE:01") == "server"

    def test_find_hostname_by_mac_case_insensitive(self):
        adapter = ConcreteAdapter(
            statics=[{"name": "server", "mac": "AA:BB:CC:DD:EE:01", "ip": "192.168.1.50"}]
        )
        assert adapter.find_hostname_by_mac("aa:bb:cc:dd:ee:01") == "server"

    def test_find_hostname_by_mac_not_found(self):
        adapter = ConcreteAdapter(
            statics=[{"name": "server", "mac": "AA:BB:CC:DD:EE:01", "ip": "192.168.1.50"}]
        )
        assert adapter.find_hostname_by_mac("FF:FF:FF:FF:FF:FF") == ""

    def test_find_hostname_by_mac_empty_statics(self):
        adapter = ConcreteAdapter()
        assert adapter.find_hostname_by_mac("AA:BB:CC:DD:EE:01") == ""

    def test_get_all_devices(self):
        adapter = ConcreteAdapter(
            statics=[{"name": "s", "mac": "AA:BB:CC:DD:EE:01", "ip": "1.1.1.1"}],
            leases=[{"name": "l", "mac": "AA:BB:CC:DD:EE:02", "ip": "1.1.1.2"}],
            arp={"br0": [{"name": "a", "mac": "AA:BB:CC:DD:EE:03", "ip": "1.1.1.3"}]},
        )
        result = adapter.get_all_devices()
        assert "statics" in result
        assert "lease" in result
        assert "arplist" in result

    def test_to_json(self):
        adapter = ConcreteAdapter(
            statics=[{"name": "s", "mac": "AA:BB:CC:DD:EE:01", "ip": "1.1.1.1"}],
        )
        result = json.loads(adapter.to_json())
        assert result["statics"][0]["name"] == "s"
        assert result["lease"] == []
        assert result["arplist"] == {}

    def test_stores_connection_params(self):
        adapter = ConcreteAdapter()
        assert adapter.host == "192.168.1.1"
        assert adapter.username == "admin"
        assert adapter.password == "pass"
