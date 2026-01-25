#!/usr/bin/env python3

import argparse
import csv
import io
import json
import logging
import os
import re
import sys
from typing import Optional

import ssl

from dotenv import load_dotenv
import requests
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth
import urllib3


class TLSAdapter(HTTPAdapter):
    """Custom adapter to handle routers with legacy TLS configurations."""

    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.set_ciphers('DEFAULT@SECLEVEL=1')
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)

# Module logger
logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging based on verbosity level."""
    level = logging.DEBUG if verbose else logging.WARNING

    # Remove existing handlers to allow reconfiguration
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    logging.basicConfig(
        level=level,
        format='%(levelname)s: %(message)s',
        stream=sys.stderr,
    )
    logger.setLevel(level)


# Regex patterns for parsing router response
name_regex_str = r"[a-zA-Z0-9]*-?[a-zA-Z0-9]+"
ipv4_regex_str = r"(?:[0-9]{1,3}\.){3}[0-9]{1,3}"
mac_regex_str = r"[a-fA-F0-9]{2}:[a-fA-F0-9]{2}:[a-fA-F0-9]{2}:[a-fA-F0-9]{2}:[a-fA-F0-9]{2}:[a-fA-F0-9]{2}"

lease_regex = re.compile(
    r"\[('{}','{}','{}')".format(name_regex_str, ipv4_regex_str, mac_regex_str),
    re.IGNORECASE | re.MULTILINE
)
arplist_regex = re.compile(
    r"'{}','{}','{}'".format(ipv4_regex_str, mac_regex_str, name_regex_str),
    re.IGNORECASE | re.MULTILINE
)
statics_regex = re.compile(
    r"{}<{}<{}".format(mac_regex_str, ipv4_regex_str, name_regex_str),
    re.IGNORECASE | re.MULTILINE
)

# Default configuration
DEFAULT_ROUTER_IP = "192.168.1.1"
DEFAULT_ENDPOINT = "/status-devices.asp"


def get_router_url(router_ip: str) -> str:
    """Build the router URL from the IP address."""
    return f"https://{router_ip}{DEFAULT_ENDPOINT}"


def get_devices(username: str, password: str, router_ip: str) -> dict:
    """
    Fetch device information from the Tomato router.

    Args:
        username: Router admin username
        password: Router admin password
        router_ip: Router IP address

    Returns:
        Dictionary containing arplist, lease, and statics data

    Raises:
        requests.RequestException: If the network request fails
        ValueError: If the response cannot be parsed
    """
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    url = get_router_url(router_ip)
    auth = HTTPBasicAuth(username, password)

    logger.debug(f"Connecting to router at {url}")
    session = requests.Session()
    session.mount('https://', TLSAdapter())
    response = session.get(url, auth=auth, verify=False, timeout=30)
    response.raise_for_status()
    logger.debug(f"Received response: {response.status_code} ({len(response.text)} bytes)")

    devlist = response.text

    # Parse the response using regex
    lease_matches = [str(i).replace("'", '').split(',') for i in lease_regex.findall(devlist)]
    statics_matches = [str(i).replace("'", '').split('<') for i in statics_regex.findall(devlist)]
    arplist_matches = [str(i).replace("'", '').split(',') for i in arplist_regex.findall(devlist)]
    logger.debug(f"Parsed {len(lease_matches)} leases, {len(statics_matches)} statics, {len(arplist_matches)} arp entries")

    # Format lease entries
    leases = [
        {
            'name': entry[0],
            'mac': entry[1] if ':' in entry[1] else entry[2],
            'ip': entry[1] if ':' in entry[2] else entry[2],
        } for entry in lease_matches
    ]

    # Format static entries
    statics = [
        {
            'name': entry[-1],
            'mac': entry[0] if ':' in entry[0] else entry[1],
            'ip': entry[0] if ':' in entry[1] else entry[1],
        } for entry in statics_matches
    ]

    # Helper to find device name by MAC address
    def find_name(mac: str) -> str:
        combined = statics + leases
        matches = [device for device in combined if device['mac'] == mac]
        return matches[0]['name'] if matches else ''

    # Format arplist entries, grouped by interface
    arplist = {}
    for entry in arplist_matches:
        interface = entry[-1]
        values = entry[:-1]
        mac = values[0] if ':' in values[0] else values[1]
        ip = values[1] if ':' in values[0] else values[0]
        name = find_name(mac)

        device = {
            'name': name,
            'mac': mac,
            'ip': ip
        }

        if interface in arplist:
            arplist[interface].append(device)
        else:
            arplist[interface] = [device]

    return {
        'arplist': arplist,
        'lease': leases,
        'statics': statics
    }


def flatten_devices(devices: dict) -> list:
    """Flatten device data into a list of rows with source type."""
    rows = []

    for device in devices.get('lease', []):
        rows.append({
            'type': 'lease',
            'interface': '',
            'name': device['name'],
            'ip': device['ip'],
            'mac': device['mac'],
        })

    for device in devices.get('statics', []):
        rows.append({
            'type': 'static',
            'interface': '',
            'name': device['name'],
            'ip': device['ip'],
            'mac': device['mac'],
        })

    for interface, interface_devices in devices.get('arplist', {}).items():
        for device in interface_devices:
            rows.append({
                'type': 'arp',
                'interface': interface,
                'name': device['name'],
                'ip': device['ip'],
                'mac': device['mac'],
            })

    return rows


def format_csv(devices: dict) -> str:
    """Format devices as CSV."""
    rows = flatten_devices(devices)
    if not rows:
        return ""

    output = io.StringIO()
    fieldnames = ['type', 'interface', 'name', 'ip', 'mac']
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def format_table(devices: dict) -> str:
    """Format devices as ASCII table."""
    rows = flatten_devices(devices)
    if not rows:
        return "No devices found."

    headers = ['TYPE', 'INTERFACE', 'NAME', 'IP', 'MAC']
    col_widths = [
        max(len(headers[0]), max(len(r['type']) for r in rows)),
        max(len(headers[1]), max(len(r['interface']) for r in rows)),
        max(len(headers[2]), max(len(r['name']) for r in rows)),
        max(len(headers[3]), max(len(r['ip']) for r in rows)),
        max(len(headers[4]), max(len(r['mac']) for r in rows)),
    ]

    def format_row(values):
        return '  '.join(v.ljust(w) for v, w in zip(values, col_widths))

    lines = [
        format_row(headers),
        format_row(['-' * w for w in col_widths]),
    ]
    for row in rows:
        lines.append(format_row([
            row['type'],
            row['interface'],
            row['name'],
            row['ip'],
            row['mac'],
        ]))

    return '\n'.join(lines)


def format_json(devices: dict, pretty: bool = False) -> str:
    """Format devices as JSON."""
    if pretty:
        return json.dumps(devices, indent=2)
    return json.dumps(devices)


def filter_by_interface(devices: dict, interface: str) -> dict:
    """Filter devices to only include entries from the specified interface."""
    if not interface:
        return devices

    filtered_arplist = {}
    if interface in devices.get('arplist', {}):
        filtered_arplist[interface] = devices['arplist'][interface]

    return {
        'arplist': filtered_arplist,
        'lease': devices.get('lease', []),
        'statics': devices.get('statics', []),
    }


def main(argv: Optional[list] = None) -> int:
    """Main entry point for the CLI."""
    # Load environment variables from .env file if it exists
    load_dotenv()

    parser = argparse.ArgumentParser(
        description='Fetch device information from a Tomato Router',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s                              # Use credentials from .env
  %(prog)s admin password               # Use explicit credentials
  %(prog)s --router 192.168.0.1
  %(prog)s --format table
  %(prog)s --format csv > devices.csv
  %(prog)s --interface br0
  %(prog)s --verbose
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
        choices=['json', 'csv', 'table'],
        default='json',
        help='Output format (default: json)'
    )
    parser.add_argument(
        '--pretty', '-p',
        action='store_true',
        help='Pretty print JSON output (only applies to json format)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output for debugging'
    )
    parser.add_argument(
        '--interface', '-i',
        default=None,
        help='Filter ARP list by interface (e.g., br0, br1)'
    )

    args = parser.parse_args(argv)
    setup_logging(args.verbose)

    # Validate required credentials
    if not args.username or not args.password:
        parser.error(
            "Username and password are required. Provide them as arguments "
            "or set TOMATO_USERNAME and TOMATO_PASSWORD environment variables (or in .env file)."
        )

    try:
        devices = get_devices(args.username, args.password, args.router)

        if args.interface:
            logger.debug(f"Filtering by interface: {args.interface}")
            devices = filter_by_interface(devices, args.interface)

        if args.format == 'csv':
            print(format_csv(devices), end='')
        elif args.format == 'table':
            print(format_table(devices))
        else:
            print(format_json(devices, args.pretty))

        return 0

    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to router at {args.router}", file=sys.stderr)
        return 1
    except requests.exceptions.Timeout:
        print(f"Error: Connection to router timed out", file=sys.stderr)
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
