"""Tests for SSL helpers."""

from src.routers.ssl_helpers import LegacySSLAdapter


class TestLegacySSLAdapter:
    def test_creates_poolmanager(self):
        adapter = LegacySSLAdapter()
        adapter.init_poolmanager()
        assert adapter.poolmanager is not None

    def test_is_http_adapter(self):
        from requests.adapters import HTTPAdapter

        adapter = LegacySSLAdapter()
        assert isinstance(adapter, HTTPAdapter)

    def test_backward_compat_alias(self):
        from src.devlist import TLSAdapter

        assert TLSAdapter is LegacySSLAdapter
