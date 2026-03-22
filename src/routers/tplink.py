"""TP-Link router adapter (stub).

Known API approaches:
- Screen-scrape: http://<router>/userRpm/AssignedIpAddrListRpm.htm
- Newer models: REST API at http://<router>/cgi-bin/luci/
- Python library: https://github.com/AlexandrEroworthy/TP-Link-Archer-C6U
"""

from .base import RouterAdapter


class TPLinkAdapter(RouterAdapter):
    """Stub adapter for TP-Link routers."""

    def get_statics(self) -> list[dict[str, str]]:
        raise NotImplementedError("TP-Link router support is not yet implemented")

    def get_leases(self) -> list[dict[str, str]]:
        raise NotImplementedError("TP-Link router support is not yet implemented")

    def get_arp_table(self) -> dict[str, list[dict[str, str]]]:
        raise NotImplementedError("TP-Link router support is not yet implemented")
