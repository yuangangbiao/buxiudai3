# -*- coding: utf-8 -*-
"""
ci/test_dataflow.py - 调度中心/报工任务/数据源 CI数据流验证

[v3.6.2] Stage 3.1: 核心数据流端到端验证

验证链路：
  5002(容器中心) ─→ 5003(调度中心) ─→ 5008(移动端) ─→ 8008(同步桥)

每个测试返回：(endpoint, status_code, latency_ms, ok)
"""
import os
import sys
import time
import requests
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

TESTS = []
FAILED = []
TIMEOUT = 30


def t(label, server, method, path, expected=None, **kwargs):
    url = f'{server}{path}'
    start = time.time()
    try:
        if method.upper() == 'GET':
            r = requests.get(url, timeout=TIMEOUT, **kwargs)
        elif method.upper() == 'POST':
            r = requests.post(url, timeout=TIMEOUT, **kwargs)
        else:
            r = requests.request(method.upper(), url, timeout=TIMEOUT, **kwargs)
        latency = (time.time() - start) * 1000
        code = r.status_code
        ok = (expected is None) or (code == expected)
        TESTS.append((label, code, latency, ok))
        status = '✅' if ok else '❌'
        print(f'  {status} [{code}] {label} ({latency:.0f}ms)')
        if not ok:
            FAILED.append((label, code, expected))
        return r
    except requests.exceptions.Timeout:
        latency = (time.time() - start) * 1000
        TESTS.append((label, 'TIMEOUT', latency, False))
        FAILED.append((label, 'TIMEOUT', expected))
        print(f'  ❌ [TIMEOUT] {label} ({latency:.0f}ms)')
        return None
    except Exception as e:
        latency = (time.time() - start) * 1000
        TESTS.append((label, f'ERR:{e}', latency, False))
        FAILED.append((label, str(e), expected))
        print(f'  ❌ [ERR] {label} → {e}')
        return None


def section(name):
    print(f'\n── {name} ──')


def main():
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'=' * 60)
    print(f'CI Dataflow Test v3.6.2 | {ts}')
    print(f'=' * 60)

    # ── 5002 容器中心：排产/工序/任务 ─────────────────────
    section('5002 Container Center — 排产/工序/任务')
    t('容器-健康', C2, 'GET', '/health', 200)
    t('容器-工序列表', C2, 'GET', '/api/process/list', 200)
    t('容器-任务列表', C2, 'GET', '/api/tasks', 200)
    t('容器-未确认任务', C2, 'GET', '/api/tasks/unacknowledged', 200)
    t('容器-发布排产(SAMPLE)', C2, 'POST', '/api/schedule/publish', 200,
      json={'order_no': f'DATA-{datetime.now().strftime("%m%d%H%M%S")}'})

    # ── 5003 调度中心：工单/排产/工序/报工 ─────────────
    section('5003 Dispatch Center — 工单/排产/工序')
    t('调度-健康', D3, 'GET', '/health', 200)
    t('调度-工单列表', D3, 'GET', '/api/dispatch-center/workorder/list', 200)
    t('调度-排产列表', D3, 'GET', '/api/schedule/list', 200)
    t('调度-工序列表', D3, 'GET', '/api/dispatch-center/process/list', 200)
    t('调度-报工记录', D3, 'GET', '/api/report_record/list', 200)
    t('调度-质检列表', D3, 'GET', '/api/dispatch-center/quality/list', 200)
    t('调度-发货列表', D3, 'GET', '/api/dispatch-center/shipment/list', 200)
    t('调度-日报列表', D3, 'GET', '/api/dispatch-center/daily-report/list', 200)
    t('调度-员工列表', D3, 'GET', '/api/dispatch-center/employee/list', 200)
    t('调度-物料列表', D3, 'GET', '/api/dispatch-center/material/list', 200)
    t('调度-生产看板', D3, 'GET', '/api/dispatch-center/dashboard/production', 200)
    t('调度-报工回调', D3, 'POST', '/api/dispatch-center/report-submitted', 200,
      json={'order_no': 'TEST-ORDER', 'process': '测试', 'quantity': 10})

    # ── 5008 移动端：任务/工单/报工 ─────────────────────
    section('5008 Mobile API — 任务/工单/报工')
    t('移动-健康', M8, 'GET', '/health', 200)
    t('移动-任务列表', M8, 'GET', '/api/tasks', 200)
    t('移动-工单列表', M8, 'GET', '/api/workorder/list', 200)
    t('移动-排产记录', M8, 'GET', '/api/schedule_record/list', 200)
    t('移动-报工记录', M8, 'GET', '/api/report_record/list', 200)
    t('移动-工序列表', M8, 'GET', '/api/process/list', 200)
    t('移动-员工列表', M8, 'GET', '/api/employee/list', 200)
    t('移动-物料列表', M8, 'GET', '/api/material/list', 200)
    t('移动-日报列表', M8, 'GET', '/api/daily-report/list', 200)
    t('移动-报工更新', M8, 'POST', '/api/report_record/update', 200,
      json={'record_id': 0, 'quantity': 10})

    # ── 8008 同步桥：任务同步/报工同步 ─────────────────
    section('8008 Sync Bridge — 任务同步/报工同步')
    t('同步-健康', S8, 'GET', '/health', 200)
    t('同步-同步状态', S8, 'GET', '/api/sync/status', 200)
    t('同步-报工(SAMPLE)', S8, 'POST', '/api/sync/report', 200,
      json={'order_no': f'DATA-{datetime.now().strftime("%m%d%H%M%S")}',
            'process': '测试工序', 'quantity': 5, 'operator': 'CI-TEST',
            'force': True})

    # ── 5001 桌面端：数据查看 ──────────────────────────
    section('5001 Desktop Web — 数据查看')
    t('桌面-健康', W1, 'GET', '/health', 200)
    t('桌面-工单列表', W1, 'GET', '/api/workorder/list', 200)
    t('桌面-员工列表', W1, 'GET', '/api/employee/list', 200)
    t('桌面-物料列表', W1, 'GET', '/api/material/list', 200)
    t('桌面-生产看板', W1, 'GET', '/api/dashboard/production', 200)

    # ── 数据一致性：同一数据多源查询 ───────────────────
    section('Data Consistency — 同一数据多源查询')
    r_d3 = t('一致性-工单:5003', D3, 'GET', '/api/dispatch-center/workorder/list', 200)
    r_m8 = t('一致性-工单:5008', M8, 'GET', '/api/workorder/list', 200)

    if r_d3 and r_m8:
        d3_count = len(r_d3.json().get('data', [])) if r_d3.json().get('code') == 0 else 0
        m8_count = len(r_m8.json().get('data', [])) if r_m8.json().get('code') == 0 else 0
        print(f'  数据一致性: 5003工单={d3_count}, 5008工单={m8_count}')

    r_d3sch = t('一致性-排产:5003', D3, 'GET', '/api/schedule/list', 200)
    r_m8sch = t('一致性-排产:5008', M8, 'GET', '/api/schedule_record/list', 200)

    if r_d3sch and r_m8sch:
        d3s_count = len(r_d3sch.json().get('data', [])) if r_d3sch.json().get('code') == 0 else 0
        m8s_count = len(r_m8sch.json().get('data', [])) if r_m8sch.json().get('code') == 0 else 0
        print(f'  数据一致性: 5003排产={d3s_count}, 5008排产={m8s_count}')

    # ── 汇总 ──────────────────────────────────────────────
    print(f'\n{"=" * 60}')
    total = len(TESTS)
    passed = sum(1 for _, _, _, ok in TESTS if ok)
    failed = total - passed
    print(f'总计: {total} 项 | ✅ {passed} | ❌ {failed}')
    if failed > 0:
        print(f'\n失败项:')
        for label, got, expected in FAILED:
            print(f'  {label}: got={got}, expected={expected}')
    print(f'{"=" * 60}')

    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
