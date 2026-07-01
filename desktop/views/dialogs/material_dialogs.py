# -*- coding: utf-8 -*-
import json
import tkinter as tk
import logging
from datetime import datetime
from tkinter import ttk, messagebox
from config import COLORS, FONTS
from constants import ProductionStatus
from models.database import get_connection
from utils.material_calculator import MaterialCalculator
from desktop.views.dialogs import popup_form, alert
from desktop.views.dialogs.base import BaseDialog
from utils.material_templates import get_all_templates, get_template, delete_template, rename_template

logger = logging.getLogger("material_dialogs")


class MaterialPrepHistoryDialog(BaseDialog):
    def __init__(self, parent):
        self._history_data = []
        super().__init__(parent, title="📜 备料历史记录", width=800, height=500, resizable=True)

    def _build_ui(self):
        frame = tk.Frame(self.window)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        cols = ("order", "material", "action", "detail", "time")
        tree = ttk.Treeview(frame, columns=cols, show="headings", height=18)

        for col, txt, w in [
            ("order", "订单号", 140), ("material", "物料", 120), ("action", "操作", 100),
            ("detail", "详情", 200), ("time", "时间", 140)
        ]:
            tree.heading(col, text=txt)
            tree.column(col, width=w)

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT h.*, o.order_no
            FROM material_history h
            LEFT JOIN orders o ON h.order_id = o.id
            ORDER BY h.created_at DESC
            LIMIT 200
        """)
        self._history_data = cursor.fetchall()
        cursor.close()
        conn.close()

        for h in self._history_data:
            tree.insert("", tk.END, values=(
                h["order_no"] or f"ID:{h['order_id']}",
                h["material_name"],
                h["action"],
                h.get("detail", ""),
                h.get("created_at", "")[:16]
            ))

        ttk.Button(self.window, text="关闭", command=self._on_cancel).pack(pady=10)

    def _on_cancel(self):
        self.window.destroy()


class MaterialQueryLogDialog:
    """库存查询日志弹窗"""

    def __init__(self, parent, query_log):
        self.parent = parent
        self.query_log = query_log
        self.window = tk.Toplevel(parent)
        self.window.title("📊 库存查询日志")
        self.window.geometry("900x600")
        self.window.transient(parent)
        self.window.grab_set()

        self._build_ui()
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        main_frame = tk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        header_frame = tk.Frame(main_frame, bg="#E3F2FD", padx=10, pady=8)
        header_frame.pack(fill=tk.X)

        info_text = f"订单: {self.query_log.get('order_no', '未知')} | 产品类型: {self.query_log.get('product_type', '')} | 时间: {self.query_log.get('timestamp', '')}"
        tk.Label(header_frame, text=info_text, font=FONTS["body"], bg="#E3F2FD").pack(anchor="w")

        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=5)

        query_frame = tk.Frame(notebook)
        notebook.add(query_frame, text="📋 查询参数")
        self._build_query_tab(query_frame)

        result_frame = tk.Frame(notebook)
        notebook.add(result_frame, text="📦 库存结果")
        self._build_result_tab(result_frame)

        raw_frame = tk.Frame(notebook)
        notebook.add(raw_frame, text="📄 原始数据")
        self._build_raw_tab(raw_frame)

        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Button(btn_frame, text="💾 保存JSON", command=self._save_json).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📊 保存CSV", command=self._save_csv).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="关闭", command=self._on_close).pack(side=tk.RIGHT, padx=5)

    def _build_query_tab(self, parent):
        frame = tk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        cols = ("material_name", "spec", "unit", "required_qty")
        tree = ttk.Treeview(frame, columns=cols, show="headings")

        for col, txt, w in [
            ("material_name", "物料名称", 200),
            ("spec", "规格", 200),
            ("unit", "单位", 80),
            ("required_qty", "需求数量", 100)
        ]:
            tree.heading(col, text=txt)
            tree.column(col, width=w, anchor="center")

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for m in self.query_log.get("materials_query", []):
            tree.insert("", tk.END, values=(
                m.get("material_name", ""),
                m.get("spec", ""),
                m.get("unit", ""),
                str(m.get("required_qty", 0))
            ))

    def _build_result_tab(self, parent):
        frame = tk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        cols = ("material_name", "required", "stock", "status", "warehouse")
        tree = ttk.Treeview(frame, columns=cols, show="headings")

        for col, txt, w in [
            ("material_name", "物料名称", 180),
            ("required", "需求数量", 100),
            ("stock", "库存数量", 100),
            ("status", "状态", 80),
            ("warehouse", "仓库分布", 300)
        ]:
            tree.heading(col, text=txt)
            tree.column(col, width=w, anchor="center")

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for r in self.query_log.get("inventory_results", []):
            available = r.get("available", False)
            status = "✅ 充足" if available else "❌ 不足"

            warehouses = r.get("warehouses", [])
            warehouse_text = "; ".join([f"{w.get('warehouse', '')}: {w.get('stock', 0)}" for w in warehouses]) if warehouses else "无数据"

            item_id = tree.insert("", tk.END, values=(
                r.get("material_name", ""),
                str(r.get("required", 0)),
                str(r.get("total_stock", 0)),
                status,
                warehouse_text
            ))

            if not available:
                tree.item(item_id, tags=("shortage",))

        tree.tag_configure("shortage", background="#FFEBEE")

    def _build_raw_tab(self, parent):
        frame = tk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        text_widget = tk.Text(frame, wrap=tk.NONE, font=("Consolas", 10))
        scrollbar_y = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text_widget.yview)
        scrollbar_x = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=text_widget.xview)
        text_widget.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)

        raw_json = json.dumps(self.query_log, ensure_ascii=False, indent=2)
        text_widget.insert("1.0", raw_json)
        text_widget.config(state="disabled")

    def _save_json(self):
        from tkinter import filedialog
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=f"inventory_query_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        if filename:
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(self.query_log, f, ensure_ascii=False, indent=2)
                messagebox.showinfo("保存成功", f"已保存到:\n{filename}")
            except Exception as e:
                messagebox.showerror("保存失败", str(e))

    def _save_csv(self):
        from tkinter import filedialog
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"inventory_query_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        if filename:
            try:
                import csv
                with open(filename, "w", encoding="utf-8-sig", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["物料名称", "规格", "单位", "需求数量", "库存数量", "是否充足", "仓库分布"])

                    for r in self.query_log.get("inventory_results", []):
                        available = r.get("available", False)
                        warehouses = r.get("warehouses", [])
                        warehouse_text = "; ".join([f"{w.get('warehouse', '')}: {w.get('stock', 0)}" for w in warehouses])

                        writer.writerow([
                            r.get("material_name", ""),
                            r.get("spec", ""),
                            r.get("unit", ""),
                            r.get("required", 0),
                            r.get("total_stock", 0),
                            "充足" if available else "不足",
                            warehouse_text
                        ])

                messagebox.showinfo("保存成功", f"已保存到:\n{filename}")
            except Exception as e:
                messagebox.showerror("保存失败", str(e))

    def show(self):
        self.window.deiconify()
        self.window.wait_window()

    def _on_close(self):
        self.window.destroy()


class MaterialRulesContainerDialog(BaseDialog):
    """物料计算规则配置容器对话框"""

    def __init__(self, parent):
        super().__init__(parent, title="⚙️ 物料计算规则配置", width=900, height=600, resizable=True)

    def _build_ui(self):
        from desktop.views.material_rules_view import MaterialRulesView
        MaterialRulesView(self.window).pack(fill=tk.BOTH, expand=True)

    def _on_cancel(self):
        self.window.destroy()


class BatchCalcMaterialDialog(BaseDialog):
    """批量计算物料对话框"""

    def __init__(self, parent_view, work_orders: list):
        self._parent_view = parent_view
        self._work_orders = work_orders
        self._order_vars = {}
        self._tree = None
        super().__init__(parent_view, title="🔧 批量计算物料", width=900, height=620, resizable=True)

    def _build_ui(self):
        top_frame = tk.Frame(self.window, bg="#FFFFFF", padx=10, pady=10)
        top_frame.pack(fill=tk.X)

        tk.Label(top_frame, text=f"共 {len(self._work_orders)} 个待备料工单，请选择要计算的订单：",
                 font=FONTS["body"], bg="#FFFFFF", fg="#333").pack(anchor="w")

        btn_frame = tk.Frame(top_frame, bg="#FFFFFF")
        btn_frame.pack(anchor="w", pady=5)

        def select_all():
            for item in self._tree.get_children():
                self._tree.selection_add(item)

        def deselect_all():
            for item in self._tree.get_children():
                self._tree.selection_remove(item)

        tk.Button(btn_frame, text="全选", font=FONTS["small"], command=select_all,
                  bg=COLORS["primary"], fg="white", width=8).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="取消全选", font=FONTS["small"], command=deselect_all,
                  bg="#E74C3C", fg="white", width=8).pack(side=tk.LEFT, padx=2)

        tree_frame = tk.Frame(self.window, bg="#FFFFFF")
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        columns = ("订单号", "产品类型", "客户", "数量", "单位", "状态", "下达日期")
        self._tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)
        for col in columns:
            self._tree.heading(col, text=col)
            self._tree.column(col, width=100 if col != "订单号" else 150)

        v_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=v_scroll.set)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        for wo in self._work_orders:
            o = dict(wo)
            item_id = self._tree.insert("", tk.END, values=(
                o.get("order_no", ""),
                o.get("product_type", ""),
                o.get("customer_name", ""),
                o.get("quantity", ""),
                o.get("unit", ""),
                o.get("status", ""),
                str(o.get("planned_date", "") or "")[:10]
            ))
            self._order_vars[item_id] = o

        self._tree.selection_set([next(iter(self._order_vars))]) if self._order_vars else None

        bottom_frame = tk.Frame(self.window, bg="#FFFFFF")
        bottom_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(bottom_frame, text="取消", width=12, command=self._on_cancel).pack(side=tk.RIGHT, padx=5)
        ttk.Button(bottom_frame, text="计算选中工单", width=15, command=self._do_calculate,
                   style="Accent.TButton").pack(side=tk.RIGHT, padx=5)

    def _do_calculate(self):
        selected = self._tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选择要计算的工单！", parent=self.window)
            return

        conn = get_connection()
        cursor = conn.cursor()

        success_count = 0
        fail_count = 0
        total_qty = 0

        for item_id in selected:
            order = self._order_vars.get(item_id)
            if not order:
                continue

            order_id = order.get("id")
            order_data = {
                "order_id": order_id,
                "order_no": order.get("order_no", ""),
                "product_type": order.get("product_type", ""),
                "quantity": order.get("quantity", 0),
                "unit": order.get("unit", "米"),
                "customer_name": order.get("customer_name", ""),
                "extra_params": order.get("extra_params", "{}")
            }

            try:
                calculator = MaterialCalculator(order_data)
                results = calculator.calculate()
                if not results:
                    fail_count += 1
                    continue

                existing_count = 0
                cursor.execute("SELECT COUNT(*) as cnt FROM order_materials WHERE order_id=%s", (order_id,))
                row = cursor.fetchone()
                if row:
                    existing_count = row["cnt"] if isinstance(row, dict) else row[0]

                missing_units = []
                for mat in results:
                    missing = mat.get("missing_params", [])
                    for m in missing:
                        if "单位" in m and mat.get("material_name") not in missing_units:
                            missing_units.append(mat.get("material_name"))

                if missing_units:
                    messagebox.showwarning(
                        "单位未配置",
                        f"以下物料的数量单位未配置，请先在「DIM_FIELDS」或「material_rules」中设置：\n\n" +
                        "\n".join(f"• {name}" for name in missing_units),
                        parent=self.window
                    )
                    fail_count += len(missing_units)
                    continue

                for mat in results:
                    spec_value = mat.get("spec_value", "") or ""
                    spec_unit = mat.get("spec_unit", "") or ""
                    spec = spec_value + spec_unit
                    qty_value = mat.get("qty_value", 0) or 0
                    qty_unit = mat.get("qty_unit", "") or "未配置"
                    cursor.execute("""
                        INSERT INTO order_materials (order_id, material_name, spec, required_qty, unit, remark)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        order_id,
                        mat.get("material_name", ""),
                        spec,
                        qty_value,
                        qty_unit,
                        mat.get("remark", "") or ""
                    ))

                success_count += 1
                total_qty += sum(m.get("qty_value", 0) for m in results)

                if existing_count > 0:
                    action = "更新" if messagebox.askyesno("确认", f"工单 {order.get('order_no', '')} 已有 {existing_count} 条物料记录，是否覆盖更新？",
                                                           parent=self.window) else "跳过"
                    if action == "跳过":
                        success_count -= 1
                        fail_count += 1
                        continue
                    else:
                        cursor.execute("DELETE FROM order_materials WHERE order_id=%s", (order_id,))
                        for mat in results:
                            spec_value = mat.get("spec_value", "") or ""
                            spec_unit = mat.get("spec_unit", "") or ""
                            spec = spec_value + spec_unit
                            qty_value = mat.get("qty_value", 0) or 0
                            qty_unit = mat.get("qty_unit", "") or "未配置"
                            cursor.execute("""
                                INSERT INTO order_materials (order_id, material_name, spec, required_qty, unit, remark)
                                VALUES (%s, %s, %s, %s, %s, %s)
                            """, (
                                order_id,
                                mat.get("material_name", ""),
                                spec,
                                qty_value,
                                qty_unit,
                                mat.get("remark", "") or ""
                            ))
            except Exception as e:
                logger.exception(f"计算工单 {order_id} 物料失败")
                fail_count += 1

        conn.commit()
        cursor.close()
        conn.close()

        result_msg = f"计算完成！\n成功：{success_count} 个工单"
        if fail_count:
            result_msg += f"\n失败：{fail_count} 个工单"
        result_msg += f"\n合计物料数量：{total_qty:.2f}"

        messagebox.showinfo("批量计算完成", result_msg, parent=self.window)
        self.window.destroy()
        self._parent_view.load_data()

    def _on_cancel(self):
        self.window.destroy()


class MaterialTemplateManagerDialog(BaseDialog):
    def __init__(self, parent):
        self._tree = None
        super().__init__(parent, title="📂 模板管理", width=600, height=400, resizable=True)

    def _build_ui(self):
        tk.Label(self.window, text="💡 双击编辑模板名称，右键删除", font=FONTS["small"], fg="#666").pack(pady=5)

        list_frame = tk.Frame(self.window)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        cols = ("name", "description", "materials", "updated")
        self._tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=12)

        for col, txt, w in [
            ("name", "模板名称", 150),
            ("description", "描述", 200),
            ("materials", "物料数", 80),
            ("updated", "更新时间", 130)
        ]:
            self._tree.heading(col, text=txt)
            self._tree.column(col, width=w)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def refresh_templates():
            for item in self._tree.get_children():
                self._tree.delete(item)
            templates = get_all_templates()
            for t in templates:
                mat_count = len(t.get("materials", []))
                self._tree.insert("", tk.END, values=(
                    t.get("name", ""),
                    t.get("description", ""),
                    f"{mat_count}种",
                    t.get("updated_at", "")[:16]
                ))

        refresh_templates()

        def on_rename():
            sel = self._tree.selection()
            if not sel:
                alert("请选择要重命名的模板", "提示")
                return
            old_name = self._tree.item(sel[0])["values"][0]
            fields = [
                ("原名称", "old", old_name, "label"),
                ("新名称", "new_name", old_name, "entry"),
            ]

            def on_save(data):
                new_name = data.get("new_name", "").strip()
                if not new_name:
                    alert("请输入新名称", "提示")
                    return
                rename_template(old_name, new_name)
                refresh_templates()
                alert("模板已重命名", "成功")

            popup_form("重命名模板", fields, on_save, width=350)

        def on_delete():
            sel = self._tree.selection()
            if not sel:
                alert("请选择要删除的模板", "提示")
                return
            values = self._tree.item(sel[0])["values"]
            template_name = values[0]
            if not messagebox.askyesno("确认", f"确定删除模板「{template_name}」？"):
                return
            delete_template(template_name)
            refresh_templates()
            alert("模板已删除", "成功")

        def on_preview():
            sel = self._tree.selection()
            if not sel:
                alert("请选择要预览的模板", "提示")
                return
            template_name = self._tree.item(sel[0])["values"][0]
            template = get_template(template_name)
            if not template:
                return
            materials = template.get("materials", [])
            MaterialTemplatePreviewDialog(self.window, template_name, materials)

        self._tree.bind("<Double-1>", lambda e: on_rename())

        def show_menu(event):
            item = self._tree.identify_row(event.y)
            if not item:
                return
            self._tree.selection_set(item)
            menu = tk.Menu(self.window, tearoff=0)
            menu.add_command(label="📝 重命名", command=on_rename)
            menu.add_command(label="👁️ 预览内容", command=on_preview)
            menu.add_separator()
            menu.add_command(label="🗑️ 删除", command=on_delete)
            menu.post(event.x_root, event.y_root)

        self._tree.bind("<Button-3>", show_menu)

        btn_frame = tk.Frame(self.window)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="🔄 刷新", command=refresh_templates).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📝 重命名", command=on_rename).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🗑️ 删除", command=on_delete).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="关闭", command=self._on_cancel).pack(side=tk.LEFT, padx=5)

    def _on_cancel(self):
        self.window.destroy()


class MaterialTemplatePreviewDialog(BaseDialog):
    def __init__(self, parent, template_name, materials):
        self._template_name = template_name
        self._materials = materials
        super().__init__(parent, title=f"📋 预览模板 - {template_name}", width=500, height=350, resizable=True)

    def _build_ui(self):
        tk.Label(self.window, text=f"模板: {self._template_name} | 物料数: {len(self._materials)}",
                font=FONTS["body"]).pack(pady=5)

        cols = ("name", "unit", "qty", "remark")
        preview_tree = ttk.Treeview(self.window, columns=cols, show="headings")
        for col, txt, w in [("name", "物料名称", 150), ("unit", "单位", 80), ("qty", "需求数量", 100), ("remark", "备注", 150)]:
            preview_tree.heading(col, text=txt)
            preview_tree.column(col, width=w)

        for m in self._materials:
            preview_tree.insert("", tk.END, values=(
                m.get("name", ""),
                m.get("unit", "米"),
                str(m.get("required_qty", 0)),
                m.get("remark", "")
            ))

        preview_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        ttk.Button(self.window, text="关闭", command=self._on_cancel).pack(pady=5)

    def _on_cancel(self):
        self.window.destroy()
