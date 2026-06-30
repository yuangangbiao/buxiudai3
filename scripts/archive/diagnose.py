# -*- coding: utf-8 -*-
"""诊断工单创建问题"""

import sys
import os

project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

print("="*60)
print("工单创建问题诊断")
print("="*60)

# 1. 检查 production.py 文件内容
print("\n[1] 检查 production.py 导入...")
prod_file = os.path.join(project_dir, "models", "production.py")
with open(prod_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()[:15]
    
has_generate_import = False
has_log_import = False

for i, line in enumerate(lines, 1):
    if 'generate_work_order_no' in line:
        has_generate_import = True
        print(f"✓ 第{i}行: {line.strip()}")
    if 'from utils.op_logger import' in line:
        has_log_import = True
        
if not has_generate_import:
    print("✗ 缺少 generate_work_order_no 导入!")
if not has_log_import:
    print("✗ 缺少 op_logger 导入!")

# 2. 检查函数是否存在
print("\n[2] 检查 database.py 中的函数...")
db_file = os.path.join(project_dir, "models", "database.py")
with open(db_file, 'r', encoding='utf-8') as f:
    content = f.read()
    
if 'def generate_work_order_no():' in content:
    print("✓ generate_work_order_no 函数存在")
else:
    print("✗ generate_work_order_no 函数不存在")

# 3. 尝试实际导入
print("\n[3] 测试实际导入...")
try:
    from models.database import generate_work_order_no
    print("✓ 导入成功")
except Exception as e:
    print(f"✗ 导入失败: {e}")

print("\n" + "="*60)
print("诊断完成")
print("="*60)
