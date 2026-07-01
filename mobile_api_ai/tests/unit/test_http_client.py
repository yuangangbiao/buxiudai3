# -*- coding: utf-8 -*-
"""
http_client 单元测试

覆盖：
- SyncBridgeClient POST/GET 请求
- ContainerCenterClient POST/GET 请求
- 超时处理
- HTTP 错误处理
- 异常抛出
- 会话管理
"""
import pytest
from unittest.mock import MagicMock, patch
import requests


class TestSyncBridgeClientPost:
    """SyncBridgeClient.post 测试"""

    def setup_method(self):
        from utils.http_client import SyncBridgeClient
        SyncBridgeClient._session = None

    def test_post_success(self):
        from utils.http_client import SyncBridgeClient
        with patch('utils.http_client.requests.Session') as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {'code': 0, 'data': 'ok'}
            mock_session.post.return_value = mock_resp
            SyncBridgeClient._session = mock_session

            result = SyncBridgeClient.post('/api/test', {'key': 'value'})
            assert result == {'code': 0, 'data': 'ok'}

    def test_post_timeout_raises(self):
        from utils.http_client import SyncBridgeClient, HttpClientError
        with patch('utils.http_client.requests.Session') as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.post.side_effect = requests.exceptions.Timeout()
            SyncBridgeClient._session = mock_session

            with pytest.raises(HttpClientError, match='请求超时'):
                SyncBridgeClient.post('/api/test')

    def test_post_request_exception_raises(self):
        from utils.http_client import SyncBridgeClient, HttpClientError
        with patch('utils.http_client.requests.Session') as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.post.side_effect = requests.exceptions.ConnectionError('fail')
            SyncBridgeClient._session = mock_session

            with pytest.raises(HttpClientError, match='请求失败'):
                SyncBridgeClient.post('/api/test')

    def test_post_uses_default_timeout(self):
        from utils.http_client import SyncBridgeClient
        with patch('utils.http_client.requests.Session') as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_resp = MagicMock()
            mock_resp.json.return_value = {}
            mock_session.post.return_value = mock_resp
            SyncBridgeClient._session = mock_session

            SyncBridgeClient.post('/api/test')
            assert mock_session.post.call_args[1]['timeout'] == SyncBridgeClient.DEFAULT_TIMEOUT

    def test_post_uses_custom_timeout(self):
        from utils.http_client import SyncBridgeClient
        with patch('utils.http_client.requests.Session') as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_resp = MagicMock()
            mock_resp.json.return_value = {}
            mock_session.post.return_value = mock_resp
            SyncBridgeClient._session = mock_session

            SyncBridgeClient.post('/api/test', timeout=5)
            assert mock_session.post.call_args[1]['timeout'] == 5

    def test_post_http_error_raises(self):
        from utils.http_client import SyncBridgeClient, HttpClientError
        with patch('utils.http_client.requests.Session') as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_resp = MagicMock()
            mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError('500')
            mock_session.post.return_value = mock_resp
            SyncBridgeClient._session = mock_session

            with pytest.raises(HttpClientError):
                SyncBridgeClient.post('/api/test')


class TestSyncBridgeClientGet:
    """SyncBridgeClient.get 测试"""

    def setup_method(self):
        from utils.http_client import SyncBridgeClient
        SyncBridgeClient._session = None

    def test_get_success(self):
        from utils.http_client import SyncBridgeClient
        with patch('utils.http_client.requests.Session') as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_resp = MagicMock()
            mock_resp.json.return_value = {'code': 0}
            mock_session.get.return_value = mock_resp
            SyncBridgeClient._session = mock_session

            result = SyncBridgeClient.get('/api/list', {'page': 1})
            assert result == {'code': 0}

    def test_get_request_exception(self):
        from utils.http_client import SyncBridgeClient, HttpClientError
        with patch('utils.http_client.requests.Session') as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.get.side_effect = requests.exceptions.ConnectionError()
            SyncBridgeClient._session = mock_session

            with pytest.raises(HttpClientError):
                SyncBridgeClient.get('/api/list')

    def test_get_http_error(self):
        from utils.http_client import SyncBridgeClient, HttpClientError
        with patch('utils.http_client.requests.Session') as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_resp = MagicMock()
            mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError()
            mock_session.get.return_value = mock_resp
            SyncBridgeClient._session = mock_session

            with pytest.raises(HttpClientError):
                SyncBridgeClient.get('/api/list')


class TestContainerCenterClientPost:
    """ContainerCenterClient.post 测试"""

    def setup_method(self):
        from utils.http_client import ContainerCenterClient
        ContainerCenterClient._session = None

    def test_post_success(self):
        from utils.http_client import ContainerCenterClient
        with patch('utils.http_client.requests.Session') as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_resp = MagicMock()
            mock_resp.json.return_value = {'code': 0}
            mock_session.post.return_value = mock_resp
            ContainerCenterClient._session = mock_session

            result = ContainerCenterClient.post('/api/test', {'a': 1})
            assert result == {'code': 0}

    def test_post_timeout(self):
        from utils.http_client import ContainerCenterClient, HttpClientError
        with patch('utils.http_client.requests.Session') as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.post.side_effect = requests.exceptions.Timeout()
            ContainerCenterClient._session = mock_session

            with pytest.raises(HttpClientError, match='请求超时'):
                ContainerCenterClient.post('/api/test')

    def test_post_error(self):
        from utils.http_client import ContainerCenterClient, HttpClientError
        with patch('utils.http_client.requests.Session') as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.post.side_effect = requests.exceptions.RequestException('fail')
            ContainerCenterClient._session = mock_session

            with pytest.raises(HttpClientError):
                ContainerCenterClient.post('/api/test')


class TestContainerCenterClientGet:
    """ContainerCenterClient.get 测试"""

    def setup_method(self):
        from utils.http_client import ContainerCenterClient
        ContainerCenterClient._session = None

    def test_get_success(self):
        from utils.http_client import ContainerCenterClient
        with patch('utils.http_client.requests.Session') as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_resp = MagicMock()
            mock_resp.json.return_value = {'data': [1, 2, 3]}
            mock_session.get.return_value = mock_resp
            ContainerCenterClient._session = mock_session

            result = ContainerCenterClient.get('/api/items')
            assert result == {'data': [1, 2, 3]}

    def test_get_error(self):
        from utils.http_client import ContainerCenterClient, HttpClientError
        with patch('utils.http_client.requests.Session') as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.get.side_effect = requests.exceptions.RequestException()
            ContainerCenterClient._session = mock_session

            with pytest.raises(HttpClientError):
                ContainerCenterClient.get('/api/items')


class TestSessionManagement:
    """会话管理测试"""

    def test_sync_bridge_session_lazy_init(self):
        from utils.http_client import SyncBridgeClient
        SyncBridgeClient._session = None
        with patch('utils.http_client.requests.Session') as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            SyncBridgeClient._get_session()
            assert mock_session_cls.called

    def test_sync_bridge_session_reused(self):
        from utils.http_client import SyncBridgeClient
        SyncBridgeClient._session = None
        existing = MagicMock()
        SyncBridgeClient._session = existing
        result = SyncBridgeClient._get_session()
        assert result is existing

    def test_container_center_session_lazy_init(self):
        from utils.http_client import ContainerCenterClient
        ContainerCenterClient._session = None
        with patch('utils.http_client.requests.Session') as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            ContainerCenterClient._get_session()
            assert mock_session_cls.called

    def test_user_agent_header_set(self):
        from utils.http_client import SyncBridgeClient
        SyncBridgeClient._session = None
        with patch('utils.http_client.requests.Session') as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            SyncBridgeClient._get_session()
            assert mock_session.headers.update.called


class TestHttpClientError:
    """HttpClientError 异常类测试"""

    def test_error_inherits_exception(self):
        from utils.http_client import HttpClientError
        err = HttpClientError('test')
        assert isinstance(err, Exception)
        assert str(err) == 'test'
