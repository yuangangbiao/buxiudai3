"""测试报工流程 - 验证进度不刷新的问题"""
import urllib.request
import json
import sys
import time

BASE = 'http://localhost:5008'

def eprint(*args, **kwargs):
    print(*args, **kwargs, flush=True)

def post(path, data):
    body = json.dumps(data, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(f'{BASE}{path}', data=body,
                                 headers={'Content-Type': 'application/json'})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read().decode('utf-8'))

def get(path):
    resp = urllib.request.urlopen(f'{BASE}{path}')
    return json.loads(resp.read().decode('utf-8'))

if len(sys.argv) < 2:
    print("用法: python test_report_progress.py <订单号>")
    print("示例: python test_report_progress.py ORD-202604210003")
    sys.exit(1)

order_no = sys.argv[1]

print(f"=== 测试订单: {order_no} ===\n")

print("1. 查询报工前状态...")
try:
    info1 = get(f'/api/scan-info?code={order_no}')
    if info1.get('code') != 0:
        print(f"   错误: {info1.get('message')}")
        sys.exit(1)

    data1 = info1.get('data', {})
    print(f"   工单号: {data1.get('order_no')}")
    print(f"   产品: {data1.get('product_name')}")
    print(f"   总数量: {data1.get('quantity')}")
    print(f"   总完成: {data1.get('total_completed_qty')}")
    print(f"   工序列表:")
    for p in data1.get('processes', []):
        completed = p.get('completed_qty', 0)
        required = p.get('required_qty', 0)
        print(f"     - {p.get('process_name')}: {completed}/{required}")

except Exception as e:
    print(f"   查询失败: {e}")
    sys.exit(1)

print(f"\n2. 请在手机上执行报工操作...")
print(f"   选择一个工序，输入完成数量，点击提交")
print(f"   报工成功后，返回这里按回车继续测试...")

input()

print(f"\n3. 查询报工后状态...")
time.sleep(1)
try:
    info2 = get(f'/api/scan-info?code={order_no}')
    if info2.get('code') != 0:
        print(f"   错误: {info2.get('message')}")
        sys.exit(1)

    data2 = info2.get('data', {})
    print(f"   总完成: {data2.get('total_completed_qty')}")
    print(f"   工序列表:")
    for p in data2.get('processes', []):
        completed = p.get('completed_qty', 0)
        required = p.get('required_qty', 0)
        print(f"     - {p.get('process_name')}: {completed}/{required}")

    total_before = data1.get('total_completed_qty', 0)
    total_after = data2.get('total_completed_qty', 0)

    print(f"\n4. 结果对比:")
    print(f"   报工前总完成: {total_before}")
    print(f"   报工后总完成: {total_after}")
    print(f"   变化: {total_after - total_before}")

    if total_after > total_before:
        print(f"\n✅ 进度已更新!")
    else:
        print(f"\n❌ 进度未更新!")
        print(f"   可能原因:")
        print(f"   1. 报工数据没有写入数据库")
        print(f"   2. 查询 API 没有正确读取数据")
        print(f"   3. 数据库文件路径不一致")

except Exception as e:
    print(f"   查询失败: {e}")
    import traceback
    traceback.print_exc()
