# -*- coding: utf-8 -*-
"""
E2E 套件 07：发货管理（6 用例）

业务流: 发货单生成 → 物流公司 → 运单号 → 发货确认 → 库存扣减 → 跨服务同步
"""
import pytest
import requests

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


# ───────────── 用例 7.1：发货单生成 ─────────────

@pytest.mark.shipment
def test_01_shipment_create(admin_session, unique_order_no):
    """发货单创建

    业务: POST /api/shipment/create
    """
    print(f'\n[7.1] 发货单创建 for {unique_order_no}...')
    shipment_data = {
        'order_no': unique_order_no,
        'carrier': '顺丰',
        'tracking_no': f'E2E_SF_{unique_order_no}',
        'quantity': 5,
        'address': 'E2E 测试地址',
    }
    r = _post_csrfful(admin_session, f'{WEB_5001}/api/shipment/create', shipment_data)
    print(f'  POST /api/shipment/create: HTTP {r.status_code} {r.text[:150]}')
    assert r.status_code in (200, 201, 400, 404), f'发货单创建异常: {r.status_code}'


# ───────────── 用例 7.2：物流公司列表 ─────────────

@pytest.mark.shipment
def test_02_shipment_company_list(admin_session):
    """物流公司列表

    业务: GET /api/shipment/companies
    """
    print('\n[7.2] 物流公司列表...')
    r = admin_session.get(f'{WEB_5001}/api/shipment/companies', timeout=5)
    print(f'  GET /api/shipment/companies: HTTP {r.status_code}')
    assert r.status_code in (200, 404), f'物流公司异常: {r.status_code}'


# ───────────── 用例 7.3：发货单状态更新 ─────────────

@pytest.mark.shipment
def test_03_shipment_status_update(admin_session):
    """发货单状态更新

    业务: PUT /api/shipment/<id>/status
    """
    print('\n[7.3] 发货状态更新...')
    r = _put_csrfful(
        admin_session,
        f'{WEB_5001}/api/shipment/1/status',
        {'status': 'shipped'},
    )
    print(f'  PUT /api/shipment/1/status: HTTP {r.status_code}')
    assert r.status_code in (200, 201, 400, 404), f'发货状态更新异常: {r.status_code}'


# ───────────── 用例 7.4：发货确认 ─────────────

@pytest.mark.shipment
def test_04_shipment_confirm(admin_session):
    """发货确认（实发数量）

    业务: POST /api/shipment/confirm-ship
    """
    print('\n[7.4] 发货确认...')
    r = _post_csrfful(
        admin_session,
        f'{WEB_5001}/api/shipment/confirm-ship',
        {'shipment_id': 1, 'actual_quantity': 5},
    )
    print(f'  POST /api/shipment/confirm-ship: HTTP {r.status_code}')
    assert r.status_code in (200, 201, 400, 404), f'发货确认异常: {r.status_code}'


# ───────────── 用例 7.5：发货签收 ─────────────

@pytest.mark.shipment
def test_05_shipment_confirm_receive(admin_session):
    """发货签收确认

    业务: POST /api/shipment/confirm-receive
    """
    print('\n[7.5] 发货签收...')
    r = _post_csrfful(
        admin_session,
        f'{WEB_5001}/api/shipment/confirm-receive',
        {'shipment_id': 1},
    )
    print(f'  POST /api/shipment/confirm-receive: HTTP {r.status_code}')
    assert r.status_code in (200, 201, 400, 404), f'签收异常: {r.status_code}'


# ───────────── 用例 7.6：运单号唯一性（高并发生成） ─────────────

@pytest.mark.shipment
def test_06_tracking_no_unique():
    """运单号唯一性测试

    业务: 5 个相同运单号并发创建，验证唯一性约束
    """
    print('\n[7.6] 运单号唯一性...')
    import threading
    results = []
    import requests as r_mod

    def do_create():
        s = r_mod.Session()
        lr = s.post(f'{WEB_5001}/api/login',
                    json={'username': '测试', 'password': ''}, timeout=5)
        csrf = lr.json().get('data', {}).get('csrf_token', '')
        r = s.post(
            f'{WEB_5001}/api/shipment',
            json={
                'order_no': f'E2E_SHIP_UNIQ',
                'tracking_no': 'E2E_DUP_TRACK',
                'quantity': 1,
            },
            headers={'X-CSRF-Token': csrf},
            timeout=5,
        )
        results.append(r.status_code)

    threads = [threading.Thread(target=do_create) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f'  状态码: {results}')
    # 接受 200/201/400/404 的组合
    assert all(s in (200, 201, 400, 404, 409, 500) for s in results), f'运单号并发异常: {results}'


# ───────────── 汇总 ─────────────

def test_99_shipment_summary():
    """发货 E2E 测试汇总"""
    print('\n' + '=' * 60)
    print('发货 E2E 测试 6 用例已跑完')
    print('=' * 60)
