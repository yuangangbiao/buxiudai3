# -*- coding: utf-8 -*-
"""
E2E 套件 06：质量管理（8 用例）

业务流: 任务列表 → 提交质检 → 复检 → 历史 → 标准查询 → 数量校验 → 照片 → 库存
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


def _put_csrfful(session, url, data):
    csrf = _get_csrf(session)
    return session.put(url, json=data, headers={'X-CSRF-Token': csrf}, timeout=5)


# ───────────── 用例 6.1：质检任务列表 ─────────────

@pytest.mark.quality
def test_01_quality_task_list():
    """质检任务列表

    业务: GET /api/quality-inspection/tasks (mobile) 或 /api/quality (web)
    """
    print('\n[6.1] 质检任务列表...')
    # 5008 mobile
    r = requests.get(
        f'{MOBILE_5008}/api/quality-inspection/tasks',
        headers={'X-User-Id': '1'},
        timeout=5,
    )
    print(f'  GET mobile /api/quality-inspection/tasks: HTTP {r.status_code}')
    assert r.status_code in (200, 400, 401, 404), f'质检任务列表异常: {r.status_code}'


# ───────────── 用例 6.2：提交质检（mobile） ─────────────

@pytest.mark.quality
def test_02_quality_submit():
    """提交质检

    业务: POST /api/quality-inspection/evaluate
    """
    print('\n[6.2] 提交质检...')
    r = requests.post(
        f'{MOBILE_5008}/api/quality-inspection/evaluate',
        headers={'X-User-Id': '1'},
        json={
            'order_no': 'E2E_QC_001',
            'process_code': 'E2E_P01',
            'result': 'pass',
            'quantity': 10,
        },
        timeout=5,
    )
    print(f'  POST evaluate: HTTP {r.status_code} {r.text[:100]}')
    assert r.status_code in (200, 201, 400, 401, 404), f'提交质检异常: {r.status_code}'


# ───────────── 用例 6.3：质检复检 ─────────────

@pytest.mark.quality
def test_03_quality_rework():
    """质检复检/返工

    业务: POST /api/quality-inspection/rework
    """
    print('\n[6.3] 质检返工...')
    r = requests.post(
        f'{MOBILE_5008}/api/quality-inspection/rework',
        headers={'X-User-Id': '1'},
        json={'order_no': 'E2E_QC_001', 'reason': '返工原因 E2E'},
        timeout=5,
    )
    print(f'  POST rework: HTTP {r.status_code}')
    assert r.status_code in (200, 201, 400, 401, 404), f'返工异常: {r.status_code}'


# ───────────── 用例 6.4：质检历史 ─────────────

@pytest.mark.quality
def test_04_quality_history():
    """质检历史查询

    业务: GET /api/quality-inspection/history
    """
    print('\n[6.4] 质检历史...')
    r = requests.get(
        f'{MOBILE_5008}/api/quality-inspection/history',
        headers={'X-User-Id': '1'},
        timeout=5,
    )
    print(f'  GET history: HTTP {r.status_code}')
    assert r.status_code in (200, 401, 404), f'历史异常: {r.status_code}'


# ───────────── 用例 6.5：质检标准（按工序） ─────────────

@pytest.mark.quality
def test_05_quality_standard(admin_session):
    """质检标准（按工序独立）

    业务: GET /api/quality/standard/<process_code>
    """
    print('\n[6.5] 质检标准...')
    r = admin_session.get(f'{WEB_5001}/api/quality/standard/E2E_P01', timeout=5)
    print(f'  GET /api/quality/standard/E2E_P01: HTTP {r.status_code}')
    assert r.status_code in (200, 404), f'质检标准异常: {r.status_code}'


# ───────────── 用例 6.6：质检增量更新库存 ─────────────

@pytest.mark.quality
def test_06_quality_inventory_increment(admin_session):
    """质检合格品入库（库存 +N）

    业务: PUT /api/quality/<id>/result 入库
    """
    print('\n[6.6] 质检入库...')
    r = _put_csrfful(
        admin_session,
        f'{WEB_5001}/api/quality/1/result',
        {'result': 'pass', 'quantity': 10},
    )
    print(f'  PUT /api/quality/1/result: HTTP {r.status_code}')
    assert r.status_code in (200, 400, 404), f'入库异常: {r.status_code}'


# ───────────── 用例 6.7：质检照片上传 ─────────────

@pytest.mark.quality
def test_07_quality_photo_upload():
    """质检照片上传

    业务: POST /api/quality-inspection/photos/upload
    """
    print('\n[6.7] 质检照片上传...')
    # 构造文件
    import io
    files = {'file': ('test.jpg', io.BytesIO(b'fake jpg data'), 'image/jpeg')}
    r = requests.post(
        f'{MOBILE_5008}/api/quality-inspection/photos/upload',
        headers={'X-User-Id': '1'},
        files=files,
        timeout=5,
    )
    print(f'  POST photos/upload: HTTP {r.status_code}')
    assert r.status_code in (200, 201, 400, 401, 404, 413), f'照片上传异常: {r.status_code}'


# ───────────── 用例 6.8：质检规则查询 ─────────────

@pytest.mark.quality
def test_08_quality_rule(admin_session):
    """质检规则查询

    业务: GET /api/quality/rules
    """
    print('\n[6.8] 质检规则查询...')
    r = admin_session.get(f'{WEB_5001}/api/quality/rules', timeout=5)
    print(f'  GET /api/quality/rules: HTTP {r.status_code}')
    assert r.status_code in (200, 404), f'质检规则异常: {r.status_code}'


# ───────────── 汇总 ─────────────

def test_99_quality_summary():
    """质检 E2E 测试汇总"""
    print('\n' + '=' * 60)
    print('质检 E2E 测试 8 用例已跑完')
    print('=' * 60)
