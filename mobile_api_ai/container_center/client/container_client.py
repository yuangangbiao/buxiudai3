import os
import json
import time
import hashlib
import logging
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin

import requests

logger = logging.getLogger(__name__)


class ContainerCenterError(Exception):
    pass


class ContainerCenterConnectionError(ContainerCenterError):
    pass


class ContainerCenterAuthError(ContainerCenterError):
    pass


class ContainerCenterAPIError(ContainerCenterError):
    pass


class ContainerCenterClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        secret: Optional[str] = None,
        connect_timeout: int = 5,
        read_timeout: int = 30,
        max_retries: int = 3,
    ):
        self.base_url = (
            base_url or os.environ.get('CONTAINER_CENTER_URL', 'http://localhost:5002')
        ).rstrip('/')
        self.secret = secret or os.environ.get('CONTAINER_CENTER_SECRET', '')
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.max_retries = max_retries

        self._session = requests.Session()
        self._session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'ContainerCenterSDK/4.0',
        })

    def _build_signature(self, body: bytes) -> str:
        payload = body + self.secret.encode('utf-8')
        return hashlib.sha256(payload).hexdigest()

    def _request(self, method: str, path: str, json_data: Optional[Dict] = None,
                 query_params: Optional[Dict] = None) -> Dict:
        url = urljoin(self.base_url + '/', path.lstrip('/'))
        body_bytes = b''
        headers = {}

        if method.upper() == 'GET' and json_data:
            query_params = {**(query_params or {}), **json_data}
            json_data = None

        if json_data:
            body_bytes = json.dumps(json_data, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
            if self.secret:
                headers['X-CC-Signature'] = self._build_signature(body_bytes)

        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = self._session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    data=body_bytes if json_data else None,
                    params=query_params,
                    timeout=(self.connect_timeout, self.read_timeout),
                )

                if resp.status_code == 401:
                    raise ContainerCenterAuthError(f"鉴权失败: {resp.text}")
                if resp.status_code == 403:
                    raise ContainerCenterAuthError(f"权限不足: {resp.text}")

                result = resp.json()

                if result.get('code') != 0:
                    raise ContainerCenterAPIError(
                        f"API错误(code={result.get('code')}): {result.get('message', 'unknown')}"
                    )

                return result.get('data', result)

            except (ContainerCenterAuthError, ContainerCenterAPIError):
                raise
            except requests.ConnectionError as e:
                last_exception = ContainerCenterConnectionError(f"连接失败: {e}")
            except requests.Timeout as e:
                last_exception = ContainerCenterConnectionError(f"请求超时: {e}")
            except requests.RequestException as e:
                last_exception = ContainerCenterConnectionError(f"请求异常: {e}")
            except json.JSONDecodeError as e:
                last_exception = ContainerCenterAPIError(f"响应解析失败: {e}")

            if attempt < self.max_retries:
                wait = 2 ** attempt
                logger.warning(f"请求重试({attempt + 1}/{self.max_retries}): {method} {path}, 等待{wait}s")
                time.sleep(wait)

        raise last_exception

    def query_documents(
        self,
        doc_type: str,
        status: Optional[str] = None,
        q: Optional[str] = None,
        page: int = 1,
        size: int = 50,
        sort: str = '-updated_at',
        all: bool = False,
    ) -> Dict:
        params = {'page': page, 'size': size, 'sort': sort}
        if status:
            params['status'] = status
        if q:
            params['q'] = q
        if all:
            params['all'] = '1'
        result = self._request('GET', f'/api/v4/documents/{doc_type}', query_params=params)
        if isinstance(result, dict):
            items = result.get('items', result.get('data', []))
            if isinstance(items, list):
                result['items'] = items
                result['data'] = items
        return result

    def get_document(self, doc_type: str, doc_id: str) -> Dict:
        return self._request('GET', f'/api/v4/documents/{doc_type}/{doc_id}')

    def create_document(self, doc_type: str, data: Dict) -> Dict:
        return self._request('POST', f'/api/v4/documents/{doc_type}', json_data=data)

    def update_document(self, doc_type: str, doc_id: str, fields: Dict) -> Dict:
        return self._request('PUT', f'/api/v4/documents/{doc_type}/{doc_id}', json_data=fields)

    def update_document_status(self, doc_type: str, doc_id: str, status: str) -> Dict:
        return self._request('PUT', f'/api/v4/documents/{doc_type}/{doc_id}/status', json_data={'status': status})

    def delete_document(self, doc_type: str, doc_id: str) -> bool:
        result = self._request('DELETE', f'/api/v4/documents/{doc_type}/{doc_id}')
        return result.get('deleted', False)

    def get_packages(self, doc_type: str = 'work_order', status: Optional[str] = None, limit: int = 100) -> List[Dict]:
        result = self.query_documents(doc_type=doc_type, status=status, size=limit)
        if isinstance(result, list):
            return result
        items = result.get('items', result.get('data', []))
        return items if isinstance(items, list) else []

    def get_package(self, pkg_id: str, doc_type: str = 'work_order') -> Dict:
        return self.get_document(doc_type=doc_type, doc_id=pkg_id)

    def save_package(self, data: Dict, doc_type: str = 'work_order') -> Dict:
        if data.get('id'):
            return self.update_document(doc_type=doc_type, doc_id=data['id'], fields=data.get('data', {}))
        return self.create_document(doc_type=doc_type, data=data.get('data', {}))

    def send_message(self, content: str, to: str, msg_type: str = 'markdown', channel: str = 'all') -> Dict:
        return self._request('POST', '/api/v4/messages', json_data={
            'content': content,
            'to': to,
            'msg_type': msg_type,
            'channel': channel,
        })

    def distribute(self, task_id: str, operator_id: str) -> Dict:
        return self._request('POST', '/api/v4/distribute', json_data={
            'task_id': task_id,
            'operator_id': operator_id,
        })

    def get_operators(self, department: Optional[str] = None) -> List[Dict]:
        query_params = {}
        if department:
            query_params['department'] = department
        result = self._request('GET', '/api/operators', query_params=query_params)
        operators = result.get('operators', result.get('data', [])) if isinstance(result, dict) else result
        return operators if isinstance(operators, list) else []

    def get_alert_rules(self) -> Dict:
        """[F22 行动项 3-硬迁移 2026-06-20] 获取告警规则 → 5003 调度中心

        旧：5002 /api/v4/configs/alert_rules (随 container_center/api/ 死代码包删除而消失)
        新：5003 /api/dispatch-center/configs/alert_rules
        """
        dispatch_url = os.environ.get('DISPATCH_CENTER_URL', 'http://localhost:5003')
        url = dispatch_url.rstrip('/') + '/api/dispatch-center/configs/alert_rules'
        resp = self._session.get(url, timeout=(self.connect_timeout, self.read_timeout))
        resp.raise_for_status()
        data = resp.json()
        return data.get('data', {}) if isinstance(data, dict) else data

    def update_alert_rules(self, rules: Dict) -> Dict:
        """[F22 行动项 3-硬迁移 2026-06-20] 更新告警规则 → 5003 调度中心

        旧：PUT 5002 /api/v4/configs/alert_rules (随死代码包删除而消失)
        新：PUT 5003 /api/dispatch-center/configs/alert_rules
        """
        dispatch_url = os.environ.get('DISPATCH_CENTER_URL', 'http://localhost:5003')
        url = dispatch_url.rstrip('/') + '/api/dispatch-center/configs/alert_rules'
        resp = self._session.put(url, json=rules, timeout=(self.connect_timeout, self.read_timeout))
        resp.raise_for_status()
        data = resp.json()
        return data.get('data', {'updated': True}) if isinstance(data, dict) else data

    def get_alert_list(self, level: Optional[str] = None, alert_type: Optional[str] = None) -> List[Dict]:
        """[F22 行动项 3-硬迁移 2026-06-20] 告警 API 仅指向 5003 调度中心

        硬迁移策略（不兜底）：
        - 调用方必须保证 5003 服务可用
        - 5003 不可用时**直接抛异常**，不静默回退到 5002 mock 数据
        - 配置：环境变量 DISPATCH_CENTER_URL（默认 http://localhost:5003）

        旧端点：5002 /api/v4/alerts (PUT /dismiss) → 已删除
        新端点：5003 /api/dispatch-center/alerts (POST /dismiss)
        """
        dispatch_url = os.environ.get('DISPATCH_CENTER_URL', 'http://localhost:5003')
        url = dispatch_url.rstrip('/') + '/api/dispatch-center/alerts'
        query_params = {}
        if level:
            query_params['level'] = level
        if alert_type:
            query_params['alert_type'] = alert_type
        resp = self._session.get(url, params=query_params, timeout=(self.connect_timeout, self.read_timeout))
        resp.raise_for_status()
        data = resp.json()
        return data.get('data', {}).get('items', []) if isinstance(data, dict) else data

    def dismiss_alert(self, alert_id: str) -> bool:
        """[F22 行动项 3-硬迁移 2026-06-20] 告警关闭仅调用 5003 调度中心

        硬迁移策略（不兜底）：5003 不可用时**直接抛异常**，不静默回退。
        """
        dispatch_url = os.environ.get('DISPATCH_CENTER_URL', 'http://localhost:5003')
        url = dispatch_url.rstrip('/') + f'/api/dispatch-center/alerts/{alert_id}/dismiss'
        resp = self._session.post(url, timeout=(self.connect_timeout, self.read_timeout))
        resp.raise_for_status()
        data = resp.json()
        return data.get('data', {}).get('dismissed', False) if isinstance(data, dict) else data.get('dismissed', False)
