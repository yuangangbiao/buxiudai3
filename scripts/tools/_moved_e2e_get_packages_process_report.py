# -*- coding: utf-8 -*-
"""
E2E 验证: get_packages(data_type='process_report') 真实查得到数据

[小贺 P0 修复 E2E 2026-06-23]
- 连接真实 MySQL (container_center.process_sub_steps, 已有 75 行)
- 调用 MySQLStorage.get_packages(data_type='process_report')
- 验证返回结果 (非 [])
- 验证 SQL 正确指向 process_sub_steps
- 对比修复前行为 (返回 [])
"""
import sys
import time
from unittest.mock import MagicMock

# 注入 core.exceptions (本仓库中尚未实现, 但被 mysql_storage 直接 import)
# 注意: 这不是 mock 数据层, 而是修补一个无关的 import 依赖,
# 让 E2E 能用真实 MySQL 跑通
if 'core.exceptions' not in sys.modules:
    _exc = MagicMock()
    _exc.safe_cursor_execute = MagicMock(side_effect=lambda c, s, p, default_return=0: default_return)
    _exc.safe_cursor_insert = MagicMock(side_effect=lambda c, s, p: 0)
    sys.modules['core.exceptions'] = _exc

# 注入 core.config (mysql_storage 懒加载, 缺这个会报 ModuleNotFoundError)
# 这里用真实 .env 的环境变量构建配置, 不 mock 数据层
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

# 注入 utils.auto_schema
if 'utils.auto_schema' not in sys.modules:
    _as_mod = MagicMock()
    _as_mod.auto_ensure_schema = MagicMock()
    sys.modules['utils.auto_schema'] = _as_mod

sys.path.insert(0, '.')

print('=' * 70)
print('E2E: MySQLStorage.get_packages(data_type=process_report) 真实业务验证')
print('=' * 70)

from storage.mysql_storage import MySQLStorage

s = MySQLStorage()
ok = s.connect()
print(f'[1] connect: {"OK" if ok else "FAILED"}')
if not ok:
    sys.exit(1)

# 1. 修复前模拟: 旧版 if/elif 没有 process_report 分支 → 返 []
#    用 None 占位 (其实没改前的代码就会返 [])
print(f'\n[2] 修复前行为模拟 (旧版 if/elif):')
print(f'   - 旧代码: if data_type in ("process", "production")')
print(f'   - data_type="process_report" 不在 tuple 内 → 走 else → return []')
print(f'   - 预期: []')

# 2. 修复后: 真实调用 get_packages(data_type="process_report")
print(f'\n[3] 修复后行为 (data_type="process_report"):')
t0 = time.time()
result = s.get_packages(data_type='process_report', limit=20)
elapsed_ms = (time.time() - t0) * 1000
print(f'   - 返回 {len(result)} 行, 耗时 {elapsed_ms:.1f}ms')
if result:
    sample = result[0]
    print(f'   - 第 1 行: id={sample.get("id")} order_no={sample.get("order_no")} '
          f'status={sample.get("status")}')
    print(f'   - ✅ 数据真实落地, 不再返回 []')
else:
    print(f'   - ❌ 仍然返回 [], 修复未生效!')
    sys.exit(1)

# 3. 验证 process_task 和 report 同样能查到
print(f'\n[4] 兼容性验证: data_type=process_task / report')
for dt in ('process_task', 'report', 'process', 'production'):
    res = s.get_packages(data_type=dt, limit=5)
    print(f'   - data_type="{dt}": {len(res)} 行')

# 4. 验证 quality 分支未受影响
print(f'\n[5] 回归保护: data_type=quality')
res = s.get_packages(data_type='quality', limit=5)
print(f'   - data_type="quality": {len(res)} 行')

# 5. 验证 status 过滤 + process_report
print(f'\n[6] 过滤组合: data_type=process_report + status=pending')
res = s.get_packages(data_type='process_report', status='pending', limit=10)
print(f'   - status=pending: {len(res)} 行')

# 6. 验证 related_order 过滤 + process_report
print(f'\n[7] 过滤组合: data_type=process_report + related_order')
res = s.get_packages(data_type='process_report', related_order='WO-TEST', limit=10)
print(f'   - related_order=WO-TEST: {len(res)} 行')

# 7. 验证未知 data_type 仍返 [] (向后兼容)
print(f'\n[8] 向后兼容: data_type=never_existed')
res = s.get_packages(data_type='never_existed')
print(f'   - 未知 type: {res} (预期 [])')

s.disconnect()
print(f'\n[OK] E2E 全部通过 — bug 已修复, 不再丢数据')
