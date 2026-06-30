# -*- coding: utf-8 -*-
"""
新建订单对话框（分组参数选择版 v2）
- 顶部：产品类型 + 模板工具
- 客户信息区
- 尺寸参数：点击添加按钮方式
- 材质参数区
- 表面处理区
- 备注区
- 底部：确认新建
"""
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from config import COLORS, FONTS, PRODUCT_TYPES
from utils.custom_types import get_product_types, add_product_type
from models.database import generate_order_no
from utils.order_templates import (
    get_common_fields, get_remark_fields,
    get_template_names, get_template, save_template,
    rename_template, delete_template,
    get_custom_params, get_custom_dim_params, add_custom_dim_param, remove_custom_dim_param,
    MATERIAL_OPTS, DIM_FIELDS, MATERIAL_FIELDS, SURFACE_FIELD, SURFACE_OPTS,
)


class NewOrderDialog(tk.Toplevel):
    def __init__(self, parent, on_save_callback, order=None):
        """
        新建/编辑订单对话框
        :param parent: 父窗口
        :param on_save_callback: 保存回调函数
        :param order: 订单数据（None=新建，非None=编辑）
        """
        super().__init__(parent)
        self.on_save_callback = on_save_callback
        self._order = order  # 编辑模式的订单数据

        self.title("编辑订单" if order else "新建订单")
        self.resizable(True, True)
        self.grab_set()
        self.transient(parent)

        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = 800, 750
        self.geometry(f"{w}x{h}+{sw//2-w//2}+{sh//2-h//2}")
        self.minsize(720, 600)

        # 如果是编辑模式，使用原有订单号
        self._order_no = order.get("order_no") if order else generate_order_no()
        self._pt_var = tk.StringVar(value=order.get("product_type", get_product_types()[0]) if order else (get_product_types()[0] if get_product_types() else ""))
        self._added_dim_params = []  # 已添加的尺寸参数列表
        self._added_mat_params = []  # 已添加的材质参数列表
        self._added_surface_params = []  # 已添加的表面处理参数列表
        self._custom_dim_params = []  # 自定义尺寸参数
        self._custom_mat_params = []  # 自定义材质参数
        self._custom_surface_params = []  # 自定义表面处理参数
        self._group_widgets = {}
        self._param_var_map = {}
        self._param_widget_map = {}
        self._dim_fields_by_key = {fd["key"]: fd for fd in DIM_FIELDS}
        self._mat_fields_by_key = {fd["key"]: fd for fd in MATERIAL_FIELDS}
        self._surface_fields_by_key = {fd["key"]: fd for fd in SURFACE_FIELD}

        self._build_ui()
        # 重建UI（会自动加载自定义尺寸参数）
        self._rebuild_content()

        # 如果是编辑模式，填充数据
        if order:
            self._load_order_data(order)

    # ═══════════════════════════════════════════════════════════
    # UI 骨架
    # ═══════════════════════════════════════════════════════════
    def _build_ui(self):
        self.configure(bg=COLORS["bg_main"])

        # 顶部工具栏
        top_bar = tk.Frame(self, bg="#FFFFFF", padx=10, pady=6)
        top_bar.pack(fill=tk.X, side=tk.TOP)

        tk.Label(top_bar, text="产品类型", font=FONTS["subtitle"],
                 bg="#FFFFFF", fg=COLORS["primary"]).pack(side=tk.LEFT, padx=(5, 5))
        self._pt_combo = ttk.Combobox(top_bar, textvariable=self._pt_var,
                                      values=get_product_types(), width=16,
                                      font=FONTS["body"], state="readonly")
        self._pt_combo.pack(side=tk.LEFT, padx=(0, 5))
        self._pt_combo.bind("<<ComboboxSelected>>", lambda e: self._rebuild_content())
        self._pt_combo.bind("<MouseWheel>", lambda e: "break")

        tk.Button(top_bar, text="➕", font=(FONTS["body"][0], 10), bd=1,
                  fg=COLORS["accent"], command=self._add_custom_product_type
                 ).pack(side=tk.LEFT, padx=(0, 5))

        tk.Label(top_bar, text="│", font=(FONTS["body"][0], 12),
                 bg="#FFFFFF", fg="#CCCCCC").pack(side=tk.LEFT, padx=8)

        ttk.Button(top_bar, text="📥 加载模板", command=self._load_template).pack(side=tk.LEFT, padx=3)
        ttk.Button(top_bar, text="💾 保存模板", command=self._save_template).pack(side=tk.LEFT, padx=3)
        ttk.Button(top_bar, text="📂 管理模板", command=self._manage_templates).pack(side=tk.LEFT, padx=3)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X)

        # 订单号栏
        no_bar = tk.Frame(self, bg="#F7F7FA", padx=12, pady=5)
        no_bar.pack(fill=tk.X)
        tk.Label(no_bar, text="订单号（自动生成）", font=FONTS["body"],
                 bg="#F7F7FA", width=14, anchor="e").pack(side=tk.LEFT)
        tk.Label(no_bar, text=self._order_no, font=(FONTS["body"][0], 11, "bold"),
                 bg="#F7F7FA", fg=COLORS["accent"]).pack(side=tk.LEFT, padx=8)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X)

        # 可滚动区域
        canvas_frame = tk.Frame(self, bg=COLORS["bg_main"])
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        self._canvas = tk.Canvas(canvas_frame, bg=COLORS["bg_main"], highlightthickness=0)
        vscroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=vscroll.set)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vscroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._scroll_frame = tk.Frame(self._canvas, bg=COLORS["bg_main"])
        self._canvas_window = self._canvas.create_window((0, 0), window=self._scroll_frame, anchor="nw")

        self._scroll_frame.bind("<Configure>", self._on_frame_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X)

        # 底部按钮
        btn_row = tk.Frame(self, bg="#FFFFFF", pady=8)
        btn_row.pack(fill=tk.X)
        ttk.Button(btn_row, text="取  消", command=self.destroy, width=12).pack(side=tk.RIGHT, padx=10)
        ttk.Button(btn_row, text="保存修改" if self._order else "确认新建", command=self._on_confirm,
                   style="Accent.TButton", width=12).pack(side=tk.RIGHT, padx=5)

    # ═══════════════════════════════════════════════════════════
    # 编辑模式：填充订单数据
    # ═══════════════════════════════════════════════════════════
    def _load_order_data(self, order):
        """填充订单数据到表单（编辑模式）"""
        # 展开 extra_params
        extra = order.get("extra_params") or {}
        if isinstance(extra, str):
            try:
                import json
                extra = json.loads(extra)
            except:
                extra = {}

        # 使用 _param_var_map 填充所有字段
        for key, var in self._param_var_map.items():
            val = order.get(key) or extra.get(key, "")
            if val:
                var.set(val)
                # 同时恢复输入框前景色（如果是占位符）
                widget = self._param_widget_map.get(key)
                if widget and hasattr(widget, "config"):
                    try:
                        widget.config(foreground="#000000")
                    except:
                        pass

        # 填充 Text 组件（备注等）
        for key, widget in self._param_widget_map.items():
            if isinstance(widget, tk.Text):
                val = order.get(key) or extra.get(key, "")
                if val:
                    widget.delete("1.0", tk.END)
                    widget.insert("1.0", val)
                    try:
                        widget.config(foreground="#000000")
                    except:
                        pass

        # 填充尺寸参数（从 extra_params 中找）
        dim_keys = {fd["key"] for fd in DIM_FIELDS}
        for key in extra:
            if key in dim_keys and key not in self._added_dim_params:
                val = extra.get(key, "")
                if val:
                    self._added_dim_params.append(key)
                    self._add_dim_row(key)
                    if key in self._param_var_map:
                        self._param_var_map[key].set(val)

        # 填充材质参数
        mat_keys = {fd["key"] for fd in MATERIAL_FIELDS}
        for key in extra:
            if key in mat_keys and key not in self._added_mat_params:
                val = extra.get(key, "")
                if val:
                    self._added_mat_params.append(key)
                    self._add_mat_row(key)
                    if key in self._param_var_map:
                        self._param_var_map[key].set(val)

        # 填充表面处理参数
        surface_keys = {fd["key"] for fd in SURFACE_FIELD}
        for key in extra:
            if key in surface_keys and key not in self._added_surface_params:
                val = extra.get(key, "")
                if val:
                    self._added_surface_params.append(key)
                    self._add_surface_row(key)
                    if key in self._param_var_map:
                        self._param_var_map[key].set(val)

        # 隐藏空提示
        self._dim_empty_lbl.pack_forget()
        self._mat_empty_lbl.pack_forget()

    # ═══════════════════════════════════════════════════════════
    # 内容区构建
    # ═══════════════════════════════════════════════════════════
    def _rebuild_content(self):
        for w in self._scroll_frame.winfo_children():
            w.destroy()
        self._group_widgets.clear()
        self._param_var_map.clear()
        self._param_widget_map.clear()
        self._added_dim_params = []
        self._added_mat_params = []

        # 客户信息
        self._build_section(self._scroll_frame, "👤 客户信息",
                             self._build_customer_fields)

        # 尺寸参数（点击添加方式）
        self._build_dim_section(self._scroll_frame)

        # 材质参数（点击添加方式）
        self._build_mat_section(self._scroll_frame)

        # 表面处理（直接显示 + 自定义按钮）
        self._build_surface_section(self._scroll_frame)

        # 备注
        self._build_section(self._scroll_frame, "📝 备注",
                             self._build_remark_fields)

        # 重建后，重新加载已保存的自定义尺寸参数（永久录入）
        for p in get_custom_dim_params():
            label = p["label"]
            if label not in self._added_dim_params:
                self._added_dim_params.append(label)
                self._add_custom_dim_row(label)
        if self._added_dim_params:
            self._dim_empty_lbl.pack_forget()

        self._scroll_frame.update_idletasks()
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _build_section(self, parent, title, builder_func):
        container = tk.Frame(parent, bg=COLORS["bg_main"])
        container.pack(fill=tk.X, padx=4, pady=(6, 0))

        header = tk.Frame(container, bg="#FFFFFF", relief=tk.RAISED, borderwidth=1)
        header.pack(fill=tk.X)
        lbl = tk.Label(header, text=title, font=FONTS["subtitle"],
                       bg="#FFFFFF", fg=COLORS["primary"], anchor="w", padx=10, pady=7)
        lbl.pack(fill=tk.X)

        content = tk.Frame(container, bg="#FFFFFF", padx=10, pady=6)
        content.pack(fill=tk.X, pady=(0, 4))
        builder_func(content)

    # ── 尺寸参数：点击添加方式 ─────────────────────────────────
    def _build_dim_section(self, parent):
        container = tk.Frame(parent, bg=COLORS["bg_main"])
        container.pack(fill=tk.X, padx=4, pady=(6, 0))

        header = tk.Frame(container, bg="#FFFFFF", relief=tk.RAISED, borderwidth=1)
        header.pack(fill=tk.X)
        lbl = tk.Label(header, text="📏 尺寸参数", font=FONTS["subtitle"],
                       bg="#FFFFFF", fg=COLORS["primary"], anchor="w", padx=10, pady=7)
        lbl.pack(side=tk.LEFT)


        btn_frame = tk.Frame(header, bg="#FFFFFF")
        btn_frame.pack(side=tk.RIGHT, padx=10, pady=5)
        
        # 尺寸参数排序按钮组
        tk.Button(btn_frame, text="⏮️", font=(FONTS["body"][0], 9), bd=1, cursor="hand2",
                 command=lambda: self._move_dim_param(-999)  # 置顶
                 ).pack(side=tk.LEFT, padx=(0, 1))
        tk.Button(btn_frame, text="⬆️", font=(FONTS["body"][0], 9), bd=1, cursor="hand2",
                 command=lambda: self._move_dim_param(-1)
                 ).pack(side=tk.LEFT, padx=(0, 1))
        tk.Button(btn_frame, text="⬇️", font=(FONTS["body"][0], 9), bd=1, cursor="hand2",
                 command=lambda: self._move_dim_param(1)
                 ).pack(side=tk.LEFT, padx=(0, 1))
        tk.Button(btn_frame, text="⏭️", font=(FONTS["body"][0], 9), bd=1, cursor="hand2",
                 command=lambda: self._move_dim_param(999)  # 置底
                 ).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(btn_frame, text="✏️ 自定义", font=(FONTS["body"][0], 9), bd=1,
                 fg="#888888", command=self._add_custom_dim
                 ).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(btn_frame, text="➕ 添加", font=(FONTS["body"][0], 9), bd=1,
                 fg=COLORS["accent"], command=self._show_dim_picker
                 ).pack(side=tk.LEFT)

        # 尺寸参数列表区域
        self._dim_content = tk.Frame(container, bg="#FFFFFF", padx=10, pady=6)
        self._dim_content.pack(fill=tk.X, pady=(0, 4))

        # 空提示
        self._dim_empty_lbl = tk.Label(self._dim_content,
            text="暂无尺寸参数，点击上方「添加」按钮添加",
            font=(FONTS["body"][0], 10), fg="#999999", bg="#FFFFFF", pady=10)
        self._dim_empty_lbl.pack()

    # ── 材质参数：点击添加方式 ─────────────────────────────────
    def _build_mat_section(self, parent):
        container = tk.Frame(parent, bg=COLORS["bg_main"])
        container.pack(fill=tk.X, padx=4, pady=(6, 0))

        header = tk.Frame(container, bg="#FFFFFF", relief=tk.RAISED, borderwidth=1)
        header.pack(fill=tk.X)
        lbl = tk.Label(header, text="🔩 材质参数", font=FONTS["subtitle"],
                       bg="#FFFFFF", fg=COLORS["primary"], anchor="w", padx=10, pady=7)
        lbl.pack(side=tk.LEFT)

        btn_frame = tk.Frame(header, bg="#FFFFFF")
        btn_frame.pack(side=tk.RIGHT, padx=10, pady=5)
        
        # 材质参数排序按钮组
        tk.Button(btn_frame, text="⏮️", font=(FONTS["body"][0], 9), bd=1, cursor="hand2",
                 command=lambda: self._move_mat_param(-999)  # 置顶
                 ).pack(side=tk.LEFT, padx=(0, 1))
        tk.Button(btn_frame, text="⬆️", font=(FONTS["body"][0], 9), bd=1, cursor="hand2",
                 command=lambda: self._move_mat_param(-1)
                 ).pack(side=tk.LEFT, padx=(0, 1))
        tk.Button(btn_frame, text="⬇️", font=(FONTS["body"][0], 9), bd=1, cursor="hand2",
                 command=lambda: self._move_mat_param(1)
                 ).pack(side=tk.LEFT, padx=(0, 1))
        tk.Button(btn_frame, text="⏭️", font=(FONTS["body"][0], 9), bd=1, cursor="hand2",
                 command=lambda: self._move_mat_param(999)  # 置底
                 ).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(btn_frame, text="✏️ 自定义", font=(FONTS["body"][0], 9), bd=1,
                 fg="#888888", command=self._add_custom_mat
                 ).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(btn_frame, text="➕ 添加", font=(FONTS["body"][0], 9), bd=1,
                 fg=COLORS["accent"], command=self._show_mat_picker
                 ).pack(side=tk.LEFT)

        # 材质参数列表区域
        self._mat_content = tk.Frame(container, bg="#FFFFFF", padx=10, pady=6)
        self._mat_content.pack(fill=tk.X, pady=(0, 4))

        # 空提示
        self._mat_empty_lbl = tk.Label(self._mat_content,
            text="暂无材质参数，点击上方「添加」按钮添加",
            font=(FONTS["body"][0], 10), fg="#999999", bg="#FFFFFF", pady=10)
        self._mat_empty_lbl.pack()

    # ── 表面处理：直接显示 + 自定义 ───────────────────────────────
    def _build_surface_section(self, parent):
        container = tk.Frame(parent, bg=COLORS["bg_main"])
        container.pack(fill=tk.X, padx=4, pady=(6, 0))

        header = tk.Frame(container, bg="#FFFFFF", relief=tk.RAISED, borderwidth=1)
        header.pack(fill=tk.X)
        lbl = tk.Label(header, text="✨ 表面处理", font=FONTS["subtitle"],
                       bg="#FFFFFF", fg=COLORS["primary"], anchor="w", padx=10, pady=7)
        lbl.pack(side=tk.LEFT)

        # 自定义按钮
        tk.Button(header, text="✏️ 自定义", font=(FONTS["body"][0], 9), bd=1,
                  fg="#888888", command=self._add_custom_surface
                 ).pack(side=tk.RIGHT, padx=10, pady=5)

        # 表面处理内容区域 - 分两部分
        # 1. 预设字段区域（使用 grid）
        content = tk.Frame(container, bg="#FFFFFF", padx=10, pady=6)
        content.pack(fill=tk.X, pady=(0, 4))
        self._surface_content = content
        self._build_direct_fields(content, SURFACE_FIELD)

        # 2. 动态添加字段区域（使用 pack）
        self._surface_dynamic = tk.Frame(container, bg="#FFFFFF", padx=10)
        self._surface_dynamic.pack(fill=tk.X, pady=(0, 4))

    def _show_mat_picker(self):
        """弹出材质参数选择器"""
        unadded = [fd for fd in MATERIAL_FIELDS if fd["key"] not in self._added_mat_params]
        if not unadded:
            messagebox.showinfo("提示", "所有材质参数已添加完毕", parent=self)
            return

        win = tk.Toplevel(self)
        win.title("选择材质参数")
        win.grab_set()
        win.transient(self)
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry(f"380x480+{sw//2-190}+{sh//2-240}")
        win.resizable(False, True)

        tk.Label(win, text="选择要添加的材质参数（可多选）：", font=FONTS["body"],
                 bg="#FFFFFF").pack(anchor="w", padx=15, pady=(12, 8))

        # 主容器 - 分为列表区和按钮区
        main_container = tk.Frame(win, bg="#FFFFFF")
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        list_frame = tk.Frame(main_container, bg="#FFFFFF")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        canvas_c = tk.Canvas(list_frame, bg="#FFFFFF", highlightthickness=0)
        scroll_y = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=canvas_c.yview)
        canvas_c.configure(yscrollcommand=scroll_y.set)
        canvas_c.pack(side=tk.LEFT, fill=tk.BOTH)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        canvas_c.focus_set()

        inner = tk.Frame(canvas_c, bg="#FFFFFF", width=320)
        canvas_c_window = canvas_c.create_window((0, 0), window=inner, anchor="nw")

        def on_inner_config(e):
            canvas_c.configure(scrollregion=(0, 0, 320, inner.winfo_reqheight()))
        inner.bind("<Configure>", on_inner_config)

        def on_canvas_config(e):
            canvas_c.itemconfig(canvas_c_window, width=e.width)

        def on_mousewheel(event):
            try:
                canvas_c.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except:
                pass
            return "break"

        def on_button4(e):
            try:
                canvas_c.yview_scroll(-3, "units")
            except:
                pass
            return "break"

        def on_button5(e):
            try:
                canvas_c.yview_scroll(3, "units")
            except:
                pass
            return "break"

        canvas_c.bind("<Configure>", on_canvas_config)
        canvas_c.bind("<MouseWheel>", on_mousewheel)
        canvas_c.bind("<Button-4>", on_button4)
        canvas_c.bind("<Button-5>", on_button5)
        inner.bind("<MouseWheel>", on_mousewheel)
        inner.bind("<Button-4>", on_button4)
        inner.bind("<Button-5>", on_button5)

        self._mat_check_vars = {}
        row = 0
        for fd in unadded:
            var = tk.BooleanVar(value=False)
            self._mat_check_vars[fd["key"]] = var
            cb = tk.Checkbutton(inner, variable=var, text=fd["label"],
                                font=FONTS["body"], bg="#FFFFFF", anchor="w",
                                padx=10, pady=3, cursor="hand2")
            cb.grid(row=row, column=0, columnspan=2, sticky="w")
            row += 1

        # 全选/全不选
        sel_frame = tk.Frame(inner, bg="#FFFFFF", pady=4)
        sel_frame.grid(row=row, column=0, columnspan=2, sticky="w", pady=(6, 0))
        tk.Button(sel_frame, text="全选", font=(FONTS["body"][0], 9), bd=1,
                 command=lambda: [v.set(True) for v in self._mat_check_vars.values()]
                ).pack(side=tk.LEFT, padx=(5, 3))
        tk.Button(sel_frame, text="全不选", font=(FONTS["body"][0], 9), bd=1,
                 command=lambda: [v.set(False) for v in self._mat_check_vars.values()]
                ).pack(side=tk.LEFT, padx=3)

        def do_add():
            selected = [k for k, v in self._mat_check_vars.items() if v.get()]
            if not selected:
                messagebox.showwarning("提示", "请至少选择一项", parent=win)
                return
            for key in selected:
                if key not in self._added_mat_params:
                    self._added_mat_params.append(key)
                    self._add_mat_row(key)
            self._mat_empty_lbl.pack_forget()
            win.destroy()

        # 按钮区域 - 放在 main_container 中
        btn_row = tk.Frame(main_container, bg="#FFFFFF", height=50)
        btn_row.pack(fill=tk.X, pady=(8, 0))
        btn_row.pack_propagate(False)  # 固定高度
        ttk.Button(btn_row, text="取消", command=win.destroy, width=10).pack(side=tk.LEFT, padx=10, pady=10)
        ttk.Button(btn_row, text="添加", command=do_add, width=10,
                   style="Accent.TButton").pack(side=tk.LEFT, padx=5, pady=10)

    def _add_mat_row(self, key):
        """动态添加一行材质参数"""
        fd = self._mat_fields_by_key.get(key)
        if not fd:
            return

        inner = tk.Frame(self._mat_content, bg="#FFFFFF", relief=tk.SOLID, borderwidth=1)
        inner.pack(fill=tk.X, pady=3)
        inner._key = key

        # 点击事件绑定到所有子组件
        def on_mat_click(e):
            self._selected_mat_key = key  # 更新实例变量
            for w in self._mat_content.winfo_children():
                if hasattr(w, '_key'):
                    if w._key == key:
                        w.config(bg="#E8F4FD", relief=tk.GROOVE, borderwidth=2)
                    else:
                        w.config(bg="#FFFFFF", relief=tk.SOLID, borderwidth=1)

        inner.bind("<Button-1>", on_mat_click)

        lbl = tk.Label(inner, text=fd["label"], font=FONTS["body"],
                       bg="#FFFFFF", width=14, anchor="e", pady=4)
        lbl.pack(side=tk.LEFT, padx=(5, 5))
        lbl.bind("<Button-1>", on_mat_click)

        opts = fd.get("options", MATERIAL_OPTS)
        var = tk.StringVar(value=opts[0] if opts else "")
        w = ttk.Combobox(inner, textvariable=var, values=opts,
                        font=FONTS["body"], width=22, state="readonly")
        w.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        w.bind("<Button-1>", on_mat_click)
        # 阻止滚轮改变下拉框选项
        w.bind("<MouseWheel>", lambda e: "break")
        w.bind("<Button-4>", lambda e: "break")
        w.bind("<Button-5>", lambda e: "break")
        self._param_var_map[key] = var
        self._param_widget_map[key] = w

        tk.Button(inner, text="✕", font=(FONTS["body"][0], 9), bd=1,
                 fg="#FF6666", command=lambda: self._remove_mat_row(key, inner),
                 cursor="hand2"
                 ).pack(side=tk.LEFT, padx=(0, 5))

    def _remove_mat_row(self, key, row_widget):
        """删除一行材质参数"""
        if key in self._added_mat_params:
            self._added_mat_params.remove(key)
        if key in self._param_var_map:
            del self._param_var_map[key]
        if key in self._param_widget_map:
            del self._param_widget_map[key]
        row_widget.destroy()
        if not self._added_mat_params:
            self._mat_empty_lbl.pack()

    # ── 自定义参数添加 ──────────────────────────────────────────────
    def _add_custom_dim(self):
        """添加自定义尺寸参数"""
        # 预设的尺寸参数
        preset_sizes = [
            "总宽度", "带宽", "网宽", "有效宽度",
            "总长度", "带长", "网长",
            "目数", "丝径", "螺距", "节距",
            "边高", "边宽", "翻边高度",
            "转弯半径", "内半径", "外半径",
            "链条节距", "链条宽度", "销轴直径",
            "穿杆直径", "穿杆间距",
            "开孔率", "透气率",
        ]

        win = tk.Toplevel(self)
        win.title("添加自定义尺寸参数")
        win.grab_set()
        win.transient(self)
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry(f"320x200+{sw//2-160}+{sh//2-100}")
        win.resizable(False, False)

        tk.Label(win, text="选择或输入尺寸参数：", font=FONTS["body"],
                bg="#FFFFFF").pack(anchor="w", padx=15, pady=(15, 5))

        # 预设下拉框
        combo = ttk.Combobox(win, font=FONTS["body"], values=preset_sizes,
                            state="readonly", width=28)
        combo.pack(padx=15, pady=5)
        combo.current(0)
        combo.bind("<MouseWheel>", lambda e: "break")

        tk.Label(win, text="或输入自定义名称：", font=FONTS["body"],
                bg="#FFFFFF").pack(anchor="w", padx=15, pady=(10, 5))

        entry = ttk.Entry(win, font=FONTS["body"], width=30)
        entry.pack(padx=15, pady=5)

        def do_add():
            # 优先使用自定义输入
            name = entry.get().strip()
            if not name:
                name = combo.get()
            if not name:
                messagebox.showwarning("提示", "请选择或输入参数名称", parent=win)
                return
            # 永久保存到文件
            success, msg = add_custom_dim_param(name)
            if not success:
                # 已存在也允许添加
                pass
            win.name = name
            win.destroy()

        entry.bind("<Return>", lambda e: entry.focus())

        btn_row = tk.Frame(win, bg="#FFFFFF", pady=10)
        btn_row.pack()
        ttk.Button(btn_row, text="取消", command=win.destroy, width=10).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_row, text="添加", command=do_add, width=10,
                   style="Accent.TButton").pack(side=tk.LEFT, padx=5)

        win.wait_window()
        name = getattr(win, "name", None)
        if name:
            if name not in self._added_dim_params:
                self._added_dim_params.append(name)
                self._add_custom_dim_row(name)
                self._dim_empty_lbl.pack_forget()

    def _add_custom_mat(self):
        """添加自定义材质参数"""
        key = self._ask_custom_param_name("单位参数")
        if key:
            if key not in self._added_mat_params:
                self._added_mat_params.append(key)
                self._add_custom_mat_row(key)
                self._mat_empty_lbl.pack_forget()

    def _add_custom_surface(self):
        """添加自定义表面处理参数"""
        key = self._ask_custom_param_name("表面处理参数")
        if key:
            if key not in self._added_surface_params:
                self._added_surface_params.append(key)
                self._add_custom_surface_row(key)

    def _ask_custom_param_name(self, param_type):
        """弹出对话框让用户输入自定义参数名称"""
        win = tk.Toplevel(self)
        win.title(f"添加自定义{param_type}")
        win.grab_set()
        win.transient(self)
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry(f"300x130+{sw//2-150}+{sh//2-65}")
        win.resizable(False, False)

        tk.Label(win, text=f"请输入自定义{param_type}名称：",
                 font=FONTS["body"], bg="#FFFFFF").pack(anchor="w", padx=15, pady=(15, 5))

        entry = ttk.Entry(win, font=FONTS["body"], width=30)
        entry.pack(padx=15, pady=5)
        entry.focus()

        def do_add():
            name = entry.get().strip()
            if not name:
                messagebox.showwarning("提示", "请输入参数名称", parent=win)
                return
            win.name = name
            win.destroy()

        def on_enter(e):
            do_add()

        entry.bind("<Return>", on_enter)

        btn_row = tk.Frame(win, bg="#FFFFFF", pady=10)
        btn_row.pack()
        ttk.Button(btn_row, text="取消", command=win.destroy, width=10).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_row, text="添加", command=do_add, width=10,
                   style="Accent.TButton").pack(side=tk.LEFT, padx=5)

        win.wait_window()
        return getattr(win, "name", None)

    def _add_custom_dim_row(self, key):
        """添加自定义尺寸参数行"""
        inner = tk.Frame(self._dim_content, bg="#FFFFFF", relief=tk.SOLID, borderwidth=1)
        inner.pack(fill=tk.X, pady=3)
        inner._key = key

        def on_dim_click(e):
            # 更新实例变量
            self._selected_dim_key = key
            # 更新视觉样式
            for w in self._dim_content.winfo_children():
                if hasattr(w, '_key'):
                    if w._key == key:
                        w.config(bg="#E8F4FD", relief=tk.GROOVE, borderwidth=2)
                    else:
                        w.config(bg="#FFFFFF", relief=tk.SOLID, borderwidth=1)

        inner.bind("<Button-1>", on_dim_click)

        lbl = tk.Label(inner, text=key, font=FONTS["body"],
                       bg="#FFFFFF", width=18, anchor="e", pady=4)
        lbl.pack(side=tk.LEFT, padx=(5, 5))
        lbl.bind("<Button-1>", on_dim_click)

        var = tk.StringVar()
        w = ttk.Entry(inner, textvariable=var, font=FONTS["body"], width=20)
        w.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        w.bind("<Button-1>", on_dim_click)
        self._param_var_map[key] = var
        self._param_widget_map[key] = w

        # mm 单位标签
        unit_lbl = tk.Label(inner, text="mm", font=(FONTS["body"][0], 10),
                           bg="#FFFFFF", fg="#888888", width=4, anchor="w", pady=4)
        unit_lbl.pack(side=tk.LEFT, padx=(0, 5))

        tk.Button(inner, text="✕", font=(FONTS["body"][0], 9), bd=1,
                 fg="#FF6666", command=lambda: self._remove_custom_dim_row(key, inner),
                 cursor="hand2").pack(side=tk.LEFT, padx=(0, 5))

    def _remove_custom_dim_row(self, key, row_widget):
        """删除自定义尺寸参数行"""
        if key in self._added_dim_params:
            self._added_dim_params.remove(key)
        if key in self._param_var_map:
            del self._param_var_map[key]
        if key in self._param_widget_map:
            del self._param_widget_map[key]
        # 同步删除文件记录
        remove_custom_dim_param(key)
        row_widget.destroy()
        if not self._added_dim_params:
            self._dim_empty_lbl.pack()

    def _add_custom_mat_row(self, key):
        """添加自定义材质参数行"""
        inner = tk.Frame(self._mat_content, bg="#FFFFFF", relief=tk.SOLID, borderwidth=1)
        inner.pack(fill=tk.X, pady=3)
        inner._key = key

        def on_mat_click(e):
            # 更新实例变量
            self._selected_mat_key = key
            # 更新视觉样式
            for w in self._mat_content.winfo_children():
                if hasattr(w, '_key'):
                    if w._key == key:
                        w.config(bg="#E8F4FD", relief=tk.GROOVE, borderwidth=2)
                    else:
                        w.config(bg="#FFFFFF", relief=tk.SOLID, borderwidth=1)

        inner.bind("<Button-1>", on_mat_click)

        lbl = tk.Label(inner, text=key, font=FONTS["body"],
                       bg="#FFFFFF", width=14, anchor="e", pady=4)
        lbl.pack(side=tk.LEFT, padx=(5, 5))
        lbl.bind("<Button-1>", on_mat_click)

        var = tk.StringVar()
        w = ttk.Entry(inner, textvariable=var, font=FONTS["body"], width=22)
        w.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        w.bind("<Button-1>", on_mat_click)
        self._param_var_map[key] = var
        self._param_widget_map[key] = w

        tk.Button(inner, text="✕", font=(FONTS["body"][0], 9), bd=1,
                 fg="#FF6666", command=lambda: self._remove_custom_mat_row(key, inner),
                 cursor="hand2").pack(side=tk.LEFT, padx=(0, 5))

    def _remove_custom_mat_row(self, key, row_widget):
        """删除自定义材质参数行"""
        if key in self._added_mat_params:
            self._added_mat_params.remove(key)
        if key in self._param_var_map:
            del self._param_var_map[key]
        if key in self._param_widget_map:
            del self._param_widget_map[key]
        row_widget.destroy()
        if not self._added_mat_params:
            self._mat_empty_lbl.pack()

    def _add_custom_surface_row(self, key):
        """添加自定义表面处理参数行"""
        inner = tk.Frame(self._surface_dynamic, bg="#FFFFFF")
        inner.pack(fill=tk.X, pady=3)

        lbl = tk.Label(inner, text=key, font=FONTS["body"],
                       bg="#FFFFFF", width=14, anchor="e", pady=4)
        lbl.pack(side=tk.LEFT, padx=(5, 5))

        var = tk.StringVar()
        w = ttk.Entry(inner, textvariable=var, font=FONTS["body"], width=22)
        w.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self._param_var_map[key] = var
        self._param_widget_map[key] = w

        tk.Button(inner, text="✕", font=(FONTS["body"][0], 9), bd=1,
                  fg="#FF6666", command=lambda: self._remove_custom_surface_row(key, inner)
                 ).pack(side=tk.LEFT, padx=(0, 5))

    def _remove_custom_surface_row(self, key, row_widget):
        """删除自定义表面处理参数行"""
        if key in self._added_surface_params:
            self._added_surface_params.remove(key)
        if key in self._param_var_map:
            del self._param_var_map[key]
        if key in self._param_widget_map:
            del self._param_widget_map[key]
        row_widget.destroy()

    def _add_surface_row(self, key):
        """动态添加一行预设表面处理参数"""
        fd = self._surface_fields_by_key.get(key)
        if not fd:
            return

        inner = tk.Frame(self._surface_dynamic, bg="#FFFFFF")
        inner.pack(fill=tk.X, pady=3)

        lbl = tk.Label(inner, text=fd["label"], font=FONTS["body"],
                       bg="#FFFFFF", width=14, anchor="e", pady=4)
        lbl.pack(side=tk.LEFT, padx=(5, 5))

        if fd.get("type") == "combo":
            opts = fd.get("options", SURFACE_OPTS)
            var = tk.StringVar(value=opts[0] if opts else "")
            w = ttk.Combobox(inner, textvariable=var, values=opts,
                            font=FONTS["body"], width=22, state="readonly")
            w.bind("<MouseWheel>", lambda e: "break")
        else:
            var = tk.StringVar()
            w = ttk.Entry(inner, textvariable=var, font=FONTS["body"], width=22)
        w.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self._param_var_map[key] = var
        self._param_widget_map[key] = w

        tk.Button(inner, text="✕", font=(FONTS["body"][0], 9), bd=1,
                 fg="#FF6666", command=lambda: self._remove_surface_row(key, inner)
                 ).pack(side=tk.LEFT, padx=(0, 5))

    def _remove_surface_row(self, key, row_widget):
        """删除预设表面处理参数行"""
        if key in self._added_surface_params:
            self._added_surface_params.remove(key)
        if key in self._param_var_map:
            del self._param_var_map[key]
        if key in self._param_widget_map:
            del self._param_widget_map[key]
        row_widget.destroy()

    def _show_dim_picker(self):
        """弹出尺寸参数选择器"""
        # 找出未添加的参数
        unadded = [fd for fd in DIM_FIELDS if fd["key"] not in self._added_dim_params]
        if not unadded:
            messagebox.showinfo("提示", "所有尺寸参数已添加完毕", parent=self)
            return

        win = tk.Toplevel(self)
        win.title("选择尺寸参数")
        win.grab_set()
        win.focus_force()  # 强制获取焦点
        win.transient(self)
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry(f"420x520+{sw//2-210}+{sh//2-260}")
        win.resizable(True, True)  # 可自由调节大小

        tk.Label(win, text="选择要添加的尺寸参数（可多选）：", font=FONTS["body"],
                 bg="#FFFFFF").pack(anchor="w", padx=15, pady=(12, 8))

        # 按子分组显示
        groups = {}
        for fd in unadded:
            g = fd.get("group", "其他")
            groups.setdefault(g, []).append(fd)

        # 主容器 - 分为列表区和按钮区
        main_container = tk.Frame(win, bg="#FFFFFF")
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        list_frame = tk.Frame(main_container, bg="#FFFFFF")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        # 使用 Canvas + Checkbutton 列表，支持滚动
        canvas_c = tk.Canvas(list_frame, bg="#FFFFFF", highlightthickness=0)
        scroll_y = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=canvas_c.yview)
        canvas_c.configure(yscrollcommand=scroll_y.set)
        canvas_c.pack(side=tk.LEFT, fill=tk.BOTH)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        canvas_c.focus_set()  # Canvas 获得焦点，滚轮只在这里响应

        # inner 需要设置背景色和有大小才能被 Canvas 正确包裹
        inner = tk.Frame(canvas_c, bg="#FFFFFF", width=360)
        canvas_c_window = canvas_c.create_window((0, 0), window=inner, anchor="nw")

        def on_inner_config(e):
            # 设置滚动区域
            canvas_c.configure(scrollregion=(0, 0, 360, inner.winfo_reqheight()))
        inner.bind("<Configure>", on_inner_config)

        def on_canvas_config(e):
            canvas_c.itemconfig(canvas_c_window, width=e.width)

        def on_mousewheel(event):
            canvas_c.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"  # 阻止事件冒泡

        def on_button4(e):
            canvas_c.yview_scroll(-3, "units")
            return "break"

        def on_button5(e):
            canvas_c.yview_scroll(3, "units")
            return "break"

        canvas_c.bind("<Configure>", on_canvas_config)
        canvas_c.bind("<MouseWheel>", on_mousewheel)
        # 支持 Linux 滚轮
        canvas_c.bind("<Button-4>", on_button4)
        canvas_c.bind("<Button-5>", on_button5)
        # inner 也要响应滚轮
        inner.bind("<MouseWheel>", on_mousewheel)
        inner.bind("<Button-4>", on_button4)
        inner.bind("<Button-5>", on_button5)

        self._dim_check_vars = {}
        row = 0
        for gname, fields in sorted(groups.items()):
            tk.Label(inner, text=f"── {gname} ──", font=(FONTS["body"][0], 9, "bold"),
                     bg="#F0F0F5", fg=COLORS["primary"], anchor="w",
                     padx=8, pady=4).grid(row=row, column=0, columnspan=2, sticky="ew", pady=(6, 2))
            row += 1
            for fd in fields:
                var = tk.BooleanVar(value=False)
                self._dim_check_vars[fd["key"]] = var
                cb = tk.Checkbutton(inner, variable=var, text=fd["label"],
                                    font=FONTS["body"], bg="#FFFFFF", anchor="w",
                                    padx=10, pady=2)
                cb.grid(row=row, column=0, columnspan=2, sticky="w")
                row += 1

        # 全选/全不选
        sel_frame = tk.Frame(inner, bg="#FFFFFF", pady=4)
        sel_frame.grid(row=row, column=0, columnspan=2, sticky="w", pady=(6, 0))
        tk.Button(sel_frame, text="全选", font=(FONTS["body"][0], 9), bd=1,
                  command=lambda: [v.set(True) for v in self._dim_check_vars.values()]
                 ).pack(side=tk.LEFT, padx=(5, 3))
        tk.Button(sel_frame, text="全不选", font=(FONTS["body"][0], 9), bd=1,
                  command=lambda: [v.set(False) for v in self._dim_check_vars.values()]
                 ).pack(side=tk.LEFT, padx=3)
        row += 1

        def do_add():
            selected = [k for k, v in self._dim_check_vars.items() if v.get()]
            if not selected:
                messagebox.showwarning("提示", "请至少选择一项", parent=win)
                return
            for key in selected:
                if key not in self._added_dim_params:
                    self._added_dim_params.append(key)
                    self._add_dim_row(key)
            self._dim_empty_lbl.pack_forget()
            win.destroy()

        # 按钮区域 - 放在 main_container 中
        btn_row = tk.Frame(main_container, bg="#FFFFFF", height=50)
        btn_row.pack(fill=tk.X, pady=(8, 0))
        btn_row.pack_propagate(False)  # 固定高度
        ttk.Button(btn_row, text="取消", command=win.destroy, width=10).pack(side=tk.LEFT, padx=10, pady=10)
        ttk.Button(btn_row, text="添加", command=do_add, width=10,
                   style="Accent.TButton").pack(side=tk.LEFT, padx=5, pady=10)


    def _move_dim_param(self, direction):
        """移动尺寸参数顺序
        direction: -1=上移, 1=下移, -999=置顶, 999=置底
        """
        # 使用 pack_slaves() 获取当前 pack 顺序的子元素
        try:
            children = [w for w in self._dim_content.pack_slaves() if hasattr(w, '_key')]
        except:
            return
        
        if len(children) < 2:
            return
        
        # 使用实例变量追踪选中的 key
        selected_key = getattr(self, '_selected_dim_key', None)
        
        # 找到选中项在 children 中的位置
        selected_idx = -1
        for i, w in enumerate(children):
            if hasattr(w, '_key') and w._key == selected_key:
                selected_idx = i
                break
        
        if selected_idx < 0:
            # 没有选中时，选中第一行
            if children:
                self._selected_dim_key = children[0]._key
                children[0].config(bg="#E8F4FD", relief=tk.GROOVE, borderwidth=2)
            return
        
        # 计算目标位置
        if direction == -999:  # 置顶
            new_idx = 0
        elif direction == 999:  # 置底
            new_idx = len(children) - 1
        else:
            new_idx = selected_idx + direction
        
        if new_idx < 0:
            new_idx = 0
        if new_idx >= len(children):
            new_idx = len(children) - 1
        
        if new_idx == selected_idx:
            return
        
        # 从列表中取出选中项，插入到目标位置
        children.insert(new_idx, children.pop(selected_idx))
        
        # 重新 pack（先清空再按新顺序）
        for w in self._dim_content.pack_slaves():
            try:
                w.pack_forget()
            except:
                pass
        for w in children:
            try:
                w.pack(fill=tk.X, pady=3)
            except:
                pass
        
        # 恢复选中状态（使用实例变量）
        for w in children:
            if hasattr(w, '_key') and w._key == selected_key:
                w.config(bg="#E8F4FD", relief=tk.GROOVE, borderwidth=2)
                break

    def _move_mat_param(self, direction):
        """移动材质参数顺序
        direction: -1=上移, 1=下移, -999=置顶, 999=置底
        """
        # 使用 pack_slaves() 获取当前 pack 顺序的子元素
        try:
            children = [w for w in self._mat_content.pack_slaves() if hasattr(w, '_key')]
        except:
            return
        
        if len(children) < 2:
            return
        
        # 使用实例变量追踪选中的 key
        selected_key = getattr(self, '_selected_mat_key', None)
        
        # 找到选中项在 children 中的位置
        selected_idx = -1
        for i, w in enumerate(children):
            if hasattr(w, '_key') and w._key == selected_key:
                selected_idx = i
                break
        
        if selected_idx < 0:
            # 没有选中时，选中第一行
            if children:
                self._selected_mat_key = children[0]._key
                children[0].config(bg="#E8F4FD", relief=tk.GROOVE, borderwidth=2)
            return
        
        # 计算目标位置
        if direction == -999:  # 置顶
            new_idx = 0
        elif direction == 999:  # 置底
            new_idx = len(children) - 1
        else:
            new_idx = selected_idx + direction
        
        if new_idx < 0:
            new_idx = 0
        if new_idx >= len(children):
            new_idx = len(children) - 1
        
        if new_idx == selected_idx:
            return
        
        # 从列表中取出选中项，插入到目标位置
        children.insert(new_idx, children.pop(selected_idx))
        
        # 重新 pack（先清空再按新顺序）
        for w in self._mat_content.pack_slaves():
            try:
                w.pack_forget()
            except:
                pass
        for w in children:
            try:
                w.pack(fill=tk.X, pady=3)
            except:
                pass
        
        # 恢复选中状态（使用 _selected_mat_key）
        for w in children:
            if hasattr(w, '_key') and w._key == selected_key:
                w.config(bg="#E8F4FD", relief=tk.GROOVE, borderwidth=2)
                break

    def _add_dim_row(self, key):
        """动态添加一行尺寸参数"""
        fd = self._dim_fields_by_key.get(key)
        if not fd:
            return

        inner = tk.Frame(self._dim_content, bg="#FFFFFF", relief=tk.SOLID, borderwidth=1)
        inner.pack(fill=tk.X, pady=3)
        inner._key = key

        def on_dim_click(e):
            # 更新实例变量
            self._selected_dim_key = key
            # 更新视觉样式
            for w in self._dim_content.winfo_children():
                if hasattr(w, '_key'):
                    if w._key == key:
                        w.config(bg="#E8F4FD", relief=tk.GROOVE, borderwidth=2)
                    else:
                        w.config(bg="#FFFFFF", relief=tk.SOLID, borderwidth=1)

        inner.bind("<Button-1>", on_dim_click)

        lbl = tk.Label(inner, text=fd["label"], font=FONTS["body"],
                       bg="#FFFFFF", width=14, anchor="e", pady=4)
        lbl.pack(side=tk.LEFT, padx=(5, 5))
        lbl.bind("<Button-1>", on_dim_click)

        var = tk.StringVar()
        ftype = fd.get("type", "entry")
        placeholder = fd.get("placeholder", "")

        if ftype == "number":
            w = ttk.Entry(inner, textvariable=var, font=FONTS["body"], width=16)
        else:
            w = ttk.Entry(inner, textvariable=var, font=FONTS["body"], width=16)
            if placeholder:
                var.set(placeholder)
                w.config(foreground="#AAAAAA")
                w.bind("<FocusIn>",  lambda e, v=var, p=placeholder: self._clear_ph(e, v, p))
                w.bind("<FocusOut>", lambda e, v=var, p=placeholder: self._set_ph(e, v, p))

        w.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        w.bind("<Button-1>", on_dim_click)
        self._param_var_map[key] = var
        self._param_widget_map[key] = w

        # 添加单位标签
        unit = fd.get("unit", "")
        if unit:
            unit_lbl = tk.Label(inner, text=unit, font=FONTS["body"],
                               bg="#FFFFFF", fg="#666666")
            unit_lbl.pack(side=tk.LEFT, padx=5, pady=4)

        # 删除按钮
        tk.Button(inner, text="✕", font=(FONTS["body"][0], 9), bd=1,
                 fg="#FF6666", command=lambda: self._remove_dim_row(key, inner),
                 cursor="hand2"
                 ).pack(side=tk.LEFT, padx=(0, 5))

    def _remove_dim_row(self, key, row_widget):
        """删除一行尺寸参数"""
        if key in self._added_dim_params:
            self._added_dim_params.remove(key)
        if key in self._param_var_map:
            del self._param_var_map[key]
        if key in self._param_widget_map:
            del self._param_widget_map[key]
        row_widget.destroy()
        # 如果空了，显示空提示
        if not self._added_dim_params:
            self._dim_empty_lbl.pack()

    # ── 直接显示的字段 ──────────────────────────────────────────
    def _build_direct_fields(self, content, fields):
        for i, fd in enumerate(fields):
            self._add_field_to_frame(content, i, 0, fd)

    def _build_customer_fields(self, content):
        common = get_common_fields()
        for i, fd in enumerate(common):
            row = i // 2
            col = (i % 2) * 2
            self._add_field_to_frame(content, row, col, fd)

    def _build_remark_fields(self, content):
        for i, fd in enumerate(get_remark_fields()):
            self._add_field_to_frame(content, i * 2, 0, fd, wide=True)

    def _add_field_to_frame(self, parent, row, col, fd: dict, wide=False):
        key = fd["key"]
        label = fd.get("label", key)
        ftype = fd["type"]
        opts = fd.get("options", [])
        placeholder = fd.get("placeholder", "")

        lbl = tk.Label(parent, text=label, font=FONTS["body"],
                       bg="#FFFFFF", width=14, anchor="e", pady=4)
        lbl.grid(row=row, column=col, padx=(5, 5), pady=3, sticky="e")

        if ftype == "entry":
            var = tk.StringVar()
            w = ttk.Entry(parent, textvariable=var, font=FONTS["body"], width=26)
            if placeholder:
                var.set(placeholder)
                w.config(foreground="#AAAAAA")
                w.bind("<FocusIn>",  lambda e, v=var, p=placeholder: self._clear_ph(e, v, p))
                w.bind("<FocusOut>", lambda e, v=var, p=placeholder: self._set_ph(e, v, p))
            w.grid(row=row, column=col+1, padx=5, pady=3, sticky="ew")
            self._param_var_map[key] = var
            self._param_widget_map[key] = w

        elif ftype == "number":
            var = tk.StringVar()
            w = ttk.Entry(parent, textvariable=var, font=FONTS["body"], width=26)
            if placeholder:
                var.set(placeholder)
                w.config(foreground="#AAAAAA")
                w.bind("<FocusIn>",  lambda e, v=var, p=placeholder: self._clear_ph(e, v, p))
                w.bind("<FocusOut>", lambda e, v=var, p=placeholder: self._set_ph(e, v, p))
            w.grid(row=row, column=col+1, padx=5, pady=3, sticky="ew")
            self._param_var_map[key] = var
            self._param_widget_map[key] = w

        elif ftype == "combo":
            vals = opts or []
            var = tk.StringVar(value=vals[0] if vals else "")
            w = ttk.Combobox(parent, textvariable=var, values=vals,
                             font=FONTS["body"], width=24, state="readonly")
            w.grid(row=row, column=col+1, padx=5, pady=3, sticky="ew")
            w.bind("<MouseWheel>", lambda e: "break")
            self._param_var_map[key] = var
            self._param_widget_map[key] = w

        elif ftype == "combo_editable":
            vals = opts or MATERIAL_OPTS
            var = tk.StringVar(value=vals[0] if vals else "")
            w = ttk.Combobox(parent, textvariable=var, values=vals,
                             font=FONTS["body"], width=24)
            w.grid(row=row, column=col+1, padx=5, pady=3, sticky="ew")
            self._param_var_map[key] = var
            self._param_widget_map[key] = w
            # 阻止滚轮改变下拉框选项
            w.bind("<MouseWheel>", lambda e: "break")

        elif ftype == "date":
            var = tk.StringVar()
            w = DateEntry(parent, textvariable=var, font=FONTS["body"],
                          date_pattern="yyyy-mm-dd", width=24)
            w.grid(row=row, column=col+1, padx=5, pady=3, sticky="ew")
            self._param_var_map[key] = var
            self._param_widget_map[key] = w

        elif ftype == "textarea":
            container2 = tk.Frame(parent, bg="#FFFFFF")
            container2.grid(row=row, column=col, columnspan=3, padx=5, pady=3, sticky="ew")
            w = tk.Text(container2, font=FONTS["body"], width=62, height=3,
                        relief=tk.SOLID, borderwidth=1)
            w.pack(side=tk.LEFT, fill=tk.X, expand=True)
            if placeholder:
                w.insert("1.0", placeholder)
                w.config(foreground="#AAAAAA")
                w.bind("<FocusIn>",  lambda e, w=w, p=placeholder: self._clear_ph_text(e, w, p))
                w.bind("<FocusOut>", lambda e, w=w, p=placeholder: self._set_ph_text(e, w, p))
            scroll = ttk.Scrollbar(container2, orient=tk.VERTICAL, command=w.yview)
            scroll.pack(side=tk.RIGHT, fill=tk.Y)
            w.configure(yscrollcommand=scroll.set)
            self._param_widget_map[key] = w

        parent.columnconfigure(col+1, weight=1)

    # ── 占位符 ───────────────────────────────────────────────
    def _clear_ph(self, event, var, placeholder):
        if var.get() == placeholder:
            var.set("")
            event.widget.config(foreground="#000000")

    def _set_ph(self, event, var, placeholder):
        if not var.get().strip():
            var.set(placeholder)
            event.widget.config(foreground="#AAAAAA")

    def _clear_ph_text(self, event, widget: tk.Text, placeholder):
        if widget.get("1.0", tk.END).strip() == placeholder:
            widget.delete("1.0", tk.END)
            widget.config(foreground="#000000")

    def _set_ph_text(self, event, widget: tk.Text, placeholder):
        if not widget.get("1.0", tk.END).strip():
            widget.insert("1.0", placeholder)
            widget.config(foreground="#AAAAAA")

    # ═══════════════════════════════════════════════════════════
    # 添加自定义产品类型
    # ═══════════════════════════════════════════════════════════
    def _add_custom_product_type(self):
        win = tk.Toplevel(self)
        win.title("添加自定义产品类型")
        win.grab_set()
        win.transient(self)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        win.geometry(f"380x140+{sw//2-190}+{sh//2-70}")
        win.resizable(False, False)

        tk.Label(win, text="产品类型名称：", font=FONTS["body"],
                 bg="#FFFFFF").pack(anchor="w", padx=20, pady=(20, 5))
        name_var = tk.StringVar()
        name_entry = ttk.Entry(win, textvariable=name_var, font=FONTS["body"], width=30)
        name_entry.pack(fill=tk.X, padx=20, pady=(0, 15))
        name_entry.focus()

        def do_add():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning("提示", "名称不能为空", parent=win)
                return
            success, msg = add_product_type(name)
            if success:
                new_types = get_product_types()
                self._pt_combo["values"] = new_types
                self._pt_combo.set(name)
                win.destroy()
                messagebox.showinfo("成功", f"已添加「{name}」", parent=self)
            else:
                messagebox.showwarning("提示", msg, parent=win)

        name_entry.bind("<Return>", lambda e: do_add())

        btn_frame = tk.Frame(win, bg="#FFFFFF")
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="取消", width=10, command=win.destroy).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="添加", width=10, command=do_add,
                   style="Accent.TButton").pack(side=tk.LEFT, padx=10)

    # ═══════════════════════════════════════════════════════════
    # 数据采集
    # ═══════════════════════════════════════════════════════════
    def _collect_all_values(self) -> dict:
        fixed_keys = {fd["key"] for fd in get_common_fields()}
        fixed_keys.update({fd["key"] for fd in get_remark_fields()})
        fixed_keys.update({fd["key"] for fd in MATERIAL_FIELDS})
        fixed_keys.update({fd["key"] for fd in SURFACE_FIELD})

        # 占位符文本列表
        placeholders = {
            "详细描述产品规格、特殊要求等（产品专属备注，与订单备注区分）",
            "其他补充说明",
        }
        # 匹配 "如：XX" 格式的占位符
        import re
        placeholder_pattern = re.compile(r"^如[：:]\s*.+$")

        data = {"product_type": self._pt_var.get()}

        for key, widget in self._param_widget_map.items():
            if key in fixed_keys or key in self._added_dim_params or key in self._added_mat_params or key in self._added_surface_params:
                if isinstance(widget, tk.Text):
                    val = widget.get("1.0", tk.END).strip()
                else:
                    val = widget.get().strip() if hasattr(widget, "get") else ""
                # 跳过占位符文本
                if placeholder_pattern.match(val) or val in placeholders:
                    continue
                if val:
                    data[key] = val

        return data

    def _on_confirm(self):
        data = self._collect_all_values()
        
        # 必填项验证
        if not data.get("customer_name"):
            messagebox.showwarning("必填项", "请填写客户名称！", parent=self)
            return
        if not data.get("product_type"):
            messagebox.showwarning("必填项", "请选择产品类型！", parent=self)
            return
        
        # 数量验证
        try:
            qty = float(data.get("quantity", 0))
            if qty <= 0:
                messagebox.showwarning("填写错误", "数量必须大于0！", parent=self)
                return
        except (ValueError, TypeError):
            messagebox.showwarning("填写错误", "数量请填写数字！", parent=self)
            return
        
        # 单价验证（如果有填写）
        unit_price = data.get("unit_price", "").strip()
        if unit_price:
            try:
                price = float(unit_price)
                if price < 0:
                    messagebox.showwarning("填写错误", "单价不能为负数！", parent=self)
                    return
            except ValueError:
                messagebox.showwarning("填写错误", "单价请填写数字！", parent=self)
                return
        
        data["order_no"] = self._order_no
        self.on_save_callback(data)
        self.destroy()

    # ═══════════════════════════════════════════════════════════
    # 模板
    # ═══════════════════════════════════════════════════════════
    def _save_template(self):
        pt = self._pt_var.get()
        values = self._collect_all_values()
        for k in ("customer_name", "customer_phone", "customer_address",
                  "quantity", "unit_price", "delivery_date", "remark",
                  "product_remark", "product_type", "order_no"):
            values.pop(k, None)

        win = tk.Toplevel(self)
        win.title("保存模板")
        win.grab_set()
        win.transient(self)
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry(f"340x140+{sw//2-170}+{sh//2-70}")
        win.resizable(False, False)

        tk.Label(win, text="模板名称：", font=FONTS["body"]).grid(row=0, column=0, padx=15, pady=20, sticky="e")
        name_var = tk.StringVar()
        ttk.Entry(win, textvariable=name_var, font=FONTS["body"], width=20).grid(row=0, column=1, padx=5, pady=20)

        def do_save():
            ok, msg = save_template(pt, name_var.get().strip(), values)
            messagebox.showinfo("提示", msg, parent=win)
            if ok:
                win.destroy()

        btn_row = tk.Frame(win)
        btn_row.grid(row=1, column=0, columnspan=2, pady=5)
        ttk.Button(btn_row, text="取消", command=win.destroy, width=10).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_row, text="保存", command=do_save, width=10,
                   style="Accent.TButton").pack(side=tk.LEFT, padx=5)

    def _load_template(self):
        pt = self._pt_var.get()
        names = get_template_names(pt)
        if not names:
            messagebox.showinfo("提示", f"「{pt}」暂无可用模板", parent=self)
            return

        win = tk.Toplevel(self)
        win.title("加载模板")
        win.grab_set()
        win.transient(self)
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry(f"340x180+{sw//2-170}+{sh//2-90}")
        win.resizable(False, False)

        tk.Label(win, text="选择模板：", font=FONTS["body"]).grid(row=0, column=0, padx=15, pady=20, sticky="e")
        sel_var = tk.StringVar(value=names[0])
        tpl_combo = ttk.Combobox(win, textvariable=sel_var, values=names,
                     font=FONTS["body"], width=20, state="readonly")
        tpl_combo.grid(row=0, column=1, padx=5, pady=20)
        tpl_combo.bind("<MouseWheel>", lambda e: "break")

        def do_load():
            tpl = get_template(pt, sel_var.get())
            # 应用模板值到表单
            for key, val in tpl.items():
                if key in self._param_var_map:
                    self._param_var_map[key].set(val)
                    widget = self._param_widget_map.get(key)
                    if widget and hasattr(widget, "config"):
                        widget.config(foreground=COLORS.get("text_primary", "#000000"))
                elif key in self._added_dim_params:
                    # 已在尺寸参数中，更新值
                    widget = self._param_widget_map.get(key)
                    if widget:
                        if isinstance(widget, tk.Text):
                            widget.delete("1.0", tk.END)
                            widget.insert("1.0", val)
                        else:
                            widget.delete(0, tk.END)
                            widget.insert(0, val)
                        widget.config(foreground=COLORS.get("text_primary", "#000000"))
                elif key in self._added_mat_params:
                    # 已在材质参数中，更新值
                    widget = self._param_widget_map.get(key)
                    if widget:
                        widget.set(val)
                elif key in self._added_surface_params:
                    # 已在表面处理参数中，更新值
                    widget = self._param_widget_map.get(key)
                    if widget:
                        if isinstance(widget, tk.Text):
                            widget.delete("1.0", tk.END)
                            widget.insert("1.0", val)
                        else:
                            widget.delete(0, tk.END)
                            widget.insert(0, val)
                        widget.config(foreground=COLORS.get("text_primary", "#000000"))
                else:
                    # 预设参数，自动添加到对应区域
                    dim_keys = {fd["key"] for fd in DIM_FIELDS}
                    mat_keys = {fd["key"] for fd in MATERIAL_FIELDS}
                    surface_keys = {fd["key"] for fd in SURFACE_FIELD}

                    if key in dim_keys and key not in self._added_dim_params:
                        self._added_dim_params.append(key)
                        self._add_dim_row(key)
                        self._dim_empty_lbl.pack_forget()
                        widget = self._param_widget_map.get(key)
                        if widget:
                            widget.delete(0, tk.END)
                            widget.insert(0, val)
                            widget.config(foreground=COLORS.get("text_primary", "#000000"))
                    elif key in mat_keys and key not in self._added_mat_params:
                        self._added_mat_params.append(key)
                        self._add_mat_row(key)
                        self._mat_empty_lbl.pack_forget()
                        widget = self._param_widget_map.get(key)
                        if widget:
                            widget.set(val)
                    elif key in surface_keys and key not in self._added_surface_params:
                        self._added_surface_params.append(key)
                        self._add_surface_row(key)
                        widget = self._param_widget_map.get(key)
                        if widget:
                            if isinstance(widget, tk.Text):
                                widget.delete("1.0", tk.END)
                                widget.insert("1.0", val)
                            else:
                                widget.delete(0, tk.END)
                                widget.insert(0, val)
                            widget.config(foreground=COLORS.get("text_primary", "#000000"))
            win.destroy()
            messagebox.showinfo("提示", "模板已加载", parent=self)

        btn_row = tk.Frame(win)
        btn_row.grid(row=1, column=0, columnspan=2, pady=5)
        ttk.Button(btn_row, text="取消", command=win.destroy, width=10).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_row, text="加载", command=do_load, width=10,
                   style="Accent.TButton").pack(side=tk.LEFT, padx=5)

    def _manage_templates(self):
        pt = self._pt_var.get()
        names = get_template_names(pt)

        win = tk.Toplevel(self)
        win.title(f"模板管理 - {pt}")
        win.grab_set()
        win.transient(self)
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry(f"420x360+{sw//2-210}+{sh//2-180}")

        tk.Label(win, text=f"产品类型：{pt}", font=FONTS["subtitle"],
                 fg=COLORS["primary"]).pack(pady=(10, 5))

        listbox = tk.Listbox(win, font=FONTS["body"], height=12, selectmode=tk.SINGLE,
                             relief=tk.SOLID, borderwidth=1)
        listbox.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        def refresh_list():
            listbox.delete(0, tk.END)
            for n in get_template_names(pt):
                listbox.insert(tk.END, n)
        refresh_list()

        def do_rename():
            sel = listbox.curselection()
            if not sel:
                messagebox.showwarning("提示", "请先选中一个模板", parent=win)
                return
            old_name = listbox.get(sel[0])
            new_name = tk.simpledialog.askstring("重命名", f"新名称：", initialvalue=old_name, parent=win)
            if new_name:
                ok, msg = rename_template(pt, old_name, new_name.strip())
                messagebox.showinfo("提示", msg, parent=win)
                refresh_list()

        def do_delete():
            sel = listbox.curselection()
            if not sel:
                messagebox.showwarning("提示", "请先选中一个模板", parent=win)
                return
            name = listbox.get(sel[0])
            if messagebox.askyesno("确认", f"确定删除模板「{name}」？", parent=win):
                ok, msg = delete_template(pt, name)
                messagebox.showinfo("提示", msg, parent=win)
                refresh_list()

        btn_row = tk.Frame(win)
        btn_row.pack(pady=8)
        ttk.Button(btn_row, text="重命名", command=do_rename, width=10).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_row, text="删除", command=do_delete, width=10).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_row, text="关闭", command=win.destroy, width=10).pack(side=tk.LEFT, padx=8)

    # ── 滚动 ─────────────────────────────────────────────────
    def _on_frame_configure(self, event):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self._canvas.itemconfig(self._canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        try:
            if self._canvas.winfo_exists() and self._canvas.winfo_ismapped():
                self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except:
            pass
