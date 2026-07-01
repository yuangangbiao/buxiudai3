"""淇 orders 琛ㄦ暟鎹細娓呯悊 WO- 姹℃煋鏁版嵁 + 瀵归綈鐘舵€?""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv('D:/yuan/涓嶉攬閽㈢綉甯﹁窡鍗?.0/mobile_api_ai/.env')

import pymysql
from pymysql.cursors import DictCursor
from datetime import datetime

cfg = {
    'host': os.environ.get('MYSQL_HOST', ''),
    'port': int(os.environ.get('MYSQL_PORT', 3306)),
    'user': os.environ.get('MYSQL_USER', 'root'),
    'password': os.environ.get('MYSQL_PASSWORD', ''),
    'database': os.environ.get('MYSQL_DATABASE', 'steel_belt'),
    'charset': 'utf8mb4',
}

conn = pymysql.connect(**cfg, cursorclass=DictCursor)
c = conn.cursor()

def log_step(msg):
    print(f"\n{'='*60}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    print('='*60)

def backup_table(tbl, file_label):
    c.execute(f"SELECT * FROM {tbl} ORDER BY id")
    rows = c.fetchall()
    fname = f'D:/yuan/涓嶉攬閽㈢綉甯﹁窡鍗?.0/mobile_api_ai/scripts/backup_{tbl}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.sql'
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(f"-- {tbl} 琛ㄥ浠?({datetime.now()})\n\n")
        for r in rows:
            cols = ', '.join(r.keys())
            vals = ', '.join(f"'{str(v).replace(chr(39), chr(39)*2)}'" if v is not None else 'NULL' for v in r.values())
            f.write(f"INSERT INTO {tbl} ({cols}) VALUES ({vals});\n")
    print(f"  {file_label}: {len(rows)} 鏉?-> {fname}")
    return fname

# =====================================================
# 1. 澶囦唤
# =====================================================
log_step("1/6 澶囦唤鏁版嵁")
backup_table('orders', 'orders')
backup_table('production_orders', 'production_orders')
# Also backup child tables that might have references to WO- records
c.execute("SELECT id FROM orders WHERE order_no LIKE 'WO-%'")
wo_ids = [r['id'] for r in c.fetchall()]

child_tables = [
    'finished_goods', 'inventory_records', 'material_history',
    'operation_logs', 'order_logs', 'order_materials',
    'shipments', 'production_stats', 'quality_records',
    'process_records', 'production_orders'
]

if wo_ids:
    placeholders = ','.join(['%s'] * len(wo_ids))
    for tbl in child_tables:
        c.execute(f"SELECT COUNT(*) AS cnt FROM {tbl} WHERE order_id IN ({placeholders})", wo_ids)
        if c.fetchone()['cnt'] > 0:
            # Backup only rows related to WO- records
            c.execute(f"SELECT * FROM {tbl} WHERE order_id IN ({placeholders}) ORDER BY id", wo_ids)
            rows = c.fetchall()
            fname = f'D:/yuan/涓嶉攬閽㈢綉甯﹁窡鍗?.0/mobile_api_ai/scripts/backup_{tbl}_wo_{datetime.now().strftime("%Y%m%d_%H%M%S")}.sql'
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(f"-- {tbl} 琛ㄦ暟鎹浠?鈥?鍏宠仈 WO- 璁板綍 ({datetime.now()})\n\n")
                for r in rows:
                    cols = ', '.join(r.keys())
                    vals = ', '.join(f"'{str(v).replace(chr(39), chr(39)*2)}'" if v is not None else 'NULL' for v in r.values())
                    f.write(f"INSERT INTO {tbl} ({cols}) VALUES ({vals});\n")
            print(f"  {tbl} (WO- 鍏宠仈): {len(rows)} 鏉?-> {fname}")

print("  鎵€鏈夊浠藉畬鎴?)

# =====================================================
# 2. 娓呯悊 WO- 姹℃煋鏁版嵁锛堢骇鑱斿垹闄わ級
# =====================================================
log_step("2/6 娓呯悊 orders 琛ㄤ腑 WO- 姹℃煋鏁版嵁")

c.execute("SELECT id, order_no, status, created_at FROM orders WHERE order_no LIKE 'WO-%' ORDER BY id")
wo_records = c.fetchall()
print(f"  鍙戠幇 {len(wo_records)} 鏉?WO- 姹℃煋璁板綍:")
for r in wo_records:
    print(f"    o_id={r['id']:>3} order_no={r['order_no']:<25} status={r['status']:<8}")

if not wo_records:
    print("  鏃?WO- 姹℃煋璁板綍锛岃烦杩?)
else:
    wo_ids = [r['id'] for r in wo_records]
    placeholders = ','.join(['%s'] * len(wo_ids))

    # Step A: 澶勭悊 production_orders 绾ц仈锛堣琛ㄥ悓鏃惰 processes/production_stats/quality_records/process_records 寮曠敤锛?    c.execute(f"SELECT id, order_no FROM production_orders WHERE order_id IN ({placeholders})", wo_ids)
    linked_pos = c.fetchall()
    if linked_pos:
        po_ids = [po['id'] for po in linked_pos]
        po_ph = ','.join(['%s'] * len(po_ids))

        print(f"\n  鎵惧埌 {len(linked_pos)} 涓叧鑱?production_orders: IDs={po_ids}")

        # 绾ц仈鍒犻櫎: 寮曠敤 production_orders 鐨勮〃
        for tbl, col in [('process_records', 'production_id'), ('production_stats', 'production_id'),
                        ('quality_records', 'production_id'), ('processes', 'prod_order_id')]:
            c.execute(f"SELECT COUNT(*) AS cnt FROM {tbl} WHERE {col} IN ({po_ph})", po_ids)
            cnt = c.fetchone()['cnt']
            if cnt > 0:
                print(f"    绾ц仈鍒犻櫎 {tbl}.{col}: {cnt} 鏉?)
                c.execute(f"DELETE FROM {tbl} WHERE {col} IN ({po_ph})", po_ids)

        # 鍒犻櫎 production_orders 鏈韩
        print(f"    鍒犻櫎 production_orders: {len(po_ids)} 鏉?)
        c.execute(f"DELETE FROM production_orders WHERE id IN ({po_ph})", po_ids)

    # Step B: 鍒犻櫎鐩存帴寮曠敤 WO- orders 鐨勫叾浠栬〃
    table_col_map = [
        ('finished_goods', 'order_id'), ('inventory_records', 'order_id'),
        ('material_history', 'order_id'), ('operation_logs', 'order_id'),
        ('order_logs', 'order_id'), ('order_materials', 'order_id'),
        ('shipments', 'order_id'), ('production_stats', 'order_id'),
        ('quality_records', 'order_id'), ('process_records', 'order_id'),
    ]
    for tbl, col in table_col_map:
        c.execute(f"SELECT COUNT(*) AS cnt FROM {tbl} WHERE {col} IN ({placeholders})", wo_ids)
        cnt = c.fetchone()['cnt']
        if cnt > 0:
            print(f"  绾ц仈鍒犻櫎 {tbl}.{col}: {cnt} 鏉?)
            c.execute(f"DELETE FROM {tbl} WHERE {col} IN ({placeholders})", wo_ids)

    # Step C: 鍒犻櫎 WO- 姹℃煋鐨?orders 璁板綍
    c.execute(f"DELETE FROM orders WHERE id IN ({placeholders})", wo_ids)
    print(f"\n  宸插垹闄?{c.rowcount} 鏉?WO- 姹℃煋 orders 璁板綍")

# =====================================================
# 3. 淇鐘舵€佷笉涓€鑷?# =====================================================
log_step("3/6 淇鐘舵€佷笉涓€鑷?)
c.execute("""
    SELECT po.id AS po_id, po.order_no, po.status AS po_status,
           o.id AS o_id, o.order_no, o.status AS o_status
    FROM production_orders po
    JOIN orders o ON po.order_id = o.id
    WHERE po.status != o.status
    ORDER BY po.id
""")
inconsistencies = c.fetchall()
print(f"  鍙戠幇 {len(inconsistencies)} 鏉＄姸鎬佷笉涓€鑷?")
fixed_count = 0
skip_count = 0
for r in inconsistencies:
    print(f"    po_id={r['po_id']:>3} {r['order_no']:<22} po={r['po_status']:<8} | o_id={r['o_id']:>3} {r['order_no']:<22} o={r['o_status']:<8}", end='')
    if r['po_status'] in ('宸叉帓浜?, '寰呭彂甯?, '寰呭紑濮?, '寰呮帓浜?, '鐢熶骇涓?, '宸叉姤宸?, '璐ㄦ閫氳繃', '宸插畬鎴?):
        c.execute("UPDATE orders SET status=%s, updated_at=NOW() WHERE id=%s", (r['po_status'], r['o_id']))
        fixed_count += 1
        print(f" -> UPDATED to {r['po_status']}")
    else:
        print(f" -> SKIPPED (unrecognized po_status)")
        skip_count += 1
print(f"  宸蹭慨澶?{fixed_count} 鏉? 璺宠繃 {skip_count} 鏉?)

# =====================================================
# 4. 妫€鏌ユ棤 production_orders 鐨勮鍗?# =====================================================
log_step("4/6 妫€鏌ユ棤 production_orders 鐨勫悎娉曡鍗?)
c.execute("""
    SELECT o.id, o.order_no, o.status
    FROM orders o
    LEFT JOIN production_orders po ON o.id = po.order_id
    WHERE po.id IS NULL
    ORDER BY o.id
""")
no_po = c.fetchall()
print(f"  浠ヤ笅 {len(no_po)} 涓悎娉曡鍗曟棤瀵瑰簲 production_orders:")
for r in no_po:
    label = '宸插彇娑堬紝鏃犻渶澶勭悊' if r['status'] == '宸插彇娑? else '寰呭垱寤哄伐鍗?
    print(f"    o_id={r['id']:>3} order_no={r['order_no']:<22} status={r['status']:<8} [{label}]")

conn.commit()
print(f"\n  浜嬪姟宸叉彁浜?)

# =====================================================
# 5. 楠岃瘉
# =====================================================
log_step("5/6 鏈€缁堥獙璇?)

print("\n--- orders 琛ㄥ墿浣?WO- 璁板綍 ---")
c.execute("SELECT COUNT(*) AS cnt FROM orders WHERE order_no LIKE 'WO-%'")
wo_left = c.fetchone()['cnt']
print(f"  {'[OK] 鏃?WO- 姹℃煋璁板綍' if wo_left == 0 else f'[!] 鍓╀綑 {wo_left} 鏉?}")

print("\n--- 鐘舵€佷竴鑷存€ф鏌?---")
c.execute("""
    SELECT COUNT(*) AS cnt FROM production_orders po
    JOIN orders o ON po.order_id = o.id
    WHERE po.status != o.status
""")
mismatch_count = c.fetchone()['cnt']
print(f"  {'[OK] 鍏ㄩ儴涓€鑷? if mismatch_count == 0 else f'[!] 鍓╀綑 {mismatch_count} 鏉′笉涓€鑷?}")

print("\n--- orders 鍏ㄩ噺鍒楄〃 ---")
c.execute("SELECT id, order_no, status, created_at FROM orders ORDER BY id")
for r in c.fetchall():
    print(f"    o_id={r['id']:>3} order_no={r['order_no']:<25} status={r['status']:<8}")

conn.close()

print(f"\n{'='*60}")
print(f"淇瀹屾垚!")
print(f"{'='*60}")
