"""Tomato/Asus router adapter — parses /status-devices.asp HTML response."""

import logging
import re

import requests
import urllib3
from requests.auth import HTTPBasicAuth

from .base import RouterAdapter
from .ssl_helpers import LegacySSLAdapter

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

# Regex patterns for Tomato router response parsing
_NAME = r"[a-zA-Z0-9]*-?[a-zA-Z0-9]+"
_IPV4 = r"(?:[0-9]{1,3}\.){3}[0-9]{1,3}"
_MAC = r"[a-fA-F0-9]{2}:[a-fA-F0-9]{2}:[a-fA-F0-9]{2}:[a-fA-F0-9]{2}:[a-fA-F0-9]{2}:[a-fA-F0-9]{2}"

LEASE_RE = re.compile(
    rf"\[('{_NAME}','{_IPV4}','{_MAC}')",
    re.IGNORECASE | re.MULTILINE,
)
STATICS_RE = re.compile(
    rf"{_MAC}<{_IPV4}<{_NAME}",
    re.IGNORECASE | re.MULTILINE,
)
ARPLIST_RE = re.compile(
    rf"'{_IPV4}','{_MAC}','{_NAME}'",
    re.IGNORECASE | re.MULTILINE,
)

DEFAULT_ENDPOINT = "/status-devices.asp"


class TomatoAdapter(RouterAdapter):
    """Adapter for Tomato/Asus routers."""

    def _fetch(self) -> str:
        session = requests.Session()
        session.mount("https://", LegacySSLAdapter())
        auth = HTTPBasicAuth(self.username, self.password)
        url = f"https://{self.host}{DEFAULT_ENDPOINT}"
        logger.debug(f"Connecting to router at {url}")
        response = session.get(url, auth=auth, verify=False, timeout=30)
        response.raise_for_status()
        logger.debug(f"Received response: {response.status_code} ({len(response.text)} bytes)")
        return str(response.text)

    def get_leases(self) -> list[dict[str, str]]:
        text = self._fetch()
        return self._parse_leases(text)

    def get_statics(self) -> list[dict[str, str]]:
        text = self._fetch()
        return self._parse_statics(text)

    def get_arp_table(self) -> dict[str, list[dict[str, str]]]:
        text = self._fetch()
        leases = self._parse_leases(text)
        statics = self._parse_statics(text)
        return self._parse_arp(text, statics + leases)

    def get_all_devices(self) -> dict:
        """Fetch once and parse all sections."""
        text = self._fetch()
        leases = self._parse_leases(text)
        statics = self._parse_statics(text)
        arp = self._parse_arp(text, statics + leases)
        return {"arplist": arp, "lease": leases, "statics": statics}

    @staticmethod
    def _parse_leases(text: str) -> list[dict[str, str]]:
        raw = [str(i).replace("'", "").split(",") for i in LEASE_RE.findall(text)]
        return [
            {
                "name": i[0],
                "mac": i[1] if ":" in i[1] else i[2],
                "ip": i[1] if ":" in i[2] else i[2],
            }
            for i in raw
        ]

    @staticmethod
    def _parse_statics(text: str) -> list[dict[str, str]]:
        raw = [str(i).replace("'", "").split("<") for i in STATICS_RE.findall(text)]
        return [
            {
                "name": i[-1],
                "mac": i[0] if ":" in i[0] else i[1],
                "ip": i[0] if ":" in i[1] else i[1],
            }
            for i in raw
        ]

    @staticmethod
    def _parse_arp(
        text: str, known_devices: list[dict[str, str]]
    ) -> dict[str, list[dict[str, str]]]:
        def find_name(mac: str) -> str:
            matches = [d for d in known_devices if d["mac"] == mac]
            return matches[0]["name"] if matches else ""

        raw = [str(i).replace("'", "").split(",") for i in ARPLIST_RE.findall(text)]
        arp: dict[str, list[dict[str, str]]] = {}
        for entry in raw:
            interface = entry[-1]
            values = entry[:-1]
            mac = values[0] if ":" in values[0] else values[1]
            ip = values[1] if ":" in values[0] else values[0]
            name = find_name(mac)
            device = {"name": name, "mac": mac, "ip": ip}
            arp.setdefault(interface, []).append(device)
        return arp
