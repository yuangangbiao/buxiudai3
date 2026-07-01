import sqlite3, json

db = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row

# process_records 表结构
cols = [c[1] for c in conn.execute("PRAGMA table_info(process_records)")]
print(f'process_records 字段: {cols}')

# 查所有工单（找对应字段）
for col in ['order_no', 'order_id', 'order_no']:
    try:
        rows = conn.execute(f"""
            SELECT "{col}", COUNT(*) as cnt, MIN(id) as first_id, MAX(id) as last_id
            FROM process_records
            WHERE "{col}" IS NOT NULL AND "{col}" != ''
            GROUP BY "{col}"
            ORDER BY cnt DESC
        """).fetchall()
        if rows:
            print(f'\n=== process_records.{col} 汇总 ===')
            for r in rows:
                print(f'  {r[col]}: {r["cnt"]} 条')
    except Exception as e:
        print(f'process_records.{col}: 字段不存在 (查询失败: {e})')

# order_records / schedule_records 表
for table in ['order_records', 'schedule_records', 'orders', 'work_orders']:
    try:
        cnt = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        cols2 = [c[1] for c in conn.execute(f"PRAGMA table_info({table})")]
        print(f'\n=== {table} ({cnt} 行) 字段: {cols2[:8]}... ===')
        if cnt > 0 and cnt < 50:
            for col in cols2[:2]:
                try:
                    rows = conn.execute(f'SELECT DISTINCT "{col}" FROM "{table}" WHERE "{col}" IS NOT NULL AND "{col}" != ""').fetchall()
                    if rows:
                        vals = [r[col] for r in rows]
                        print(f'  {col}: {vals}')
                except Exception as e:
                    print(f'  {col}: 查询失败 ({e})')
    except Exception as e:
        print(f'{table}: 不存在 (查询失败: {e})')

conn.close()
