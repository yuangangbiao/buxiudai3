import sqlite3, json

def query_db(path, label):
    print(f'\n{"="*60}')
    print(f'{label}: {path}')
    print(f'{"="*60}')
    try:
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        print(f'表列表: {[t["name"] for t in tables]}')
        
        for t in tables:
            tn = t['name']
            cols = conn.execute(f'PRAGMA table_info("{tn}")').fetchall()
            col_names = [c['name'] for c in cols]
            print(f'\n--- {tn} (列: {col_names}) ---')
            
            if tn == 'sub_steps':
                rows = conn.execute("SELECT * FROM sub_steps WHERE order_no LIKE '%008%' OR order_no LIKE '%WO-2026%' ORDER BY created_at DESC").fetchall()
            elif tn == 'process_sub_steps':
                rows = conn.execute("SELECT * FROM process_sub_steps WHERE order_no LIKE '%008%' OR order_no LIKE '%WO-2026%' ORDER BY created_at DESC").fetchall()
            elif tn == 'data_packages':
                rows = conn.execute("SELECT * FROM data_packages WHERE related_order LIKE '%008%' OR related_order LIKE '%ORD-2026%' ORDER BY created_at DESC").fetchall()
            elif tn == 'work_orders':
                rows = conn.execute("SELECT * FROM work_orders WHERE order_no LIKE '%008%' OR id LIKE '%008%' LIMIT 10").fetchall()
            else:
                rows = None
            
            if rows is None:
                all_rows = conn.execute(f'SELECT * FROM "{tn}" LIMIT 5').fetchall()
                for r in all_rows:
                    print(f'  {dict(r)}')
            elif len(rows) == 0:
                print('  (无匹配记录)')
                all_rows = conn.execute(f'SELECT * FROM "{tn}" LIMIT 3').fetchall()
                if all_rows:
                    print(f'  (样本数据): {[dict(r) for r in all_rows]}')
            else:
                for r in rows:
                    d = dict(r)
                    for k, v in d.items():
                        if isinstance(v, str) and len(v) > 200:
                            d[k] = v[:200] + '...(截断)'
                    print(f'  {d}')
        
        conn.close()
    except Exception as e:
        print(f'  错误: {e}')

# 检查所有相关数据库
query_db('chengsheng.db', '晨圣数据库')
query_db('wechat_container.db', '微信容器数据库')
