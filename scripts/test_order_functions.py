# -*- coding: utf-8 -*-
"""
订单功能测试脚本
测试订单删除和归档功能
验证订单管理的业务逻辑
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.order_service import OrderService
from scripts.order_archive_manager import OrderArchiveManager

print("=" * 60)
print("订单数据验证（新逻辑）")
print("=" * 60)
print()

# 查看活跃订单（默认，排除归档/取消）
orders = OrderService.get_all_orders()
print(f"活跃订单总数: {len(orders)}")
print()
print("订单列表（默认，只显示活跃订单）:")
print("-" * 80)
for o in orders[:5]:
    order_no = o.get("order_no", "")[:15]
    customer = o.get("customer_name", "")[:10]
    status = o.get("status", "")[:6]
    print(f"ID: {o.get('id'):3} | 订单号: {order_no:15} | 客户: {customer:10} | 状态: {status}")
if len(orders) > 5:
    print("...")
print()

# 查看未排产订单（可删除）
unplanned = OrderService.get_unplanned_orders()
print(f"未排产订单（可删除）: {len(unplanned)}")
print()

# 查看可归档订单（已排产但未完成）
archivable = OrderService.get_archivable_orders()
print(f"已排产未完成订单（可归档）: {len(archivable)}")
print()

# 归档表
archive_mgr = OrderArchiveManager()
archive_count = archive_mgr.get_archive_count()
print(f"归档表记录数: {archive_count}")
print()

print("=" * 60)
print("业务逻辑说明")
print("=" * 60)
print("1. 未排产订单 -> 可直接删除")
print("2. 已排产但未完成 -> 可归档（订单+生产工单一起归档）")
print("3. 归档/取消订单 -> 只在历史查询中出现")
print("4. 订单管理界面默认不显示历史订单")
print("=" * 60)
print("测试完成")
print("=" * 60)
