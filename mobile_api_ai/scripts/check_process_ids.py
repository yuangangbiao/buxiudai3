# -*- coding: utf-8 -*-
"""查询容器中心 SQLite 数据库中的所有任务"""
import os
import sqlite3
import json

DB_PATH = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'
OUTPUT_PATH = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\scripts\_process_ids_output.txt'

def main():
    result = []

    if not os.path.exists(DB_PATH):
        result.append(f"数据库不存在: {DB_PATH}")
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            f.write('\n'.join(result))
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    result.append("=" * 80)
    result.append("process_records 表 (工序主记录)")
    result.append("=" * 80)

    cur.execute("""
        SELECT id, order_no, work_order_no, product_name, quantity, unit,
               status, current_step, created_at, updated_at
        FROM process_records
        ORDER BY created_at DESC
        LIMIT 50
    """)
    rows = cur.fetchall()
    if rows:
        result.append(f"{'ID':<12} {'order_no':<20} {'work_order_no':<20} {'产品':<15} {'数量':<8} {'状态':<10}")
        result.append("-" * 90)
        for r in rows:
            product = (r['product_name'] or '')[:14]
            result.append(f"{r['id']:<12} {(r['order_no'] or ''):<20} {(r['work_order_no'] or ''):<20} {product:<15} {r['quantity']:<8} {r['status']:<10}")
        result.append(f"\n共 {len(rows)} 条记录")
    else:
        result.append("无记录")

    result.append("\n" + "=" * 80)
    result.append("process_sub_steps 表 (报工明细)")
    result.append("=" * 80)

    cur.execute("""
        SELECT id, process_id, order_no, step_name, batch_no, quantity,
               operator, created_at
        FROM process_sub_steps
        ORDER BY created_at DESC
        LIMIT 50
    """)
    rows = cur.fetchall()
    if rows:
        result.append(f"{'ID':<38} {'process_id':<12} {'order_no':<20} {'工序':<15} {'数量':<8} {'操作员':<10}")
        result.append("-" * 110)
        for r in rows:
            step = (r['step_name'] or '')[:14]
            result.append(f"{r['id']:<38} {r['process_id']:<12} {(r['order_no'] or ''):<20} {step:<15} {r['quantity']:<8} {r['operator']:<10}")
        result.append(f"\n共 {len(rows)} 条记录")
    else:
        result.append("无记录")

    result.append("\n" + "=" * 80)
    result.append("process_id 匹配检查")
    result.append("=" * 80)

    cur.execute("SELECT DISTINCT process_id FROM process_sub_steps")
    sub_process_ids = set(r['process_id'] for r in cur.fetchall())

    cur.execute("SELECT DISTINCT id FROM process_records")
    main_ids = set(r['id'] for r in cur.fetchall())

    orphan_ids = sub_process_ids - main_ids
    if orphan_ids:
        result.append("以下 process_id 在报工表中存在，但在工序主表中找不到:")
        for pid in orphan_ids:
            result.append(f"  - {pid}")
    else:
        result.append("所有 process_id 都匹配正常")

    conn.close()

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(result))

if __name__ == '__main__':
    main()
