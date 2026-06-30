# -*- coding: utf-8 -*-
"""
物料计算规则配置视图
"""
import tkinter as tk
from tkinter import ttk, messagebox
import logging
from config import COLORS, FONTS
from models.material_rules import MaterialRulesDAO
from models.product_type import ProductTypeDAO
from utils.material_calculator import MaterialCalculator
from utils.order_templates import DIM_FIELDS, MATERIAL_FIELDS, SURFACE_FIELD
from utils.custom_types import get_unit_options

logger = logging.getLogger(__name__)


def get_all_spec_field_options() -> list:
    """获取所有可选的规格字段选项（包括预设+自定义+裙边+材质参数）"""
    from models.database import get_connection

    options = []
    for f in DIM_FIELDS:
        if f["key"] not in options:
            options.append(f["key"])
    for f in MATERIAL_FIELDS:
        if f["key"] not in options:
            options.append(f["key"])
    for f in SURFACE_FIELD:
        if f["key"] not in options:
            options.append(f["key"])

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM custom_dim_params")
    for row in cursor.fetchall():
        name = row[0] if isinstance(row, tuple) else row["name"]
        if name not in options:
            options.append(name)

    cursor.execute("SELECT name FROM custom_mat_params")
    for row in cursor.fetchall():
        name = row[0] if isinstance(row, tuple) else row["name"]
        if name not in options:
            options.append(name)

    try:
        cursor.execute("SELECT name FROM custom_surface_params")
        for row in cursor.fetchall():
            name = row[0] if isinstance(row, tuple) else row["name"]
            if name not in options:
                options.append(name)
    except Exception as e:
        logger.warning(f"获取自定义表面参数失败: {e}")

    cursor.close()
    conn.close()
    return options


def get_all_material_param_options() -> list:
    """获取所有可选的材质参数（包括预设+自定义）"""
    from models.database import get_connection

    options = []
    for f in MATERIAL_FIELDS:
        if f["key"] not in options:
            options.append(f["key"])

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM custom_mat_params")
    for row in cursor.fetchall():
        name = row[0] if isinstance(row, tuple) else row["name"]
        if name not in options:
            options.append(name)

    cursor.close()
    conn.close()
    return options


class MaterialRulesView(tk.Frame):
    """物料计算规则配置视图"""

    def __init__(self, parent):
        super().__init__(parent, bg=COLORS["bg_main"])
        self.selected_rule_id = None
        self.current_product_type = None
        ProductTypeDAO.init_default_types()
        self.init_ui()
        self.load_product_types()

    def init_ui(self):
        toolbar = tk.Frame(self, bg="#FFFFFF", height=50)
        toolbar.pack(fill=tk.X, side=tk.TOP)
        toolbar.pack_propagate(False)

        tk.Label(toolbar, text="⚙️ 物料计算规则配置", font=FONTS["large"], bg="#FFFFFF",
                fg=COLORS["primary"]).pack(side=tk.LEFT, padx=15, pady=10)

        template_btn_frame = tk.Frame(toolbar, bg="#FFFFFF")
        template_btn_frame.pack(side=tk.LEFT, padx=10)
        ttk.Button(template_btn_frame, text="💾 保存模板", command=self.save_as_template).pack(side=tk.LEFT, padx=2)
        ttk.Button(template_btn_frame, text="📥 载入模板", command=self.load_template).pack(side=tk.LEFT, padx=2)
        ttk.Button(template_btn_frame, text="📂 管理模板", command=self.manage_templates).pack(side=tk.LEFT, padx=2)

        ttk.Button(toolbar, text="🔄 刷新", command=self.load_rules).pack(side=tk.RIGHT, padx=10)

        filter_frame = tk.Frame(toolbar, bg="#FFFFFF")
        filter_frame.pack(side=tk.RIGHT, padx=10)

        tk.Label(filter_frame, text="产品类型:", font=FONTS["body"], bg="#FFFFFF").pack(side=tk.LEFT, padx=5)

        self.product_type_combo = ttk.Combobox(filter_frame, width=15, font=FONTS["body"],
                                             state="readonly")
        self.product_type_combo.pack(side=tk.LEFT, padx=5)
        self.product_type_combo.bind("<<ComboboxSelected>>", self.on_product_type_changed)

        ttk.Button(filter_frame, text="➕ 添加产品类型", command=self.add_product_type).pack(side=tk.LEFT, padx=5)

        main_frame = tk.Frame(self, bg=COLORS["bg_main"])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))

        left_frame = tk.Frame(main_frame, bg="#FFFFFF")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(left_frame, text="📋 规则列表", font=FONTS["subtitle"], bg="#FFFFFF",
                fg=COLORS["text_primary"]).pack(anchor="w", padx=10, pady=(10, 5))

        table_frame = tk.Frame(left_frame, bg="#FFFFFF", padx=10, pady=5)
        table_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("material_param", "material_name_template", "spec_field", "spec_unit", "enabled")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=12)

        col_configs = [
            ("material_param", "材质参数", 120),
            ("material_name_template", "物料名称模板", 180),
            ("spec_field", "规格字段", 100),
            ("spec_unit", "规格单位", 80),
            ("enabled", "状态", 60)
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

        right_frame = tk.Frame(main_frame, bg="#FFFFFF", width=300)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        right_frame.pack_propagate(False)

        tk.Label(right_frame, text="📖 使用说明", font=FONTS["subtitle"], bg="#FFFFFF",
                fg=COLORS["text_primary"]).pack(anchor="w", padx=10, pady=(10, 5))

        help_text = """
【物料名称模板】
  使用 {material} 代替材质值
  
  例如：{material}钢丝
  当材质为"304不锈钢"时
  生成的物料名称为：
  "304不锈钢钢丝"

【规格字段】
  选择对应的尺寸参数
  用于生成规格信息
  
【示例规则】
  眼镜网带 + 网丝材质
  → 模板：{material}钢丝
  → 规格：钢丝直径
        """
        
        help_label = tk.Label(right_frame, text=help_text, font=("微软雅黑", 9), 
                             bg="#FFFFFF", fg="#666666", justify="left", anchor="nw")
        help_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.tree.bind("<<TreeviewSelect>>", self.on_rule_selected)
        self.tree.bind("<Double-1>", lambda e: self.edit_rule())

    def load_product_types(self):
        types = ProductTypeDAO.get_all_names()
        configured_types = MaterialRulesDAO.get_distinct_product_types()
        for pt in configured_types:
            if pt not in types:
                types.append(pt)

        self.product_type_combo["values"] = types
        if types:
            self.product_type_combo.current(0)
            self.current_product_type = types[0]
            self.load_rules()

    def on_product_type_changed(self, event=None):
        self.current_product_type = self.product_type_combo.get()
        self.load_rules()

    def load_rules(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        if not self.current_product_type:
            return

        rules = MaterialRulesDAO.get_by_product_type(self.current_product_type)
        
        for rule in rules:
            enabled_text = "✅" if rule.get("enabled") else "❌"
            self.tree.insert("", tk.END, values=(
                rule["material_param"],
                rule["material_name_template"],
                rule.get("spec_field", ""),
                rule.get("spec_unit", ""),
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

    def add_product_type(self):
        """添加新产品类型"""
        from .dialogs.rule_dialogs import AddProductTypeDialog
        AddProductTypeDialog(self)

    def add_rule(self):
        if not self.current_product_type:
            messagebox.showwarning("提示", "请先选择产品类型")
            return
        from .dialogs.rule_dialogs import MaterialRuleDialog
        MaterialRuleDialog(self, self.current_product_type, None)

    def edit_rule(self):
        if not self.selected_rule_id:
            messagebox.showwarning("提示", "请选择要编辑的规则")
            return

        rule = MaterialRulesDAO.get_by_id(self.selected_rule_id)
        if not rule:
            return
        from .dialogs.rule_dialogs import MaterialRuleDialog
        MaterialRuleDialog(self, rule["product_type"], rule)

    def delete_rule(self):
        if not self.selected_rule_id:
            messagebox.showwarning("提示", "请选择要删除的规则")
            return

        if not messagebox.askyesno("确认删除", "确定要删除选中的规则吗？"):
            return

        try:
            MaterialRulesDAO.delete(self.selected_rule_id)
            messagebox.showinfo("成功", "规则已删除")
            self.load_rules()
        except Exception as e:
            messagebox.showerror("错误", f"删除失败: {e}")

    def save_as_template(self):
        """保存当前规则为模板"""
        if not self.current_product_type:
            messagebox.showwarning("提示", "请先选择产品类型")
            return

        rules = MaterialRulesDAO.get_by_product_type(self.current_product_type)
        if not rules:
            messagebox.showwarning("提示", "当前没有规则可保存")
            return
        from .dialogs.rule_dialogs import SaveRuleTemplateDialog
        SaveRuleTemplateDialog(self, rules)

    def load_template(self):
        """载入模板"""
        from .dialogs.rule_dialogs import LoadRuleTemplateDialog
        LoadRuleTemplateDialog(self)

    def manage_templates(self):
        """管理模板"""
        from .dialogs.rule_dialogs import ManageRuleTemplatesDialog
        ManageRuleTemplatesDialog(self)
