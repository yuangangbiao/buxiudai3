# -*- coding: utf-8 -*-
"""
T1: 历史数据回填脚本 - 将 data_packages.completed_qty 回填到 process_sub_steps

执行时间: 2026-06-20
执行顺序: T1 (T0 之后执行)

回填逻辑:
从 data_packages 中按 order_no + step_name 汇总 completed_qty，
然后更新到 process_sub_steps 表。

回滚:
UPDATE process_sub_steps SET completed_qty = 0 WHERE completed_qty > 0;
"""
import os
import sys

PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJ_ROOT not in sys.path:
    sys.path.insert(0, PROJ_ROOT)

from mobile_api_ai.storage.mysql_storage import MySQLStorage


def backfill():
    """回填 process_sub_steps.completed_qty"""
    storage = MySQLStorage()

    print("[T1] 开始回填 process_sub_steps.completed_qty...")

    print("[T1.1] 检查待回填数据...")
    preview = storage.fetch_all("""
        SELECT ps.order_no, ps.step_name, ps.completed_qty as old_qty,
               COALESCE(dp.total_qty, 0) as new_qty
        FROM process_sub_steps ps
        LEFT JOIN (
            SELECT related_order, related_process,
                   SUM(COALESCE(completed_qty, 0)) as total_qty
            FROM data_packages
            WHERE data_type = 'process_task'
              AND related_order IS NOT NULL
              AND related_process IS NOT NULL
            GROUP BY related_order, related_process
        ) dp ON ps.order_no = dp.related_order
            AND ps.step_name = dp.related_process
        WHERE dp.total_qty IS NOT NULL
          AND dp.total_qty > 0
        LIMIT 10
    """)
    print(f"[T1.1] 预览前 10 条待回填数据:")
    for row in preview:
        print(f"       order={row['order_no']}, step={row['step_name']}, old={row['old_qty']}, new={row['new_qty']}")

    print("[T1.2] 执行回填...")
    affected = storage.execute("""
        UPDATE process_sub_steps ps
        INNER JOIN (
            SELECT related_order, related_process,
                   SUM(COALESCE(completed_qty, 0)) as total_qty
            FROM data_packages
            WHERE data_type = 'process_task'
              AND related_order IS NOT NULL
              AND related_process IS NOT NULL
            GROUP BY related_order, related_process
        ) dp ON ps.order_no = dp.related_order
            AND ps.step_name = dp.related_process
        SET ps.completed_qty = dp.total_qty
    """)
    print(f"[T1.2] ✅ 回填完成，影响 {affected} 行")

    print("[T1.3] 验证回填结果...")
    total = storage.fetch_one("SELECT SUM(COALESCE(completed_qty, 0)) as total FROM process_sub_steps")
    print(f"[T1.3] process_sub_steps.completed_qty 总和: {total['total'] if total else 0}")

    print("[T1] ✅ 历史数据回填完成")


def rollback():
    """回滚回填"""
    storage = MySQLStorage()

    print("[T1 回滚] 重置 process_sub_steps.completed_qty 为 0...")
    affected = storage.execute("""
        UPDATE process_sub_steps SET completed_qty = 0 WHERE completed_qty > 0
    """)
    print(f"[T1 回滚] ✅ 重置完成，影响 {affected} 行")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--rollback', action='store_true', help='回滚回填')
    args = parser.parse_args()

    if args.rollback:
        rollback()
    else:
        backfill()
