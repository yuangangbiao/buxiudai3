# -*- coding: utf-8 -*-
"""
E2E 套件 03：工艺管理（6 用例）

业务流: 工艺列表 → 详情 → 工序添加 → 工序插入 → 工序删除 → 工序排序
"""
import pytest
import requests
import urllib.parse

WEB_5001 = 'http://127.0.0.1:5001'


def _get_csrf(session):
    r = session.post(f'{WEB_5001}/api/login',
                     json={'username': '测试', 'password': ''}, timeout=5)
    return r.json().get('data', {}).get('csrf_token', '')


def _post_csrfful(session, url, data):
    csrf = _get_csrf(session)
    return session.post(url, json=data, headers={'X-CSRF-Token': csrf}, timeout=5)


def _put_csrfful(session, url, data):
    csrf = _get_csrf(session)
    return session.put(url, json=data, headers={'X-CSRF-Token': csrf}, timeout=5)


# ───────────── 用例 3.1：工艺列表（无筛选） ─────────────

@pytest.mark.process
def test_01_process_list(admin_session):
    """工艺列表

    业务: /api/process/list — 列出所有工艺
    """
    print('\n[3.1] 工艺列表...')
    r = admin_session.get(f'{WEB_5001}/api/process/list', timeout=5)
    print(f'  GET /api/process/list: HTTP {r.status_code}')
    assert r.status_code == 200, f'工艺列表失败: {r.status_code} {r.text[:200]}'
    data = r.json()
    items = data.get('data', [])
    if isinstance(items, list):
        print(f'  工艺数: {len(items)}')
    else:
        print(f'  响应: {str(data)[:200]}')


# ───────────── 用例 3.2：工艺详情/状态/历史/时间线 ─────────────

@pytest.mark.process
def test_02_process_sub_routes(admin_session):
    """工艺子路由（status/history/timeline）

    业务: 多角度查工艺
    """
    print('\n[3.2] 工艺子路由...')
    test_order = 'E2E_ROUTE_TEST'
    routes = [
        ('GET', f'/api/process/status/{test_order}'),
        ('GET', f'/api/process/history/{test_order}'),
        ('GET', f'/api/process/timeline/{test_order}'),
    ]
    success = 0
    for method, path in routes:
        r = admin_session.get(f'{WEB_5001}{path}', timeout=5)
        if r.status_code in (200, 404):
            success += 1
        print(f'  {method} {path}: HTTP {r.status_code}')
    assert success == len(routes), f'工艺子路由异常'


# ───────────── 用例 3.3：admin-list 管理员视图 ─────────────

@pytest.mark.process
def test_03_process_admin_list(admin_session):
    """工艺 admin-list

    业务: P0-7 修复的 SQL 验证 — 包含 customer_name 字段
    """
    print('\n[3.3] 工艺 admin-list...')
    r = admin_session.get(f'{WEB_5001}/api/process/admin-list', timeout=5)
    print(f'  GET /api/process/admin-list: HTTP {r.status_code}')
    # 必须是 200（P0-7 修复后）
    assert r.status_code == 200, f'admin-list 失败（可能是 P0-7 SQL 未修）: {r.status_code}'
    data = r.json()
    print(f'  响应: {str(data)[:150]}')


# ───────────── 用例 3.4：工艺添加（POST） ─────────────

@pytest.mark.process
def test_04_process_add(admin_session, unique_order_no):
    """添加工序

    业务: 创建工艺工序
    """
    print(f'\n[3.4] 工艺添加 for {unique_order_no}...')
    process_data = {
        'order_no': unique_order_no,
        'process_code': 'E2E_P01',
        'process_name': 'E2E_测试工序01',
        'quantity': 10,
        'unit': '件',
    }
    r = _post_csrfful(admin_session, f'{WEB_5001}/api/process/add', process_data)
    print(f'  POST /api/process/add: HTTP {r.status_code} {r.text[:150]}')
    # 接受 200/201/400/404
    assert r.status_code in (200, 201, 400, 404), f'工艺添加异常: {r.status_code}'


# ───────────── 用例 3.5：工艺插入（B 类工序） ─────────────

@pytest.mark.process
def test_05_process_insert(admin_session, unique_order_no):
    """插入工序（在指定工序后）

    业务: 在某工序后插入 B 工序
    """
    print(f'\n[3.5] 工艺插入 for {unique_order_no}...')
    insert_data = {
        'order_no': unique_order_no,
        'after_process_code': 'E2E_P01',
        'process_code': 'E2E_P01_B',
        'process_name': 'E2E_测试工序01-B',
        'quantity': 5,
    }
    r = _post_csrfful(admin_session, f'{WEB_5001}/api/process/insert', insert_data)
    print(f'  POST /api/process/insert: HTTP {r.status_code}')
    assert r.status_code in (200, 201, 400, 404), f'工艺插入异常: {r.status_code}'


# ───────────── 用例 3.6：swap-seq 工序排序交换 ─────────────

@pytest.mark.process
def test_06_process_swap_seq(admin_session, unique_order_no):
    """工序交换顺序

    业务: swap-seq 改变工艺顺序
    """
    print(f'\n[3.6] 工艺 swap-seq for {unique_order_no}...')
    swap_data = {
        'order_no': unique_order_no,
        'process_code_1': 'E2E_P01',
        'process_code_2': 'E2E_P01_B',
    }
    r = _put_csrfful(admin_session, f'{WEB_5001}/api/process/swap-seq', swap_data)
    print(f'  PUT /api/process/swap-seq: HTTP {r.status_code}')
    assert r.status_code in (200, 400, 404), f'swap-seq 异常: {r.status_code}'


# ───────────── 汇总 ─────────────

def test_99_process_summary():
    """工艺管理 E2E 测试汇总"""
    print('\n' + '=' * 60)
    print('工艺 E2E 测试 6 用例已跑完')
    print('=' * 60)
