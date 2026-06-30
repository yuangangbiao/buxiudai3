
# -*- coding: utf-8 -*-
"""
测试商品搜索功能
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from inventory_db_complete import inv_db

def test_products():
    print("=== 测试商品数据 ===\n")
    products = inv_db.get_all_products()
    print(f"商品数量: {len(products)}")
    if products:
        print("\n商品列表:")
        for i, p in enumerate(products, 1):
            name = p.get('name', '')
            spec = p.get('spec', '')
            price = float(p.get('price', 0) or 0)
            stock = inv_db.get_product_stock(p['id'])
            print(f"  {i}. 名称: {name} | 规格: {spec} | 库存: {stock:.0f} | 单价: ¥{price:.2f}")
    else:
        print("\n❌ 没有商品数据！")
    return products

def test_filter():
    print("\n\n=== 测试过滤功能 ===\n")
    products = test_products()
    if not products:
        return
    
    test_keywords = ['', '不锈钢', '螺栓', '弹垫', 'M8']
    for keyword in test_keywords:
        print(f"\n搜索关键词: '{keyword}'")
        found = 0
        for p in products:
            name = p.get('name', '')
            spec = p.get('spec', '')
            if keyword.lower() in name.lower() or keyword.lower() in spec.lower():
                found += 1
                print(f"  ✅ {name} | {spec}")
        print(f"找到: {found} 个商品")

if __name__ == "__main__":
    test_filter()
