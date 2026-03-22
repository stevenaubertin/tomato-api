"""Abstract base class for router adapters."""

import json
from abc import ABC, abstractmethod


class RouterAdapter(ABC):
    """Base class for router adapters that fetch device information."""

    def __init__(self, host: str, username: str, password: str) -> None:
        self.host = host
        self.username = username
        self.password = password

    @abstractmethod
    def get_statics(self) -> list[dict[str, str]]:
        """Return list of dicts with static DHCP reservations.

        Each dict has keys: name, mac, ip
        """

    @abstractmethod
    def get_leases(self) -> list[dict[str, str]]:
        """Return list of dicts with active DHCP leases.

        Each dict has keys: name, mac, ip
        """

    @abstractmethod
    def get_arp_table(self) -> dict[str, list[dict[str, str]]]:
        """Return dict mapping interface names to lists of device dicts.

        Each device dict has keys: name, mac, ip
        """

    def find_hostname_by_mac(self, mac: str) -> str:
        """Look up hostname from MAC in static reservations."""
        for device in self.get_statics():
            if device["mac"].upper() == mac.upper():
                return device["name"]
        return ""

    def get_all_devices(self) -> dict:
        """Return all device data in the standard format."""
        return {
            "arplist": self.get_arp_table(),
            "lease": self.get_leases(),
            "statics": self.get_statics(),
        }

    def to_json(self) -> str:
        """Return JSON string of all device data."""
        return json.dumps(self.get_all_devices())
