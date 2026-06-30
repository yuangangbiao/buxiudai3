# -*- coding: utf-8 -*-
"""
draft_service.py 单元测试

覆盖场景:
1. save → get → 完整往返
2. 重复保存同 draft_id → upsert 语义
3. list_by_operator 状态过滤
4. submit 成功路径
5. submit 失败重试 3 次
6. submit_all 批量
7. delete
8. stats
9. cleanup_synced
10. 缓存 fallback (cache 不可用时仍可用)
11. 7 个 HTTP 端点
12. 并发安全
"""
import os
import sys
import json
import threading
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'mobile_api_ai'))


class FakeStorage:
    """简化版：直接接管 cursor() 返回的游标对象，绕过 SQL 解析"""

    def __init__(self):
        self._pool = MagicMock()
        self._cur = FakeCursor()
        self._cur.storage = self
        self._pool.connection.return_value = self
        self._pool.connection.side_effect = lambda: self

    def cursor(self):
        return self._cur

    def commit(self):
        pass

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeCursor:
    """直接拦截 execute，根据 SQL 类型做简单分支"""

    def __init__(self):
        self.description = None
        self.rowcount = 0
        self._buffer = []
        self._store = {}
        self._ddl_done = False
        self._last_fetchall = []
        self._last_fetchone = None
        self.executed = []

    def execute(self, sql, params=None):
        params = params or ()
        self.executed.append((sql.strip(), params))
        s_upper = sql.strip().upper()
        if 'CREATE TABLE' in s_upper and not self._ddl_done:
            self._ddl_done = True
            self.rowcount = 0
            return
        if s_upper.startswith('INSERT'):
            draft_id = params[0]
            self._store[draft_id] = {
                'id': draft_id,
                'operator': params[1],
                'endpoint': params[2],
                'payload_json': params[3],
                'status': 'pending',
                'retry_count': 0,
                'last_error': '',
                'client_info': params[4] if len(params) > 4 else '',
                'created_at': params[5] if len(params) > 5 else None,
                'updated_at': params[6] if len(params) > 6 else None,
                'synced_at': None,
            }
            self.rowcount = 1
        elif s_upper.startswith('UPDATE'):
            self._handle_update(sql, params)
        elif s_upper.startswith('DELETE'):
            self._handle_delete(sql, params)
        elif 'GROUP BY STATUS' in s_upper:
            self._handle_group_by_status()
        elif s_upper.startswith('SELECT * FROM'):
            self._handle_select_by_id(params)
        elif 'FROM REPORT_DRAFTS' in s_upper and 'OPERATOR=%S' in s_upper:
            self._handle_select_by_operator(sql, params)
        else:
            self._last_fetchall = []
            self._last_fetchone = None

    def _handle_update(self, sql, params):
        s = sql.strip()
        if 'synced_at=%s' in s:
            status, synced_at, _now, draft_id = params
            if draft_id in self._store:
                self._store[draft_id]['status'] = status
                self._store[draft_id]['synced_at'] = synced_at
                self._store[draft_id]['updated_at'] = _now
                self.rowcount = 1
        elif 'retry_count=retry_count+1' in s:
            status, last_error, _now, draft_id = params
            if draft_id in self._store:
                self._store[draft_id]['status'] = status
                self._store[draft_id]['last_error'] = last_error
                self._store[draft_id]['retry_count'] += 1
                self._store[draft_id]['updated_at'] = _now
                self.rowcount = 1
        elif 'status=%s' in s and 'last_error=%s' in s:
            status, last_error, _now, draft_id = params
            if draft_id in self._store:
                self._store[draft_id]['status'] = status
                self._store[draft_id]['last_error'] = last_error
                self._store[draft_id]['updated_at'] = _now
                self.rowcount = 1

    def _handle_delete(self, sql, params):
        s = sql.strip()
        if "WHERE STATUS='SYNCED'" in s.upper():
            cutoff = params[0]
            deleted = 0
            for k in list(self._store.keys()):
                r = self._store[k]
                if r['status'] == 'synced' and r['synced_at'] and r['synced_at'] < cutoff:
                    del self._store[k]
                    deleted += 1
            self.rowcount = deleted
        else:
            draft_id = params[0]
            if draft_id in self._store:
                del self._store[draft_id]
                self.rowcount = 1
            else:
                self.rowcount = 0

    def _handle_group_by_status(self):
        counts = {}
        for r in self._store.values():
            counts[r['status']] = counts.get(r['status'], 0) + 1
        self._last_fetchall = list(counts.items())
        self.description = [('status', None), ('cnt', None)]

    def _handle_select_by_id(self, params):
        draft_id = params[0]
        row = self._store.get(draft_id)
        if row:
            keys = list(row.keys())
            self._last_fetchone = tuple(row[k] for k in keys)
            self.description = [(k, None) for k in keys]
        else:
            self._last_fetchone = None
            self.description = None

    def _handle_select_by_operator(self, sql, params):
        s = sql.strip()
        operator = params[0]
        if 'AND STATUS=%S' in s.upper():
            status_filter = params[1]
            limit = params[2]
        else:
            status_filter = None
            limit = params[1]
        rows = [dict(r) for r in self._store.values()
                if r['operator'] == operator
                and (status_filter is None or r['status'] == status_filter)]
        rows.sort(key=lambda r: r['updated_at'] or datetime.min, reverse=True)
        rows = rows[:limit]
        result = []
        for r in rows:
            result.append((
                r['id'], r['operator'], r['endpoint'],
                r['status'], r['retry_count'], r['last_error'],
                r['client_info'], r['created_at'],
                r['updated_at'], r['synced_at'],
            ))
        self._last_fetchall = result
        self.description = [
            ('id', None), ('operator', None), ('endpoint', None),
            ('status', None), ('retry_count', None), ('last_error', None),
            ('client_info', None), ('created_at', None),
            ('updated_at', None), ('synced_at', None),
        ]

    def fetchall(self):
        return list(self._last_fetchall)

    def fetchone(self):
        return self._last_fetchone

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def make_storage():
    return FakeStorage(), None


class FakeCache:
    def __init__(self):
        self.store = {}
        self.get_count = 0
        self.set_count = 0

    def get(self, key, default=None):
        self.get_count += 1
        return self.store.get(key, default)

    def set(self, key, value, ttl=None):
        self.set_count += 1
        self.store[key] = value
        return True

    def delete(self, key):
        self.store.pop(key, None)
        return True


def _make_svc(cache=None):
    from draft_service import DraftService
    storage, _ = make_storage()
    return DraftService(lambda: storage, cache=cache)


# ==================== Service 层测试 ====================

def test_save_returns_id_and_increments_stats():
    svc = _make_svc()
    draft_id = svc.save('张三', '/api/process_sub_step', {'order_no': 'X1', 'quantity': 5})
    assert draft_id.startswith('张三_')
    s = svc.stats()
    assert s['saved'] == 1
    assert s['by_status'].get('pending') == 1


def test_save_rejects_empty_operator():
    svc = _make_svc()
    with pytest.raises(Exception):
        svc.save('', '/api/test', {})


def test_save_rejects_non_dict_payload():
    svc = _make_svc()
    with pytest.raises(Exception):
        svc.save('张三', '/api/test', 'not a dict')


def test_save_uses_cache_when_available():
    cache = FakeCache()
    svc = _make_svc(cache=cache)
    draft_id = svc.save('李四', '/api/test', {'k': 'v', 'n': 1})
    assert cache.set_count >= 1
    assert f'draft:{draft_id}' in cache.store


def test_get_from_cache():
    """有缓存时直接返回缓存，不查 DB"""
    cache = FakeCache()
    svc = _make_svc(cache=cache)
    draft_id = svc.save('王五', '/api/test', {'k': 'v'})
    item = svc.get(draft_id)
    assert item is not None
    assert item['operator'] == '王五'
    assert item['payload'] == {'k': 'v'}


def test_get_from_db_when_no_cache():
    """无缓存时从 DB 读"""
    svc = _make_svc(cache=None)
    draft_id = svc.save('王五', '/api/test', {'k': 'v'})
    item = svc.get(draft_id)
    assert item is not None
    assert item['operator'] == '王五'
    assert item['payload'] == {'k': 'v'}


def test_upsert_same_id():
    svc = _make_svc()
    id1 = svc.save('赵六', '/api/test', {'qty': 1})
    id2 = svc.save('赵六', '/api/test', {'qty': 99}, draft_id=id1)
    assert id1 == id2
    item = svc.get(id1)
    assert item['payload'] == {'qty': 99}


def test_submit_success():
    svc = _make_svc()
    draft_id = svc.save('submit_op', '/api/test', {'x': 1})
    result = svc.submit(draft_id, lambda d: True)
    assert result['ok'] is True
    assert result['status'] == 'synced'
    s = svc.stats()
    assert s['synced'] == 1


def test_submit_failure_keeps_draft():
    svc = _make_svc()
    draft_id = svc.save('fail_op', '/api/test', {'x': 1})
    result = svc.submit(draft_id, lambda d: False, max_retries=3)
    assert result['ok'] is False
    assert '重试 3 次' in result['message']
    s = svc.stats()
    assert s['failed'] == 1


def test_submit_raises_on_missing_draft():
    svc = _make_svc()
    with pytest.raises(Exception):
        svc.submit('nonexistent_id', lambda d: True)


def test_submit_already_synced_returns_immediately():
    svc = _make_svc()
    draft_id = svc.save('twice_op', '/api/test', {})
    svc.submit(draft_id, lambda d: True)
    counter = [0]
    def counting(d):
        counter[0] += 1
        return True
    result = svc.submit(draft_id, counting)
    assert result['ok'] is True
    assert counter[0] == 0


def test_list_by_operator_with_status():
    svc = _make_svc()
    svc.save('op1', '/api/test', {'i': 1})
    svc.save('op1', '/api/test', {'i': 2})
    items = svc.list_by_operator('op1', status='pending')
    assert len(items) == 2
    for it in items:
        assert it['status'] == 'pending'


def test_list_by_operator_no_filter():
    svc = _make_svc()
    svc.save('op1', '/api/test', {'i': 1})
    items = svc.list_by_operator('op1')
    assert len(items) == 1


def test_delete_returns_true_on_existing():
    svc = _make_svc()
    draft_id = svc.save('del_op', '/api/test', {})
    ok = svc.delete(draft_id)
    assert ok is True
    assert svc.get(draft_id) is None


def test_delete_returns_false_on_missing():
    svc = _make_svc()
    ok = svc.delete('nonexistent_id_xyz')
    assert ok is False


def test_stats_works_without_cache():
    svc = _make_svc(cache=None)
    s = svc.stats()
    assert 'saved' in s
    assert 'by_status' in s


def test_cache_optional_methods():
    """cache 抛异常时不影响主流程"""
    class BrokenCache:
        def get(self, *a, **k): raise IOError('down')
        def set(self, *a, **k): raise IOError('down')
        def delete(self, *a, **k): raise IOError('down')
    svc = _make_svc(cache=BrokenCache())
    draft_id = svc.save('吴十', '/api/test', {'k': 1})
    assert draft_id is not None
    assert svc.get(draft_id) is not None


def test_cleanup_synced():
    svc = _make_svc()
    draft_id = svc.save('cleanup_op', '/api/test', {})
    svc.submit(draft_id, lambda d: True)
    deleted = svc.cleanup_synced(older_than_days=0)
    assert deleted == 1


def test_submit_all():
    svc = _make_svc()
    svc.save('op1', '/api/test', {'i': 1})
    svc.save('op1', '/api/test', {'i': 2})
    svc.save('op1', '/api/test', {'i': 3})
    result = svc.submit_all('op1', lambda d: True, max_retries=1)
    assert result['total'] == 3
    assert result['synced'] == 3
    assert result['failed'] == 0


def test_submit_all_partial_failure():
    svc = _make_svc()
    svc.save('op1', '/api/test', {'i': 1})
    svc.save('op1', '/api/test', {'i': 2})
    counter = [0]
    def flaky(d):
        counter[0] += 1
        return counter[0] > 1
    result = svc.submit_all('op1', flaky, max_retries=1)
    assert result['total'] == 2
    assert result['synced'] == 1
    assert result['failed'] == 1


def test_concurrent_save():
    svc = _make_svc()
    errors = []
    def worker(i):
        try:
            svc.save(f'op{i}', '/api/test', {'i': i})
        except Exception as e:
            errors.append(str(e))
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert len(errors) == 0
    s = svc.stats()
    assert s['saved'] == 20


# ==================== HTTP 端点测试 ====================

def test_register_routes_creates_flask_app():
    from flask import Flask
    from draft_service import register_draft_routes
    app = Flask(__name__)
    storage, _ = make_storage()
    submitter_map = {'/api/process_sub_step': lambda d: True}
    svc = register_draft_routes(app, lambda: storage, submitter_map=submitter_map)
    rules = [r.rule for r in app.url_map.iter_rules() if r.rule.startswith('/api/draft')]
    assert '/api/draft/save' in rules
    assert '/api/draft/list' in rules
    assert '/api/draft/<draft_id>' in rules
    assert '/api/draft/submit/<draft_id>' in rules
    assert '/api/draft/sync_all' in rules
    assert '/api/draft/stats' in rules
    assert '/api/draft/cleanup' in rules


def test_draft_save_endpoint():
    from flask import Flask
    from draft_service import register_draft_routes
    app = Flask(__name__)
    storage, _ = make_storage()
    register_draft_routes(app, lambda: storage, submitter_map={})
    client = app.test_client()
    rv = client.post('/api/draft/save', json={
        'operator': 'test_op',
        'endpoint': '/api/process_sub_step',
        'payload': {'order_no': 'X1', 'quantity': 10}
    })
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['code'] == 0
    assert 'draft_id' in data['data']


def test_draft_save_rejects_empty_operator():
    from flask import Flask
    from draft_service import register_draft_routes
    app = Flask(__name__)
    storage, _ = make_storage()
    register_draft_routes(app, lambda: storage)
    client = app.test_client()
    rv = client.post('/api/draft/save', json={'payload': {}})
    assert rv.status_code == 400


def test_draft_save_rejects_invalid_payload():
    from flask import Flask
    from draft_service import register_draft_routes
    app = Flask(__name__)
    storage, _ = make_storage()
    register_draft_routes(app, lambda: storage)
    client = app.test_client()
    rv = client.post('/api/draft/save', json={
        'operator': 'op1',
        'payload': 'not a dict'
    })
    assert rv.status_code == 400


def test_draft_list_endpoint():
    from flask import Flask
    from draft_service import register_draft_routes
    app = Flask(__name__)
    storage, _ = make_storage()
    register_draft_routes(app, lambda: storage)
    client = app.test_client()
    rv = client.get('/api/draft/list?operator=test_op')
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['code'] == 0
    assert data['data']['count'] == 0


def test_draft_list_endpoint_with_data():
    from flask import Flask
    from draft_service import register_draft_routes
    app = Flask(__name__)
    storage, _ = make_storage()
    register_draft_routes(app, lambda: storage)
    client = app.test_client()
    client.post('/api/draft/save', json={'operator': 'op1', 'payload': {'a': 1}})
    client.post('/api/draft/save', json={'operator': 'op1', 'payload': {'a': 2}})
    rv = client.get('/api/draft/list?operator=op1')
    assert rv.status_code == 200
    data = rv.get_json()['data']
    assert data['count'] == 2


def test_draft_list_requires_operator():
    from flask import Flask
    from draft_service import register_draft_routes
    app = Flask(__name__)
    storage, _ = make_storage()
    register_draft_routes(app, lambda: storage)
    client = app.test_client()
    rv = client.get('/api/draft/list')
    assert rv.status_code == 400


def test_draft_get_not_found():
    from flask import Flask
    from draft_service import register_draft_routes
    app = Flask(__name__)
    storage, _ = make_storage()
    register_draft_routes(app, lambda: storage)
    client = app.test_client()
    rv = client.get('/api/draft/nonexistent')
    assert rv.status_code == 404


def test_draft_get_existing():
    from flask import Flask
    from draft_service import register_draft_routes
    app = Flask(__name__)
    storage, _ = make_storage()
    register_draft_routes(app, lambda: storage)
    client = app.test_client()
    rv = client.post('/api/draft/save', json={'operator': 'op1', 'payload': {'a': 1}})
    draft_id = rv.get_json()['data']['draft_id']
    rv2 = client.get(f'/api/draft/{draft_id}')
    assert rv2.status_code == 200
    assert rv2.get_json()['data']['payload'] == {'a': 1}


def test_draft_delete_endpoint():
    from flask import Flask
    from draft_service import register_draft_routes
    app = Flask(__name__)
    storage, _ = make_storage()
    register_draft_routes(app, lambda: storage)
    client = app.test_client()
    rv = client.post('/api/draft/save', json={'operator': 'op1', 'payload': {}})
    draft_id = rv.get_json()['data']['draft_id']
    rv2 = client.delete(f'/api/draft/{draft_id}')
    assert rv2.status_code == 200
    rv3 = client.get(f'/api/draft/{draft_id}')
    assert rv3.status_code == 404


def test_draft_submit_with_submitter():
    from flask import Flask
    from draft_service import register_draft_routes
    app = Flask(__name__)
    storage, _ = make_storage()
    submitter_map = {'/api/test': lambda d: True}
    register_draft_routes(app, lambda: storage, submitter_map=submitter_map)
    client = app.test_client()
    rv = client.post('/api/draft/save', json={
        'operator': 'op1', 'endpoint': '/api/test', 'payload': {'k': 'v'}
    })
    draft_id = rv.get_json()['data']['draft_id']
    rv2 = client.post(f'/api/draft/submit/{draft_id}')
    assert rv2.status_code == 200
    assert rv2.get_json()['data']['ok'] is True


def test_draft_submit_with_failure():
    from flask import Flask
    from draft_service import register_draft_routes
    app = Flask(__name__)
    storage, _ = make_storage()
    submitter_map = {'/api/test': lambda d: False}
    register_draft_routes(app, lambda: storage, submitter_map=submitter_map)
    client = app.test_client()
    rv = client.post('/api/draft/save', json={
        'operator': 'op1', 'endpoint': '/api/test', 'payload': {'k': 'v'}
    })
    draft_id = rv.get_json()['data']['draft_id']
    rv2 = client.post(f'/api/draft/submit/{draft_id}')
    assert rv2.status_code == 502
    assert rv2.get_json()['data']['ok'] is False


def test_draft_submit_no_submitter_map():
    from flask import Flask
    from draft_service import register_draft_routes
    app = Flask(__name__)
    storage, _ = make_storage()
    register_draft_routes(app, lambda: storage, submitter_map=None)
    client = app.test_client()
    rv = client.post('/api/draft/save', json={'operator': 'op1', 'payload': {}})
    draft_id = rv.get_json()['data']['draft_id']
    rv2 = client.post(f'/api/draft/submit/{draft_id}')
    assert rv2.status_code == 503


def test_draft_sync_all_endpoint():
    from flask import Flask
    from draft_service import register_draft_routes
    app = Flask(__name__)
    storage, _ = make_storage()
    submitter_map = {'/api/test': lambda d: True}
    register_draft_routes(app, lambda: storage, submitter_map=submitter_map)
    client = app.test_client()
    client.post('/api/draft/save', json={'operator': 'op1', 'endpoint': '/api/test', 'payload': {'a': 1}})
    client.post('/api/draft/save', json={'operator': 'op1', 'endpoint': '/api/test', 'payload': {'a': 2}})
    rv = client.post('/api/draft/sync_all', json={'operator': 'op1'})
    assert rv.status_code == 200
    data = rv.get_json()['data']
    assert data['total'] == 2
    assert data['synced'] == 2
    assert data['failed'] == 0


def test_draft_stats_endpoint():
    from flask import Flask
    from draft_service import register_draft_routes
    app = Flask(__name__)
    storage, _ = make_storage()
    register_draft_routes(app, lambda: storage)
    client = app.test_client()
    rv = client.get('/api/draft/stats')
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['code'] == 0
    assert 'saved' in data['data']


def test_draft_cleanup_endpoint():
    from flask import Flask
    from draft_service import register_draft_routes
    app = Flask(__name__)
    storage, _ = make_storage()
    register_draft_routes(app, lambda: storage)
    client = app.test_client()
    rv = client.post('/api/draft/cleanup', json={'older_than_days': 0})
    assert rv.status_code == 200
    assert 'deleted' in rv.get_json()['data']


def test_draft_cleanup_default_days():
    from flask import Flask
    from draft_service import register_draft_routes
    app = Flask(__name__)
    storage, _ = make_storage()
    register_draft_routes(app, lambda: storage)
    client = app.test_client()
    rv = client.post('/api/draft/cleanup', json={})
    assert rv.status_code == 200


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
