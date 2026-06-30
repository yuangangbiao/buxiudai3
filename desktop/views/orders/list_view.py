# -*- coding: utf-8 -*-
"""
订单列表视图
"""
import tkinter as tk
import threading
from tkinter import ttk, messagebox
from config import COLORS, FONTS, ORDER_STATUS, LAYOUT
from constants import OrderStatus
from i18n import t
from models.order import OrderDAO
from models.production import ProductionDAO
from models.process import ProcessDAO
from desktop.views.dialogs import popup_form, confirm, alert
from utils.helpers import format_amount, format_date
from utils.op_logger import log_ui
from utils.auto_refresh_mixin import AutoRefreshMixin
from .form import get_new_order_fields, get_edit_order_fields
from .confirm import show_order_confirm
from .new_order_dialog import NewOrderDialog


class OrderListView(AutoRefreshMixin, tk.Frame):
    """订单列表视图"""

    def __init__(self, parent, on_order_saved=None):
        super().__init__(parent, bg=COLORS["bg_main"])
        self.on_order_saved = on_order_saved
        self.filters = {"status": "全部", "archived": "未归档"}
        self.init_ui()
        self.load_orders()
        self._start_auto_refresh()

    def _refresh_data(self):
        self.load_orders()

    def init_ui(self):
        # 工具栏
        toolbar = tk.Frame(self, bg=COLORS["bg_card"], height=50)
        toolbar.pack(fill=tk.X, side=tk.TOP)
        toolbar.pack_propagate(False)

        tk.Label(toolbar, text=t('order.title'), font=FONTS["large"], bg=COLORS["bg_card"],
                fg=COLORS["primary"]).pack(side=tk.LEFT, padx=LAYOUT["padding"]["large"], pady=LAYOUT["padding"]["medium"])

        ttk.Button(toolbar, text="+ 新建订单", command=self.new_order,
                  style="Accent.TButton").pack(side=tk.LEFT, padx=LAYOUT["padding"]["medium"])

        # 筛选区
        filter_frame = tk.Frame(toolbar, bg=COLORS["bg_card"])
        filter_frame.pack(side=tk.RIGHT, padx=LAYOUT["padding"]["medium"])

        tk.Label(filter_frame, text=t('order.status'), font=FONTS["body"], bg=COLORS["bg_card"]).pack(side=tk.LEFT, padx=LAYOUT["padding"]["small"])
        self.status_combo = ttk.Combobox(filter_frame,
                                         values=[t('order.status_all')] + list(ORDER_STATUS.keys()),
                                         width=10, font=FONTS["body"], state="readonly")
        self.status_combo.current(0)
        self.status_combo.pack(side=tk.LEFT, padx=LAYOUT["padding"]["small"])
        self.status_combo.bind("<<ComboboxSelected>>", lambda e: self.apply_filter())

        tk.Label(filter_frame, text="归档:", font=FONTS["body"], bg=COLORS["bg_card"]).pack(side=tk.LEFT, padx=(10, 2))
        self.archive_combo = ttk.Combobox(filter_frame,
                                         values=["全部", "未归档", "已归档"],
                                         width=8, font=FONTS["body"], state="readonly")
        self.archive_combo.current(1)
        self.archive_combo.pack(side=tk.LEFT, padx=LAYOUT["padding"]["small"])
        self.archive_combo.bind("<<ComboboxSelected>>", lambda e: self.apply_filter())

        # 动态归档/恢复按钮
        self.archive_button = ttk.Button(filter_frame, text="归档订单", command=self.handle_archive_action)
        self.archive_button.pack(side=tk.LEFT, padx=5)

        # 搜索区
        search_frame = tk.Frame(toolbar, bg=COLORS["bg_card"])
        search_frame.pack(side=tk.RIGHT, padx=LAYOUT["padding"]["medium"])

        tk.Label(search_frame, text="🔍", font=FONTS["body"], bg=COLORS["bg_card"]).pack(side=tk.LEFT)
        self.keyword_var = tk.StringVar()
        self.keyword_entry = ttk.Entry(search_frame, textvariable=self.keyword_var,
                                       width=18, font=FONTS["body"])
        self.keyword_entry.pack(side=tk.LEFT, padx=(2, 4))
        self.keyword_entry.bind("<KeyRelease>", lambda e: self._on_keyword_change())
        self.keyword_entry.bind("<Return>", lambda e: self.apply_filter())

        # 结果数量提示
        self.search_hint = tk.Label(search_frame, text="", font=FONTS["small"], bg=COLORS["bg_card"], fg="#888888")
        self.search_hint.pack(side=tk.LEFT, padx=(0, 4))

        ttk.Button(search_frame, text=t('order.search'), command=self.apply_filter).pack(side=tk.LEFT, padx=2)
        ttk.Button(search_frame, text=t('order.reset'), command=self.reset_filter).pack(side=tk.LEFT, padx=2)
        ttk.Button(search_frame, text="🔄 刷新", command=self.load_orders).pack(side=tk.LEFT, padx=2)
        ttk.Button(search_frame, text="🔄 状态同步", command=self._sync_status,
                  style="Accent.TButton").pack(side=tk.LEFT, padx=2)

        # 状态筛选
        tk.Label(search_frame, text=t('order.status'), font=FONTS["body"], bg=COLORS["bg_card"]).pack(side=tk.LEFT, padx=(8, 2))
        self.status_combo = ttk.Combobox(search_frame,
                                         values=[t('order.status_all')] + list(ORDER_STATUS.keys()),
                                         width=10, font=FONTS["body"], state="readonly")
        self.status_combo.current(0)
        self.status_combo.pack(side=tk.LEFT, padx=2)
        self.status_combo.bind("<<ComboboxSelected>>", lambda e: self.apply_filter())

        # 表格区
        table_frame = tk.Frame(self, bg=COLORS["bg_card"], padx=10, pady=5)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=LAYOUT["padding"]["medium"], pady=(5, 10))

        cols = ("order_no", "customer", "product", "material", "spec", "qty", "unit", "amount", "delivery", "order_days", "prod_days", "loss_rate", "process", "status")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=LAYOUT["heights"]["large"])

        self.tree.heading("order_no", text=t('order.columns.order_no'))
        self.tree.heading("customer", text=t('order.columns.customer'))
        self.tree.heading("product", text=t('order.columns.product'))
        self.tree.heading("material", text=t('order.columns.material'))
        self.tree.heading("spec", text=t('order.columns.spec'))
        self.tree.heading("qty", text=t('order.columns.qty'))
        self.tree.heading("unit", text="单位")
        self.tree.heading("amount", text=t('order.columns.amount'))
        self.tree.heading("delivery", text=t('order.columns.delivery'))
        self.tree.heading("order_days", text="订单用时")
        self.tree.heading("prod_days", text="生产用时")
        self.tree.heading("loss_rate", text="损耗率")
        self.tree.heading("process", text="生产工艺")
        self.tree.heading("status", text=t('order.columns.status'))

        self.tree.column("order_no", width=110, anchor="w")
        self.tree.column("customer", width=90, anchor="w")
        self.tree.column("product", width=80, anchor="w")
        self.tree.column("material", width=60, anchor="w")
        self.tree.column("spec", width=120, anchor="w")
        self.tree.column("qty", width=50, anchor="center")
        self.tree.column("unit", width=45, anchor="center")
        self.tree.column("amount", width=70, anchor="e")
        self.tree.column("delivery", width=80, anchor="center")
        self.tree.column("order_days", width=65, anchor="center")
        self.tree.column("prod_days", width=65, anchor="center")
        self.tree.column("loss_rate", width=55, anchor="center")
        self.tree.column("process", width=70, anchor="w")
        self.tree.column("status", width=65, anchor="center")

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        style = ttk.Style()
        style.configure("Treeview", font=FONTS["body"], rowheight=32)
        style.configure("Treeview.Heading", font=FONTS["subtitle"])

        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.show_context_menu)

    def _on_keyword_change(self):
        """输入框每次按键松开时：超过1字符实时搜索"""
        kw = self.keyword_var.get().strip()
        if len(kw) >= 1:
            self.filters["keyword"] = kw
            self.load_orders()
        elif kw == "":
            self.filters.pop("keyword", None)
            self.load_orders()

    def apply_filter(self):
        self.filters["status"] = self.status_combo.get()
        self.filters["archived"] = self.archive_combo.get()
        kw = self.keyword_var.get().strip()
        if kw:
            self.filters["keyword"] = kw
        else:
            self.filters.pop("keyword", None)
        
        # 根据归档状态切换按钮文本
        archived_status = self.archive_combo.get()
        if archived_status == "已归档":
            self.archive_button.config(text="恢复归档")
        else:
            self.archive_button.config(text="归档订单")
            
        self.load_orders()

    def handle_archive_action(self):
        """根据当前归档状态执行归档或恢复归档操作"""
        archived_status = self.archive_combo.get()
        if archived_status == "已归档":
            self.unarchive_selected_orders()
        else:
            self.archive_selected_orders()

    def reset_filter(self):
        self.status_combo.current(0)
        self.archive_combo.current(1)
        self.keyword_var.set("")
        self.filters = {"status": "全部", "archived": "未归档"}
        self.search_hint.config(text="")
        self.load_orders()

    def load_orders(self):
        log_ui("订单列表", "加载订单列表")
        for item in self.tree.get_children():
            self.tree.delete(item)

        kw = self.filters.get("keyword", "")
        archived = self.filters.get("archived", "未归档")
        
        # 根据归档状态选择不同的查询方法
        if archived == "已归档":
            # 查询已归档订单
            filters = {}
            if kw:
                filters["keyword"] = kw
            orders = OrderDAO.get_archived_orders(filters)
        elif not kw and self.filters.get("status") == "全部" and archived == "未归档":
            orders = OrderDAO.get_recent_for_list(limit=200)
        else:
            orders = OrderDAO.get_all(self.filters)

        if kw:
            self.search_hint.config(text=f"找到 {len(orders)} 条" + ("（已限制前200条）" if len(orders) >= 200 else ""))
        else:
            self.search_hint.config(text=f"显示最近 200 条" if len(orders) >= 200 else "")

        # 批量获取订单统计信息（优化N+1查询问题）
        order_ids = [o.get("id") for o in orders if o.get("id")]
        stats_map = OrderDAO.get_batch_order_statistics(order_ids) if order_ids else {}

        for o in orders:
            order_id = o.get("id")
            status = o.get("status", OrderStatus.PENDING.value)
            status_color = ORDER_STATUS.get(status, "#666666")
            delivery = format_date(o.get("delivery_date", ""), "-")

            # 从批量查询结果中获取统计数据
            stats = stats_map.get(order_id, {})
            order_days = f"{stats.get('order_total_days')}天" if stats.get('order_total_days') is not None else "无"
            prod_days = f"{stats.get('production_total_days')}天" if stats.get('production_total_days') is not None else "无"
            loss_rate = f"{stats.get('loss_rate')}%" if stats.get('loss_rate') is not None else "无"
            process = stats.get('production_process') or "无"

            values = (
                o.get("order_no", ""),
                o.get("customer_name", ""),
                o.get("product_type", ""),
                o.get("material", ""),
                self._spec_str(o),
                o.get("quantity", 0),
                o.get("unit", "米"),
                format_amount(o.get("total_amount", 0)),
                delivery,
                order_days,
                prod_days,
                loss_rate,
                process,
                status,
            )
            item = self.tree.insert("", tk.END, values=values, tags=(status,))
            self.tree.tag_configure(status, foreground=status_color)

    def _spec_str(self, o: dict) -> str:
        """生成规格摘要字符串，优先从 extra_params 读取新字段"""
        extra = o.get("extra_params") or {}
        parts = []
        # 优先读新字段（尺寸参数），同时兼容旧字段
        width = extra.get("总宽") or extra.get("网带宽度") or o.get("width")
        length = extra.get("单段长度") or o.get("length")
        wire_d = extra.get("钢丝直径") or o.get("wire_diameter")
        pitch = extra.get("螺距") or extra.get("网带节距") or o.get("mesh_size")
        if width:
            parts.append(f"宽:{width}mm")
        if length:
            parts.append(f"长:{length}m")
        if wire_d:
            parts.append(f"丝径:{wire_d}mm")
        if pitch:
            parts.append(f"螺距:{pitch}mm")
        return " ".join(parts) if parts else "-"

    def new_order(self):
        log_ui("订单列表", "新建订单")
        def on_save(data):
            log_ui("订单列表", "保存新订单", f"客户={data.get('customer_name', '')}, 产品类型={data.get('product_type', '')}")
            order_id = OrderDAO.create(data)
            self.load_orders()
            if self.on_order_saved:
                self.on_order_saved()
            saved_order = OrderDAO.get_by_id(order_id)
            if saved_order:
                show_order_confirm(self, saved_order)

        NewOrderDialog(self, on_save)

    def on_double_click(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0])["values"]
        order_no = values[0]
        orders = OrderDAO.get_all({"keyword": order_no})
        for o in orders:
            if o["order_no"] == order_no:
                self.view_order(o)
                break

    def view_order(self, order: dict):
        """查看订单并确认"""
        from .confirm import show_order_confirm
        show_order_confirm(self, order)

    def edit_order(self, order: dict):
        """编辑订单 - 先编辑保存，再确认"""
        order_status = order.get("status", "")
        # 已排产但未生产的订单允许修改参数
        protected_statuses = ["生产中", "质检中", "已完成", "已发货"]
        if order_status in protected_statuses:
            alert(f"订单当前状态为「{order_status}」，不允许修改参数！\n\n如需修改，请先取消当前状态。", "提示")
            return

        log_ui("订单列表", "编辑订单", f"订单号={order.get('order_no', '')}")
        from .new_order_dialog import NewOrderDialog
        from .confirm import show_order_confirm

        def on_save(data):
            if not data.get("customer_name"):
                alert("请填写客户名称！", "必填项")
                return

            def do_save():
                result = OrderDAO.update(order["id"], data)
                self.after(0, lambda: self._on_order_saved(order["id"], result))

            threading.Thread(target=do_save, daemon=True).start()

        NewOrderDialog(self, on_save, order)

    def _on_order_saved(self, order_id, result):
        """订单保存完成后的回调（在主线程执行）"""
        if not result:
            messagebox.showerror("保存失败", "订单保存失败，请查看日志", parent=self)
            return
        self.load_orders()
        updated_order = OrderDAO.get_by_id(order_id)
        if updated_order:
            show_order_confirm(self, updated_order)

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.tree.selection_set(item)
        order_no = self.tree.item(item)["values"][0]

        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="查看详情", command=lambda: self.view_detail(order_no))
        menu.add_command(label="编辑订单", command=lambda: self.edit_by_no(order_no))
        menu.add_separator()
        menu.add_command(label="生产排单", command=lambda: self.create_production(order_no))
        menu.add_command(label="工序报工", command=lambda: self.report_process(order_no))
        menu.add_command(label="质检记录", command=lambda: self.add_quality(order_no))
        menu.add_command(label="发货出库", command=lambda: self.create_shipment(order_no))
        menu.add_separator()
        archived = self.filters.get("archived", "未归档")
        if archived == "已归档":
            menu.add_command(label="取消归档", command=lambda: self.unarchive_selected_orders)
        else:
            menu.add_command(label="归档订单", command=lambda: self.archive_selected_orders)
        menu.add_command(label="删除订单", command=lambda: self.delete_order(order_no),
                        foreground="red")
        menu.post(event.x_root, event.y_root)

    def delete_order(self, order_no):
        """删除订单（逻辑删除，标记为已取消）"""
        log_ui("订单列表", "删除订单", f"订单号={order_no}")
        from tkinter import messagebox
        orders = OrderDAO.get_all({"keyword": order_no})
        for o in orders:
            if o["order_no"] == order_no:
                # 检查订单状态，只有未开始生产的订单才能删除
                status = o.get("status", "")
                if status in [OrderStatus.PRODUCTION.value, OrderStatus.FINISHED.value, OrderStatus.SHIPPED.value]:
                    messagebox.showwarning("无法删除", f"该订单状态为「{status}」，无法删除！\n只有「{OrderStatus.PENDING.value}」「{OrderStatus.CONFIRMED.value}」「{OrderStatus.SCHEDULED.value}」状态的订单可以删除。", parent=self)
                    return
                
                # 确认删除
                if messagebox.askyesno("确认删除", f"确定要删除订单「{order_no}」吗？\n\n删除后订单状态将变为「已取消」，可在状态筛选中查看。", parent=self):
                    try:
                        OrderDAO.delete(o["id"])
                        self.load_orders()
                        messagebox.showinfo("删除成功", f"订单「{order_no}」已删除！", parent=self)
                    except Exception as e:
                        messagebox.showerror("删除失败", f"删除订单失败：{e}", parent=self)
                return

    def view_detail(self, order_no):
        orders = OrderDAO.get_all({"keyword": order_no})
        for o in orders:
            if o["order_no"] == order_no:
                from desktop.views.dialogs import show_detail
                production = ProductionDAO.get_by_order_id(o["id"])
                processes = ProcessDAO.get_by_order(o["id"]) if production else []
                show_detail(self, o, production, processes)
                return

    def edit_by_no(self, order_no):
        orders = OrderDAO.get_all({"keyword": order_no})
        for o in orders:
            if o["order_no"] == order_no:
                self.edit_order(o)
                return

    def create_production(self, order_no):
        log_ui("订单列表", "排产", f"订单号={order_no}")
        orders = OrderDAO.get_all({"keyword": order_no})
        for o in orders:
            if o["order_no"] == order_no:
                if o.get("status") not in [OrderStatus.CONFIRMED.value, OrderStatus.SCHEDULED.value]:
                    alert(f"只有{OrderStatus.CONFIRMED.value}的订单才能排产！", "状态限制")
                    return
                try:
                    ProductionDAO.create(o["id"], {"priority": 5})
                    self.load_orders()
                    alert("生产工单已创建！", "排产成功")
                except Exception as e:
                    alert(f"排产失败：{e}", "错误")
                return

    def report_process(self, order_no):
        orders = OrderDAO.get_all({"keyword": order_no})
        for o in orders:
            if o["order_no"] == order_no:
                production = ProductionDAO.get_by_order_id(o["id"])
                if not production:
                    alert("该订单尚未排产，请先创建生产工单！", "提示")
                    return
                self.after(100, lambda: self.master.master.show_module("process"))
                return

    def add_quality(self, order_no):
        self.after(100, lambda: self.master.master.show_module("quality"))

    def create_shipment(self, order_no):
        self.after(100, lambda: self.master.master.show_module("shipment"))

    def archive_selected_orders(self):
        """归档选中的订单"""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("请选择订单", "请先选择要归档的订单！", parent=self)
            return

        order_nos = [self.tree.item(item)["values"][0] for item in selected_items]

        if messagebox.askyesno("确认归档", f"确定要归档选中的 {len(order_nos)} 个订单吗？\n\n归档后订单将从默认列表中隐藏，可在「已归档」筛选中查看。", parent=self):
            try:
                order_ids = []
                for order_no in order_nos:
                    orders = OrderDAO.get_all({"keyword": order_no})
                    for o in orders:
                        if o["order_no"] == order_no:
                            order_ids.append(o["id"])
                            break

                if not order_ids:
                    messagebox.showinfo("归档结果", "没有找到有效的订单", parent=self)
                    return

                result = OrderDAO.archive_orders(order_ids=order_ids, operator="系统")
                archived_count = result.get("archived", 0)
                if archived_count > 0:
                    messagebox.showinfo("归档成功", f"已成功归档 {archived_count} 个订单！", parent=self)
                    self.load_orders()
                else:
                    messagebox.showinfo("归档结果", "没有需要归档的订单（可能已被归档或状态不符合要求）", parent=self)
            except Exception as e:
                messagebox.showerror("归档失败", f"归档订单失败：{e}", parent=self)

    def unarchive_selected_orders(self):
        """取消归档选中的订单"""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("请选择订单", "请先选择要取消归档的订单！", parent=self)
            return

        order_nos = [self.tree.item(item)["values"][0] for item in selected_items]

        if messagebox.askyesno("确认取消归档", f"确定要取消归档选中的 {len(order_nos)} 个订单吗？\n\n取消归档后订单将恢复显示在默认列表中。", parent=self):
            try:
                order_ids = []
                for order_no in order_nos:
                    orders = OrderDAO.get_all({"keyword": order_no})
                    for o in orders:
                        if o["order_no"] == order_no:
                            order_ids.append(o["id"])
                            break

                if not order_ids:
                    messagebox.showinfo("操作结果", "没有找到有效的订单", parent=self)
                    return

                result = OrderDAO.unarchive_orders(order_ids=order_ids)
                unarchived_count = result.get("unarchived", 0)
                if unarchived_count > 0:
                    messagebox.showinfo("操作成功", f"已成功取消归档 {unarchived_count} 个订单！", parent=self)
                    self.load_orders()
                else:
                    messagebox.showinfo("操作结果", "没有需要取消归档的订单", parent=self)
            except Exception as e:
                messagebox.showerror("操作失败", f"取消归档失败：{e}", parent=self)
