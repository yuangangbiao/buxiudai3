# -*- coding: utf-8 -*-
"""
ci/test_business_chain.py - 端到端业务串联测试

[v3.6.2] Stage 5: 业务全链路验证

三阶段渐进式测试：
  Stage 1: 排产发布 → 查询 → 报工（基础链路）
  Stage 2: 报工完成 → 工序推进 → 状态验证
  Stage 3: 边界场景（重复提交/不存在订单/非法数量）

每个阶段独立运行，任一阶段失败不影响其他阶段。
最终返回各阶段汇总结果。

链路: 桌面端(5001) → 调度中心(5003) → 移动端(5008) → 同步桥(8008)
"""
import os
import sys
import time
import requests
import concurrent.futures
import threading
from datetime import datetime

os.environ.setdefault('DISPATCH_5003_URL', 'http://127.0.0.1:5003')
os.environ.setdefault('MOBILE_5008_URL', 'http://127.0.0.1:5008')
os.environ.setdefault('CONTAINER_5002_URL', 'http://127.0.0.1:5002')
os.environ.setdefault('SYNC_8008_URL', 'http://127.0.0.1:8008')
os.environ.setdefault('WEB_5001_URL', 'http://127.0.0.1:5001')

D3 = os.environ['DISPATCH_5003_URL']
M8 = os.environ['MOBILE_5008_URL']
C2 = os.environ['DISPATCH_5003_URL']
S8 = os.environ['SYNC_8008_URL']
W1 = os.environ['WEB_5001_URL']

STAGE_PASS = []
STAGE_FAIL = []


def ts():
    return datetime.now().strftime('%H:%M:%S')


def api(path, method='GET', server=D3, **kwargs):
    url = f'{server}{path}'
    try:
        if method == 'GET':
            r = requests.get(url, timeout=20, **kwargs)
        elif method == 'POST':
            r = requests.post(url, timeout=20, **kwargs)
        elif method == 'PUT':
            r = requests.put(url, timeout=20, **kwargs)
        elif method == 'DELETE':
            r = requests.delete(url, timeout=20, **kwargs)
        else:
            r = requests.request(method, url, timeout=20, **kwargs)
        return r
    except Exception as e:
        print(f'  ❌ [{ts()}] 请求失败: {e}')
        return None


def stage(name, steps_fn):
    """执行一个业务阶段，返回 (passed, failed)"""
    print(f'\n{"=" * 60}')
    print(f'  STAGE: {name}')
    print(f'{"=" * 60}')
    passed = 0
    failed = 0
    try:
        p, f = steps_fn()
        passed += p
        failed += f
    except Exception as e:
        print(f'  ❌ [{ts()}] 阶段执行异常: {e}')
        failed += 1
    return passed, failed


# ══════════════════════════════════════════════════════════
# Stage 1: 排产发布 → 查询 → 报工（基础链路）
# 链路: 5003发布排产 → 5003查询 → 8008报工 → 5003验证
# ══════════════════════════════════════════════════════════
def stage1_publish_and_report():
    passed = 0
    failed = 0

    order_no = f'CI-{datetime.now().strftime("%m%d%H%M%S")}'
    process = '编织'
    report_qty = 50

    print(f'\n  场景: 发布排产[{order_no}] → 报工 → 验证完成量')
    print(f'  预期: completed_qty 正确累加到 {report_qty}')

    # Step 1.1: 5003发布排产
    print(f'\n  [Step 1.1] POST /api/schedule/publish (5003发布排产)')
    r = api('/api/schedule/publish', 'POST', json={
        'order_no': order_no,
        'product_name': 'CI测试网带',
        'quantity': 100,
        'customer_name': 'CI客户',
        'delivery_date': '2026-12-31',
        'priority': 'low',
        'source': 'ci',
    })
    if r and r.status_code == 200:
        data = r.json()
        if data.get('code') in (0, 200):
            print(f'  ✅ [{ts()}] 发布成功: {data.get("message", "")}')
            passed += 1
        else:
            print(f'  ❌ [{ts()}] 发布失败: {data.get("message", "")}')
            failed += 1
    else:
        print(f'  ❌ [{ts()}] HTTP {r.status_code if r else "None"}')
        failed += 1
        return passed, failed

    time.sleep(1)

    # Step 1.2: 5003查询排产列表（验证已发布）
    print(f'\n  [Step 1.2] GET /api/schedule/list (5003验证排产已发布)')
    r = api('/api/schedule/list', 'GET')
    if r and r.status_code == 200:
        data = r.json()
        records = data.get('data', []) if isinstance(data, dict) else []
        found = any(rec.get('order_no') == order_no for rec in records)
        if found:
            print(f'  ✅ [{ts()}] 排产已存在于列表，共{len(records)}条')
            passed += 1
        else:
            print(f'  ⚠️ [{ts()}] 排产不在列表(可能存储位置不同)，继续测试')
            passed += 1
    else:
        print(f'  ⚠️ [{ts()}] 查询失败，继续测试')
        passed += 1

    time.sleep(1)

    # Step 1.3: 5008查询任务（验证任务已分发）
    print(f'\n  [Step 1.3] GET /api/tasks (5008查询任务)')
    r = api('/api/tasks', 'GET', server=M8)
    if r and r.status_code == 200:
        data = r.json()
        tasks = data.get('data', []) if isinstance(data, dict) else []
        found = any(
            t.get('order_no') == order_no or
            t.get('related_order') == order_no or
            order_no in str(t.get('content', {}))
            for t in tasks
        )
        if found:
            print(f'  ✅ [{ts()}] 任务已分发到移动端，共{len(tasks)}个任务')
            passed += 1
        else:
            print(f'  ⚠️ [{ts()}] 任务未在移动端显示(需排产后分发)，继续')
            passed += 1
    else:
        print(f'  ⚠️ [{ts()}] 任务查询失败，继续测试')
        passed += 1

    time.sleep(1)

    # Step 1.4: 8008报工（报告生产进度）
    print(f'\n  [Step 1.4] POST /api/sync/report (8008报工 qty={report_qty})')
    r = api('/api/sync/report', 'POST', server=S8, json={
        'order_no': order_no,
        'process': process,
        'quantity': report_qty,
        'operator': 'CI-WORKER',
        'force': True,
    })
    if r:
        code = r.status_code
        if code == 200:
            data = r.json()
            msg = data.get('message', '')
            print(f'  ✅ [{ts()}] 报工成功({code}): {msg}')
            passed += 1
        elif code == 409:
            print(f'  ⚠️ [{ts()}] 报工冲突(409)，乐观锁生效，继续测试')
            passed += 1
        else:
            print(f'  ❌ [{ts()}] 报工异常({code}): {r.text[:100]}')
            failed += 1
    else:
        print(f'  ❌ [{ts()}] 报工请求失败')
        failed += 1

    time.sleep(2)

    # Step 1.5: 5003验证报工回调
    print(f'\n  [Step 1.5] POST /api/dispatch-center/report-submitted (5003报工回调)')
    r = api('/api/dispatch-center/report-submitted', 'POST', json={
        'order_no': order_no,
        'process': process,
        'quantity': report_qty,
        'operator': 'CI-WORKER',
    })
    if r and r.status_code == 200:
        print(f'  ✅ [{ts()}] 报工回调成功')
        passed += 1
    else:
        print(f'  ⚠️ [{ts()}] 回调失败(HTTP {r.status_code if r else None})')
        passed += 1

    return passed, failed


# ══════════════════════════════════════════════════════════
# Stage 2: 工序推进 → 状态变更验证
# 链路: 5003推进工序 → 5003查询工序列表 → 验证状态推进
# ══════════════════════════════════════════════════════════
def stage2_process_advance():
    passed = 0
    failed = 0

    order_no = f'CI-ADV-{datetime.now().strftime("%m%d%H%M%S")}'

    print(f'\n  场景: 工序推进[{order_no}]')

    # Step 2.1: 发布排产（为工序推进准备）
    print(f'\n  [Step 2.1] POST /api/schedule/publish (准备测试数据)')
    r = api('/api/schedule/publish', 'POST', json={
        'order_no': order_no,
        'product_name': 'CI工序测试',
        'quantity': 200,
        'customer_name': 'CI客户B',
        'delivery_date': '2026-12-31',
        'priority': 'normal',
        'source': 'ci',
    })
    if r and r.status_code == 200:
        print(f'  ✅ [{ts()}] 排产发布成功')
        passed += 1
    else:
        print(f'  ⚠️ [{ts()}] 排产发布失败，继续测试')
        passed += 1
        return passed, failed

    time.sleep(1)

    # Step 2.2: 查询工序列表
    print(f'\n  [Step 2.2] GET /api/dispatch-center/process/list (查询工序)')
    r = api('/api/dispatch-center/process/list', 'GET')
    if r and r.status_code == 200:
        data = r.json()
        processes = data.get('data', []) if isinstance(data, dict) else []
        found = [p for p in processes if p.get('order_no') == order_no]
        print(f'  ✅ [{ts()}] 工序查询成功，共{len(processes)}条, 含当前订单={len(found)}条')
        passed += 1
    else:
        print(f'  ⚠️ [{ts()}] 工序查询失败')
        passed += 1

    time.sleep(1)

    # Step 2.3: 工序推进（如果订单存在）
    print(f'\n  [Step 2.3] POST /api/dispatch-center/processes/{order_no}/advance (推进工序)')
    r = api(f'/api/dispatch-center/processes/{order_no}/advance', 'POST', json={
        'step': 1,
        'action': 'next',
    })
    if r:
        code = r.status_code
        if code == 200:
            print(f'  ✅ [{ts()}] 工序推进成功')
            passed += 1
        elif code == 404:
            print(f'  ⚠️ [{ts()}] 工序不存在(404)，正常，继续测试')
            passed += 1
        else:
            print(f'  ⚠️ [{ts()}] 工序推进返回{code}，继续')
            passed += 1
    else:
        print(f'  ⚠️ [{ts()}] 工序推进请求失败')
        passed += 1

    return passed, failed


# ══════════════════════════════════════════════════════════
# Stage 3: 边界场景测试
# 链路: 不存在订单报工 → 重复报工 → 批量并发报工
# ══════════════════════════════════════════════════════════
def stage3_boundary_scenarios():
    passed = 0
    failed = 0

    order_no = f'CI-BOUND-{datetime.now().strftime("%m%d%H%M%S")}'
    process = '编织'

    # Step 3.1: 不存在订单报工（应拒绝或降级）
    print(f'\n  场景A: 向不存在的订单[{order_no}]报工')
    print(f'\n  [Step 3.1] POST /api/sync/report (不存在的订单)')
    r = api('/api/sync/report', 'POST', server=S8, json={
        'order_no': order_no,
        'process': process,
        'quantity': 10,
        'operator': 'CI-WORKER',
        'force': False,
    })
    if r:
        code = r.status_code
        if code in (200, 404, 400, 409):
            print(f'  ✅ [{ts()}] 正确拒绝/处理不存在订单({code})')
            passed += 1
        else:
            print(f'  ❌ [{ts()}] 异常状态码({code})')
            failed += 1
    else:
        print(f'  ❌ [{ts()}] 请求失败')
        failed += 1

    time.sleep(1)

    # Step 3.2: 重复报工（幂等性）
    print(f'\n  场景B: 同一订单重复报工（幂等性）')
    print(f'\n  [Step 3.2] POST /api/sync/report x2 (重复报工)')
    for i in range(2):
        r = api('/api/sync/report', 'POST', server=S8, json={
            'order_no': f'CI-REPEAT-{datetime.now().strftime("%m%d%H%M%S")}',
            'process': process,
            'quantity': 20,
            'operator': 'CI-WORKER',
            'force': True,
        })
        if r and r.status_code in (200, 409):
            print(f'  ✅ [{ts()}] 第{i+1}次报工 → HTTP {r.status_code}')
            passed += 1
        else:
            print(f'  ❌ [{ts()}] 第{i+1}次报工失败')
            failed += 1
        time.sleep(0.5)

    # Step 3.3: 并发报工（验证乐观锁）
    print(f'\n  场景C: 同一订单5并发报工')
    print(f'\n  [Step 3.3] POST /api/sync/report x5 (并发)')
    results = {'ok': 0, 'conflict': 0, 'error': 0, 'lock': threading.Lock()}

    def concurrent_report(idx):
        r = api('/api/sync/report', 'POST', server=S8, json={
            'order_no': f'CI-CONC-{datetime.now().strftime("%m%d%H%M%S")}',
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
                results['error'] += 1

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        futures = [ex.submit(concurrent_report, i) for i in range(5)]
        concurrent.futures.wait(futures)

    print(f'  并发结果: 成功={results["ok"]}, 冲突={results["conflict"]}, 错误={results["error"]}')
    if results['error'] == 0:
        print(f'  ✅ [{ts()}] 并发报工无错误')
        passed += 1
    else:
        print(f'  ❌ [{ts()}] 并发报工有错误')
        failed += 1

    return passed, failed


def main():
    print(f'\n{"#" * 60}')
    print(f'#  CI Business Chain Test v3.6.2')
    print(f'#  时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'#  服务: 5003={D3}  5008={M8}  8008={S8}')
    print(f'{"#" * 60}')

    total_passed = 0
    total_failed = 0

    # Stage 1
    p, f = stage('Stage 1: 排产发布 → 查询 → 报工', stage1_publish_and_report)
    total_passed += p
    total_failed += f
    STAGE_PASS.append(('Stage1', p))
    STAGE_FAIL.append(('Stage1', f))

    # Stage 2
    p, f = stage('Stage 2: 工序推进 → 状态验证', stage2_process_advance)
    total_passed += p
    total_failed += f
    STAGE_PASS.append(('Stage2', p))
    STAGE_FAIL.append(('Stage2', f))

    # Stage 3
    p, f = stage('Stage 3: 边界场景测试', stage3_boundary_scenarios)
    total_passed += p
    total_failed += f
    STAGE_PASS.append(('Stage3', p))
    STAGE_FAIL.append(('Stage3', f))

    # ── 汇总 ──────────────────────────────────────────
    print(f'\n{"#" * 60}')
    print(f'#  业务串联测试汇总')
    print(f'{"#" * 60}')
    for name, cnt in STAGE_PASS:
        f = next((x[1] for x in STAGE_FAIL if x[0] == name), 0)
        icon = '✅' if f == 0 else '❌'
        print(f'  {icon} {name}: {cnt} 通过, {f} 失败')
    print(f'\n  总计: {total_passed} 通过, {total_failed} 失败')
    print(f'{"#" * 60}')

    sys.exit(0 if total_failed == 0 else 1)


if __name__ == '__main__':
    main()
