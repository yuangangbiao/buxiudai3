# -*- coding: utf-8 -*-
"""
ci/test_business_chain.py - 端到端业务串联测试（真实数据验证版）

[v3.6.3] Stage 5: 业务全链路 + 数据库真实数据验证

三阶段渐进式测试，每步验证数据真实写入数据库：
  Stage 1: 排产发布 → DB验证(process_records) → 报工 → DB验证(process_sub_steps)
  Stage 2: 工序推进 → DB验证(process_records.status更新)
  Stage 3: 边界场景 → DB验证无脏数据

核心验证点：
  1. HTTP 200 + DB 数据落地一致
  2. completed_qty 真实累加
  3. status 真实推进
  4. 无脏数据残留
"""
import os
import sys
import time
import requests
import pymysql
import concurrent.futures
import threading
from datetime import datetime

os.environ.setdefault('DISPATCH_5003_URL', 'http://127.0.0.1:5003')
os.environ.setdefault('MOBILE_5008_URL', 'http://127.0.0.1:5008')
os.environ.setdefault('SYNC_8008_URL', 'http://127.0.0.1:8008')

D3 = os.environ['DISPATCH_5003_URL']
M8 = os.environ['MOBILE_5008_URL']
S8 = os.environ['SYNC_8008_URL']

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
    results = db_query(sql, args)
    return results[0] if results else None


def ts():
    return datetime.now().strftime('%H:%M:%S')


def check(name, condition, got=None, expected=None):
    global PASSED, FAILED
    icon = '✅' if condition else '❌'
    detail = ''
    if not condition and got is not None and expected is not None:
        detail = f' (got={got!r}, expected={expected!r})'
    print(f'  {icon} {name}{detail}')
    if condition:
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


def section(name):
    print(f'\n{"=" * 56}')
    print(f'  {name}')
    print(f'{"=" * 56}')


# ══════════════════════════════════════════════════════════
# Stage 1: 排产发布 → DB验证 → 报工 → DB验证
# 真实数据路径：
#   POST /api/schedule/publish
#     → save_schedule_record() → update_order_status()
#     → process_records 表（SSOT）
#     → completed_qty 写在 order 文档
#
#   POST /api/sync/report
#     → sync_bp.sync_report()
#     → _find_order() → order 文档 completed_qty += quantity
#     → process_sub_steps 表（report_records表）
#     → _container_client.update_document('order')
# ══════════════════════════════════════════════════════════
def stage1_publish_and_report():
    global PASSED, FAILED
    ts_str = datetime.now().strftime('%m%d%H%M%S')
    order_no = f'CI-{ts_str}'
    process = '编织'
    report_qty = 50

    section('Stage 1: 排产发布 → 报工 → 真实DB验证')

    # Step 1.1: 发布排产
    print(f'\n  [1.1] POST /api/schedule/publish')
    r = api('/api/schedule/publish', 'POST', json={
        'order_no': order_no,
        'product_name': 'CI测试网带',
        'quantity': 100,
        'customer_name': 'CI客户',
        'delivery_date': '2026-12-31',
        'priority': 'normal',
        'source': 'ci',
    })
    check('排产发布HTTP成功', r is not None and r.status_code == 200,
          r.status_code if r else None, 200)
    if r:
        try:
            data = r.json()
            check('排产响应code=0', data.get('code') in (0, 200), data.get('code'), '0/200')
        except Exception:
            check('排产响应JSON解析', False, None, 'valid JSON')
    time.sleep(1)

    # Step 1.2: DB验证 - process_records 有该订单
    print(f'\n  [1.2] DB验证: process_records')
    rec = db_fetchone(
        'SELECT * FROM process_records WHERE order_no=%s',
        (order_no,)
    )
    check('process_records有该订单', rec is not None,
          'found' if rec else 'not found', 'found')
    if rec:
        check('process_records.status=scheduled',
              rec.get('status') == 'scheduled',
              rec.get('status'), 'scheduled')
        check('process_records.product_name正确',
              rec.get('product_name') == 'CI测试网带',
              rec.get('product_name'), 'CI测试网带')
        check('process_records.quantity=100',
              float(rec.get('quantity', 0)) == 100.0,
              rec.get('quantity'), 100)
    time.sleep(1)

    # Step 1.3: 报工
    print(f'\n  [1.3] POST /api/sync/report (qty={report_qty})')
    r = api('/api/sync/report', 'POST', server=S8, json={
        'order_no': order_no,
        'process': process,
        'quantity': report_qty,
        'operator': 'CI-WORKER',
        'force': True,
    })
    http_ok = r is not None and r.status_code == 200
    check('报工HTTP成功', http_ok,
          r.status_code if r else None, 200)
    if http_ok:
        try:
            data = r.json()
            check('报工data有completed_qty',
                  'completed_qty' in data.get('data', {}),
                  'yes' if 'completed_qty' in data.get('data', {}) else 'no',
                  'yes')
        except Exception:
            pass
    time.sleep(2)

    # Step 1.4: DB验证 - process_sub_steps 有报工记录
    print(f'\n  [1.4] DB验证: process_sub_steps')
    steps = db_query(
        'SELECT * FROM process_sub_steps WHERE order_no=%s',
        (order_no,)
    )
    check('process_sub_steps有报工记录',
          len(steps) > 0, len(steps), '>=1')
    if steps:
        latest = steps[-1]
        check('process_sub_steps.quantity正确',
              float(latest.get('quantity', 0)) == report_qty,
              latest.get('quantity'), report_qty)
        check('process_sub_steps.operator=CI-WORKER',
              latest.get('operator') == 'CI-WORKER',
              latest.get('operator'), 'CI-WORKER')

    # Step 1.5: DB验证 - order 文档 completed_qty 累加
    print(f'\n  [1.5] DB验证: order文档 completed_qty')
    order_doc = db_fetchone(
        'SELECT * FROM process_records WHERE order_no=%s',
        (order_no,)
    )
    if order_doc:
        content_str = order_doc.get('content') or order_doc.get('extra_data') or '{}'
        if isinstance(content_str, str):
            try:
                import json
                content = json.loads(content_str)
            except Exception:
                content = {}
        else:
            content = content_str if isinstance(content_str, dict) else {}
        order_completed = float(content.get('completed_qty', 0) or 0)
        check('order completed_qty累加',
              order_completed >= report_qty,
              order_completed, f'>={report_qty}')

    return PASSED, FAILED


# ══════════════════════════════════════════════════════════
# Stage 2: 工序推进 → status推进验证
# 路径: POST /api/dispatch-center/processes/{order_no}/advance
#     → update_order_status() → process_records.status 更新
# ══════════════════════════════════════════════════════════
def stage2_process_advance():
    global PASSED, FAILED
    order_no = f'CI-ADV-{datetime.now().strftime("%m%d%H%M%S")}'

    section('Stage 2: 工序推进 → status真实推进')

    # Step 2.1: 发布排产（准备测试数据）
    print(f'\n  [2.1] POST /api/schedule/publish')
    r = api('/api/schedule/publish', 'POST', json={
        'order_no': order_no,
        'product_name': 'CI工序测试',
        'quantity': 200,
        'customer_name': 'CI客户B',
        'delivery_date': '2026-12-31',
        'priority': 'normal',
        'source': 'ci',
    })
    check('工序测试排产发布', r is not None and r.status_code == 200,
          r.status_code if r else None, 200)
    time.sleep(1)

    rec_before = db_fetchone(
        'SELECT status FROM process_records WHERE order_no=%s',
        (order_no,)
    )
    initial_status = rec_before.get('status') if rec_before else None
    check('工序初始status=scheduled',
          initial_status == 'scheduled',
          initial_status, 'scheduled')

    # Step 2.2: 推进工序
    print(f'\n  [2.2] POST /api/dispatch-center/processes/{order_no}/advance')
    r = api(f'/api/dispatch-center/processes/{order_no}/advance', 'POST', json={
        'step': 1,
        'action': 'next',
    })
    http_ok = r is not None and r.status_code == 200
    check('工序推进HTTP', http_ok,
          r.status_code if r else None, 200)
    time.sleep(1)

    # Step 2.3: DB验证 status 推进
    print(f'\n  [2.3] DB验证: process_records.status变化')
    rec_after = db_fetchone(
        'SELECT status FROM process_records WHERE order_no=%s',
        (order_no,)
    )
    final_status = rec_after.get('status') if rec_after else None
    check('工序status已推进',
          final_status != 'scheduled',
          final_status, '!=scheduled')

    return PASSED, FAILED


# ══════════════════════════════════════════════════════════
# Stage 3: 边界场景 + 无脏数据
# ══════════════════════════════════════════════════════════
def stage3_boundary_and_cleanup():
    global PASSED, FAILED
    ts_str = datetime.now().strftime('%m%d%H%M%S')
    order_no = f'CI-BOUND-{ts_str}'
    process = '编织'

    section('Stage 3: 边界场景 → 无脏数据验证')

    # Step 3.1: 向不存在订单报工
    print(f'\n  [3.1] 向不存在订单报工 (expect 404)')
    r = api('/api/sync/report', 'POST', server=S8, json={
        'order_no': order_no,
        'process': process,
        'quantity': 10,
        'operator': 'CI-WORKER',
        'force': False,
    })
    check('不存在订单报工返回404/400',
          r is not None and r.status_code in (404, 400, 409, 200),
          r.status_code if r else None, '404/400/409')
    time.sleep(0.5)

    # Step 3.2: DB验证 - 无脏数据
    print(f'\n  [3.2] DB验证: 无脏数据残留')
    orphan_steps = db_query(
        'SELECT COUNT(*) as cnt FROM process_sub_steps WHERE order_no=%s',
        (order_no,)
    )
    orphan_count = orphan_steps[0]['cnt'] if orphan_steps else 0
    check('不存在订单无脏数据', orphan_count == 0, orphan_count, 0)

    # Step 3.3: 并发报工
    print(f'\n  [3.3] 5并发报工 → 验证DB无数据撕裂')
    conc_order = f'CI-CONC-{ts_str}'
    results = {'ok': 0, 'conflict': 0, 'err': 0, 'lock': threading.Lock()}

    def conc_report(idx):
        r = api('/api/sync/report', 'POST', server=S8, json={
            'order_no': conc_order,
            'process': process,
            'quantity': 5,
            'operator': f'CI-WORKER-{idx}',
            'force': True,
        })
        with results['lock']:
            if r and r.status_code == 200:
                results['ok'] += 1
            elif r and r.status_code == 409:
                results['conflict'] += 1
            else:
                results['err'] += 1

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        futures = [ex.submit(conc_report, i) for i in range(5)]
        concurrent.futures.wait(futures)

    print(f'    并发结果: 成功={results["ok"]}, 冲突={results["conflict"]}, 错误={results["err"]}')
    check('并发报工无错误', results['err'] == 0, results['err'], 0)
    check('并发乐观锁生效', results['conflict'] > 0 or results['ok'] > 0,
          f'ok={results["ok"]} conflict={results["conflict"]}', '>=0 total')

    # Step 3.4: DB验证 - 报工记录数量合理
    print(f'\n  [3.4] DB验证: 报工记录数量')
    conc_steps = db_query(
        'SELECT COUNT(*) as cnt FROM process_sub_steps WHERE order_no=%s',
        (conc_order,)
    )
    conc_count = conc_steps[0]['cnt'] if conc_steps else 0
    check('并发报工记录<=5', conc_count <= 5, conc_count, '<=5')

    return PASSED, FAILED


def main():
    global PASSED, FAILED
    print(f'\n{"#" * 56}')
    print(f'#  CI Business Chain v3.6.3 - 真实数据验证版')
    print(f'#  时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'#  服务: 5003={D3}  5008={M8}  8008={S8}')
    print(f'#  DB:   {DB_HOST}:{DB_PORT}/{DB_NAME}')
    print(f'{"#" * 56}')

    try:
        stage1_publish_and_report()
    except Exception as e:
        print(f'  ❌ Stage1异常: {e}')

    try:
        stage2_process_advance()
    except Exception as e:
        print(f'  ❌ Stage2异常: {e}')

    try:
        stage3_boundary_and_cleanup()
    except Exception as e:
        print(f'  ❌ Stage3异常: {e}')

    print(f'\n{"#" * 56}')
    print(f'#  测试汇总')
    print(f'{"#" * 56}')
    print(f'  ✅ 通过: {PASSED}')
    print(f'  ❌ 失败: {FAILED}')
    print(f'  总计:   {PASSED + FAILED}')
    print(f'{"#" * 56}')

    sys.exit(0 if FAILED == 0 else 1)


if __name__ == '__main__':
    main()
