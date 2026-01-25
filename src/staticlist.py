#!/usr/bin/env python3
"""Fetch and manage static DHCP/ARP entries from Tomato Router."""

import argparse
import json
import logging
import os
import re
import sys
from typing import Optional

from dotenv import load_dotenv
import requests
from requests.auth import HTTPBasicAuth

from .devlist import TLSAdapter, setup_logging

# Module logger
logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_ROUTER_IP = "192.168.1.1"
DEFAULT_ENDPOINT = "/basic-static.asp"

# Regex to extract dhcpd_static from response
DHCPD_STATIC_REGEX = re.compile(r"'dhcpd_static':\s*'([^']*)'")


def get_router_url(router_ip: str) -> str:
    """Build the router URL from the IP address."""
    return f"https://{router_ip}{DEFAULT_ENDPOINT}"


def parse_static_entries(dhcpd_static: str) -> list:
    """
    Parse the dhcpd_static string into a list of entries.

    Format: MAC<IP<Name<Flag>MAC<IP<Name<Flag>...
    """
    if not dhcpd_static:
        return []

    entries = []
    # Split by '>' to get individual entries, filter empty strings
    raw_entries = [e for e in dhcpd_static.split('>') if e]

    for raw in raw_entries:
        parts = raw.split('<')
        if len(parts) >= 3:
            entry = {
                'mac': parts[0],
                'ip': parts[1],
                'name': parts[2],
                'enabled': parts[3] == '1' if len(parts) > 3 else True
            }
            entries.append(entry)

    return entries


def get_static_list(username: str, password: str, router_ip: str) -> list:
    """
    Fetch static DHCP entries from the Tomato router.

    Args:
        username: Router admin username
        password: Router admin password
        router_ip: Router IP address

    Returns:
        List of static DHCP entries

    Raises:
        requests.RequestException: If the network request fails
    """
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    url = get_router_url(router_ip)
    auth = HTTPBasicAuth(username, password)

    logger.debug(f"Connecting to router at {url}")
    session = requests.Session()
    session.mount('https://', TLSAdapter())
    response = session.get(url, auth=auth, verify=False, timeout=30)
    response.raise_for_status()
    logger.debug(f"Received response: {response.status_code} ({len(response.text)} bytes)")

    # Extract dhcpd_static from response
    match = DHCPD_STATIC_REGEX.search(response.text)
    if not match:
        logger.warning("Could not find dhcpd_static in response")
        return []

    dhcpd_static = match.group(1)
    logger.debug(f"Found dhcpd_static: {len(dhcpd_static)} chars")

    entries = parse_static_entries(dhcpd_static)
    logger.debug(f"Parsed {len(entries)} static entries")

    return entries


def format_table(entries: list) -> str:
    """Format entries as ASCII table."""
    if not entries:
        return "No static entries found."

    headers = ['NAME', 'IP', 'MAC', 'ENABLED']
    col_widths = [
        max(len(headers[0]), max(len(e['name']) for e in entries)),
        max(len(headers[1]), max(len(e['ip']) for e in entries)),
        max(len(headers[2]), max(len(e['mac']) for e in entries)),
        len(headers[3]),
    ]

    def format_row(values):
        return '  '.join(v.ljust(w) for v, w in zip(values, col_widths))

    lines = [
        format_row(headers),
        format_row(['-' * w for w in col_widths]),
    ]
    for entry in entries:
        lines.append(format_row([
            entry['name'],
            entry['ip'],
            entry['mac'],
            'yes' if entry['enabled'] else 'no',
        ]))

    return '\n'.join(lines)


def format_json(entries: list, pretty: bool = False) -> str:
    """Format entries as JSON."""
    if pretty:
        return json.dumps(entries, indent=2)
    return json.dumps(entries)


def main(argv: Optional[list] = None) -> int:
    """Main entry point for the CLI."""
    load_dotenv()

    parser = argparse.ArgumentParser(
        description='Fetch static DHCP entries from a Tomato Router',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s                              # Use credentials from .env
  %(prog)s admin password               # Use explicit credentials
  %(prog)s --format table
  %(prog)s --router 192.168.0.1
        '''
    )
    parser.add_argument(
        'username',
        nargs='?',
        default=os.environ.get('TOMATO_USERNAME'),
        help='Router admin username (default: $TOMATO_USERNAME)'
    )
    parser.add_argument(
        'password',
        nargs='?',
        default=os.environ.get('TOMATO_PASSWORD'),
        help='Router admin password (default: $TOMATO_PASSWORD)'
    )
    parser.add_argument(
        '--router', '-r',
        default=os.environ.get('TOMATO_ROUTER_IP', DEFAULT_ROUTER_IP),
        help=f'Router IP address (default: $TOMATO_ROUTER_IP or {DEFAULT_ROUTER_IP})'
    )
    parser.add_argument(
        '--format', '-f',
        choices=['json', 'table'],
        default='json',
        help='Output format (default: json)'
    )
    parser.add_argument(
        '--pretty', '-p',
        action='store_true',
        help='Pretty print JSON output'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output for debugging'
    )

    args = parser.parse_args(argv)
    setup_logging(args.verbose)

    if not args.username or not args.password:
        parser.error(
            "Username and password are required. Provide them as arguments "
            "or set TOMATO_USERNAME and TOMATO_PASSWORD environment variables."
        )

    try:
        entries = get_static_list(args.username, args.password, args.router)

        if args.format == 'table':
            print(format_table(entries))
        else:
            print(format_json(entries, args.pretty))

        return 0

    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to router at {args.router}", file=sys.stderr)
        return 1
    except requests.exceptions.Timeout:
        print("Error: Connection to router timed out", file=sys.stderr)
        return 1
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("Error: Authentication failed - check username and password", file=sys.stderr)
        else:
            print(f"Error: HTTP {e.response.status_code} - {e.response.reason}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
