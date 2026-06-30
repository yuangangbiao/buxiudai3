# -*- coding: utf-8 -*-
"""测试 generate_work_order_no 导入"""

import sys
import os

project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

try:
    print("测试导入 generate_work_order_no...")
    from models.database import get_connection, generate_work_order_no
    print("✓ 导入成功!")
    
    print("\n测试调用函数...")
    # 不实际连接数据库，只是验证函数存在
    print(f"函数类型: {type(generate_work_order_no)}")
    print(f"函数名: {generate_work_order_no.__name__}")
    
    print("\n✓ 所有测试通过!")
    
except Exception as e:
    print(f"\n✗ 错误: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
