# -*- coding: utf-8 -*-
"""
逾期预警视图
"""
import tkinter as tk
from tkinter import ttk
from datetime import datetime
from config import COLORS, FONTS
from models.alert import AlertDAO
from desktop.views.dialogs import alert


def _format_date(val):
    """安全格式化日期，处理datetime对象或字符串"""
    if hasattr(val, 'strftime'):
        return val.strftime('%Y-%m-%d')
    elif val:
        return str(val)[:10]
    return "-"


class AlertView(tk.Frame):
    """逾期预警视图"""

    def __init__(self, parent, warning_days: int = 3):
        super().__init__(parent, bg=COLORS["bg_main"])
        self.warning_days = warning_days
        self.init_ui()
        self.load_data()

    def init_ui(self):
        # 工具栏
        toolbar = tk.Frame(self, bg="#FFFFFF", height=50)
        toolbar.pack(fill=tk.X, side=tk.TOP)
        toolbar.pack_propagate(False)

        tk.Label(toolbar, text="🚨 逾期预警中心", font=FONTS["large"], bg="#FFFFFF",
                fg="#D32F2F").pack(side=tk.LEFT, padx=15, pady=10)

        # 统计标签
        self.stats_label = tk.Label(toolbar, text="", font=FONTS["body"], bg="#FFFFFF", fg="#666666")
        self.stats_label.pack(side=tk.LEFT, padx=20)

        ttk.Button(toolbar, text="🔄 刷新", command=self.load_data).pack(side=tk.RIGHT, padx=10)
        ttk.Button(toolbar, text="⚙️ 设置", command=self._show_settings).pack(side=tk.RIGHT, padx=5)

        # 预警天数设置
        setting_frame = tk.Frame(toolbar, bg="#FFFFFF")
        setting_frame.pack(side=tk.RIGHT, padx=10)
        tk.Label(setting_frame, text="提前预警:", font=FONTS["body"], bg="#FFFFFF").pack(side=tk.LEFT, padx=5)
        self.days_spin = tk.Spinbox(setting_frame, from_=1, to=30, width=5, font=FONTS["body"])
        self.days_spin.delete(0, tk.END)
        self.days_spin.insert(0, self.warning_days)
        self.days_spin.pack(side=tk.LEFT, padx=5)
        tk.Label(setting_frame, text="天", font=FONTS["body"], bg="#FFFFFF").pack(side=tk.LEFT)
        self.days_spin.bind("<ButtonRelease-1>", lambda e: self._update_warning_days())

        # 预警内容区
        content = tk.Frame(self, bg=COLORS["bg_main"])
        content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 左侧：逾期订单
        left_frame = tk.Frame(content, bg="#FFFFFF", relief=tk.RIDGE, bd=1)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        tk.Label(left_frame, text="🔴 逾期订单", font=FONTS["subtitle"], bg="#FFEBEE",
                fg="#D32F2F", pady=8).pack(fill=tk.X)
        
        # 逾期订单表格
        overdue_frame = tk.Frame(left_frame, bg="#FFFFFF")
        overdue_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        cols = ("order_no", "customer", "delivery_date", "overdue_days", "status")
        self.overdue_tree = ttk.Treeview(overdue_frame, columns=cols, show="headings", height=8)
        
        for col, txt, w in [
            ("order_no", "订单号", 120), ("customer", "客户", 100),
            ("delivery_date", "交货日期", 100), ("overdue_days", "逾期天数", 80), ("status", "状态", 80)
        ]:
            self.overdue_tree.heading(col, text=txt)
            self.overdue_tree.column(col, width=w, anchor="center")
        
        self.overdue_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ttk.Scrollbar(overdue_frame, orient=tk.VERTICAL, command=self.overdue_tree.yview).pack(side=tk.RIGHT, fill=tk.Y)

        # 右侧：预警订单
        right_frame = tk.Frame(content, bg="#FFFFFF", relief=tk.RIDGE, bd=1)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        tk.Label(right_frame, text="🟡 即将到期", font=FONTS["subtitle"], bg="#FFF8E1",
                fg="#F57C00", pady=8).pack(fill=tk.X)
        
        # 预警订单表格
        warning_frame = tk.Frame(right_frame, bg="#FFFFFF")
        warning_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        cols = ("order_no", "customer", "delivery_date", "remain_days", "status")
        self.warning_tree = ttk.Treeview(warning_frame, columns=cols, show="headings", height=8)
        
        for col, txt, w in [
            ("order_no", "订单号", 120), ("customer", "客户", 100),
            ("delivery_date", "交货日期", 100), ("remain_days", "剩余天数", 80), ("status", "状态", 80)
        ]:
            self.warning_tree.heading(col, text=txt)
            self.warning_tree.column(col, width=w, anchor="center")
        
        self.warning_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ttk.Scrollbar(warning_frame, orient=tk.VERTICAL, command=self.warning_tree.yview).pack(side=tk.RIGHT, fill=tk.Y)

        # 底部：库存预警
        bottom_frame = tk.Frame(self, bg="#FFFFFF", relief=tk.RIDGE, bd=1)
        bottom_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        tk.Label(bottom_frame, text="🟠 库存预警", font=FONTS["subtitle"], bg="#FFF3E0",
                fg="#E65100", pady=8).pack(fill=tk.X)
        
        # 库存预警表格
        inventory_frame = tk.Frame(bottom_frame, bg="#FFFFFF")
        inventory_frame.pack(fill=tk.X, padx=10, pady=5)
        
        cols = ("name", "type", "qty", "warning_qty", "level")
        self.inventory_tree = ttk.Treeview(inventory_frame, columns=cols, show="headings", height=5)
        
        for col, txt, w in [
            ("name", "材料名称", 150), ("type", "类型", 100),
            ("qty", "当前库存", 100), ("warning_qty", "预警线", 100), ("level", "预警等级", 100)
        ]:
            self.inventory_tree.heading(col, text=txt)
            self.inventory_tree.column(col, width=w, anchor="center")
        
        self.inventory_tree.pack(fill=tk.X)
        ttk.Scrollbar(inventory_frame, orient=tk.HORIZONTAL, command=self.inventory_tree.xview).pack(fill=tk.X)

        # 双击事件
        self.overdue_tree.bind("<Double-1>", lambda e: self._view_order(self.overdue_tree))
        self.warning_tree.bind("<Double-1>", lambda e: self._view_order(self.warning_tree))

    def load_data(self):
        """加载预警数据"""
        # 清空表格
        for item in self.overdue_tree.get_children():
            self.overdue_tree.delete(item)
        for item in self.warning_tree.get_children():
            self.warning_tree.delete(item)
        for item in self.inventory_tree.get_children():
            self.inventory_tree.delete(item)

        # 获取预警数据
        alerts = AlertDAO.get_all_alerts(self.warning_days)
        
        # 填充逾期订单
        overdue_count = 0
        for order in alerts.get("overdue_orders", []):
            overdue_days = order.get("overdue_days", 0)
            bg_color = "#FFCDD2" if overdue_days > 7 else "#FFEBEE"
            item = self.overdue_tree.insert("", tk.END, values=(
                order.get("order_no", ""),
                order.get("customer_name", ""),
                _format_date(order.get("delivery_date")),
                f"{overdue_days}天",
                order.get("status", ""),
            ))
            overdue_count += 1

        # 填充预警订单
        warning_count = 0
        for order in alerts.get("warning_orders", []):
            remain_days = order.get("remain_days", 0)
            item = self.warning_tree.insert("", tk.END, values=(
                order.get("order_no", ""),
                order.get("customer_name", ""),
                _format_date(order.get("delivery_date")),
                f"{remain_days}天",
                order.get("status", ""),
            ))
            warning_count += 1

        # 填充库存预警
        inventory_count = 0
        for inv in alerts.get("low_inventory", []):
            level = inv.get("alert_level", "")
            level_color = "#D32F2F" if "不足" in level else "#F57C00"
            item = self.inventory_tree.insert("", tk.END, values=(
                inv.get("material_name", ""),
                inv.get("material_type", ""),
                f"{inv.get('quantity', 0):.1f} {inv.get('unit', 'kg')}",
                f"{inv.get('warning_qty', 0):.1f} {inv.get('unit', 'kg')}",
                level,
            ))
            inventory_count += 1

        # 更新统计
        total_alerts = overdue_count + warning_count + inventory_count
        self.stats_label.config(text=f"📊 逾期{overdue_count} | 预警{warning_count} | 库存{inventory_count} | 共{total_alerts}项")

    def _update_warning_days(self):
        """更新预警天数"""
        try:
            self.warning_days = int(self.days_spin.get())
            self.load_data()
        except ValueError:
            pass

    def _view_order(self, tree):
        """查看订单详情"""
        sel = tree.selection()
        if not sel:
            return
        values = tree.item(sel[0])["values"]
        order_no = values[0]
        
        from models.order import OrderDAO
        from models.production import ProductionDAO
        from models.process import ProcessDAO
        from desktop.views.dialogs import show_detail
        
        order = OrderDAO.get_by_order_no(order_no)
        if order:
            production = ProductionDAO.get_by_order_id(order["id"])
            processes = ProcessDAO.get_by_order(order["id"]) if production else []
            show_detail(self.winfo_toplevel(), order, production, processes)

    def _show_settings(self):
        """显示设置"""
        fields = [
            ("提前预警天数", "warning_days", str(self.warning_days), "number"),
        ]
        
        def on_save(data):
            try:
                self.warning_days = int(data.get("warning_days", 3))
                self.days_spin.delete(0, tk.END)
                self.days_spin.insert(0, self.warning_days)
                self.load_data()
                alert("设置已保存", "成功")
            except ValueError:
                alert("请输入有效的数字", "提示")
        
        from desktop.views.dialogs import popup_form
        popup_form("预警设置", fields, on_save, width=400)


def show_alert_popup(parent, warning_days: int = 3):
    """显示预警弹窗（启动时调用）"""
    alerts = AlertDAO.get_all_alerts(warning_days)
    overdue_count = len(alerts.get("overdue_orders", []))
    warning_count = len(alerts.get("warning_orders", []))
    inventory_count = len(alerts.get("low_inventory", []))
    total = overdue_count + warning_count + inventory_count

    if total == 0:
        return None

    win = tk.Toplevel(parent)
    win.title("⚠️ 预警提醒")
    win.geometry("500x400")
    win.transient(parent)
    win.grab_set()
    win.configure(bg="#FFFFFF")

    # 标题
    tk.Label(win, text="🚨 您有待处理的预警", font=("微软雅黑", 16, "bold"),
            bg="#FFFFFF", fg="#D32F2F").pack(pady=15)

    # 统计卡片
    stats_frame = tk.Frame(win, bg="#FFFFFF")
    stats_frame.pack(pady=10)

    cards = [
        ("🔴 逾期订单", overdue_count, "#FFEBEE", "#D32F2F"),
        ("🟡 即将到期", warning_count, "#FFF8E1", "#F57C00"),
        ("🟠 库存预警", inventory_count, "#FFF3E0", "#E65100"),
    ]
    
    for i, (title, count, bg, fg) in enumerate(cards):
        card = tk.Frame(stats_frame, bg=bg, relief=tk.RIDGE, bd=1, padx=20, pady=10)
        card.pack(side=tk.LEFT, padx=10)
        tk.Label(card, text=title, font=FONTS["small"], bg=bg, fg="#666666").pack()
        tk.Label(card, text=str(count), font=("微软雅黑", 24, "bold"), bg=bg, fg=fg).pack()

    # 预警列表
    list_frame = tk.Frame(win, bg="#FFFFFF")
    list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

    tk.Label(list_frame, text="📋 预警详情", font=FONTS["subtitle"], bg="#FFFFFF").pack(anchor="w")

    text = tk.Text(list_frame, font=FONTS["body"], height=8, relief=tk.SUNKEN, bd=1)
    text.pack(fill=tk.BOTH, expand=True, pady=5)
    scroll = ttk.Scrollbar(text, orient=tk.VERTICAL, command=text.yview)
    text.configure(yscrollcommand=scroll.set)

    # 添加预警内容
    for order in alerts.get("overdue_orders", [])[:5]:
        days = order.get("overdue_days", 0)
        text.insert(tk.END, f"🔴 逾期{days}天 | {order.get('order_no')} | {order.get('customer_name')} | {_format_date(order.get('delivery_date'))}\n")

    for order in alerts.get("warning_orders", [])[:5]:
        days = order.get("remain_days", 0)
        text.insert(tk.END, f"🟡 {days}天后到期 | {order.get('order_no')} | {order.get('customer_name')} | {_format_date(order.get('delivery_date'))}\n")

    for inv in alerts.get("low_inventory", [])[:5]:
        text.insert(tk.END, f"🟠 库存不足 | {inv.get('material_name')} | 当前:{inv.get('quantity')}{inv.get('unit')} | 预警:{inv.get('warning_qty')}{inv.get('unit')}\n")

    text.config(state=tk.DISABLED)

    # 按钮
    btn_frame = tk.Frame(win, bg="#FFFFFF")
    btn_frame.pack(pady=15)

    def goto_alerts():
        win.destroy()
        # 切换到预警视图
        main_win = parent.winfo_toplevel()
        if hasattr(main_win, 'show_module'):
            main_win.show_module("alerts")

    ttk.Button(btn_frame, text="查看详情", command=goto_alerts).pack(side=tk.LEFT, padx=10)
    ttk.Button(btn_frame, text="稍后处理", command=win.destroy).pack(side=tk.LEFT, padx=10)

    return win
