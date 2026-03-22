#!/usr/bin/env python3
"""Find a device on the network by name, IP, or MAC address."""

import argparse
import json
import logging
import os
import sys
from typing import Optional

from dotenv import load_dotenv

from .devlist import get_devices, setup_logging

# Module logger
logger = logging.getLogger(__name__)


def search_devices(devices: dict, query: str) -> list[dict]:
    """Search for devices matching a query string across all sections.

    Args:
        devices: Device data dict from get_devices()
        query: Search string to match against name, IP, or MAC (case-insensitive)

    Returns:
        List of matching device dicts with an added 'source' key
    """
    query_lower = query.lower()
    results = []

    for device in devices.get("statics", []):
        if _matches(device, query_lower):
            results.append({**device, "source": "static"})

    for device in devices.get("lease", []):
        if _matches(device, query_lower):
            results.append({**device, "source": "lease"})

    for interface, arp_devices in devices.get("arplist", {}).items():
        for device in arp_devices:
            if _matches(device, query_lower):
                results.append({**device, "source": f"arp:{interface}"})

    return results


def _matches(device: dict, query_lower: str) -> bool:
    """Check if a device matches the search query."""
    return (
        query_lower in device.get("name", "").lower()
        or query_lower in device.get("ip", "").lower()
        or query_lower in device.get("mac", "").lower()
    )


def format_table(results: list[dict]) -> str:
    """Format search results as ASCII table."""
    if not results:
        return "No matching devices found."

    headers = ["SOURCE", "NAME", "IP", "MAC"]
    col_widths = [
        max(len(headers[0]), max(len(r["source"]) for r in results)),
        max(len(headers[1]), max(len(r["name"]) for r in results)),
        max(len(headers[2]), max(len(r["ip"]) for r in results)),
        max(len(headers[3]), max(len(r["mac"]) for r in results)),
    ]

    def format_row(values: list[str]) -> str:
        return "  ".join(v.ljust(w) for v, w in zip(values, col_widths))

    lines = [
        format_row(headers),
        format_row(["-" * w for w in col_widths]),
    ]
    for r in results:
        lines.append(format_row([r["source"], r["name"], r["ip"], r["mac"]]))

    return "\n".join(lines)


def format_json(results: list[dict], pretty: bool = False) -> str:
    """Format search results as JSON."""
    if pretty:
        return json.dumps(results, indent=2)
    return json.dumps(results)


def main(argv: Optional[list] = None) -> int:
    """Main entry point for the CLI."""
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Find a device on the network by name, IP, or MAC address",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s laptop                     # Search by name
  %(prog)s 192.168.1.100              # Search by IP
  %(prog)s AA:BB:CC                   # Search by partial MAC
  %(prog)s --format table laptop
        """,
    )
    parser.add_argument("query", help="Search string (matches name, IP, or MAC)")
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
        devices = get_devices(args.username, args.password, args.router)
        results = search_devices(devices, args.query)

        if args.format == "table":
            print(format_table(results))
        else:
            print(format_json(results, args.pretty))

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
