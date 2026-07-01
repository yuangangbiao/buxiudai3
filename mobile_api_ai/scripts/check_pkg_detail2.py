import sqlite3, json

db_path = 'd:/yuan/不锈钢网带跟单3.0/mobile_api_ai/wechat_container.db'
db = sqlite3.connect(db_path)
cur = db.cursor()

cur.execute('PRAGMA table_info(data_packages)')
cols = [d[1] for d in cur.fetchall()]
print(f'data_packages 字段: {cols}')

col_str = ', '.join(cols)
cur.execute(f"SELECT {col_str} FROM data_packages WHERE related_order IN ('WO-202605005', 'ORD-202604210003') ORDER BY id")
rows = cur.fetchall()
print(f'\n记录数: {len(rows)}')
for r in rows:
    row = dict(zip(cols, r))
    print(f'\n--- id={row["id"]}, related_order={row.get("related_order")}, related_process={row.get("related_process")} ---')
    for k, v in row.items():
        if k in ('content',) and isinstance(v, str) and len(v) > 50:
            try:
                c = json.loads(v)
                print(f'  {k}: (JSON) keys={list(c.keys())}')
                for ck, cv in c.items():
                    if ck in ('steps','processes','products') and isinstance(cv, list):
                        print(f'    {ck}: {[s.get("name","?") if isinstance(s,dict) else str(s)[:30] for s in cv]}')
                    elif isinstance(cv, (str,int,float)):
                        print(f'    {ck}: {cv}')
                    elif isinstance(cv, dict):
                        print(f'    {ck}: {json.dumps(cv, ensure_ascii=False)[:200]}')
            except Exception as e:
                print(f'  {k}: {v[:200]} (JSON解析失败: {e})')
        elif k not in ('content',):
            print(f'  {k}: {v}')

# 查看 data_packages 的 order_no 分布
cur.execute("SELECT DISTINCT related_order, related_process FROM data_packages ORDER BY related_order")
print('\n=== data_packages 所有工单/工序 ===')
for r in cur.fetchall():
    print(f'  {r[0]} | {r[1]}')

print(f'\n总记录数: {cur.execute("SELECT COUNT(*) FROM data_packages").fetchone()[0]}')

db.close()
