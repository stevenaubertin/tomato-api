"""Tests for find_device module."""

import json

import responses

from src.find_device import format_json, format_table, main, search_devices

SAMPLE_DEVICES = {
    "lease": [
        {"name": "desktop-pc", "ip": "192.168.1.100", "mac": "AA:BB:CC:DD:EE:01"},
        {"name": "laptop", "ip": "192.168.1.101", "mac": "AA:BB:CC:DD:EE:02"},
    ],
    "statics": [
        {"name": "server", "ip": "192.168.1.50", "mac": "AA:BB:CC:DD:EE:10"},
    ],
    "arplist": {
        "br0": [
            {"name": "desktop-pc", "ip": "192.168.1.100", "mac": "AA:BB:CC:DD:EE:01"},
        ],
    },
}

SAMPLE_ROUTER_RESPONSE = """
<script>
var dhcpd_lease = [
['desktop-pc','192.168.1.100','AA:BB:CC:DD:EE:01'],
['laptop','192.168.1.101','AA:BB:CC:DD:EE:02']
];
var nvram = { dhcpd_static: 'AA:BB:CC:DD:EE:10<192.168.1.50<server' };
var arplist = [
'192.168.1.100','AA:BB:CC:DD:EE:01','br0'
];
</script>
"""


class TestSearchDevices:
    def test_search_by_name(self):
        results = search_devices(SAMPLE_DEVICES, "laptop")
        assert len(results) == 1
        assert results[0]["name"] == "laptop"
        assert results[0]["source"] == "lease"

    def test_search_by_name_case_insensitive(self):
        results = search_devices(SAMPLE_DEVICES, "LAPTOP")
        assert len(results) == 1

    def test_search_by_ip(self):
        results = search_devices(SAMPLE_DEVICES, "192.168.1.50")
        assert len(results) == 1
        assert results[0]["name"] == "server"
        assert results[0]["source"] == "static"

    def test_search_by_partial_mac(self):
        results = search_devices(SAMPLE_DEVICES, "AA:BB:CC:DD:EE:01")
        # Should match in lease and arp
        assert len(results) == 2
        sources = [r["source"] for r in results]
        assert "lease" in sources
        assert "arp:br0" in sources

    def test_search_no_match(self):
        results = search_devices(SAMPLE_DEVICES, "nonexistent")
        assert results == []

    def test_search_partial_name(self):
        results = search_devices(SAMPLE_DEVICES, "desk")
        assert len(results) >= 1
        assert results[0]["name"] == "desktop-pc"

    def test_search_empty_devices(self):
        results = search_devices({"lease": [], "statics": [], "arplist": {}}, "test")
        assert results == []


class TestFormatTable:
    def test_table_has_headers(self):
        results = [{"source": "lease", "name": "pc", "ip": "1.1.1.1", "mac": "AA:BB:CC:DD:EE:01"}]
        output = format_table(results)
        assert "SOURCE" in output
        assert "NAME" in output

    def test_table_has_data(self):
        results = [{"source": "lease", "name": "pc", "ip": "1.1.1.1", "mac": "AA:BB:CC:DD:EE:01"}]
        output = format_table(results)
        assert "pc" in output
        assert "1.1.1.1" in output

    def test_table_empty(self):
        output = format_table([])
        assert "No matching devices found." in output


class TestFormatJson:
    def test_json_compact(self):
        results = [{"source": "lease", "name": "pc", "ip": "1.1.1.1", "mac": "AA:BB:CC:DD:EE:01"}]
        output = format_json(results)
        data = json.loads(output)
        assert len(data) == 1

    def test_json_pretty(self):
        results = [{"source": "lease", "name": "pc", "ip": "1.1.1.1", "mac": "AA:BB:CC:DD:EE:01"}]
        output = format_json(results, pretty=True)
        assert "\n" in output
        assert "  " in output


class TestCLI:
    @responses.activate
    def test_main_finds_device(self, capsys):
        responses.add(
            responses.GET,
            "https://192.168.1.1/status-devices.asp",
            body=SAMPLE_ROUTER_RESPONSE,
            status=200,
        )
        result = main(["laptop", "admin", "password"])
        assert result == 0
        output = capsys.readouterr().out
        assert "laptop" in output

    @responses.activate
    def test_main_no_match(self, capsys):
        responses.add(
            responses.GET,
            "https://192.168.1.1/status-devices.asp",
            body=SAMPLE_ROUTER_RESPONSE,
            status=200,
        )
        result = main(["nonexistent", "admin", "password"])
        assert result == 0
        output = capsys.readouterr().out
        assert "No matching devices found." in output

    @responses.activate
    def test_main_json_format(self, capsys):
        responses.add(
            responses.GET,
            "https://192.168.1.1/status-devices.asp",
            body=SAMPLE_ROUTER_RESPONSE,
            status=200,
        )
        result = main(["laptop", "admin", "password", "--format", "json"])
        assert result == 0
        data = json.loads(capsys.readouterr().out)
        assert len(data) >= 1
