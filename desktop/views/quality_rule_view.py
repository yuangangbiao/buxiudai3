# -*- coding: utf-8 -*-
"""
质量监督规则配置视图
每个规则可配置：
1. 规则名称
2. 生效条件（产品类型列表）
3. 质检项目列表
4. 质检判定公式
"""
import tkinter as tk
from tkinter import ttk, messagebox
import json
from config import COLORS, FONTS, INSPECTION_ITEMS_BY_CATEGORY, PROCESSES
from models.quality_rule import QualityRuleDAO
from models.product_type import ProductTypeDAO
from models.database import get_connection
from utils.op_logger import log_ui
from utils.order_templates import DIM_FIELDS, MATERIAL_FIELDS
from utils.window_manager import setup_resizable_window


def get_all_dim_options() -> list:
    options = []
    for f in DIM_FIELDS:
        if f["key"] not in options:
            options.append(f["key"])
    skirt_params = [f["key"] for f in DIM_FIELDS if "裙边" in f["key"]]
    for sp in skirt_params:
        if sp not in options:
            options.append(sp)
    return options


def get_custom_params() -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT params_json FROM custom_params ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row:
        if isinstance(row, dict):
            raw = row.get("params_json", "")
        else:
            raw = row[0] if row else ""
        if raw:
            return json.loads(raw)
    return []


def get_custom_material_params() -> list:
    custom_params = get_custom_params()
    result = []
    for p in custom_params:
        if isinstance(p, dict):
            key = p.get("key", "")
        elif isinstance(p, str):
            key = p
        else:
            continue
        if key:
            result.append(key)
    return result


def get_custom_surface_params() -> list:
    custom_params = get_custom_params()
    result = []
    for p in custom_params:
        if isinstance(p, dict):
            key = p.get("key", "")
            if "表面" in key:
                result.append(key)
        elif isinstance(p, str) and "表面" in p:
            result.append(p)
    return result


def get_all_param_options() -> list:
    dim_options = get_all_dim_options()
    material_options = [f["key"] for f in MATERIAL_FIELDS]
    custom_material_options = get_custom_material_params()
    custom_surface_options = get_custom_surface_params()
    all_params = dim_options + material_options + custom_material_options + custom_surface_options + ["物料数量"]
    return list(dict.fromkeys(all_params))


class QualityRuleView(tk.Frame):

    def __init__(self, parent):
        super().__init__(parent, bg=COLORS["bg_main"])
        self.selected_rule_id = None
        ProductTypeDAO.init_default_types()
        self.init_ui()
        self.load_rules()

    def init_ui(self):
        toolbar = tk.Frame(self, bg="#FFFFFF", height=50)
        toolbar.pack(fill=tk.X, side=tk.TOP)
        toolbar.pack_propagate(False)

        tk.Label(toolbar, text="⚙️ 质量监督规则配置", font=FONTS["large"], bg="#FFFFFF",
                fg=COLORS["primary"]).pack(side=tk.LEFT, padx=15, pady=10)

        ttk.Button(toolbar, text="🔄 刷新", command=self.load_rules).pack(side=tk.RIGHT, padx=10)

        main_frame = tk.Frame(self, bg=COLORS["bg_main"])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))

        left_frame = tk.Frame(main_frame, bg="#FFFFFF")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(left_frame, text="📋 规则列表", font=FONTS["subtitle"], bg="#FFFFFF",
                fg=COLORS["text_primary"]).pack(anchor="w", padx=10, pady=(10, 5))

        table_frame = tk.Frame(left_frame, bg="#FFFFFF", padx=10, pady=5)
        table_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("rule_name", "inspection_items", "check_formula", "enabled")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=15)

        col_configs = [
            ("rule_name", "规则名称", 150),
            ("inspection_items", "质检项目", 280),
            ("check_formula", "判定公式", 200),
            ("enabled", "状态", 80)
        ]
        for col, txt, w in col_configs:
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=w, anchor="w")

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        style = ttk.Style()
        style.configure("Treeview", font=("微软雅黑", 11), rowheight=28)

        btn_frame = tk.Frame(left_frame, bg="#FFFFFF", padx=10, pady=10)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="➕ 添加规则", command=self.add_rule).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="✏️ 编辑选中", command=self.edit_rule).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="🗑️ 删除选中", command=self.delete_rule).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="🔧 初始化默认规则", command=self.init_default_rules).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="📤 导出规则", command=self.export_rules).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="📥 导入规则", command=self.import_rules).pack(side=tk.LEFT, padx=3)

        right_frame = tk.Frame(main_frame, bg="#FFFFFF", width=320)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        right_frame.pack_propagate(False)

        tk.Label(right_frame, text="📖 使用说明", font=FONTS["subtitle"], bg="#FFFFFF",
                fg=COLORS["text_primary"]).pack(anchor="w", padx=10, pady=(10, 5))

        help_text = """
【质量监督规则说明】

━━━ 生效条件 ━━━
决定该质检规则适用于哪些产品类型

━━━ 质检项目 ━━━
定义该规则需要检查的项目列表
如：材质核对、外观检查、尺寸核对等

━━━ 判定公式 ━━━
根据订单参数自动判定质检是否通过
可用参数：
  • quantity（数量）
  • 尺寸参数：总宽、钢丝直径、总长度等
  • 物料数量（物料种类数）
  • 支持运算符：+ - * / （括号先算）

示例公式：
  1                    → 始终通过
  quantity >= 100      → 数量≥100时通过
  物料数量 > 0         → 有物料时通过
        """

        help_label = tk.Label(right_frame, text=help_text, font=("微软雅黑", 9),
                             bg="#FFFFFF", fg="#666666", justify="left", anchor="nw")
        help_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.tree.bind("<<TreeviewSelect>>", self.on_rule_selected)
        self.tree.bind("<Double-1>", lambda e: self.edit_rule())

    def load_rules(self):
        """加载所有质量规则"""
        log_ui("质量规则", "加载规则列表", "")
        for item in self.tree.get_children():
            self.tree.delete(item)

        rules = QualityRuleDAO.get_all()

        for rule in rules:
            enabled_text = "✅" if rule.get("enabled") else "❌"

            inspection_items = rule.get("inspection_items_json") or "[]"
            try:
                items_list = ", ".join(json.loads(inspection_items)) if inspection_items and inspection_items != "[]" else "（未设置）"
            except Exception:
                items_list = "（未设置）"

            check_formula = rule.get("check_formula") or ""
            if not check_formula:
                check_formula = "（未设置）"

            self.tree.insert("", tk.END, values=(
                rule["rule_name"],
                items_list,
                check_formula,
                enabled_text
            ), tags=(rule["id"],))

    def on_rule_selected(self, event=None):
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            tags = item.get("tags", ())
            if tags:
                self.selected_rule_id = tags[0]
        else:
            self.selected_rule_id = None

    def add_rule(self):
        """添加新质量规则"""
        log_ui("质量规则", "添加规则", "")
        new_rule = {
            "id": None,
            "rule_name": "",
            "product_types_json": "[]",
            "condition_expr": "所有产品类型",
            "inspection_items_json": "[]",
            "check_formula": "",
            "priority": 5,
            "enabled": True
        }
        self._show_rule_dialog(new_rule, is_new=True)

    def edit_rule(self):
        """编辑选中规则"""
        log_ui("质量规则", "编辑规则", f"规则ID={self.selected_rule_id}")
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请先选择要编辑的规则")
            return

        item = self.tree.item(selection[0])
        rule_id = item.get("tags", [])[0] if item.get("tags") else None
        if not rule_id:
            return

        rule = QualityRuleDAO.get_by_id(rule_id)
        if not rule:
            messagebox.showerror("错误", "规则不存在")
            return

        self._show_rule_dialog(rule, is_new=False)

    def delete_rule(self):
        """删除选中规则"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请先选择要删除的规则")
            return

        item = self.tree.item(selection[0])
        rule_id = item.get("tags", [])[0] if item.get("tags") else None
        if not rule_id:
            return

        if not messagebox.askyesno("确认删除", "确定要删除这条质量规则吗？"):
            return

        success, msg = QualityRuleDAO.delete(rule_id)
        if success:
            log_ui("质量规则", "删除规则", f"规则ID={rule_id}")
            messagebox.showinfo("成功", msg)
            self.load_rules()
        else:
            messagebox.showerror("错误", msg)

    def init_default_rules(self):
        """初始化默认质量规则"""
        log_ui("质量规则", "初始化默认规则")
        if not messagebox.askyesno("确认", "将创建默认质量规则，继续吗？"):
            return

        QualityRuleDAO.init_default_rules()
        log_ui("质量规则", "✅ 默认规则已初始化")
        messagebox.showinfo("成功", "默认质量规则已初始化")
        self.load_rules()

    def export_rules(self):
        """导出规则到JSON文件"""
        import tkinter.filedialog as fd
        rules = QualityRuleDAO.get_all()
        if not rules:
            messagebox.showinfo("提示", "暂无规则可导出")
            return

        file_path = fd.asksaveasfilename(
            title="导出质量规则",
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json")],
            initialfile=f"quality_rules_export.json"
        )
        if not file_path:
            return

        try:
            from models.quality_rule import QualityRuleDAO as QR
            export_data = []
            for rule in rules:
                items = QR.get_rule_items(rule["id"])
                rule_copy = {
                    "rule_name": rule.get("rule_name", ""),
                    "process_name": rule.get("process_name", ""),
                    "product_types": json.loads(rule.get("product_types_json", "[]")),
                    "condition_expr": rule.get("condition_expr", ""),
                    "inspection_items": json.loads(rule.get("inspection_items_json", "[]")),
                    "check_formula": rule.get("check_formula", ""),
                    "priority": rule.get("priority", 5),
                    "enabled": rule.get("enabled", True),
                    "rule_items": [
                        {
                            "inspection_item": item.get("inspection_item", ""),
                            "check_formula": item.get("check_formula", ""),
                            "tolerance": item.get("tolerance", "")
                        }
                        for item in items
                    ]
                }
                export_data.append(rule_copy)

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

            log_ui("质量规则", f"导出规则成功: {file_path}")
            messagebox.showinfo("成功", f"已导出 {len(export_data)} 条规则到:\n{file_path}")
        except Exception as e:
            log_ui("质量规则", f"导出规则失败: {e}")
            messagebox.showerror("错误", f"导出失败: {e}")

    def import_rules(self):
        """从JSON文件导入规则"""
        import tkinter.filedialog as fd
        file_path = fd.askopenfilename(
            title="导入质量规则",
            filetypes=[("JSON文件", "*.json")]
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                import_data = json.load(f)

            if not isinstance(import_data, list):
                messagebox.showerror("错误", "文件格式不正确")
                return

            count = 0
            for rule_data in import_data:
                rule_name = rule_data.get("rule_name", "").strip()
                if not rule_name:
                    continue

                success, msg, rule_id = QualityRuleDAO.create(
                    rule_name=rule_name,
                    product_types=rule_data.get("product_types", []),
                    condition_expr=rule_data.get("condition_expr", ""),
                    inspection_items=rule_data.get("inspection_items", []),
                    check_formula=rule_data.get("check_formula", ""),
                    priority=rule_data.get("priority", 5),
                    enabled=rule_data.get("enabled", True),
                    process_name=rule_data.get("process_name", "")
                )

                if success and rule_id:
                    for item_data in rule_data.get("rule_items", []):
                        QualityRuleDAO.add_rule_item(
                            rule_id,
                            item_data.get("inspection_item", ""),
                            item_data.get("check_formula", ""),
                            item_data.get("tolerance", "")
                        )
                    count += 1

            log_ui("质量规则", f"导入规则成功: {count}条")
            messagebox.showinfo("成功", f"成功导入 {count} 条规则")
            self.load_rules()
        except Exception as e:
            log_ui("质量规则", f"导入规则失败: {e}")
            messagebox.showerror("错误", f"导入失败: {e}")

    def _show_rule_dialog(self, rule: dict, is_new: bool):
        from .dialogs.rule_dialogs import QualityRuleDialog
        QualityRuleDialog(self, rule, is_new)
