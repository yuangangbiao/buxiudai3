# -*- coding: utf-8 -*-
"""批量打印测试脚本"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from inventory_db_complete import inv_db
from inventory_print import print_inbound, print_outbound, generate_inbound_html, generate_outbound_html
from datetime import date

def test_batch_inbound_print():
    """测试批量入库打印"""
    print("=" * 50)
    print("  测试批量入库打印功能")
    print("=" * 50)

    # 获取产品和仓库
    products = inv_db.get_all_products()
    warehouses = inv_db.get_warehouses()

    if not products:
        print("错误: 没有产品数据")
        return False

    if not warehouses:
        print("错误: 没有仓库数据")
        return False

    # 模拟批量入库数据
    items = []
    for p in products[:3]:  # 只取前3个产品
        items.append({
            "name": p.get('name', ''),
            "spec": p.get('spec', ''),
            "qty": 100,
            "unit_price": float(p.get('price', 0)),
            "unit": p.get('unit', '件'),
            "supplier": "测试供应商"
        })

    trans_nos = ['RK-2026-TEST-001', 'RK-2026-TEST-002']

    # 构建打印数据
    data = {
        "order_no": ", ".join(trans_nos),
        "date": date.today().strftime("%Y-%m-%d"),
        "handler": "测试员",
        "warehouse": warehouses[0].get('name', '1号仓'),
        "remark": "批量打印测试",
        "operator": "测试操作员",
        "contact": "联系人",
        "phone": "13800138000",
        "items": items
    }

    print(f"\n打印数据:")
    print(f"  单号: {data['order_no']}")
    print(f"  日期: {data['date']}")
    print(f"  仓库: {data['warehouse']}")
    print(f"  商品数量: {len(items)}")

    # 生成HTML测试
    print("\n生成HTML...")
    try:
        html = generate_inbound_html(data)
        print(f"  HTML长度: {len(html)} 字节")
        print("  [OK] HTML生成成功")
    except Exception as e:
        print(f"  [ERROR] HTML生成失败: {e}")
        return False

    # 执行打印测试
    print("\n执行打印...")
    try:
        result = print_inbound(data)
        if result:
            print("  [OK] 打印功能执行成功")
            print("  提示: 如果有默认打印机，打印机应该正在打印")
            return True
        else:
            print("  [ERROR] 打印功能返回失败")
            return False
    except Exception as e:
        print(f"  [ERROR] 打印执行异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_batch_outbound_print():
    """测试批量出库打印"""
    print("\n" + "=" * 50)
    print("  测试批量出库打印功能")
    print("=" * 50)

    products = inv_db.get_all_products()
    warehouses = inv_db.get_warehouses()

    if not products:
        print("错误: 没有产品数据")
        return False

    items = []
    for p in products[:3]:
        items.append({
            "name": p.get('name', ''),
            "spec": p.get('spec', ''),
            "qty": 50,
            "unit_price": float(p.get('price', 0)),
            "unit": p.get('unit', '件')
        })

    trans_nos = ['CK-2026-TEST-001', 'CK-2026-TEST-002']

    data = {
        "order_no": ", ".join(trans_nos),
        "date": date.today().strftime("%Y-%m-%d"),
        "customer": "测试客户",
        "handler": "测试员",
        "warehouse": warehouses[0].get('name', '1号仓') if warehouses else '1号仓',
        "remark": "批量出库打印测试",
        "operator": "测试操作员",
        "contact": "联系人",
        "phone": "13800138000",
        "items": items
    }

    print(f"\n打印数据:")
    print(f"  单号: {data['order_no']}")
    print(f"  客户: {data['customer']}")
    print(f"  商品数量: {len(items)}")

    try:
        html = generate_outbound_html(data)
        print(f"  HTML长度: {len(html)} 字节")
        print("  [OK] HTML生成成功")
    except Exception as e:
        print(f"  [ERROR] HTML生成失败: {e}")
        return False

    try:
        result = print_outbound(data)
        if result:
            print("  [OK] 打印功能执行成功")
            return True
        else:
            print("  [ERROR] 打印功能返回失败")
            return False
    except Exception as e:
        print(f"  [ERROR] 打印执行异常: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("  库存管理系统 - 批量打印功能测试")
    print("=" * 60)

    # 测试入库打印
    inbound_ok = test_batch_inbound_print()

    # 测试出库打印
    outbound_ok = test_batch_outbound_print()

    print("\n" + "=" * 60)
    print("  测试结果汇总")
    print("=" * 60)
    print(f"  批量入库打印: {'[OK] 通过' if inbound_ok else '[ERROR] 失败'}")
    print(f"  批量出库打印: {'[OK] 通过' if outbound_ok else '[ERROR] 失败'}")

    if inbound_ok and outbound_ok:
        print("\n所有测试通过！打印功能正常。")
    else:
        print("\n存在测试失败，请检查上述错误信息。")
