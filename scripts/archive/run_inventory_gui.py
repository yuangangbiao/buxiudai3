# -*- coding: utf-8 -*-
"""检查MySQL库存系统GUI是否运行"""
import os
import sys

sys.path.insert(0, r'd:\yuan\不锈钢网带跟单3.0')

try:
    import tkinter as tk
    from inventory_manager_gui import InventoryGUI
    import threading

    def run_gui():
        root = tk.Tk()
        app = InventoryGUI()
        root.mainloop()

    print("=" * 60)
    print("  库存管理系统 MySQL版 - 启动中...")
    print("=" * 60)
    print("  窗口将自动打开")
    print("  关闭窗口即可退出程序")
    print("=" * 60)

    run_gui()

except ImportError as e:
    print(f"[ERROR] 导入失败: {e}")
    input("按回车键退出...")
except Exception as e:
    print(f"[ERROR] 运行失败: {e}")
    import traceback
    traceback.print_exc()
    input("按回车键退出...")
