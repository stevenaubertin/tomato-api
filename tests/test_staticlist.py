"""Unit tests for staticlist.py"""

import json

import pytest
import requests
import responses

from src.staticlist import (
    DEFAULT_ROUTER_IP,
    DHCPD_STATIC_REGEX,
    format_json,
    format_table,
    get_router_url,
    get_static_list,
    main,
    parse_static_entries,
)

# Sample router response HTML (simulates Tomato router output)
SAMPLE_ROUTER_RESPONSE = """
<title>Static DHCP/ARP/BW</title>
<content>
<script type="text/javascript">
nvram = {
    'at_update': '',
    'lan_ipaddr': '192.168.1.1',
    'lan_netmask': '255.255.255.0',
    'dhcpd_static': 'AA:BB:CC:DD:EE:01<192.168.1.10<server<1>AA:BB:CC:DD:EE:02<192.168.1.20<desktop<1>AA:BB:CC:DD:EE:03<192.168.1.30<disabled-device<0>',
    'dhcpd_startip': '192.168.1.2',
    'http_id': 'TIDtest123'
};
</script>
</content>
"""

EMPTY_ROUTER_RESPONSE = """
<title>Static DHCP/ARP/BW</title>
<content>
<script type="text/javascript">
nvram = {
    'dhcpd_static': '',
    'http_id': 'TIDtest123'
};
</script>
</content>
"""


class TestParseStaticEntries:
    """Test the parse_static_entries function."""

    def test_parse_valid_entries(self):
        dhcpd_static = (
            "AA:BB:CC:DD:EE:01<192.168.1.10<server<1>AA:BB:CC:DD:EE:02<192.168.1.20<desktop<1>"
        )
        entries = parse_static_entries(dhcpd_static)

        assert len(entries) == 2
        assert entries[0]["mac"] == "AA:BB:CC:DD:EE:01"
        assert entries[0]["ip"] == "192.168.1.10"
        assert entries[0]["name"] == "server"
        assert entries[0]["enabled"] is True

    def test_parse_disabled_entry(self):
        dhcpd_static = "AA:BB:CC:DD:EE:03<192.168.1.30<disabled<0>"
        entries = parse_static_entries(dhcpd_static)

        assert len(entries) == 1
        assert entries[0]["enabled"] is False

    def test_parse_empty_string(self):
        entries = parse_static_entries("")
        assert entries == []

    def test_parse_single_entry(self):
        dhcpd_static = "AA:BB:CC:DD:EE:01<192.168.1.10<server<1>"
        entries = parse_static_entries(dhcpd_static)

        assert len(entries) == 1
        assert entries[0]["name"] == "server"

    def test_parse_entry_without_flag(self):
        # Some routers might not include the flag
        dhcpd_static = "AA:BB:CC:DD:EE:01<192.168.1.10<server"
        entries = parse_static_entries(dhcpd_static)

        assert len(entries) == 1
        assert entries[0]["enabled"] is True  # Default to enabled


class TestDhcpdStaticRegex:
    """Test the regex pattern for extracting dhcpd_static."""

    def test_regex_matches_sample_response(self):
        match = DHCPD_STATIC_REGEX.search(SAMPLE_ROUTER_RESPONSE)
        assert match is not None
        assert "AA:BB:CC:DD:EE:01" in match.group(1)

    def test_regex_matches_empty_response(self):
        match = DHCPD_STATIC_REGEX.search(EMPTY_ROUTER_RESPONSE)
        assert match is not None
        assert match.group(1) == ""


class TestGetRouterUrl:
    """Test URL building function."""

    def test_default_ip(self):
        url = get_router_url(DEFAULT_ROUTER_IP)
        assert url == "https://192.168.1.1/basic-static.asp"

    def test_custom_ip(self):
        url = get_router_url("10.0.0.1")
        assert url == "https://10.0.0.1/basic-static.asp"


class TestGetStaticList:
    """Test the main static list fetching function."""

    @responses.activate
    def test_get_static_list_returns_list(self):
        responses.add(
            responses.GET,
            "https://192.168.1.1/basic-static.asp",
            body=SAMPLE_ROUTER_RESPONSE,
            status=200,
        )

        result = get_static_list("admin", "password", "192.168.1.1")

        assert isinstance(result, list)
        assert len(result) == 3

    @responses.activate
    def test_get_static_list_parses_entries(self):
        responses.add(
            responses.GET,
            "https://192.168.1.1/basic-static.asp",
            body=SAMPLE_ROUTER_RESPONSE,
            status=200,
        )

        result = get_static_list("admin", "password", "192.168.1.1")

        assert result[0]["mac"] == "AA:BB:CC:DD:EE:01"
        assert result[0]["ip"] == "192.168.1.10"
        assert result[0]["name"] == "server"
        assert result[0]["enabled"] is True

    @responses.activate
    def test_get_static_list_handles_disabled(self):
        responses.add(
            responses.GET,
            "https://192.168.1.1/basic-static.asp",
            body=SAMPLE_ROUTER_RESPONSE,
            status=200,
        )

        result = get_static_list("admin", "password", "192.168.1.1")

        # Third entry should be disabled
        assert result[2]["enabled"] is False

    @responses.activate
    def test_get_static_list_handles_empty_response(self):
        responses.add(
            responses.GET,
            "https://192.168.1.1/basic-static.asp",
            body=EMPTY_ROUTER_RESPONSE,
            status=200,
        )

        result = get_static_list("admin", "password", "192.168.1.1")

        assert result == []

    @responses.activate
    def test_get_static_list_raises_on_auth_failure(self):
        responses.add(
            responses.GET,
            "https://192.168.1.1/basic-static.asp",
            status=401,
        )

        with pytest.raises(requests.exceptions.HTTPError):
            get_static_list("admin", "wrong", "192.168.1.1")


class TestOutputFormats:
    """Test output formatting functions."""

    def test_format_table_has_headers(self):
        entries = [
            {"mac": "AA:BB:CC:DD:EE:01", "ip": "192.168.1.10", "name": "server", "enabled": True}
        ]

        output = format_table(entries)

        assert "NAME" in output
        assert "IP" in output
        assert "MAC" in output
        assert "ENABLED" in output

    def test_format_table_has_data(self):
        entries = [
            {"mac": "AA:BB:CC:DD:EE:01", "ip": "192.168.1.10", "name": "server", "enabled": True}
        ]

        output = format_table(entries)

        assert "server" in output
        assert "192.168.1.10" in output
        assert "AA:BB:CC:DD:EE:01" in output
        assert "yes" in output

    def test_format_table_shows_disabled(self):
        entries = [
            {"mac": "AA:BB:CC:DD:EE:01", "ip": "192.168.1.10", "name": "server", "enabled": False}
        ]

        output = format_table(entries)

        assert "no" in output

    def test_format_table_empty(self):
        output = format_table([])
        assert output == "No static entries found."

    def test_format_json_compact(self):
        entries = [
            {"mac": "AA:BB:CC:DD:EE:01", "ip": "192.168.1.10", "name": "server", "enabled": True}
        ]
        output = format_json(entries, pretty=False)

        # Should be valid JSON
        data = json.loads(output)
        assert len(data) == 1
        assert data[0]["name"] == "server"

    def test_format_json_pretty(self):
        entries = [
            {"mac": "AA:BB:CC:DD:EE:01", "ip": "192.168.1.10", "name": "server", "enabled": True}
        ]
        output = format_json(entries, pretty=True)

        assert "\n" in output
        assert "  " in output


class TestCLI:
    """Test command-line interface."""

    @responses.activate
    def test_main_returns_zero_on_success(self):
        responses.add(
            responses.GET,
            "https://192.168.1.1/basic-static.asp",
            body=SAMPLE_ROUTER_RESPONSE,
            status=200,
        )

        result = main(["admin", "password"])
        assert result == 0

    @responses.activate
    def test_main_returns_nonzero_on_auth_failure(self):
        responses.add(
            responses.GET,
            "https://192.168.1.1/basic-static.asp",
            status=401,
        )

        result = main(["admin", "wrong"])
        assert result == 1

    @responses.activate
    def test_main_accepts_custom_router(self):
        responses.add(
            responses.GET,
            "https://10.0.0.1/basic-static.asp",
            body=SAMPLE_ROUTER_RESPONSE,
            status=200,
        )

        result = main(["admin", "password", "--router", "10.0.0.1"])
        assert result == 0

    @responses.activate
    def test_main_table_format(self, capsys):
        responses.add(
            responses.GET,
            "https://192.168.1.1/basic-static.asp",
            body=SAMPLE_ROUTER_RESPONSE,
            status=200,
        )

        main(["admin", "password", "--format", "table"])
        captured = capsys.readouterr()

        assert "NAME" in captured.out
        assert "server" in captured.out

    @responses.activate
    def test_main_json_output_is_valid(self, capsys):
        responses.add(
            responses.GET,
            "https://192.168.1.1/basic-static.asp",
            body=SAMPLE_ROUTER_RESPONSE,
            status=200,
        )

        main(["admin", "password"])
        captured = capsys.readouterr()

        # Should be valid JSON
        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert len(data) == 3

    @responses.activate
    def test_main_pretty_flag(self, capsys):
        responses.add(
            responses.GET,
            "https://192.168.1.1/basic-static.asp",
            body=SAMPLE_ROUTER_RESPONSE,
            status=200,
        )

        main(["admin", "password", "--pretty"])
        captured = capsys.readouterr()

        assert "\n" in captured.out
        assert "  " in captured.out
