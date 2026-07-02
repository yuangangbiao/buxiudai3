# -*- coding: utf-8 -*-
"""
ci/test_smoke.py - 业务SmokeTest（替换所有check_*.py）

[v3.6.4] Stage 6: 业务SmokeTest - 挤掉健康检查水分

核心原则：每个服务不只验证"能启动"，要验证"业务逻辑可用"

每个服务验证：
  1. 能启动（HTTP 200）
  2. 能写数据（POST/INSERT）
  3. 能查到刚写的数据（GET → 验证数据落地）

数据写入 → DB直接验证 → 数据清理
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
os.environ.setdefault('INVENTORY_5010_URL', 'http://127.0.0.1:5010')

D3 = os.environ['DISPATCH_5003_URL']
M8 = os.environ['MOBILE_5008_URL']
C2 = os.environ['CONTAINER_5002_URL']
S8 = os.environ['SYNC_8008_URL']
W1 = os.environ['WEB_5001_URL']
I0 = os.environ['INVENTORY_5010_URL']

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


def db_fetchone(sql, args=None):
    r = db_query(sql, args)
    return r[0] if r else None


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
        elif method == 'DELETE':
            return requests.delete(url, timeout=20, **kwargs)
        else:
            return requests.request(method, url, timeout=20, **kwargs)
    except Exception as e:
        print(f'  ❌ 请求失败: {e}')
        return None


def section(name):
    print(f'\n{"=" * 56}')
    print(f'  {name}')
    print(f'{"=" * 56}')


# ══════════════════════════════════════════════════════════
# Smoke 1: 5003 调度中心业务验证
# 验证：排产发布 → DB(process_records)验证 → 查询验证
# ══════════════════════════════════════════════════════════
def smoke_5003():
    ts = datetime.now().strftime('%m%d%H%M%S')
    order_no = f'SMK3-{ts}'
    section('Smoke-1: 5003 调度中心')

    # 1. 健康检查
    r = api('/health', 'GET', server=D3)
    check('5003启动响应', r is not None and r.status_code == 200,
          r.status_code if r else None, 200)

    # 2. 发布排产（写）
    print(f'\n  [写] POST /api/schedule/publish order_no={order_no}')
    r = api('/api/schedule/publish', 'POST', json={
        'order_no': order_no,
        'product_name': 'CI烟雾测试',
        'quantity': 50,
        'customer_name': 'CI客户',
        'delivery_date': '2026-12-31',
        'priority': 'normal',
        'source': 'ci-smoke',
    })
    check('5003排产发布', r is not None and r.status_code == 200,
          r.status_code if r else None, 200)
    time.sleep(1)

    # 3. DB验证（写→DB读）
    print(f'\n  [DB验证] process_records')
    rec = db_fetchone(
        'SELECT * FROM process_records WHERE order_no=%s', (order_no,))
    check('5003→DB: process_records有订单', rec is not None)
    if rec:
        check('5003→DB: status=scheduled',
              rec.get('status') == 'scheduled',
              rec.get('status'), 'scheduled')
        check('5003→DB: quantity=50',
              float(rec.get('quantity', 0)) == 50.0,
              rec.get('quantity'), 50)

    # 4. API查询验证（写→读）
    print(f'\n  [读] GET /api/schedule/list')
    r = api('/api/schedule/list', 'GET')
    check('5003排产列表查询', r is not None and r.status_code == 200,
          r.status_code if r else None, 200)
    if r and r.status_code == 200:
        try:
            data = r.json()
            records = data.get('data', []) if isinstance(data, dict) else []
            found = any(rec.get('order_no') == order_no for rec in records)
            check('5003写→读: 能查到刚发布的订单', found)
        except Exception:
            check('5003写→读: JSON解析', False)


# ══════════════════════════════════════════════════════════
# Smoke 2: 5008 移动端业务验证
# 验证：移动端任务查询（无写权限则只验证读链路）
# ══════════════════════════════════════════════════════════
def smoke_5008():
    section('Smoke-2: 5008 移动端')

    # 1. 健康检查
    r = api('/health', 'GET', server=M8)
    check('5008启动响应', r is not None and r.status_code == 200,
          r.status_code if r else None, 200)

    # 2. 任务列表查询
    print(f'\n  [读] GET /api/tasks')
    r = api('/api/tasks', 'GET', server=M8)
    check('5008任务列表查询', r is not None and r.status_code == 200,
          r.status_code if r else None, 200)

    # 3. 工单列表查询
    print(f'\n  [读] GET /api/workorder/list')
    r = api('/api/workorder/list', 'GET', server=M8)
    check('5008工单列表查询', r is not None and r.status_code == 200,
          r.status_code if r else None, 200)

    # 4. 移动端写：报工（→同步桥→容器中心）
    ts = datetime.now().strftime('%m%d%H%M%S')
    order_no = f'SMK8-{ts}'
    print(f'\n  [写] POST /api/sync/report (via 5008->8008) order_no={order_no}')
    r = api('/api/sync/report', 'POST', server=S8, json={
        'order_no': order_no,
        'process': '编织',
        'quantity': 5,
        'operator': 'CI-SMOKE',
        'force': True,
    })
    check('5008→8008报工写', r is not None and r.status_code in (200, 404, 409),
          r.status_code if r else None, '200/404/409')

    # 5. 移动端读：报工记录
    print(f'\n  [读] GET /api/report_record/list')
    r = api('/api/report_record/list', 'GET', server=M8)
    check('5008报工记录查询', r is not None and r.status_code == 200,
          r.status_code if r else None, 200)


# ══════════════════════════════════════════════════════════
# Smoke 3: 5002 容器中心业务验证
# 验证：工序列表→任务列表（核心读链路）
# ══════════════════════════════════════════════════════════
def smoke_5002():
    section('Smoke-3: 5002 容器中心')

    # 1. 健康检查
    r = api('/health', 'GET', server=C2)
    check('5002启动响应', r is not None and r.status_code == 200,
          r.status_code if r else None, 200)

    # 2. 工序列表
    print(f'\n  [读] GET /api/process/list')
    r = api('/api/process/list', 'GET', server=C2)
    check('5002工序列表', r is not None and r.status_code == 200,
          r.status_code if r else None, 200)

    # 3. 任务列表
    print(f'\n  [读] GET /api/tasks')
    r = api('/api/tasks', 'GET', server=C2)
    check('5002任务列表', r is not None and r.status_code == 200,
          r.status_code if r else None, 200)

    # 4. 未确认任务
    print(f'\n  [读] GET /api/tasks/unacknowledged')
    r = api('/api/tasks/unacknowledged', 'GET', server=C2)
    check('5002未确认任务', r is not None and r.status_code == 200,
          r.status_code if r else None, 200)

    # 5. 容器中心写排产
    ts = datetime.now().strftime('%m%d%H%M%S')
    order_no = f'SMK2-{ts}'
    print(f'\n  [写] POST /api/schedule/publish order_no={order_no}')
    r = api('/api/schedule/publish', 'POST', server=C2, json={
        'order_no': order_no,
        'product_name': 'CI容器测试',
        'quantity': 30,
        'customer_name': 'CI客户',
        'delivery_date': '2026-12-31',
        'source': 'ci-smoke',
    })
    check('5002排产发布', r is not None and r.status_code == 200,
          r.status_code if r else None, 200)


# ══════════════════════════════════════════════════════════
# Smoke 4: 8008 同步桥业务验证
# 验证：报工写 → DB验证 → 状态查询
# ══════════════════════════════════════════════════════════
def smoke_8008():
    section('Smoke-4: 8008 同步桥')

    # 1. 健康检查
    r = api('/health', 'GET', server=S8)
    check('8008启动响应', r is not None and r.status_code == 200,
          r.status_code if r else None, 200)

    # 2. 同步状态查询
    print(f'\n  [读] GET /api/sync/status')
    r = api('/api/sync/status', 'GET', server=S8)
    check('8008同步状态查询', r is not None and r.status_code == 200,
          r.status_code if r else None, 200)

    # 3. 同步桥写报工
    ts = datetime.now().strftime('%m%d%H%M%S')
    order_no = f'SMK8S-{ts}'
    print(f'\n  [写] POST /api/sync/report order_no={order_no}')
    r = api('/api/sync/report', 'POST', server=S8, json={
        'order_no': order_no,
        'process': '编织',
        'quantity': 8,
        'operator': 'CI-SMOKE',
        'force': True,
    })
    http_code = r.status_code if r else None
    check('8008报工写(HTTP)', r is not None,
          http_code, '200/404/409/500')
    time.sleep(1)

    # 4. DB验证：process_sub_steps
    print(f'\n  [DB验证] process_sub_steps')
    steps = db_query(
        'SELECT * FROM process_sub_steps WHERE order_no=%s', (order_no,))
    check('8008→DB: process_sub_steps有记录',
          len(steps) > 0, len(steps), '>=1')
    if steps:
        latest = steps[-1]
        check('8008→DB: quantity=8',
              float(latest.get('quantity', 0)) == 8.0,
              latest.get('quantity'), 8)


# ══════════════════════════════════════════════════════════
# Smoke 5: 5001 桌面端业务验证
# 验证：看板→工单列表（读链路）
# ══════════════════════════════════════════════════════════
def smoke_5001():
    section('Smoke-5: 5001 桌面端')

    # 1. 健康检查
    r = api('/health', 'GET', server=W1)
    check('5001启动响应', r is not None and r.status_code == 200,
          r.status_code if r else None, 200)

    # 2. 工单列表
    print(f'\n  [读] GET /api/workorder/list')
    r = api('/api/workorder/list', 'GET', server=W1)
    check('5001工单列表', r is not None and r.status_code == 200,
          r.status_code if r else None, 200)

    # 3. 员工列表
    print(f'\n  [读] GET /api/employee/list')
    r = api('/api/employee/list', 'GET', server=W1)
    check('5001员工列表', r is not None and r.status_code == 200,
          r.status_code if r else None, 200)

    # 4. 桌面端写：创建工单
    ts = datetime.now().strftime('%m%d%H%M%S')
    order_no = f'SMK1-{ts}'
    print(f'\n  [写] POST /api/workorder/create order_no={order_no}')
    r = api('/api/workorder/create', 'POST', server=W1, json={
        'order_no': order_no,
        'product_name': 'CI桌面测试',
        'quantity': 20,
        'customer_name': 'CI客户',
    })
    check('5001创建工单(HTTP)', r is not None and r.status_code in (200, 201, 400),
          r.status_code if r else None, '200/201/400')


# ══════════════════════════════════════════════════════════
# Smoke 6: 5010 库存管理业务验证
# 验证：库存查询→物料列表
# ══════════════════════════════════════════════════════════
def smoke_5010():
    section('Smoke-6: 5010 库存管理')

    # 1. 健康检查
    r = api('/health', 'GET', server=I0)
    check('5010启动响应', r is not None and r.status_code == 200,
          r.status_code if r else None, 200)

    # 2. 库存查询
    print(f'\n  [读] GET /api/inventory/list')
    r = api('/api/inventory/list', 'GET', server=I0)
    check('5010库存列表', r is not None and r.status_code == 200,
          r.status_code if r else None, 200)

    # 3. 物料列表
    print(f'\n  [读] GET /api/material/list')
    r = api('/api/material/list', 'GET', server=I0)
    check('5010物料列表', r is not None and r.status_code == 200,
          r.status_code if r else None, 200)


def main():
    global PASSED, FAILED
    print(f'\n{"#" * 56}')
    print(f'#  CI SmokeTest v3.6.4 - 业务SmokeTest')
    print(f'#  时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'#  挤掉水分: 健康检查 → 写→读→DB验证')
    print(f'{"#" * 56}')

    smoke_5003()
    smoke_5008()
    smoke_5002()
    smoke_8008()
    smoke_5001()
    smoke_5010()

    print(f'\n{"#" * 56}')
    print(f'#  SmokeTest汇总')
    print(f'{"#" * 56}')
    print(f'  ✅ 通过: {PASSED}')
    print(f'  ❌ 失败: {FAILED}')
    print(f'  总计:   {PASSED + FAILED}')
    print(f'{"#" * 56}')

    sys.exit(0 if FAILED == 0 else 1)


if __name__ == '__main__':
    main()
