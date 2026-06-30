# -*- coding: utf-8 -*-
"""
规则配置对话框模块
"""
import tkinter as tk
from tkinter import ttk, messagebox
import json
import logging
from config import COLORS, FONTS, INSPECTION_ITEMS_BY_CATEGORY, PROCESSES
from models.quality_rule import QualityRuleDAO
from models.material_rules import MaterialRulesDAO
from models.product_type import ProductTypeDAO
from models.process_calc_rule import ProcessCalcRuleDAO
from models.database import get_connection
from utils.material_calculator import MaterialCalculator
from utils.op_logger import log_ui
from utils.custom_types import get_unit_options
from utils.order_templates import DIM_FIELDS, MATERIAL_FIELDS
from .base import BaseDialog

logger = logging.getLogger(__name__)


class AddProductTypeDialog(BaseDialog):
    def __init__(self, parent_view):
        self._name_var = None
        self._desc_var = None
        self._flow_var = None
        self._parent_view = parent_view
        super().__init__(parent_view, "添加产品类型", 400, 250)

    def _build_ui(self):
        frame = tk.Frame(self.window, bg="#FFFFFF", padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="产品类型名称:", font=FONTS["body"], bg="#FFFFFF").grid(row=0, column=0, sticky="w", pady=10)
        self._name_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self._name_var, width=25, font=FONTS["body"]).grid(row=0, column=1, sticky="w", pady=10)

        tk.Label(frame, text="描述:", font=FONTS["body"], bg="#FFFFFF").grid(row=1, column=0, sticky="nw", pady=10)
        self._desc_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self._desc_var, width=25, font=FONTS["body"]).grid(row=1, column=1, sticky="w", pady=10)

        tk.Label(frame, text="流程类型:", font=FONTS["body"], bg="#FFFFFF").grid(row=2, column=0, sticky="w", pady=10)
        self._flow_var = tk.StringVar(value="production")
        ff = tk.Frame(frame, bg="#FFFFFF")
        ff.grid(row=2, column=1, sticky="w", pady=10)
        tk.Radiobutton(ff, text="生产", variable=self._flow_var, value="production", font=FONTS["body"], bg="#FFFFFF").pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(ff, text="外协", variable=self._flow_var, value="outsource", font=FONTS["body"], bg="#FFFFFF").pack(side=tk.LEFT, padx=5)

        btn_frame = tk.Frame(frame, bg="#FFFFFF")
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="取消", width=10, command=self._on_cancel).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="添加", width=10, command=self._on_confirm, style="Accent.TButton").pack(side=tk.LEFT, padx=10)

    def _validate(self):
        name = self._name_var.get().strip()
        if not name:
            messagebox.showerror("错误", "产品类型名称不能为空", parent=self.window)
            return False
        if ProductTypeDAO.exists(name):
            messagebox.showerror("错误", f"产品类型「{name}」已存在", parent=self.window)
            return False
        return True

    def _on_confirm(self):
        if not self._validate():
            return
        name = self._name_var.get().strip()
        description = self._desc_var.get().strip()
        flow_type = self._flow_var.get() if self._flow_var else "production"
        try:
            pt_id = ProductTypeDAO.create(name, description)
            from utils.custom_types import set_product_flow_type
            set_product_flow_type(pt_id, flow_type)
            messagebox.showinfo("成功", f"产品类型「{name}」添加成功", parent=self.window)
            self.window.destroy()
            self._parent_view.load_product_types()
            self._parent_view.product_type_combo.set(name)
        except Exception as e:
            messagebox.showerror("错误", f"添加失败: {e}", parent=self.window)

    def _on_cancel(self):
        self.window.destroy()


class QualityRuleDialog(BaseDialog):
    def __init__(self, parent_view, rule: dict, is_new: bool):
        self._parent_view = parent_view
        self._rule = rule
        self._is_new = is_new
        self._name_var = None
        self._cat_var = None
        self._search_var = None
        self._param_var = None
        self._priority_var = None
        self._enabled_var = None
        self._current_items = []
        self._item_vars = {}
        self._item_formula_vars = {}
        self._item_tolerance_vars = {}
        self._existing_items_formulas = {}
        self._existing_items_tolerances = {}
        self._canvas = None
        self._item_list_frame = None
        self._formula_canvas = None
        self._formula_inner_frame = None
        super().__init__(parent_view, "编辑质量规则" if not is_new else "添加质量规则", 750, 700)

    def _build_ui(self):
        frame = tk.Frame(self.window, bg="#FFFFFF", padx=20, pady=15)
        frame.pack(fill=tk.BOTH, expand=True)

        row = 0

        tk.Label(frame, text="规则名称:", font=FONTS["body"], bg="#FFFFFF").grid(row=row, column=0, sticky="nw", pady=8)
        self._name_var = tk.StringVar(value=self._rule.get("rule_name") or "")
        tk.Entry(frame, textvariable=self._name_var, font=FONTS["body"], width=30).grid(row=row, column=1, columnspan=2, sticky="w", pady=8)
        row += 1

        tk.Label(frame, text="质检项目:", font=FONTS["body"], bg="#FFFFFF").grid(row=row, column=0, sticky="nw", pady=8)
        items_top_frame = tk.Frame(frame, bg="#FFFFFF")
        items_top_frame.grid(row=row, column=1, columnspan=2, sticky="w", pady=8)

        try:
            items_json = self._rule.get("inspection_items_json") or "[]"
            if items_json and items_json != "[]":
                self._current_items = json.loads(items_json)
        except Exception:
            self._current_items = []

        for item in self._current_items:
            self._item_vars[item] = tk.BooleanVar(value=True)

        if not self._is_new and self._rule.get("id"):
            existing = QualityRuleDAO.get_rule_items(self._rule["id"])
            for ei in existing:
                self._existing_items_formulas[ei["inspection_item"]] = ei.get("check_formula") or ""
                self._existing_items_tolerances[ei["inspection_item"]] = ei.get("tolerance") or ""

        self._param_var = tk.StringVar()

        list_container = tk.Frame(frame, bg="#FFFFFF")
        list_container.grid(row=row + 1, column=1, columnspan=2, sticky="wens", pady=5)

        self._canvas = tk.Canvas(list_container, bg="#FFFFFF", highlightthickness=0, height=220)
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=self._canvas.yview)
        self._item_list_frame = tk.Frame(self._canvas, bg="#FFFFFF")

        self._canvas.configure(yscrollcommand=scrollbar.set)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def _on_frame_configure(event):
            self._canvas.configure(scrollregion=self._canvas.bbox("all"))

        self._item_list_frame.bind("<Configure>", _on_frame_configure)
        self._canvas.create_window((0, 0), window=self._item_list_frame, anchor="nw")

        tk.Label(items_top_frame, text="工序:", font=FONTS["small"], bg="#FFFFFF").pack(side=tk.LEFT, padx=(0, 3))
        self._cat_var = tk.StringVar(value=self._rule.get("process_name") or "")
        cat_combo = ttk.Combobox(items_top_frame, textvariable=self._cat_var, font=FONTS["body"],
                                  width=14, state="readonly")
        cat_combo.pack(side=tk.LEFT, padx=3)
        cat_combo["values"] = PROCESSES

        tk.Label(items_top_frame, text="增加:", font=FONTS["small"], bg="#FFFFFF").pack(side=tk.LEFT, padx=(10, 3))
        item_combo = ttk.Combobox(items_top_frame, font=FONTS["body"], width=14, state="readonly")
        item_combo.pack(side=tk.LEFT, padx=3)

        def on_cat_change(*args):
            self._refresh_item_list()
            sub_items = []
            for v in INSPECTION_ITEMS_BY_CATEGORY.get(self._cat_var.get(), {}).values():
                sub_items.extend(v)
            item_combo["values"] = sub_items
            if sub_items:
                item_combo.current(0)

        self._cat_var.trace_add("write", on_cat_change)
        if PROCESSES:
            self._cat_var.set(PROCESSES[0])
        else:
            self._cat_var.set("")
            item_combo["values"] = []

        def add_item():
            selected = item_combo.get()
            if selected and selected not in self._current_items:
                self._current_items.append(selected)
                self._item_vars[selected] = tk.BooleanVar(value=True)
                self._refresh_item_list()

        tk.Button(items_top_frame, text="添加", font=FONTS["small"], command=add_item,
                  bg=COLORS["primary"], fg="white").pack(side=tk.LEFT, padx=5)

        tk.Label(items_top_frame, text="自定义:", font=FONTS["small"], bg="#FFFFFF").pack(side=tk.LEFT, padx=(10, 3))
        custom_var = tk.StringVar()
        tk.Entry(items_top_frame, textvariable=custom_var, font=FONTS["body"], width=10).pack(side=tk.LEFT, padx=3)

        def add_custom_item():
            custom_text = custom_var.get().strip()
            if custom_text and custom_text not in self._current_items:
                self._current_items.append(custom_text)
                self._item_vars[custom_text] = tk.BooleanVar(value=True)
                self._refresh_item_list()
                custom_var.set("")

        tk.Button(items_top_frame, text="自定义", font=FONTS["small"], command=add_custom_item,
                  bg=COLORS["accent"], fg="white").pack(side=tk.LEFT, padx=3)

        tk.Label(items_top_frame, text="搜索:", font=FONTS["small"], bg="#FFFFFF").pack(side=tk.LEFT, padx=(10, 3))
        self._search_var = tk.StringVar()
        tk.Entry(items_top_frame, textvariable=self._search_var, font=FONTS["body"], width=8).pack(side=tk.LEFT, padx=3)

        def on_search_change(*args):
            filter_t = self._search_var.get().strip()
            for w in self._item_list_frame.winfo_children():
                w.destroy()
            tk.Label(self._item_list_frame, text="已选:", font=FONTS["small"], bg="#FFFFFF",
                    fg=COLORS["deep_gray"]).pack(anchor="w", padx=5, pady=(5, 2))
            current_cat = self._cat_var.get()
            if current_cat in INSPECTION_ITEMS_BY_CATEGORY:
                sub_cats = INSPECTION_ITEMS_BY_CATEGORY[current_cat]
                for sub_cat, sub_items in sub_cats.items():
                    tk.Label(self._item_list_frame, text=f"【{sub_cat}】", font=FONTS["small"], bg="#FFFFFF",
                            fg=COLORS["primary"]).pack(anchor="w", padx=5, pady=(3, 1))
                    for item_name in sub_items:
                        if filter_t and filter_t.lower() not in item_name.lower():
                            continue
                        var = self._item_vars.get(item_name, tk.BooleanVar(value=(item_name in self._current_items)))
                        self._item_vars[item_name] = var

                        def make_trace_search(item):
                            def on_change(*args):
                                self._current_items.clear()
                                for it, v in self._item_vars.items():
                                    if v.get():
                                        self._current_items.append(it)
                                self._refresh_formula_list()
                            return on_change
                        var.trace_add("write", make_trace_search(item_name))
                        tk.Checkbutton(self._item_list_frame, text=item_name, variable=var,
                                      font=FONTS["body"], bg="#FFFFFF").pack(anchor="w", padx=15, pady=1)
            for item_name in self._current_items:
                if item_name not in self._item_vars:
                    self._item_vars[item_name] = tk.BooleanVar(value=True)
                var = self._item_vars[item_name]

                def make_trace_search2(item):
                    def on_change(*args):
                        self._current_items.clear()
                        for it, v in self._item_vars.items():
                            if v.get():
                                self._current_items.append(it)
                        self._refresh_formula_list()
                    return on_change
                var.trace_add("write", make_trace_search2(item_name))
                tk.Checkbutton(self._item_list_frame, text=f"+ {item_name}", variable=var,
                              font=FONTS["body"], bg="#FFFFFF").pack(anchor="w", padx=5, pady=1)

        self._search_var.trace_add("write", on_search_change)

        self._refresh_item_list()
        row += 2

        sep = ttk.Separator(frame, orient="horizontal")
        sep.grid(row=row, column=0, columnspan=3, sticky="ew", pady=10)
        row += 1

        tk.Label(frame, text="检查项公式:", font=FONTS["body"], bg="#FFFFFF").grid(row=row, column=0, sticky="nw", pady=8)
        row += 1

        from .rule_dialogs import get_all_param_options_for_quality
        param_opts = get_all_param_options_for_quality()

        formula_top_frame = tk.Frame(frame, bg="#FFFFFF")
        formula_top_frame.grid(row=row, column=1, columnspan=2, sticky="w", pady=8)

        tk.Label(formula_top_frame, text="参数:", font=FONTS["small"], bg="#FFFFFF").pack(side=tk.LEFT, padx=(0, 3))
        param_combo = ttk.Combobox(formula_top_frame, textvariable=self._param_var,
                                    values=param_opts, font=FONTS["body"], width=25, state="readonly")
        param_combo.pack(side=tk.LEFT, padx=3)
        if param_opts:
            param_combo.current(0)
            self._param_var.set(param_opts[0])

        tk.Label(formula_top_frame, text="（点击+参插入参数", font=FONTS["small"], bg="#FFFFFF",
                  fg=COLORS["gray_blue"]).pack(side=tk.LEFT, padx=8)

        formula_list_container = tk.Frame(frame, bg="#FFFFFF")
        formula_list_container.grid(row=row + 1, column=1, columnspan=2, sticky="wens", pady=5)

        self._formula_canvas = tk.Canvas(formula_list_container, bg="#FFFFFF", highlightthickness=0, height=180)
        formula_scrollbar = ttk.Scrollbar(formula_list_container, orient="vertical", command=self._formula_canvas.yview)
        self._formula_inner_frame = tk.Frame(self._formula_canvas, bg="#FFFFFF")

        self._formula_canvas.configure(yscrollcommand=formula_scrollbar.set)
        self._formula_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        formula_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def on_formula_frame_configure(event):
            self._formula_canvas.configure(scrollregion=self._formula_canvas.bbox("all"))

        self._formula_inner_frame.bind("<Configure>", on_formula_frame_configure)
        self._formula_canvas.create_window((0, 0), window=self._formula_inner_frame, anchor="nw")

        self._refresh_formula_list()
        row += 2

        tk.Label(frame, text="优先级:", font=FONTS["body"], bg="#FFFFFF").grid(row=row, column=0, sticky="nw", pady=8)
        self._priority_var = tk.IntVar(value=self._rule.get("priority", 5))
        tk.Entry(frame, textvariable=self._priority_var, font=FONTS["body"], width=10).grid(row=row, column=1, sticky="w", pady=8)

        self._enabled_var = tk.BooleanVar(value=self._rule.get("enabled", True))
        tk.Checkbutton(frame, text="启用", variable=self._enabled_var,
                      font=FONTS["body"], bg="#FFFFFF").grid(row=row, column=2, sticky="w", pady=8)

    def _on_cancel(self):
        self.window.destroy()

    def _on_confirm(self):
        rule_name = self._name_var.get().strip()
        if not rule_name:
            messagebox.showwarning("提示", "规则名称不能为空！", parent=self.window)
            return

        selected_items = [item for item, var in self._item_vars.items() if var.get()]
        priority = self._priority_var.get()
        enabled = self._enabled_var.get()
        process_name = self._cat_var.get()

        items_data = {}
        for item_name, fv in self._item_formula_vars.items():
            fval = fv.get().strip()
            tval = self._item_tolerance_vars.get(item_name, tk.StringVar()).get().strip()
            if fval:
                items_data[item_name] = {"formula": fval, "tolerance": tval}

        if self._is_new:
            success, msg, new_id = QualityRuleDAO.create(
                rule_name, [], "", selected_items, "", priority, enabled, process_name)
            if success and new_id:
                QualityRuleDAO.save_rule_items(new_id, items_data)
        else:
            success, msg, _ = QualityRuleDAO.update(
                self._rule.get("id"), rule_name, [], "", selected_items,
                "", priority, enabled, process_name)
            if success:
                QualityRuleDAO.save_rule_items(self._rule["id"], items_data)

        if success:
            log_ui("质量规则", "✅ 保存规则", f"规则='{rule_name}'")
            messagebox.showinfo("成功", msg, parent=self.window)
            self.window.destroy()
            self._parent_view.load_rules()
        else:
            messagebox.showerror("错误", msg, parent=self.window)

    def _refresh_item_list(self):
        for w in self._item_list_frame.winfo_children():
            w.destroy()
        tk.Label(self._item_list_frame, text="预设项目:", font=FONTS["small"], bg="#FFFFFF",
                fg=COLORS["deep_gray"]).pack(anchor="w", padx=5, pady=(5, 2))
        current_cat = self._cat_var.get()
        if current_cat in INSPECTION_ITEMS_BY_CATEGORY:
            sub_cats = INSPECTION_ITEMS_BY_CATEGORY[current_cat]
            for sub_cat, sub_items in sub_cats.items():
                tk.Label(self._item_list_frame, text=f"【{sub_cat}】", font=FONTS["small"], bg="#FFFFFF",
                        fg=COLORS["primary"]).pack(anchor="w", padx=5, pady=(3, 1))
                for item_name in sub_items:
                    var = self._item_vars.get(item_name, tk.BooleanVar(value=(item_name in self._current_items)))
                    self._item_vars[item_name] = var

                    def make_trace(item):
                        def on_change(*args):
                            self._current_items[:] = [it for it, v in self._item_vars.items() if v.get()]
                            self._refresh_formula_list()
                        return on_change
                    var.trace_add("write", make_trace(item_name))
                    tk.Checkbutton(self._item_list_frame, text=item_name, variable=var,
                                  font=FONTS["body"], bg="#FFFFFF").pack(anchor="w", padx=15, pady=1)

        custom_items = [item for item in self._current_items
                      if item not in [item_name for sub_cats in INSPECTION_ITEMS_BY_CATEGORY.get(current_cat, {}).values() for item_name in sub_cats]]

        if custom_items:
            btn_bar = tk.Frame(self._item_list_frame, bg="#FFFFFF")
            btn_bar.pack(anchor="w", padx=5, pady=(10, 2))
            tk.Label(btn_bar, text="自定义项目:", font=FONTS["small"], bg="#FFFFFF",
                    fg=COLORS["accent"]).pack(side=tk.LEFT, padx=(0, 5))

            def move_up():
                idx = self._item_list_frame.winfo_children().index(btn_bar) - 1
                custom_start = idx + 1
                sel_indices = []
                for i, w in enumerate(self._item_list_frame.winfo_children()[custom_start:], custom_start):
                    if isinstance(w, tk.Frame):
                        for cw in w.winfo_children():
                            if isinstance(cw, tk.Checkbutton) and cw.cget("text").startswith("+ "):
                                sel_indices.append(i)
                                break
                if sel_indices:
                    min_idx = min(sel_indices)
                    if min_idx > custom_start:
                        custom_items.insert(0, custom_items.pop(sel_indices.index(min_idx)))
                        self._current_items[:] = [it for it in self._current_items if it in [item_name for sub_cats in INSPECTION_ITEMS_BY_CATEGORY.get(current_cat, {}).values() for item_name in sub_cats]] + custom_items
                        self._refresh_item_list()

            def move_down():
                pass

            tk.Button(btn_bar, text="⬆ 上移", font=FONTS["small"], command=move_up,
                     bg=COLORS["primary"], fg="white", width=5).pack(side=tk.LEFT, padx=2)
            tk.Button(btn_bar, text="下移 ⬇", font=FONTS["small"], command=move_down,
                     bg=COLORS["primary"], fg="white", width=5).pack(side=tk.LEFT, padx=2)

            custom_frame = tk.Frame(self._item_list_frame, bg="#FFFFFF")
            custom_frame.pack(anchor="w", padx=5, pady=2)
            for item_name in custom_items:
                if item_name not in self._item_vars:
                    self._item_vars[item_name] = tk.BooleanVar(value=True)
                var = self._item_vars[item_name]

                def make_trace(item):
                    def on_change(*args):
                        self._current_items[:] = [it for it, v in self._item_vars.items() if v.get()]
                        self._refresh_formula_list()
                    return on_change
                var.trace_add("write", make_trace(item_name))
                tk.Checkbutton(custom_frame, text=f"+ {item_name}", variable=var,
                              font=FONTS["body"], bg="#FFFFFF").pack(anchor="w", padx=15, pady=1)

    def _refresh_formula_list(self):
        if not hasattr(self, '_formula_inner_frame') or not self._formula_inner_frame:
            return
        try:
            for w in self._formula_inner_frame.winfo_children():
                w.destroy()
            for item_name in self._current_items:
                row_frame = tk.Frame(self._formula_inner_frame, bg="#FFFFFF", pady=3)
                row_frame.pack(fill=tk.X, padx=5)

                tk.Label(row_frame, text=f"{item_name}:", font=FONTS["small"],
                        bg="#FFFFFF", width=12, anchor="e").pack(side=tk.LEFT, padx=(0, 5))

                f_var = tk.StringVar(value=self._existing_items_formulas.get(item_name, ""))
                self._item_formula_vars[item_name] = f_var

                f_entry = tk.Entry(row_frame, textvariable=f_var, font=FONTS["body"], width=15)
                f_entry.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

                def make_add_param(fe):
                    def add_p():
                        fe.insert("insert", self._param_var.get())
                    return add_p

                tk.Button(row_frame, text="+参", font=FONTS["small"], command=make_add_param(f_entry),
                         bg=COLORS["primary"], fg="white", width=3).pack(side=tk.LEFT, padx=1)

                tk.Label(row_frame, text="公差:", font=FONTS["small"],
                        bg="#FFFFFF").pack(side=tk.LEFT, padx=(3, 2))

                t_var = tk.StringVar(value=self._existing_items_tolerances.get(item_name, ""))
                self._item_tolerance_vars[item_name] = t_var

                t_entry = tk.Entry(row_frame, textvariable=t_var, font=FONTS["body"], width=8)
                t_entry.pack(side=tk.LEFT, padx=2)

                def make_del(fv, tv):
                    def del_f():
                        fv.set("")
                        tv.set("")
                    return del_f

                tk.Button(row_frame, text="清", font=FONTS["small"], command=make_del(f_var, t_var),
                         bg=COLORS["warning"], fg="white", width=3).pack(side=tk.LEFT, padx=1)
        except Exception:
            pass


def get_all_param_options_for_quality() -> list:
    from models.database import get_connection
    from utils.order_templates import DIM_FIELDS, MATERIAL_FIELDS
    from desktop.views.quality_rule_view import get_custom_material_params, get_custom_surface_params

    def get_all_dim_options():
        options = []
        for f in DIM_FIELDS:
            if f["key"] not in options:
                options.append(f["key"])
        skirt_params = [f["key"] for f in DIM_FIELDS if "裙边" in f["key"]]
        for sp in skirt_params:
            if sp not in options:
                options.append(sp)
        return options

    dim_options = get_all_dim_options()
    material_options = [f["key"] for f in MATERIAL_FIELDS]
    custom_material_options = get_custom_material_params()
    custom_surface_options = get_custom_surface_params()
    all_params = dim_options + material_options + custom_material_options + custom_surface_options + ["物料数量"]
    return list(dict.fromkeys(all_params))


class MaterialRuleDialog(BaseDialog):
    def __init__(self, parent_view, product_type: str, rule_data: dict = None):
        self._parent_view = parent_view
        self._product_type = product_type
        self._rule_data = rule_data
        self._is_edit = rule_data is not None
        super().__init__(parent_view, "编辑规则" if self._is_edit else "添加规则", 720, 550)

    def _build_ui(self):
        from config import MATERIALS, MATERIAL_DENSITIES

        frame = tk.Frame(self.window, bg="#FFFFFF", padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="产品类型:", font=FONTS["body"], bg="#FFFFFF").grid(row=0, column=0, sticky="w", pady=5)
        tk.Label(frame, text=self._product_type, font=FONTS["body"], bg="#E3F2FD").grid(row=0, column=1, sticky="w", pady=5)

        tk.Label(frame, text="━━━ 物料种类配置 ━━━", font=FONTS["subtitle"], bg="#FFFFFF",
                fg=COLORS["primary"]).grid(row=1, column=0, columnspan=2, sticky="w", pady=(15, 5))

        tk.Label(frame, text="材质参数 *:", font=FONTS["body"], bg="#FFFFFF").grid(row=2, column=0, sticky="w", pady=5)

        new_rule = not self._is_edit

        if new_rule:
            from desktop.views.material_rules_view import get_all_material_param_options
            all_material_params = get_all_material_param_options()
            param_combo = ttk.Combobox(frame, values=all_material_params, width=25, font=FONTS["body"], state="readonly")
            param_combo.grid(row=2, column=1, sticky="w", pady=5)
            if all_material_params:
                param_combo.current(0)
        else:
            tk.Label(frame, text=self._rule_data["material_param"], font=FONTS["body"], bg="#E3F2FD").grid(row=2, column=1, sticky="w", pady=5)
            param_combo = None

        tk.Label(frame, text="物料名称 *:", font=FONTS["body"], bg="#FFFFFF").grid(row=3, column=0, sticky="w", pady=5)

        name_combo = ttk.Combobox(frame, values=[], width=25, font=FONTS["body"], state="readonly")
        name_combo.grid(row=3, column=1, sticky="w", pady=5)

        if self._is_edit:
            from utils.material_calculator import MaterialCalculator
            material_params = MaterialCalculator.get_material_params_for_product(self._rule_data["product_type"])
            param_names = [p["key"] for p in material_params]
            current_mat_param = self._rule_data["material_param"]
            if current_mat_param in param_names:
                param_name_clean = current_mat_param.replace("材质", "")
                material_names = [f"{mat_val}{param_name_clean}" for mat_val in MATERIALS]
                name_combo["values"] = material_names
                current_material_name = self._rule_data["material_name_template"]
                if current_material_name in material_names:
                    name_combo.set(current_material_name)
                    current_density = None
                    for mat, density in MATERIAL_DENSITIES.items():
                        if current_material_name.startswith(mat):
                            current_density = density
                            break
                elif material_names:
                    name_combo.current(0)
                    current_density = MATERIAL_DENSITIES.get(MATERIALS[0])
                else:
                    current_density = None
            else:
                name_combo["values"] = [self._rule_data["material_name_template"]]
                name_combo.set(self._rule_data["material_name_template"])
                current_density = None
        else:
            current_density = None

        tk.Label(frame, text="材质密度:", font=FONTS["body"], bg="#FFFFFF").grid(row=4, column=0, sticky="w", pady=5)
        density_lbl = tk.Label(frame, text=f"{current_density} kg/m³" if current_density else "--",
                              font=FONTS["body"], bg="#E3F2FD", width=25, anchor="w")
        density_lbl.grid(row=4, column=1, sticky="w", pady=5)

        if new_rule:
            def on_param_select(event):
                selected_param = param_combo.get()
                if selected_param:
                    param_name_clean = selected_param.replace("材质", "")
                    material_names = [f"{mat_val}{param_name_clean}" for mat_val in MATERIALS]
                    name_combo["values"] = material_names
                    if material_names:
                        name_combo.current(0)
                        first_mat = MATERIALS[0]
                        density = MATERIAL_DENSITIES.get(first_mat, 0)
                        density_lbl.config(text=f"{density} kg/m³" if density else "--")

            param_combo.bind("<<ComboboxSelected>>", on_param_select)

        def on_name_select(event):
            selected_name = name_combo.get()
            if selected_name:
                for mat, density in MATERIAL_DENSITIES.items():
                    if selected_name.startswith(mat):
                        density_lbl.config(text=f"{density} kg/m³")
                        return
                density_lbl.config(text="--")

        name_combo.bind("<<ComboboxSelected>>", on_name_select)

        tk.Label(frame, text="规格字段:", font=FONTS["body"], bg="#FFFFFF").grid(row=5, column=0, sticky="w", pady=5)

        from desktop.views.material_rules_view import get_all_spec_field_options
        spec_combo = ttk.Combobox(frame, values=get_all_spec_field_options(), width=15, font=FONTS["body"])
        spec_combo.grid(row=5, column=1, sticky="w", pady=5)
        spec_combo.current(0)

        def refresh_spec_options(event):
            current = spec_combo.get()
            spec_combo['values'] = get_all_spec_field_options()
            if current in spec_combo['values']:
                spec_combo.set(current)
            else:
                spec_combo.current(0)

        spec_combo.bind("<FocusIn>", refresh_spec_options)

        selected_specs = []
        if self._is_edit:
            current_spec = self._rule_data.get("spec_field", "") or ""
            if current_spec:
                for s in get_all_spec_field_options():
                    if s in current_spec and s not in selected_specs:
                        selected_specs.append(s)

        spec_lbl = tk.Label(frame, text=f"已选: {''.join(selected_specs) if selected_specs else '无'}",
                           font=FONTS["body"], bg="#E3F2FD", width=15, anchor="w")
        spec_lbl.grid(row=5, column=2, sticky="w", padx=3)

        def add_spec():
            selected = spec_combo.get()
            if selected and selected not in selected_specs:
                selected_specs.append(selected)
                spec_lbl.config(text=f"已选: {''.join(selected_specs)}")

        def remove_spec():
            if selected_specs:
                selected_specs.pop()
                spec_lbl.config(text=f"已选: {''.join(selected_specs) if selected_specs else '无'}")

        tk.Button(frame, text="添加", font=FONTS["body"], command=add_spec,
                 bg=COLORS["primary"], fg="white", width=4).grid(row=5, column=3, sticky="w", padx=(2,0))
        tk.Button(frame, text="删除", font=FONTS["body"], command=remove_spec,
                 bg="#FF5722", fg="white", width=4).grid(row=5, column=4, sticky="w", padx=2)

        tk.Label(frame, text="规格单位:", font=FONTS["body"], bg="#FFFFFF").grid(row=6, column=0, sticky="w", pady=5)

        current_spec_unit = self._rule_data.get("spec_unit", "") if self._is_edit else ""
        spec_unit_values = ["自动"] + get_unit_options()
        spec_unit_combo = ttk.Combobox(frame, values=spec_unit_values, width=25, font=FONTS["body"])
        spec_unit_combo.grid(row=6, column=1, sticky="w", pady=5)
        if self._is_edit and current_spec_unit and current_spec_unit in spec_unit_values:
            spec_unit_combo.set(current_spec_unit)
        else:
            spec_unit_combo.current(0)
        tk.Label(frame, text="(自动从规格字段获取或手动选择)", font=("微软雅黑", 9), bg="#FFF8E1", fg="#FF8F00").grid(row=7, column=1, sticky="w", pady=2)

        tk.Label(frame, text="━━━ 数量计算配置 ━━━", font=FONTS["subtitle"], bg="#FFFFFF",
                fg=COLORS["primary"]).grid(row=8, column=0, columnspan=2, sticky="w", pady=(15, 5))

        tk.Label(frame, text="数量公式:", font=FONTS["body"], bg="#FFFFFF").grid(row=9, column=0, sticky="w", pady=5)
        formula_entry = ttk.Entry(frame, width=28, font=FONTS["body"])
        formula_entry.grid(row=9, column=1, sticky="w", pady=5)
        if self._is_edit:
            formula_entry.insert("0", self._rule_data.get("qty_formula") or "")
        tk.Label(frame, text='如: {qty}×1.2 或 {qty}÷0.5', font=("微软雅黑", 9), bg="#FFF8E1", fg="#FF8F00").grid(row=10, column=1, sticky="w", pady=2)

        tk.Label(frame, text="插入规格:", font=FONTS["body"], bg="#FFFFFF").grid(row=11, column=0, sticky="w", pady=5)
        spec_combo2 = ttk.Combobox(frame, values=["无"] + get_all_spec_field_options(), width=20, font=FONTS["body"])
        spec_combo2.grid(row=11, column=1, sticky="w", pady=5)
        spec_combo2.current(0)

        def refresh_spec_options2(event):
            current = spec_combo2.get()
            spec_combo2['values'] = ["无"] + get_all_spec_field_options()
            if current in spec_combo2['values']:
                spec_combo2.set(current)
            else:
                spec_combo2.current(0)

        spec_combo2.bind("<FocusIn>", refresh_spec_options2)

        def insert_spec_to_formula():
            selected = spec_combo2.get()
            if selected and selected != "无":
                formula_entry.insert(tk.INSERT, selected)
                formula_entry.focus_set()

        tk.Button(frame, text="添加", font=FONTS["body"], command=insert_spec_to_formula,
                 bg=COLORS["primary"], fg="white", width=5).grid(row=13, column=2, sticky="w", padx=5, pady=5)

        tk.Label(frame, text="数量单位:", font=FONTS["body"], bg="#FFFFFF").grid(row=14, column=0, sticky="w", pady=5)
        qty_unit_combo = ttk.Combobox(frame, values=["无"] + get_unit_options(), width=25, font=FONTS["body"])
        qty_unit_combo.grid(row=14, column=1, sticky="w", pady=5)

        if self._is_edit:
            current_qty_unit = self._rule_data.get("qty_unit", "")
            unit_opts = ["无"] + get_unit_options()
            found = False
            for i, u in enumerate(unit_opts):
                if u == current_qty_unit:
                    qty_unit_combo.current(i)
                    found = True
                    break
            if not found:
                qty_unit_combo.current(0)
        else:
            qty_unit_combo.current(0)

        enabled_var = None
        if self._is_edit:
            tk.Label(frame, text="启用状态:", font=FONTS["body"], bg="#FFFFFF").grid(row=15, column=0, sticky="w", pady=5)
            enabled_var = tk.BooleanVar(value=bool(self._rule_data.get("enabled")))
            tk.Checkbutton(frame, text="启用此规则", variable=enabled_var, bg="#FFFFFF").grid(row=15, column=1, sticky="w", pady=5)

        self._store_widget_refs(name_combo, param_combo, spec_combo, spec_combo2, formula_entry,
                               spec_unit_combo, qty_unit_combo, spec_lbl, density_lbl,
                               selected_specs, enabled_var)

    def _store_widget_refs(self, name_combo, param_combo, spec_combo, spec_combo2, formula_entry,
                          spec_unit_combo, qty_unit_combo, spec_lbl, density_lbl,
                          selected_specs, enabled_var):
        self._name_combo = name_combo
        self._param_combo = param_combo
        self._spec_combo = spec_combo
        self._spec_combo2 = spec_combo2
        self._formula_entry = formula_entry
        self._spec_unit_combo = spec_unit_combo
        self._qty_unit_combo = qty_unit_combo
        self._spec_lbl = spec_lbl
        self._density_lbl = density_lbl
        self._selected_specs = selected_specs
        self._enabled_var = enabled_var

    def _on_cancel(self):
        self.window.destroy()

    def _on_confirm(self):
        material_name = self._name_combo.get().strip()
        if self._is_edit:
            if not material_name:
                messagebox.showerror("错误", "请选择物料名称", parent=self.window)
                return
            spec_field_str = ",".join(self._selected_specs) if self._selected_specs else None
            spec_unit = self._spec_unit_combo.get().strip()
            if spec_unit == "自动":
                spec_unit = None
            qty_formula = self._formula_entry.get().strip()
            if not qty_formula:
                qty_formula = None
            qty_unit = self._qty_unit_combo.get().strip()
            if qty_unit == "无":
                qty_unit = None
            try:
                MaterialRulesDAO.update(self._rule_data["id"], {
                    "material_name_template": material_name,
                    "spec_field": spec_field_str,
                    "spec_unit": spec_unit,
                    "qty_field": "quantity",
                    "qty_formula": qty_formula,
                    "qty_unit": qty_unit,
                    "enabled": self._enabled_var.get()
                })
                messagebox.showinfo("成功", "规则已更新", parent=self.window)
                self.window.destroy()
                self._parent_view.load_rules()
            except Exception as e:
                messagebox.showerror("错误", f"更新失败: {e}", parent=self.window)
        else:
            material_param = self._param_combo.get().strip()
            if not material_param:
                messagebox.showerror("错误", "请选择材质参数", parent=self.window)
                return
            if not material_name:
                messagebox.showerror("错误", "请选择物料名称", parent=self.window)
                return
            spec_field_str = ",".join(self._selected_specs) if self._selected_specs else None
            spec_unit = self._spec_unit_combo.get().strip()
            if spec_unit == "自动":
                spec_unit = None
            qty_formula = self._formula_entry.get().strip()
            if not qty_formula:
                qty_formula = None
            qty_unit = self._qty_unit_combo.get().strip()
            if qty_unit == "无":
                qty_unit = None
            try:
                MaterialRulesDAO.create(
                    self._product_type, material_param, material_name,
                    spec_field_str, spec_unit, "quantity", qty_formula, qty_unit
                )
                messagebox.showinfo("成功", "规则已添加", parent=self.window)
                self.window.destroy()
                self._parent_view.load_rules()
            except Exception as e:
                messagebox.showerror("错误", f"添加失败: {e}", parent=self.window)


class SaveRuleTemplateDialog(BaseDialog):
    def __init__(self, parent_view, current_product_type):
        self._parent_view = parent_view
        self._current_product_type = current_product_type
        self._name_var = None
        self._desc_text = None
        super().__init__(parent_view, "💾 保存模板", 400, 250)

    def _build_ui(self):
        frame = tk.Frame(self.window, bg="#FFFFFF", padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="模板名称:", font=FONTS["body"], bg="#FFFFFF").grid(row=0, column=0, sticky="w", pady=10)
        self._name_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self._name_var, width=25, font=FONTS["body"]).grid(row=0, column=1, sticky="w", pady=10)

        tk.Label(frame, text="模板描述:", font=FONTS["body"], bg="#FFFFFF").grid(row=1, column=0, sticky="nw", pady=10)
        self._desc_text = tk.Text(frame, width=25, height=4, font=FONTS["body"])
        self._desc_text.grid(row=1, column=1, sticky="w", pady=10)

        btn_frame = tk.Frame(frame, bg="#FFFFFF")
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="取消", width=10, command=self._on_cancel).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="保存", width=10, command=self._on_confirm, style="Accent.TButton").pack(side=tk.LEFT, padx=10)

    def _on_cancel(self):
        self.window.destroy()

    def _validate(self):
        name = self._name_var.get().strip()
        if not name:
            messagebox.showerror("错误", "请输入模板名称", parent=self.window)
            return False
        return True

    def _on_confirm(self):
        from models.material_rules_template import save_template
        name = self._name_var.get().strip()
        if not name:
            messagebox.showerror("错误", "请输入模板名称", parent=self.window)
            return
        description = self._desc_text.get("1.0", tk.END).strip()
        rules = MaterialRulesDAO.get_by_product_type(self._current_product_type)
        success, msg = save_template(name, rules, description)
        if success:
            messagebox.showinfo("成功", msg, parent=self.window)
            self.window.destroy()
        else:
            messagebox.showerror("错误", msg, parent=self.window)


class LoadRuleTemplateDialog(BaseDialog):
    def __init__(self, parent_view):
        self._parent_view = parent_view
        self._template_combo = None
        super().__init__(parent_view, "📥 载入模板", 400, 180)

    def _build_ui(self):
        from models.material_rules_template import get_template_names
        template_names = get_template_names()

        frame = tk.Frame(self.window, bg="#FFFFFF", padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="选择模板:", font=FONTS["body"], bg="#FFFFFF").grid(row=0, column=0, sticky="w", pady=10)

        self._template_combo = ttk.Combobox(frame, values=template_names, width=23, font=FONTS["body"], state="readonly")
        self._template_combo.grid(row=0, column=1, sticky="w", pady=10)
        if template_names:
            self._template_combo.current(0)

        btn_frame = tk.Frame(frame, bg="#FFFFFF")
        btn_frame.grid(row=1, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="取消", width=10, command=self._on_cancel).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="载入", width=10, command=self._on_confirm, style="Accent.TButton").pack(side=tk.LEFT, padx=10)

    def _on_cancel(self):
        self.window.destroy()

    def _on_confirm(self):
        from models.material_rules_template import get_template
        selected_name = self._template_combo.get()
        template = get_template(selected_name)
        if not template:
            messagebox.showerror("错误", "模板不存在", parent=self.window)
            return
        rules = template.get("rules", [])
        if not rules:
            messagebox.showinfo("提示", "模板中没有规则", parent=self.window)
            return
        confirm = messagebox.askyesno("确认",
            f"将载入模板「{selected_name}」的 {len(rules)} 条规则\n\n是否继续？", parent=self.window)
        if not confirm:
            return
        for rule in rules:
            MaterialRulesDAO.create(
                rule["product_type"], rule["material_param"],
                rule["material_name_template"], rule.get("spec_field"), rule.get("spec_unit")
            )
        messagebox.showinfo("成功", f"已载入 {len(rules)} 条规则", parent=self.window)
        self.window.destroy()
        self._parent_view.load_rules()


class ManageRuleTemplatesDialog(BaseDialog):
    def __init__(self, parent_view):
        self._parent_view = parent_view
        self._selected_template = [None]
        self._template_tree = None
        super().__init__(parent_view, "📂 管理模板", 700, 500)

    def _build_ui(self):
        from models.material_rules_template import get_all_templates

        frame = tk.Frame(self.window, bg="#FFFFFF", padx=15, pady=15)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="模板列表", font=FONTS["subtitle"], bg="#FFFFFF",
                fg=COLORS["text_primary"]).pack(anchor="w", pady=(0, 10))

        list_frame = tk.Frame(frame, bg="#FFFFFF")
        list_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("name", "description", "rules_count", "created_at")
        self._template_tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=12)

        for col, txt, w in [
            ("name", "模板名称", 150),
            ("description", "描述", 250),
            ("rules_count", "规则数", 80),
            ("created_at", "创建时间", 140)
        ]:
            self._template_tree.heading(col, text=txt)
            self._template_tree.column(col, width=w, anchor="w")

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self._template_tree.yview)
        self._template_tree.configure(yscrollcommand=scrollbar.set)
        self._template_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        templates = get_all_templates()
        for t in templates:
            self._template_tree.insert("", tk.END, values=(
                t.get("name", ""),
                t.get("description", ""),
                len(t.get("rules", [])),
                t.get("created_at", "")
            ))

        btn_frame = tk.Frame(frame, bg="#FFFFFF", pady=10)
        btn_frame.pack(fill=tk.X)

        def on_select(event):
            selection = self._template_tree.selection()
            if selection:
                item = self._template_tree.item(selection[0])
                self._selected_template[0] = item["values"][0]

        self._template_tree.bind("<<TreeviewSelect>>", on_select)

        ttk.Button(btn_frame, text="✏️ 重命名", command=self._do_rename).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🗑️ 删除", command=self._do_delete).pack(side=tk.LEFT, padx=5)

        bottom_frame = tk.Frame(frame, bg="#FFFFFF")
        bottom_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(bottom_frame, text="关闭", width=10, command=self._on_cancel).pack(side=tk.RIGHT)

    def _on_cancel(self):
        self.window.destroy()

    def _do_rename(self):
        from models.material_rules_template import rename_template

        if not self._selected_template[0]:
            messagebox.showwarning("提示", "请选择要重命名的模板", parent=self.window)
            return

        old_name = self._selected_template[0]

        rename_dialog = tk.Toplevel(self.window)
        rename_dialog.title("✏️ 重命名模板")
        from utils.window_manager import setup_resizable_window
        setup_resizable_window(rename_dialog, "rename_template", "300x120")
        rename_dialog.transient(self.window)
        rename_dialog.grab_set()

        rename_frame = tk.Frame(rename_dialog, bg="#FFFFFF", padx=20, pady=20)
        rename_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(rename_frame, text="新名称:", font=FONTS["body"], bg="#FFFFFF").pack(anchor="w", pady=5)
        new_name_entry = ttk.Entry(rename_frame, width=20, font=FONTS["body"])
        new_name_entry.pack(pady=5)
        new_name_entry.insert(0, old_name)

        def do_rename_confirm():
            new_name = new_name_entry.get().strip()
            if not new_name:
                messagebox.showerror("错误", "名称不能为空", parent=rename_dialog)
                return
            success, msg = rename_template(old_name, new_name)
            if success:
                messagebox.showinfo("成功", msg, parent=rename_dialog)
                rename_dialog.destroy()
                self.window.destroy()
                ManageRuleTemplatesDialog(self._parent_view)
            else:
                messagebox.showerror("错误", msg, parent=rename_dialog)

        btn_frame2 = tk.Frame(rename_frame, bg="#FFFFFF")
        btn_frame2.pack(pady=10)
        ttk.Button(btn_frame2, text="取消", width=8, command=rename_dialog.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame2, text="确定", width=8, command=do_rename_confirm).pack(side=tk.LEFT, padx=5)

    def _do_delete(self):
        from models.material_rules_template import delete_template

        if not self._selected_template[0]:
            messagebox.showwarning("提示", "请选择要删除的模板", parent=self.window)
            return

        template_name = self._selected_template[0]
        confirm = messagebox.askyesno("确认删除", f"确定要删除模板「{template_name}」吗？\n\n此操作不可恢复！", parent=self.window)
        if not confirm:
            return

        success, msg = delete_template(template_name)
        if success:
            messagebox.showinfo("成功", msg, parent=self.window)
            self.window.destroy()
            ManageRuleTemplatesDialog(self._parent_view)
        else:
            messagebox.showerror("错误", msg, parent=self.window)


def _get_process_dim_options() -> list:
    """获取工序规则可用的尺寸/材质参数选项"""
    options = []
    for f in DIM_FIELDS:
        if f["key"] not in options:
            options.append(f["key"])
    skirt_params = [f["key"] for f in DIM_FIELDS if "裙边" in f["key"]]
    for sp in skirt_params:
        if sp not in options:
            options.append(sp)
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM custom_dim_params")
        for row in cursor.fetchall():
            name = row[0] if isinstance(row, tuple) else row["name"]
            if name not in options:
                options.append(name)
    except Exception:
        pass
    cursor.close()
    conn.close()
    return options


class SaveProcessRuleTemplateDialog(BaseDialog):
    """保存工序规则模板对话框"""

    def __init__(self, parent_view):
        self._parent_view = parent_view
        self._name_var = None
        self._desc_text = None
        super().__init__(parent_view, "💾 保存工序规则模板", 400, 250)

    def _build_ui(self):
        frame = tk.Frame(self.window, bg="#FFFFFF", padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="模板名称:", font=FONTS["body"], bg="#FFFFFF").grid(row=0, column=0, sticky="w", pady=5)
        self._name_var = tk.StringVar()
        tk.Entry(frame, textvariable=self._name_var, font=FONTS["body"], width=30).grid(row=0, column=1, sticky="w", pady=5)

        tk.Label(frame, text="描述:", font=FONTS["body"], bg="#FFFFFF").grid(row=1, column=0, sticky="nw", pady=5)
        self._desc_text = tk.Text(frame, font=FONTS["body"], width=30, height=4)
        self._desc_text.grid(row=1, column=1, sticky="w", pady=5)

        btn_frame = tk.Frame(frame, bg="#FFFFFF")
        btn_frame.grid(row=2, column=0, columnspan=2, pady=15)
        ttk.Button(btn_frame, text="取消", width=10, command=self._on_cancel).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="保存", width=10, command=self._on_confirm, style="Accent.TButton").pack(side=tk.LEFT, padx=10)

    def _on_cancel(self):
        self.window.destroy()

    def _validate(self):
        name = self._name_var.get().strip()
        if not name:
            messagebox.showerror("错误", "模板名称不能为空！", parent=self.window)
            return False
        return True

    def _on_confirm(self):
        if not self._validate():
            return
        name = self._name_var.get().strip()
        desc = self._desc_text.get("1.0", "end-1c").strip()
        rules = ProcessCalcRuleDAO.get_all()

        def convert_for_json(obj):
            if isinstance(obj, dict):
                return {k: convert_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_for_json(item) for item in obj]
            elif hasattr(obj, 'strftime'):
                return obj.strftime("%Y-%m-%d %H:%M:%S")
            return obj

        rules_json = json.dumps(convert_for_json(rules), ensure_ascii=False)

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id FROM process_rules_templates WHERE name=%s", (name,))
            existing = cursor.fetchone()

            if existing:
                cursor.execute("""
                    UPDATE process_rules_templates
                    SET conditions_json=%s, actions_json=%s, description=%s, updated_at=NOW()
                    WHERE name=%s
                """, (rules_json, "", desc, name))
            else:
                cursor.execute("""
                    INSERT INTO process_rules_templates (name, conditions_json, actions_json, description, priority)
                    VALUES (%s, %s, %s, %s, 5)
                """, (name, rules_json, "", desc))

            conn.commit()
            messagebox.showinfo("成功", f"模板「{name}」已保存！", parent=self.window)
            self.window.destroy()
        except Exception as e:
            messagebox.showerror("错误", f"保存失败：{str(e)}", parent=self.window)
        finally:
            cursor.close()
            conn.close()


class ProcessRuleEditDialog(BaseDialog):
    """工序规则编辑对话框"""

    def __init__(self, parent_view, rule: dict, is_new: bool = False):
        self._parent_view = parent_view
        self._rule = rule
        self._is_new = is_new
        self._current_types = []
        self._type_var = None
        self._type_combo = None
        self._selected_types_listbox = None
        self._dim_var = None
        self._dim_combo = None
        self._cond_text = None
        self._priority_spin = None
        self._enabled_var = None
        self._default_worker_entry = None
        self._unit_combo = None
        super().__init__(parent_view, f"编辑规则 - {rule['process_name']}", 750, 720, resizable=True)

    def _build_ui(self):
        rule = self._rule

        frame = tk.Frame(self.window, bg="#FFFFFF", padx=20, pady=15)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text=f"工序：{rule['process_name']}", font=FONTS["subtitle"], bg="#FFFFFF",
                fg=COLORS["primary"]).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 15))

        tk.Label(frame, text="━━━ 第一框：生效条件（产品类型） ━━━", font=FONTS["body"], bg="#FFFFFF",
                fg=COLORS["primary"]).grid(row=1, column=0, columnspan=3, sticky="w", pady=(5, 10))

        tk.Label(frame, text="选择产品:", font=FONTS["body"], bg="#FFFFFF").grid(row=2, column=0, sticky="nw", pady=5)

        skirt_params = [f["key"] for f in DIM_FIELDS if "裙边" in f["key"]]
        product_types = ProductTypeDAO.get_all_names() + skirt_params
        try:
            pt_json = rule.get("product_types_json") or "[]"
            if pt_json and pt_json != "[]":
                self._current_types = json.loads(pt_json)
        except Exception:
            self._current_types = []

        type_select_frame = tk.Frame(frame, bg="#FFFFFF")
        type_select_frame.grid(row=2, column=1, columnspan=2, sticky="w", pady=5)

        self._type_var = tk.StringVar()
        self._type_combo = ttk.Combobox(type_select_frame, textvariable=self._type_var,
                                         font=FONTS["body"], width=22, state="readonly")
        self._type_combo.pack(side=tk.LEFT, padx=(0, 5))
        self._type_combo["values"] = product_types
        self._type_combo.update()

        self._selected_types_listbox = tk.Listbox(type_select_frame, font=FONTS["body"],
                                                   height=3, width=25, selectmode=tk.EXTENDED)
        self._selected_types_listbox.pack(side=tk.LEFT, padx=5)

        for pt in self._current_types:
            self._selected_types_listbox.insert(tk.END, pt)

        def add_type():
            selected = self._type_var.get()
            if selected and selected not in self._current_types:
                self._current_types.append(selected)
                self._selected_types_listbox.insert(tk.END, selected)

        def add_all_types():
            for pt in product_types:
                if pt not in self._current_types:
                    self._current_types.append(pt)
                    self._selected_types_listbox.insert(tk.END, pt)

        def remove_type():
            sel = self._selected_types_listbox.curselection()
            for idx in reversed(sel):
                self._selected_types_listbox.delete(idx)
                self._current_types.pop(idx)

        btn_frame1 = tk.Frame(type_select_frame, bg="#FFFFFF")
        btn_frame1.pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame1, text="添加", font=FONTS["small"], command=add_type,
                  bg=COLORS["primary"], fg="white").pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame1, text="添加全部", font=FONTS["small"], command=add_all_types,
                  bg="#27AE60", fg="white").pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame1, text="移除", font=FONTS["small"], command=remove_type,
                  bg="#E74C3C", fg="white").pack(side=tk.LEFT, padx=2)

        tk.Label(frame, text="━━━ 第二框：工序计划数量计算（尺寸+材质参数） ━━━", font=FONTS["body"], bg="#FFFFFF",
                fg=COLORS["primary"]).grid(row=3, column=0, columnspan=3, sticky="w", pady=(15, 10))

        tk.Label(frame, text="选择参数:", font=FONTS["body"], bg="#FFFFFF").grid(row=4, column=0, sticky="nw", pady=5)

        dim_options = _get_process_dim_options()
        material_options = [f["key"] for f in MATERIAL_FIELDS]
        all_param_options = dim_options + material_options + ["物料数量"]
        cond_expr = rule.get("planned_qty_formula") or ""

        dim_select_frame = tk.Frame(frame, bg="#FFFFFF")
        dim_select_frame.grid(row=4, column=1, columnspan=2, sticky="w", pady=5)

        self._dim_var = tk.StringVar()
        self._dim_combo = ttk.Combobox(dim_select_frame, textvariable=self._dim_var,
                                        font=FONTS["body"], width=25, state="readonly")
        self._dim_combo.pack(side=tk.LEFT, padx=(0, 5))
        self._dim_combo["values"] = all_param_options
        self._dim_combo.update()

        def add_dim():
            selected = self._dim_var.get()
            if selected:
                self._cond_text.insert("insert", selected)

        tk.Button(dim_select_frame, text="添加", font=FONTS["small"], command=add_dim,
                  bg=COLORS["primary"], fg="white").pack(side=tk.LEFT)

        cond_frame = tk.Frame(frame, bg="#FFFFFF")
        cond_frame.grid(row=5, column=1, columnspan=2, sticky="w", pady=5)

        self._cond_text = tk.Text(cond_frame, width=45, height=4, font=FONTS["body"])
        self._cond_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._cond_text.insert("1.0", cond_expr)

        cond_scroll = ttk.Scrollbar(cond_frame, orient="vertical", command=self._cond_text.yview)
        self._cond_text.configure(yscrollcommand=cond_scroll.set)
        cond_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        tk.Label(frame, text="━━━ 其他设置 ━━━", font=FONTS["body"], bg="#FFFFFF",
                fg=COLORS["primary"]).grid(row=6, column=0, columnspan=3, sticky="w", pady=(15, 10))

        tk.Label(frame, text="优先级:", font=FONTS["body"], bg="#FFFFFF").grid(row=7, column=0, sticky="w", pady=5)
        self._priority_spin = ttk.Spinbox(frame, from_=1, to=10, width=10, font=FONTS["body"])
        self._priority_spin.grid(row=7, column=1, sticky="w", pady=5)
        self._priority_spin.set(rule.get("priority", 5))

        tk.Label(frame, text="启用规则:", font=FONTS["body"], bg="#FFFFFF").grid(row=7, column=2, sticky="w", pady=5)
        self._enabled_var = tk.BooleanVar(value=bool(rule.get("enabled", True)))
        tk.Checkbutton(frame, text="启用", variable=self._enabled_var, font=FONTS["body"], bg="#FFFFFF").grid(row=7, column=2, sticky="w", pady=5)

        tk.Label(frame, text="默认负责人:", font=FONTS["body"], bg="#FFFFFF").grid(row=8, column=0, sticky="w", pady=5)
        default_worker_var = tk.StringVar(value=rule.get("default_worker", ""))
        self._default_worker_entry = ttk.Combobox(frame, textvariable=default_worker_var, width=18, font=FONTS["body"])
        self._default_worker_entry.grid(row=8, column=1, sticky="w", pady=5)
        try:
            conn_w = get_connection()
            cursor_w = conn_w.cursor()
            cursor_w.execute("SELECT DISTINCT assigned_to FROM production_orders WHERE assigned_to IS NOT NULL AND assigned_to != ''")
            workers = [r['assigned_to'] for r in cursor_w.fetchall()]
            cursor_w.close()
            conn_w.close()
            self._default_worker_entry["values"] = workers
        except Exception:
            pass

        tk.Label(frame, text="工序单位:", font=FONTS["body"], bg="#FFFFFF").grid(row=9, column=0, sticky="w", pady=5)
        self._unit_var = tk.StringVar(value=rule.get("unit", "件"))
        self._unit_combo = ttk.Combobox(frame, textvariable=self._unit_var, width=18, font=FONTS["body"],
                                         state="readonly")
        self._unit_combo.grid(row=9, column=1, sticky="w", pady=5)
        self._unit_combo["values"] = ["件", "米", "个", "条", "根", "片", "卷", "套", "批", "kg"]

        btn_frame = tk.Frame(self.window, bg="#FFFFFF")
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=15, padx=20)
        ttk.Button(btn_frame, text="取消", width=12, command=self._on_cancel).pack(side=tk.RIGHT, padx=10)
        ttk.Button(btn_frame, text="保存", width=12, command=self._on_confirm, style="Accent.TButton").pack(side=tk.RIGHT, padx=10)

    def _on_cancel(self):
        self.window.destroy()

    def _on_confirm(self):
        new_formula = self._cond_text.get("1.0", "end-1c").strip()
        new_priority = int(self._priority_spin.get())
        new_enabled = self._enabled_var.get()
        new_default_worker = self._default_worker_entry.get().strip()
        new_unit = self._unit_var.get().strip() or "件"
        rule = self._rule

        action = "新建规则" if self._is_new else "更新规则"
        log_ui("工序规则", action, f"工序='{rule['process_name']}', 公式='{new_formula}', 负责人='{new_default_worker}', 单位='{new_unit}'")

        if self._is_new:
            success, msg, _ = ProcessCalcRuleDAO.create(
                process_name=rule["process_name"],
                product_types=self._current_types,
                condition_expr="所有产品类型",
                planned_qty_formula=new_formula,
                priority=new_priority,
                enabled=new_enabled,
                default_worker=new_default_worker,
                unit=new_unit
            )
        else:
            success, msg = ProcessCalcRuleDAO.update(
                rule_id=rule["id"],
                process_name=rule["process_name"],
                product_types=self._current_types,
                condition_expr="所有产品类型",
                planned_qty_formula=new_formula,
                priority=new_priority,
                enabled=new_enabled,
                default_worker=new_default_worker,
                unit=new_unit
            )

        if success:
            messagebox.showinfo("成功", msg, parent=self.window)
            self.window.destroy()
            self._parent_view.load_rules()
        else:
            messagebox.showerror("错误", msg, parent=self.window)


class FlowTypeConfigDialog(BaseDialog):
    def __init__(self, parent_view):
        self._parent_view = parent_view
        from models.product_type import ProductTypeDAO
        self._types = ProductTypeDAO.get_all()
        super().__init__(parent_view, "流程类型设置", 420, 80 + len(self._types) * 35)

    def _build_ui(self):
        from utils.custom_types import set_product_flow_type
        frame = tk.Frame(self.window, bg="#FFFFFF", padx=15, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)
        tk.Label(frame, text="产品类型", font=FONTS["normal_bold"], bg="#FFFFFF").grid(row=0, column=0, sticky="w", padx=10)
        tk.Label(frame, text="流程", font=FONTS["normal_bold"], bg="#FFFFFF").grid(row=0, column=1, padx=10)
        vars_map = {}
        for i, pt in enumerate(self._types):
            pid, pname = pt.get("id",0), pt.get("name","")
            tk.Label(frame, text=pname, font=FONTS["body"], bg="#FFFFFF").grid(row=i+1, column=0, sticky="w", padx=10, pady=3)
            v = tk.StringVar(value='production')
            vars_map[pid] = v
            rbf = tk.Frame(frame, bg="#FFFFFF")
            rbf.grid(row=i+1, column=1, padx=10, pady=3)
            tk.Radiobutton(rbf, text="生产", variable=v, value="production", font=FONTS["body"], bg="#FFFFFF").pack(side=tk.LEFT, padx=3)
            tk.Radiobutton(rbf, text="外协", variable=v, value="outsource", font=FONTS["body"], bg="#FFFFFF").pack(side=tk.LEFT, padx=3)
        btn_frame = tk.Frame(frame, bg="#FFFFFF")
        btn_frame.grid(row=len(self._types)+1, column=0, columnspan=2, pady=10)
        def do_save():
            changed = 0
            for pid, var in vars_map.items():
                if var.get() != 'production':
                    set_product_flow_type(pid, var.get())
                    changed += 1
            messagebox.showinfo("完成", "已更新 %d 项" % changed, parent=self.window)
            self.window.destroy()
        ttk.Button(btn_frame, text="保存", width=12, command=do_save, style="Accent.TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", width=10, command=self._on_cancel).pack(side=tk.LEFT, padx=5)
