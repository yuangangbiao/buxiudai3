# -*- coding: utf-8 -*-
"""
工序计算规则配置视图
每个工序有两个逻辑计算框：
1. 生效条件（产品类型列表）
2. 工序计划数量计算（尺寸参数表达式）
"""
import tkinter as tk
from tkinter import ttk, messagebox
import json
from config import COLORS, FONTS, PROCESSES
from models.process_calc_rule import ProcessCalcRuleDAO, ProcessCalcEngine
from models.product_type import ProductTypeDAO
from models.database import get_connection
from utils.op_logger import log_ui





class ProcessCalcRuleView(tk.Frame):
    """工序计算规则配置视图"""

    def __init__(self, parent):
        super().__init__(parent, bg=COLORS["bg_main"])
        self.selected_rule_id = None
        self.current_process = None
        ProductTypeDAO.init_default_types()
        self.init_ui()
        self.load_processes()

    def init_ui(self):
        toolbar = tk.Frame(self, bg="#FFFFFF", height=50)
        toolbar.pack(fill=tk.X, side=tk.TOP)
        toolbar.pack_propagate(False)

        tk.Label(toolbar, text="⚙️ 工序计算规则配置", font=FONTS["large"], bg="#FFFFFF",
                fg=COLORS["primary"]).pack(side=tk.LEFT, padx=15, pady=10)

        ttk.Button(toolbar, text="🔄 刷新", command=self.load_rules).pack(side=tk.RIGHT, padx=10)

        filter_frame = tk.Frame(toolbar, bg="#FFFFFF")
        filter_frame.pack(side=tk.RIGHT, padx=10)

        tk.Label(filter_frame, text="选择工序:", font=FONTS["body"], bg="#FFFFFF").pack(side=tk.LEFT, padx=5)

        self.process_combo = ttk.Combobox(filter_frame, width=18, font=FONTS["body"],
                                          state="readonly")
        self.process_combo.pack(side=tk.LEFT, padx=5)
        self.process_combo.bind("<<ComboboxSelected>>", self.on_process_changed)

        main_frame = tk.Frame(self, bg=COLORS["bg_main"])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))

        left_frame = tk.Frame(main_frame, bg="#FFFFFF")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(left_frame, text="📋 工序列表", font=FONTS["subtitle"], bg="#FFFFFF",
                fg=COLORS["text_primary"]).pack(anchor="w", padx=10, pady=(10, 5))

        table_frame = tk.Frame(left_frame, bg="#FFFFFF", padx=10, pady=5)
        table_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("process_name", "product_types", "planned_qty", "default_worker", "unit", "enabled")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=15)

        col_configs = [
            ("process_name", "工序名称", 120),
            ("product_types", "适用产品类型", 160),
            ("planned_qty", "工序计划数量", 200),
            ("default_worker", "默认负责人", 90),
            ("unit", "单位", 50),
            ("enabled", "状态", 50)
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
        ttk.Button(btn_frame, text="🔧 初始化全部工序", command=self.init_all_processes).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="💾 保存模板", command=self.save_as_template).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="📤 导出模板", command=self.export_template).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="📥 导入模板", command=self.import_template).pack(side=tk.LEFT, padx=3)

        right_frame = tk.Frame(main_frame, bg="#FFFFFF", width=320)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        right_frame.pack_propagate(False)

        tk.Label(right_frame, text="📖 使用说明", font=FONTS["subtitle"], bg="#FFFFFF",
                fg=COLORS["text_primary"]).pack(anchor="w", padx=10, pady=(10, 5))

        help_text = """
【工序计算规则说明】

━━━ 生效条件（决定工序是否被创建）━━━
当订单"调入工序表"时：
  → 符合生效条件的工序 → 会被创建
  → 不符合的工序 → 不会被创建

配置项：
  • 产品类型：多选，不选则对所有类型生效
  • 尺寸条件：如"宽度 > 1000"（单位mm）
  • 逻辑组合：AND/OR/括号

━━━ 计划数量公式（决定工序的planned_qty）━━━
当工序被创建时，按公式计算数量

可用参数：
  • quantity（数量）、product_type（产品类型）
  • 尺寸参数：总宽、网带宽度、钢丝直径、总长度等
  • 支持运算符：+ - * / （括号先算）

示例公式：
  quantity                    → 直接用订单数量
  总宽 * 0.001 * quantity    → 总宽(mm)转米后乘数量
  quantity / 2               → 数量的一半
  1                          → 固定为1

━━━ 尺寸参数参考（单位：mm）━━━
  宽度类：总宽、网带宽度
  长度类：总长度、折边长度、单段长度
  直径类：钢丝直径、链条直径、穿杆直径
  数量类：网带段数、加强筋数量
        """

        help_label = tk.Label(right_frame, text=help_text, font=("微软雅黑", 9),
                             bg="#FFFFFF", fg="#666666", justify="left", anchor="nw")
        help_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.tree.bind("<<TreeviewSelect>>", self.on_rule_selected)
        self.tree.bind("<Double-1>", lambda e: self.edit_rule())

    def load_processes(self):
        """加载工序列表到下拉框"""
        self.process_combo["values"] = list(PROCESSES)
        if PROCESSES:
            self.process_combo.current(0)
            self.current_process = PROCESSES[0]
            self.load_rules()

    def on_process_changed(self, event=None):
        self.current_process = self.process_combo.get()
        log_ui("工序规则", "切换工序", f"工序='{self.current_process}'")
        self.load_rules()

    def load_rules(self):
        """加载所有工序规则"""
        log_ui("工序规则", "加载规则列表", f"工序='{self.current_process}'")
        for item in self.tree.get_children():
            self.tree.delete(item)

        rules = ProcessCalcRuleDAO.get_all()

        for rule in rules:
            enabled_text = "✅" if rule.get("enabled") else "❌"
            product_types = rule.get("product_types_json") or "[]"
            try:
                types_list = ", ".join(json.loads(product_types)) if product_types and product_types != "[]" else "全部"
            except Exception:
                types_list = "全部"

            planned_qty = rule.get("planned_qty_formula") or ""
            if not planned_qty:
                planned_qty = "（未设置）"

            default_worker = rule.get("default_worker") or ""
            unit = rule.get("unit") or "件"

            self.tree.insert("", tk.END, values=(
                rule["process_name"],
                types_list,
                planned_qty,
                default_worker,
                unit,
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
        """添加新工序规则"""
        log_ui("工序规则", "添加规则", f"工序='{self.current_process}'")
        if not self.current_process:
            messagebox.showwarning("提示", "请先从上方选择工序")
            return

        new_rule = {
            "id": None,
            "process_name": self.current_process,
            "product_types_json": "[]",
            "condition_expr": "所有产品类型",
            "planned_qty_formula": "物料种类数量",
            "priority": 5,
            "enabled": True
        }
        self._show_rule_dialog(new_rule, is_new=True)

    def edit_rule(self):
        """编辑选中工序的规则"""
        log_ui("工序规则", "编辑规则")
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请先选择要编辑的工序")
            return

        item = self.tree.item(selection[0])
        rule_id = item.get("tags", [])[0] if item.get("tags") else None
        if not rule_id:
            return

        rule = None
        for r in ProcessCalcRuleDAO.get_all():
            if str(r["id"]) == str(rule_id):
                rule = r
                break

        if not rule:
            messagebox.showerror("错误", "规则不存在")
            return

        self._show_rule_dialog(rule, is_new=False)

    def init_all_processes(self):
        """初始化所有工序的默认规则"""
        log_ui("工序规则", "初始化所有工序默认规则")
        if not messagebox.askyesno("确认", "将为所有工序创建默认规则，继续吗？"):
            return

        ProcessCalcRuleDAO.init_default_rules(list(PROCESSES))
        log_ui("工序规则", "✅ 所有工序规则已初始化")
        messagebox.showinfo("成功", "所有工序规则已初始化")
        self.load_rules()

    def save_as_template(self):
        """保存当前规则为模板"""
        rules = ProcessCalcRuleDAO.get_all()
        if not rules:
            messagebox.showwarning("提示", "没有可保存的规则！")
            return
        from .dialogs.rule_dialogs import SaveProcessRuleTemplateDialog
        SaveProcessRuleTemplateDialog(self)

    def export_template(self):
        """导出规则模板到文件"""
        rules = ProcessCalcRuleDAO.get_all()
        if not rules:
            messagebox.showwarning("提示", "没有可导出的规则！")
            return

        from tkinter import filedialog
        filepath = filedialog.asksaveasfilename(
            title="导出规则模板",
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        if not filepath:
            return

        try:
            def convert_for_json(obj):
                if isinstance(obj, dict):
                    return {k: convert_for_json(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_for_json(item) for item in obj]
                elif hasattr(obj, 'strftime'):
                    return obj.strftime("%Y-%m-%d %H:%M:%S")
                return obj

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(convert_for_json(rules), f, ensure_ascii=False, indent=2)
            messagebox.showinfo("成功", f"规则已导出到：\n{filepath}")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败：{str(e)}")

    def import_template(self):
        """从文件导入规则模板"""
        from tkinter import filedialog
        filepath = filedialog.askopenfilename(
            title="导入规则模板",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        if not filepath:
            return

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                rules = json.load(f)

            if not isinstance(rules, list) or len(rules) == 0:
                messagebox.showerror("错误", "文件格式不正确，没有规则数据！")
                return

            for rule in rules:
                process_name = rule.get("process_name", "")
                if not process_name:
                    continue

                product_types = rule.get("product_types_json", "[]")
                condition_expr = rule.get("condition_expr", "")
                planned_qty_formula = rule.get("planned_qty_formula", "")
                priority = rule.get("priority", 5)

                existing = ProcessCalcRuleDAO.get_by_process(process_name)
                if existing:
                    ProcessCalcRuleDAO.update(
                        existing["id"], process_name,
                        json.loads(product_types) if isinstance(product_types, str) else product_types,
                        condition_expr, planned_qty_formula, priority, True
                    )
                else:
                    ProcessCalcRuleDAO.create(
                        process_name,
                        json.loads(product_types) if isinstance(product_types, str) else product_types,
                        condition_expr, planned_qty_formula, priority, True
                    )

            self.load_rules()
            messagebox.showinfo("成功", f"已导入 {len(rules)} 条规则！")
        except Exception as e:
            messagebox.showerror("错误", f"导入失败：{str(e)}")

    def _show_rule_dialog(self, rule: dict, is_new: bool = False):
        """显示规则编辑对话框"""
        from .dialogs.rule_dialogs import ProcessRuleEditDialog
        ProcessRuleEditDialog(self, rule, is_new)
