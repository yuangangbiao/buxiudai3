import sqlite3
import os
import json

os.chdir(r"d:\yuan\不锈钢网带跟单3.0")

print("=" * 60)
print("检查缓存和数据库中的工单状态")
print("=" * 60)

# 1. 检查 process_records 表
print("\n[1] wechat_container.db - process_records 表")
conn = sqlite3.connect('mobile_api_ai/wechat_container.db')
cursor = conn.cursor()

# 检查 WO-202605007 和 WO-202605008
for wo in ['WO-202605007', 'WO-202605008', 'WO-202605005', 'WO-202605006']:
    cursor.execute('SELECT id, order_no, order_no, status, source, created_at FROM process_records WHERE order_no LIKE ?', (f'%{wo}%',))
    result = cursor.fetchall()
    if result:
        for r in result:
            print(f"  {wo}: ID={r[0]}, Status={r[3]}, Source={r[4]}, Created={r[5]}")
    else:
        print(f"  {wo}: 未找到")

conn.close()

# 2. 检查缓存文件
print("\n[2] dispatch_center_data.json 缓存")
cache_file = 'mobile_api_ai/dispatch_center_data.json'
if os.path.exists(cache_file):
    with open(cache_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    processes = data.get('processes', [])
    print(f"  流程数: {len(processes)}")

    for wo in ['WO-202605007', 'WO-202605008', 'WO-202605005', 'WO-202605006']:
        found = [p for p in processes if wo in str(p.get('order_no', '')) or wo in str(p.get('order_no', ''))]
        if found:
            for p in found:
                print(f"  {wo}: ID={p.get('id')}, Status={p.get('status')}, OrderNo={p.get('order_no')}")
        else:
            print(f"  {wo}: 缓存中未找到")

    # 显示最新5个流程
    print("\n  最新5个流程:")
    sorted_procs = sorted(processes, key=lambda x: x.get('updated_at', ''), reverse=True)[:5]
    for p in sorted_procs:
        print(f"    {p.get('order_no', 'N/A')}/{p.get('order_no', 'N/A')}: Status={p.get('status')}, Updated={p.get('updated_at', 'N/A')[:19] if p.get('updated_at') else 'N/A'}")
else:
    print("  缓存文件不存在")

print("\n" + "=" * 60)
