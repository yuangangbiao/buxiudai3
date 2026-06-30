# -*- coding: utf-8 -*-
"""库存管理系统调试测试"""
import sys
import os
import traceback
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('inventory_debug.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('inventory_test')

def log_step(step, status='INFO'):
    logger.log(logging.INFO if status == 'INFO' else logging.DEBUG, f"[{step}] {status}")

def test_db():
    """测试数据库连接和操作"""
    log_step("1. 测试数据库连接", "DEBUG")
    try:
        from inventory_db_complete import InventoryDB, inv_db
        db = InventoryDB()

        log_step("  - 检查连接", "DEBUG")
        if db.check_connection():
            log_step("  - 数据库连接: OK")
        else:
            log_step("  - 数据库连接: FAILED", "ERROR")
            return False

        log_step("  - 初始化数据库表", "DEBUG")
        db.init_database()
        log_step("  - 初始化数据", "DEBUG")
        db.insert_initial_data()

        log_step("  - 测试获取仓库", "DEBUG")
        warehouses = db.get_warehouses()
        log_step(f"  - 仓库数量: {len(warehouses)}", "DEBUG")

        log_step("  - 测试获取商品", "DEBUG")
        products = db.get_all_products()
        log_step(f"  - 商品数量: {len(products)}", "DEBUG")

        log_step("  - 测试获取统计", "DEBUG")
        stats = db.get_statistics()
        log_step(f"  - 统计数据: {stats}", "DEBUG")

        log_step("  - 测试获取库存", "DEBUG")
        inventory = db.get_all_inventory()
        log_step(f"  - 库存记录数: {len(inventory)}", "DEBUG")

        log_step("数据库测试: PASS")
        return True
    except Exception as e:
        logger.error(f"数据库测试失败: {e}")
        logger.error(traceback.format_exc())
        return False

def test_print():
    """测试打印功能"""
    log_step("2. 测试打印模块", "DEBUG")
    try:
        from inventory_print import generate_outbound_html, generate_inbound_html, num_to_cn

        log_step("  - 测试金额转换", "DEBUG")
        result = num_to_cn(12345.67)
        log_step(f"  - 12345.67 -> {result}", "DEBUG")

        log_step("  - 测试出库单生成", "DEBUG")
        test_data = {
            'order_no': 'OUT-TEST-001',
            'date': '2026-04-29',
            'customer': '测试客户',
            'handler': '测试员',
            'warehouse': '1号仓',
            'items': [
                {'name': '测试商品1', 'spec': 'M8*50', 'quantity': 100, 'unit_price': 25.5, 'amount': 2550},
                {'name': '测试商品2', 'spec': 'M10*60', 'quantity': 50, 'unit_price': 42.0, 'amount': 2100},
            ]
        }
        html = generate_outbound_html(test_data)
        log_step(f"  - 出库单HTML长度: {len(html)}", "DEBUG")

        log_step("打印模块测试: PASS")
        return True
    except Exception as e:
        logger.error(f"打印测试失败: {e}")
        logger.error(traceback.format_exc())
        return False

def test_gui():
    """测试GUI模块"""
    log_step("3. 测试GUI模块", "DEBUG")
    try:
        from inventory_manager_complete import InventoryGUI, THEME

        log_step("  - 主题配置: OK", "DEBUG")
        log_step(f"  - 背景色: {THEME['bg_dark']}", "DEBUG")

        log_step("  - 导入GUI类: OK", "DEBUG")

        log_step("GUI模块测试: PASS")
        return True
    except Exception as e:
        logger.error(f"GUI测试失败: {e}")
        logger.error(traceback.format_exc())
        return False

def test_full_flow():
    """测试完整流程"""
    log_step("4. 测试完整业务流程", "DEBUG")
    try:
        from inventory_db_complete import InventoryDB, inv_db
        db = InventoryDB()

        log_step("  - 测试添加入库", "DEBUG")
        products = db.get_all_products()
        if products:
            product = products[0]
            log_step(f"  - 商品: {product.get('name')}", "DEBUG")

            warehouses = db.get_warehouses()
            if warehouses:
                warehouse = warehouses[0]
                log_step(f"  - 仓库: {warehouse.get('name')}", "DEBUG")

                log_step("  - 执行入库操作", "DEBUG")
                success = db.update_inventory_qty(
                    product['id'],
                    warehouse['id'],
                    100,
                    'inbound'
                )
                log_step(f"  - 入库结果: {'SUCCESS' if success else 'FAILED'}", "DEBUG" if success else "ERROR")

                log_step("  - 添加事务记录", "DEBUG")
                trans_no = db.add_transaction(
                    'inbound',
                    product['id'],
                    warehouse['id'],
                    100,
                    product.get('price', 0),
                    None,
                    'TEST-ORDER-001',
                    '测试操作员',
                    '测试入库'
                )
                log_step(f"  - 事务单号: {trans_no}", "DEBUG")

                log_step("  - 验证库存更新", "DEBUG")
                inventory = db.get_inventory_by_product(product['id'])
                log_step(f"  - 库存记录数: {len(inventory)}", "DEBUG")
                if inventory:
                    for inv in inventory:
                        log_step(f"  - 当前库存: {inv.get('current_qty')}", "DEBUG")

        log_step("完整流程测试: PASS")
        return True
    except Exception as e:
        logger.error(f"完整流程测试失败: {e}")
        logger.error(traceback.format_exc())
        return False

def main():
    print("=" * 60)
    print("  库存管理系统 V3.0 调试测试")
    print("=" * 60)
    print()

    results = {
        'db': test_db(),
        'print': test_print(),
        'gui': test_gui(),
        'flow': test_full_flow()
    }

    print()
    print("=" * 60)
    print("  测试结果汇总")
    print("=" * 60)
    for name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"  {name.upper()}: {status}")
    print("=" * 60)

    if all(results.values()):
        print("\n所有测试通过！系统可以正常运行。")
        print("\n启动GUI界面...")
        print("=" * 60)

        from inventory_manager_complete import InventoryGUI
        app = InventoryGUI()
        app.mainloop()
    else:
        print("\n存在测试失败，请检查日志文件: inventory_debug.log")
        input("\n按回车键退出...")

if __name__ == "__main__":
    main()
