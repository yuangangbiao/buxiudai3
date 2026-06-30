# -*- coding: utf-8 -*-
"""
生产排单视图
"""
import tkinter as tk
from tkinter import ttk
from config import COLORS, FONTS, ORDER_STATUS, WINDOW_SIZES, LAYOUT
from constants import ProductionStatus, OrderStatus, PRIORITY_VALUE_MAPPING, PRIORITY_MAPPING
from i18n import t
from models.production import ProductionDAO
from models.order import OrderDAO
from services.schedule_dispatch_service import ScheduleDispatchService
from models.database import get_connection
from desktop.views.dialogs import popup_form, confirm, alert
from utils.helpers import format_date
from utils.op_logger import log_ui
from utils.auto_refresh_mixin import AutoRefreshMixin
from datetime import datetime


class ProductionView(AutoRefreshMixin, tk.Frame):

    SORT_COLUMNS = {
        "wo_no": "po.order_no",
        "order_no": "o.order_no",
        "customer": "o.customer_name",
        "product": "o.product_type",
        "qty": "o.quantity",
        "priority": "po.priority",
        "plan_start": "po.plan_start",
        "plan_end": "po.plan_end",
        "actual_start": "po.actual_start",
        "status": "po.status",
    }

    def __init__(self, parent, default_statuses=None):
        super().__init__(parent, bg=COLORS["bg_main"])
        self.filters = {}
        self.default_statuses = default_statuses or []
        self.sort_col = "priority"
        self.sort_reverse = False
        self.init_ui()
        self.load_data()
        self._start_auto_refresh()

    def init_ui(self):
        toolbar = tk.Frame(self, bg="#FFFFFF", height=50)
        toolbar.pack(fill=tk.X, side=tk.TOP)
        toolbar.pack_propagate(False)

        tk.Label(toolbar, text=t('production.title'), font=FONTS["large"], bg=COLORS["bg_card"],
                fg=COLORS["primary"]).pack(side=tk.LEFT, padx=LAYOUT["padding"]["large"], pady=LAYOUT["padding"]["medium"])

        # 操作按钮区
        btn_frame = tk.Frame(toolbar, bg=COLORS["bg_card"])
        btn_frame.pack(side=tk.LEFT, padx=LAYOUT["margin"]["medium"])
        ttk.Button(btn_frame, text="➕ 新建工单", command=self._create_work_order).pack(side=tk.LEFT, padx=LAYOUT["margin"]["small"])
        ttk.Button(btn_frame, text="✏️ 编辑选中", command=self._edit_selected).pack(side=tk.LEFT, padx=LAYOUT["margin"]["small"])

        # 跳转到材料备料按钮
        self.goto_material_btn = ttk.Button(btn_frame, text="📋 材料备料",
                                           command=self._goto_material_prep)
        self.goto_material_btn.pack(side=tk.LEFT, padx=LAYOUT["margin"]["small"])

        # 自动发布任务开关
        self.auto_publish_var = tk.BooleanVar(value=False)
        self.auto_publish_switch = ttk.Checkbutton(btn_frame, text="⚡ 自动发布", 
                                                   variable=self.auto_publish_var,
                                                   command=self._on_auto_publish_toggle)
        self.auto_publish_switch.pack(side=tk.LEFT, padx=LAYOUT["margin"]["small"])

        self._publish_btn = ttk.Button(btn_frame, text="发布任务",
            command=self._test_publish_click)
        self._publish_btn.pack(side=tk.LEFT, padx=LAYOUT["margin"]["small"])

        self._retry_dead_btn = ttk.Button(btn_frame, text="🔄 重发死信",
            command=self._retry_dead_letters)
        self._retry_dead_btn.pack(side=tk.LEFT, padx=LAYOUT["margin"]["small"])

        def _on_refresh():
            print("="*30, "刷新按钮被点击", "="*30, flush=True)
            self.load_data()
        ttk.Button(toolbar, text="🔄 刷新", command=_on_refresh).pack(side=tk.RIGHT, padx=LAYOUT["padding"]["medium"])
        ttk.Button(toolbar, text="🔄 状态同步", command=self._sync_status,
                  style="Accent.TButton").pack(side=tk.RIGHT, padx=LAYOUT["padding"]["medium"])

        filter_frame = tk.Frame(toolbar, bg=COLORS["bg_card"])
        filter_frame.pack(side=tk.RIGHT, padx=LAYOUT["padding"]["medium"])

        tk.Label(filter_frame, text=t('production.status'), font=FONTS["body"], bg=COLORS["bg_card"]).pack(side=tk.LEFT, padx=LAYOUT["margin"]["medium"])
        self.status_combo = ttk.Combobox(filter_frame, values=["全部", ProductionStatus.PENDING.value, ProductionStatus.IN_PROGRESS.value, ProductionStatus.COMPLETED.value],
                                         width=LAYOUT["widths"]["medium"], font=FONTS["body"], state="readonly")
        if self.default_statuses:
            status_display_map = {
                ProductionStatus.SCHEDULED.value: "已排产",
                ProductionStatus.IN_PROGRESS.value: "生产中",
                ProductionStatus.COMPLETED.value: "已完成"
            }
            display_statuses = [status_display_map.get(s, s) for s in self.default_statuses]
            self.status_combo["values"] = ["全部"] + list(set(display_statuses))
            self.status_combo.current(1 if display_statuses else 0)
        else:
            self.status_combo.current(0)
        self.status_combo.pack(side=tk.LEFT, padx=LAYOUT["margin"]["medium"])
        self.status_combo.bind("<<ComboboxSelected>>", lambda e: self.load_data())

        tk.Label(filter_frame, text=t('production.keyword'), font=FONTS["body"], bg=COLORS["bg_card"]).pack(side=tk.LEFT, padx=LAYOUT["margin"]["medium"])
        self.kw_entry = ttk.Entry(filter_frame, width=15, font=FONTS["body"])
        self.kw_entry.pack(side=tk.LEFT, padx=LAYOUT["margin"]["medium"])
        self.kw_entry.bind("<Return>", lambda e: self.load_data())
        ttk.Button(filter_frame, text="搜索", command=self.load_data).pack(side=tk.LEFT, padx=LAYOUT["margin"]["small"])

        table_frame = tk.Frame(self, bg=COLORS["bg_card"], padx=LAYOUT["padding"]["medium"], pady=LAYOUT["padding"]["small"])
        table_frame.pack(fill=tk.BOTH, expand=True, padx=LAYOUT["padding"]["medium"], pady=(LAYOUT["padding"]["small"], LAYOUT["padding"]["medium"]))

        cols = ("wo_no", "order_no", "customer", "product", "qty", "priority", "plan_start", "plan_end", "actual_start", "status")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=LAYOUT["heights"]["extra_large"])

        for col, txt, w in [
            ("wo_no", t('production.columns.wo_no'), 140), ("order_no", t('production.columns.order_no'), 140), ("customer", t('production.columns.customer'), 100),
            ("product", t('production.columns.product'), 100), ("qty", t('production.columns.qty'), 60), ("priority", t('production.columns.priority'), 70),
            ("plan_start", t('production.columns.plan_start'), 100), ("plan_end", t('production.columns.plan_end'), 100),
            ("actual_start", t('production.columns.actual_start'), 130), ("status", t('production.columns.status'), 80)
        ]:
            self.tree.heading(col, text=txt, command=lambda c=col: self._on_column_click(c))
            self.tree.column(col, width=w, anchor="w" if col != "qty" else "center")

        self._update_column_headers()

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        style = ttk.Style()
        style.configure("Treeview", font=FONTS["body"], rowheight=32)

        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.show_context_menu)

    def _on_column_click(self, col):
        if self.sort_col == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_col = col
            self.sort_reverse = False
        self._update_column_headers()
        self.load_data()

    def _update_column_headers(self):
        for col in self.SORT_COLUMNS.keys():
            txt = t(f'production.columns.{col}' if col != "qty" else "production.columns.qty")
            if col == "wo_no":
                txt = t('production.columns.wo_no')
            elif col == "order_no":
                txt = t('production.columns.order_no')
            elif col == "customer":
                txt = t('production.columns.customer')
            elif col == "product":
                txt = t('production.columns.product')
            elif col == "qty":
                txt = t('production.columns.qty')
            elif col == "priority":
                txt = t('production.columns.priority')
            elif col == "plan_start":
                txt = t('production.columns.plan_start')
            elif col == "plan_end":
                txt = t('production.columns.plan_end')
            elif col == "actual_start":
                txt = t('production.columns.actual_start')
            elif col == "status":
                txt = t('production.columns.status')
            if col == self.sort_col:
                arrow = " ▲" if self.sort_reverse else " ▼"
                txt = txt + arrow
            self.tree.heading(col, text=txt, command=lambda c=col: self._on_column_click(c))

    def load_data(self):
        log_ui("生产排单", "加载工单列表")
        for item in self.tree.get_children():
            self.tree.delete(item)

        filters = {}
        selected_status = self.status_combo.get()

        if self.default_statuses and selected_status == "全部":
            filters["status"] = self.default_statuses
        elif selected_status != "全部":
            filters["status"] = selected_status

        filters["keyword"] = self.kw_entry.get().strip()
        sort_col = self.SORT_COLUMNS.get(self.sort_col, "po.priority")
        filters["sort_col"] = sort_col
        filters["sort_reverse"] = self.sort_reverse
        orders = ProductionDAO.get_all_with_order(filters)

        status_colors = {ProductionStatus.PENDING.value: COLORS["text_secondary"], 
                        ProductionStatus.IN_PROGRESS.value: COLORS["warning"], 
                        ProductionStatus.COMPLETED.value: COLORS["success"]}
        for o in orders:
            status = o.get("status", ProductionStatus.PENDING.value)
            values = (
                o.get("order_no", ""),
                o.get("order_no", ""),
                o.get("customer_name", ""),
                o.get("product_type", ""),
                f"{o.get('quantity', 0)} {o.get('unit', '米')}",
                o.get("priority", 5),
                format_date(o.get("plan_start", ""), "-"),
                format_date(o.get("plan_end", ""), "-"),
                format_date(o.get("actual_start", ""), "-"),
                status,
            )
            item = self.tree.insert("", tk.END, values=values, tags=(status,))
            self.tree.tag_configure(status, foreground=status_colors.get(status, COLORS["text_primary"]))

    def on_double_click(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        wo_no = self.tree.item(sel[0])["values"][0]
        tags = self.tree.item(sel[0])["tags"]
        status = tags[0] if tags else ""

        if status == ProductionStatus.PENDING_PUBLISH.value:
            log_ui("生产排单", "双击待发布工单", f"wo_no={wo_no}")
            all_orders = ProductionDAO.get_all_with_order({})
            for o in all_orders:
                if o.get("order_no") == wo_no:
                    prod_id = o.get("id")
                    order_id = o.get("order_id")
                    order = OrderDAO.get_by_id(order_id)
                    if order:
                        self._show_publish_dialog(wo_no, order, prod_id)
                        return
                    else:
                        alert("未找到关联订单信息", "错误")
                        return
            alert("未找到工单信息", "错误")
            return

        self._view_order_detail(wo_no)

    def _on_auto_publish_toggle(self):
        """自动发布开关切换回调"""
        is_enabled = self.auto_publish_var.get()
        if is_enabled:
            log_ui("生产排单", "开启微信报工自动发布")
            alert("自动发布已开启\n排产确认后将自动发布任务到微信报工系统", "提示")
        else:
            log_ui("生产排单", "关闭微信报工自动发布")

    def _test_publish_click(self):
        """发布排产任务 - 先选择未排产订单，再发布排产信息"""
        log_ui("生产排单", "获取未排产订单列表")

        unscheduled = OrderDAO.get_unscheduled()
        if not unscheduled:
            alert("没有未排产的订单\n请先在订单管理中确认订单", "提示")
            return

        self._show_unscheduled_selection(unscheduled)

    def _show_unscheduled_selection(self, orders: list):
        """显示未排产订单选择对话框"""
        dialog = tk.Toplevel(self)
        dialog.title("选择未排产订单")
        dialog.geometry("750x420")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        dialog.configure(bg=COLORS["bg_main"])

        header = tk.Frame(dialog, bg=COLORS["bg_main"])
        header.pack(fill=tk.X, padx=LAYOUT["padding"]["medium"], pady=(LAYOUT["padding"]["medium"], 0))
        tk.Label(header, text="未排产订单列表",
                 font=FONTS["subtitle"], bg=COLORS["bg_main"],
                 fg=COLORS["primary"]).pack(anchor=tk.W)
        tk.Label(header,
                 text=f"共 {len(orders)} 条未排产订单，请选择一条进行排产发布",
                 font=FONTS["body"], bg=COLORS["bg_main"],
                 fg=COLORS["text_secondary"]).pack(anchor=tk.W, pady=(4, 0))

        tree_frame = tk.Frame(dialog, bg=COLORS["bg_main"])
        tree_frame.pack(fill=tk.BOTH, expand=True,
                        padx=LAYOUT["padding"]["medium"],
                        pady=LAYOUT["padding"]["medium"])

        cols = ("order_no", "customer", "product", "material", "mesh_size", "width", "length", "qty")
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=12)

        col_config = [
            ("order_no", "订单号", 150),
            ("customer", "客户", 120),
            ("product", "产品类型", 100),
            ("material", "材质", 80),
            ("mesh_size", "网孔", 80),
            ("width", "宽度", 70),
            ("length", "长度", 70),
            ("qty", "数量", 80),
        ]
        for key, txt, w in col_config:
            tree.heading(key, text=txt)
            tree.column(key, width=w, anchor="w" if key != "qty" else "center")

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for o in orders:
            qty = f"{o.get('quantity', 0)} {o.get('unit', '米')}"
            tree.insert("", tk.END, iid=str(o["id"]), values=(
                o.get("order_no", ""),
                o.get("customer_group", "") or o.get("customer_name", ""),
                o.get("product_type", ""),
                o.get("material", ""),
                o.get("mesh_size", ""),
                o.get("width", ""),
                o.get("length", ""),
                qty,
            ))

        btn_frame = tk.Frame(dialog, bg=COLORS["bg_main"])
        btn_frame.pack(fill=tk.X, padx=LAYOUT["padding"]["medium"],
                       pady=(0, LAYOUT["padding"]["medium"]))

        def do_select():
            sel = tree.selection()
            if not sel:
                alert("请先选择一条未排产订单！", "提示")
                return
            order_id = int(sel[0])
            dialog.destroy()
            self._proceed_publish(order_id)

        def do_cancel():
            dialog.destroy()

        ttk.Button(btn_frame, text="发布排产", command=do_select, width=15).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=do_cancel, width=10).pack(side=tk.RIGHT, padx=5)

        tree.bind("<Double-1>", lambda e: do_select())

    def _proceed_publish(self, order_id: int):
        """选中未排产订单后，创建工单并进入发布流程"""
        log_ui("生产排单", "创建生产工单", f"order_id={order_id}")

        existing_prod = ProductionDAO.get_by_order_id(order_id)
        if existing_prod and existing_prod.get("status") == "已取消":
            prod_id = existing_prod["id"]
            wo_no = existing_prod.get("order_no", "")
            log_ui("生产排单", "发现已取消的旧工单，复用", f"prod_id={prod_id}, wo_no={wo_no}")
            ProductionDAO.update_status(prod_id, ProductionStatus.PENDING_PUBLISH.value)
        else:
            try:
                prod_id = ProductionDAO.create(order_id, {
                    "priority": 5,
                    "plan_start": "",
                    "plan_end": "",
                    "assigned_to": "",
                    "remark": "",
                })
            except Exception as e:
                log_ui("生产排单", "创建工单失败", str(e))
                alert(f"创建生产工单失败：{e}", "错误")
                return

            ProductionDAO.update_status(prod_id, ProductionStatus.PENDING_PUBLISH.value)

            all_orders = ProductionDAO.get_all_with_order({})
            prod = None
            for o in all_orders:
                if o.get("id") == prod_id:
                    prod = o
                    break
            if not prod:
                alert("创建工单后未找到对应记录", "错误")
                return
            wo_no = prod.get("order_no", "")

        log_ui("生产排单", "工单准备就绪", f"wo_no={wo_no}, prod_id={prod_id}, status={ProductionStatus.PENDING_PUBLISH.value}")

        order = OrderDAO.get_by_id(order_id)
        if not order:
            alert("未找到订单信息", "错误")
            return

        self._show_publish_dialog(wo_no, order, prod_id)

    def _show_publish_dialog(self, wo_no: str, order: dict, prod_id: int):
        """显示工单详情及发布确认对话框"""
        extra_params = order.get("extra_params", {})
        if isinstance(extra_params, str):
            try:
                import json
                extra_params = json.loads(extra_params)
            except Exception:
                extra_params = {}

        log_ui("生产排单", "创建任务对话框", f"wo_no={wo_no}, prod_id={prod_id}")

        try:
            dialog = tk.Toplevel(self)
            dialog.title(f"排产任务 - {wo_no}")
            dialog.geometry("600x540")
            dialog.transient(self.winfo_toplevel())
            dialog.grab_set()
            dialog.configure(bg=COLORS["bg_main"])

            content = tk.Frame(dialog, bg=COLORS["bg_main"])
            content.pack(fill=tk.BOTH, expand=True, padx=LAYOUT["padding"]["medium"], pady=LAYOUT["padding"]["medium"])

            tk.Label(content, text=f"排产任务单 - {wo_no}",
                     font=FONTS["subtitle"], bg=COLORS["bg_main"],
                     fg=COLORS["primary"]).pack(pady=(0, LAYOUT["padding"]["medium"]))

            from tkinter import scrolledtext
            st = scrolledtext.ScrolledText(content, font=FONTS["body"],
                                           wrap=tk.WORD, height=22,
                                           bg="white", fg=COLORS["deep_gray"],
                                           relief=tk.FLAT, bd=0,
                                           highlightthickness=0)
            st.pack(fill=tk.BOTH, expand=True)

            st.tag_configure("bold", font=FONTS["normal_bold"], foreground=COLORS["primary"])
            st.tag_configure("section", font=FONTS["normal_bold"], foreground=COLORS["primary"],
                             spacing3=8, spacing2=4)
            st.tag_configure("label", foreground="#888888")
            st.tag_configure("value", foreground=COLORS["deep_gray"])
            st.tag_configure("highlight", foreground=COLORS["orange"], font=FONTS["normal_bold"])

            st.insert(tk.END, "\n工单信息\n", "section")
            st.insert(tk.END, "订单号：", "label")
            st.insert(tk.END, f"{wo_no}\n", "bold")
            st.insert(tk.END, "订单号：", "label")
            st.insert(tk.END, f"{order.get('order_no', '-')}\n", "value")
            st.insert(tk.END, "客户群：", "label")
            customer_group = order.get("customer_group") or order.get("customer_name", "")
            st.insert(tk.END, f"{customer_group}\n", "bold")
            st.insert(tk.END, "产品类型：", "label")
            st.insert(tk.END, f"{order.get('product_type', '-')}\n", "value")

            st.insert(tk.END, "\n尺寸参数\n", "section")
            st.insert(tk.END, "网孔尺寸：", "label")
            st.insert(tk.END, f"{order.get('mesh_size', '-')} mm\n" if order.get('mesh_size') else "- mm\n", "value")
            st.insert(tk.END, "丝径：", "label")
            st.insert(tk.END, f"{order.get('wire_diameter', '-')} mm\n" if order.get('wire_diameter') else "- mm\n", "value")
            st.insert(tk.END, "宽度：", "label")
            st.insert(tk.END, f"{order.get('width', '-')} mm\n" if order.get('width') else "- mm\n", "value")
            st.insert(tk.END, "长度：", "label")
            st.insert(tk.END, f"{order.get('length', '-')} mm\n" if order.get('length') else "- mm\n", "highlight")
            st.insert(tk.END, "数量：", "label")
            st.insert(tk.END, f"{order.get('quantity', 0)} {order.get('unit', '米')}\n", "value")

            st.insert(tk.END, "\n生产参数\n", "section")
            st.insert(tk.END, "材质：", "label")
            st.insert(tk.END, f"{order.get('material', '-')}\n", "value")
            st.insert(tk.END, "表面处理：", "label")
            st.insert(tk.END, f"{order.get('surface_treatment', '-')}\n", "value")
            st.insert(tk.END, "特殊要求：", "label")
            st.insert(tk.END, f"{order.get('special_requirements', '-')}\n", "value")
            st.insert(tk.END, "交货日期：", "label")
            st.insert(tk.END, f"{order.get('delivery_date', '-')}\n", "value")
            st.insert(tk.END, "备注：", "label")
            st.insert(tk.END, f"{order.get('remark', '-')}\n", "value")

            if extra_params:
                st.insert(tk.END, "\n自定义参数\n", "section")
                for k, v in extra_params.items():
                    if v:
                        st.insert(tk.END, f"{k}：", "label")
                        st.insert(tk.END, f"{v}\n", "value")

            st.configure(state=tk.DISABLED)

            btn_frame = tk.Frame(dialog, bg=COLORS["bg_main"])
            btn_frame.pack(fill=tk.X, padx=LAYOUT["padding"]["medium"], pady=(0, LAYOUT["padding"]["medium"]))

            def do_publish():
                try:
                    log_ui("生产排单", "确认发布", f"wo_no={wo_no}")
                    dialog.destroy()
                    if not prod_id:
                        from desktop.views.dialogs import alert
                        alert("未找到工单ID，无法发布排产", "错误")
                        self.load_data()
                        return

                    # 直接调用发布（内部自带防重复校验）
                    result = ScheduleDispatchService.publish_schedule(
                        wo_no, order, prod_id, "", ""
                    )
                    if result['success']:
                        log_ui("生产排单", "发布成功", f"wo_no={wo_no}")
                        from desktop.views.dialogs import alert
                        alert("排产发布成功，已发送到容器中心\n等待企业微信操作员确认排产", "提示")
                    else:
                        log_ui("生产排单", "发布失败", f"wo_no={wo_no}, {result['message']}")
                        from desktop.views.dialogs import alert
                        alert(result['message'], "错误")
                    self.load_data()
                except Exception as e:
                    log_ui("生产排单", "发布异常", str(e))

            def do_close():
                try:
                    dialog.destroy()
                except Exception:
                    pass

            ttk.Button(btn_frame, text="确认发布", command=do_publish, width=15).pack(side=tk.RIGHT, padx=5)
            ttk.Button(btn_frame, text="关闭", command=do_close, width=10).pack(side=tk.RIGHT, padx=5)

        except Exception as e:
            log_ui("生产排单", "对话框创建异常", str(e))
            alert(f"创建对话框失败：{e}", "错误")

    def _publish_task(self):
        """发布排产任务（代理到 _test_publish_click）"""
        self._test_publish_click()

    def _retry_dead_letters(self):
        """重发死信 — 显示死信列表并支持批量重发"""
        try:
            dead_letters = ScheduleDispatchService.get_dead_letters()
        except Exception as e:
            alert(f"查询死信失败：{e}", "错误")
            return

        if not dead_letters:
            alert("当前没有死信条目", "提示")
            return

        dialog = tk.Toplevel(self)
        dialog.title("死信重发")
        dialog.geometry("820x420")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        dialog.configure(bg=COLORS["bg_main"])

        header = tk.Frame(dialog, bg=COLORS["bg_main"])
        header.pack(fill=tk.X, padx=LAYOUT["padding"]["medium"], pady=(LAYOUT["padding"]["medium"], 0))
        tk.Label(header, text=f"死信列表（共 {len(dead_letters)} 条，retry ≥ 5次）",
                 font=FONTS["subtitle"], bg=COLORS["bg_main"],
                 fg=COLORS["warning"] if hasattr(COLORS, 'warning') else "red").pack(anchor=tk.W)

        # 表格
        tree_frame = tk.Frame(dialog, bg=COLORS["bg_main"])
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=LAYOUT["padding"]["medium"], pady=LAYOUT["padding"]["medium"])

        columns = ("select", "order_no", "retry", "error", "time")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=12)
        tree.heading("select", text="☑")
        tree.heading("order_no", text="订单号")
        tree.heading("retry", text="重试次数")
        tree.heading("error", text="最后错误")
        tree.heading("time", text="更新时间")
        tree.column("select", width=30, anchor="center")
        tree.column("order_no", width=150)
        tree.column("retry", width=70, anchor="center")
        tree.column("error", width=350)
        tree.column("time", width=150)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(fill=tk.BOTH, expand=True)

        select_vars = {}
        for i, dl in enumerate(dead_letters):
            v = tk.BooleanVar(value=True)
            select_vars[dl['id']] = v
            error_text = (dl.get('last_error') or '未知')[:60]
            time_text = str(dl.get('updated_at') or dl.get('created_at', ''))[:19]
            tree.insert("", tk.END, iid=str(dl['id']),
                       values=("☑", dl['order_no'], dl.get('retry_count', 0),
                               error_text, time_text))

        def toggle_all():
            all_selected = all(v.get() for v in select_vars.values())
            new_val = not all_selected
            for v in select_vars.values():
                v.set(new_val)
            values = ("☑" if new_val else "☐",)
            for item in tree.get_children():
                tree.set(item, "select", "☑" if new_val else "☐")

        def do_retry():
            selected = [dl_id for dl_id, v in select_vars.items() if v.get()]
            if not selected:
                alert("请至少选择一条死信", "提示")
                return

            success_count = 0
            fail_count = 0
            for dl_id in selected:
                item = tree.item(str(dl_id))
                tree.set(str(dl_id), "select", "⏳")
                dialog.update()

                try:
                    result = ScheduleDispatchService.retry_dead_letter(dl_id)
                    if result.get('skipped'):
                        tree.set(str(dl_id), "select", "⏭")
                    elif result['success']:
                        tree.set(str(dl_id), "select", "✅")
                        success_count += 1
                    else:
                        tree.set(str(dl_id), "select", "❌")
                        fail_count += 1
                except Exception as e:
                    tree.set(str(dl_id), "select", "❌")
                    fail_count += 1

            dialog.destroy()
            msg_parts = []
            if success_count:
                msg_parts.append(f"成功 {success_count} 条")
            if fail_count:
                msg_parts.append(f"失败 {fail_count} 条")
            alert(f"死信重发完成\n{'，'.join(msg_parts)}", "结果")
            self.load_data()

        btn_frame = tk.Frame(dialog, bg=COLORS["bg_main"])
        btn_frame.pack(fill=tk.X, padx=LAYOUT["padding"]["medium"], pady=(0, LAYOUT["padding"]["medium"]))
        ttk.Button(btn_frame, text="全选/取消", command=toggle_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🔄 重发选中", command=do_retry).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="关闭", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)

    def _goto_material_prep(self):
        """跳转到材料备料模块"""
        sel = self.tree.selection()
        if not sel:
            alert("请先选择要备料的工单！", "提示")
            return

        wo_values = self.tree.item(sel[0])["values"]
        wo_no = wo_values[0]

        # 找到关联的订单ID
        all_orders = ProductionDAO.get_all_with_order({})
        for o in all_orders:
            if o.get("order_no") == wo_no:
                order_id = o.get("order_id")
                # 通过主窗口切换到材料备料模块，并传递订单ID
                self.winfo_toplevel().material_prep_order_id = order_id
                self.winfo_toplevel().show_module("material_prep")
                return

        # 如果没找到关联订单，直接切换模块
        self.winfo_toplevel().show_module("material_prep")

    def edit_work_order(self, wo: dict):
        # 优先级数值转文字
        priority_map = {1: PRIORITY_MAPPING["HIGH"], 5: PRIORITY_MAPPING["MEDIUM"], 9: PRIORITY_MAPPING["LOW"]}
        priority_val = wo.get("priority", 5)
        priority_text = priority_map.get(priority_val, PRIORITY_MAPPING["MEDIUM"])

        fields = [
            ("订单号", "wo_no", wo.get("order_no", ""), "readonly"),
            ("订单号", "order_no", wo.get("order_no", ""), "readonly"),
            ("优先级", "priority", priority_text, "combo", [PRIORITY_MAPPING["HIGH"], PRIORITY_MAPPING["MEDIUM"], PRIORITY_MAPPING["LOW"]]),
            ("计划开始", "plan_start", wo.get("plan_start", ""), "date"),
            ("计划结束", "plan_end", wo.get("plan_end", ""), "date"),
            ("实际开始", "actual_start", format_date(wo.get("actual_start", ""), "尚未开始"), "readonly"),
            ("负责人", "assigned_to", wo.get("assigned_to", ""), "entry"),
            ("工单状态", "status", wo.get("status", ProductionStatus.PENDING.value), "combo", [ProductionStatus.PENDING.value, ProductionStatus.IN_PROGRESS.value, ProductionStatus.COMPLETED.value]),
            ("备　　注", "remark", wo.get("remark", ""), "textarea"),
        ]

        def on_save(data):
            # 优先级映射（文字转数值）
            priority_val = PRIORITY_VALUE_MAPPING.get(data.get("priority", PRIORITY_MAPPING["MEDIUM"]), 5)

            ProductionDAO.update(wo["id"], {
                "priority": priority_val,
                "plan_start": data.get("plan_start", ""),
                "plan_end": data.get("plan_end", ""),
                "assigned_to": data.get("assigned_to", ""),
                "status": data.get("status", ProductionStatus.PENDING.value),
                "remark": data.get("remark", ""),
            })
            self.load_data()

        popup_form("编辑工单", fields, on_save, width=550)

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.tree.selection_set(item)
        wo_no = self.tree.item(item)["values"][0]

        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="查看订单详情", command=lambda: self._view_order_detail(wo_no))
        menu.add_command(label="编辑工单", command=lambda: self._edit_by_wo(wo_no))
        menu.add_separator()
        menu.add_command(label="开始生产", command=lambda: self._change_status(wo_no, ProductionStatus.IN_PROGRESS.value))
        menu.add_command(label="标记完成", command=lambda: self._change_status(wo_no, ProductionStatus.COMPLETED.value))
        menu.post(event.x_root, event.y_root)

    def _view_order_detail(self, wo_no):
        """查看关联订单详情"""
        from desktop.views.dialogs import show_detail
        from models.process import ProcessDAO
        all_orders = ProductionDAO.get_all_with_order({})
        for o in all_orders:
            if o.get("order_no") == wo_no:
                # 获取订单信息
                order = OrderDAO.get_by_id(o.get("order_id"))
                if order:
                    production = ProductionDAO.get_by_order_id(o.get("order_id"))
                    processes = ProcessDAO.get_by_order(o.get("order_id")) if production else []
                    show_detail(self.winfo_toplevel(), order, production, processes)
                else:
                    alert("未找到关联订单", "提示")
                return
        alert("未找到工单信息", "提示")

    def _edit_by_wo(self, wo_no):
        all_orders = ProductionDAO.get_all_with_order({})
        for o in all_orders:
            if o.get("order_no") == wo_no:
                self.edit_work_order(o)
                return

    def _change_status(self, wo_no, new_status):
        log_ui("生产排单", "变更工单状态", f"订单号={wo_no}, 新状态={new_status}")
        all_orders = ProductionDAO.get_all_with_order({})
        for o in all_orders:
            if o.get("order_no") == wo_no:
                ProductionDAO.update_status(o["id"], new_status)
                self.load_data()
                alert(f"工单状态已更新为「{new_status}」", "操作成功")
                return

    def _edit_selected(self):
        """编辑选中的工单"""
        sel = self.tree.selection()
        if not sel:
            alert("请先选择要编辑的工单", "提示")
            return
        wo_no = self.tree.item(sel[0])["values"][0]
        self._edit_by_wo(wo_no)

    def _create_work_order(self):
        """创建新工单 - 选择订单弹窗（9列显示）"""
        log_ui("生产排单", "点击创建工单", "打开订单选择弹窗")
        def refresh_order_list():
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT o.id, o.order_no, o.customer_name, o.product_type,
                       o.material,
                       o.quantity, COALESCE(o.total_amount, 0) as total_amount,
                       COALESCE(o.delivery_date, '') as delivery_date,
                       o.status
                FROM orders o
                LEFT JOIN production_orders po ON o.id = po.order_id
                WHERE po.id IS NULL AND o.status = %s
                AND COALESCE(o.is_archived, 0) = 0
                ORDER BY o.created_at DESC
            """, (OrderStatus.CONFIRMED.value,))
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return rows

        rows = refresh_order_list()

        sel_win = tk.Toplevel(self)
        sel_win.title("选择订单")
        from utils.window_manager import setup_resizable_window
        setup_resizable_window(sel_win, "production_select", WINDOW_SIZES["production_select"])
        sel_win.transient(self.winfo_toplevel())
        sel_win.grab_set()
        sel_win.configure(bg=COLORS["bg_card"])

        tk.Label(sel_win, text=t('production.select_title'), font=FONTS["subtitle"], bg=COLORS["bg_card"]).pack(pady=LAYOUT["padding"]["small"])

        tree_frame = tk.Frame(sel_win, bg=COLORS["bg_card"])
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=LAYOUT["padding"]["medium"], pady=LAYOUT["padding"]["small"])

        cols = ("no", "customer", "product", "material", "qty", "amount", "delivery", "status")
        sel_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=LAYOUT["heights"]["medium"])
        col_config = [
            ("no", t('production.select_columns.no'), 120), ("customer", t('production.select_columns.customer'), 100), ("product", t('production.select_columns.product'), 100),
            ("material", t('production.select_columns.material'), 80), ("qty", t('production.select_columns.qty'), 80),
            ("amount", t('production.select_columns.amount'), 100), ("delivery", t('production.select_columns.delivery'), 100), ("status", t('production.select_columns.status'), 80)
        ]
        for col, txt, w in col_config:
            sel_tree.heading(col, text=txt)
            sel_tree.column(col, width=w, anchor="center")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=sel_tree.yview)
        sel_tree.configure(yscrollcommand=vsb.set)
        sel_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        def populate_tree():
            for item in sel_tree.get_children():
                sel_tree.delete(item)
            rows = refresh_order_list()
            for r in rows:
                status = r["status"]
                tag = ("pending",) if status == OrderStatus.PENDING.value else ("confirmed",)
                amount_str = f"¥{r['total_amount']:,.2f}" if r['total_amount'] else "-"
                sel_tree.insert("", tk.END, values=(
                    r["order_no"], r["customer_name"], r["product_type"],
                    r["material"], r["quantity"],
                    amount_str, r["delivery_date"] or "-", status
                ), tags=(str(r["id"]),))

        populate_tree()
        sel_tree.tag_configure("pending", background=COLORS["light_orange"])  # 橙色底
        sel_tree.tag_configure("confirmed", background=COLORS["bg_card"])

        def get_selected_id():
            sel = sel_tree.selection()
            if not sel:
                return None
            return int(sel_tree.item(sel[0])["tags"][0])

        def show_detail():
            order_id = get_selected_id()
            if not order_id:
                alert("请先选择一个订单", "提示")
                return
            order = OrderDAO.get_by_id(order_id)
            if order:
                self._show_order_card(order)

        def confirm_and_schedule():
            order_id = get_selected_id()
            if not order_id:
                alert("请先选择一个订单", "提示")
                return
            log_ui("生产排单", "确认并排产", f"订单ID={order_id}")
            order = OrderDAO.get_by_id(order_id)
            if order and order["status"] == OrderStatus.PENDING.value:
                OrderDAO.update_status(order_id, OrderStatus.CONFIRMED.value)
            sel_win.destroy()
            self._show_create_form(order_id)

        def direct_schedule():
            order_id = get_selected_id()
            if not order_id:
                alert("请先选择一个订单", "提示")
                return
            log_ui("生产排单", "直接排产", f"订单ID={order_id}")
            sel_win.destroy()
            self._show_create_form(order_id)

        btn_frame = tk.Frame(sel_win, bg=COLORS["bg_card"])
        btn_frame.pack(pady=LAYOUT["padding"]["medium"])
        ttk.Button(btn_frame, text="🔍 查看详情", command=show_detail).pack(side=tk.LEFT, padx=LAYOUT["margin"]["medium"])
        ttk.Button(btn_frame, text="✅ 确认并排产", command=confirm_and_schedule).pack(side=tk.LEFT, padx=LAYOUT["margin"]["medium"])
        ttk.Button(btn_frame, text="⚡ 直接排产", command=direct_schedule).pack(side=tk.LEFT, padx=LAYOUT["margin"]["medium"])
        ttk.Button(btn_frame, text="🔄 刷新列表", command=populate_tree).pack(side=tk.LEFT, padx=LAYOUT["margin"]["medium"])
        ttk.Button(btn_frame, text="关闭", command=sel_win.destroy).pack(side=tk.LEFT, padx=LAYOUT["margin"]["medium"])

        def on_double_click(event):
            item = sel_tree.selection()
            if item:
                direct_schedule()
        sel_tree.bind("<Double-Button-1>", on_double_click)

    def _show_order_card(self, order):
        """显示订单详情卡片"""
        detail_win = tk.Toplevel(self)
        detail_win.title("订单详情")
        from utils.window_manager import setup_resizable_window
        setup_resizable_window(detail_win, "order_detail", WINDOW_SIZES["order_detail"])
        detail_win.transient(self.winfo_toplevel())
        detail_win.grab_set()
        detail_win.configure(bg=COLORS["light_gray"])

        tk.Label(detail_win, text=t('production.detail_title'), font=FONTS["subtitle"], bg=COLORS["light_gray"]).pack(pady=LAYOUT["padding"]["medium"])

        info_frame = tk.Frame(detail_win, bg=COLORS["bg_card"], relief=tk.RIDGE, bd=1)
        info_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        fields_display = [
            (t('production.detail_fields.order_no'), order["order_no"]),
            (t('production.detail_fields.customer_name'), order["customer_name"]),
            (t('production.detail_fields.product_type'), order["product_type"]),
            (t('production.detail_fields.material'), order.get("material", "-")),
            (t('production.detail_fields.mesh_size'), f"{order.get('mesh_size', '-')} mm" if order.get('mesh_size') else "-"),
            (t('production.detail_fields.wire_diameter'), f"{order.get('wire_diameter', '-')} mm" if order.get('wire_diameter') else "-"),
            (t('production.detail_fields.dimensions'), f"{order.get('width', '-')} / {order.get('length', '-')} mm"),
            (t('production.detail_fields.quantity'), f"{order['quantity']} {order.get('unit', '米')}"),
            (t('production.detail_fields.unit_price'), f"¥{order.get('unit_price', 0):.2f} 元/米"),
            (t('production.detail_fields.total_amount'), f"¥{order.get('total_amount', 0):,.2f} 元"),
            (t('production.detail_fields.delivery_date'), order.get("delivery_date", "-")),
            (t('production.detail_fields.status'), order["status"]),
            (t('production.detail_fields.created_at'), order.get("created_at", "-")[:19] if order.get("created_at") else "-"),
        ]
        for i, (label, value) in enumerate(fields_display):
            row = i // 2
            col = (i % 2) * 2
            tk.Label(info_frame, text=f"{label}：", font=FONTS["normal_bold"], bg=COLORS["bg_card"], anchor="e").grid(
                row=row, column=col, sticky="e", padx=LAYOUT["padding"]["medium"], pady=LAYOUT["padding"]["small"])
            val_color = COLORS["orange"] if label == t('production.detail_fields.status') and value == OrderStatus.PENDING.value else COLORS["deep_gray"]
            tk.Label(info_frame, text=value, font=FONTS["body"], bg=COLORS["bg_card"], fg=val_color, anchor="w").grid(
                row=row, column=col+1, sticky="w", padx=LAYOUT["padding"]["medium"], pady=LAYOUT["padding"]["small"])

        if order.get("remark"):
            tk.Label(detail_win, text=f"备　注：{order['remark']}", bg=COLORS["light_gray"], font=FONTS["small"]).pack(pady=LAYOUT["padding"]["small"])

        ttk.Button(detail_win, text="关闭", command=detail_win.destroy).pack(pady=LAYOUT["padding"]["medium"])

    def _show_create_form(self, order_id):
        """显示创建工单表单"""
        from models.database import generate_order_no

        order = OrderDAO.get_by_id(order_id)
        if not order:
            alert("订单不存在", "错误")
            return

        # 预生成订单号
        preview_wo_no = generate_order_no()

        fields = [
            ("订单号", "readonly", preview_wo_no, "readonly"),
            ("订单号", "readonly", order["order_no"], "readonly"),
            ("客户名称", "readonly", order["customer_name"], "readonly"),
            ("产品类型", "readonly", order["product_type"], "readonly"),
            ("订单数量", "readonly", f"{order['quantity']} {order.get('unit', '米')}", "readonly"),
            ("优先级", "priority", PRIORITY_MAPPING["MEDIUM"], "combo", [PRIORITY_MAPPING["HIGH"], PRIORITY_MAPPING["MEDIUM"], PRIORITY_MAPPING["LOW"]]),
            ("计划开始", "plan_start", "", "date"),
            ("计划结束", "plan_end", "", "date"),
            ("负责人*", "assigned_to", "", "entry"),
            ("备　　注", "remark", "", "textarea"),
        ]

        def on_save(data):
            # 验证必填项
            if not data.get("assigned_to", "").strip():
                alert("请填写负责人（必填项）", "提示")
                return

            # 检查是否已有工单
            existing_wo = ProductionDAO.get_by_order_id(order_id)
            if existing_wo:
                alert("该订单已创建工单，请勿重复创建！", "提示")
                return

            # 优先级映射
            priority_val = PRIORITY_VALUE_MAPPING.get(data.get("priority", PRIORITY_MAPPING["MEDIUM"]), 5)

            try:
                log_ui("生产排单", "提交创建工单", f"订单ID={order_id}, 负责人={data.get('assigned_to', '')}")
                ProductionDAO.create(order_id, {
                    "priority": priority_val,
                    "plan_start": data.get("plan_start", ""),
                    "plan_end": data.get("plan_end", ""),
                    "assigned_to": data.get("assigned_to", ""),
                    "remark": data.get("remark", ""),
                })
                log_ui("生产排单", "✅ 工单创建成功", f"订单ID={order_id}")
                self.load_data()
                alert("工单创建成功！", "成功")
            except Exception as e:
                log_ui("生产排单", "❌ 工单创建失败", f"{type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                alert(f"创建失败：{e}", "错误")

        def on_confirm_production(data):
            # 验证必填项
            if not data.get("assigned_to", "").strip():
                alert("请填写负责人（必填项）！", "提示")
                return

            # 检查是否已有工单
            existing_wo = ProductionDAO.get_by_order_id(order_id)
            if existing_wo:
                alert("该订单已创建工单，请勿重复创建！", "提示")
                return

            # 优先级映射
            priority_val = PRIORITY_VALUE_MAPPING.get(data.get("priority", PRIORITY_MAPPING["MEDIUM"]), 5)

            try:
                log_ui("生产排单", "确认生产", f"订单ID={order_id}, 负责人={data.get('assigned_to', '')}")
                prod_id = ProductionDAO.create(order_id, {
                    "priority": priority_val,
                    "plan_start": data.get("plan_start", ""),
                    "plan_end": data.get("plan_end", ""),
                    "assigned_to": data.get("assigned_to", ""),
                    "remark": data.get("remark", ""),
                })
                log_ui("生产排单", "✅ 确认生产成功", f"工单ID={prod_id}")
                self.load_data()
                alert("工单已创建并进入生产状态！", "成功")
            except Exception as e:
                log_ui("生产排单", "❌ 确认生产失败", f"{type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                alert(f"操作失败：{e}", "错误")

        popup_form("创建生产工单", fields, on_save, on_confirm=("确认生产", on_confirm_production), width=500)
