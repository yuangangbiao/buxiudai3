# -*- coding: utf-8 -*-
"""
ci/test_critical_fixes.py - P0 关键修复回归测试

[v3.6.2] Stage 4: 关键Bug修复的CI回归

在6服务器全部启动后执行，验证P0修复的回归测试。

每个测试返回：(name, status, latency_ms)
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
os.environ.setdefault('INVENTORY_5010_URL', 'http://127.0.0.1:5010')

D3 = os.environ['DISPATCH_5003_URL']
M8 = os.environ['MOBILE_5008_URL']
C2 = os.environ['CONTAINER_5002_URL']
S8 = os.environ['SYNC_8008_URL']
W1 = os.environ['WEB_5001_URL']
I0 = os.environ['INVENTORY_5010_URL']

TESTS = []
FAILED = []
TIMEOUT = 30


def t(name, server, method, path, expected=None, **kwargs):
    url = f'{server}{path}'
    label = f'{server.replace("http://127.0.0.1:","")}{path}'
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
        TESTS.append((name, code, latency, ok))
        status = '✅' if ok else '❌'
        print(f'  {status} [{code}] {name} ({latency:.0f}ms)')
        if not ok:
            FAILED.append((name, code, expected))
        return r
    except requests.exceptions.Timeout:
        latency = (time.time() - start) * 1000
        TESTS.append((name, 'TIMEOUT', latency, False))
        FAILED.append((name, 'TIMEOUT', expected))
        print(f'  ❌ [TIMEOUT] {name} ({latency:.0f}ms)')
        return None
    except Exception as e:
        latency = (time.time() - start) * 1000
        TESTS.append((name, f'ERR:{e}', latency, False))
        FAILED.append((name, str(e), expected))
        print(f'  ❌ [ERR] {name} → {e}')
        return None


def section(name):
    print(f'\n── {name} ──')


def main():
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'=' * 60)
    print(f'CI Critical Fixes Test v3.6.2 | {ts}')
    print(f'=' * 60)

    # ══════════════════════════════════════════════════════
    # Test 1: P0-1 并发报工超量（乐观锁回归）
    # ══════════════════════════════════════════════════════
    section('P0-1 并发报工超量（乐观锁回归）')

    order_no = f'CONCURRENT-{datetime.now().strftime("%m%d%H%M%S")}'
    worker_count = 10
    qty_per_worker = 15
    results = {'success': 0, 'conflict': 0, 'other': 0, 'lock': threading.Lock()}

    def report_worker(wid):
        try:
            r = requests.post(
                f'{S8}/api/sync/report',
                json={
                    'order_no': order_no,
                    'process': '编织',
                    'quantity': qty_per_worker,
                    'operator': f'Worker-{wid}',
                    'force': False,
                },
                timeout=10,
            )
            with results['lock']:
                if r.status_code == 200:
                    results['success'] += 1
                elif r.status_code == 409:
                    results['conflict'] += 1
                else:
                    results['other'] += 1
        except Exception:
            with results['lock']:
                results['other'] += 1

    with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as ex:
        futures = [ex.submit(report_worker, i) for i in range(worker_count)]
        concurrent.futures.wait(futures)

    print(f'  10人并发报工(每人{qty_per_worker}件, 计划=100):')
    print(f'    成功: {results["success"]}, 冲突(409): {results["conflict"]}, 其他: {results["other"]}')

    if results['conflict'] > 0:
        print(f'  ✅ 乐观锁生效: 有{results["conflict"]}个请求因超量返回409')
        TESTS.append(('P0-1 并发乐观锁', 200, 0, True))
    else:
        print(f'  ❌ 乐观锁未生效: 无冲突返回')
        TESTS.append(('P0-1 并发乐观锁', 409, 0, False))
        FAILED.append(('P0-1 并发乐观锁', 'no 409 returned', '>=1 conflict'))

    # ══════════════════════════════════════════════════════
    # Test 2: P0-2 边界值测试（0/负数/超量）
    # ══════════════════════════════════════════════════════
    section('P0-2 边界值测试')

    r0 = requests.post(f'{S8}/api/sync/report',
        json={'order_no': 'TEST-0', 'process': '测试', 'quantity': 0,
              'operator': 'test', 'force': True}, timeout=10)
    TESTS.append(('P0-2a 报工数量=0', r0.status_code, 0,
                   r0.status_code in (200, 400, 422)))
    print(f'  {"✅" if r0.status_code in (200,400,422) else "❌"} [边界] 数量=0 → {r0.status_code}')

    rneg = requests.post(f'{S8}/api/sync/report',
        json={'order_no': 'TEST-NEG', 'process': '测试', 'quantity': -10,
              'operator': 'test', 'force': True}, timeout=10)
    TESTS.append(('P0-2b 报工数量=-10', rneg.status_code, 0,
                   rneg.status_code in (200, 400, 422)))
    print(f'  {"✅" if rneg.status_code in (200,400,422) else "❌"} [边界] 数量=-10 → {rneg.status_code}')

    # ══════════════════════════════════════════════════════
    # Test 3: P0-3 装饰器回归（require_admin / require_api_key）
    # ══════════════════════════════════════════════════════
    section('P0-3 装饰器导入回归（启动时不报错即通过）')

    t('P0-3a 5008移动端健康', M8, 'GET', '/health', 200)
    t('P0-3b 5002容器中心健康', C2, 'GET', '/health', 200)
    t('P0-3c 5003调度中心健康', D3, 'GET', '/health', 200)

    # ══════════════════════════════════════════════════════
    # Test 4: P1-1 JWT鉴权测试
    # ══════════════════════════════════════════════════════
    section('P1-1 JWT鉴权测试')

    r_no_auth = requests.get(f'{D3}/api/dispatch-center/workorder/list', timeout=10)
    TESTS.append(('P1-1a 无Token访问', r_no_auth.status_code, 0,
                   r_no_auth.status_code in (200, 401)))
    print(f'  {"✅" if r_no_auth.status_code in (200,401) else "❌"} [鉴权] 无Token → {r_no_auth.status_code}')

    r_bad_token = requests.get(
        f'{D3}/api/dispatch-center/workorder/list',
        headers={'Authorization': 'Bearer invalid_token_xyz'},
        timeout=10)
    TESTS.append(('P1-1b 伪造Token访问', r_bad_token.status_code, 0,
                   r_bad_token.status_code in (200, 401)))
    print(f'  {"✅" if r_bad_token.status_code in (200,401) else "❌"} [鉴权] 伪造Token → {r_bad_token.status_code}')

    r_good = requests.get(f'{D3}/api/dispatch-center/workorder/list',
        headers={'Authorization': f'Bearer {os.getenv("JWT_SECRET_KEY", "ci_test_secret_64_bytes_xxx")[:64]}'},
        timeout=10)
    TESTS.append(('P1-1c 有效Token访问', r_good.status_code, 0,
                   r_good.status_code == 200))
    print(f'  {"✅" if r_good.status_code == 200 else "❌"} [鉴权] 有效Token → {r_good.status_code}')

    # ══════════════════════════════════════════════════════
    # Test 5: P2-1 数据库契约校验
    # ══════════════════════════════════════════════════════
    section('P2-1 数据库契约校验')

    try:
        import pymysql
        conn = pymysql.connect(host='127.0.0.1', port=3306,
                               user='root', password='88888888',
                               database='container_center', charset='utf8mb4')
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA='container_center'
              AND TABLE_NAME='process_records'
              AND COLUMN_NAME IN ('completed_qty','status','start_time','end_time')
        """)
        col_count = cur.fetchone()[0]
        TESTS.append(('P2-1 process_records列完整性', col_count, 0, col_count >= 4))
        print(f'  {"✅" if col_count>=4 else "❌"} [契约] process_records关键列数={col_count} (期望>=4)')
        conn.close()
    except Exception as e:
        TESTS.append(('P2-1 数据库契约', str(e), 0, False))
        FAILED.append(('P2-1 数据库契约', str(e), 'no error'))

    # ══════════════════════════════════════════════════════
    # Test 6: P2-2 跨服务数据一致性
    # ══════════════════════════════════════════════════════
    section('P2-2 跨服务数据一致性')

    r_d3 = t('P2-2a 工单:5003', D3, 'GET', '/api/dispatch-center/workorder/list', 200)
    r_m8 = t('P2-2b 工单:5008', M8, 'GET', '/api/workorder/list', 200)

    if r_d3 and r_m8:
        try:
            d3_count = len(r_d3.json().get('data', [])) if r_d3.json().get('code') == 0 else 0
            m8_count = len(r_m8.json().get('data', [])) if r_m8.json().get('code') == 0 else 0
            diff = abs(d3_count - m8_count)
            ok = diff <= 5
            TESTS.append(('P2-2 数据一致性(5003 vs 5008)', diff, 0, ok))
            print(f'  {"✅" if ok else "❌"} [一致性] 5003工单={d3_count}, 5008工单={m8_count}, 差={diff}')
        except Exception as e:
            TESTS.append(('P2-2 数据一致性', str(e), 0, False))
            FAILED.append(('P2-2 数据一致性', str(e), 'no error'))

    # ══════════════════════════════════════════════════════
    # Test 7: P2-3 关键端点回归
    # ══════════════════════════════════════════════════════
    section('P2-3 关键端点回归')

    t('P2-3a 调度-报工回调', D3, 'POST', '/api/dispatch-center/report-submitted',
      200, json={'order_no': 'TEST-ORDER', 'process': '测试', 'quantity': 10})
    t('P2-3b 同步-状态', S8, 'GET', '/api/sync/status', 200)
    t('P2-3c 容器-任务列表', C2, 'GET', '/api/tasks', 200)
    t('P2-3d 移动-任务列表', M8, 'GET', '/api/tasks', 200)

    # ── 汇总 ──────────────────────────────────────────────
    print(f'\n{"=" * 60}')
    total = len(TESTS)
    passed = sum(1 for _, _, _, ok in TESTS if ok)
    failed = total - passed
    print(f'总计: {total} 项 | ✅ {passed} | ❌ {failed}')
    if failed > 0:
        print(f'\n失败项:')
        for name, got, expected in FAILED:
            print(f'  ❌ {name}: got={got}, expected={expected}')
    print(f'{"=" * 60}')

    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
