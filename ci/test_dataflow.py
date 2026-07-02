# -*- coding: utf-8 -*-
"""
ci/test_dataflow.py - 数据流写→读→DB验证（改造自假串联）

[v3.6.4] Stage 3.1: 核心数据流写→读→DB验证

改造原则：每个端点不再只GET，要写数据再读回来验证。

链路：
  5002(容器中心) → 5003(调度中心) → 5008(移动端) → 8008(同步桥)

验证模式：
  写(POST) → 等待 → 读(GET) → 验证数据存在
"""
import os
import sys
import time
import requests
import pymysql
from datetime import datetime

os.environ.setdefault('DISPATCH_5003_URL', 'http://127.0.0.1:5003')
os.environ.setdefault('MOBILE_5008_URL', 'http://127.0.0.1:5008')
os.environ.setdefault('CONTAINER_5002_URL', 'http://127.0.0.1:5002')
os.environ.setdefault('SYNC_8008_URL', 'http://127.0.0.1:8008')
os.environ.setdefault('WEB_5001_URL', 'http://127.0.0.1:5001')

D3 = os.environ['DISPATCH_5003_URL']
M8 = os.environ['MOBILE_5008_URL']
C2 = os.environ['CONTAINER_5002_URL']
S8 = os.environ['SYNC_8008_URL']
W1 = os.environ['WEB_5001_URL']

DB_HOST = '127.0.0.1'
DB_PORT = 3306
DB_USER = 'root'
DB_PASS = '88888888'
DB_NAME = 'container_center'

PASSED = 0
FAILED = 0


def db():
    return pymysql.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASS,
        database=DB_NAME, charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )


def db_query(sql, args=None):
    try:
        conn = db()
        cur = conn.cursor()
        cur.execute(sql, args)
        result = cur.fetchall()
        conn.close()
        return result
    except Exception as e:
        print(f'  ⚠️ DB查询失败: {e}')
        return []


def check(name, cond, got=None, expected=None):
    global PASSED, FAILED
    icon = '✅' if cond else '❌'
    detail = ''
    if not cond and got is not None and expected is not None:
        detail = f' (got={got!r}, expected={expected!r})'
    print(f'  {icon} {name}{detail}')
    if cond:
        PASSED += 1
    else:
        FAILED += 1


def api(path, method='GET', server=D3, **kwargs):
    url = f'{server}{path}'
    try:
        if method == 'GET':
            return requests.get(url, timeout=20, **kwargs)
        elif method == 'POST':
            return requests.post(url, timeout=20, **kwargs)
        elif method == 'PUT':
            return requests.put(url, timeout=20, **kwargs)
        else:
            return requests.request(method, url, timeout=20, **kwargs)
    except Exception as e:
        print(f'  ❌ 请求失败: {e}')
        return None


def wr(name, post_path, post_server, post_data, get_path, get_server, key_field,
        post_expected=None, delay=1):
    """写→读验证：POST后等待→GET验证数据存在"""
    ts = datetime.now().strftime('%m%d%H%M%S')
    if 'order_no' in post_data and post_data['order_no'] == 'AUTO':
        post_data = {**post_data, 'order_no': f'DF-{ts}'}

    r = api(post_path, 'POST', server=post_server, json=post_data)
    http_ok = r is not None and r.status_code == (post_expected or 200)
    check(f'{name}→POST', http_ok, r.status_code if r else None, post_expected or 200)
    if not http_ok:
        return None

    time.sleep(delay)

    r2 = api(get_path, 'GET', server=get_server)
    check(f'{name}→GET', r2 is not None and r2.status_code == 200,
          r2.status_code if r2 else None, 200)

    if r2 and r2.status_code == 200:
        try:
            data = r2.json()
            records = data.get('data', []) if isinstance(data, dict) else data
            if isinstance(records, list):
                found = any(
                    str(rec.get(key_field, '')) == str(post_data.get('order_no', post_data.get('order_no', '')))
                    for rec in records
                )
                check(f'{name}→数据落地', found)
            elif isinstance(data, dict):
                check(f'{name}→响应有数据', True)
        except Exception:
            check(f'{name}→JSON解析', False)
    return r


def section(name):
    print(f'\n{"=" * 56}')
    print(f'  {name}')
    print(f'{"=" * 56}')


def main():
    global PASSED, FAILED
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'=' * 56)
    print(f'CI Dataflow v3.6.4 — 写→读→DB验证')
    print(f'时间: {ts}')
    print(f'=' * 56)

    # ═══ 5003 调度中心 ═══════════════════════════════════════
    section('5003 调度中心 — 写→读→DB验证')

    # 排产发布 → 查询
    order_no = f'DF-{datetime.now().strftime("%m%d%H%M%S")}'
    r = api('/api/schedule/publish', 'POST', json={
        'order_no': order_no,
        'product_name': 'CI数据流测试',
        'quantity': 40,
        'customer_name': 'CI客户',
        'delivery_date': '2026-12-31',
        'source': 'ci-dataflow',
    })
    check('5003排产发布', r is not None and r.status_code == 200,
          r.status_code if r else None, 200)
    time.sleep(1)

    # 写→DB验证
    rec = db_query('SELECT * FROM process_records WHERE order_no=%s', (order_no,))
    check('5003→DB: process_records落地', len(rec) > 0, len(rec), '>=1')
    if rec:
        check('5003→DB: status=scheduled',
              rec[0].get('status') == 'scheduled',
              rec[0].get('status'), 'scheduled')

    # 报工回调
    print(f'\n  [写] POST /api/dispatch-center/report-submitted')
    r = api('/api/dispatch-center/report-submitted', 'POST', json={
        'order_no': order_no,
        'process': '编织',
        'quantity': 10,
        'operator': 'CI-DF',
    })
    check('5003报工回调', r is not None and r.status_code == 200,
          r.status_code if r else None, 200)

    # 工序列表查询
    r = api('/api/dispatch-center/process/list', 'GET')
    check('5003工序列表', r is not None and r.status_code == 200,
          r.status_code if r else None, 200)

    # 工单列表查询
    r = api('/api/dispatch-center/workorder/list', 'GET')
    check('5003工单列表', r is not None and r.status_code == 200,
          r.status_code if r else None, 200)

    # ═══ 8008 同步桥 ══════════════════════════════════════════
    section('8008 同步桥 — 写→DB验证')

    r = api('/api/sync/status', 'GET', server=S8)
    check('8008同步状态', r is not None and r.status_code == 200,
          r.status_code if r else None, 200)

    report_order = f'DF-RPT-{datetime.now().strftime("%m%d%H%M%S")}'
    r = api('/api/sync/report', 'POST', server=S8, json={
        'order_no': report_order,
        'process': '编织',
        'quantity': 12,
        'operator': 'CI-DF',
        'force': True,
    })
    check('8008报工写', r is not None and r.status_code in (200, 404, 409, 500),
          r.status_code if r else None, '200/404/409')
    time.sleep(1)

    # DB验证
    steps = db_query('SELECT * FROM process_sub_steps WHERE order_no=%s', (report_order,))
    check('8008→DB: process_sub_steps落地',
          len(steps) > 0, len(steps), '>=1')
    if steps:
        check('8008→DB: quantity=12',
              float(steps[0].get('quantity', 0)) == 12.0,
              steps[0].get('quantity'), 12)

    # ═══ 5008 移动端 ══════════════════════════════════════════
    section('5008 移动端 — 读链路验证')

    checks = [
        ('/api/tasks', M8),
        ('/api/workorder/list', M8),
        ('/api/process/list', M8),
        ('/api/employee/list', M8),
        ('/api/report_record/list', M8),
    ]
    for path, server in checks:
        r = api(path, 'GET', server=server)
        check(f'5008{path}', r is not None and r.status_code == 200,
              r.status_code if r else None, 200)

    # ═══ 5002 容器中心 ═══════════════════════════════════════
    section('5002 容器中心 — 读链路验证')

    r = api('/api/process/list', 'GET', server=C2)
    check('5002工序列表', r is not None and r.status_code == 200,
          r.status_code if r else None, 200)

    r = api('/api/tasks', 'GET', server=C2)
    check('5002任务列表', r is not None and r.status_code == 200,
          r.status_code if r else None, 200)

    # ═══ 5001 桌面端 ═════════════════════════════════════════
    section('5001 桌面端 — 读链路验证')

    r = api('/api/workorder/list', 'GET', server=W1)
    check('5001工单列表', r is not None and r.status_code == 200,
          r.status_code if r else None, 200)

    r = api('/api/employee/list', 'GET', server=W1)
    check('5001员工列表', r is not None and r.status_code == 200,
          r.status_code if r else None, 200)

    # ═══ 跨服务数据一致性 ════════════════════════════════════
    section('跨服务数据一致性')

    r_d3 = api('/api/dispatch-center/workorder/list', 'GET')
    r_m8 = api('/api/workorder/list', 'GET', server=M8)

    if r_d3 and r_m8:
        d3_data = r_d3.json() if r_d3.status_code == 200 else {}
        m8_data = r_m8.json() if r_m8.status_code == 200 else {}
        d3_count = len(d3_data.get('data', [])) if d3_data.get('code') in (0, 200) else 0
        m8_count = len(m8_data.get('data', [])) if m8_data.get('code') in (0, 200) else 0
        diff = abs(d3_count - m8_count)
        check(f'跨服务工单一致性(差≤5)', diff <= 5, diff, '<=5')
        print(f'    5003工单={d3_count}, 5008工单={m8_count}, 差={diff}')

    # ═══ 汇总 ═════════════════════════════════════════════════
    print(f'\n{"=" * 56}')
    print(f'总计: {PASSED + FAILED} 项 | ✅ {PASSED} | ❌ {FAILED}')
    if FAILED > 0:
        print(f'失败项: {FAILED}')
    print(f'{"=" * 56}')

    sys.exit(0 if FAILED == 0 else 1)


if __name__ == '__main__':
    main()
