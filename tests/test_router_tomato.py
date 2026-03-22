"""Tests for the Tomato/Asus router adapter."""

import json
from unittest.mock import MagicMock, patch

from src.routers.tomato import TomatoAdapter


def _make_adapter(mock_text):
    """Create a TomatoAdapter with mocked HTTP response."""
    adapter = TomatoAdapter("192.168.1.1", "admin", "pass")
    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = mock_text
    mock_resp.status_code = 200
    mock_session.get.return_value = mock_resp
    return adapter, mock_session


class TestTomatoAdapter:
    def test_parse_statics(self, router_html_fixture):
        adapter, mock_session = _make_adapter(router_html_fixture)
        with patch("src.routers.tomato.requests.Session", return_value=mock_session):
            statics = adapter.get_statics()
        names = [d["name"] for d in statics]
        assert "swarm0" in names
        assert "swarm1" in names
        assert "swarm2" in names

    def test_parse_leases(self, router_html_fixture):
        adapter, mock_session = _make_adapter(router_html_fixture)
        with patch("src.routers.tomato.requests.Session", return_value=mock_session):
            leases = adapter.get_leases()
        names = [d["name"] for d in leases]
        assert "swarm0" in names
        assert "laptop" in names

    def test_parse_arp_table(self, router_html_fixture):
        adapter, mock_session = _make_adapter(router_html_fixture)
        with patch("src.routers.tomato.requests.Session", return_value=mock_session):
            arp = adapter.get_arp_table()
        assert "br0" in arp
        macs = [d["mac"] for d in arp["br0"]]
        assert "B8:27:EB:80:09:E3" in macs

    def test_find_hostname_by_mac(self, router_html_fixture):
        adapter, mock_session = _make_adapter(router_html_fixture)
        with patch("src.routers.tomato.requests.Session", return_value=mock_session):
            assert adapter.find_hostname_by_mac("B8:27:EB:64:64:85") == "swarm1"

    def test_find_hostname_case_insensitive(self, router_html_fixture):
        adapter, mock_session = _make_adapter(router_html_fixture)
        with patch("src.routers.tomato.requests.Session", return_value=mock_session):
            assert adapter.find_hostname_by_mac("b8:27:eb:64:64:85") == "swarm1"

    def test_find_hostname_unknown_mac(self, router_html_fixture):
        adapter, mock_session = _make_adapter(router_html_fixture)
        with patch("src.routers.tomato.requests.Session", return_value=mock_session):
            assert adapter.find_hostname_by_mac("FF:FF:FF:FF:FF:FF") == ""

    def test_get_all_devices_format(self, router_html_fixture):
        adapter, mock_session = _make_adapter(router_html_fixture)
        with patch("src.routers.tomato.requests.Session", return_value=mock_session):
            result = adapter.get_all_devices()
        assert "lease" in result
        assert "statics" in result
        assert "arplist" in result

    def test_to_json(self, router_html_fixture):
        adapter, mock_session = _make_adapter(router_html_fixture)
        with patch("src.routers.tomato.requests.Session", return_value=mock_session):
            result = json.loads(adapter.to_json())
        assert "lease" in result
        assert "statics" in result
        assert "arplist" in result

    def test_empty_response(self):
        adapter, mock_session = _make_adapter("// empty page")
        with patch("src.routers.tomato.requests.Session", return_value=mock_session):
            result = adapter.get_all_devices()
        assert result["lease"] == []
        assert result["statics"] == []
        assert result["arplist"] == {}

    def test_statics_parses_mac_and_ip(self, router_html_fixture):
        adapter, mock_session = _make_adapter(router_html_fixture)
        with patch("src.routers.tomato.requests.Session", return_value=mock_session):
            statics = adapter.get_statics()
        swarm1 = [d for d in statics if d["name"] == "swarm1"]
        assert len(swarm1) == 1
        assert swarm1[0]["mac"] == "B8:27:EB:64:64:85"
        assert swarm1[0]["ip"] == "192.168.1.51"

    def test_arp_resolves_names_from_known_devices(self, router_html_fixture):
        adapter, mock_session = _make_adapter(router_html_fixture)
        with patch("src.routers.tomato.requests.Session", return_value=mock_session):
            arp = adapter.get_arp_table()
        swarm0_entry = [d for d in arp["br0"] if d["mac"] == "B8:27:EB:80:09:E3"]
        assert len(swarm0_entry) == 1
        assert swarm0_entry[0]["name"] == "swarm0"
