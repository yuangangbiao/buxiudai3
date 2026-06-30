# -*- coding: utf-8 -*-
"""
主窗口 - 应用入口（懒加载优化版）
"""
import logging
import tkinter as tk
from tkinter import ttk, messagebox
import os, json, subprocess, threading, time, webbrowser

logger = logging.getLogger(__name__)

from config import COLORS, FONTS, APP_NAME, WINDOW_SIZES, WINDOW
from models.database import init_db

WINDOW_CONFIG_FILE = os.path.join(os.path.dirname(__file__), "..", "window_config.json")

from steel_belt_tracking import setup_styles

# 注意：视图模块采用懒加载，在首次访问Tab时才导入
# 这是为了加快程序启动速度


class MainWindow:
    """主窗口"""

    def __init__(self):
        # 初始化数据库
        init_db()

        # 确保数据库唯一约束索引和性能索引存在
        from models.database import ensure_unique_indexes, ensure_performance_indexes
        ensure_unique_indexes()
        ensure_performance_indexes()

        # 创建主窗口
        self.root = tk.Tk()
        self.root.title(APP_NAME)

        # 使用窗口管理器，支持调整大小
        from utils.window_manager import setup_resizable_window
        setup_resizable_window(self.root, "main_window", f"{WINDOW['width']}x{WINDOW['height']}")

        # 初始化样式
        setup_styles()

        # 设置主题色
        self.root.configure(bg=COLORS["bg_main"])

        self.setup_ui()

        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)

        # 启动后显示预警弹窗
        self.root.after(500, self._check_alerts)

    def run(self):
        """运行主窗口"""
        self.root.mainloop()

    def setup_ui(self):
        """构建UI"""
        # 顶部标题栏
        self.create_title_bar()

        # 左侧导航栏
        self.create_sidebar()

        # 右侧内容区
        self.content_area = tk.Frame(self.root, bg=COLORS["bg_main"])
        self.content_area.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # 将主窗口方法绑定到 root，方便子视图调用
        self.root.show_module = lambda m: self.show_module(m)
        self.root.main_window = self

        # 默认显示订单管理（使用后台线程加载，避免阻塞界面显示）
        self._default_module_loaded = False
        self.root.after(100, self._load_default_module)

    def create_title_bar(self):
        """标题栏"""
        title_bar = tk.Frame(self.root, bg=COLORS["primary"], height=48)
        title_bar.pack(fill=tk.X)
        title_bar.pack_propagate(False)

        tk.Label(title_bar, text="🏭", font=("Segoe UI Emoji", 18), bg=COLORS["primary"],
                fg="white").pack(side=tk.LEFT, padx=15)
        tk.Label(title_bar, text=APP_NAME, font=FONTS["title"], bg=COLORS["primary"],
                fg="white").pack(side=tk.LEFT, pady=12)

        ttk.Button(title_bar, text="退出", command=self.on_exit,
                  style="Title.TButton").pack(side=tk.RIGHT, padx=15)

    def create_sidebar(self):
        """左侧导航"""
        sidebar = tk.Frame(self.root, bg=COLORS["bg_sidebar"], width=200)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        self.nav_buttons = {}
        modules = [
            ("📝", "订单管理", "orders"),
            ("🔍", "订单查询", "order_query"),
            ("🏭", "生产排单", "production"),
            ("📋", "材料备料", "material_prep"),
            ("🔧", "工序追踪", "process"),
            ("✅", "质检管理", "quality"),
            ("🚚", "发货管理", "shipment"),
            ("📦", "成品统计", "finished_stats"),
            ("📋", "后台日志", "logs"),
            ("📦", "BOM清单", "bom"),
            ("🚨", "逾期预警", "alerts"),
            ("📊", "数据导入导出", "excel"),
            ("📋", "看板", "dashboard"),
            ("👤", "操作员管理", "operators"),
            ("📦", "库存管理", "inventory"),
            ("⚙️", "系统设置", "settings"),
        ]

        tk.Label(sidebar, text="📌 业务流程导航", font=("微软雅黑", 10, "bold"),
                bg=COLORS["bg_sidebar"], fg="#FFD700", pady=10).pack()

        flow_label = tk.Label(sidebar, text="订单 → 排产 → 备料 → 工序 → 质检 → 发货",
                            font=("微软雅黑", 8), bg=COLORS["bg_sidebar"], fg="#888888")
        flow_label.pack(pady=(0, 10))

        tk.Label(sidebar, text="功能导航", font=FONTS["subtitle"], bg=COLORS["bg_sidebar"],
                fg="#AAAAAA", pady=10).pack()

        for icon, name, mod_id in modules:
            btn = tk.Button(
                sidebar, text=f"{icon} {name}",
                font=FONTS["body"], bg=COLORS["bg_sidebar"], fg="white",
                activebackground=COLORS["accent"], activeforeground="white",
                bd=0, anchor="w", padx=20, pady=6, cursor="hand2",
                command=lambda m=mod_id: self.show_module(m)
            )
            btn.pack(fill=tk.X, padx=0, pady=0)
            self.nav_buttons[mod_id] = btn

        from core.app import get_version
        ver_frame = tk.Frame(sidebar, bg="#1a2a3a")
        ver_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=0)

        tk.Label(ver_frame, text=f"v{get_version()}",
                font=("Consolas", 8), bg="#1a2a3a", fg="#666").pack(pady=(8, 2))

        update_btn = tk.Button(ver_frame, text="🔄 检查更新",
            font=("微软雅黑", 8), bg="#1a2a3a", fg="#2196F3",
            bd=0, activebackground="#1a2a3a", activeforeground="#64b5f6",
            cursor="hand2", command=self._do_check_update)
        update_btn.pack(pady=(0, 8))

    def _do_check_update(self):
        """手动检查更新"""
        try:
            from updater import check_for_updates, show_update_dialog
            result = check_for_updates()
            if result.get('has_update'):
                show_update_dialog(self.root)
            else:
                messagebox.showinfo("版本检查", f"已是最新版本 v{result.get('local_version', '?')}\n无需更新")
        except Exception as e:
            messagebox.showerror("检查更新失败", str(e))

    def _load_default_module(self):
        """后台加载默认模块（订单管理）"""
        if self._default_module_loaded:
            return
        self._default_module_loaded = True
        self.show_module("orders")

    def show_module(self, module_id: str):
        """切换模块视图（含异常保护）"""
        if hasattr(self, 'current_view') and self.current_view is not None:
            if getattr(self, '_current_module_id', None) == module_id:
                return
            self.current_view = None

        for mid, btn in self.nav_buttons.items():
            if mid == module_id:
                btn.config(bg=COLORS["accent"], fg="white")
            else:
                btn.config(bg=COLORS["bg_sidebar"], fg="white")

        for widget in self.content_area.winfo_children():
            widget.destroy()

        self._current_module_id = module_id

        try:
            if module_id == "orders":
                from desktop.views.order_view import OrderListView
                self.current_view = OrderListView(
                    self.content_area,
                    on_order_saved=lambda: self.show_module("orders")
                )
            elif module_id == "order_query":
                from desktop.views.order_query_view import OrderQueryView
                self.current_view = OrderQueryView(self.content_area)
            elif module_id == "production":
                from desktop.views.production_view import ProductionView
                self.current_view = ProductionView(self.content_area)
            elif module_id == "material_prep":
                from desktop.views.material_prep_view import MaterialPrepView
                self.current_view = MaterialPrepView(self.content_area)
            elif module_id == "process":
                from desktop.views.process_view import ProcessView
                self.current_view = ProcessView(self.content_area)
            elif module_id == "quality":
                from desktop.views.quality_view import QualityView
                self.current_view = QualityView(self.content_area)
            elif module_id == "shipment":
                from desktop.views.shipment_view import ShipmentView
                self.current_view = ShipmentView(self.content_area)
            elif module_id == "finished_stats":
                from desktop.views.finished_product_stats_view import FinishedProductStatsView
                self.current_view = FinishedProductStatsView(self.content_area)
            elif module_id == "logs":
                from desktop.views.log_view import LogView
                self.current_view = LogView(self.content_area)
            elif module_id == "bom":
                from desktop.views.bom_view import BOMView
                self.current_view = BOMView(self.content_area)
            elif module_id == "alerts":
                from desktop.views.alert_view import AlertView, show_alert_popup
                self.current_view = AlertView(self.content_area)
            elif module_id == "excel":
                from desktop.views.excel_view import ExcelView
                self.current_view = ExcelView(self.content_area, refresh_callback=lambda: self.show_module("orders"))
            elif module_id == "operators":
                from desktop.views.operator_view import OperatorManagerView
                self.current_view = OperatorManagerView(self.content_area)
            elif module_id == "settings":
                from desktop.views.settings_dialog import show_settings_dialog
                show_settings_dialog(self.root)
                return
            elif module_id == "dashboard":
                from desktop.views.kanban_view import KanbanView
                self.current_view = KanbanView(self.content_area)
            elif module_id == "inventory":
                from desktop.views.inventory_view import InventoryView
                self.current_view = InventoryView(self.content_area)
            else:
                tk.Label(self.content_area, text="开发中...", font=FONTS["title"],
                        bg=COLORS["bg_main"]).pack()

            if self.current_view is not None:
                self.current_view.pack(fill=tk.BOTH, expand=True)
        except Exception as e:
            logger.error(f"加载模块 [{module_id}] 失败: {e}", exc_info=True)
            tk.Label(self.content_area, text=f"⚠ 加载失败: {e}\n请查看日志了解详情",
                     font=FONTS["body"], fg="#F44336", bg=COLORS["bg_main"],
                     wraplength=500, justify="center").pack(expand=True)

    def on_order_click(self, order_id):
        """订单卡片点击事件"""
        from models.order import OrderDAO
        from desktop.views.dialogs import show_detail
        from models.production import ProductionDAO
        from models.process import ProcessDAO

        order = OrderDAO.get_by_id(order_id)
        if order:
            production = ProductionDAO.get_by_order_id(order_id)
            processes = ProcessDAO.get_by_order(order_id) if production else []
            show_detail(self.root, order, production, processes)

    def on_exit(self):
        """退出确认"""
        if messagebox.askyesno("退出确认", f"确定退出 {APP_NAME} 吗？"):
            self._save_window_size()
            self.root.destroy()

    def _load_window_size(self):
        """加载上次保存的窗口大小"""
        try:
            if os.path.exists(WINDOW_CONFIG_FILE):
                with open(WINDOW_CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    return config.get("window_size")
        except Exception as e:
            logger.warning(f"加载窗口配置失败: {e}")
        return None

    def _save_window_size(self):
        """保存窗口大小"""
        try:
            config = {}
            if os.path.exists(WINDOW_CONFIG_FILE):
                try:
                    with open(WINDOW_CONFIG_FILE, "r", encoding="utf-8") as f:
                        config = json.load(f)
                except Exception as e:
                    logger.warning(f"读取窗口配置失败: {e}")
            config["window_size"] = self.root.geometry()
            with open(WINDOW_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"保存窗口配置失败: {e}")

    def _check_alerts(self):
        """启动后检查预警"""
        try:
            from desktop.views.alert_view import show_alert_popup
            show_alert_popup(self.root, 3)
        except Exception as e:
            logger.warning(f"检查预警失败: {e}")
