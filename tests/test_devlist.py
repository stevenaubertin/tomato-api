"""Unit tests for devlist.py"""

import json

import pytest
import requests
import responses

from src.devlist import (
    DEFAULT_ROUTER_IP,
    arplist_regex,
    filter_by_interface,
    flatten_devices,
    format_csv,
    format_json,
    format_table,
    get_devices,
    get_router_url,
    lease_regex,
    main,
    statics_regex,
)

# Sample router response HTML (simulates Tomato router output)
SAMPLE_ROUTER_RESPONSE = """
<html>
<head><title>Device List</title></head>
<body>
<script>
var dhcpd_lease = [
['desktop-pc','192.168.1.100','AA:BB:CC:DD:EE:01'],
['laptop','192.168.1.101','AA:BB:CC:DD:EE:02'],
['phone','192.168.1.102','AA:BB:CC:DD:EE:03']
];

var nvram = {
dhcpd_static: 'AA:BB:CC:DD:EE:10<192.168.1.50<server\nAA:BB:CC:DD:EE:11<192.168.1.51<nas'
};

var arplist = [
['192.168.1.100','AA:BB:CC:DD:EE:01','br0'],
['192.168.1.101','AA:BB:CC:DD:EE:02','br0'],
['192.168.1.200','AA:BB:CC:DD:EE:99','br1']
];
</script>
</body>
</html>
"""

EMPTY_ROUTER_RESPONSE = """
<html>
<head><title>Device List</title></head>
<body>
<script>
var dhcpd_lease = [];
var nvram = { dhcpd_static: '' };
var arplist = [];
</script>
</body>
</html>
"""


class TestRegexPatterns:
    """Test the regex patterns for parsing router responses."""

    def test_lease_regex_matches_valid_entries(self):
        text = "['desktop-pc','192.168.1.100','AA:BB:CC:DD:EE:01']"
        matches = lease_regex.findall(text)
        assert len(matches) == 1
        assert "desktop-pc" in matches[0]
        assert "192.168.1.100" in matches[0]
        assert "AA:BB:CC:DD:EE:01" in matches[0]

    def test_lease_regex_handles_multiple_entries(self):
        text = """
        ['device1','192.168.1.1','AA:BB:CC:DD:EE:01'],
        ['device2','192.168.1.2','AA:BB:CC:DD:EE:02']
        """
        matches = lease_regex.findall(text)
        assert len(matches) == 2

    def test_arplist_regex_matches_valid_entries(self):
        text = "'192.168.1.100','AA:BB:CC:DD:EE:01','br0'"
        matches = arplist_regex.findall(text)
        assert len(matches) == 1

    def test_statics_regex_matches_valid_entries(self):
        text = "AA:BB:CC:DD:EE:10<192.168.1.50<server"
        matches = statics_regex.findall(text)
        assert len(matches) == 1


class TestGetRouterUrl:
    """Test URL building function."""

    def test_default_ip(self):
        url = get_router_url(DEFAULT_ROUTER_IP)
        assert url == "https://192.168.1.1/status-devices.asp"

    def test_custom_ip(self):
        url = get_router_url("10.0.0.1")
        assert url == "https://10.0.0.1/status-devices.asp"


class TestGetDevices:
    """Test the main device fetching function."""

    @responses.activate
    def test_get_devices_returns_dict(self):
        responses.add(
            responses.GET,
            "https://192.168.1.1/status-devices.asp",
            body=SAMPLE_ROUTER_RESPONSE,
            status=200,
        )

        result = get_devices("admin", "password", "192.168.1.1")

        assert isinstance(result, dict)
        assert "arplist" in result
        assert "lease" in result
        assert "statics" in result

    @responses.activate
    def test_get_devices_parses_leases(self):
        responses.add(
            responses.GET,
            "https://192.168.1.1/status-devices.asp",
            body=SAMPLE_ROUTER_RESPONSE,
            status=200,
        )

        result = get_devices("admin", "password", "192.168.1.1")

        assert len(result["lease"]) == 3
        assert result["lease"][0]["name"] == "desktop-pc"
        assert result["lease"][0]["ip"] == "192.168.1.100"
        assert result["lease"][0]["mac"] == "AA:BB:CC:DD:EE:01"

    @responses.activate
    def test_get_devices_parses_statics(self):
        responses.add(
            responses.GET,
            "https://192.168.1.1/status-devices.asp",
            body=SAMPLE_ROUTER_RESPONSE,
            status=200,
        )

        result = get_devices("admin", "password", "192.168.1.1")

        assert len(result["statics"]) == 2
        assert result["statics"][0]["name"] == "server"
        assert result["statics"][0]["ip"] == "192.168.1.50"

    @responses.activate
    def test_get_devices_parses_arplist_by_interface(self):
        responses.add(
            responses.GET,
            "https://192.168.1.1/status-devices.asp",
            body=SAMPLE_ROUTER_RESPONSE,
            status=200,
        )

        result = get_devices("admin", "password", "192.168.1.1")

        assert "br0" in result["arplist"]
        assert "br1" in result["arplist"]
        assert len(result["arplist"]["br0"]) == 2
        assert len(result["arplist"]["br1"]) == 1

    @responses.activate
    def test_get_devices_correlates_names_from_leases(self):
        responses.add(
            responses.GET,
            "https://192.168.1.1/status-devices.asp",
            body=SAMPLE_ROUTER_RESPONSE,
            status=200,
        )

        result = get_devices("admin", "password", "192.168.1.1")

        # ARP entry with MAC AA:BB:CC:DD:EE:01 should get name from lease
        br0_devices = result["arplist"]["br0"]
        desktop = next(d for d in br0_devices if d["mac"] == "AA:BB:CC:DD:EE:01")
        assert desktop["name"] == "desktop-pc"

    @responses.activate
    def test_get_devices_handles_empty_response(self):
        responses.add(
            responses.GET,
            "https://192.168.1.1/status-devices.asp",
            body=EMPTY_ROUTER_RESPONSE,
            status=200,
        )

        result = get_devices("admin", "password", "192.168.1.1")

        assert result["lease"] == []
        assert result["statics"] == []
        assert result["arplist"] == {}

    @responses.activate
    def test_get_devices_raises_on_auth_failure(self):
        responses.add(
            responses.GET,
            "https://192.168.1.1/status-devices.asp",
            status=401,
        )

        with pytest.raises(requests.exceptions.HTTPError):
            get_devices("admin", "wrong", "192.168.1.1")

    @responses.activate
    def test_get_devices_raises_on_connection_error(self):
        responses.add(
            responses.GET,
            "https://192.168.1.1/status-devices.asp",
            body=requests.exceptions.ConnectionError("Connection refused"),
        )

        with pytest.raises(requests.exceptions.ConnectionError):
            get_devices("admin", "password", "192.168.1.1")


class TestCLI:
    """Test command-line interface."""

    @responses.activate
    def test_main_returns_zero_on_success(self):
        responses.add(
            responses.GET,
            "https://192.168.1.1/status-devices.asp",
            body=SAMPLE_ROUTER_RESPONSE,
            status=200,
        )

        result = main(["admin", "password"])
        assert result == 0

    @responses.activate
    def test_main_returns_nonzero_on_auth_failure(self):
        responses.add(
            responses.GET,
            "https://192.168.1.1/status-devices.asp",
            status=401,
        )

        result = main(["admin", "wrong"])
        assert result == 1

    @responses.activate
    def test_main_accepts_custom_router(self):
        responses.add(
            responses.GET,
            "https://10.0.0.1/status-devices.asp",
            body=SAMPLE_ROUTER_RESPONSE,
            status=200,
        )

        result = main(["admin", "password", "--router", "10.0.0.1"])
        assert result == 0

    @responses.activate
    def test_main_pretty_flag(self, capsys):
        responses.add(
            responses.GET,
            "https://192.168.1.1/status-devices.asp",
            body=SAMPLE_ROUTER_RESPONSE,
            status=200,
        )

        main(["admin", "password", "--pretty"])
        captured = capsys.readouterr()

        # Pretty output should have newlines and indentation
        assert "\n" in captured.out
        assert "  " in captured.out

    @responses.activate
    def test_main_json_output_is_valid(self, capsys):
        responses.add(
            responses.GET,
            "https://192.168.1.1/status-devices.asp",
            body=SAMPLE_ROUTER_RESPONSE,
            status=200,
        )

        main(["admin", "password"])
        captured = capsys.readouterr()

        # Should be valid JSON
        data = json.loads(captured.out)
        assert "arplist" in data
        assert "lease" in data
        assert "statics" in data

    @responses.activate
    def test_main_format_csv(self, capsys):
        responses.add(
            responses.GET,
            "https://192.168.1.1/status-devices.asp",
            body=SAMPLE_ROUTER_RESPONSE,
            status=200,
        )

        main(["admin", "password", "--format", "csv"])
        captured = capsys.readouterr()

        # CSV should have header and data rows
        assert "type,interface,name,ip,mac" in captured.out
        assert "lease" in captured.out
        assert "desktop-pc" in captured.out

    @responses.activate
    def test_main_format_table(self, capsys):
        responses.add(
            responses.GET,
            "https://192.168.1.1/status-devices.asp",
            body=SAMPLE_ROUTER_RESPONSE,
            status=200,
        )

        main(["admin", "password", "--format", "table"])
        captured = capsys.readouterr()

        # Table should have headers and data
        assert "TYPE" in captured.out
        assert "NAME" in captured.out
        assert "desktop-pc" in captured.out

    @responses.activate
    def test_main_verbose_flag(self, capsys):
        responses.add(
            responses.GET,
            "https://192.168.1.1/status-devices.asp",
            body=SAMPLE_ROUTER_RESPONSE,
            status=200,
        )

        main(["admin", "password", "--verbose"])
        captured = capsys.readouterr()

        # Verbose output should have debug messages in stderr
        assert "DEBUG" in captured.err
        assert "Connecting to router" in captured.err

    @responses.activate
    def test_main_interface_filter(self, capsys):
        responses.add(
            responses.GET,
            "https://192.168.1.1/status-devices.asp",
            body=SAMPLE_ROUTER_RESPONSE,
            status=200,
        )

        main(["admin", "password", "--interface", "br0", "--format", "json"])
        captured = capsys.readouterr()

        data = json.loads(captured.out)
        # Should only have br0 in arplist
        assert "br0" in data["arplist"]
        assert "br1" not in data["arplist"]

    @responses.activate
    def test_main_interface_filter_nonexistent(self, capsys):
        responses.add(
            responses.GET,
            "https://192.168.1.1/status-devices.asp",
            body=SAMPLE_ROUTER_RESPONSE,
            status=200,
        )

        main(["admin", "password", "--interface", "br99"])
        captured = capsys.readouterr()

        data = json.loads(captured.out)
        # Should have empty arplist but still include leases and statics
        assert data["arplist"] == {}
        assert len(data["lease"]) > 0


class TestOutputFormats:
    """Test output formatting functions."""

    def test_flatten_devices_includes_all_types(self):
        devices = {
            "lease": [{"name": "pc", "ip": "192.168.1.1", "mac": "AA:BB:CC:DD:EE:01"}],
            "statics": [{"name": "server", "ip": "192.168.1.2", "mac": "AA:BB:CC:DD:EE:02"}],
            "arplist": {
                "br0": [{"name": "phone", "ip": "192.168.1.3", "mac": "AA:BB:CC:DD:EE:03"}]
            },
        }

        rows = flatten_devices(devices)

        assert len(rows) == 3
        types = [r["type"] for r in rows]
        assert "lease" in types
        assert "static" in types
        assert "arp" in types

    def test_flatten_devices_empty(self):
        devices = {"lease": [], "statics": [], "arplist": {}}
        rows = flatten_devices(devices)
        assert rows == []

    def test_format_csv_valid_output(self):
        devices = {
            "lease": [{"name": "pc", "ip": "192.168.1.1", "mac": "AA:BB:CC:DD:EE:01"}],
            "statics": [],
            "arplist": {},
        }

        output = format_csv(devices)

        assert "type,interface,name,ip,mac" in output
        assert "lease,,pc,192.168.1.1,AA:BB:CC:DD:EE:01" in output

    def test_format_csv_empty(self):
        devices = {"lease": [], "statics": [], "arplist": {}}
        output = format_csv(devices)
        assert output == ""

    def test_format_table_has_headers(self):
        devices = {
            "lease": [{"name": "pc", "ip": "192.168.1.1", "mac": "AA:BB:CC:DD:EE:01"}],
            "statics": [],
            "arplist": {},
        }

        output = format_table(devices)

        assert "TYPE" in output
        assert "INTERFACE" in output
        assert "NAME" in output
        assert "IP" in output
        assert "MAC" in output

    def test_format_table_has_data(self):
        devices = {
            "lease": [{"name": "pc", "ip": "192.168.1.1", "mac": "AA:BB:CC:DD:EE:01"}],
            "statics": [],
            "arplist": {},
        }

        output = format_table(devices)

        assert "lease" in output
        assert "pc" in output
        assert "192.168.1.1" in output

    def test_format_table_empty(self):
        devices = {"lease": [], "statics": [], "arplist": {}}
        output = format_table(devices)
        assert output == "No devices found."

    def test_format_json_compact(self):
        devices = {"lease": [], "statics": [], "arplist": {}}
        output = format_json(devices, pretty=False)
        assert output == '{"lease": [], "statics": [], "arplist": {}}'

    def test_format_json_pretty(self):
        devices = {"lease": [], "statics": [], "arplist": {}}
        output = format_json(devices, pretty=True)
        assert "\n" in output
        assert "  " in output


class TestInterfaceFilter:
    """Test interface filtering function."""

    def test_filter_by_interface_returns_matching(self):
        devices = {
            "lease": [{"name": "pc", "ip": "192.168.1.1", "mac": "AA:BB:CC:DD:EE:01"}],
            "statics": [],
            "arplist": {
                "br0": [{"name": "pc", "ip": "192.168.1.1", "mac": "AA:BB:CC:DD:EE:01"}],
                "br1": [{"name": "phone", "ip": "192.168.1.2", "mac": "AA:BB:CC:DD:EE:02"}],
            },
        }

        filtered = filter_by_interface(devices, "br0")

        assert "br0" in filtered["arplist"]
        assert "br1" not in filtered["arplist"]
        assert len(filtered["arplist"]["br0"]) == 1

    def test_filter_by_interface_preserves_lease_and_statics(self):
        devices = {
            "lease": [{"name": "pc", "ip": "192.168.1.1", "mac": "AA:BB:CC:DD:EE:01"}],
            "statics": [{"name": "server", "ip": "192.168.1.2", "mac": "AA:BB:CC:DD:EE:02"}],
            "arplist": {
                "br0": [{"name": "pc", "ip": "192.168.1.1", "mac": "AA:BB:CC:DD:EE:01"}],
            },
        }

        filtered = filter_by_interface(devices, "br0")

        assert len(filtered["lease"]) == 1
        assert len(filtered["statics"]) == 1

    def test_filter_by_interface_nonexistent_returns_empty_arplist(self):
        devices = {
            "lease": [{"name": "pc", "ip": "192.168.1.1", "mac": "AA:BB:CC:DD:EE:01"}],
            "statics": [],
            "arplist": {
                "br0": [{"name": "pc", "ip": "192.168.1.1", "mac": "AA:BB:CC:DD:EE:01"}],
            },
        }

        filtered = filter_by_interface(devices, "br99")

        assert filtered["arplist"] == {}
        assert len(filtered["lease"]) == 1

    def test_filter_by_interface_none_returns_unfiltered(self):
        devices = {
            "lease": [],
            "statics": [],
            "arplist": {
                "br0": [{"name": "pc", "ip": "192.168.1.1", "mac": "AA:BB:CC:DD:EE:01"}],
                "br1": [{"name": "phone", "ip": "192.168.1.2", "mac": "AA:BB:CC:DD:EE:02"}],
            },
        }

        filtered = filter_by_interface(devices, None)

        assert filtered == devices

    def test_filter_by_interface_empty_string_returns_unfiltered(self):
        devices = {
            "lease": [],
            "statics": [],
            "arplist": {
                "br0": [{"name": "pc", "ip": "192.168.1.1", "mac": "AA:BB:CC:DD:EE:01"}],
            },
        }

        filtered = filter_by_interface(devices, "")

        assert filtered == devices
