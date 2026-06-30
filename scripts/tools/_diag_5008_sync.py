"""5008 同步链路诊断脚本 - 2026-06-23"""
import pymysql
from collections import Counter

CONN_KW = dict(host='127.0.0.1', port=3306, user='root', password='88888888', connect_timeout=5, cursorclass=pymysql.cursors.DictCursor)

def show_table(host_db, tbl):
    try:
        conn = pymysql.connect(database=host_db, **CONN_KW)
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) c FROM `{tbl}`")
        c = cur.fetchone()['c']
        print(f"  {host_db}.{tbl:35s}  {c}")
        # 状态分布
        try:
            cur.execute(f"SELECT status, COUNT(*) c FROM `{tbl}` GROUP BY status")
            for r in cur.fetchall():
                print(f"    - {r['status']:20s} {r['c']}")
        except Exception:
            pass
        conn.close()
    except Exception as e:
        print(f"  FAIL {host_db}.{tbl}: {e}")

print("=" * 60)
print("【1】5001 写入的源头数据 (steel_belt)")
print("=" * 60)
for t in ['orders', 'production_orders', 'process_sub_steps', 'process_records', 'quality_records', 'material_records', 'outsource_records', 'repair_records']:
    show_table('steel_belt', t)

print()
print("=" * 60)
print("【2】5008 端的容器中心 (container_center)")
print("=" * 60)
for t in ['orders', 'production_orders', 'process_sub_steps', 'process_records', 'quality_records', 'material_records', 'outsource_records', 'repair_records']:
    show_table('container_center', t)

print()
print("=" * 60)
print("【3】同步链路 (outbox / sync_outbox / sync_queue)")
print("=" * 60)
for db, t in [('steel_belt','outbox'), ('steel_belt','sync_outbox'), ('steel_belt','sync_queue'),
              ('container_center','outbox'), ('container_center','sync_outbox'), ('container_center','sync_queue'),
              ('container_center','sync_log'), ('container_center','sync_logs'),
              ('container_center','etl_dead_letter'), ('container_center','sync_retry_queue')]:
    show_table(db, t)

print()
print("=" * 60)
print("【4】最近 orders (steel_belt)")
print("=" * 60)
conn = pymysql.connect(database='steel_belt', **CONN_KW)
cur = conn.cursor()
cur.execute("SELECT order_no, customer_name, product_name, status, create_time FROM orders ORDER BY create_time DESC LIMIT 5")
for r in cur.fetchall():
    print(f"  {r['order_no']:35s} {r['status']:15s} {r['create_time']}")
conn.close()

print()
print("【5】最近 orders (container_center)")
conn = pymysql.connect(database='container_center', **CONN_KW)
cur = conn.cursor()
cur.execute("SELECT order_no, customer_name, product_name, status, create_time FROM orders ORDER BY create_time DESC LIMIT 5")
for r in cur.fetchall():
    print(f"  {r['order_no']:35s} {r['status']:15s} {r['create_time']}")
conn.close()
