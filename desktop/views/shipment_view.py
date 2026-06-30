# -*- coding: utf-8 -*-
"""
发货管理视图
"""
import threading
import tkinter as tk
from tkinter import ttk
from config import COLORS, FONTS
from constants import ShipmentStatus
from models.order import OrderDAO
from models.shipment import ShipmentDAO
from desktop.views.dialogs import popup_form, confirm, alert
from utils.logistics_companies import get_all_companies, add_company, get_custom_companies, remove_company
from utils.auto_refresh_mixin import AutoRefreshMixin


def _format_date(val):
    """安全格式化日期，处理datetime对象或字符串"""
    if hasattr(val, 'strftime'):
        return val.strftime('%Y-%m-%d')
    elif val:
        return str(val)[:10]
    return "-"


class ShipmentView(AutoRefreshMixin, tk.Frame):

    def __init__(self, parent):
        super().__init__(parent, bg=COLORS["bg_main"])
        self.filters = {}
        self._tracking_shipment_ids = {}
        self._tab_loaded = {"fg": False, "tracking": False}
        self._loading = False
        self.init_ui()
        self.load_data()
        self._start_auto_refresh()

    def init_ui(self):
        toolbar = tk.Frame(self, bg="#FFFFFF", height=50)
        toolbar.pack(fill=tk.X, side=tk.TOP)
        toolbar.pack_propagate(False)

        tk.Label(toolbar, text="🚚 发货管理", font=FONTS["large"], bg="#FFFFFF",
                fg=COLORS["primary"]).pack(side=tk.LEFT, padx=15, pady=10)

        ttk.Button(toolbar, text="+ 新建发货单", command=self.new_shipment,
                  style="Accent.TButton").pack(side=tk.LEFT, padx=8)
        ttk.Button(toolbar, text="🏢 物流公司", command=self.manage_logistics).pack(side=tk.LEFT, padx=8)
        ttk.Button(toolbar, text="⚙️ 追踪设置", command=self.tracking_settings).pack(side=tk.LEFT, padx=8)
        ttk.Button(toolbar, text="🔄 刷新", command=self.load_data).pack(side=tk.RIGHT, padx=10)
        ttk.Button(toolbar, text="🔄 状态同步", command=self._sync_status,
                  style="Accent.TButton").pack(side=tk.RIGHT, padx=10)

        filter_frame = tk.Frame(toolbar, bg="#FFFFFF")
        filter_frame.pack(side=tk.RIGHT, padx=10)

        tk.Label(filter_frame, text="状态:", font=FONTS["body"], bg="#FFFFFF").pack(side=tk.LEFT, padx=5)
        self.status_combo = ttk.Combobox(filter_frame, values=["全部", ShipmentStatus.PENDING.value, ShipmentStatus.COMPLETED.value],
                                         width=10, font=FONTS["body"], state="readonly")
        self.status_combo.current(0)
        self.status_combo.pack(side=tk.LEFT, padx=5)
        self.status_combo.bind("<<ComboboxSelected>>", lambda e: self.load_data())

        tk.Label(filter_frame, text="关键词:", font=FONTS["body"], bg="#FFFFFF").pack(side=tk.LEFT, padx=5)
        self.kw_entry = ttk.Entry(filter_frame, width=15, font=FONTS["body"])
        self.kw_entry.pack(side=tk.LEFT, padx=5)
        self.kw_entry.bind("<Return>", lambda e: self.load_data())
        ttk.Button(filter_frame, text="搜索", command=self.load_data).pack(side=tk.LEFT, padx=3)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))

        self.tab1 = tk.Frame(self.nb, bg="#FFFFFF")
        self.nb.add(self.tab1, text="📋 发货单列表")
        self.create_shipment_table(self.tab1)

        self.tab2 = tk.Frame(self.nb, bg="#FFFFFF")
        self.nb.add(self.tab2, text="📦 成品库存")
        self.create_finished_goods_table(self.tab2)

        self.tab3 = tk.Frame(self.nb, bg="#FFFFFF")
        self.nb.add(self.tab3, text="📍 物流追踪")
        self.create_tracking_tab(self.tab3)

        self.nb.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def create_shipment_table(self, parent):
        table_frame = tk.Frame(parent, bg="#FFFFFF", padx=10, pady=5)
        table_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("ship_no", "order_no", "customer", "product", "warehouse", "qty", "logistics", "tracking", "ship_date", "status")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=18)

        for col, txt, w in [
            ("ship_no", "发货单号", 130), ("order_no", "订单号/订单号", 160), ("customer", "客户", 100),
            ("product", "产品", 100), ("warehouse", "仓库", 80), ("qty", "数量", 70),
            ("logistics", "物流公司", 100), ("tracking", "运单号", 130),
            ("ship_date", "发货日期", 100), ("status", "状态", 80)
        ]:
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=w, anchor="center" if col not in ("customer", "product", "logistics") else "w")

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        style = ttk.Style()
        style.configure("Treeview", font=FONTS["subtitle"], rowheight=32)
        self.tree.tag_configure("pending", foreground="#FF9800")
        self.tree.tag_configure("shipped", foreground="#4CAF50")

        self.tree.bind("<Button-3>", self.show_context_menu)

    def create_finished_goods_table(self, parent):
        table_frame = tk.Frame(parent, bg="#FFFFFF", padx=10, pady=5)
        table_frame.pack(fill=tk.BOTH, expand=True)

        header_frame = tk.Frame(table_frame, bg="#FFFFFF")
        header_frame.pack(fill=tk.X, pady=(0, 5))

        cols = ("order_no", "customer", "product", "warehouse", "qty", "unit", "in_date", "status")
        self.fg_tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=18)

        for col, txt, w in [
            ("order_no", "订单号/订单号", 160), ("customer", "客户", 100), ("product", "产品", 100),
            ("warehouse", "仓库", 100), ("qty", "库存量", 80), ("unit", "单位", 60),
            ("in_date", "入库日期", 100), ("status", "状态", 80)
        ]:
            self.fg_tree.heading(col, text=txt)
            self.fg_tree.column(col, width=w, anchor="center" if col not in ("customer", "product") else "w")

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.fg_tree.yview)
        self.fg_tree.configure(yscrollcommand=scrollbar.set)
        self.fg_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        style = ttk.Style()
        style.configure("Treeview", font=FONTS["subtitle"], rowheight=32)

        tk.Button(header_frame, text="🔄 刷新成品库", command=self.load_finished_goods,
                 font=FONTS["body"], bg=COLORS["accent"], fg="white",
                 relief=tk.FLAT, cursor="hand2", padx=10).pack(side=tk.RIGHT, padx=5)

    def create_tracking_tab(self, parent):
        """创建物流追踪标签页"""
        top_frame = tk.Frame(parent, bg="#FFFFFF", padx=10, pady=8)
        top_frame.pack(fill=tk.X)

        tk.Label(top_frame, text="运单号:", font=FONTS["body"], bg="#FFFFFF").pack(side=tk.LEFT, padx=5)
        self.track_no_entry = ttk.Entry(top_frame, width=20, font=FONTS["body"])
        self.track_no_entry.pack(side=tk.LEFT, padx=5)
        self.track_no_entry.bind("<Return>", lambda e: self.query_tracking())

        tk.Label(top_frame, text="物流公司:", font=FONTS["body"], bg="#FFFFFF").pack(side=tk.LEFT, padx=5)
        self.track_company_combo = ttk.Combobox(top_frame, values=get_all_companies(),
                                                 width=12, font=FONTS["body"], state="readonly")
        self.track_company_combo.pack(side=tk.LEFT, padx=5)

        tk.Button(top_frame, text="🔍 查询物流", command=self.query_tracking,
                 font=FONTS["body"], bg=COLORS["accent"], fg="white",
                 relief=tk.FLAT, cursor="hand2", padx=12).pack(side=tk.LEFT, padx=8)

        tk.Button(top_frame, text="📋 订阅推送", command=self.subscribe_tracking,
                 font=FONTS["body"], bg="#FF9800", fg="white",
                 relief=tk.FLAT, cursor="hand2", padx=12).pack(side=tk.LEFT, padx=4)

        self.track_status_label = tk.Label(top_frame, text="", font=FONTS["small"],
                                           bg="#FFFFFF", fg="#666")
        self.track_status_label.pack(side=tk.RIGHT, padx=10)

        content_frame = tk.Frame(parent, bg="#FFFFFF")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        left_frame = tk.Frame(content_frame, bg="#FFFFFF")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(left_frame, text="📦 已发货单列表", font=FONTS["subtitle"],
                bg="#FFFFFF", fg=COLORS["primary"]).pack(anchor="w", pady=(0, 5))

        track_cols = ("ship_no", "order_no", "customer", "logistics", "tracking", "ship_date", "track_state", "action")
        self.track_tree = ttk.Treeview(left_frame, columns=track_cols, show="headings", height=14)

        for col, txt, w in [
            ("ship_no", "发货单号", 120), ("order_no", "订单号/订单号", 150), ("customer", "客户", 90), ("logistics", "物流公司", 90),
            ("tracking", "运单号", 120), ("ship_date", "发货日期", 90),
            ("track_state", "物流状态", 80), ("action", "操作", 70)
        ]:
            self.track_tree.heading(col, text=txt)
            self.track_tree.column(col, width=w, anchor="center" if col not in ("customer", "logistics") else "w")

        track_scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.track_tree.yview)
        self.track_tree.configure(yscrollcommand=track_scrollbar.set)
        self.track_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        track_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.track_tree.tag_configure("signed", foreground="#4CAF50")
        self.track_tree.tag_configure("transit", foreground="#2196F3")
        self.track_tree.tag_configure("problem", foreground="#F44336")
        self.track_tree.tag_configure("none", foreground="#999999")

        self.track_tree.bind("<Double-1>", self.on_track_tree_double_click)

        right_frame = tk.Frame(content_frame, bg="#FFFFFF", width=380)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        right_frame.pack_propagate(False)

        tk.Label(right_frame, text="📍 物流轨迹详情", font=FONTS["subtitle"],
                bg="#FFFFFF", fg=COLORS["primary"]).pack(anchor="w", pady=(0, 5))

        detail_container = tk.Frame(right_frame, bg="#FFFFFF")
        detail_container.pack(fill=tk.BOTH, expand=True)

        self.track_detail_text = tk.Text(detail_container, font=FONTS["mono"],
                                          wrap=tk.WORD, bg="#FAFAFA", fg="#333333",
                                          relief=tk.FLAT, padx=10, pady=10,
                                          state=tk.DISABLED, cursor="arrow")
        detail_scrollbar = ttk.Scrollbar(detail_container, orient=tk.VERTICAL,
                                          command=self.track_detail_text.yview)
        self.track_detail_text.configure(yscrollcommand=detail_scrollbar.set)
        self.track_detail_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        detail_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.track_detail_text.tag_configure("title", font=FONTS["heading"], foreground=COLORS["primary"])
        self.track_detail_text.tag_configure("state_signed", foreground="#4CAF50", font=FONTS["normal_bold"])
        self.track_detail_text.tag_configure("state_transit", foreground="#2196F3", font=FONTS["normal_bold"])
        self.track_detail_text.tag_configure("state_problem", foreground="#F44336", font=FONTS["normal_bold"])
        self.track_detail_text.tag_configure("time", foreground="#888888", font=FONTS["mono_small"])
        self.track_detail_text.tag_configure("context", foreground="#333333", font=FONTS["body"])
        self.track_detail_text.tag_configure("divider", foreground="#E0E0E0")

    def _on_tab_changed(self, event):
        nb = event.widget
        current_tab = nb.select()
        if current_tab == str(self.tab2) and not self._tab_loaded.get("fg"):
            self._tab_loaded["fg"] = True
            self.load_finished_goods()
        elif current_tab == str(self.tab3) and not self._tab_loaded.get("tracking"):
            self._tab_loaded["tracking"] = True
            self.load_tracking_list()

    def load_finished_goods(self):
        if self._loading:
            return
        self._loading = True
        threading.Thread(target=self._bg_load_finished_goods, daemon=True).start()

    def _bg_load_finished_goods(self):
        try:
            goods = ShipmentDAO.get_finished_goods()
            self.after(0, self._update_fg_tree, goods)
        except Exception as e:
            self.after(0, lambda: self._finish_loading())

    def _update_fg_tree(self, goods):
        for item in self.fg_tree.get_children():
            self.fg_tree.delete(item)
        for g in goods:
            self.fg_tree.insert("", tk.END, values=(
                f'{g.get("order_no", "")} ({g.get("order_no", "")})',
                g.get("customer_name", ""),
                g.get("product_type", ""),
                g.get("warehouse", ""),
                g.get("quantity", 0),
                g.get("unit", "米"),
                _format_date(g.get("in_date")),
                g.get("status", ""),
            ))
        self._loading = False

    def load_data(self):
        if self._loading:
            return
        self._loading = True
        filters = {}
        filters["status"] = self.status_combo.get()
        filters["keyword"] = self.kw_entry.get().strip()
        threading.Thread(target=self._bg_load_data, args=(filters,), daemon=True).start()

    def _bg_load_data(self, filters):
        try:
            shipments = ShipmentDAO.get_all(filters)
            self.after(0, self._update_shipment_tree, shipments)
        except Exception as e:
            self.after(0, lambda: self._finish_loading())

    def _update_shipment_tree(self, shipments):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for s in shipments:
            status = s.get("status", ShipmentStatus.PENDING.value)
            tag = "shipped" if status == ShipmentStatus.COMPLETED.value else "pending"
            self.tree.insert("", tk.END, values=(
                s.get("shipment_no", ""),
                f'{s.get("order_no", "")} ({s.get("order_no", "")})',
                s.get("customer_name", ""),
                s.get("product_type", ""),
                s.get("warehouse", ""),
                f"{s.get('ship_quantity', 0)} {s.get('unit', '米')}",
                s.get("logistics_company", ""),
                s.get("tracking_no", ""),
                _format_date(s.get("ship_date")),
                status,
            ), tags=(tag,))
        self._loading = False

    def _finish_loading(self):
        self._loading = False

    def load_tracking_list(self):
        """加载物流追踪列表"""
        if self._loading:
            return
        self._loading = True
        threading.Thread(target=self._bg_load_tracking_list, daemon=True).start()

    def _bg_load_tracking_list(self):
        try:
            from constants import ShipmentStatus
            try:
                shipments = ShipmentDAO.get_all_with_latest_tracking(
                    {"status": ShipmentStatus.COMPLETED.value}
                )
            except Exception:
                shipments = ShipmentDAO.get_all_shipments(
                    {"status": ShipmentStatus.COMPLETED.value}
                )
            self.after(0, self._update_track_tree, shipments)
        except Exception as e:
            self.after(0, lambda: self._finish_loading())

    def _update_track_tree(self, shipments):
        for item in self.track_tree.get_children():
            self.track_tree.delete(item)

        self._tracking_shipment_ids = {}
        from constants import ShipmentStatus

        for s in shipments:
            tracking_no = s.get("tracking_no", "")

            track_state = s.get("track_state", "")
            track_time = s.get("track_time", "")

            if "签收" in track_state:
                tag = "signed"
            elif "运输" in track_state or "揽收" in track_state:
                tag = "transit"
            elif "问题" in track_state:
                tag = "problem"
            else:
                tag = "none"

            ship_status = s.get("status", "")
            is_received = ship_status == ShipmentStatus.RECEIVED.value

            item_id = self.track_tree.insert("", tk.END, values=(
                s.get("shipment_no", ""),
                f'{s.get("order_no", "")} ({s.get("order_no", "")})',
                s.get("customer_name", ""),
                s.get("logistics_company", ""),
                tracking_no,
                _format_date(s.get("ship_date")),
                track_state or "未查询",
                "已完成" if is_received else ("✅ 确认收货" if tag != "signed" else "已签收"),
            ), tags=(tag,))

            self._tracking_shipment_ids[item_id] = {
                "shipment_id": s.get("id"),
                "tracking_no": tracking_no,
                "company_name": s.get("logistics_company", ""),
                "status": s.get("status", ""),
            }
        self._loading = False

    def query_tracking(self):
        """查询物流动态"""
        tracking_no = self.track_no_entry.get().strip()
        company_name = self.track_company_combo.get()

        if not tracking_no:
            selected = self.track_tree.selection()
            if selected:
                info = self._tracking_shipment_ids.get(selected[0])
                if info:
                    tracking_no = info["tracking_no"]
                    company_name = info.get("company_name", "")
                    self.track_no_entry.insert(0, tracking_no)
                    if company_name:
                        self.track_company_combo.set(company_name)
            else:
                alert("请输入运单号或选择已发货单！", "提示")
                return

        self.track_status_label.config(text="⏳ 正在查询...", fg="#FF9800")
        self.update_idletasks()

        try:
            from utils.logistics_tracker import get_tracker
            tracker = get_tracker()

            if not tracker.is_configured():
                self.track_status_label.config(text="⚠️ API未配置", fg="#F44336")
                self._show_tracking_detail({
                    "success": False,
                    "message": "物流追踪API未配置！\n\n请点击工具栏「⚙️ 追踪设置」按钮，\n配置快递100或快递鸟的API密钥。",
                    "traces": [],
                })
                return

            result = tracker.query_sync(tracking_no, company_name)

            if result.get("success"):
                selected = self.track_tree.selection()
                shipment_id = None
                if selected:
                    info = self._tracking_shipment_ids.get(selected[0])
                    if info:
                        shipment_id = info.get("shipment_id")

                if shipment_id:
                    ShipmentDAO.save_tracking(
                        shipment_id=shipment_id,
                        tracking_no=tracking_no,
                        state=result.get("state", "0"),
                        state_text=result.get("state_text", ""),
                        traces=result.get("traces", []),
                        company_code=result.get("company", ""),
                    )

                self.track_status_label.config(
                    text=f"✅ {result.get('state_text', '查询成功')}",
                    fg="#4CAF50"
                )
                self.load_tracking_list()
            else:
                self.track_status_label.config(text="❌ 查询失败", fg="#F44336")

            self._show_tracking_detail(result)

        except Exception as e:
            self.track_status_label.config(text="❌ 查询异常", fg="#F44336")
            self._show_tracking_detail({
                "success": False,
                "message": f"查询异常: {str(e)}",
                "traces": [],
            })

    def subscribe_tracking(self):
        """订阅物流推送"""
        tracking_no = self.track_no_entry.get().strip()
        company_name = self.track_company_combo.get()

        if not tracking_no:
            selected = self.track_tree.selection()
            if selected:
                info = self._tracking_shipment_ids.get(selected[0])
                if info:
                    tracking_no = info["tracking_no"]
                    company_name = info.get("company_name", "")
            else:
                alert("请输入运单号或选择已发货单！", "提示")
                return

        if not tracking_no:
            alert("运单号不能为空！", "提示")
            return

        try:
            from utils.logistics_tracker import get_tracker
            tracker = get_tracker()

            if not tracker.is_configured():
                alert("物流追踪API未配置！\n请先在「⚙️ 追踪设置」中配置API密钥。", "提示")
                return

            result = tracker.subscribe(tracking_no, company_name)
            if result.get("success"):
                alert(f"订阅成功！\n运单号: {tracking_no}\n物流更新将自动推送到回调地址。", "订阅成功")
            else:
                alert(f"订阅失败: {result.get('message', '未知错误')}", "订阅失败")
        except Exception as e:
            alert(f"订阅异常: {str(e)}", "错误")

    def _show_tracking_detail(self, result):
        """在右侧详情区域显示物流轨迹"""
        self.track_detail_text.config(state=tk.NORMAL)
        self.track_detail_text.delete("1.0", tk.END)

        if not result.get("success"):
            self.track_detail_text.insert(tk.END, "⚠️ 查询失败\n\n", "state_problem")
            self.track_detail_text.insert(tk.END, result.get("message", "未知错误"), "context")
            self.track_detail_text.config(state=tk.DISABLED)
            return

        tracking_no = result.get("tracking_no", "")
        state_text = result.get("state_text", "")
        state = result.get("state", "0")
        traces = result.get("traces", [])

        self.track_detail_text.insert(tk.END, f"运单号: {tracking_no}\n", "title")

        if "签收" in state_text:
            state_tag = "state_signed"
        elif "问题" in state_text:
            state_tag = "state_problem"
        else:
            state_tag = "state_transit"

        self.track_detail_text.insert(tk.END, f"状态: {state_text}\n", state_tag)
        self.track_detail_text.insert(tk.END, "─" * 35 + "\n", "divider")

        if not traces:
            self.track_detail_text.insert(tk.END, "\n暂无物流轨迹信息\n", "context")
        else:
            for i, trace in enumerate(traces):
                time_str = trace.get("ftime", "") or trace.get("time", "")
                context = trace.get("context", "") or trace.get("AcceptStation", "")
                location = trace.get("location", "")

                if time_str:
                    self.track_detail_text.insert(tk.END, f"  {time_str}\n", "time")

                detail = context
                if location:
                    detail = f"[{location}] {context}"
                self.track_detail_text.insert(tk.END, f"  {detail}\n", "context")

                if i < len(traces) - 1:
                    self.track_detail_text.insert(tk.END, "  │\n", "divider")

        self.track_detail_text.config(state=tk.DISABLED)

    def on_track_tree_double_click(self, event):
        """双击追踪列表项，查询物流或确认收货"""
        selected = self.track_tree.selection()
        if not selected:
            return

        info = self._tracking_shipment_ids.get(selected[0])
        if not info:
            return

        region = self.track_tree.identify_region(event.x, event.y)
        if region == "heading":
            return

        col = self.track_tree.identify_column(event.x)
        col_idx = int(str(col).replace("#", ""))
        columns = self.track_tree.cget("columns")
        if col_idx <= len(columns) and columns[col_idx - 1] == "action":
            self.confirm_receive(selected[0])
            return

        tracking_no = info.get("tracking_no", "")
        company_name = info.get("company_name", "")

        if not tracking_no:
            alert("该发货单没有运单号！", "提示")
            return

        self.track_no_entry.delete(0, tk.END)
        self.track_no_entry.insert(0, tracking_no)
        if company_name:
            self.track_company_combo.set(company_name)

        self.query_tracking()

    def _sync_to_bridge(self, order_no, status_key):
        if not order_no:
            return
        try:
            import os, requests as _req
            sync_url = os.environ.get('SYNC_BRIDGE_URL', 'http://127.0.0.1:5008')
            _req.post(f'{sync_url}/api/sync/status-change', json={
                'order_no': order_no,
                'status_key': status_key,
                'source': 'shipment_view'
            }, timeout=2)
        except Exception:
            pass

    def _get_order_no_by_order_id(self, order_id):
        try:
            from models.database import get_connection
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT order_no FROM production_orders WHERE order_id=%s LIMIT 1", (order_id,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            return row[0] if row else None
        except Exception:
            return None

    def confirm_receive(self, item_id):
        """确认收货，结束订单"""
        info = self._tracking_shipment_ids.get(item_id)
        if not info:
            return

        shipment_id = info.get("shipment_id")
        shipment_no = self.track_tree.item(item_id)["values"][0]

        if not confirm(f"确认「{shipment_no}」已收货？\n\n确认后该订单将标记为完成。"):
            return

        try:
            from models.database import log_status_change, get_connection
            from constants import OrderStatus, ShipmentStatus
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT order_id, status FROM shipments WHERE id=%s", (shipment_id,))
            row = cursor.fetchone()
            if not row:
                cursor.close()
                conn.close()
                alert("未找到该发货单！", "错误")
                return

            order_id = row[0]
            old_ship_status = row[1]

            cursor.execute("SELECT order_no FROM shipments WHERE id=%s", (shipment_id,))
            wo_row = cursor.fetchone()
            order_no = self._get_order_no_by_order_id(order_id)

            cursor.execute(
                "UPDATE shipments SET status=%s, updated_at=NOW() WHERE id=%s",
                (ShipmentStatus.RECEIVED.value, shipment_id)
            )
            cursor.execute(
                "UPDATE orders SET status=%s, updated_at=NOW() WHERE id=%s",
                ('订单完成', order_id)
            )
            conn.commit()
            cursor.close()
            conn.close()

            log_status_change("shipments", shipment_id, old_ship_status, ShipmentStatus.RECEIVED.value, "用户")
            log_status_change("orders", order_id, old_ship_status, '订单完成', "用户", "确认收货")

            self._sync_to_bridge(order_no, 'received')
            self._sync_to_bridge(order_no, 'order_complete')

            alert(f"「{shipment_no}」已确认收货，订单已完成！", "操作成功")
            self.load_tracking_list()
            self.load_data()
        except Exception as e:
            alert(f"操作失败: {str(e)}", "错误")

    def new_shipment(self):
        goods = ShipmentDAO.get_finished_goods()
        if not goods:
            alert("暂无可发货的成品库存！\n请先完成质检，合格后将自动入库。", "提示")
            return

        goods_options = [f"{g['order_no']} ({g.get('order_no', '')}) - {g['customer_name']} - {g['product_type']}" for g in goods]
        goods_map = {goods_options[i]: goods[i]["id"] for i in range(len(goods))}

        fields = [
            ("选择成品 *", "finished_goods", goods_options[0], "combo", goods_options),
            ("存放仓库", "warehouse", "成品仓库", "entry"),
            ("发货数量 *", "ship_quantity", "1", "number"),
            ("物流公司", "logistics_company", "", "combo", get_all_companies()),
            ("运单号", "tracking_no", "", "entry"),
            ("发货日期", "ship_date", "", "date"),
            ("收货人", "recipient", "", "entry"),
            ("联系电话", "recipient_phone", "", "entry"),
            ("收货地址", "recipient_address", "", "textarea"),
            ("运费(¥)", "freight", "0", "number"),
            ("备　　注", "remark", "", "textarea"),
        ]

        def on_save(data):
            selected = data.get("finished_goods", "")
            fg_id = goods_map.get(selected)
            if not fg_id:
                alert("请选择成品！", "必填项")
                return

            qty = float(data.get("ship_quantity") or 0)
            if qty <= 0:
                alert("发货数量必须大于0！", "输入错误")
                return

            fg = ShipmentDAO.get_finished_goods_by_id(fg_id)
            order_id = fg["order_id"] if fg else None

            ShipmentDAO.create({
                "order_id": order_id,
                "finished_goods_id": fg_id,
                "warehouse": data.get("warehouse", "成品仓库"),
                "ship_quantity": qty,
                "unit": fg["unit"] if fg else "米",
                "logistics_company": data.get("logistics_company", ""),
                "tracking_no": data.get("tracking_no", ""),
                "ship_date": data.get("ship_date", ""),
                "recipient": data.get("recipient", ""),
                "recipient_phone": data.get("recipient_phone", ""),
                "recipient_address": data.get("recipient_address", ""),
                "freight": data.get("freight", 0),
                "remark": data.get("remark", ""),
            })
            self.load_data()
            self.load_finished_goods()
            alert("发货单已创建！", "操作成功")

        popup_form("新建发货单", fields, on_save, width=550)

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.tree.selection_set(item)
        ship_no = self.tree.item(item)["values"][0]
        status = self.tree.item(item)["values"][9]
        tracking_no = self.tree.item(item)["values"][7]

        menu = tk.Menu(self, tearoff=0)
        if status == ShipmentStatus.PENDING.value:
            menu.add_command(label="确认发货", command=lambda: self.confirm_ship(ship_no))
        menu.add_command(label="查看详情", command=lambda: self.view_shipment(ship_no))
        if tracking_no and status == ShipmentStatus.COMPLETED.value:
            menu.add_separator()
            menu.add_command(label="📍 查询物流动态", command=lambda: self._track_from_context(tracking_no))
            menu.add_command(label="📋 订阅物流推送", command=lambda: self._subscribe_from_context(tracking_no))
        menu.post(event.x_root, event.y_root)

    def _track_from_context(self, tracking_no):
        """从右键菜单查询物流"""
        self.track_no_entry.delete(0, tk.END)
        self.track_no_entry.insert(0, tracking_no)
        self.query_tracking()

    def _subscribe_from_context(self, tracking_no):
        """从右键菜单订阅物流"""
        self.track_no_entry.delete(0, tk.END)
        self.track_no_entry.insert(0, tracking_no)
        self.subscribe_tracking()

    def confirm_ship(self, ship_no):
        if not confirm(f"确认发货单「{ship_no}」已发货？"):
            return
        shipments = ShipmentDAO.get_all({})
        for s in shipments:
            if s.get("shipment_no") == ship_no:
                ShipmentDAO.confirm_ship(s["id"])
                self.load_data()
                self.load_finished_goods()
                self.load_tracking_list()
                self._sync_to_bridge(s.get("order_no", ""), 'shipped')
                alert("发货确认成功！", "操作成功")
                return

    def view_shipment(self, ship_no):
        shipment = ShipmentDAO.get_by_shipment_no(ship_no)
        if not shipment:
            shipments = ShipmentDAO.get_all({})
            for s in shipments:
                if s.get("shipment_no") == ship_no:
                    shipment = s
                    break

        if shipment:
            latest_track = ShipmentDAO.get_latest_tracking(shipment.get("id", 0))
            track_info = ""
            if latest_track:
                track_info = f"\n── 物流追踪 ──\n物流状态: {latest_track.get('state_text', '')}\n查询时间: {latest_track.get('query_time', '')}"

            info = f"""
发货单号: {shipment.get('shipment_no')}
订单号: {shipment.get('order_no')} (订单号: {shipment.get('order_no', '')})
客户: {shipment.get('customer_name')}
产品: {shipment.get('product_type')}
仓库: {shipment.get('warehouse')}
数量: {shipment.get('ship_quantity')} {shipment.get('unit')}
物流: {shipment.get('logistics_company')}
运单: {shipment.get('tracking_no')}
收货人: {shipment.get('recipient')}
电话: {shipment.get('recipient_phone')}
地址: {shipment.get('recipient_address')}
运费: ¥{shipment.get('freight', 0)}
状态: {shipment.get('status')}
备注: {shipment.get('remark', '')}{track_info}
            """
            alert(info.strip(), "发货单详情")

    def tracking_settings(self):
        """物流追踪API设置"""
        from utils.window_manager import setup_resizable_window
        win = tk.Toplevel(self)
        win.title("⚙️ 物流追踪设置")
        win.attributes("-topmost", True)
        win.transient(self)
        setup_resizable_window(win, "logistics_tracking_settings", "520x520")

        def on_settings_close():
            save_settings()
            try:
                win.destroy()
            except Exception:
                pass

        win.protocol("WM_DELETE_WINDOW", on_settings_close)

        main_frame = tk.Frame(win, bg="#FFFFFF", padx=20, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(main_frame, text="物流追踪API设置", font=FONTS["title"],
                bg="#FFFFFF", fg=COLORS["primary"]).pack(pady=(0, 15))

        try:
            from utils.logistics_tracker import get_tracker
            tracker = get_tracker()
            config = tracker.config
        except Exception:
            config = None

        platform_frame = tk.LabelFrame(main_frame, text="选择API平台", font=FONTS["body"],
                                        bg="#FFFFFF", padx=10, pady=8)
        platform_frame.pack(fill=tk.X, pady=(0, 10))

        platform_var = tk.StringVar(value=config.platform if config else "kuaidi100")

        platforms_info = [
            ("kuaidi100", "快递100", "覆盖3000+快递公司，企业版稳定"),
            ("kdniao", "快递鸟", "每天免费3000次，注册即用"),
        ]

        for val, name, desc in platforms_info:
            rb_frame = tk.Frame(platform_frame, bg="#FFFFFF")
            rb_frame.pack(anchor="w", pady=2)
            tk.Radiobutton(rb_frame, text=name, variable=platform_var, value=val,
                          font=FONTS["body"], bg="#FFFFFF",
                          activebackground="#FFFFFF").pack(side=tk.LEFT)
            tk.Label(rb_frame, text=f"  ({desc})", font=FONTS["small"],
                    bg="#FFFFFF", fg="#999").pack(side=tk.LEFT)

        kd100_frame = tk.LabelFrame(main_frame, text="快递100 配置", font=FONTS["body"],
                                     bg="#FFFFFF", padx=10, pady=8)
        kd100_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(kd100_frame, text="Customer Key:", font=FONTS["body"],
                bg="#FFFFFF").pack(anchor="w")
        kd100_customer = ttk.Entry(kd100_frame, width=45, font=FONTS["body"])
        kd100_customer.pack(fill=tk.X, pady=(0, 5))
        if config and config.kuaidi100_customer:
            kd100_customer.insert(0, config.kuaidi100_customer)

        tk.Label(kd100_frame, text="API Key:", font=FONTS["body"],
                bg="#FFFFFF").pack(anchor="w")
        kd100_key = ttk.Entry(kd100_frame, width=45, font=FONTS["body"], show="*")
        kd100_key.pack(fill=tk.X, pady=(0, 5))
        if config and config.kuaidi100_key:
            kd100_key.insert(0, config.kuaidi100_key)

        tk.Label(kd100_frame, text="回调地址 (订阅推送用):", font=FONTS["body"],
                bg="#FFFFFF").pack(anchor="w")
        kd100_callback = ttk.Entry(kd100_frame, width=45, font=FONTS["body"])
        kd100_callback.pack(fill=tk.X, pady=(0, 5))
        if config and config.kuaidi100_callback_url:
            kd100_callback.insert(0, config.kuaidi100_callback_url)

        kdniao_frame = tk.LabelFrame(main_frame, text="快递鸟 配置", font=FONTS["body"],
                                      bg="#FFFFFF", padx=10, pady=8)
        kdniao_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(kdniao_frame, text="EBusinessID:", font=FONTS["body"],
                bg="#FFFFFF").pack(anchor="w")
        kdniao_id = ttk.Entry(kdniao_frame, width=45, font=FONTS["body"])
        kdniao_id.pack(fill=tk.X, pady=(0, 5))
        if config and config.kdniao_ebusiness_id:
            kdniao_id.insert(0, config.kdniao_ebusiness_id)

        tk.Label(kdniao_frame, text="API Key:", font=FONTS["body"],
                bg="#FFFFFF").pack(anchor="w")
        kdniao_key = ttk.Entry(kdniao_frame, width=45, font=FONTS["body"], show="*")
        kdniao_key.pack(fill=tk.X, pady=(0, 5))
        if config and config.kdniao_api_key:
            kdniao_key.insert(0, config.kdniao_api_key)

        tk.Label(kdniao_frame, text="回调地址 (订阅推送用):", font=FONTS["body"],
                bg="#FFFFFF").pack(anchor="w")
        kdniao_callback = ttk.Entry(kdniao_frame, width=45, font=FONTS["body"])
        kdniao_callback.pack(fill=tk.X, pady=(0, 5))
        if config and config.kdniao_callback_url:
            kdniao_callback.insert(0, config.kdniao_callback_url)

        tip_label = tk.Label(main_frame,
            text="💡 提示: 快递100官网 kuaidi100.com 注册获取密钥 | 快递鸟官网 kdniao.com 注册获取密钥\n"
                 "密钥信息保存在本地 logistics_api_config.json 文件中，不会上传到任何服务器",
            font=FONTS["small"], bg="#FFFFFF", fg="#999", wraplength=480, justify="left")
        tip_label.pack(anchor="w", pady=(0, 10))

        btn_frame = tk.Frame(main_frame, bg="#FFFFFF")
        btn_frame.pack(fill=tk.X)

        def save_settings():
            try:
                from utils.logistics_tracker import get_tracker
                tracker = get_tracker()
                cfg = tracker.config

                cfg.platform = platform_var.get()
                cfg.kuaidi100_customer = kd100_customer.get().strip()
                cfg.kuaidi100_key = kd100_key.get().strip()
                cfg.kuaidi100_callback_url = kd100_callback.get().strip()
                cfg.kdniao_ebusiness_id = kdniao_id.get().strip()
                cfg.kdniao_api_key = kdniao_key.get().strip()
                cfg.kdniao_callback_url = kdniao_callback.get().strip()

                cfg.save()
                alert("设置已保存！\n现在可以使用物流追踪功能了。", "保存成功")
                win.destroy()
            except Exception as e:
                alert(f"保存失败: {str(e)}", "错误")

        tk.Button(btn_frame, text="💾 保存设置", command=save_settings,
                 font=FONTS["body"], bg=COLORS["accent"], fg="white",
                 relief=tk.FLAT, cursor="hand2", padx=20, pady=6).pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="取消", command=win.destroy,
                 font=FONTS["body"], bg="#9E9E9E", fg="white",
                 relief=tk.FLAT, cursor="hand2", padx=20, pady=6).pack(side=tk.LEFT, padx=5)

        def test_connection():
            try:
                from utils.logistics_tracker import get_tracker
                tracker = get_tracker()
                if tracker.is_configured():
                    alert("API配置有效，连接测试通过！", "测试成功")
                else:
                    alert("API密钥未配置或配置不完整，请填写对应平台的密钥。", "测试失败")
            except Exception as e:
                alert(f"测试异常: {str(e)}", "错误")

        tk.Button(btn_frame, text="🔗 测试连接", command=test_connection,
                 font=FONTS["body"], bg="#4CAF50", fg="white",
                 relief=tk.FLAT, cursor="hand2", padx=20, pady=6).pack(side=tk.RIGHT, padx=5)

    def manage_logistics(self):
        """管理物流公司"""
        from utils.window_manager import setup_resizable_window
        win = tk.Toplevel(self)
        win.title("🏢 管理物流公司")
        win.attributes("-topmost", True)
        win.transient(self)
        setup_resizable_window(win, "logistics_company_manage", "500x400")

        tk.Label(win, text="物流公司管理", font=FONTS["title"], bg="#FFFFFF",
                fg=COLORS["primary"]).pack(pady=15)

        tk.Label(win, text="✅ 默认列表（不可删除）", font=FONTS["small"], bg="#FFFFFF",
                fg="#666").pack(anchor="w", padx=20)

        from utils.logistics_companies import DEFAULT_LOGISTICS
        default_frame = tk.Frame(win, bg="#FFFFFF")
        default_frame.pack(fill=tk.X, padx=20, pady=(5, 10))

        default_text = "、".join(DEFAULT_LOGISTICS)
        tk.Label(default_frame, text=default_text, font=FONTS["small"],
                bg="#F5F5F5", fg="#666", wraplength=440, justify="left",
                padx=10, pady=8).pack(fill=tk.X)

        tk.Label(win, text="📝 自定义列表", font=FONTS["small"], bg="#FFFFFF",
                fg=COLORS["primary"]).pack(anchor="w", padx=20)

        list_frame = tk.Frame(win, bg="#FFFFFF")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.logistics_listbox = tk.Listbox(list_frame, font=FONTS["body"],
                                            yscrollcommand=scrollbar.set,
                                            height=8, bg="#FFFFFF",
                                            selectbackground=COLORS["accent"],
                                            selectforeground="white")
        self.logistics_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.logistics_listbox.yview)

        def refresh_list():
            self.logistics_listbox.delete(0, tk.END)
            custom = get_custom_companies()
            if not custom:
                self.logistics_listbox.insert(tk.END, "（暂无自定义物流公司）")
            else:
                for c in custom:
                    self.logistics_listbox.insert(tk.END, c)

        refresh_list()

        op_frame = tk.Frame(win, bg="#FFFFFF")
        op_frame.pack(fill=tk.X, padx=20, pady=10)

        tk.Label(op_frame, text="新增:", font=FONTS["body"], bg="#FFFFFF").pack(side=tk.LEFT)

        self.new_company_entry = ttk.Entry(op_frame, width=20, font=FONTS["body"])
        self.new_company_entry.pack(side=tk.LEFT, padx=5)
        self.new_company_entry.bind("<Return>", lambda e: add_new())

        def add_new():
            name = self.new_company_entry.get().strip()
            if not name:
                alert("请输入物流公司名称！", "提示")
                return
            success, msg = add_company(name)
            if success:
                self.new_company_entry.delete(0, tk.END)
                refresh_list()
                alert(msg, "成功")
            else:
                alert(msg, "提示")

        tk.Button(op_frame, text="添加", command=add_new, font=FONTS["body"],
                 bg=COLORS["accent"], fg="white", relief=tk.FLAT,
                 cursor="hand2", padx=10).pack(side=tk.LEFT, padx=5)

        tk.Button(op_frame, text="删除", command=lambda: delete_selected(),
                 font=FONTS["body"], bg="#F44336", fg="white", relief=tk.FLAT,
                 cursor="hand2", padx=10).pack(side=tk.LEFT, padx=5)

        def delete_selected():
            idx = self.logistics_listbox.curselection()
            if not idx:
                alert("请先选择要删除的物流公司！", "提示")
                return
            name = self.logistics_listbox.get(idx[0])
            if name == "（暂无自定义物流公司）":
                return
            if confirm(f"确认删除「{name}」？"):
                success, msg = remove_company(name)
                if success:
                    refresh_list()
                    alert(msg, "成功")
                else:
                    alert(msg, "提示")

        tk.Frame(win, height=2, bg="#E0E0E0").pack(fill=tk.X, padx=20)
        tk.Button(win, text="关闭", command=win.destroy, font=FONTS["body"],
                 bg="#9E9E9E", fg="white", relief=tk.FLAT,
                 cursor="hand2", padx=20, pady=8).pack(pady=15)
