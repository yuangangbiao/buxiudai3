# -*- coding: utf-8 -*-
"""测试库存管理系统启动"""
import sys
import os

print("=" * 60)
print("  库存管理系统 V3.0 启动测试")
print("=" * 60)
print()

try:
    print("[1/6] 导入pymysql...")
    import pymysql
    print("    OK")

    print("[2/6] 导入tkinter...")
    import tkinter as tk
    print("    OK")

    print("[3/6] 导入数据库模块...")
    from inventory_db_complete import InventoryDB, inv_db
    print("    OK")

    print("[4/6] 导入打印模块...")
    from inventory_print import print_outbound, print_inbound, print_inventory_report
    print("    OK")

    print("[5/6] 初始化数据库...")
    db = InventoryDB()
    db.init_database()
    db.insert_initial_data()
    print("    OK")

    print("[6/6] 导入GUI模块...")
    from inventory_manager_complete import InventoryGUI
    print("    OK")

    print()
    print("=" * 60)
    print("  所有模块加载成功!")
    print("=" * 60)
    print()
    print("  启动GUI界面...")
    print()

    app = InventoryGUI()
    app.mainloop()

    print()
    print("程序已退出")

except ImportError as e:
    print(f"\n[ERROR] 模块导入失败: {e}")
    import traceback
    traceback.print_exc()
    input("\n按回车键退出...")

except Exception as e:
    print(f"\n[ERROR] 运行错误: {e}")
    import traceback
    traceback.print_exc()
    input("\n按回车键退出...")
