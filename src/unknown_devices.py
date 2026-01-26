#!/usr/bin/env python3
"""Find connected devices not in the static DHCP list and identify them by MAC vendor."""

import argparse
import json
import logging
import os
import sys
import urllib.request
from typing import Optional

from dotenv import load_dotenv

from .devlist import get_devices, setup_logging
from .staticlist import get_static_list

# Module logger
logger = logging.getLogger(__name__)


def lookup_mac_vendor(mac: str) -> str:
    """
    Look up the vendor/manufacturer for a MAC address.

    Args:
        mac: MAC address in any format (colons, dashes, or no separators)

    Returns:
        Vendor name or 'Unknown' if lookup fails
    """
    try:
        url = f"https://api.maclookup.app/v2/macs/{mac}"
        req = urllib.request.Request(url, headers={"User-Agent": "tomato-api/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return str(data.get("company", "Unknown"))
    except Exception as e:
        logger.debug(f"MAC lookup failed for {mac}: {e}")
        return "Unknown"


def find_unknown_devices(
    username: str, password: str, router_ip: str, lookup_vendor: bool = True
) -> list[dict]:
    """
    Find devices connected to the router that are not in the static DHCP list.

    Args:
        username: Router admin username
        password: Router admin password
        router_ip: Router IP address
        lookup_vendor: Whether to look up MAC address vendors (slower)

    Returns:
        List of unknown device dicts with keys: name, ip, mac, interface, vendor
    """
    # Fetch data from router
    devices = get_devices(username, password, router_ip)
    statics = get_static_list(username, password, router_ip)

    # Build set of static MACs (uppercase for comparison)
    static_macs = {s["mac"].upper() for s in statics}

    # Find connected devices not in static list
    unknown = []
    for interface, arp_devices in devices.get("arplist", {}).items():
        for device in arp_devices:
            mac_upper = device["mac"].upper()
            if mac_upper not in static_macs:
                entry = {
                    "name": device.get("name") or "",
                    "ip": device["ip"],
                    "mac": device["mac"],
                    "interface": interface,
                    "vendor": "",
                }
                if lookup_vendor:
                    entry["vendor"] = lookup_mac_vendor(device["mac"])
                unknown.append(entry)

    # Sort by IP address
    unknown.sort(key=lambda x: tuple(int(p) for p in x["ip"].split(".")))

    return unknown


def format_table(devices: list[dict]) -> str:
    """Format devices as ASCII table."""
    if not devices:
        return "No unknown devices found."

    headers = ["NAME", "IP", "MAC", "INTERFACE", "VENDOR"]
    col_widths = [
        max(len(headers[0]), max((len(d["name"]) for d in devices), default=0)),
        max(len(headers[1]), max((len(d["ip"]) for d in devices), default=0)),
        max(len(headers[2]), max((len(d["mac"]) for d in devices), default=0)),
        max(len(headers[3]), max((len(d["interface"]) for d in devices), default=0)),
        max(len(headers[4]), max((len(d["vendor"]) for d in devices), default=0)),
    ]

    def format_row(values: list[str]) -> str:
        return "  ".join(v.ljust(w) for v, w in zip(values, col_widths))

    lines = [
        format_row(headers),
        format_row(["-" * w for w in col_widths]),
    ]
    for device in devices:
        lines.append(
            format_row(
                [
                    device["name"] or "(unknown)",
                    device["ip"],
                    device["mac"],
                    device["interface"],
                    device["vendor"],
                ]
            )
        )

    return "\n".join(lines)


def format_json(devices: list[dict], pretty: bool = False) -> str:
    """Format devices as JSON."""
    if pretty:
        return json.dumps(devices, indent=2)
    return json.dumps(devices)


def main(argv: Optional[list] = None) -> int:
    """Main entry point for the CLI."""
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Find connected devices not in the static DHCP list",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # Use credentials from .env
  %(prog)s admin password               # Use explicit credentials
  %(prog)s --format table
  %(prog)s --no-vendor                  # Skip vendor lookup (faster)
        """,
    )
    parser.add_argument(
        "username",
        nargs="?",
        default=os.environ.get("TOMATO_USERNAME"),
        help="Router admin username (default: $TOMATO_USERNAME)",
    )
    parser.add_argument(
        "password",
        nargs="?",
        default=os.environ.get("TOMATO_PASSWORD"),
        help="Router admin password (default: $TOMATO_PASSWORD)",
    )
    parser.add_argument(
        "--router",
        "-r",
        default=os.environ.get("TOMATO_ROUTER_IP", "192.168.1.1"),
        help="Router IP address (default: $TOMATO_ROUTER_IP or 192.168.1.1)",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["json", "table"],
        default="table",
        help="Output format (default: table)",
    )
    parser.add_argument("--pretty", "-p", action="store_true", help="Pretty print JSON output")
    parser.add_argument(
        "--no-vendor",
        "-n",
        action="store_true",
        help="Skip MAC vendor lookup (faster)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output for debugging"
    )

    args = parser.parse_args(argv)
    setup_logging(args.verbose)

    if not args.username or not args.password:
        parser.error(
            "Username and password are required. Provide them as arguments "
            "or set TOMATO_USERNAME and TOMATO_PASSWORD environment variables."
        )

    try:
        devices = find_unknown_devices(
            args.username,
            args.password,
            args.router,
            lookup_vendor=not args.no_vendor,
        )

        if args.format == "table":
            print(format_table(devices))
        else:
            print(format_json(devices, args.pretty))

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
