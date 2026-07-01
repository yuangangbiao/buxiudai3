# -*- coding: utf-8 -*-
"""
[F16 T16.2 修复] schedule_records 表已于 F6 P9 2026-06-10 被 DROP
        (跨库历史表清理, 详见 .workbuddy/memory/MEMORY.md L20)

本脚本已废弃, 不再执行 SQL 查询。

替代方案:
  - 排产数据已迁移到 process_records + dispatch_cache
  - 实时聚合: dispatch_center._core._get_process_names_set() → 走 process_departments.keys()
  - 历史排产数据查询: 使用 process_records 表 (容器中心 MySQL)
  - 命令行查询: 改用 sql/queries/schedule_overview.sql (即将提供) 或
    python -c "from mobile_api_ai.storage.mysql_storage import MySQLStorage; \
               s=MySQLStorage(); s.connect(); print(s.fetch_all('SELECT * FROM process_records ORDER BY created_at DESC LIMIT 5'))"

如确需保留此脚本, 请改写为查询 process_records (按 order_no + status 过滤)。
"""
import sys

print("=" * 60)
print("[F16 T16.2 废弃] schedule_records 表已 F6 P9 DROP")
print("=" * 60)
print(__doc__)
print("=" * 60)
sys.exit(0)
