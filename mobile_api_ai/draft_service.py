# -*- coding: utf-8 -*-
"""
草稿/离线队列服务 — 不锈钢网带跟单 3.0

解决问题:
- MES 车间网络不稳，员工填到一半断网/误关，数据丢失
- 报工提交失败时需要本地暂存，重连后自动重试

设计:
- Redis 热存（TTL 7 天）+ MySQL 冷备（report_drafts 表）
- 草稿 ID 格式: draft:{operator_id}:{uuid}
- 状态机: pending → syncing → synced / failed
- 同步策略: 网络恢复时自动批量重试 + 手动触发

集成方式:
    from draft_service import DraftService, register_draft_routes

    # 方式一: 注册路由到现有 app
    app = Flask(__name__)
    register_draft_routes(app, storage_factory=_get_storage)

    # 方式二: 直接调用服务
    svc = DraftService(storage, cache)
    draft_id = svc.save(operator='张三', payload={...})
    ok = svc.submit(draft_id=draft_id, submitter=lambda d: ...)
"""
import os
import json
import time
import uuid
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional, Callable, Dict, Any, List
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DRAFT_KEY_PREFIX = 'draft:'
DRAFT_INDEX_PREFIX = 'draft_index:'
DRAFT_TTL_SECONDS = 7 * 24 * 3600
MAX_DRAFT_PER_OPERATOR = 100
DRAFT_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS `report_drafts` (
    `id` VARCHAR(64) PRIMARY KEY,
    `operator` VARCHAR(64) NOT NULL,
    `endpoint` VARCHAR(128) NOT NULL,
    `payload_json` LONGTEXT NOT NULL,
    `status` VARCHAR(16) NOT NULL DEFAULT 'pending',
    `retry_count` INT NOT NULL DEFAULT 0,
    `last_error` TEXT,
    `client_info` VARCHAR(255),
    `created_at` DATETIME NOT NULL,
    `updated_at` DATETIME NOT NULL,
    `synced_at` DATETIME,
    INDEX `idx_operator_status` (`operator`, `status`),
    INDEX `idx_status_updated` (`status`, `updated_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='离线草稿与失败重试';
"""


class DraftError(Exception):
    pass


class DraftNotFound(DraftError):
    pass


class DraftService:
    """草稿与离线队列服务"""

    def __init__(self, storage_getter: Callable, cache=None, max_per_operator: int = MAX_DRAFT_PER_OPERATOR):
        self._storage_getter = storage_getter
        self._cache = cache
        self._max_per_operator = max_per_operator
        self._lock = threading.RLock()
        self._initialized = False
        self._stats = {'saved': 0, 'submitted': 0, 'synced': 0, 'failed': 0, 'deleted': 0}

    def _ensure_table(self):
        if self._initialized:
            return
        try:
            storage = self._storage_getter()
            with storage._pool.connection() as conn:
                cur = conn.cursor()
                for stmt in DRAFT_TABLE_DDL.strip().split(';'):
                    stmt = stmt.strip()
                    if stmt:
                        cur.execute(stmt)
                conn.commit()
            self._initialized = True
            logger.info('[DraftService] report_drafts 表就绪')
        except Exception as e:
            logger.warning(f'[DraftService] 初始化表失败（继续运行）: {e}')

    def save(self, operator: str, endpoint: str, payload: Dict[str, Any],
             draft_id: Optional[str] = None, client_info: Optional[str] = None) -> str:
        """保存草稿，返回 draft_id"""
        if not operator:
            raise DraftError('operator 不能为空')
        if not endpoint:
            raise DraftError('endpoint 不能为空')
        if not isinstance(payload, dict):
            raise DraftError('payload 必须是 dict')

        self._ensure_table()
        if draft_id is None:
            draft_id = f'{operator}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}'
        now = datetime.now()
        payload_json = json.dumps(payload, ensure_ascii=False)

        storage = self._storage_getter()
        with storage._pool.connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO report_drafts
                   (id, operator, endpoint, payload_json, status, retry_count, client_info, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, 'pending', 0, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE
                   payload_json=VALUES(payload_json),
                   updated_at=VALUES(updated_at),
                   client_info=VALUES(client_info)""",
                (draft_id, operator, endpoint, payload_json, client_info or '', now, now)
            )
            conn.commit()

        self._cache_set(draft_id, {
            'id': draft_id, 'operator': operator, 'endpoint': endpoint,
            'payload': payload, 'status': 'pending', 'created_at': now.isoformat()
        })
        self._add_to_index(operator, draft_id)

        with self._lock:
            self._stats['saved'] += 1
        logger.info(f'[DraftService] 保存草稿: id={draft_id} operator={operator} endpoint={endpoint}')
        return draft_id

    def get(self, draft_id: str) -> Optional[Dict[str, Any]]:
        cached = self._cache_get(draft_id)
        if cached:
            return cached
        storage = self._storage_getter()
        with storage._pool.connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM report_drafts WHERE id=%s", (draft_id,))
            row = cur.fetchone()
        if not row:
            return None
        col = [d[0] for d in cur.description]
        item = dict(zip(col, row))
        item['payload'] = json.loads(item.pop('payload_json'))
        for k in ('created_at', 'updated_at', 'synced_at'):
            if item.get(k) and hasattr(item[k], 'isoformat'):
                item[k] = item[k].isoformat()
        self._cache_set(draft_id, item)
        return item

    def list_by_operator(self, operator: str, status: Optional[str] = None,
                         limit: int = 50) -> List[Dict[str, Any]]:
        """列出某操作员的草稿"""
        storage = self._storage_getter()
        with storage._pool.connection() as conn:
            cur = conn.cursor()
            if status:
                cur.execute(
                    """SELECT id, operator, endpoint, status, retry_count, last_error,
                              client_info, created_at, updated_at, synced_at
                       FROM report_drafts
                       WHERE operator=%s AND status=%s
                       ORDER BY updated_at DESC LIMIT %s""",
                    (operator, status, limit)
                )
            else:
                cur.execute(
                    """SELECT id, operator, endpoint, status, retry_count, last_error,
                              client_info, created_at, updated_at, synced_at
                       FROM report_drafts
                       WHERE operator=%s
                       ORDER BY updated_at DESC LIMIT %s""",
                    (operator, limit)
                )
            rows = cur.fetchall()
        if not rows:
            return []
        col = [d[0] for d in cur.description]
        items = []
        for row in rows:
            item = dict(zip(col, row))
            for k in ('created_at', 'updated_at', 'synced_at'):
                if item.get(k) and hasattr(item[k], 'isoformat'):
                    item[k] = item[k].isoformat()
            items.append(item)
        return items

    def submit(self, draft_id: str, submitter: Callable[[Dict[str, Any]], bool],
               max_retries: int = 3) -> Dict[str, Any]:
        """提交草稿到真实业务端点，失败时记录并保留草稿"""
        draft = self.get(draft_id)
        if not draft:
            raise DraftNotFound(f'草稿不存在: {draft_id}')

        if draft['status'] == 'synced':
            return {'ok': True, 'draft_id': draft_id, 'status': 'synced', 'message': '已同步'}

        storage = self._storage_getter()
        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                self._update_status(draft_id, 'syncing')
                ok = submitter(draft)
                if ok:
                    self._update_status(draft_id, 'synced', synced_at=datetime.now())
                    self._cache_delete(draft_id)
                    with self._lock:
                        self._stats['submitted'] += 1
                        self._stats['synced'] += 1
                    logger.info(f'[DraftService] 同步成功: id={draft_id} attempt={attempt}')
                    return {'ok': True, 'draft_id': draft_id, 'status': 'synced', 'attempt': attempt}
                last_error = 'submitter returned False'
            except Exception as e:
                last_error = str(e)
                logger.warning(f'[DraftService] 同步失败: id={draft_id} attempt={attempt} err={e}')

            self._update_status(draft_id, 'pending', last_error=last_error, incr_retry=True)

        with self._lock:
            self._stats['failed'] += 1
        return {'ok': False, 'draft_id': draft_id, 'status': 'pending',
                'message': f'同步失败（已重试 {max_retries} 次）: {last_error}',
                'retry_count': draft.get('retry_count', 0) + max_retries}

    def submit_all(self, operator: str, submitter: Callable[[Dict[str, Any]], bool],
                   status: str = 'pending', max_retries: int = 3) -> Dict[str, Any]:
        """批量提交某操作员的所有草稿"""
        drafts = self.list_by_operator(operator, status=status)
        results = {'total': len(drafts), 'synced': 0, 'failed': 0, 'errors': []}
        for d in drafts:
            r = self.submit(d['id'], submitter, max_retries=max_retries)
            if r['ok']:
                results['synced'] += 1
            else:
                results['failed'] += 1
                results['errors'].append({'id': d['id'], 'error': r.get('message')})
        return results

    def delete(self, draft_id: str) -> bool:
        storage = self._storage_getter()
        with storage._pool.connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM report_drafts WHERE id=%s", (draft_id,))
            affected = cur.rowcount
            conn.commit()
        self._cache_delete(draft_id)
        with self._lock:
            self._stats['deleted'] += 1
        return affected > 0

    def cleanup_synced(self, older_than_days: int = 7) -> int:
        """清理已同步超过 N 天的草稿"""
        storage = self._storage_getter()
        cutoff = datetime.now() - timedelta(days=older_than_days)
        with storage._pool.connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM report_drafts WHERE status='synced' AND synced_at < %s",
                (cutoff,)
            )
            deleted = cur.rowcount
            conn.commit()
        logger.info(f'[DraftService] 清理 {deleted} 条已同步草稿（{older_than_days} 天前）')
        return deleted

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            base = dict(self._stats)
        try:
            storage = self._storage_getter()
            with storage._pool.connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT status, COUNT(*) FROM report_drafts GROUP BY status")
                status_counts = {row[0]: row[1] for row in cur.fetchall()}
        except Exception as e:
            status_counts = {'_error': str(e)}
        base['by_status'] = status_counts
        return base

    def _update_status(self, draft_id: str, status: str, last_error: Optional[str] = None,
                       incr_retry: bool = False, synced_at: Optional[datetime] = None):
        storage = self._storage_getter()
        with storage._pool.connection() as conn:
            cur = conn.cursor()
            if incr_retry and synced_at is None:
                cur.execute(
                    """UPDATE report_drafts
                       SET status=%s, last_error=%s, retry_count=retry_count+1, updated_at=%s
                       WHERE id=%s""",
                    (status, last_error or '', datetime.now(), draft_id)
                )
            elif synced_at is not None:
                cur.execute(
                    """UPDATE report_drafts
                       SET status=%s, synced_at=%s, updated_at=%s
                       WHERE id=%s""",
                    (status, synced_at, datetime.now(), draft_id)
                )
            else:
                cur.execute(
                    "UPDATE report_drafts SET status=%s, last_error=%s, updated_at=%s WHERE id=%s",
                    (status, last_error or '', datetime.now(), draft_id)
                )
            conn.commit()

    def _add_to_index(self, operator: str, draft_id: str):
        if not self._cache:
            return
        try:
            key = f'{DRAFT_INDEX_PREFIX}{operator}'
            current = self._cache.get(key) or []
            if draft_id not in current:
                current.append(draft_id)
                if len(current) > self._max_per_operator:
                    current = current[-self._max_per_operator:]
                self._cache.set(key, current, ttl=DRAFT_TTL_SECONDS)
        except Exception as e:
            logger.debug(f'[DraftService] 索引更新失败: {e}')

    def _cache_set(self, key: str, value: Dict[str, Any]):
        if not self._cache:
            return
        try:
            self._cache.set(f'{DRAFT_KEY_PREFIX}{key}', value, ttl=DRAFT_TTL_SECONDS)
        except Exception:
            pass

    def _cache_get(self, key: str) -> Optional[Dict[str, Any]]:
        if not self._cache:
            return None
        try:
            return self._cache.get(f'{DRAFT_KEY_PREFIX}{key}')
        except Exception:
            return None

    def _cache_delete(self, key: str):
        if not self._cache:
            return
        try:
            self._cache.delete(f'{DRAFT_KEY_PREFIX}{key}')
        except Exception:
            pass


def _make_submitter(endpoint: str):
    """把 endpoint 字符串映射到真实 submitter 函数（解耦）"""
    raise NotImplementedError(
        '请在 register_draft_routes 中通过 submitter_map 参数提供 submitter 映射'
    )


def register_draft_routes(app, storage_getter, submitter_map: Optional[Dict[str, Callable]] = None,
                          cache=None, default_endpoint: str = '/api/process_sub_step'):
    """注册草稿/离线队列路由到 Flask app

    参数:
        app: Flask 实例
        storage_getter: 返回 storage 对象的函数
        submitter_map: {endpoint: callable(payload)->bool}，可选
        cache: cache 实例（用于热存）
        default_endpoint: 默认提交端点
    """
    from flask import request, jsonify
    svc = DraftService(storage_getter, cache=cache)

    @app.route('/api/draft/save', methods=['POST'])
    def draft_save():
        body = request.get_json(silent=True) or {}
        operator = (body.get('operator') or '').strip()
        endpoint = (body.get('endpoint') or default_endpoint).strip()
        payload = body.get('payload') or {}
        client_info = request.headers.get('User-Agent', '')[:200]
        if not operator:
            return jsonify({'code': 400, 'message': 'operator 必填'}), 400
        if not isinstance(payload, dict):
            return jsonify({'code': 400, 'message': 'payload 必须是对象'}), 400
        try:
            draft_id = svc.save(operator, endpoint, payload, client_info=client_info)
            return jsonify({'code': 0, 'message': 'ok', 'data': {'draft_id': draft_id}})
        except DraftError as e:
            return jsonify({'code': 400, 'message': '操作失败，请稍后重试'}), 400
        except Exception as e:
            logger.exception('draft_save 异常')
            return jsonify({'code': 500, 'message': '操作失败，请稍后重试'}), 500

    @app.route('/api/draft/list', methods=['GET'])
    def draft_list():
        operator = request.args.get('operator', '').strip()
        status = request.args.get('status')
        if not operator:
            return jsonify({'code': 400, 'message': 'operator 必填'}), 400
        try:
            items = svc.list_by_operator(operator, status=status)
            return jsonify({'code': 0, 'data': {'list': items, 'count': len(items)}})
        except Exception as e:
            logger.exception('draft_list 异常')
            return jsonify({'code': 500, 'message': '操作失败，请稍后重试'}), 500

    @app.route('/api/draft/<draft_id>', methods=['GET'])
    def draft_get(draft_id):
        try:
            item = svc.get(draft_id)
            if not item:
                return jsonify({'code': 404, 'message': '草稿不存在'}), 404
            return jsonify({'code': 0, 'data': item})
        except Exception as e:
            logger.exception('draft_get 异常')
            return jsonify({'code': 500, 'message': '操作失败，请稍后重试'}), 500

    @app.route('/api/draft/<draft_id>', methods=['DELETE'])
    def draft_delete(draft_id):
        try:
            ok = svc.delete(draft_id)
            if not ok:
                return jsonify({'code': 404, 'message': '草稿不存在'}), 404
            return jsonify({'code': 0, 'message': 'ok'})
        except Exception as e:
            logger.exception('draft_delete 异常')
            return jsonify({'code': 500, 'message': '操作失败，请稍后重试'}), 500

    @app.route('/api/draft/submit/<draft_id>', methods=['POST'])
    def draft_submit(draft_id):
        if not submitter_map:
            return jsonify({'code': 503, 'message': 'submitter_map 未配置'}), 503
        try:
            draft = svc.get(draft_id)
            if not draft:
                return jsonify({'code': 404, 'message': '草稿不存在'}), 404
            endpoint = draft.get('endpoint', default_endpoint)
            submitter = submitter_map.get(endpoint)
            if not submitter:
                return jsonify({'code': 400, 'message': f'端点 {endpoint} 无 submitter'}), 400
            result = svc.submit(draft_id, submitter)
            status_code = 200 if result['ok'] else 502
            return jsonify({'code': 0 if result['ok'] else 502, 'data': result}), status_code
        except Exception as e:
            logger.exception('draft_submit 异常')
            return jsonify({'code': 500, 'message': '操作失败，请稍后重试'}), 500

    @app.route('/api/draft/sync_all', methods=['POST'])
    def draft_sync_all():
        if not submitter_map:
            return jsonify({'code': 503, 'message': 'submitter_map 未配置'}), 503
        body = request.get_json(silent=True) or {}
        operator = (body.get('operator') or '').strip()
        if not operator:
            return jsonify({'code': 400, 'message': 'operator 必填'}), 400
        try:
            drafts = svc.list_by_operator(operator, status='pending')
            results = {'total': len(drafts), 'synced': 0, 'failed': 0, 'errors': []}
            for d in drafts:
                endpoint = d.get('endpoint', default_endpoint)
                submitter = submitter_map.get(endpoint)
                if not submitter:
                    results['failed'] += 1
                    results['errors'].append({'id': d['id'], 'error': f'no submitter for {endpoint}'})
                    continue
                full_draft = svc.get(d['id'])
                r = svc.submit(d['id'], submitter)
                if r['ok']:
                    results['synced'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append({'id': d['id'], 'error': r.get('message')})
            return jsonify({'code': 0, 'data': results})
        except Exception as e:
            logger.exception('draft_sync_all 异常')
            return jsonify({'code': 500, 'message': '操作失败，请稍后重试'}), 500

    @app.route('/api/draft/stats', methods=['GET'])
    def draft_stats():
        return jsonify({'code': 0, 'data': svc.stats()})

    @app.route('/api/draft/cleanup', methods=['POST'])
    def draft_cleanup():
        body = request.get_json(silent=True) or {}
        days = int(body.get('older_than_days', 7))
        try:
            deleted = svc.cleanup_synced(older_than_days=days)
            return jsonify({'code': 0, 'data': {'deleted': deleted}})
        except Exception as e:
            logger.exception('draft_cleanup 异常')
            return jsonify({'code': 500, 'message': '操作失败，请稍后重试'}), 500

    return svc


if __name__ == '__main__':
    print("=== 草稿服务演示 ===")
    print("模块加载 OK,导出:", [n for n in dir() if not n.startswith('_')])
    print("DRAFT_TTL_SECONDS =", DRAFT_TTL_SECONDS)
    print("MAX_DRAFT_PER_OPERATOR =", MAX_DRAFT_PER_OPERATOR)
