"""Check if any work order numbers starting with 'W' exist in databases"""
import sqlite3

def check_db(path, label):
    print(f'=== {label} ===')
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r['name'] for r in cur.fetchall()]
    
    found = []
    for t in tables:
        cur.execute('PRAGMA table_info("%s")' % t)
        cols = [c['name'] for c in cur.fetchall()]
        for c in cols:
            try:
                cur.execute('SELECT "%s" FROM "%s" WHERE "%s" LIKE ? LIMIT 50' % (c, t, c), ('W%',))
                rows = cur.fetchall()
                for r in rows:
                    val = r[c]
                    if val and str(val).startswith('W'):
                        found.append((t, c, val))
            except Exception as e:
                print(f"[check_wno] 查询表 {t} 字段 {c} 失败: {e}")
    
    if found:
        print(f'  找到 {len(found)} 条 W 开头的记录:')
        for t, c, v in found:
            print(f'    [{t}] {c} = {v}')
    else:
        print('  没有找到 W 开头的订单号')
    
    conn.close()
    return found

# chengsheng.db
cs_db = 'D:\\yuan\\不锈钢网带跟单3.0\\mobile_api_ai\\chengsheng.db'
check_db(cs_db, 'chengsheng.db')

print()

# wechat_container.db
cc_db = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'
check_db(cc_db, 'wechat_container.db')
