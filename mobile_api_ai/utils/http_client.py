# -*- coding: utf-8 -*-
"""
统一 HTTP 客户端
所有 HTTP 调用必须通过此类，禁止直接使用 requests/urllib
"""
import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning('requests 库未安装，HTTP 客户端不可用')


class HttpClientError(Exception):
    """HTTP 客户端异常"""
    pass


class SyncBridgeClient:
    """统一调用 sync_bridge (8008) 的客户端"""

    BASE_URL = os.getenv('SYNC_BRIDGE_URL', 'http://127.0.0.1:8008')
    DEFAULT_TIMEOUT = 10
    _session = None

    @classmethod
    def _get_session(cls):
        if cls._session is None:
            cls._session = requests.Session()
            cls._session.headers.update({'User-Agent': 'mobile-api-ai/1.0'})
        return cls._session

    @classmethod
    def post(cls, endpoint: str, data: Optional[Dict[str, Any]] = None,
             timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        POST 请求

        Args:
            endpoint: API 端点，如 '/api/sync/sub-step-report'
            data: 请求体数据，会自动序列化为 JSON
            timeout: 超时时间（秒），默认 10

        Returns:
            dict: 响应 JSON

        Raises:
            HttpClientError: 请求失败时抛出
        """
        if not REQUESTS_AVAILABLE:
            raise HttpClientError('requests 库未安装')

        url = f"{cls.BASE_URL}{endpoint}"
        timeout = timeout or cls.DEFAULT_TIMEOUT

        try:
            resp = cls._get_session().post(url, json=data, timeout=timeout)
            resp.raise_for_status()
            result = resp.json()
            logger.info('[SyncBridge] POST %s -> %d', endpoint, resp.status_code)
            return result
        except requests.exceptions.Timeout:
            logger.error('[SyncBridge] POST %s 超时(%ds)', endpoint, timeout)
            raise HttpClientError(f'请求超时: {endpoint}')
        except requests.exceptions.RequestException as e:
            logger.error('[SyncBridge] POST %s 失败: %s', endpoint, e)
            raise HttpClientError(f'请求失败: {e}')

    @classmethod
    def get(cls, endpoint: str, params: Optional[Dict[str, Any]] = None,
            timeout: Optional[int] = None) -> Dict[str, Any]:
        """GET 请求"""
        if not REQUESTS_AVAILABLE:
            raise HttpClientError('requests 库未安装')

        url = f"{cls.BASE_URL}{endpoint}"
        timeout = timeout or cls.DEFAULT_TIMEOUT

        try:
            resp = cls._get_session().get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            logger.error('[SyncBridge] GET %s 失败: %s', endpoint, e)
            raise HttpClientError(f'请求失败: {e}')


class ContainerCenterClient:
    """统一调用容器中心 API (5002) 的客户端"""

    BASE_URL = os.getenv('CONTAINER_CENTER_URL', 'http://127.0.0.1:5002')
    DEFAULT_TIMEOUT = 10
    _session = None

    @classmethod
    def _get_session(cls):
        if cls._session is None:
            cls._session = requests.Session()
            cls._session.headers.update({'User-Agent': 'mobile-api-ai/1.0'})
        return cls._session

    @classmethod
    def post(cls, endpoint: str, data: Optional[Dict[str, Any]] = None,
             timeout: Optional[int] = None) -> Dict[str, Any]:
        url = f"{cls.BASE_URL}{endpoint}"
        timeout = timeout or cls.DEFAULT_TIMEOUT

        try:
            resp = cls._get_session().post(url, json=data, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.Timeout:
            logger.error('[ContainerCenter] POST %s 超时(%ds)', endpoint, timeout)
            raise HttpClientError(f'请求超时: {endpoint}')
        except requests.exceptions.RequestException as e:
            logger.error('[ContainerCenter] POST %s 失败: %s', endpoint, e)
            raise HttpClientError(f'请求失败: {e}')

    @classmethod
    def get(cls, endpoint: str, params: Optional[Dict[str, Any]] = None,
            timeout: Optional[int] = None) -> Dict[str, Any]:
        url = f"{cls.BASE_URL}{endpoint}"
        timeout = timeout or cls.DEFAULT_TIMEOUT

        try:
            resp = cls._get_session().get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            logger.error('[ContainerCenter] GET %s 失败: %s', endpoint, e)
            raise HttpClientError(f'请求失败: {e}')
