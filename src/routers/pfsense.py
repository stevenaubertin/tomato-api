"""pfSense router adapter (stub).

Known API approaches:
- REST API (requires pfSense-pkg-API package):
  GET /api/v1/services/dhcpd/static_mapping
  GET /api/v1/diagnostics/arp
- FauxAPI: https://github.com/ndejong/pfsense_fauxapi
"""

from .base import RouterAdapter


class PfSenseAdapter(RouterAdapter):
    """Stub adapter for pfSense routers."""

    def get_statics(self) -> list[dict[str, str]]:
        raise NotImplementedError("pfSense router support is not yet implemented")

    def get_leases(self) -> list[dict[str, str]]:
        raise NotImplementedError("pfSense router support is not yet implemented")

    def get_arp_table(self) -> dict[str, list[dict[str, str]]]:
        raise NotImplementedError("pfSense router support is not yet implemented")
