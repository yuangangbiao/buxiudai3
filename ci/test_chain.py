# -*- coding: utf-8 -*-
"""
ci/test_chain.py - 6服务器串联集成测试

[v3.6.2] Stage 3: 跨服务全链路验证

在 6 个服务全部启动后执行，验证服务间通信正常。

服务端口约定:
  5001 - desktop_web
  5002 - container_center_api
  5003 - standalone_dispatch_server
  5008 - mobile_api_ai/app
  5010 - inventory_api_server
  8008 - sync_bridge_server

每个测试返回:
  (server, endpoint, status_code, latency_ms)
"""
import os
import sys
import time
import requests
from datetime import datetime

os.environ.setdefault('DISPATCH_5003_URL', 'http://127.0.0.1:5003')
os.environ.setdefault('WEB_5001_URL', 'http://127.0.0.1:5001')
os.environ.setdefault('MOBILE_5008_URL', 'http://127.0.0.1:5008')
os.environ.setdefault('CONTAINER_5002_URL', 'http://127.0.0.1:5002')
os.environ.setdefault('INVENTORY_5010_URL', 'http://127.0.0.1:5010')
os.environ.setdefault('SYNC_8008_URL', 'http://127.0.0.1:8008')

D3 = os.environ['DISPATCH_5003_URL']
W1 = os.environ['WEB_5001_URL']
M8 = os.environ['MOBILE_5008_URL']
C2 = os.environ['CONTAINER_5002_URL']
I0 = os.environ['INVENTORY_5010_URL']
S8 = os.environ['SYNC_8008_URL']

TESTS = []
FAILED = []
TIMEOUT = 30


def t(name, server, method, path, expected=None, **kwargs):
    """执行单个 API 测试"""
    url = f'{server}{path}'
    label = f'{server.replace("http://127.0.0.1:","")}{path}'
    start = time.time()
    try:
        if method.upper() == 'GET':
            r = requests.get(url, timeout=TIMEOUT, **kwargs)
        elif method.upper() == 'POST':
            r = requests.post(url, timeout=TIMEOUT, **kwargs)
        elif method.upper() == 'PUT':
            r = requests.put(url, timeout=TIMEOUT, **kwargs)
        else:
            r = requests.delete(url, timeout=TIMEOUT, **kwargs)
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
    print(f'CI Chain Test v3.6.2 | {ts}')
    print(f'=' * 60)

    # ── 5003 调度中心 ───────────────────────────────────────
    section('5003 Dispatch Center (调度中心)')
    t('调度-健康', D3, 'GET', '/health', 200)
    t('调度-排产列表', D3, 'GET', '/api/schedule/list', 200)
    t('调度-工单列表', D3, 'GET', '/api/dispatch-center/workorder/list', 200)
    t('调度-工序列表', D3, 'GET', '/api/dispatch-center/process/list', 200)
    t('调度-质检列表', D3, 'GET', '/api/dispatch-center/quality/list', 200)
    t('调度-发货列表', D3, 'GET', '/api/dispatch-center/shipment/list', 200)
    t('调度-日报列表', D3, 'GET', '/api/dispatch-center/daily-report/list', 200)
    t('调度-员工列表', D3, 'GET', '/api/dispatch-center/employee/list', 200)
    t('调度-物料列表', D3, 'GET', '/api/dispatch-center/material/list', 200)
    t('调度-生产看板', D3, 'GET', '/api/dispatch-center/dashboard/production', 200)

    # ── 5008 移动端 ────────────────────────────────────────
    section('5008 Mobile API (报工/质检/发货)')
    t('移动-健康', M8, 'GET', '/health', 200)
    t('移动-工单列表', M8, 'GET', '/api/workorder/list', 200)
    t('移动-排产列表', M8, 'GET', '/api/schedule/list', 200)
    t('移动-日报列表', M8, 'GET', '/api/daily-report/list', 200)
    t('移动-工序列表', M8, 'GET', '/api/process/list', 200)

    # ── 5001 桌面端 ────────────────────────────────────────
    section('5001 Desktop Web (桌面端)')
    t('桌面-健康', W1, 'GET', '/health', 200)
    t('桌面-工单列表', W1, 'GET', '/api/workorder/list', 200)
    t('桌面-员工列表', W1, 'GET', '/api/employee/list', 200)
    t('桌面-物料列表', W1, 'GET', '/api/material/list', 200)
    t('桌面-生产看板', W1, 'GET', '/api/dashboard/production', 200)

    # ── 5002 容器中心 ─────────────────────────────────────
    section('5002 Container Center API (指令处理)')
    t('容器-健康', C2, 'GET', '/health', 200)
    t('容器-工单列表', C2, 'GET', '/api/workorder/list', 200)
    t('容器-员工列表', C2, 'GET', '/api/employee/list', 200)

    # ── 5010 库存管理 ─────────────────────────────────────
    section('5010 Inventory API (库存管理)')
    t('库存-健康', I0, 'GET', '/health', 200)
    t('库存-物料列表', I0, 'GET', '/inventory/api/material/list', 200)
    t('库存-库存列表', I0, 'GET', '/inventory/api/stock/list', 200)
    t('库存-预警列表', I0, 'GET', '/inventory/api/alert/list', 200)

    # ── 8008 同步桥 ──────────────────────────────────────
    section('8008 Sync Bridge (服务间同步)')
    t('同步-健康', S8, 'GET', '/health', 200)
    t('同步-状态', S8, 'GET', '/api/sync/status', 200)

    # ── 跨服务链路: 5003→5008 ─────────────────────────────
    section('Cross-Service Chain: 5003 ↔ 5008')
    t('跨服务-5003→5008排产', D3, 'GET', '/api/schedule/list', 200)
    t('跨服务-5008→5003报工', M8, 'GET', '/api/workreport/list', 200)
    t('跨服务-质检联动', M8, 'GET', '/api/quality/list', 200)
    t('跨服务-发货联动', M8, 'GET', '/api/shipment/list', 200)

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
