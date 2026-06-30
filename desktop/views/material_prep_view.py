# -*- coding: utf-8 -*-
"""
订单材料备料完成情况视图
"""
import tkinter as tk
import logging
import threading
import time
from tkinter import ttk, messagebox
from config import COLORS, FONTS, LAYOUT
from constants import OrderStatus, ProductionStatus
from models.order import OrderDAO
from models.database import get_connection
from services.inventory_notifier import get_inventory_notifier
from desktop.views.dialogs import popup_form, alert, MaterialPrepHistoryDialog, MaterialTemplateManagerDialog
from utils.material_templates import get_all_templates, get_template, save_template, delete_template, rename_template
from utils.auto_refresh_mixin import AutoRefreshMixin
from datetime import datetime
from utils.op_logger import log_ui

logger = logging.getLogger("material_prep")

try:
    from models.inventory import InventoryDAO as inv_db
    INV_DB_AVAILABLE = True
except Exception as e:
    logger.warning(f"[material_prep] inventory_db 导入失败: {e}")
    INV_DB_AVAILABLE = False
    inv_db = None

class MaterialPrepView(AutoRefreshMixin, tk.Frame):

    def __init__(self, parent):
        super().__init__(parent, bg=COLORS["bg_main"])
        self.selected_order_id = None
        self.init_ui()
        self.load_data()
        self._start_auto_refresh()

    def init_ui(self):
        # 顶部工具栏
        toolbar = tk.Frame(self, bg="#FFFFFF", height=50)
        toolbar.pack(fill=tk.X, side=tk.TOP)
        toolbar.pack_propagate(False)

        tk.Label(toolbar, text="📋 订单材料备料", font=FONTS["large"], bg="#FFFFFF",
                fg=COLORS["primary"]).pack(side=tk.LEFT, padx=15, pady=10)

        # 工具按钮
        btn_frame = tk.Frame(toolbar, bg="#FFFFFF")
        btn_frame.pack(side=tk.RIGHT, padx=10)
        ttk.Button(btn_frame, text="🔄 刷新", command=self.load_data).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="🔄 状态同步", command=self._sync_status,
                  style="Accent.TButton").pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="📤 发布用料需求", command=self._publish_material_demand).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="🔄 重发死信", command=self._retry_dead_tasks).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="📜 历史记录", command=self.show_history).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="⚙️ 物料规则", command=self.open_material_rules).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="🔧 计算物料", command=self.calculate_selected_materials).pack(side=tk.LEFT, padx=3)

        # 筛选
        filter_frame = tk.Frame(toolbar, bg="#FFFFFF")
        filter_frame.pack(side=tk.RIGHT, padx=10)
        tk.Label(filter_frame, text="状态:", font=FONTS["body"], bg="#FFFFFF").pack(side=tk.LEFT, padx=5)
        self.status_combo = ttk.Combobox(filter_frame,
            values=["全部", "待备料", "部分缺料", "缺料", "已备齐"],
            width=10, font=FONTS["body"], state="readonly")
        self.status_combo.current(0)
        self.status_combo.pack(side=tk.LEFT, padx=5)
        self.status_combo.bind("<<ComboboxSelected>>", lambda e: self.load_data())

        # 主内容区 - 左侧订单列表
        left_frame = tk.Frame(self, bg=COLORS["bg_main"])
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))

        tk.Label(left_frame, text="📦 订单列表", font=FONTS["subtitle"], bg=COLORS["bg_main"],
                fg=COLORS["text_primary"]).pack(anchor="w", pady=(5, 5))

        table_frame = tk.Frame(left_frame, bg="#FFFFFF")
        table_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("order_no", "customer", "product", "delivery", "status", "progress")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=15)

        for col, txt, w in [
            ("order_no", "订单号", 140), ("customer", "客户群", 100), ("product", "产品", 100),
            ("delivery", "交货日期", 100), ("status", "备料状态", 80), ("progress", "进度", 60)
        ]:
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=w, anchor="w" if col != "progress" else "center")

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        style = ttk.Style()
        style.configure("Treeview", font=FONTS["subtitle"], rowheight=32)

        # 顶部提示信息
        tip_frame = tk.Frame(self, bg="#FFF8E1", height=30)
        tip_frame.pack(fill=tk.X, side=tk.TOP, padx=10, pady=(5, 0))
        tip_frame.pack_propagate(False)
        tk.Label(tip_frame, text=f"💡 提示：仅显示{OrderStatus.SCHEDULED.value}及后续状态的订单",
                font=FONTS["small"], bg="#FFF8E1", fg="#FF8F00").pack(side=tk.LEFT, padx=10, pady=5)

        self.tree.bind("<<TreeviewSelect>>", self.on_order_select)
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.show_context_menu)

        # 右侧：物料明细
        right_frame = tk.Frame(self, bg=COLORS["bg_main"])
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(0, 10), pady=(5, 10))

        # 右侧工具栏
        right_toolbar = tk.Frame(right_frame, bg=COLORS["bg_main"])
        right_toolbar.pack(fill=tk.X, pady=(0, 5))
        tk.Label(right_toolbar, text="🧾 物料备料明细", font=FONTS["subtitle"], bg=COLORS["bg_main"],
                fg=COLORS["text_primary"]).pack(side=tk.LEFT)
        # 模板按钮组
        ttk.Button(right_toolbar, text="💾 保存模板", command=self._save_as_template).pack(side=tk.LEFT, padx=3)
        ttk.Button(right_toolbar, text="📥 载入模板", command=self._load_template).pack(side=tk.LEFT, padx=3)
        ttk.Button(right_toolbar, text="📂 管理模板", command=self._manage_templates).pack(side=tk.LEFT, padx=3)
        ttk.Button(right_toolbar, text="➕ 添加物料", command=self.add_material).pack(side=tk.RIGHT, padx=3)
        ttk.Button(right_toolbar, text="📝 编辑", command=self.edit_selected_material).pack(side=tk.RIGHT, padx=3)
        ttk.Button(right_toolbar, text="🔓 解锁", command=self.unlock_selected_material).pack(side=tk.RIGHT, padx=3)
        ttk.Button(right_toolbar, text="🔧 工序追踪", command=self._goto_process).pack(side=tk.RIGHT, padx=3)

        self.prep_detail_frame = tk.Frame(right_frame, bg="#FFFFFF")
        self.prep_detail_frame.pack(fill=tk.BOTH, expand=True)

        # 订单概览信息栏
        self.order_info_frame = tk.Frame(self.prep_detail_frame, bg="#E3F2FD", padx=10, pady=5)
        self.order_info_frame.pack(fill=tk.X)

        self.order_info_label = tk.Label(self.order_info_frame, text="请选择左侧订单查看备料情况",
                                        font=FONTS["body"], bg="#E3F2FD", fg="#1565C0")
        self.order_info_label.pack(anchor="w")

        # 备料明细表
        cols2 = ("material", "spec", "unit", "required", "prepared", "shortage", "status", "locked", "updated")
        self.detail_tree = ttk.Treeview(self.prep_detail_frame, columns=cols2, show="headings", height=10)

        for col, txt, w in [
            ("material", "物料名称", 110), ("spec", "规格", 100), ("unit", "单位", 55),
            ("required", "需求数量", 80), ("prepared", "已备数量", 80),
            ("shortage", "缺口", 65), ("status", "状态", 80), ("locked", "锁定", 60), ("updated", "更新时间", 110)
        ]:
            self.detail_tree.heading(col, text=txt)
            self.detail_tree.column(col, width=w, anchor="center" if col in ("required", "prepared", "shortage", "status", "unit", "locked") else "w")

        scrollbar2 = ttk.Scrollbar(self.prep_detail_frame, orient=tk.VERTICAL, command=self.detail_tree.yview)
        self.detail_tree.configure(yscrollcommand=scrollbar2.set)
        self.detail_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar2.pack(side=tk.RIGHT, fill=tk.Y)

        self.detail_tree.bind("<Double-1>", self.on_material_double_click)
        self.detail_tree.bind("<Button-3>", self.show_material_context_menu)

        # 状态说明
        status_frame = tk.Frame(right_frame, bg=COLORS["bg_main"])
        status_frame.pack(fill=tk.X, pady=5)
        tk.Label(status_frame, text="🔴 缺料 | 🟠 部分缺料 | 🟢 齐全",
                font=FONTS["small"], bg=COLORS["bg_main"], fg="#666").pack(anchor="w")

        # 状态颜色配置
        self.tree.tag_configure("complete", foreground="#4CAF50")
        self.tree.tag_configure("partial", foreground="#FF9800")
        self.tree.tag_configure("shortage", foreground="#F44336")
        self.tree.tag_configure("pending", foreground="#9E9E9E")

        self.detail_tree.tag_configure("complete", foreground="#4CAF50")
        self.detail_tree.tag_configure("partial", foreground="#FF9800")
        self.detail_tree.tag_configure("shortage", foreground="#F44336")
        self.detail_tree.tag_configure("pending", foreground="#9E9E9E")
        self.detail_tree.tag_configure("locked", background="#FFEBEE")
        self.detail_tree.tag_configure("unlocked", background="#E8F5E9")

    def _goto_process(self):
        """跳转到工序追踪模块"""
        if not self.selected_order_id:
            alert("请先选择一个订单！", "提示")
            return

        order = OrderDAO.get_by_id(self.selected_order_id)
        if order:
            # 通过主窗口切换到工序追踪模块
            root = self.winfo_toplevel()
            root.process_track_order_id = self.selected_order_id
            root.show_module("process")

    def load_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        status_filter = self.status_combo.get()

        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT o.*, GROUP_CONCAT(DISTINCT p.order_no ORDER BY p.order_no SEPARATOR ', ') as order_no
                FROM orders o
                INNER JOIN production_orders p ON o.id = p.order_id
                WHERE o.status IN ({','.join(['%s'] * 4)})
                AND COALESCE(o.is_archived, 0) = 0
                GROUP BY o.id
                ORDER BY
                    CASE o.status
                        WHEN %s THEN 1
                        WHEN %s THEN 2
                        WHEN %s THEN 3
                        WHEN %s THEN 4
                    END,
                    o.delivery_date ASC
            """, (
                OrderStatus.SCHEDULED.value, OrderStatus.PRODUCTION.value,
                OrderStatus.QC.value, OrderStatus.FINISHED.value,
                OrderStatus.SCHEDULED.value, OrderStatus.PRODUCTION.value,
                OrderStatus.QC.value, OrderStatus.FINISHED.value
            ))
            rows = cursor.fetchall()
            cursor.close()

            if not rows:
                return

            order_ids = [o["id"] if hasattr(o, 'get') else o[0] for o in rows]

            cursor = conn.cursor()
            placeholders = ','.join(['%s'] * len(order_ids))
            cursor.execute(f"""
                SELECT order_id,
                       SUM(CASE WHEN required_qty > 0 THEN 1 ELSE 0 END) as total_items,
                       SUM(CASE WHEN required_qty > 0 AND prepared_qty >= required_qty THEN 1 ELSE 0 END) as complete_items,
                       SUM(CASE WHEN required_qty > 0 AND prepared_qty = 0 THEN 1 ELSE 0 END) as shortage_items,
                       SUM(CASE WHEN required_qty > 0 AND prepared_qty > 0 AND prepared_qty < required_qty THEN 1 ELSE 0 END) as partial_items
                FROM order_materials
                WHERE order_id IN ({placeholders})
                GROUP BY order_id
            """, order_ids)
            stats_map = {row["order_id"]: row for row in cursor.fetchall()}
            cursor.close()

            tag_map = {"已备齐": "complete", "部分缺料": "partial", "缺料": "shortage", "待备料": "pending"}
            order_status_map = {
                OrderStatus.SCHEDULED.value: "#03A9F4",
                OrderStatus.PRODUCTION.value: "#FF9800",
                OrderStatus.QC.value: "#FF5722",
                OrderStatus.FINISHED.value: "#4CAF50"
            }

            for o in rows:
                order_id = o["id"] if hasattr(o, 'get') else o[0]
                stats = stats_map.get(order_id)

                if not stats or stats["total_items"] == 0:
                    prep_status = "待备料"
                    progress = 0
                elif stats["complete_items"] == stats["total_items"]:
                    prep_status = "已备齐"
                    progress = 100
                elif stats["shortage_items"] > 0:
                    prep_status = "缺料"
                    progress = int(stats["complete_items"] / stats["total_items"] * 100) if stats["total_items"] > 0 else 0
                else:
                    prep_status = "部分缺料"
                    progress = int(stats["complete_items"] / stats["total_items"] * 100) if stats["total_items"] > 0 else 0

                if status_filter != "全部" and prep_status != status_filter:
                    continue

                delivery_date = o.get("delivery_date", "") if hasattr(o, 'get') else None
                if hasattr(delivery_date, 'strftime'):
                    delivery_str = delivery_date.strftime('%Y-%m-%d')
                elif delivery_date:
                    delivery_str = str(delivery_date)[:10]
                else:
                    delivery_str = "-"

                values = (
                    o.get("order_no", "") or o.get("order_no", "") if hasattr(o, 'get') else o[1],
                    o.get("customer_group", "") or "无",
                    o.get("product_type", "") if hasattr(o, 'get') else o[3],
                    delivery_str,
                    prep_status,
                    f"{progress}%",
                )
                item_id = self.tree.insert("", tk.END, values=values)
                self.tree.item(item_id, tags=(str(order_id), tag_map.get(prep_status, "pending")))
        finally:
            conn.close()

    def _get_prep_status(self, order_id):
        """计算订单备料状态：缺料/部分缺料/已备齐"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT required_qty, prepared_qty FROM order_materials WHERE order_id=%s",
            (order_id,)
        )
        materials = cursor.fetchall()
        cursor.close()
        conn.close()

        if not materials:
            return "待备料"

        has_shortage = False
        has_partial = False
        all_complete = True

        for m in materials:
            req = m["required_qty"] or 0
            prep = m["prepared_qty"] or 0
            if prep == 0 and req > 0:
                has_shortage = True
                all_complete = False
            elif prep < req:
                has_partial = True
                all_complete = False

        if all_complete:
            return "已备齐"
        elif has_shortage:
            return "缺料"
        elif has_partial:
            return "部分缺料"
        return "待备料"

    def _get_prep_progress(self, order_id):
        """计算备料进度"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM order_materials WHERE order_id=%s AND required_qty > 0",
            (order_id,)
        )
        total = cursor.fetchone()["cnt"]

        if total == 0:
            cursor.close()
            conn.close()
            return 0

        cursor.execute(
            "SELECT COUNT(*) as cnt FROM order_materials WHERE order_id=%s AND required_qty > 0 AND prepared_qty >= required_qty",
            (order_id,)
        )
        done = cursor.fetchone()["cnt"]
        cursor.close()
        conn.close()

        return int(done / total * 100)

    def on_order_select(self, event=None):
        sel = self.tree.selection()
        if sel:
            # 从item tags获取订单ID
            tags = self.tree.item(sel[0])["tags"]
            if tags and len(tags) > 0:
                try:
                    order_id = int(tags[0])
                    self.selected_order_id = order_id
                    self._load_prep_detail(order_id)
                    self._update_order_info(order_id)
                except (ValueError, TypeError):
                    pass

    def _get_display_order_no(self, order_id):
        """从树形表格获取订单号显示文本，优先 order_no"""
        if not order_id:
            return ""
        for item in self.tree.get_children():
            tags = self.tree.item(item, 'tags')
            if tags and str(order_id) == str(tags[0]):
                values = self.tree.item(item, 'values')
                if values and values[0]:
                    return values[0]
        return ""

    def _update_order_info(self, order_id):
        """更新订单概览信息"""
        order = OrderDAO.get_by_id(order_id)
        if not order:
            self.order_info_label.config(text="请选择左侧订单查看备料情况")
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN required_qty > 0 AND prepared_qty >= required_qty THEN 1 ELSE 0 END) as complete,
                SUM(CASE WHEN required_qty > 0 AND prepared_qty < required_qty AND prepared_qty > 0 THEN 1 ELSE 0 END) as partial,
                SUM(CASE WHEN required_qty > 0 AND prepared_qty = 0 THEN 1 ELSE 0 END) as shortage,
                SUM(required_qty) as total_req,
                SUM(prepared_qty) as total_prep
            FROM order_materials WHERE order_id=%s
        """, (order_id,))
        stats = cursor.fetchone()
        cursor.close()
        conn.close()

        total = stats["total"] or 0
        complete = stats["complete"] or 0
        shortage = stats["shortage"] or 0
        total_req = stats["total_req"] or 0
        total_prep = stats["total_prep"] or 0

        if total == 0:
            status_text = "暂无物料"
            color = "#666"
        else:
            progress = int(total_prep / total_req * 100) if total_req > 0 else 0
            order_no = self._get_display_order_no(order_id)
            if not order_no:
                order_no = order.get('order_no', '')
            status_text = f"订单：{order_no} | 物料：{total}种 | 🟢齐全：{complete} | 🔴缺料：{shortage} | 整体进度：{progress}%"
            color = "#4CAF50" if shortage == 0 else "#F44336"

        self.order_info_label.config(text=status_text, fg=color)

    def _load_prep_detail(self, order_id):
        for item in self.detail_tree.get_children():
            self.detail_tree.delete(item)

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM order_materials WHERE order_id=%s ORDER BY id",
            (order_id,)
        )
        materials = cursor.fetchall()
        cursor.close()
        conn.close()

        if not materials:
            self.detail_tree.insert("", tk.END, values=("--", "--", "--", "--", "--", "--", "--", "暂无物料", "--"))
            return

        for m in materials:
            mat = dict(m)
            req = mat.get("required_qty") or 0
            prep = mat.get("prepared_qty") or 0
            shortage = max(0, req - prep)
            unit = mat.get("unit", "")
            spec = mat.get("spec", "") or ""

            if req == 0:
                status = "无需备料"
                tag = "pending"
            elif prep == 0:
                status = "缺料"
                tag = "shortage"
            elif prep < req:
                status = "部分缺料"
                tag = "partial"
            else:
                status = "已备齐"
                tag = "complete"

            locked = mat.get("locked", 1)
            locked_text = "是" if locked else "否"
            locked_tag = "locked" if locked else "unlocked"

            updated_at = mat.get("updated_at")
            if updated_at:
                updated = str(updated_at)[:16]
            else:
                updated = ""

            shortage_str = f"{shortage}" if shortage > 0 else "-"

            self.detail_tree.insert("", tk.END, values=(
                mat.get("material_name", ""),
                spec,
                unit,
                f"{req}",
                f"{prep}",
                shortage_str,
                status,
                locked_text,
                updated,
            ), tags=(tag, locked_tag,))

    def add_material(self):
        if not self.selected_order_id:
            alert("请先选择订单", "提示")
            return

        order = OrderDAO.get_by_id(self.selected_order_id)
        display_no = self._get_display_order_no(self.selected_order_id) or order.get('order_no', '')

        # 预设常用物料选项
        common_materials = ["不锈钢网带", "侧板", "传动轴", "链条", "轴承", "减速机", "电机", "链条板", "导轨", "托轮", "包胶滚筒", "调节螺杆"]

        fields = [
            ("物料名称", "material_name", "", "entry"),
            ("规格", "material_type", "", "entry"),
            ("单位", "unit", "米", "entry"),
            ("需求数量", "required_qty", "0", "number"),
            ("备注", "remark", "", "entry"),
        ]

        def on_save(data):
            material_name = data.get("material_name", "").strip()
            if not material_name:
                alert("请输入物料名称", "提示")
                return

            required = float(data.get("required_qty", 0))

            conn = get_connection()
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 检查物料是否已存在，防止重复添加
            cursor.execute(
                "SELECT id FROM order_materials WHERE order_id = %s AND material_name = %s",
                (self.selected_order_id, material_name)
            )
            existing = cursor.fetchone()

            if existing:
                cursor.close()
                conn.close()
                alert(f"物料「{material_name}」已存在，请勿重复添加！", "提示")
                return

            # 自动计算状态
            if required == 0:
                status = "待备料"
            else:
                status = "缺料"

            cursor.execute("""
                INSERT INTO order_materials (order_id, material_name, material_type, unit, required_qty, prepared_qty, prep_status, remark, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                self.selected_order_id,
                material_name,
                data.get("material_type", ""),
                data.get("unit", "米"),
                required,
                0,  # 新增物料初始已备数量为0
                status,
                data.get("remark", ""),
                now
            ))
            conn.commit()
            cursor.close()
            conn.close()

            # 记录历史
            self._save_history(self.selected_order_id, "添加物料", material_name, {
                "required": required,
                "unit": data.get("unit", "米")
            })

            self.load_data()
            self._load_prep_detail(self.selected_order_id)
            alert(f"物料「{material_name}」添加成功！", "操作成功")

        popup_form(f"➕ 添加物料 - {display_no}", fields, on_save, width=400)

    def edit_selected_material(self):
        sel = self.detail_tree.selection()
        if not sel:
            alert("请选择要编辑的物料", "提示")
            return

        values = self.detail_tree.item(sel[0])["values"]
        material_name = values[0]

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM order_materials WHERE order_id=%s AND material_name=%s ORDER BY id DESC LIMIT 1",
            (self.selected_order_id, material_name)
        )
        m = cursor.fetchone()
        cursor.close()
        conn.close()

        if not m:
            return

        mat = dict(m)

        if mat.get("locked") == 1:
            alert("该物料已锁定，请先点击「🔓 解锁」按钮解除锁定后再编辑！", "提示")
            return

        fields = [
            ("物料名称", "material_name", mat.get("material_name", ""), "entry"),
            ("规格", "spec", mat.get("spec", ""), "entry"),
            ("单位", "unit", mat.get("unit", "米"), "entry"),
            ("需求数量", "required_qty", str(mat.get("required_qty", 0)), "number"),
            ("已备数量", "prepared_qty", str(mat.get("prepared_qty", 0)), "number"),
            ("备注", "remark", mat.get("remark", ""), "entry"),
        ]

        def on_save(data):
            req = float(data.get("required_qty", 0))
            prep = float(data.get("prepared_qty", 0))

            if prep == 0 and req > 0:
                status = "缺料"
            elif prep < req:
                status = "部分缺料"
            elif prep >= req:
                status = "已备齐"
            else:
                status = "待备料"

            conn = get_connection()
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                UPDATE order_materials SET
                    material_name=%s, spec=%s, unit=%s, required_qty=%s, prepared_qty=%s, prep_status=%s, remark=%s, updated_at=%s
                WHERE id=%s
            """, (
                data.get("material_name", ""),
                data.get("spec", ""),
                data.get("unit", "米"),
                req,
                prep,
                status,
                data.get("remark", ""),
                now,
                mat.get("id")
            ))
            conn.commit()
            cursor.close()
            conn.close()

            self._save_history(self.selected_order_id, "编辑物料", data.get("material_name", ""), {
                "old_prepared": mat.get("prepared_qty", 0),
                "new_prepared": prep
            })

            self.load_data()
            self._load_prep_detail(self.selected_order_id)
            alert("物料已更新！", "保存成功")

        popup_form("编辑物料", fields, on_save, width=400)

    def unlock_selected_material(self):
        """解锁选中的物料"""
        sel = self.detail_tree.selection()
        if not sel:
            alert("请选择要解锁的物料", "提示")
            return

        values = self.detail_tree.item(sel[0])["values"]
        material_name = values[0]

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM order_materials WHERE order_id=%s AND material_name=%s ORDER BY id DESC LIMIT 1",
            (self.selected_order_id, material_name)
        )
        m = cursor.fetchone()
        cursor.close()
        conn.close()

        if not m:
            return

        mat = dict(m)

        if mat.get("locked") == 0:
            alert("该物料已经是解锁状态，无需重复解锁！", "提示")
            return

        confirm = messagebox.askyesno("确认解锁",
            f"确定要解锁物料「{material_name}」吗？\n\n解锁后可以手动编辑该物料。")

        if not confirm:
            return

        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            UPDATE order_materials SET locked=0, updated_at=%s WHERE id=%s
        """, (now, mat.get("id")))
        conn.commit()
        cursor.close()
        conn.close()

        self._save_history(self.selected_order_id, "解锁物料", material_name, {})
        self._load_prep_detail(self.selected_order_id)
        alert("物料已解锁，可以手动编辑！", "解锁成功")

    def on_material_double_click(self, event):
        self.edit_selected_material()

    def show_material_context_menu(self, event):
        item = self.detail_tree.identify_row(event.y)
        if not item:
            return
        self.detail_tree.selection_set(item)

        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="📝 编辑", command=self.edit_selected_material)
        menu.add_command(label="✅ 标记已备齐", command=self._mark_material_done)
        menu.add_command(label="🔢 添加入库", command=self._add_prepared_qty)
        menu.add_separator()
        menu.add_command(label="🗑️ 删除", command=self._delete_material)
        menu.post(event.x_root, event.y_root)

    def _mark_material_done(self):
        sel = self.detail_tree.selection()
        if not sel:
            return

        values = self.detail_tree.item(sel[0])["values"]
        material_name = values[0]

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM order_materials WHERE order_id=%s AND material_name=%s ORDER BY id DESC LIMIT 1",
            (self.selected_order_id, material_name)
        )
        m = cursor.fetchone()

        if m:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("UPDATE order_materials SET prepared_qty=required_qty, prep_status='已备齐', updated_at=%s WHERE id=%s",
                        (now, m["id"]))
            conn.commit()

            self._save_history(self.selected_order_id, "标记已备齐", material_name)

        cursor.close()
        conn.close()
        self.load_data()
        self._load_prep_detail(self.selected_order_id)

    def _add_prepared_qty(self):
        sel = self.detail_tree.selection()
        if not sel:
            return

        values = self.detail_tree.item(sel[0])["values"]
        material_name = values[0]

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM order_materials WHERE order_id=%s AND material_name=%s ORDER BY id DESC LIMIT 1",
            (self.selected_order_id, material_name)
        )
        m = cursor.fetchone()
        cursor.close()
        conn.close()

        if not m:
            return

        # MySQL DictCursor转dict
        mat = dict(m)

        fields = [
            ("物料", "info", f"{material_name}", "label"),
            ("当前已备", "current", f"{mat.get('prepared_qty', 0)} {mat.get('unit', '')}", "label"),
            ("需求数量", "required", f"{mat.get('required_qty', 0)} {mat.get('unit', '')}", "label"),
            ("入库数量", "add_qty", "0", "number"),
            ("入库批次号", "batch_no", "", "entry"),
            ("备注", "remark", "", "entry"),
        ]

        def on_save(data):
            add_qty = float(data.get("add_qty", 0))
            if add_qty <= 0:
                alert("入库数量必须大于0", "提示")
                return

            new_prep = mat.get("prepared_qty", 0) + add_qty
            req = mat.get("required_qty", 0)

            if new_prep >= req:
                status = "已备齐"
            elif new_prep > 0:
                status = "部分缺料"
            else:
                status = "缺料"

            conn = get_connection()
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("UPDATE order_materials SET prepared_qty=%s, prep_status=%s, updated_at=%s WHERE id=%s",
                        (new_prep, status, now, mat.get("id")))
            conn.commit()
            cursor.close()
            conn.close()

            batch_no = data.get("batch_no", "").strip()
            remark = data.get("remark", "").strip()
            detail = {"add_qty": add_qty, "unit": mat.get("unit", ""), "total": new_prep}
            if batch_no:
                detail["batch_no"] = batch_no
            if remark:
                detail["remark"] = remark

            self._save_history(self.selected_order_id, "物料入库", material_name, detail)

            self.load_data()
            self._load_prep_detail(self.selected_order_id)

            msg = f"物料「{material_name}」已入库 {add_qty} {m.get('unit', '')}"
            alert(msg, "操作成功")

        popup_form("添加入库数量", fields, on_save, width=350)

    def _delete_material(self):
        sel = self.detail_tree.selection()
        if not sel:
            return

        values = self.detail_tree.item(sel[0])["values"]
        material_name = values[0]

        if not messagebox.askyesno("确认", f"确定删除物料「{material_name}」？"):
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM order_materials WHERE order_id=%s AND material_name=%s ORDER BY id DESC LIMIT 1",
            (self.selected_order_id, material_name)
        )
        row = cursor.fetchone()
        if row:
            cursor.execute("DELETE FROM order_materials WHERE id=%s", (row['id'],))
        conn.commit()
        cursor.close()
        conn.close()

        self.load_data()
        self._load_prep_detail(self.selected_order_id)

    def _save_history(self, order_id, action, material_name, detail=None):
        """保存历史记录"""
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        detail_str = str(detail) if detail else ""

        cursor.execute("""
            INSERT INTO material_history (order_id, action, material_name, detail, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (order_id, action, material_name, detail_str, now))
        conn.commit()
        cursor.close()
        conn.close()

    def open_material_rules(self):
        """打开物料计算规则配置"""
        from desktop.views.dialogs import MaterialRulesContainerDialog
        MaterialRulesContainerDialog(self)

    def calculate_selected_materials(self):
        """计算选中订单的物料"""
        if not self.selected_order_id:
            messagebox.showwarning("提示", "请先选择一个订单！")
            return

        from models.database import get_connection
        from utils.material_calculator import MaterialCalculator
        import json

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT po.*, o.order_no, o.customer_name, o.customer_group, o.product_type,
                   o.quantity, o.unit, o.extra_params
            FROM production_orders po
            JOIN orders o ON o.id = po.order_id
            WHERE o.id = %s
            AND COALESCE(o.is_archived, 0) = 0
        """, (self.selected_order_id,))
        order_row = cursor.fetchone()

        if not order_row:
            cursor.execute("""
                SELECT o.* FROM orders o WHERE o.id = %s
            """, (self.selected_order_id,))
            order_row = cursor.fetchone()

        if not order_row:
            cursor.close()
            conn.close()
            messagebox.showwarning("提示", "未找到选中的订单")
            return

        cursor.execute(
            "SELECT COUNT(*) as cnt FROM order_materials WHERE order_id = %s",
            (self.selected_order_id,)
        )
        existing = cursor.fetchone()
        if existing and existing["cnt"] > 0:
            cursor.close()
            conn.close()
            if not messagebox.askyesno("提示", "该订单已有物料配置，是否重新计算？\n（将删除现有物料后重新计算）"):
                return

            cursor = conn.cursor()
            cursor.execute("DELETE FROM order_materials WHERE order_id = %s", (self.selected_order_id,))
            conn.commit()

        order_params = {
            "product_type": order_row["product_type"],
            "quantity": order_row["quantity"],
            "unit": order_row.get("unit", "米")
        }

        extra = order_row.get("extra_params") or {}
        if isinstance(extra, str):
            try:
                extra = json.loads(extra)
            except Exception:
                extra = {}
        order_params.update(extra)

        calculator = MaterialCalculator(order_params)
        materials = calculator.calculate_material_types()

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total_materials = 0
        missing_info = []
        query_log = {
            "order_id": self.selected_order_id,
            "order_no": order_row.get("order_no", "未知"),
            "product_type": order_row.get("product_type", ""),
            "timestamp": now,
            "materials_query": [],
            "inventory_results": []
        }

        for m in materials:
            material_name = m["material_name"]
            spec_value = m.get("spec_value")
            spec_unit = m.get("spec_unit", "")
            qty_value = m.get("qty_value")
            qty_unit = m.get("qty_unit", "待定")
            missing_params = m.get("missing_params", [])

            spec_text = ""
            if spec_value:
                spec_text = f"{spec_value}{spec_unit}"

            required_qty = qty_value if qty_value is not None else 0
            unit = qty_unit if qty_unit else "待定"

            try:
                cursor.execute("""
                    INSERT INTO order_materials (order_id, material_name, spec, unit,
                        required_qty, prepared_qty, prep_status, locked, created_at)
                    VALUES (%s, %s, %s, %s, %s, 0, '待备料', 1, %s)
                """, (self.selected_order_id, material_name, spec_text, unit, required_qty, now))
                total_materials += 1
            except Exception as e:
                print(f"添加物料失败: {e}")

            if missing_params:
                missing_info.append(f"• {material_name}：缺少 {', '.join(missing_params)}")

            query_log["materials_query"].append({
                "material_name": material_name,
                "spec": spec_text,
                "unit": unit,
                "required_qty": required_qty
            })

        conn.commit()
        cursor.close()
        conn.close()

        if INV_DB_AVAILABLE:
            for m in query_log["materials_query"]:
                try:
                    stock_results = inv_db.search_by_material(
                        material_name=m["material_name"],
                        spec=m["spec"] if m["spec"] else None
                    )
                    total_stock = sum(float(r.get("current_qty", 0) or 0) for r in stock_results)
                    
                    warehouse_info = []
                    for r in stock_results:
                        warehouse_info.append({
                            "warehouse": r.get("warehouse", ""),
                            "stock": float(r.get("current_qty", 0) or 0)
                        })
                    
                    m["inventory_check"] = {
                        "total_stock": total_stock,
                        "available": total_stock >= m["required_qty"],
                        "shortage": max(0, m["required_qty"] - total_stock),
                        "warehouses": warehouse_info
                    }
                    query_log["inventory_results"].append({
                        "material_name": m["material_name"],
                        "required": m["required_qty"],
                        "total_stock": total_stock,
                        "available": total_stock >= m["required_qty"],
                        "warehouses": warehouse_info
                    })
                except Exception as e:
                    logger.warning(f"[material_prep] 库存查询失败: {e}")
                    m["inventory_check"] = {"error": str(e)}
                    query_log["inventory_results"].append({
                        "material_name": m["material_name"],
                        "error": str(e)
                    })
        else:
            logger.warning("[material_prep] 库存系统不可用，跳过库存查询")

        self.load_data()
        self._load_prep_detail(self.selected_order_id)

        msg = f"物料计算完成！\n已添加 {total_materials} 种物料"
        if missing_info:
            msg += f"\n\n⚠️ 以下物料缺少参数：\n" + "\n".join(missing_info[:5])
            if len(missing_info) > 5:
                msg += f"\n... 还有 {len(missing_info) - 5} 条"
        
        if INV_DB_AVAILABLE:
            msg += f"\n\n库存查询结果已生成，可点击「查看库存」查看详情"
        
        messagebox.showinfo("完成", msg)

        if INV_DB_AVAILABLE and query_log["inventory_results"]:
            self._show_inventory_query_dialog(query_log)

    def batch_calculate_materials(self):
        """批量计算物料"""
        from models.database import get_connection
        from utils.material_calculator import MaterialCalculator
        import json

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT po.*, o.order_no, o.customer_name, o.customer_group, o.product_type,
                   o.quantity, o.unit, o.extra_params
            FROM production_orders po
            JOIN orders o ON po.order_id = o.id
            WHERE po.status IN ({','.join(['%s'] * 3)})
            AND COALESCE(o.is_archived, 0) = 0
            ORDER BY po.order_no
        """, (
            ProductionStatus.PENDING.value,
            ProductionStatus.IN_PROGRESS.value,
            ProductionStatus.PAUSED.value
        ))
        work_orders = cursor.fetchall()
        cursor.close()
        conn.close()

        if not work_orders:
            messagebox.showinfo("提示", f"没有{ProductionStatus.SCHEDULED.value}的生产工单")
            return

        from desktop.views.dialogs import BatchCalcMaterialDialog
        BatchCalcMaterialDialog(self, work_orders)

    def _publish_material_demand(self):
        """发布用料需求到微信报工系统"""
        if not self.selected_order_id:
            alert("请先选择订单！", "提示")
            return

        order_id = self.selected_order_id
        order = OrderDAO.get_by_id(order_id)
        if not order:
            messagebox.showerror("错误", f"找不到订单 {order_id}")
            return

        order_no = order['order_no']
        display_no = self._get_display_order_no(order_id) or order_no

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM order_materials WHERE order_id=%s", (order_id,))
        materials = cursor.fetchall()
        cursor.close()
        conn.close()

        shortage_materials = []
        for m in materials:
            mat = dict(m)
            req = mat.get("required_qty") or 0
            prep = mat.get("prepared_qty") or 0
            if req > prep:
                shortage_materials.append({
                    'material_name': mat.get('material_name', ''),
                    'spec': mat.get('spec', '') or '',
                    'unit': mat.get('unit', '') or '',
                    'required_qty': req,
                    'shortage_qty': max(0, req - prep)
                })

        if not shortage_materials:
            messagebox.showinfo("提示", f"订单 {display_no} 没有缺料物料，无需发布")
            return

        if messagebox.askyesno("确认发布", f"确定要将订单 {display_no} 的 {len(shortage_materials)} 项用料需求发布到微信报工系统吗？"):
            try:
                from services.wechat_report_service import WeChatReportService

                success_count = 0
                fail_count = 0

                for mat in shortage_materials:
                    task_data = {
                        'order_no': order_no,
                        'process_name': mat['material_name'],
                        'process_code': 'M01',
                        'quantity': mat['shortage_qty'],
                        'planned_qty': mat['required_qty'],
                        'priority': 'normal',
                        'remark': f"物料: {mat['material_name']} {mat['spec']} {mat['unit']}"
                    }
                    result = WeChatReportService.publish_task_to_operator(task_data, 'OP001')
                    if result.get('success'):
                        success_count += 1
                    else:
                        fail_count += 1
                    time.sleep(1)

                log_ui("材料备料", "发布用料需求", f"{display_no} (成功:{success_count}, 失败:{fail_count})")
                messagebox.showinfo("发布成功", f"订单 {display_no} 的用料需求已发布到微信报工系统\n成功: {success_count}, 失败: {fail_count}")
            except Exception as e:
                import traceback
                log_ui("材料备料", "发布用料需求失败", str(e))
                messagebox.showerror("发布失败", f"发布用料需求失败: {str(e)}\n{traceback.format_exc()}")

    def _retry_dead_tasks(self):
        """重发死信 — 显示微信报工死信列表并支持批量重发"""
        from services.wechat_report_service import WeChatReportService

        try:
            dead_tasks = WeChatReportService.get_dead_tasks()
        except Exception as e:
            alert(f"查询死信失败：{e}", "错误")
            return

        if not dead_tasks:
            alert("当前没有死信任务", "提示")
            return

        dialog = tk.Toplevel(self)
        dialog.title("报工死信重发")
        dialog.geometry("820x420")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        dialog.configure(bg=COLORS["bg_main"])

        header = tk.Frame(dialog, bg=COLORS["bg_main"])
        header.pack(fill=tk.X, padx=LAYOUT["padding"]["medium"], pady=(LAYOUT["padding"]["medium"], 0))
        tk.Label(header, text=f"报工死信列表（共 {len(dead_tasks)} 条）",
                 font=FONTS["subtitle"], bg=COLORS["bg_main"],
                 fg="red").pack(anchor=tk.W)

        tree_frame = tk.Frame(dialog, bg=COLORS["bg_main"])
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=LAYOUT["padding"]["medium"], pady=LAYOUT["padding"]["medium"])

        columns = ("select", "order_no", "process", "retry", "error", "time")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=12)
        tree.heading("select", text="☑")
        tree.heading("order_no", text="订单号")
        tree.heading("process", text="工序")
        tree.heading("retry", text="重试")
        tree.heading("error", text="最后错误")
        tree.heading("time", text="更新时间")
        tree.column("select", width=30, anchor="center")
        tree.column("order_no", width=130)
        tree.column("process", width=100)
        tree.column("retry", width=50, anchor="center")
        tree.column("error", width=320)
        tree.column("time", width=130)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(fill=tk.BOTH, expand=True)

        select_vars = {}
        for i, dt in enumerate(dead_tasks):
            v = tk.BooleanVar(value=True)
            select_vars[dt['id']] = v
            error_text = (dt.get('last_error') or '未知')[:60]
            time_text = str(dt.get('updated_at') or dt.get('created_at', ''))[:19]
            tree.insert("", tk.END, iid=str(dt['id']),
                       values=("☑", dt.get('order_no', ''), dt.get('process_name', ''),
                               dt.get('retry_count', 0), error_text, time_text))

        def toggle_all():
            new_val = not all(v.get() for v in select_vars.values())
            for v in select_vars.values():
                v.set(new_val)
            for item in tree.get_children():
                tree.set(item, "select", "☑" if new_val else "☐")

        def do_retry():
            selected = [tid for tid, v in select_vars.items() if v.get()]
            if not selected:
                alert("请至少选择一条死信", "提示")
                return
            success_count = 0
            fail_count = 0
            for tid in selected:
                tree.set(str(tid), "select", "⏳")
                dialog.update()
                try:
                    result = WeChatReportService.retry_dead_task(tid)
                    if result.get('skipped'):
                        tree.set(str(tid), "select", "⏭")
                    elif result['success']:
                        tree.set(str(tid), "select", "✅")
                        success_count += 1
                    else:
                        tree.set(str(tid), "select", "❌")
                        fail_count += 1
                except Exception:
                    tree.set(str(tid), "select", "❌")
                    fail_count += 1
            dialog.destroy()
            alert(f"死信重发完成\n成功 {success_count} 条，失败 {fail_count} 条", "结果")

        btn_frame = tk.Frame(dialog, bg=COLORS["bg_main"])
        btn_frame.pack(fill=tk.X, padx=LAYOUT["padding"]["medium"], pady=(0, LAYOUT["padding"]["medium"]))
        ttk.Button(btn_frame, text="全选/取消", command=toggle_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🔄 重发选中", command=do_retry).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="关闭", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)

    def show_history(self):
        MaterialPrepHistoryDialog(self)

    def on_double_click(self, event):
        self.on_order_select()
        self.edit_material_prep()

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.tree.selection_set(item)

        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="📝 编辑订单备料", command=self.edit_material_prep)
        menu.add_command(label="➕ 添加物料", command=self.add_material)
        menu.add_separator()
        menu.add_command(label="✅ 全部标记已备齐", command=self._mark_all_done)
        menu.add_command(label="🔄 重置", command=self._reset_prep)
        menu.post(event.x_root, event.y_root)

    def _edit_selected_prep(self):
        self.edit_material_prep()

    def _mark_all_done(self):
        if not self.selected_order_id:
            return
        order = OrderDAO.get_by_id(self.selected_order_id)
        display_no = self._get_display_order_no(self.selected_order_id) or order.get('order_no', '')
        if messagebox.askyesno("确认", "确定将该订单所有物料标记为已备齐？"):
            conn = get_connection()
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("UPDATE order_materials SET prepared_qty=required_qty, prep_status='已备齐', updated_at=%s WHERE order_id=%s",
                        (now, self.selected_order_id))
            conn.commit()
            cursor.close()
            conn.close()

            self._save_history(self.selected_order_id, "全部标记已备齐", "全部物料")

            self.load_data()
            self._load_prep_detail(self.selected_order_id)
            alert(f"订单 {display_no} 已全部备齐！", "操作成功")

            self._notify_inventory_system(order)

    def _reset_prep(self):
        if not self.selected_order_id:
            return
        order = OrderDAO.get_by_id(self.selected_order_id)
        display_no = self._get_display_order_no(self.selected_order_id) or order.get('order_no', '')
        if messagebox.askyesno("确认", f"确定重置订单 {display_no} 的备料状态？"):
            conn = get_connection()
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("UPDATE order_materials SET prepared_qty=0, prep_status='待备料', updated_at=%s WHERE order_id=%s",
                        (now, self.selected_order_id))
            conn.commit()
            cursor.close()
            conn.close()

            self._save_history(self.selected_order_id, "重置备料", "全部物料")

            self.load_data()
            self._load_prep_detail(self.selected_order_id)

    def edit_material_prep(self):
        if not self.selected_order_id:
            alert("请先选择订单", "提示")
            return

        order = OrderDAO.get_by_id(self.selected_order_id)
        if not order:
            return
        display_no = self._get_display_order_no(self.selected_order_id) or order.get('order_no', '')

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM order_materials WHERE order_id=%s",
            (self.selected_order_id,)
        )
        materials = cursor.fetchone()["cnt"]
        cursor.close()
        conn.close()

        fields = [
            ("订单号", "order_no", display_no, "label"),
            ("客户群", "customer", order.get("customer_group", "") or "无", "label"),
            ("产品", "product", order.get("product_type", ""), "label"),
            ("物料数", "material_count", str(materials), "label"),
            ("整体状态", "status", self._get_prep_status(self.selected_order_id), "label"),
        ]

        def on_save(data):
            self.load_data()
            self._load_prep_detail(self.selected_order_id)
            alert("已刷新备料状态", "完成")

        popup_form(f"备料概览 - {display_no}", fields, on_save, width=400)

    def _save_as_template(self):
        """保存当前订单物料为模板"""
        if not self.selected_order_id:
            alert("请先选择订单", "提示")
            return

        order = OrderDAO.get_by_id(self.selected_order_id)
        if not order:
            return
        display_no = self._get_display_order_no(self.selected_order_id) or order.get('order_no', '')

        # 获取当前订单的物料列表
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT material_name, unit, required_qty, remark FROM order_materials WHERE order_id=%s",
            (self.selected_order_id,)
        )
        materials = cursor.fetchall()
        cursor.close()
        conn.close()

        if not materials:
            alert("当前订单没有物料明细，请先添加物料后再保存模板", "提示")
            return

        # 获取现有模板列表用于重名检测
        existing_templates = get_all_templates()
        existing_names = [t.get("name") for t in existing_templates]

        fields = [
            ("模板名称", "template_name", "", "entry"),
            ("模板描述", "description", "", "entry"),
            ("物料数量", "info", f"共 {len(materials)} 种物料", "label"),
        ]

        def on_save(data):
            template_name = data.get("template_name", "").strip()
            if not template_name:
                alert("请输入模板名称", "提示")
                return

            # 准备物料数据
            template_materials = []
            for m in materials:
                mat = dict(m) if hasattr(m, 'keys') else m
                template_materials.append({
                    "name": mat.get("material_name", ""),
                    "unit": mat.get("unit", "米"),
                    "required_qty": mat.get("required_qty", 0),
                    "remark": mat.get("remark", "")
                })

            save_template(template_name, template_materials, data.get("description", ""))

            self._save_history(self.selected_order_id, "保存模板", template_name, {
                "material_count": len(template_materials)
            })

            alert(f"模板「{template_name}」保存成功！", "操作成功")

        popup_form(f"💾 保存模板 - {display_no}", fields, on_save, width=400)

    def _load_template(self):
        """载入模板应用到当前订单"""
        if not self.selected_order_id:
            alert("请先选择订单", "提示")
            return

        order = OrderDAO.get_by_id(self.selected_order_id)
        if not order:
            return
        display_no = self._get_display_order_no(self.selected_order_id) or order.get('order_no', '')

        templates = get_all_templates()
        if not templates:
            alert("暂无可用模板，请先保存模板", "提示")
            return

        template_names = [t.get("name", "") for t in templates]

        # 选择模板
        fields = [
            ("选择模板", "template_name", template_names[0], "combo", template_names),
            ("应用模式", "mode", "追加（保留现有物料）", "combo", ["追加（保留现有物料）", "覆盖（清空后应用）"]),
        ]

        def on_save(data):
            selected_name = data.get("template_name", "")
            mode = data.get("mode", "")

            template = get_template(selected_name)
            if not template:
                return

            materials = template.get("materials", [])
            if not materials:
                alert("模板为空", "提示")
                return

            conn = get_connection()
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 根据模式处理
            if "覆盖" in mode:
                # 清空现有物料
                cursor.execute("DELETE FROM order_materials WHERE order_id=%s", (self.selected_order_id,))

            # 添加模板物料
            added_count = 0
            for mat in materials:
                # 检查是否已存在同名物料
                cursor.execute(
                    "SELECT id FROM order_materials WHERE order_id=%s AND material_name=%s ORDER BY id DESC LIMIT 1",
                    (self.selected_order_id, mat.get("name", ""))
                )
                existing = cursor.fetchone()

                if existing:
                    continue  # 跳过已存在的物料

                required = float(mat.get("required_qty", 0))
                status = "缺料" if required > 0 else "待备料"

                cursor.execute("""
                    INSERT INTO order_materials (order_id, material_name, unit, required_qty, prepared_qty, prep_status, remark, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    self.selected_order_id,
                    mat.get("name", ""),
                    mat.get("unit", "米"),
                    required,
                    0,
                    status,
                    mat.get("remark", ""),
                    now
                ))
                added_count += 1

            conn.commit()
            cursor.close()
            conn.close()

            self._save_history(self.selected_order_id, "载入模板", selected_name, {
                "mode": mode,
                "added_count": added_count
            })

            self.load_data()
            self._load_prep_detail(self.selected_order_id)

            alert(f"模板「{selected_name}」已应用，添加了 {added_count} 种物料", "操作成功")

        popup_form(f"📥 载入模板 - {display_no}", fields, on_save, width=400)

    def _manage_templates(self):
        MaterialTemplateManagerDialog(self)

    def _notify_inventory_system(self, order):
        """通知库存系统物料已备齐并等待反馈"""
        if not order:
            return

        notifier = get_inventory_notifier()
        if not notifier.is_enabled():
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT material_name, spec, unit, required_qty, prepared_qty FROM order_materials WHERE order_id=%s AND required_qty > 0",
                (self.selected_order_id,)
            )
            materials = cursor.fetchall()
            cursor.close()
            conn.close()

            if not materials:
                return

            material_list = []
            for m in materials:
                mat = dict(m) if hasattr(m, 'keys') else m
                material_list.append({
                    "name": mat.get("material_name", ""),
                    "spec": mat.get("spec", "") or "",
                    "qty": mat.get("required_qty", 0),
                    "unit": mat.get("unit", "米")
                })

            delivery_date = order.get("delivery_date")
            deadline = str(delivery_date)[:10] if delivery_date else None

            result = notifier.notify_material_prepared(
                order_no=order.get("order_no", ""),
                customer_name=order.get("customer_name", ""),
                materials=material_list,
                deadline=deadline
            )

            if result and result.get("error"):
                logger.warning(f"通知库存系统失败: {result.get('message')}")
                return

            notification_id = result.get("notification_id")
            if not notification_id:
                logger.warning("通知库存系统未返回notification_id")
                return

            logger.info(f"已通知库存系统，等待响应: 订单 {order.get('order_no')}, notification_id={notification_id}")

            self._wait_inventory_response(order, notification_id, material_list)

        except Exception as e:
            logger.error(f"通知库存系统异常: {e}")

    def _wait_inventory_response(self, order, notification_id, material_list):
        """后台线程等待库存系统响应"""
        def do_wait():
            notifier = get_inventory_notifier()
            response = notifier.wait_for_response(notification_id, timeout=600, poll_interval=3)

            self.after(0, lambda: self._handle_inventory_response(order, response, material_list))

        threading.Thread(target=do_wait, daemon=True).start()

    def _handle_inventory_response(self, order, response, material_list):
        """处理库存系统响应，更新物料状态"""
        if response.get("status") == "disabled":
            return

        display_no_inv = self._get_display_order_no(self.selected_order_id) or ''

        if response.get("status") == "timeout":
            messagebox.showwarning("库存响应超时",
                f"等待库存系统响应超时\n订单: {display_no_inv or order.get('order_no', '')}\n\n请手动确认物料库存情况",
                parent=self)
            return

        inventory_check = response.get("inventory_check", [])
        response_status = response.get("status")
        response_msg = response.get("response", {}).get("message", "")

        check_map = {}
        for check in inventory_check:
            key = check.get("name", "")
            check_map[key] = check

        for mat in material_list:
            mat_name = mat.get("name", "")
            check = check_map.get(mat_name, {})

            if check.get("can_supply"):
                status = "库存确认"
            else:
                status = "库存不足"

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE order_materials
                SET prep_status=%s, remark=CONCAT(IFNULL(remark, ''), ' [', %s, ']')
                WHERE order_id=%s AND material_name=%s
            """, (status, response_msg, self.selected_order_id, mat_name))
            conn.commit()
            cursor.close()
            conn.close()

        self.load_data()
        self._load_prep_detail(self.selected_order_id)

        if response_status == "confirmed":
            messagebox.showinfo("库存确认",
                f"库存系统已确认供应\n订单: {display_no_inv or order.get('order_no', '')}\n\n所有物料库存充足，可继续生产",
                parent=self)
        elif response_status == "partial_confirmed":
            messagebox.showwarning("库存部分确认",
                f"库存系统部分物料可供应\n订单: {display_no_inv or order.get('order_no', '')}\n\n{response_msg}\n\n请检查库存不足的物料",
                parent=self)
        elif response_status == "rejected":
            messagebox.showerror("库存拒绝",
                f"库存系统拒绝供应\n订单: {display_no_inv or order.get('order_no', '')}\n\n{response_msg}\n\n请先补充库存后再继续",
                parent=self)

    def _show_inventory_query_dialog(self, query_log):
        """显示库存查询结果弹窗"""
        from desktop.views.dialogs import MaterialQueryLogDialog
        dialog = MaterialQueryLogDialog(self, query_log)
        dialog.show()
