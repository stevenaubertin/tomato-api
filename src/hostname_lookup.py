#!/usr/bin/env python3
"""Look up a device hostname by MAC address from router static DHCP reservations."""

import argparse
import logging
import os
import sys
from typing import Optional

from dotenv import load_dotenv

from .devlist import get_devices, setup_logging

# Module logger
logger = logging.getLogger(__name__)


def find_hostname(devices: dict, mac: str) -> str:
    """Find hostname for a MAC address in static reservations.

    Args:
        devices: Device data dict from get_devices()
        mac: MAC address to look up

    Returns:
        Hostname string, or empty string if not found
    """
    mac_upper = mac.upper()
    for device in devices.get("statics", []):
        if device["mac"].upper() == mac_upper:
            return str(device["name"])
    return ""


def main(argv: Optional[list] = None) -> int:
    """Main entry point for the CLI."""
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Look up a device hostname by MAC address from router static DHCP reservations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s AA:BB:CC:DD:EE:FF
  %(prog)s --router 192.168.0.1 AA:BB:CC:DD:EE:FF
        """,
    )
    parser.add_argument("mac", help="MAC address to look up")
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
        hostname = find_hostname(devices, args.mac)

        if not hostname:
            known_macs = [d["mac"] for d in devices.get("statics", [])]
            print(
                f'MAC "{args.mac}" not found in router static reservations.',
                file=sys.stderr,
            )
            logger.debug(f"Known MACs: {', '.join(known_macs) if known_macs else '(none)'}")
            return 1

        print(hostname)
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
