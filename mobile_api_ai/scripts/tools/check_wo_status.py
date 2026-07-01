import sqlite3
import os

os.chdir(r"d:\yuan\不锈钢网带跟单3.0")

print("=" * 60)
print("检查 WO-202605008 在各数据源的状态")
print("=" * 60)

# 1. container_center.db
print("\n[1] container_center.db - process_records 表")
try:
    conn = sqlite3.connect('mobile_api_ai/container_center.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, order_no, order_no, status, source FROM process_records ORDER BY created_at DESC LIMIT 10')
    records = cursor.fetchall()
    print(f"   总记录数: {cursor.execute('SELECT COUNT(*) FROM process_records').fetchone()[0]}")
    print("   最新10条:")
    for r in records:
        print(f"     {r}")
    cursor.execute('SELECT id, order_no FROM process_records WHERE order_no LIKE ?', ('%202605008%',))
    wo008 = cursor.fetchall()
    print(f"\n   WO-202605008: {'找到 ' + str(wo008) if wo008 else '未找到'}")
    conn.close()
except Exception as e:
    print(f"   错误: {e}")

# 2. data_packages 表
print("\n[2] container_center.db - data_packages 表")
try:
    conn = sqlite3.connect('mobile_api_ai/container_center.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, package_type, wo_no, created_at FROM data_packages WHERE wo_no LIKE ? ORDER BY created_at DESC", ('%202605008%',))
    wo008_pkg = cursor.fetchall()
    print(f"   WO-202605008 data_packages: {'找到 ' + str(len(wo008_pkg)) + ' 条' if wo008_pkg else '未找到'}")
    if wo008_pkg:
        for p in wo008_pkg:
            print(f"     {p}")
    conn.close()
except Exception as e:
    print(f"   错误: {e}")

# 3. 调度中心缓存
print("\n[3] 调度中心缓存 (dispatch_center_data.json)")
try:
    import json
    cache_file = "mobile_api_ai/dispatch_center_data.json"
    if os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        wo008_in_cache = [item for item in data if 'WO-202605008' in str(item)]
        print(f"   缓存记录数: {len(data)}")
        print(f"   WO-202605008: {'找到 ' + str(len(wo008_in_cache)) + ' 条' if wo008_in_cache else '未找到'}")
    else:
        print("   缓存文件不存在")
except Exception as e:
    print(f"   错误: {e}")

# 4. 检查调度中心API端点
print("\n[4] 调度中心 API 状态检查")
import requests
try:
    resp = requests.get("http://127.0.0.1:5003/api/dispatch/processes", timeout=3)
    if resp.status_code == 200:
        data = resp.json()
        if data.get('code') == 0:
            processes = data.get('data', [])
            wo008_in_api = [p for p in processes if 'WO-202605008' in str(p)]
            print(f"   API返回工单数: {len(processes)}")
            print(f"   WO-202605008: {'找到' if wo008_in_api else '未找到'}")
        else:
            print(f"   API错误: {data}")
    else:
        print(f"   API状态码: {resp.status_code}")
except Exception as e:
    print(f"   API连接失败: {e}")

print("\n" + "=" * 60)
