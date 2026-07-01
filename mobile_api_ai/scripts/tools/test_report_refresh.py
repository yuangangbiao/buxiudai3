"""通过 API 测试报工进度是否刷新"""
import urllib.request
import json
import sys

BASE = 'http://localhost:5008'

def eprint(*args, **kwargs):
    print(*args, **kwargs, flush=True)

def main():
    if len(sys.argv) < 2:
        print("用法: python test_report_refresh.py <订单号>")
        print("示例: python test_report_refresh.py ORD-202604210003")
        sys.exit(1)

    order_no = sys.argv[1]

    eprint("=" * 60)
    eprint(f"测试报工进度刷新 - 订单: {order_no}")
    eprint("=" * 60)

    try:
        resp = urllib.request.urlopen(f'{BASE}/api/scan-info?code={order_no}', timeout=5)
        data = json.loads(resp.read().decode('utf-8'))

        if data.get('code') != 0:
            eprint(f"\n❌ API 返回错误: {data.get('message')}")
            sys.exit(1)

        order = data.get('data', {})
        eprint(f"\n✅ API 查询成功")
        eprint(f"   工单号: {order.get('order_no')}")
        eprint(f"   产品: {order.get('product_name')}")
        eprint(f"   总数量: {order.get('quantity')}")
        eprint(f"   总完成: {order.get('total_completed_qty')}")

        eprint(f"\n   工序进度:")
        for p in order.get('processes', []):
            completed = p.get('completed_qty', 0)
            required = p.get('required_qty', 0)
            eprint(f"     - {p.get('step_name')}: {completed}/{required}")

        total = order.get('total_completed_qty', 0)
        if total > 0:
            eprint(f"\n✅ 数据库中有报工数据 (total_completed_qty={total})")
        else:
            eprint(f"\n⚠️  数据库中没有报工数据 (total_completed_qty=0)")
            eprint(f"   可能原因:")
            eprint(f"   1. 报工数据写入到其他数据库文件")
            eprint(f"   2. 数据库路径配置不一致")

    except Exception as e:
        eprint(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
