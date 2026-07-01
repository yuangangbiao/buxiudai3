"""妫€鏌?production_orders 涓?orders 鐨勬暟鎹搴斿叧绯?""
import os, pymysql, json
from pymysql.cursors import DictCursor
from dotenv import load_dotenv

load_dotenv('D:/yuan/涓嶉攬閽㈢綉甯﹁窡鍗?.0/mobile_api_ai/.env')
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

# 1. production_orders 鍏ㄩ噺锛堝惈鍏宠仈鐨?orders 淇℃伅锛?c.execute("""
    SELECT po.id, po.order_no, po.order_id, po.status AS po_status,
           po.plan_start, po.plan_end, po.created_at AS po_created,
           o.id AS o_id, o.order_no, o.status AS o_status, o.created_at AS o_created
    FROM production_orders po
    LEFT JOIN orders o ON po.order_id = o.id
    ORDER BY po.id
""")
pos = c.fetchall()

print("=" * 80)
print("銆恜roduction_orders 鍏ㄩ噺娓呭崟锛堝惈鍏宠仈 orders 淇℃伅锛夈€?)
print("=" * 80)
print(f"{'po_id':>6} {'order_no':<25} {'order_id':>9} {'po_status':<8} {'o_id':>5} {'order_no':<22} {'o_status':<8}")
print("-" * 80)
mismatches = []
orphans = []
for r in pos:
    print(f"{r['id']:>6} {r['order_no']:<25} {r['order_id']:>9} {r['po_status']:<8} {r.get('o_id',''):>5} {r.get('order_no','<鏃?')[:22]:<22} {r.get('o_status','?'):<8}")
    
    # 妫€鏌ュ搴斾笉涓?    if not r['o_id']:
        mismatches.append(f"  [!] [瀛ょ珛宸ュ崟] po_id={r['id']} order_no={r['order_no']} 鈫?鍏宠仈鐨?order_id={r['order_id']} 鍦?orders 琛ㄤ腑涓嶅瓨鍦?)
    elif r['po_status'] != r['o_status']:
        mismatches.append(f"  [!] [鐘舵€佷笉涓€鑷碷 po_id={r['id']} wo={r['order_no']}: po_status={r['po_status']} 鈮?o_status={r['o_status']} (order_no={r['order_no']})")

# 2. orders 鍏ㄩ噺锛堟鏌ュ摢浜涜鍗曟病鏈夊搴旂殑 production_orders锛?c.execute("""
    SELECT o.id, o.order_no, o.status AS o_status,
           po.id AS po_id, po.order_no, po.status AS po_status
    FROM orders o
    LEFT JOIN production_orders po ON o.id = po.order_id
    ORDER BY o.id
""")
orders = c.fetchall()

print("\n" + "=" * 80)
print("銆恛rders 鍏ㄩ噺娓呭崟锛堝惈鍏宠仈 production_orders 淇℃伅锛夈€?)
print("=" * 80)
print(f"{'o_id':>5} {'order_no':<22} {'o_status':<8} {'po_id':>6} {'order_no':<25} {'po_status':<8}")
print("-" * 80)
for r in orders:
    po_id = r.get('po_id')
    order_no_val = str(r['order_no']) if r['order_no'] else ''
    print(f"{r['id']:>5} {order_no_val:<22} {r['o_status']:<8} {str(po_id or ''):>6} {str(r.get('order_no','') or '<鏃犲伐鍗?')[:25]:<25} {str(r.get('po_status','') or ''):<8}")

# 3. 姹囨€讳笉涓€鑷?print("\n" + "=" * 80)
print("銆愪笉涓€鑷存竻鍗曘€?)
print("=" * 80)

# 鐘舵€佷笉涓€鑷?if mismatches:
    for m in mismatches:
        print(m)
else:
    print("  [+] production_orders 涓?orders 鐘舵€佸叏閮ㄤ竴鑷?)

# 鏈夌敓浜у伐鍗曚絾 orders 涓笉瀛樺湪鐨勶紙瀛ょ珛 production_orders锛?orphan_pos = [r for r in pos if not r['o_id']]
if orphan_pos:
    for r in orphan_pos:
        print(f"  [!] [瀛ょ珛宸ュ崟] po_id={r['id']} wo={r['order_no']}: 鎸囧悜涓嶅瓨鍦ㄧ殑 order_id={r['order_id']}")

# orders 涓病鏈夊搴?production_orders 鐨?no_po_orders = [r for r in orders if not r['po_id']]
if no_po_orders:
    print(f"\n  [-] 浠ヤ笅 {len(no_po_orders)} 涓鍗曟病鏈夊搴旂殑 production_orders锛堟湭杩涘叆鐢熶骇娴佺▼锛?")
    for r in no_po_orders:
        print(f"    o_id={r['id']} order_no={r['order_no']:22} status={r['o_status']}")
else:
    print("  [+] 鎵€鏈?orders 閮芥湁瀵瑰簲鐨?production_orders")

conn.close()
