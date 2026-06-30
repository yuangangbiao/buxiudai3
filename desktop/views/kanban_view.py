# -*- coding: utf-8 -*-
"""
看板视图 - 可视化展示订单在各流程状态下的分布
"""
import tkinter as tk
from tkinter import ttk
from config import COLORS, FONTS, ORDER_STATUS
from constants import OrderStatus
from models.order import OrderDAO
from models.production import ProductionDAO
from utils.helpers import format_spec, get_urgency_color, days_until


class KanbanView(tk.Frame):
    """看板视图：7列展示不同状态的订单"""

    def __init__(self, parent, on_order_click=None, on_refresh=None):
        super().__init__(parent, bg=COLORS["bg_main"])
        self.on_order_click = on_order_click
        self.on_refresh = on_refresh
        self.order_cards = {}  # 存储卡片widget引用
        self.init_ui()

    def init_ui(self):
        # 顶部工具栏
        toolbar = tk.Frame(self, bg="#FFFFFF", height=50)
        toolbar.pack(fill=tk.X, side=tk.TOP)
        toolbar.pack_propagate(False)

        tk.Label(toolbar, text="📋 生产跟单看板", font=FONTS["large"], bg="#FFFFFF",
                 fg=COLORS["primary"]).pack(side=tk.LEFT, padx=15, pady=10)

        ttk.Button(toolbar, text="🔄 刷新", command=self.refresh,
                  style="Refresh.TButton").pack(side=tk.RIGHT, padx=10)

        # 统计栏
        self.stats_frame = tk.Frame(toolbar, bg="#FFFFFF")
        self.stats_frame.pack(side=tk.RIGHT, padx=10)

        # 看板主体
        self.kanban_container = tk.Frame(self, bg=COLORS["bg_main"])
        self.kanban_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # 7个状态列
        self.columns = {}
        col_width = 170
        for i, (status, color) in enumerate(ORDER_STATUS.items()):
            col_frame, canvas, scroll_frame, scrollbar = self.create_column(status, color, col_width)
            col_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=5, pady=5)
            self.columns[status] = {
                "frame": col_frame,
                "canvas": canvas,
                "scroll_frame": scroll_frame,
                "scrollbar": scrollbar,
                "cards": []
            }

        self.refresh()

    def create_column(self, status, color, width):
        """创建单列"""
        frame = tk.Frame(self.kanban_container, bg=COLORS["bg_main"], width=width)

        # 列头
        header = tk.Frame(frame, bg=color, height=36)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        tk.Label(header, text=status, font=FONTS["subtitle"], bg=color,
                 fg="white").pack(side=tk.LEFT, padx=8, pady=6)

        self.status_labels = getattr(self, 'status_labels', {})
        lbl_count = tk.Label(header, text="0", font=("微软雅黑", 10, "bold"),
                            bg=color, fg="white", width=3)
        lbl_count.pack(side=tk.RIGHT, padx=5, pady=4)
        self.status_labels[status] = lbl_count

        # 卡片容器（可滚动）
        canvas = tk.Canvas(frame, bg=COLORS["bg_main"], highlightthickness=0,
                          width=width, height=500)
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=COLORS["bg_main"])

        scroll_frame.bind("<Configure>",
                         lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        return frame, canvas, scroll_frame, scrollbar

    def refresh(self):
        """刷新看板数据"""
        for status, col_data in self.columns.items():
            for card in col_data["cards"]:
                card.destroy()
            col_data["cards"] = []

        orders = OrderDAO.get_recent_for_kanban(limit=200)
        status_orders = {s: [] for s in ORDER_STATUS}
        for o in orders:
            st = o.get("status", OrderStatus.PENDING.value)
            if st in status_orders:
                status_orders[st].append(o)

        for status, col_data in self.columns.items():
            count_lbl = self.status_labels.get(status)
            if count_lbl:
                count_lbl.config(text=str(len(status_orders[status])))
            display_count = 0
            for order in status_orders[status]:
                if display_count >= 50:
                    break
                card = self.create_card(col_data["scroll_frame"], order)
                card.pack(fill=tk.X, padx=3, pady=4, anchor="n")
                col_data["cards"].append(card)
                display_count += 1

    def create_card(self, parent, order: dict):
        """创建单个订单卡片"""
        card = tk.Frame(parent, bg="white", relief=tk.RIDGE, bd=1, cursor="hand2")

        # 紧急度边框色
        urgency = days_until(order.get("delivery_date", ""))
        border_color = "#F44336" if urgency < 0 else "#FF9800" if urgency <= 3 else "#4CAF50" if urgency <= 7 else "#E0E0E0"

        # 顶部色条
        top_bar = tk.Frame(card, bg=border_color, height=4)
        top_bar.pack(fill=tk.X)
        top_bar.pack_propagate(False)

        # 订单号
        order_no = order.get("order_no", "")
        tk.Label(card, text=order_no, font=FONTS["subtitle"], fg=COLORS["primary"],
                bg="white", anchor="w").pack(fill=tk.X, padx=8, pady=(6, 2))

        # 客户名
        customer = order.get("customer_name", "")
        if len(customer) > 12:
            customer = customer[:11] + "…"
        tk.Label(card, text=customer, font=FONTS["small"], fg=COLORS["text_secondary"],
                bg="white", anchor="w").pack(fill=tk.X, padx=8)

        # 产品类型
        product = order.get("product_type", "")
        tk.Label(card, text=product, font=FONTS["small"], fg=COLORS["text_primary"],
                bg="#F0F4F8", anchor="w").pack(fill=tk.X, padx=8, pady=(3, 2))

        # 规格摘要
        spec = format_spec(order)
        if len(spec) > 22:
            spec = spec[:21] + "…"
        tk.Label(card, text=spec, font=FONTS["small"], fg=COLORS["text_secondary"],
                bg="white", anchor="w").pack(fill=tk.X, padx=8, pady=(0, 3))

        # 底部：数量 + 交期
        bottom = tk.Frame(card, bg="white")
        bottom.pack(fill=tk.X, padx=8, pady=(0, 6))

        qty = order.get("quantity", 0)
        unit = order.get("unit", "米")
        tk.Label(bottom, text=f"×{qty}{unit}", font=FONTS["small"],
                fg=COLORS["text_secondary"], bg="white").pack(side=tk.LEFT)

        delivery = order.get("delivery_date", "")
        if delivery:
            if hasattr(delivery, 'strftime'):
                delivery_str = delivery.strftime('%Y-%m-%d')
            else:
                delivery_str = str(delivery) if delivery else ""
            days = days_until(delivery_str)
            if days < 0:
                dlv_text = f"超期{-days}天"
                dlv_color = "#F44336"
            elif days == 0:
                dlv_text = "今日到期"
                dlv_color = "#F44336"
            elif days <= 3:
                dlv_text = f"{days}天后"
                dlv_color = "#FF9800"
            else:
                dlv_text = f"{delivery_str[5:]}"
                dlv_color = COLORS["text_secondary"]
            tk.Label(bottom, text=dlv_text, font=FONTS["small"], fg=dlv_color,
                    bg="white").pack(side=tk.RIGHT)

        # 点击事件
        def on_click(event, oid=order["id"]):
            if self.on_order_click:
                self.on_order_click(oid)

        card.bind("<Button-1>", on_click)
        for child in card.winfo_children():
            child.bind("<Button-1>", on_click)

        return card

    def highlight_order(self, order_id: int):
        """高亮指定订单卡片（闪烁效果）"""
        for status, col_data in self.columns.items():
            for card in col_data["cards"]:
                if hasattr(card, '_order_id') and card._order_id == order_id:
                    # 简单闪烁效果
                    orig_bg = card.cget("bg")
                    colors = ["#FFF9C4", orig_bg, "#FFF9C4", orig_bg]
                    for i, clr in enumerate(colors):
                        card.after(i * 200, lambda c=card, bg=clr: c.config(bg=bg))
                    return
