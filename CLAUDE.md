# CLAUDE.md

This file provides context for AI assistants working on this project.

## Project Overview

**tomato-api** is a Python CLI tool that fetches device information from Tomato Router firmware. It parses the router's web interface response to extract DHCP leases, static IP assignments, and ARP table entries.

## Architecture

### Module structure

The application consists of two main modules in `src/`:

- **`devlist.py`**: Fetches device lists (DHCP leases, ARP table, static assignments) from `/status-devices.asp`
- **`staticlist.py`**: Fetches static DHCP entries from `/basic-static.asp`

Both modules share `TLSAdapter` for legacy TLS support and follow the same patterns.

### Key components (devlist.py)

1. **TLSAdapter**: Custom HTTPS adapter to handle routers with legacy TLS configurations using relaxed cipher settings. Shared by both modules.

2. **Regex patterns**: Three compiled regex patterns parse the router's JavaScript response:
   - `lease_regex`: DHCP lease entries
   - `arplist_regex`: ARP table entries
   - `statics_regex`: Static IP assignments

3. **`get_devices()`**: Core function that fetches and parses router data. Returns a dict with `arplist`, `lease`, and `statics` keys.

4. **Format functions**: `format_json()`, `format_csv()`, `format_table()` handle output formatting.

5. **`filter_by_interface()`**: Filters ARP list by network interface.

6. **`main()`**: CLI entry point (`tomato-devlist`).

### Key components (staticlist.py)

1. **`DHCPD_STATIC_REGEX`**: Extracts `dhcpd_static` value from router response.

2. **`parse_static_entries()`**: Parses the `MAC<IP<Name<Flag>` format into a list of dicts.

3. **`get_static_list()`**: Fetches and parses static DHCP entries from `/basic-static.asp`.

4. **Format functions**: `format_json()`, `format_table()` for output.

5. **`main()`**: CLI entry point (`tomato-staticlist`).

### Data flow

```
Router HTML → Regex parsing → Dict structure → Format function → stdout
```

## Code Conventions

- **Type hints**: All functions have type annotations
- **Docstrings**: Google-style docstrings for public functions
- **Logging**: Use `logger.debug()` for debug output, errors go to stderr
- **Error handling**: Network errors caught in `main()`, return exit codes

## Testing

Tests use pytest with the `responses` library to mock HTTP requests.

### Test files

- **`tests/test_devlist.py`** (38 tests): Tests for the device list module
- **`tests/test_staticlist.py`** (26 tests): Tests for the static list module

### Test structure (devlist)

- `TestRegexPatterns`: Verify regex patterns match expected formats
- `TestGetRouterUrl`: URL building tests
- `TestGetDevices`: Core parsing logic with mocked responses
- `TestCLI`: Command-line interface tests
- `TestOutputFormats`: Format function tests
- `TestInterfaceFilter`: Filter function tests

### Test structure (staticlist)

- `TestParseStaticEntries`: Parsing logic tests
- `TestDhcpdStaticRegex`: Regex pattern tests
- `TestGetRouterUrl`: URL building tests
- `TestGetStaticList`: Core fetching function tests
- `TestOutputFormats`: Format function tests
- `TestCLI`: Command-line interface tests

### Running tests

```bash
# Run all tests (64 total)
pytest tests/ -v

# Run specific module tests
pytest tests/test_devlist.py -v
pytest tests/test_staticlist.py -v

# Run specific test class
pytest tests/test_devlist.py::TestCLI -v

# Run with coverage
pytest tests/ --cov=src
```

### Mock data

`SAMPLE_ROUTER_RESPONSE` in each test file simulates actual Tomato router HTML output. Use these as reference for expected formats.

## Common Tasks

### Adding a new CLI flag

1. Add `parser.add_argument()` in `main()`
2. Update epilog examples
3. Implement the feature
4. Add tests in `TestCLI`

### Adding a new output format

1. Create `format_<name>(devices: dict) -> str` function
2. Add choice to `--format` argument
3. Add conditional in `main()` output section
4. Add tests in `TestOutputFormats`

### Modifying regex patterns

1. Update the pattern string
2. Test against `SAMPLE_ROUTER_RESPONSE` in tests
3. Verify with `TestRegexPatterns` tests

### Adding a new router endpoint module

1. Create `src/<name>.py` following `staticlist.py` as template
2. Import `TLSAdapter` from `devlist` for HTTPS support
3. Add CLI entry point in `pyproject.toml` under `[project.scripts]`
4. Export in `src/__init__.py`
5. Create `tests/test_<name>.py` with mocked responses
6. Update documentation (README.md, CLAUDE.md)

## Dependencies

- **Runtime**: `requests`, `python-dotenv`
- **Dev**: `pytest`, `pytest-mock`, `pytest-cov`, `responses`

## Router Response Format

The Tomato router returns HTML with embedded JavaScript.

### Device list (`/status-devices.asp`)

```javascript
// DHCP leases: [name, ip, mac]
var dhcpd_lease = [['hostname','192.168.1.x','AA:BB:CC:DD:EE:FF'], ...];

// Static assignments: mac<ip<name (newline separated)
var nvram = { dhcpd_static: 'AA:BB:CC:DD:EE:FF<192.168.1.x<hostname\n...' };

// ARP list: [ip, mac, interface]
var arplist = [['192.168.1.x','AA:BB:CC:DD:EE:FF','br0'], ...];
```

### Static list (`/basic-static.asp`)

```javascript
// Static DHCP entries: MAC<IP<Name<Enabled (separated by >)
nvram = {
    'dhcpd_static': 'AA:BB:CC:DD:EE:FF<192.168.1.10<server<1>BB:CC:DD:EE:FF:00<192.168.1.20<desktop<1>'
};
// Flag: 1 = enabled, 0 = disabled
```

## Commit Convention

This project uses [Conventional Commits](https://www.conventionalcommits.org/). Always follow this format:

```
<type>[optional scope]: <description>

[optional body]

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

### Types

| Type | Use for |
|------|---------|
| `feat` | New features |
| `fix` | Bug fixes |
| `docs` | Documentation changes |
| `refactor` | Code changes that neither fix bugs nor add features |
| `test` | Adding or updating tests |
| `chore` | Maintenance tasks |

### Rules

- Use imperative mood: "add" not "added"
- Lowercase type and description
- No period at end
- Keep description under 50 characters
- Always include the co-author trailer

### Examples

```bash
feat: add csv output format
fix: handle empty arp list response
docs: update installation instructions
test: add tests for interface filter
feat(cli): add --interface filter option
```

## Notes

- SSL verification is disabled (`verify=False`) because Tomato routers use self-signed certificates
- Uses `TLSAdapter` with relaxed cipher settings (`DEFAULT@SECLEVEL=1`) for routers with legacy TLS
- Credentials can be set via `.env` file (`TOMATO_USERNAME`, `TOMATO_PASSWORD`) or CLI arguments
- Default router IP is `192.168.1.1` but configurable via `--router` or `TOMATO_ROUTER_IP` env var
- The `--interface` filter only affects `arplist`, not `lease` or `statics`
