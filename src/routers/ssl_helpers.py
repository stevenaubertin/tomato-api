"""SSL helpers for routers with legacy/self-signed certificates."""

import ssl
from typing import Any

from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager


class LegacySSLAdapter(HTTPAdapter):
    """Requests adapter that allows legacy SSL ciphers (SECLEVEL=1).

    Required for routers with old self-signed certificates.
    """

    def init_poolmanager(self, *args: Any, **kwargs: Any) -> Any:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
        kwargs["ssl_context"] = ctx
        self.poolmanager = PoolManager(*args, **kwargs)
        return None
