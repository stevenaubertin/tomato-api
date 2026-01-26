# tomato-api

Python CLI tool to fetch device information from Tomato Router firmware.

## Features

- Fetch DHCP leases, static assignments, and ARP table entries
- Fetch static DHCP configuration entries
- Find unknown devices not in static DHCP list with MAC vendor lookup
- Multiple output formats: JSON, CSV, and ASCII table
- Filter results by network interface
- Configurable router IP via CLI or environment variable
- Debug logging for troubleshooting

## Installation

### From source

```bash
git clone https://github.com/stevenaubertin/tomato-api.git
cd tomato-api
pip install -e .
```

### Using pip (local)

```bash
pip install .
```

## Usage

The package provides three CLI commands:

| Command | Description |
|---------|-------------|
| `tomato-devlist` | Fetch DHCP leases, ARP table, and static assignments |
| `tomato-staticlist` | Fetch static DHCP configuration entries |
| `tomato-unknown` | Find devices not in static DHCP list |

### tomato-devlist

Fetches device lists from the router.

```bash
tomato-devlist <username> <password>
```

#### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--router` | `-r` | Router IP address (default: 192.168.1.1) |
| `--format` | `-f` | Output format: json, csv, table (default: json) |
| `--pretty` | `-p` | Pretty print JSON output |
| `--interface` | `-i` | Filter ARP list by interface (e.g., br0) |
| `--verbose` | `-v` | Enable debug logging |

### Examples

```bash
# Default JSON output
tomato-devlist admin password

# Pretty-printed JSON
tomato-devlist admin password --pretty

# Table format
tomato-devlist admin password --format table

# CSV export
tomato-devlist admin password --format csv > devices.csv

# Custom router IP
tomato-devlist admin password --router 192.168.0.1

# Filter by interface
tomato-devlist admin password --interface br0

# Debug mode
tomato-devlist admin password --verbose
```

### tomato-staticlist

Fetches static DHCP configuration entries from the router.

```bash
tomato-staticlist <username> <password>
```

#### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--router` | `-r` | Router IP address (default: 192.168.1.1) |
| `--format` | `-f` | Output format: json, table (default: json) |
| `--pretty` | `-p` | Pretty print JSON output |
| `--verbose` | `-v` | Enable debug logging |

#### Examples

```bash
# Default JSON output
tomato-staticlist admin password

# Table format
tomato-staticlist admin password --format table

# Pretty-printed JSON
tomato-staticlist admin password --pretty
```

### tomato-unknown

Finds connected devices that are not in the static DHCP list. Optionally looks up MAC address vendors.

```bash
tomato-unknown <username> <password>
```

#### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--router` | `-r` | Router IP address (default: 192.168.1.1) |
| `--format` | `-f` | Output format: json, table (default: table) |
| `--pretty` | `-p` | Pretty print JSON output |
| `--no-vendor` | `-n` | Skip MAC vendor lookup (faster) |
| `--verbose` | `-v` | Enable debug logging |

#### Examples

```bash
# Find unknown devices with vendor lookup
tomato-unknown admin password

# Skip vendor lookup for faster results
tomato-unknown --no-vendor

# JSON output
tomato-unknown --format json --pretty
```

### Environment variables

| Variable | Description |
|----------|-------------|
| `TOMATO_USERNAME` | Router admin username |
| `TOMATO_PASSWORD` | Router admin password |
| `TOMATO_ROUTER_IP` | Router IP address (default: 192.168.1.1) |

You can set these in a `.env` file:

```bash
TOMATO_USERNAME=admin
TOMATO_PASSWORD=password
TOMATO_ROUTER_IP=192.168.1.1
```

Then run without arguments:

```bash
tomato-devlist --format table
tomato-staticlist --format table
tomato-unknown
```

## Output formats

### JSON (default)

```json
{
  "arplist": {
    "br0": [
      {"name": "desktop", "mac": "AA:BB:CC:DD:EE:01", "ip": "192.168.1.100"}
    ]
  },
  "lease": [
    {"name": "desktop", "mac": "AA:BB:CC:DD:EE:01", "ip": "192.168.1.100"}
  ],
  "statics": [
    {"name": "server", "mac": "AA:BB:CC:DD:EE:02", "ip": "192.168.1.50"}
  ]
}
```

### Table

```
TYPE    INTERFACE  NAME      IP             MAC
------  ---------  --------  -------------  -----------------
lease              desktop   192.168.1.100  AA:BB:CC:DD:EE:01
static             server    192.168.1.50   AA:BB:CC:DD:EE:02
arp     br0        desktop   192.168.1.100  AA:BB:CC:DD:EE:01
```

### CSV

```csv
type,interface,name,ip,mac
lease,,desktop,192.168.1.100,AA:BB:CC:DD:EE:01
static,,server,192.168.1.50,AA:BB:CC:DD:EE:02
arp,br0,desktop,192.168.1.100,AA:BB:CC:DD:EE:01
```

## Development

### Setup

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -e ".[dev]"
```

### Running tests

```bash
pytest tests/ -v
```

### Project structure

```
tomato-api/
├── src/
│   ├── __init__.py          # Package exports
│   ├── devlist.py           # Device list module
│   ├── staticlist.py        # Static DHCP entries module
│   └── unknown_devices.py   # Unknown devices finder module
├── tests/
│   ├── __init__.py
│   ├── test_devlist.py          # Device list tests
│   ├── test_staticlist.py       # Static list tests
│   └── test_unknown_devices.py  # Unknown devices tests
├── pyproject.toml           # Package configuration
├── requirements.txt         # Dependencies
├── .env                     # Environment variables (not in git)
└── README.md
```

## Requirements

- Python 3.8+
- requests
- python-dotenv

## TODO

- [ ] Update router firmware to [FreshTomato](https://freshtomato.org/) (the actively maintained fork)

## License

MIT License - see [LICENSE](LICENSE) for details.
