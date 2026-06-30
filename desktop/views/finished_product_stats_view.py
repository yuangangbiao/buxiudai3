# -*- coding: utf-8 -*-
"""
成品统计视图
显示订单的生产统计信息：订单用时、生产用时、损耗率、生产工艺、计量单位
双击查看工序详情（合格率、实际用量、用料损耗率）
"""
import threading
import tkinter as tk
from tkinter import ttk
import urllib.request
import json
from config import COLORS, FONTS, LAYOUT
from models.order import OrderDAO
from constants import OrderStatus
from utils.helpers import format_date
from desktop.views.orders.confirm import show_order_confirm


class FinishedProductStatsView(tk.Frame):
    """成品统计视图"""

    CONTAINER_CENTER_URL = "http://localhost:5002"

    def __init__(self, parent):
        super().__init__(parent, bg=COLORS["bg_main"])
        self.filters = {"status": "全部"}
        self._sub_step_cache = {}
        self._tree_order_map = {}
        self._loading = False
        self._debounce_timer = None
        self.init_ui()
        self.load_data()

    def _call_api(self, method, endpoint, data=None):
        url = f"{self.CONTAINER_CENTER_URL}{endpoint}"
        try:
            if method == "GET":
                resp = urllib.request.urlopen(url, timeout=3)
                return json.loads(resp.read().decode())
            return None
        except Exception:
            return None

    def _get_sub_step_summary(self, order_no):
        cache_key = f"summary_{order_no}"
        if cache_key in self._sub_step_cache:
            return self._sub_step_cache[cache_key]
        result = self._call_api("GET", f"/api/process_sub_step/summary_by_order/{order_no}")
        if result and result.get("code") == 0:
            data = result.get("data", {})
            self._sub_step_cache[cache_key] = data
            return data
        return None

    def init_ui(self):
        toolbar = tk.Frame(self, bg=COLORS["bg_card"], height=50)
        toolbar.pack(fill=tk.X, side=tk.TOP)
        toolbar.pack_propagate(False)

        tk.Label(toolbar, text="📊 成品统计", font=FONTS["large"], bg=COLORS["bg_card"],
                fg=COLORS["primary"]).pack(side=tk.LEFT, padx=LAYOUT["padding"]["large"], pady=LAYOUT["padding"]["medium"])

        filter_frame = tk.Frame(toolbar, bg=COLORS["bg_card"])
        filter_frame.pack(side=tk.RIGHT, padx=LAYOUT["padding"]["medium"])

        tk.Label(filter_frame, text="状态:", font=FONTS["body"], bg=COLORS["bg_card"]).pack(side=tk.LEFT, padx=5)
        self.status_combo = ttk.Combobox(filter_frame, values=["全部", "待确认", "待排产", "待发布", "已发布", "已排产", "生产中", "质检中", "待发货", "已发货", "已完成"],
                                         width=14, font=FONTS["body"])
        self.status_combo.current(0)
        self.status_combo.pack(side=tk.LEFT, padx=2)
        self.status_combo.bind("<<ComboboxSelected>>", lambda e: self.load_data())

        search_frame = tk.Frame(toolbar, bg=COLORS["bg_card"])
        search_frame.pack(side=tk.RIGHT, padx=10)
        tk.Label(search_frame, text="搜索:", font=FONTS["body"], bg=COLORS["bg_card"]).pack(side=tk.LEFT, padx=5)
        self.keyword_var = tk.StringVar()
        self.keyword_entry = ttk.Entry(search_frame, textvariable=self.keyword_var, width=15, font=FONTS["body"])
        self.keyword_entry.pack(side=tk.LEFT, padx=5)
        self.keyword_entry.bind("<KeyRelease>", lambda e: self._on_keyword_change())
        self.keyword_entry.bind("<Return>", lambda e: self.load_data())

        ttk.Button(toolbar, text="🔄 刷新", command=self.load_data).pack(side=tk.RIGHT, padx=10)

        table_frame = tk.Frame(self, bg=COLORS["bg_card"], padx=10, pady=5)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=LAYOUT["padding"]["medium"], pady=(5, 10))

        cols = ("order_no", "customer", "product", "material", "spec", "qty", "unit",
                "in_progress", "ship_progress",
                "order_days", "prod_days", "loss_rate", "process", "status")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=LAYOUT["heights"]["large"])

        self.tree.heading("order_no", text="订单号")
        self.tree.heading("customer", text="客户")
        self.tree.heading("product", text="产品")
        self.tree.heading("material", text="材质")
        self.tree.heading("spec", text="规格")
        self.tree.heading("qty", text="数量")
        self.tree.heading("unit", text="单位")
        self.tree.heading("in_progress", text="入库进度")
        self.tree.heading("ship_progress", text="发货进度")
        self.tree.heading("order_days", text="订单用时")
        self.tree.heading("prod_days", text="生产用时")
        self.tree.heading("loss_rate", text="损耗率")
        self.tree.heading("process", text="生产工艺")
        self.tree.heading("status", text="状态")

        self.tree.column("order_no", width=120, anchor="w")
        self.tree.column("customer", width=90, anchor="w")
        self.tree.column("product", width=80, anchor="w")
        self.tree.column("material", width=60, anchor="w")
        self.tree.column("spec", width=120, anchor="w")
        self.tree.column("qty", width=50, anchor="center")
        self.tree.column("unit", width=45, anchor="center")
        self.tree.column("in_progress", width=85, anchor="center")
        self.tree.column("ship_progress", width=85, anchor="center")
        self.tree.column("order_days", width=70, anchor="center")
        self.tree.column("prod_days", width=70, anchor="center")
        self.tree.column("loss_rate", width=60, anchor="center")
        self.tree.column("process", width=80, anchor="w")
        self.tree.column("status", width=70, anchor="center")

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        style = ttk.Style()
        style.configure("Treeview", font=FONTS["body"], rowheight=32)
        style.configure("Treeview.Heading", font=FONTS["subtitle"])

        self.tree.bind("<Double-1>", self.on_double_click)

        self.hint_label = tk.Label(self, text="", font=FONTS["small"], bg=COLORS["bg_main"], fg="#888")
        self.hint_label.pack(fill=tk.X, padx=15, pady=2)

    def _on_keyword_change(self):
        if self._debounce_timer:
            self.after_cancel(self._debounce_timer)
        self._debounce_timer = self.after(300, self._debounced_search)

    def _debounced_search(self):
        if not self.tree.winfo_exists():
            return
        self._debounce_timer = None
        kw = self.keyword_var.get().strip()
        if kw:
            self.filters["keyword"] = kw
        else:
            self.filters.pop("keyword", None)
        self.load_data()

    def load_data(self):
        if self._loading:
            return
        self._loading = True
        status_filter = self.status_combo.get()
        self.filters["status"] = status_filter if status_filter != "全部" else None
        filters = {k: v for k, v in self.filters.items() if v}
        threading.Thread(target=self._bg_load_data, args=(filters,), daemon=True).start()

    def _bg_load_data(self, filters):
        try:
            orders = OrderDAO.get_all_paginated(filters, page=1, page_size=50).get("data", [])
            order_ids = [o["id"] for o in orders if o.get("id")]
            stats_dict = OrderDAO.batch_get_order_statistics(order_ids) if order_ids else {}
            summaries = {}
            for o in orders:
                order_no = o.get("order_no", "")
                summary = self._get_sub_step_summary(order_no)
                if summary:
                    summaries[order_no] = summary
            self.after(0, self._update_tree, orders, stats_dict, summaries)
        except Exception as e:
            self.after(0, lambda: setattr(self, '_loading', False))

    def _update_tree(self, orders, stats_dict, summaries):
        if not self.tree.winfo_exists():
            return
        for item in self.tree.get_children():
            self.tree.delete(item)

        kw = self.filters.get("keyword", "")
        if kw:
            self.hint_label.config(text=f"找到 {len(orders)} 条结果（双击查看详情）")
        else:
            self.hint_label.config(text=f"显示 {len(orders)} 条订单（双击查看工序详情）")

        ORDER_STATUS = {
            "待确认": "#9E9E9E",
            "待排产": "#2196F3",
            "待发布": "#00BCD4",
            "已发布": "#0097A7",
            "已排产": "#03A9F4",
            "生产中": "#FF9800",
            "质检中": "#FF5722",
            "已完成": "#4CAF50",
            "待发货": "#9C27B0",
            "已发货": "#9C27B0",
            "已取消": "#F44336"
        }

        for o in orders:
            status = o.get("status", OrderStatus.PENDING.value)
            status_color = ORDER_STATUS.get(status, "#666666")

            stats = stats_dict.get(o.get("id"), {})
            order_days = f"{stats.get('order_total_days')}天" if stats.get('order_total_days') is not None else "无"
            prod_days = f"{stats.get('production_total_days')}天" if stats.get('production_total_days') is not None else "无"
            loss_rate = f"{stats.get('loss_rate')}%" if stats.get('loss_rate') is not None else "无"
            process = stats.get('production_process') or "无"
            unit = stats.get('unit') or o.get("unit", "米")

            spec = self._spec_str(o)

            display_work_order = o.get("order_no", "") or o.get("order_no", "")
            order_no = o.get("order_no", "")
            summary = summaries.get(order_no)
            if summary:
                order_qty = summary.get("order_qty", 0) or 0
                completed_qty = summary.get("completed_qty", 0) or 0
                shipped_qty = summary.get("shipped_qty", 0) or 0
                in_progress_text = f"{completed_qty:.0f}/{order_qty:.0f}" if order_qty else "无流程"
                ship_progress_text = f"{shipped_qty:.0f}/{order_qty:.0f}" if order_qty else "无流程"
            else:
                in_progress_text = "无流程"
                ship_progress_text = "无流程"

            values = (
                display_work_order,
                o.get("customer_group", "") or "无",
                o.get("product_type", ""),
                o.get("material", ""),
                spec,
                o.get("quantity", 0),
                unit,
                in_progress_text,
                ship_progress_text,
                order_days,
                prod_days,
                loss_rate,
                process,
                status,
            )
            item = self.tree.insert("", tk.END, values=values, tags=(status,))
            self._tree_order_map[item] = o.get("id")
            self.tree.tag_configure(status, foreground=status_color)

        self._loading = False

    def _spec_str(self, o: dict) -> str:
        extra = o.get("extra_params") or {}
        if isinstance(extra, str):
            try:
                import json
                extra = json.loads(extra)
            except Exception:
                extra = {}

        parts = []
        width = extra.get("总宽") or extra.get("网带宽度") or o.get("width")
        length = extra.get("单段长度") or o.get("length")
        wire_d = extra.get("钢丝直径") or o.get("wire_diameter")
        pitch = extra.get("螺距") or extra.get("网带节距") or o.get("mesh_size")

        if width:
            parts.append(f"宽{width}")
        if length:
            parts.append(f"长{length}")
        if wire_d:
            parts.append(f"丝{wire_d}")
        if pitch:
            parts.append(f"节{pitch}")

        return " × ".join(parts) if parts else "-"

    def on_double_click(self, event):
        if not self.tree.winfo_exists():
            return
        sel = self.tree.selection()
        if not sel:
            return

        order_id = self._tree_order_map.get(sel[0])
        if not order_id:
            return

        from models.order import OrderDAO
        order = OrderDAO.get_by_id(order_id)
        if order:
            show_order_confirm(self, order)
