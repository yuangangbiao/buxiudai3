"""查桌面端(5001)实际用的数据库配置和表"""
import pymysql
import os

# 5001 端 server.py 用什么数据库？
# 之前 models/database/config.py: 读 MYSQL_HOST/PORT/USER/PASSWORD/DATABASE
# 默认 DATABASE='steel_belt'
# 桌面端可能用了其他 DB

# 查所有数据库
conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='88888888', connect_timeout=5)
cur = conn.cursor()
cur.execute("SHOW DATABASES")
print("=== 所有数据库 ===")
for r in cur.fetchall():
    print(f"  {r[0]}")
conn.close()

# 每个 DB 都看是否有 material/outsource 相关表
for db in ['steel_belt', 'container_center', 'desktop', 'desktop_web', 'mirror']:
    try:
        conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='88888888', database=db, connect_timeout=5)
        cur = conn.cursor()
        cur.execute("SHOW TABLES")
        tables = [r[0] for r in cur.fetchall()]
        # 找物料/外协相关
        related = [t for t in tables if 'material' in t.lower() or 'out' in t.lower() or 'external' in t.lower() or 'outsource' in t.lower() or 'supplier' in t.lower() or 'process' in t.lower() or 'sub' in t.lower()]
        print(f'\n=== {db} ({len(tables)} 表) - 物料/外协相关 ===')
        for t in related: print(f'  {t}')
        conn.close()
    except Exception as e:
        print(f'  {db}: ERR {e}')
