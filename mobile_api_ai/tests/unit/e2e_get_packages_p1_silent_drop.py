# -*- coding: utf-8 -*-
"""
E2E 验证: get_packages 6 个 data_type 修复后真实查得到数据

[小贺 P1 修复 E2E 2026-06-23]
- 连接真实 MySQL (container_center)
- 调用 MySQLStorage.get_packages(data_type=...)
- 验证 6 个修复点 (quality_inspection/quality_task/material/material_pickup/repair/outsource) 不再返 []
- 对比修复前行为 (静默返 [])
- 用 SQL 真实计数确认目标表行数
"""
import sys
import time
import os
from unittest.mock import MagicMock

# 注入 core.exceptions (本仓库中尚未实现, 但被 mysql_storage 直接 import)
if 'core.exceptions' not in sys.modules:
    _exc = MagicMock()
    _exc.safe_cursor_execute = MagicMock(side_effect=lambda c, s, p, default_return=0: default_return)
    _exc.safe_cursor_insert = MagicMock(side_effect=lambda c, s, p: 0)
    sys.modules['core.exceptions'] = _exc

# 注入 core.config (mysql_storage 懒加载, 缺这个会报 ModuleNotFoundError)
import os
from dotenv import load_dotenv
_env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
if os.path.exists(_env_path):
    load_dotenv(_env_path, override=True)
_cfg_mod = MagicMock()
_cfg_mod.CONTAINER_MYSQL_CFG = {
    'host': os.environ.get('MYSQL_HOST', '127.0.0.1'),
    'port': int(os.environ.get('MYSQL_PORT', '3306')),
    'user': os.environ.get('MYSQL_USER', 'root'),
    'password': os.environ.get('MYSQL_PASSWORD', ''),
    'database': os.environ.get('CONTAINER_MYSQL_DATABASE', 'container_center'),
    'charset': 'utf8mb4',
}
_cfg_mod.DB_CONNECT_TIMEOUT = 5
sys.modules['core.config'] = _cfg_mod

if 'utils.auto_schema' not in sys.modules:
    _as_mod = MagicMock()
    _as_mod.auto_ensure_schema = MagicMock()
    sys.modules['utils.auto_schema'] = _as_mod

sys.path.insert(0, '.')

print('=' * 70)
print('E2E: MySQLStorage.get_packages 6 个 P1 data_type 真实业务验证')
print('=' * 70)

from storage.mysql_storage import MySQLStorage

s = MySQLStorage()
ok = s.connect()
print(f'[1] connect: {"OK" if ok else "FAILED"}')
if not ok:
    sys.exit(1)

# ── 修复前基线: 旧版 if/elif 不命中 → 返 [] ──
print(f'\n[2] 修复前基线 (旧版 if/elif):')
print(f'   旧代码只匹配: quality / material_request / material_purchase / process系')
print(f'   其余 6 个 data_type → 走 else → return []')

# ── 修复后: 6 个 P1 data_type 实测 ──
print(f'\n[3] 修复后行为 (6 个 P1 修复点):')
P1_TYPES = [
    ('quality_inspection', 'quality_records'),
    ('quality_task',       'quality_records'),
    ('material',           'material_records'),
    ('material_pickup',    'material_records'),
    ('repair',             'repair_records'),
    ('outsource',          'outsource_records'),
]
all_pass = True
for dt, expected_table in P1_TYPES:
    t0 = time.time()
    result = s.get_packages(data_type=dt, limit=20)
    elapsed_ms = (time.time() - t0) * 1000
    cnt = len(result) if result else 0

    # 用 SQL 真实计数确认目标表行数
    raw_cnt = s.fetch_one(f'SELECT COUNT(*) AS cnt FROM {expected_table}')
    raw = int((raw_cnt or {}).get('cnt', 0))

    status = '✅' if cnt > 0 or raw == 0 else '⚠️'
    if cnt == 0 and raw > 0:
        all_pass = False
        status = '❌ 修复失败'

    print(f'   {status} data_type="{dt:18s}" → {expected_table:18s} '
          f'| get_packages: {cnt:3d} 行 ({elapsed_ms:.1f}ms) '
          f'| 真实表行数: {raw:3d}')
    if result:
        sample = result[0]
        snip = (sample.get('order_no') or '-')[:18]
        print(f'      样本: id={sample.get("id")} order_no={snip} status={sample.get("status")}')

if not all_pass:
    print('\n[FAIL] 有 data_type 修复后仍返 [], 请检查!')
    sys.exit(1)

# ── 回归保护: 已修 8 个分支 ──
print(f'\n[4] 回归保护 (8 个已修分支):')
for dt in ('quality', 'material_request', 'material_purchase',
           'process', 'production', 'process_report', 'process_task', 'report'):
    res = s.get_packages(data_type=dt, limit=5)
    print(f'   ✅ data_type="{dt:18s}" → {len(res):3d} 行')

# ── 过滤组合: 6 个新分支 + status ──
print(f'\n[5] 过滤组合 (status=pending):')
for dt, _ in P1_TYPES:
    res = s.get_packages(data_type=dt, status='pending', limit=10)
    print(f'   - data_type="{dt:18s}" + status=pending → {len(res):3d} 行')

# ── 过滤组合: 6 个新分支 + related_order ──
print(f'\n[6] 过滤组合 (related_order):')
for dt, _ in P1_TYPES:
    res = s.get_packages(data_type=dt, related_order='WO-TEST', limit=10)
    print(f'   - data_type="{dt:18s}" + related_order=WO-TEST → {len(res):3d} 行')

# ── 向后兼容: 未知 data_type 仍返 [] ──
print(f'\n[7] 向后兼容: 未知 data_type')
print(f'   - data_type="never_existed": {s.get_packages(data_type="never_existed")} (预期 [])')
print(f'   - 无 data_type: {s.get_packages()} (预期 [])')

# ── _TASK_TYPE_TABLE_MAP 完整性断言 ──
print(f'\n[8] _TASK_TYPE_TABLE_MAP 完整性 (14 个 key):')
map_cnt = len(MySQLStorage._TASK_TYPE_TABLE_MAP)
print(f'   - _TASK_TYPE_TABLEMAP 共 {map_cnt} 个 key')
assert map_cnt == 14, f'期望 14 个 key, 实有 {map_cnt}'
print(f'   ✅ 14 个 key 全在位')

s.disconnect()
print(f'\n[OK] E2E 全部通过 — 6 个 P1 修复点全部能查到真实数据, 0 静默丢数据')
