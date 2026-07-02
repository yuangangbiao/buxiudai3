#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""增强版审计日志系统 - 含IP记录、请求追踪、数据快照、不可篡改链"""

import os
import json
import time
import uuid
import random
import hashlib
import logging
from datetime import datetime
from elasticsearch import Elasticsearch
from threading import Lock
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class EnhancedAuditLogger:
    """增强版审计日志系统（强制记录+不可篡改+全链路追踪）"""

    def __init__(self, es_hosts=None, redis_client=None):
        """
        初始化增强版审计日志

        Args:
            es_hosts: Elasticsearch主机列表
            redis_client: Redis客户端（用于缓存）
        """
        if es_hosts is None:
            es_hosts = ['localhost:9200']
        self.es = Elasticsearch(es_hosts)
        self.redis_client = redis_client
        self.fallback_path = os.environ.get('AUDIT_LOG_FALLBACK_PATH',
            os.path.join(os.environ.get('BASE_DIR', os.path.dirname(os.path.abspath(__file__))), 'DAT', 'audit_log'))
        self.chain = []
        self.chain_lock = Lock()
        self.request_context = {}
        os.makedirs(self.fallback_path, exist_ok=True)

        self._ensure_index()
        self._load_chain()

    def _ensure_index(self):
        """确保索引存在（含完整mapping）"""
        index_name = f"audit-logs-{datetime.now().strftime('%Y.%m')}"
        if not self.es.indices.exists(index=index_name):
            mapping = {
                "mappings": {
                    "properties": {
                        "timestamp": {"type": "date"},
                        "operation_type": {"type": "keyword"},
                        "user_id": {"type": "keyword"},
                        "user_name": {"type": "keyword"},
                        "action": {"type": "keyword"},
                        "result": {"type": "keyword"},
                        "details": {"type": "object"},
                        "client_ip": {"type": "ip"},
                        "request_id": {"type": "keyword"},
                        "trace_id": {"type": "keyword"},
                        "user_agent": {"type": "text"},
                        "data_before": {"type": "object", "enabled": True},
                        "data_after": {"type": "object", "enabled": True},
                        "audit_id": {"type": "keyword"},
                        "block_hash": {"type": "keyword"},
                        "previous_hash": {"type": "keyword"},
                        "chain_index": {"type": "long"},
                        "signature": {"type": "keyword"}
                    }
                },
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 1
                }
            }
            self.es.indices.create(index=index_name, body=mapping)
            logger.info(f"创建审计索引: {index_name}")

    def _load_chain(self):
        """加载审计链"""
        try:
            result = self.es.search(
                index="audit-logs-*",
                query={"match_all": {}},
                sort=[{"chain_index": {"order": "desc"}}],
                size=1000
            )

            if result['hits']['hits']:
                self.chain = [hit['_source'] for hit in result['hits']['hits']]
                logger.info(f"加载审计链，当前长度: {len(self.chain)}")
        except Exception as e:
            logger.warning(f"加载审计链失败: {e}")
            self.chain = []

    def _generate_audit_id(self):
        """生成唯一审计ID"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        random_suffix = random.randint(100000, 999999)
        return f"AUD{timestamp}{random_suffix}"

    def _generate_request_id(self):
        """生成请求追踪ID"""
        return f"REQ{uuid.uuid4().hex[:16].upper()}"

    def _calculate_block_hash(self, block):
        """计算区块哈希（包含签名）"""
        data = {
            'timestamp': block.get('timestamp', ''),
            'audit_id': block.get('audit_id', ''),
            'operation_type': block.get('operation_type', ''),
            'user_id': block.get('user_id', ''),
            'action': block.get('action', ''),
            'result': block.get('result', ''),
            'client_ip': block.get('client_ip', ''),
            'request_id': block.get('request_id', ''),
            'previous_hash': block.get('previous_hash', '')
        }
        raw = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode()).hexdigest()

    def _calculate_block_signature(self, block):
        """计算区块签名（用于二次验证）"""
        raw = json.dumps({
            'audit_id': block.get('audit_id', ''),
            'block_hash': block.get('block_hash', ''),
            'timestamp': block.get('timestamp', '')
        }, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode()).hexdigest()

    def set_request_context(self, request_id, context):
        """
        设置请求上下文（在请求开始时调用）

        Args:
            request_id: 请求追踪ID
            context: 上下文字典（包含client_ip, user_agent等）
        """
        self.request_context[request_id] = context

    def clear_request_context(self, request_id):
        """清除请求上下文"""
        self.request_context.pop(request_id, None)

    @contextmanager
    def track_operation(self, operation_type, user_id, user_name, action):
        """
        操作追踪上下文管理器（自动记录操作前后快照）

        Usage:
            with audit_logger.track_operation('report', 'user1', '张三', 'report.submit') as tracker:
                # 执行操作前的数据
                tracker.set_before_snapshot({'qty': 100})
                #执行业务操作
                update_quantity(50)
                # 执行操作后的数据
                tracker.set_after_snapshot({'qty': 50})
        """
        tracker = OperationTracker(self, operation_type, user_id, user_name, action)
        try:
            yield tracker
        except Exception as e:
            tracker.set_error(str(e))
            raise

    def log(self, operation_type, user_id, user_name, action, result,
            details=None, client_ip=None, request_id=None, trace_id=None,
            user_agent=None, data_before=None, data_after=None):
        """
        记录审计日志（强制写入）

        Args:
            operation_type: 操作类型（report, query, admin等）
            user_id: 用户ID
            user_name: 用户名称
            action: 操作动作（report.submit, report.confirm等）
            result: 操作结果（success, failure, pending）
            details: 详细信息字典
            client_ip: 客户端IP地址
            request_id: 请求追踪ID
            trace_id: 链路追踪ID
            user_agent: 用户代理字符串
            data_before: 操作前数据快照
            data_after: 操作后数据快照
        """
        if request_id and request_id in self.request_context:
            ctx = self.request_context[request_id]
            client_ip = client_ip or ctx.get('client_ip')
            user_agent = user_agent or ctx.get('user_agent')
            trace_id = trace_id or ctx.get('trace_id')

        with self.chain_lock:
            block = {
                'timestamp': datetime.now().isoformat(),
                'operation_type': operation_type,
                'user_id': user_id,
                'user_name': user_name,
                'action': action,
                'result': result,
                'details': details or {},
                'client_ip': client_ip or '0.0.0.0',
                'request_id': request_id or self._generate_request_id(),
                'trace_id': trace_id or '',
                'user_agent': user_agent or '',
                'data_before': data_before,
                'data_after': data_after,
                'audit_id': self._generate_audit_id(),
                'previous_hash': self.chain[0]['block_hash'] if self.chain else '0' * 64,
                'chain_index': len(self.chain)
            }

            block['block_hash'] = self._calculate_block_hash(block)
            block['signature'] = self._calculate_block_signature(block)

            try:
                self._write_to_es(block)
                self.chain.insert(0, block)

                if self.redis_client:
                    self._cache_recent_audit(block)

                logger.info(f"审计记录写入成功: {block['audit_id']}")
            except Exception as e:
                logger.error(f"ES写入失败，降级到本地文件: {e}")
                self._write_to_file(block)

    def _write_to_es(self, block):
        """写入Elasticsearch"""
        index_name = f"audit-logs-{datetime.now().strftime('%Y.%m')}"
        self.es.index(index=index_name, document=block)

    def _write_to_file(self, block):
        """降级写入本地文件"""
        file_path = f"{self.fallback_path}/audit_{datetime.now().strftime('%Y%m%d')}.log"
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(block, ensure_ascii=False) + '\n')

    def _cache_recent_audit(self, block):
        """缓存最近审计记录到Redis"""
        try:
            cache_key = f"audit:recent:{block['request_id']}"
            self.redis_client.setex(
                cache_key,
                86400,
                json.dumps(block, ensure_ascii=False)
            )
        except Exception as e:
            logger.warning(f"审计缓存失败: {e}")

    def verify_chain(self):
        """验证链完整性"""
        with self.chain_lock:
            for i in range(1, len(self.chain)):
                current = self.chain[i]
                previous = self.chain[i - 1]

                if current['previous_hash'] != previous['block_hash']:
                    logger.error(f"审计链断裂 at index {i}")
                    return False, {'type': 'chain_break', 'index': i}

                expected_hash = self._calculate_block_hash(current)
                if current['block_hash'] != expected_hash:
                    logger.error(f"审计记录篡改 at index {i}")
                    return False, {'type': 'tamper_detected', 'index': i}

                expected_sig = self._calculate_block_signature(current)
                if current['signature'] != expected_sig:
                    logger.error(f"审计签名验证失败 at index {i}")
                    return False, {'type': 'signature_invalid', 'index': i}

            logger.info("审计链完整性验证通过")
            return True, None

    def verify_single_record(self, audit_id):
        """
        验证单条审计记录完整性

        Args:
            audit_id: 审计记录ID

        Returns:
            tuple: (是否有效, 详情)
        """
        try:
            result = self.es.search(
                index="audit-logs-*",
                query={"term": {"audit_id": audit_id}},
                size=1
            )

            if not result['hits']['hits']:
                return False, {'error': '记录不存在'}

            block = result['hits']['hits'][0]['_source']

            expected_hash = self._calculate_block_hash(block)
            if block['block_hash'] != expected_hash:
                return False, {'error': '哈希校验失败', 'expected': expected_hash}

            return True, block

        except Exception as e:
            logger.error(f"验证审计记录失败: {e}")
            return False, {'error': str(e)}

    def query_logs(self, user_id=None, operation_type=None, action=None,
                   result=None, start_time=None, end_time=None,
                   client_ip=None, request_id=None, trace_id=None,
                   size=100):
        """
        查询审计日志（增强版）

        Args:
            user_id: 用户ID
            operation_type: 操作类型
            action: 操作动作
            result: 操作结果
            start_time: 开始时间
            end_time: 结束时间
            client_ip: 客户端IP
            request_id: 请求追踪ID
            trace_id: 链路追踪ID
            size: 返回数量

        Returns:
            list: 审计记录列表
        """
        must_clauses = []

        if user_id:
            must_clauses.append({"term": {"user_id": user_id}})
        if operation_type:
            must_clauses.append({"term": {"operation_type": operation_type}})
        if action:
            must_clauses.append({"term": {"action": action}})
        if result:
            must_clauses.append({"term": {"result": result}})
        if client_ip:
            must_clauses.append({"term": {"client_ip": client_ip}})
        if request_id:
            must_clauses.append({"term": {"request_id": request_id}})
        if trace_id:
            must_clauses.append({"term": {"trace_id": trace_id}})

        if start_time or end_time:
            range_query = {}
            if start_time:
                range_query["gte"] = start_time
            if end_time:
                range_query["lte"] = end_time
            must_clauses.append({"range": {"timestamp": range_query}})

        query = {"bool": {"must": must_clauses}} if must_clauses else {"match_all": {}}

        try:
            result = self.es.search(
                index="audit-logs-*",
                query=query,
                sort=[{"timestamp": {"order": "desc"}}],
                size=size
            )
            return [hit['_source'] for hit in result['hits']['hits']]
        except Exception as e:
            logger.error(f"查询审计日志失败: {e}")
            return []

    def get_operation_timeline(self, request_id):
        """
        获取单个请求的操作时间线

        Args:
            request_id: 请求追踪ID

        Returns:
            list: 按时间排序的操作列表
        """
        records = self.query_logs(request_id=request_id, size=100)
        return sorted(records, key=lambda x: x['timestamp'])

    def get_user_operations(self, user_id, days=7):
        """
        获取用户最近操作统计

        Args:
            user_id: 用户ID
            days: 查询天数

        Returns:
            dict: 操作统计
        """
        from datetime import timedelta
        start_time = (datetime.now() - timedelta(days=days)).isoformat()

        records = self.query_logs(user_id=user_id, start_time=start_time, size=1000)

        stats = {
            'total': len(records),
            'success': len([r for r in records if r['result'] == 'success']),
            'failure': len([r for r in records if r['result'] == 'failure']),
            'pending': len([r for r in records if r['result'] == 'pending']),
            'by_action': {},
            'by_ip': {}
        }

        for record in records:
            action = record['action']
            stats['by_action'][action] = stats['by_action'].get(action, 0) + 1

            ip = record['client_ip']
            stats['by_ip'][ip] = stats['by_ip'].get(ip, 0) + 1

        return stats


class OperationTracker:
    """操作追踪器（用于track_operation上下文管理器）"""

    def __init__(self, audit_logger, operation_type, user_id, user_name, action):
        self.audit_logger = audit_logger
        self.operation_type = operation_type
        self.user_id = user_id
        self.user_name = user_name
        self.action = action
        self.before_snapshot = None
        self.after_snapshot = None
        self.error = None
        self.request_id = audit_logger._generate_request_id()

    def set_before_snapshot(self, data):
        """设置操作前数据快照"""
        self.before_snapshot = data

    def set_after_snapshot(self, data):
        """设置操作后数据快照"""
        self.after_snapshot = data

    def set_error(self, error_msg):
        """设置错误信息"""
        self.error = error_msg

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            result = 'failure'
            details = {'error': str(self.error) if self.error else str(exc_val)}
        elif self.error:
            result = 'failure'
            details = {'error': self.error}
        else:
            result = 'success'
            details = {}

        self.audit_logger.log(
            operation_type=self.operation_type,
            user_id=self.user_id,
            user_name=self.user_name,
            action=self.action,
            result=result,
            details=details,
            request_id=self.request_id,
            data_before=self.before_snapshot,
            data_after=self.after_snapshot
        )


_global_audit_logger = None


def init_audit_logger(es_hosts=None, redis_client=None):
    """初始化全局审计日志器"""
    global _global_audit_logger
    _global_audit_logger = EnhancedAuditLogger(es_hosts=es_hosts, redis_client=redis_client)
    return _global_audit_logger


def get_audit_logger():
    """获取全局审计日志器"""
    return _global_audit_logger


def log_operation(operation_type, user_id, user_name, action, result,
                 details=None, **kwargs):
    """
    快捷记录函数

    Usage:
        log_operation('report', 'user1', '张三', 'report.submit', 'success',
                     details={'order_no': 'WO123'}, client_ip='192.168.1.1')
    """
    if _global_audit_logger is None:
        logger.warning("审计日志器未初始化，跳过记录")
        return

    _global_audit_logger.log(
        operation_type=operation_type,
        user_id=user_id,
        user_name=user_name,
        action=action,
        result=result,
        details=details,
        **kwargs
    )
