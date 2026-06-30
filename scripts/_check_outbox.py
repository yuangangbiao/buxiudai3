"""验证 outbox 表 + 等待 5003 轮询"""
import pymysql
import time
import requests

conn = pymysql.connect(
    host='127.0.0.1', port=3306, user='root', password='88888888',
    database='container_center', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor,
)
with conn.cursor() as cur:
    cur.execute("SHOW TABLES LIKE 'outbox'")
    exists = cur.fetchone()
    print(f'outbox exists in container_center: {bool(exists)}')
    if exists:
        cur.execute('SELECT COUNT(*) as cnt FROM outbox')
        print(f'outbox count: {cur.fetchone()["cnt"]}')
conn.close()

# 等 30s 让 5003 轮询 5 次
print('\n等待 30s 让 outbox 轮询跑多次...')
time.sleep(30)

# 看最新日志
with open(r'd:\yuan\不锈钢网带跟单3.0\logs\e2e_20260623\5003.err.log',
          'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

# 找最新 outbox 行
outbox_lines = [l for l in lines if 'outbox' in l.lower() or 'Outbox' in l]
print(f'\noutbox 相关日志总数: {len(outbox_lines)}')
print('最新 5 条:')
for l in outbox_lines[-5:]:
    print(f'  {l.strip()[:200]}')

# 看 5003 状态
r = requests.get('http://127.0.0.1:5003/', timeout=3)
print(f'\n5003 状态: {r.status_code}')
