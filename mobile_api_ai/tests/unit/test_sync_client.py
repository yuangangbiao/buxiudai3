# -*- coding: utf-8 -*-
"""bridge/sync_client.py 单元测试"""
import pytest
from unittest.mock import patch, MagicMock
from bridge.sync_client import send


class TestSyncClient:
    def test_send_success(self):
        with patch('bridge.sync_client.urllib.request.urlopen') as mock_open:
            send('sub-step-report', {'order_no': 'T1', 'qty': 10})
            assert mock_open.called

    def test_send_timeout_fallback(self):
        with patch('bridge.sync_client.urllib.request.urlopen', side_effect=Exception('timeout')):
            result = send('sub-step-report', {'order_no': 'T2'})
            assert result is False

    def test_send_timeout_param(self):
        with patch('bridge.sync_client.urllib.request.urlopen') as mock_open:
            send('test', {}, timeout=3)
            call_args = mock_open.call_args
            assert call_args[1]['timeout'] == 3

    def test_send_default_url(self):
        # verify the module can be imported
        from bridge.sync_client import SYNC_BRIDGE_URL
        assert '8008' in SYNC_BRIDGE_URL


class TestSyncBridgeURL:
    def test_env_override(self, monkeypatch):
        monkeypatch.setenv('SYNC_BRIDGE_URL', 'http://custom:9999')
        import importlib, bridge.sync_client
        importlib.reload(bridge.sync_client)
        assert bridge.sync_client.SYNC_BRIDGE_URL == 'http://custom:9999'
        # 还原
        monkeypatch.delenv('SYNC_BRIDGE_URL', raising=False)
        importlib.reload(bridge.sync_client)
