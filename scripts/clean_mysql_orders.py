"""
K22 业务表脏数据清理脚本 - 桌面端 orders 表

清理目标:
- ORD-20260614-*  (30 条测试订单)
- ORD-20260615-*  (200 条测试订单)
- 保留: 其他 11 条真实业务订单

支持:
- --dry-run    只打印清单, 不删
- --no-backup  不备份(默认备份)
- --include-archived  包含已归档订单
"""
import os
import sys
import json
import shutil
import argparse
from datetime import datetime
from pathlib import Path

import pymysql

PROJECT_DIR = Path(r'd:\yuan\不锈钢网带跟单3.0')
BACKUP_DIR = PROJECT_DIR / 'data' / 'backup'


def get_connection():
    return pymysql.connect(
        host='localhost', port=3306,
        user='root', password='88888888',
        database='steel_belt', charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )


def find_dirty_orders(conn, include_archived=False):
    """找出所有测试订单 (按 order_no 前缀匹配)"""
    cur = conn.cursor()
    test_prefixes = ('ORD-20260614-', 'ORD-20260615-')

    conditions = []
    params = []
    for p in test_prefixes:
        conditions.append("order_no LIKE %s")
        params.append(p + '%')
    where = " OR ".join(conditions)

    if not include_archived:
        where += " AND is_deleted=0 AND is_archived=0"

    cur.execute(
        f"SELECT id, order_no, customer_name, quantity, status, is_deleted, is_archived, created_at "
        f"FROM orders WHERE {where} ORDER BY order_no",
        params
    )
    return cur.fetchall()


def find_kept_orders(conn):
    """找出要保留的真实订单"""
    cur = conn.cursor()
    cur.execute(
        "SELECT id, order_no, customer_name, quantity, status, is_deleted, is_archived, created_at "
        "FROM orders "
        "WHERE order_no NOT LIKE 'ORD-20260614-%' AND order_no NOT LIKE 'ORD-20260615-%' "
        "ORDER BY id"
    )
    return cur.fetchall()


def backup_table(conn, backup_dir: Path):
    """备份 orders 表 (导出为 INSERT 语句文件)"""
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = backup_dir / f'{ts}_orders_backup.sql'

    cur = conn.cursor()
    cur.execute("SELECT * FROM orders ORDER BY id")
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()

    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(f'-- orders 表备份, 时间 {ts}\n')
        f.write(f'-- 共 {len(rows)} 行\n')
        f.write(f'-- 列: {", ".join(cols)}\n\n')
        for r in rows:
            vals = []
            for c in cols:
                v = r[c]
                if v is None:
                    vals.append('NULL')
                elif isinstance(v, (int, float)):
                    vals.append(str(v))
                else:
                    vals.append("'" + str(v).replace("'", "''") + "'")
            f.write(f'INSERT INTO orders (id, {", ".join(cols[1:])}) VALUES ({r["id"]}, {", ".join(vals[1:])});\n')

    return backup_path


def dry_run():
    """只打印清单, 不动数据库"""
    conn = get_connection()
    try:
        dirty = find_dirty_orders(conn)
        kept = find_kept_orders(conn)

        print('=' * 70)
        print('【dry-run 模式】不修改数据库, 只展示清理清单')
        print('=' * 70)

        print(f'\n[将删除] 测试订单: {len(dirty)} 条')
        # 按 order_no 前缀分组
        from collections import Counter
        by_prefix = Counter(r['order_no'][:13] for r in dirty)
        for p, c in by_prefix.most_common():
            print(f'  {p}*: {c} 条')

        # 时间分布
        by_date = Counter(r['created_at'].date().isoformat() for r in dirty)
        print(f'\n时间分布:')
        for d, c in sorted(by_date.items()):
            print(f'  {d}: {c} 条')

        # 客户名分布
        by_cust = Counter(r['customer_name'] for r in dirty)
        print(f'\n客户名分布:')
        for n, c in by_cust.most_common(10):
            print(f'  {n!r}: {c} 条')

        print(f'\n[将保留] 真实业务订单: {len(kept)} 条')
        for r in kept:
            print(f'  id={r["id"]:4} order_no={r["order_no"]:25} '
                  f'customer={r["customer_name"]!r:20} qty={r["quantity"]:5} '
                  f'status={r["status"]:8} created={r["created_at"]}')

        print(f'\n合计: 删除 {len(dirty)} + 保留 {len(kept)} = {len(dirty) + len(kept)} 条')
        print('  数据库当前总行数 (按 is_deleted=0 AND is_archived=0) = ?')
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM orders WHERE is_deleted=0 AND is_archived=0")
        print(f'  实际未删除未归档行数 = {cur.fetchone()["COUNT(*)"]}')
    finally:
        conn.close()


def do_clean(no_backup=False):
    """正式清理: 备份 + 逻辑删除 (is_deleted=1)"""
    conn = get_connection()
    try:
        dirty = find_dirty_orders(conn)
        if not dirty:
            print('无脏数据, 跳过')
            return

        print(f'将清理 {len(dirty)} 条测试订单')

        # 1. 备份
        if not no_backup:
            backup_path = backup_table(conn, BACKUP_DIR)
            print(f'✅ 备份完成: {backup_path} ({backup_path.stat().st_size} bytes)')
        else:
            print('⚠️  跳过备份 (用户指定 --no-backup)')

        # 2. 逻辑删除
        cur = conn.cursor()
        ids = [r['id'] for r in dirty]
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 分批更新 (避免单条 SQL 过长)
        batch_size = 50
        updated = 0
        for i in range(0, len(ids), batch_size):
            batch = ids[i:i + batch_size]
            placeholders = ','.join(['%s'] * len(batch))
            sql = f'UPDATE orders SET is_deleted=1, deleted_at=%s, deleted_by=%s WHERE id IN ({placeholders})'
            cur.execute(sql, [now, 'K22-清理-2026-06-16'] + batch)
            updated += cur.rowcount

        conn.commit()
        print(f'✅ 逻辑删除完成: {updated} 条 (is_deleted=1)')

        # 3. 验证
        cur.execute("SELECT COUNT(*) AS cnt FROM orders WHERE is_deleted=0 AND is_archived=0")
        remaining = cur.fetchone()['cnt']
        print(f'✅ 清理后未删除未归档行数: {remaining} (期望 11)')

        # 4. 列出保留的订单
        kept = find_kept_orders(conn)
        print(f'\n保留的 {len(kept)} 条真实业务订单:')
        for r in kept:
            print(f'  id={r["id"]:4} order_no={r["order_no"]:25} '
                  f'customer={r["customer_name"]!r:20} qty={r["quantity"]:5} '
                  f'status={r["status"]:8}')

    finally:
        conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='清理桌面端 orders 表测试数据')
    parser.add_argument('--dry-run', action='store_true', help='只打印清单, 不动数据库')
    parser.add_argument('--no-backup', action='store_true', help='不备份')
    parser.add_argument('--include-archived', action='store_true', help='包含已归档订单')
    args = parser.parse_args()

    if args.dry_run:
        dry_run()
    else:
        # 二次确认
        print('⚠️  即将正式清理 MySQL orders 表!')
        print('   强烈建议先跑 --dry-run 看清单')
        print()
        ans = input('确认执行? 输入 yes 继续, 其他取消: ')
        if ans.strip().lower() == 'yes':
            do_clean(no_backup=args.no_backup)
        else:
            print('已取消')
