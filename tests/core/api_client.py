# -*- coding: utf-8 -*-
"""
统一 API 客户端 - 封装 5 个服务的 HTTP 调用

修复 P0-3: 提供 test_security.py / test_performance.py 所需的 APIClient
"""
import json
import time
import logging
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from tests.core._config import SERVICES

logger = logging.getLogger(__name__)


class APIClient:
    """统一 API 客户端（带重试 + Session 复用）"""

    def __init__(self, service: str, timeout: float = 30.0, retry_count: int = 3):
        """
        Args:
            service: 服务名（desktop_web/container/dispatch/mobile/sync_bridge）
            timeout: 请求超时
            retry_count: 重试次数
        """
        if service not in SERVICES:
            raise ValueError(f"未知服务: {service}, 可选: {list(SERVICES.keys())}")

        self.service = service
        self.base_url = SERVICES[service]
        self.timeout = timeout
        self.session = self._create_session(retry_count)
        self.token: Optional[str] = None
        self.stats: Dict[str, Any] = {
            'total': 0, 'success': 0, 'failed': 0,
            'total_time_ms': 0.0, 'max_time_ms': 0.0,
        }

    def _create_session(self, retry_count: int) -> requests.Session:
        """创建带重试的 Session"""
        session = requests.Session()
        retry = Retry(
            total=retry_count,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=['GET', 'POST', 'PUT', 'DELETE'],
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    def _update_stats(self, ok: bool, elapsed_ms: float):
        """更新统计"""
        self.stats['total'] += 1
        self.stats['total_time_ms'] += elapsed_ms
        if elapsed_ms > self.stats['max_time_ms']:
            self.stats['max_time_ms'] = elapsed_ms
        if ok:
            self.stats['success'] += 1
        else:
            self.stats['failed'] += 1

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        """统一请求入口"""
        url = urljoin(self.base_url + '/', path.lstrip('/'))
        headers = kwargs.pop('headers', {})
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        headers.setdefault('Content-Type', 'application/json')

        start = time.time()
        try:
            kwargs.pop('timeout', None)
            resp = self.session.request(
                method, url,
                headers=headers,
                timeout=self.timeout,
                **kwargs
            )
            elapsed = (time.time() - start) * 1000
            ok = resp.status_code < 400
            self._update_stats(ok, elapsed)
            return resp
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            self._update_stats(False, elapsed)
            logger.error(f"请求失败 {method} {url}: {e}")
            raise

    def get(self, path: str, **kwargs) -> requests.Response:
        return self._request('GET', path, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        return self._request('POST', path, **kwargs)

    def put(self, path: str, **kwargs) -> requests.Response:
        return self._request('PUT', path, **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        return self._request('DELETE', path, **kwargs)

    def login(self, username: str, password: str) -> bool:
        """API 登录（dispatch/container 等）"""
        resp = self.post('/api/login', json={'username': username, 'password': password})
        if resp.status_code < 400:
            data = resp.json()
            self.token = data.get('token') or data.get('data', {}).get('token')
            return True
        return False

    def get_json(self, path: str, **kwargs) -> Any:
        """GET 并返回 JSON"""
        resp = self.get(path, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def post_json(self, path: str, data: dict, **kwargs) -> Any:
        """POST JSON 并返回 JSON"""
        resp = self.post(path, json=data, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def get_stats(self) -> Dict[str, Any]:
        """获取调用统计"""
        stats = self.stats.copy()
        if stats['total'] > 0:
            stats['avg_time_ms'] = stats['total_time_ms'] / stats['total']
            stats['success_rate'] = stats['success'] / stats['total']
        else:
            stats['avg_time_ms'] = 0.0
            stats['success_rate'] = 0.0
        return stats

    def close(self):
        self.session.close()


__all__ = ['APIClient']
