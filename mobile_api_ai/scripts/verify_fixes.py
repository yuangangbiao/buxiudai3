"""验证容器中心服务器修复效果"""
import urllib.request
import json
import sys

BASE = 'http://127.0.0.1:5002'
passed = 0
failed = 0

def test(name, url, expect_code=0, expect_http=200):
    global passed, failed
    try:
        r = urllib.request.urlopen(url, timeout=5)
        d = json.loads(r.read())
        http_ok = r.status == expect_http
        code_ok = d.get('code') == expect_code if expect_code is not None else True
        status = 'PASS' if (http_ok and code_ok) else 'FAIL'
        if status == 'PASS':
            passed += 1
        else:
            failed += 1
        print(f'  [{status}] {name}: HTTP {r.status}, code={d.get("code")}')
        if status == 'FAIL':
            print(f'          response: {json.dumps(d, ensure_ascii=False)[:200]}')
    except urllib.error.HTTPError as e:
        d = json.loads(e.read())
        http_ok = e.code == expect_http
        code_ok = d.get('code') == expect_code if expect_code is not None else True
        status = 'PASS' if (http_ok and code_ok) else 'FAIL'
        if status == 'PASS':
            passed += 1
        else:
            failed += 1
        print(f'  [{status}] {name}: HTTP {e.code}, code={d.get("code")}')
        if status == 'FAIL':
            print(f'          response: {json.dumps(d, ensure_ascii=False)[:200]}')
    except Exception as e:
        failed += 1
        print(f'  [FAIL] {name}: {e}')

print('=' * 60)
print('  容器中心服务器修复验证')
print('=' * 60)

# 1. 健康检查
print('\n[1/5] 基础功能验证')
test('健康检查', f'{BASE}/api/health')
test('不存在的路由(404处理器)', f'{BASE}/api/nonexistent_route', expect_code=404, expect_http=404)

# 2. 外协记录 (P2-3: 直查数据库)
print('\n[2/5] 外协管理 (P2-3: 直查+缓存)')
test('外协记录列表', f'{BASE}/api/outsource/records')

# 3. 日志文件存在
import os
log_file = os.path.join(os.path.dirname(__file__), '..', 'logs', 'container_center.log')
print(f'\n[3/5] 日志验证')
if os.path.exists(log_file):
    size = os.path.getsize(log_file)
    print(f'  [PASS] 日志文件存在: {log_file} ({size} bytes)')
    passed += 1
else:
    print(f'  [FAIL] 日志文件不存在: {log_file}')
    failed += 1

# 4. WAL模式验证
import sqlite3
db_path = os.path.join(os.path.dirname(__file__), '..', 'wechat_container.db')
print(f'\n[4/5] SQLite验证')
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('PRAGMA journal_mode')
    mode = cursor.fetchone()[0]
    if mode == 'wal':
        print(f'  [PASS] WAL模式: {mode}')
        passed += 1
    else:
        print(f'  [WARN] journal_mode: {mode} (预期 wal)')
        failed += 1
    cursor.execute('PRAGMA busy_timeout')
    timeout = cursor.fetchone()[0]
    print(f'  [INFO] busy_timeout: {timeout}ms')
    conn.close()
except Exception as e:
    print(f'  [FAIL] 数据库连接失败: {e}')
    failed += 1

# 5. 索引验证
print(f'\n[5/5] 索引验证')
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='data_packages'")
    indexes = [row[0] for row in cursor.fetchall()]
    expected = ['idx_pkg_type', 'idx_pkg_status', 'idx_pkg_operator', 'idx_pkg_created', 'idx_pkg_order']
    for idx in expected:
        if idx in indexes:
            print(f'  [PASS] 索引存在: {idx}')
            passed += 1
        else:
            print(f'  [FAIL] 索引缺失: {idx}')
            failed += 1
    conn.close()
except Exception as e:
    print(f'  [FAIL] 索引查询失败: {e}')
    failed += 1

print(f'\n{"=" * 60}')
print(f'  结果: {passed} passed, {failed} failed / {passed + failed} total')
print(f'{"=" * 60}')
sys.exit(0 if failed == 0 else 1)
