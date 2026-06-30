# -*- coding: utf-8 -*-
"""完整测试工单创建流程"""

import sys
import os

project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

print("="*60)
print("完整工单创建测试")
print("="*60)

# 1. 测试数据库连接
print("\n[1] 测试数据库连接...")
try:
    from models.database import get_connection
    conn = get_connection()
    print("✓ 数据库连接成功")
    conn.close()
except Exception as e:
    print(f"✗ 数据库连接失败: {e}")
    sys.exit(1)

# 2. 测试生成订单号
print("\n[2] 测试生成订单号...")
try:
    from models.database import generate_work_order_no
    work_order_no = generate_work_order_no()
    print(f"✓ 生成订单号成功: {work_order_no}")
except Exception as e:
    print(f"✗ 生成订单号失败: {e}")
    import traceback
    traceback.print_exc()

# 3. 测试完整的工单创建流程
print("\n[3] 测试工单创建...")
try:
    from models.production import ProductionDAO
    
    # 测试用的订单ID（需要确保存在一个已确认的订单）
    test_order_id = 1
    
    result = ProductionDAO.create(test_order_id, {
        "priority": 5,
        "remark": "测试工单"
    })
    print(f"✓ 工单创建成功，ID: {result}")
    
except Exception as e:
    print(f"✗ 工单创建失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("测试完成")
print("="*60)
