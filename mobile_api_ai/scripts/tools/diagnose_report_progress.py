"""诊断报工进度不更新问题"""
import urllib.request
import json
import sys
import sqlite3
import os
import time

BASE = 'http://localhost:5008'

def eprint(*args, **kwargs):
    print(*args, **kwargs, flush=True)

def http_get(path):
    try:
        resp = urllib.request.urlopen(f'{BASE}{path}', timeout=5)
        return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        eprint(f"  HTTP错误: {e}")
        return None

def http_post(path, data):
    try:
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        req = urllib.request.Request(f'{BASE}{path}', data=body,
                                     headers={'Content-Type': 'application/json'})
        resp = urllib.request.urlopen(req, timeout=5)
        return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        eprint(f"  HTTP错误: {e}")
        return None

def check_database(db_path):
    """检查数据库中的报工记录"""
    if not os.path.exists(db_path):
        eprint(f"  数据库不存在: {db_path}")
        return

    eprint(f"  检查数据库: {db_path}")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='process_sub_steps'")
        if not cursor.fetchone():
            eprint("    process_sub_steps 表不存在")
            conn.close()
            return

        cursor.execute("SELECT COUNT(*) FROM process_sub_steps")
        count = cursor.fetchone()[0]
        eprint(f"    process_sub_steps 表中有 {count} 条记录")

        if count > 0:
            cursor.execute("""
                SELECT process_id, step_name, quantity, operator, created_at
                FROM process_sub_steps
                ORDER BY created_at DESC
                LIMIT 5
            """)
            eprint("    最近5条记录:")
            for row in cursor.fetchall():
                eprint(f"      - process_id: {row[0][:20]}..., step: {row[1]}, qty: {row[2]}, operator: {row[3]}, time: {row[4]}")

        conn.close()
    except Exception as e:
        eprint(f"    数据库错误: {e}")

def main():
    if len(sys.argv) < 2:
        print("用法: python diagnose_report_progress.py <订单号>")
        print("示例: python diagnose_report_progress.py ORD-202604210003")
        sys.exit(1)

    order_no = sys.argv[1]

    eprint("=" * 60)
    eprint(f"诊断报工进度不更新问题 - 订单: {order_no}")
    eprint("=" * 60)

    # 1. 检查 API 服务器是否运行
    eprint("\n[1] 检查 API 服务器...")
    resp = http_get('/api/scan-info?code=test')
    if resp is not None:
        eprint("  ✅ API 服务器正常")
    else:
        eprint("  ❌ API 服务器无响应，请检查服务是否启动")
        eprint("  启动命令: python mobile_api_ai/container_center_api.py")
        sys.exit(1)

    # 2. 查询订单信息
    eprint(f"\n[2] 查询订单 {order_no} 信息...")
    info = http_get(f'/api/scan-info?code={order_no}')
    if not info or info.get('code') != 0:
        eprint(f"  ❌ 查询失败: {info.get('message') if info else '无响应'}")
        sys.exit(1)

    data = info.get('data', {})
    eprint(f"  ✅ 找到订单")
    eprint(f"     产品: {data.get('product_name')}")
    eprint(f"     总数量: {data.get('quantity')}")
    eprint(f"     总完成: {data.get('total_completed_qty')}")
    eprint(f"     工序数量: {len(data.get('processes', []))}")

    process_id = None
    if data.get('processes'):
        process_id = data['processes'][0].get('process_id')
        eprint(f"     第一个工序的 process_id: {process_id}")

    # 3. 检查工序进度
    eprint(f"\n[3] 各工序进度:")
    for p in data.get('processes', []):
        completed = p.get('completed_qty', 0)
        required = p.get('required_qty', 0)
        eprint(f"     {p.get('step_name')}: {completed}/{required}")

    # 4. 检查可能的数据库文件
    eprint(f"\n[4] 检查数据库文件...")

    possible_db_paths = [
        'D:/yuan/不锈钢网带跟单3.0/mobile_api_ai/wechat_container.db',
        'D:/yuan/不锈钢网带跟单3.0/mobile_api_ai/chengsheng.db',
        'mobile_api_ai/wechat_container.db',
        'wechat_container.db',
        'chengsheng.db',
    ]

    found_dbs = []
    for db_path in possible_db_paths:
        if os.path.exists(db_path):
            found_dbs.append(db_path)
            eprint(f"  ✅ 找到: {db_path}")
            check_database(db_path)
        else:
            eprint(f"  - 不存在: {db_path}")

    if not found_dbs:
        eprint("  ❌ 未找到任何数据库文件")

    # 5. 总结
    eprint("\n" + "=" * 60)
    eprint("诊断总结:")
    eprint("=" * 60)

    total_completed = data.get('total_completed_qty', 0)
    if total_completed == 0:
        eprint("⚠️  总完成数量为 0")
        eprint("   可能原因:")
        eprint("   1. 报工数据没有写入数据库")
        eprint("   2. 报工时使用的数据库与查询时使用的数据库不同")
        eprint("   3. process_sub_steps 表为空或查询有问题")
    else:
        eprint(f"✅ 总完成数量: {total_completed}")
        eprint("   如果报工表单仍显示 0，请检查:")
        eprint("   1. 前端代码中的数据映射是否正确")
        eprint("   2. 是否有浏览器缓存问题")

    if process_id:
        eprint(f"\n📝 订单的 process_id: {process_id}")
        eprint("   如果需要手动检查数据库，可以运行:")
        eprint(f"   sqlite3 wechat_container.db \"SELECT * FROM process_sub_steps WHERE process_id='{process_id}';\"")

if __name__ == '__main__':
    main()
