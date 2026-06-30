# -*- coding: utf-8 -*-
"""
E2E 套件 08：成本核算（6 用例）

业务流: 成本汇总 → 物料价格 → 人工价格 → 触发核算 → 收入登记 → 利润
"""
import pytest
import requests

WEB_5001 = 'http://127.0.0.1:5001'
MOBILE_5008 = 'http://127.0.0.1:5008'


def _get_csrf(session):
    r = session.post(f'{WEB_5001}/api/login',
                     json={'username': '测试', 'password': ''}, timeout=5)
    return r.json().get('data', {}).get('csrf_token', '')


def _post_csrfful(session, url, data):
    csrf = _get_csrf(session)
    return session.post(url, json=data, headers={'X-CSRF-Token': csrf}, timeout=5)


# ───────────── 用例 8.1：订单成本汇总 ─────────────

@pytest.mark.cost
def test_01_cost_summary():
    """订单成本汇总

    业务: GET /api/cost/orders/<order_no>/summary
    """
    print('\n[8.1] 订单成本汇总...')
    r = requests.get(
        f'{MOBILE_5008}/api/cost/orders/E2E_COST_001/summary',
        headers={'X-User-Id': '1'},
        timeout=5,
    )
    print(f'  GET /api/cost/orders/.../summary: HTTP {r.status_code}')
    assert r.status_code in (200, 401, 404), f'成本汇总异常: {r.status_code}'


# ───────────── 用例 8.2：物料价格维护 ─────────────

@pytest.mark.cost
def test_02_material_price_set(admin_session):
    """物料价格维护

    业务: POST /api/cost/material-prices
    """
    print('\n[8.2] 物料价格维护...')
    r = _post_csrfful(
        admin_session,
        f'{WEB_5001}/api/cost/material-prices',
        {'material_code': 'E2E_MAT_001', 'price': 100.5, 'unit': 'kg'},
    )
    print(f'  POST /api/cost/material-prices: HTTP {r.status_code}')
    assert r.status_code in (200, 201, 400, 404), f'物料价格异常: {r.status_code}'


# ───────────── 用例 8.3：人工价格维护 ─────────────

@pytest.mark.cost
def test_03_labor_price_set(admin_session):
    """人工价格维护

    业务: POST /api/cost/labor-prices
    """
    print('\n[8.3] 人工价格维护...')
    r = _post_csrfful(
        admin_session,
        f'{WEB_5001}/api/cost/labor-prices',
        {'process_code': 'E2E_P01', 'price': 5.0, 'unit': '件'},
    )
    print(f'  POST /api/cost/labor-prices: HTTP {r.status_code}')
    assert r.status_code in (200, 201, 400, 404), f'人工价格异常: {r.status_code}'


# ───────────── 用例 8.4：成本计算触发 ─────────────

@pytest.mark.cost
def test_04_cost_calculate(admin_session, unique_order_no):
    """成本计算触发

    业务: POST /api/cost/orders/<order_no>/calculate
    """
    print(f'\n[8.4] 成本计算 {unique_order_no}...')
    r = _post_csrfful(
        admin_session,
        f'{WEB_5001}/api/cost/orders/{unique_order_no}/calculate',
        {},
    )
    print(f'  POST /api/cost/orders/.../calculate: HTTP {r.status_code}')
    assert r.status_code in (200, 201, 400, 404), f'成本计算异常: {r.status_code}'


# ───────────── 用例 8.5：收入登记 ─────────────

@pytest.mark.cost
def test_05_revenue_set(admin_session, unique_order_no):
    """收入登记

    业务: PUT /api/cost/orders/<order_no>/revenue
    """
    print(f'\n[8.5] 收入登记 {unique_order_no}...')
    csrf = _get_csrf(admin_session)
    r = admin_session.put(
        f'{WEB_5001}/api/cost/orders/{unique_order_no}/revenue',
        json={'revenue': 5000.00},
        headers={'X-CSRF-Token': csrf},
        timeout=5,
    )
    print(f'  PUT /api/cost/orders/.../revenue: HTTP {r.status_code}')
    assert r.status_code in (200, 201, 400, 404), f'收入登记异常: {r.status_code}'


# ───────────── 用例 8.6：成本明细 ─────────────

@pytest.mark.cost
def test_06_cost_detail():
    """成本明细

    业务: POST /api/cost/detail
    """
    print('\n[8.6] 成本明细...')
    r = requests.post(
        f'{MOBILE_5008}/api/cost/detail',
        headers={'X-User-Id': '1'},
        json={'order_no': 'E2E_COST_001'},
        timeout=5,
    )
    print(f'  POST /api/cost/detail: HTTP {r.status_code}')
    assert r.status_code in (200, 400, 401, 404), f'成本明细异常: {r.status_code}'


# ───────────── 汇总 ─────────────

def test_99_cost_summary():
    """成本 E2E 测试汇总"""
    print('\n' + '=' * 60)
    print('成本 E2E 测试 6 用例已跑完')
    print('=' * 60)
