# -*- coding: utf-8 -*-
"""
订单管理命令行工具
提供订单查询、删除、归档等功能
"""

import sys
import os
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from core.logger import get_logger
from core.config import ensure_dir, get_sqlite_path
from services.order_service import OrderService
from scripts.order_archive_manager import OrderArchiveManager

logger = get_logger(__name__)


def print_header(title):
    """打印标题"""
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)
    print()


def print_order(order, show_full=False):
    """打印订单信息"""
    order_no = order.get('order_no', '')[:20]
    customer = order.get('customer_name', '')[:15]
    product = order.get('product_type', '')[:10]
    status = order.get('status', '')[:8]
    quantity = order.get('quantity', 0)
    updated = str(order.get('updated_at', ''))[:10]

    print(f"  [{order.get('id'):3}] {order_no:20} | {customer:15} | {product:10} | {status:8} | 数量:{quantity:4} | {updated}")


def cmd_list(args):
    """列出订单"""
    include_history = getattr(args, 'history', False)

    if include_history:
        orders = OrderService.get_history_orders(limit=50)
        print_header("历史订单列表（已归档/已取消）")
    else:
        orders = OrderService.get_all_orders(limit=50, include_history=False)
        print_header("活跃订单列表")

    if not orders:
        print("  暂无订单")
        return

    print(f"  {'ID':3} | {'订单号':20} | {'客户名称':15} | {'产品类型':10} | {'状态':8} | {'数量':5} | 更新日期")
    print("  " + "-" * 90)

    for order in orders:
        print_order(order)

    print()
    print(f"  共 {len(orders)} 条订单")


def cmd_unplanned(args):
    """列出可删除的订单（未排产）"""
    print_header("可删除订单列表（未排产）")

    orders = OrderService.get_unplanned_orders()

    if not orders:
        print("  没有可删除的订单")
        return

    print(f"  {'ID':3} | {'订单号':20} | {'客户名称':15} | {'状态':8} | {'数量':5}")
    print("  " + "-" * 70)

    for order in orders:
        order_no = order.get('order_no', '')[:20]
        customer = order.get('customer_name', '')[:15]
        status = order.get('status', '')[:8]
        quantity = order.get('quantity', 0)
        print(f"  [{order.get('id'):3}] {order_no:20} | {customer:15} | {status:8} | {quantity:5}")

    print()
    print(f"  共 {len(orders)} 条可删除订单")


def cmd_archivable(args):
    """列出可归档的订单（已排产但未完成）"""
    print_header("可归档订单列表（已排产但未完成）")

    orders = OrderService.get_archivable_orders()

    if not orders:
        print("  没有可归档的订单")
        return

    print(f"  {'ID':3} | {'订单号':20} | {'客户名称':15} | {'状态':8} | {'数量':5}")
    print("  " + "-" * 70)

    for order in orders:
        order_no = order.get('order_no', '')[:20]
        customer = order.get('customer_name', '')[:15]
        status = order.get('status', '')[:8]
        quantity = order.get('quantity', 0)
        print(f"  [{order.get('id'):3}] {order_no:20} | {customer:15} | {status:8} | {quantity:5}")

    print()
    print(f"  共 {len(orders)} 条可归档订单")


def cmd_delete(args):
    """删除订单"""
    order_id = args.order_id

    print_header(f"删除订单 ID={order_id}")

    can_delete, reason = OrderService.can_delete_order(order_id)

    if not can_delete:
        print(f"  ❌ 无法删除: {reason}")
        return

    success, message = OrderService.delete_order(order_id, operator="CLI")

    if success:
        print(f"  ✅ {message}")
    else:
        print(f"  ❌ {message}")


def cmd_batch_delete(args):
    """批量删除未排产订单"""
    print_header("批量删除未排产订单")

    orders = OrderService.get_unplanned_orders()

    if not orders:
        print("  没有可删除的订单")
        return

    print(f"  将删除 {len(orders)} 条未排产订单:")
    print()

    for order in orders:
        print(f"    - {order.get('order_no')} ({order.get('customer_name')})")

    print()

    if args.force:
        confirm = True
    else:
        confirm = input("  确认删除? (y/n): ").strip().lower() == 'y'

    if confirm:
        success, failed = OrderService.batch_delete_unplanned(operator="CLI")
        print()
        print(f"  ✅ 成功删除 {success} 条")
        if failed > 0:
            print(f"  ❌ 删除失败 {failed} 条")
    else:
        print("  已取消")


def cmd_archive(args):
    """归档订单"""
    order_id = args.order_id
    reason = getattr(args, 'reason', 'manual')

    print_header(f"归档订单 ID={order_id}")

    order = OrderService.get_order_by_id(order_id)
    if not order:
        print(f"  ❌ 订单不存在")
        return

    print(f"  订单号: {order.get('order_no')}")
    print(f"  客户: {order.get('customer_name')}")
    print(f"  状态: {order.get('status')}")
    print()

    success, message = OrderService.archive_order(order_id, reason=reason, operator="CLI")

    if success:
        print(f"  ✅ {message}")
    else:
        print(f"  ❌ {message}")


def cmd_batch_archive(args):
    """批量归档已排产但未完成订单"""
    print_header("批量归档已排产但未完成订单")

    orders = OrderService.get_archivable_orders()

    if not orders:
        print("  没有可归档的订单")
        return

    print(f"  将归档 {len(orders)} 条已排产但未完成订单:")
    print()

    for order in orders:
        order_no = order.get('order_no', '')[:20]
        customer = order.get('customer_name', '')[:15]
        status = order.get('status', '')[:8]
        print(f"    - {order_no} ({customer}) - {status}")

    print()

    reason = getattr(args, 'reason', 'batch_archive')

    if args.force:
        confirm = True
    else:
        confirm = input("  确认归档? (y/n): ").strip().lower() == 'y'

    if confirm:
        success, failed = OrderService.batch_archive_completed(reason=reason, operator="CLI")
        print()
        print(f"  ✅ 成功归档 {success} 条")
        if failed > 0:
            print(f"  ❌ 归档失败 {failed} 条")
    else:
        print("  已取消")


def cmd_archive_list(args):
    """列出归档记录"""
    print_header("归档记录列表")

    archive_mgr = OrderArchiveManager()
    archives = archive_mgr.get_archive_list(limit=50)

    if not archives:
        print("  暂无归档记录")
        return

    print(f"  {'ID':3} | {'订单号':20} | {'客户名称':15} | {'原状态':8} | {'归档时间':10} | {'原因':10}")
    print("  " + "-" * 90)

    for a in archives:
        archived_at = str(a.get('archived_at', ''))[:10]
        print(f"  [{a.get('id'):3}] {a.get('order_no', ''):20} | {a.get('customer_name', '')[:15]:15} | {a.get('status', ''):8} | {archived_at} | {a.get('archive_reason', ''):10}")

    print()
    print(f"  共 {len(archives)} 条归档记录")


def cmd_stats(args):
    """显示统计信息"""
    print_header("订单统计信息")

    active_count = OrderService.get_order_count(include_history=False)
    history_count = OrderService.get_order_count(include_history=True)

    unplanned = OrderService.get_unplanned_orders()
    archivable = OrderService.get_archivable_orders()

    archive_mgr = OrderArchiveManager()
    archive_count = archive_mgr.get_archive_count()

    print(f"  活跃订单: {active_count}")
    print(f"  历史订单: {history_count - active_count}")
    print(f"  未排产订单（可删除）: {len(unplanned)}")
    print(f"  已排产未完成（可归档）: {len(archivable)}")
    print(f"  归档记录数: {archive_count}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description='订单管理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='子命令')

    parser_list = subparsers.add_parser('list', help='列出活跃订单')
    parser_list.add_argument('--history', action='store_true', help='包含历史订单')

    subparsers.add_parser('unplanned', help='列出可删除订单（未排产）')

    subparsers.add_parser('archivable', help='列出可归档订单（已排产但未完成）')

    parser_delete = subparsers.add_parser('delete', help='删除订单')
    parser_delete.add_argument('order_id', type=int, help='订单ID')

    parser_batch_delete = subparsers.add_parser('batch-delete', help='批量删除未排产订单')
    parser_batch_delete.add_argument('--force', action='store_true', help='强制执行不询问')

    parser_archive = subparsers.add_parser('archive', help='归档订单')
    parser_archive.add_argument('order_id', type=int, help='订单ID')
    parser_archive.add_argument('--reason', default='manual', help='归档原因')

    parser_batch_archive = subparsers.add_parser('batch-archive', help='批量归档已排产但未完成订单')
    parser_batch_archive.add_argument('--force', action='store_true', help='强制执行不询问')
    parser_batch_archive.add_argument('--reason', default='batch_archive', help='归档原因')

    subparsers.add_parser('archives', help='列出归档记录')

    subparsers.add_parser('stats', help='显示统计信息')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    ensure_dir(os.path.dirname(get_sqlite_path()))

    cmd_map = {
        'list': cmd_list,
        'unplanned': cmd_unplanned,
        'archivable': cmd_archivable,
        'delete': cmd_delete,
        'batch-delete': cmd_batch_delete,
        'archive': cmd_archive,
        'batch-archive': cmd_batch_archive,
        'archives': cmd_archive_list,
        'stats': cmd_stats,
    }

    cmd = cmd_map.get(args.command)
    if cmd:
        cmd(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
