"""Shared fixtures for tomato-api tests."""

import os

import pytest

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture
def router_html_fixture():
    """Sanitized Asus/Tomato router /status-devices.asp response."""
    with open(os.path.join(FIXTURES_DIR, "asus_status_devices.html")) as f:
        return f.read()


@pytest.fixture
def sample_devices():
    """Pre-parsed device data matching the fixture HTML."""
    return {
        "lease": [
            {"name": "swarm0", "ip": "192.168.1.50", "mac": "B8:27:EB:80:09:E3"},
            {"name": "laptop", "ip": "192.168.1.100", "mac": "AA:BB:CC:DD:EE:01"},
            {"name": "phone", "ip": "192.168.1.101", "mac": "AA:BB:CC:DD:EE:02"},
        ],
        "statics": [
            {"name": "swarm0", "mac": "B8:27:EB:80:09:E3", "ip": "192.168.1.50"},
            {"name": "swarm1", "mac": "B8:27:EB:64:64:85", "ip": "192.168.1.51"},
            {"name": "swarm2", "mac": "B8:27:EB:C5:D2:7F", "ip": "192.168.1.52"},
        ],
        "arplist": {
            "br0": [
                {"name": "swarm0", "mac": "B8:27:EB:80:09:E3", "ip": "192.168.1.50"},
                {"name": "swarm1", "mac": "B8:27:EB:64:64:85", "ip": "192.168.1.51"},
                {"name": "laptop", "mac": "AA:BB:CC:DD:EE:01", "ip": "192.168.1.100"},
            ],
        },
    }
