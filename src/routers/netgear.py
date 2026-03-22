"""Netgear router adapter (stub).

Known API approaches:
- Screen-scrape: http://<router>/DEV_device_info.htm
- SOAP API: port 5000, SOAPAction headers for GetAttachDevice
- Python library: https://github.com/MatMaul/pynetgear
"""

from .base import RouterAdapter


class NetgearAdapter(RouterAdapter):
    """Stub adapter for Netgear routers."""

    def get_statics(self) -> list[dict[str, str]]:
        raise NotImplementedError("Netgear router support is not yet implemented")

    def get_leases(self) -> list[dict[str, str]]:
        raise NotImplementedError("Netgear router support is not yet implemented")

    def get_arp_table(self) -> dict[str, list[dict[str, str]]]:
        raise NotImplementedError("Netgear router support is not yet implemented")
