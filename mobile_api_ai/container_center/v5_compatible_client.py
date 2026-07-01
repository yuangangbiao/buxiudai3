# -*- coding: utf-8 -*-
"""
V5 ContainerCenter 兼容适配器

实现 v4 ContainerCenterClient HTTP SDK 的相同方法签名，
底层使用 V5 进程内存储，使现有代码可无感切换数据存储。
"""

import uuid
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

V5_FIELD_MAP = {
    'order_no': 'related_order',
    'process_name': 'related_process',
    'operator_id': 'target_operator',
    'data_type': 'data_type',
    'created_at': 'created_at',
    'updated_at': 'updated_at',
    'title': 'title',
    'status': 'status',
    'source': 'source',
    'priority': 'priority',
    'completed_qty': 'completed_qty',
    'quantity': 'completed_qty',
}

PROTECTED_FIELDS = ['order_no', 'process_name', 'order_no', 'completed_qty']


class V5CompatibleClient:
    """兼容 v4 ContainerCenterClient 接口的适配器

    实现 v4 HTTP SDK 的相同方法签名，但底层使用 V5 进程内存储，
    使 dispatch_center.py / wechat_server.py 可无感切换数据存储。

    对于 send_message / get_operators 等非文档操作方法，
    保留 v4 HTTP 回退（若提供 http_client）。
    """

    def __init__(self, container_center, http_client=None):
        self._cc = container_center
        self._http_client = http_client

    def _v5_package_id(self, data: Dict) -> str:
        return data.get('id') or str(uuid.uuid4())[:8]

    def _ensure_v5_fields(self, data: Dict, doc_type: str = '') -> Dict:
        """将 v4 风格数据转换为 V5 data_package 格式"""
        pkg = dict(data)
        if 'data_type' not in pkg and doc_type:
            pkg['data_type'] = doc_type
        if 'id' not in pkg:
            pkg['id'] = str(uuid.uuid4())[:8]
        if 'title' not in pkg:
            order = pkg.get('related_order', pkg.get('order_no', ''))
            process = pkg.get('related_process', pkg.get('process_name', ''))
            dtype = pkg.get('data_type', doc_type)
            pkg['title'] = f"{dtype}: {order} - {process}" if order or process else f"{dtype}: {pkg['id']}"
        if 'status' not in pkg:
            pkg['status'] = 'pending'
        if 'created_at' not in pkg:
            pkg['created_at'] = datetime.now().isoformat()
        if 'source' not in pkg:
            pkg['source'] = 'dispatch_center'
        if 'priority' not in pkg:
            pkg['priority'] = 'normal'
        if 'content' not in pkg:
            content = {k: v for k, v in pkg.items() if k not in V5_FIELD_MAP and k != 'id'}
            if content:
                pkg['content'] = content
            else:
                pkg['content'] = {}

        for field, v5_field in V5_FIELD_MAP.items():
            if field in pkg and v5_field not in pkg:
                pkg[v5_field] = pkg[field]

        for field in PROTECTED_FIELDS:
            if field in pkg:
                pkg['content'][field] = pkg[field]

        return pkg

    # ──────────────────────────────────────────────────
    # 文档 CRUD（映射到 V5 data_packages）
    # ──────────────────────────────────────────────────

    def query_documents(self, doc_type: str, page: int = 1, size: int = 50,
                        sort: str = '-updated_at', all: bool = False,
                        status: str = None, q: str = None) -> Dict:
        """查询文档列表 → V5 storage.get_packages()"""
        packages = []
        try:
            if self._cc is None:
                # 5003 启动时 cc 初始化失败(降级到空实例)—— RE-007 修复
                raise AttributeError('container_center instance is None (初始化失败,降级 HTTP 兜底)')
            limit = size if not all else 5000
            kwargs = {'limit': limit}
            if doc_type:  # None 或空串不传 data_type，返回所有类型
                kwargs['data_type'] = doc_type
            if status:
                kwargs['status'] = status
            packages = self._cc.storage.get_packages(**kwargs)
        except Exception as e:
            logger.error(f"V5 query_documents 失败: {e}")

        # 本地存储无数据时，回退到HTTP客户端查询
        # 注意: work_order 类型不通过 HTTP 回退，因为 /api/v4/work_order 会返回所有 data_packages 记录，
        # 不做 data_type 过滤，会错误地混入 report 等其他类型
        # RE-007 修复: cc=None 降级时, 解除 work_order 限制, 走 HTTP 兜底(数据可见优于类型隔离)
        work_order_fallback = (self._cc is None)
        if not packages and self._http_client and (doc_type != 'work_order' or work_order_fallback):
            try:
                if doc_type == 'work_order':
                    # 兼容两种客户端：一种支持 query_params，一种不支持
                    try:
                        result = self._http_client._request('GET', '/api/v4/work_order', 
                                                           query_params={'page': page, 'size': size})
                    except TypeError:
                        # container_center_client.py 的 _request 不支持 query_params
                        url = f'/api/v4/work_order?page={page}&size={size}'
                        result = self._http_client._request('GET', url)
                    packages = result.get('items', result.get('data', []))
                elif doc_type == 'operator':
                    # 兼容两种客户端：一种有 get_operators()，一种没有
                    try:
                        result = self._http_client.get_operators()
                        packages = result.get('operators', result.get('data', []))
                    except AttributeError:
                        # container_center_client.py 没有 get_operators()，直接调用API
                        result = self._http_client._request('GET', '/api/v4/operators')
                        packages = result.get('operators', result.get('data', []))
                elif doc_type is None:
                    # 获取全部 data_packages（调度中心 list_tasks/list_processes 依赖此路径）
                    try:
                        result = self._http_client._request('GET', f'/api/v4/work_order?page={page}&size={size}')
                    except TypeError:
                        result = self._http_client._request('GET', '/api/v4/work_order')
                    packages = result.get('items', result.get('data', []))
                logger.info(f"V5 query_documents 回退到HTTP成功，获取{len(packages)}条{doc_type}数据")
            except Exception as e:
                logger.warning(f"V5 query_documents HTTP回退失败: {e}")

        return {
            'items': packages,
            'data': packages,
            'total': len(packages),
            'page': page,
            'size': size,
        }

    def get_document(self, doc_type: str, doc_id: str) -> Optional[Dict]:
        """获取单个文档 → V5 storage.get_package()"""
        try:
            if doc_type == 'schedule':
                pkg = self._cc.storage.get_process_record(doc_id)
                if pkg:
                    return pkg
            pkg = self._cc.storage.get_package(doc_id)
            return pkg
        except Exception as e:
            logger.warning(f"V5 get_document({doc_type}, {doc_id}) 失败: {e}")
            return None

    def create_document(self, doc_type: str, data: Dict) -> Dict:
        """创建文档 → V5 storage.save_package()"""
        pkg = self._ensure_v5_fields(data, doc_type)
        try:
            self._cc.storage.save_package(pkg)
            return pkg
        except Exception as e:
            logger.error(f"V5 create_document 失败: {e}")
            return {'error': str(e), 'id': pkg.get('id')}

    def update_document(self, doc_type: str, doc_id: str, fields: Dict) -> Dict:
        """更新文档字段 → V5 storage.update_package()"""
        try:
            self._cc.storage.update_package(doc_id, fields)
            return {'id': doc_id, **fields}
        except Exception as e:
            logger.error(f"V5 update_document 失败: {e}")
            return {'error': str(e)}

    def update_document_status(self, doc_type: str, doc_id: str, status: str) -> Dict:
        """更新文档状态 → V5 storage.update_package_status()"""
        try:
            completed_at = datetime.now() if status in ('completed', 'cancelled') else None
            self._cc.storage.update_package_status(doc_id, status, completed_at)
            return {'id': doc_id, 'status': status}
        except Exception as e:
            logger.error(f"V5 update_document_status 失败: {e}")
            return {'error': str(e)}

    def delete_document(self, doc_type: str, doc_id: str) -> bool:
        """删除文档 → V5 storage.delete_package()"""
        try:
            return self._cc.storage.delete_package(doc_id)
        except Exception as e:
            logger.error(f"V5 delete_document 失败: {e}")
            return False

    # ──────────────────────────────────────────────────
    # 分发操作（映射到 V5 DataDistributor）
    # ──────────────────────────────────────────────────

    def distribute(self, task_id: str, operator_id: str) -> Dict:
        """分发任务 → V5 distributor.distribute()"""
        try:
            result = self._cc.distributor.distribute(task_id, operator_id)
            return {'distributed': bool(result)}
        except Exception as e:
            logger.error(f"V5 distribute 失败: {e}")
            return {'distributed': False}

    def assign_task_operator(self, doc_type: str, doc_id: str, operator_id: str) -> str:
        """分配任务操作员 → V5 storage.update_package()"""
        try:
            self._cc.storage.update_package(doc_id, {'target_operator': operator_id})
            return f'操作员已更新: {operator_id}'
        except Exception as e:
            logger.error(f"V5 assign_task_operator 失败: {e}")
            return f'分配失败: {e}'

    # ──────────────────────────────────────────────────
    # 便捷方法（来自 v4 get_packages / get_package / save_package）
    # ──────────────────────────────────────────────────

    def get_packages(self, doc_type: str = 'work_order', status: str = None,
                     limit: int = 100) -> List[Dict]:
        """获取包列表 → V5 storage.get_packages()"""
        try:
            return self._cc.storage.get_packages(
                data_type=doc_type if doc_type != 'work_order' else None,
                status=status,
                limit=limit,
            )
        except Exception as e:
            logger.error(f"V5 get_packages 失败: {e}")
            return []

    def get_package(self, pkg_id: str, doc_type: str = 'work_order') -> Optional[Dict]:
        """获取单个包 → V5 storage.get_package()"""
        return self.get_document(doc_type, pkg_id)

    def save_package(self, data: Dict, doc_type: str = 'work_order') -> Dict:
        """保存包 → V5 storage.save_package()"""
        if data.get('id'):
            fields = {k: v for k, v in data.get('data', data).items() if k != 'id'}
            return self.update_document(doc_type, data['id'], fields)
        pkg_data = data.get('data', data)
        return self.create_document(doc_type, pkg_data)

    # ──────────────────────────────────────────────────
    # 消息/操作员/告警（回退到 v4 HTTP，或返回空）
    # ──────────────────────────────────────────────────

    def send_message(self, content: str, to: str, msg_type: str = 'markdown',
                     channel: str = 'all') -> Dict:
        if self._http_client:
            try:
                return self._http_client.send_message(content, to, msg_type, channel)
            except Exception as e:
                logger.warning(f"v4 HTTP send_message 回退失败: {e}")
        raise RuntimeError("send_message 不可用：未提供 v4 HTTP 客户端")

    def get_operators(self, department: str = None) -> List[Dict]:
        if self._http_client:
            try:
                return self._http_client.get_operators(department)
            except Exception as e:
                logger.warning(f"v4 HTTP get_operators 回退失败: {e}")
        return []

    # ──────────────────────────────────────────────────
    # 流程记录（映射到 V5 process_records 表）
    # ──────────────────────────────────────────────────

    def get_process_records(self, status: str = None, process_type: str = None,
                            search: str = None, limit: int = 100) -> List[Dict]:
        """获取流程记录列表 → V5 storage.get_process_records()"""
        try:
            return self._cc.storage.get_process_records(
                status=status, process_type=process_type,
                search=search, limit=limit
            )
        except Exception as e:
            logger.error(f"V5 get_process_records 失败: {e}")
            return []

    def get_all_process_records(self) -> List[Dict]:
        """获取所有流程记录 → V5 storage.get_all_process_records()"""
        try:
            return self._cc.storage.get_all_process_records()
        except Exception as e:
            logger.error(f"V5 get_all_process_records 失败: {e}")
            return []

    def get_alert_rules(self) -> Dict:
        if self._http_client:
            try:
                return self._http_client.get_alert_rules()
            except Exception as e:
                logger.warning(f"v4 HTTP get_alert_rules 回退失败: {e}")
        return {}

    def update_alert_rules(self, rules: Dict) -> Dict:
        if self._http_client:
            try:
                return self._http_client.update_alert_rules(rules)
            except Exception as e:
                logger.warning(f"v4 HTTP update_alert_rules 回退失败: {e}")
        return {}

    def get_alert_list(self, level: str = None, alert_type: str = None) -> List[Dict]:
        if self._http_client:
            try:
                return self._http_client.get_alert_list(level, alert_type)
            except Exception as e:
                logger.warning(f"v4 HTTP get_alert_list 回退失败: {e}")
        return []

    def dismiss_alert(self, alert_id: str) -> bool:
        if self._http_client:
            try:
                return self._http_client.dismiss_alert(alert_id)
            except Exception as e:
                logger.warning(f"v4 HTTP dismiss_alert 回退失败: {e}")
        return False
