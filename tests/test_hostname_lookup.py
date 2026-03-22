"""Tests for hostname_lookup module."""

import responses

from src.hostname_lookup import find_hostname, main

SAMPLE_DEVICES = {
    "lease": [
        {"name": "laptop", "ip": "192.168.1.100", "mac": "AA:BB:CC:DD:EE:01"},
    ],
    "statics": [
        {"name": "server", "ip": "192.168.1.50", "mac": "AA:BB:CC:DD:EE:10"},
        {"name": "nas", "ip": "192.168.1.51", "mac": "AA:BB:CC:DD:EE:11"},
    ],
    "arplist": {},
}

SAMPLE_ROUTER_RESPONSE = """
<script>
var dhcpd_lease = [['laptop','192.168.1.100','AA:BB:CC:DD:EE:01']];
var nvram = {
dhcpd_static: 'AA:BB:CC:DD:EE:10<192.168.1.50<server\nAA:BB:CC:DD:EE:11<192.168.1.51<nas'
};
var arplist = [];
</script>
"""


class TestFindHostname:
    def test_finds_existing_mac(self):
        assert find_hostname(SAMPLE_DEVICES, "AA:BB:CC:DD:EE:10") == "server"

    def test_finds_case_insensitive(self):
        assert find_hostname(SAMPLE_DEVICES, "aa:bb:cc:dd:ee:10") == "server"

    def test_returns_empty_for_unknown_mac(self):
        assert find_hostname(SAMPLE_DEVICES, "FF:FF:FF:FF:FF:FF") == ""

    def test_returns_empty_for_lease_only_mac(self):
        # Hostname lookup only checks statics, not leases
        assert find_hostname(SAMPLE_DEVICES, "AA:BB:CC:DD:EE:01") == ""

    def test_empty_statics(self):
        devices = {"statics": [], "lease": [], "arplist": {}}
        assert find_hostname(devices, "AA:BB:CC:DD:EE:10") == ""


class TestCLI:
    @responses.activate
    def test_main_prints_hostname(self, capsys):
        responses.add(
            responses.GET,
            "https://192.168.1.1/status-devices.asp",
            body=SAMPLE_ROUTER_RESPONSE,
            status=200,
        )
        result = main(["AA:BB:CC:DD:EE:10", "admin", "password"])
        assert result == 0
        assert "server" in capsys.readouterr().out

    @responses.activate
    def test_main_returns_nonzero_on_no_match(self, capsys):
        responses.add(
            responses.GET,
            "https://192.168.1.1/status-devices.asp",
            body=SAMPLE_ROUTER_RESPONSE,
            status=200,
        )
        result = main(["FF:FF:FF:FF:FF:FF", "admin", "password"])
        assert result == 1
        assert "not found" in capsys.readouterr().err

    @responses.activate
    def test_main_custom_router(self, capsys):
        responses.add(
            responses.GET,
            "https://10.0.0.1/status-devices.asp",
            body=SAMPLE_ROUTER_RESPONSE,
            status=200,
        )
        result = main(["AA:BB:CC:DD:EE:11", "admin", "password", "--router", "10.0.0.1"])
        assert result == 0
        assert "nas" in capsys.readouterr().out
