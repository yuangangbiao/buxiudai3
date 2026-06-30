# -*- coding: utf-8 -*-
"""
基础对话框
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry
from config import COLORS, FONTS
from constants import OrderStatus
from .widgets import PlaceholderEntry
from utils.window_manager import setup_resizable_window
import functools
import os


def alert(message, title="提示"):
    """简单提示框"""
    win = tk.Toplevel()
    win.title(title)
    win.transient()
    win.grab_set()

    screen_w = win.winfo_screenwidth()
    screen_h = win.winfo_screenheight()
    win.geometry(f"350x120+{screen_w//2-175}+{screen_h//2-60}")

    tk.Label(win, text=message, font=FONTS["body"], wraplength=320,
             bg="#FFFFFF").pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    ttk.Button(win, text="确定", command=win.destroy).pack(pady=(0, 15))


def center_window(window, width, height, topmost=False):
    if topmost:
        window.attributes("-topmost", True)
    window.update_idletasks()
    screen_w = window.winfo_screenwidth()
    screen_h = window.winfo_screenheight()
    x = (screen_w - width) // 2
    y = (screen_h - height) // 2
    window.geometry(f"{width}x{height}+{x}+{y}")


def confirm(message, title="确认"):
    """确认对话框，返回 True/False"""
    result = [False]

    def on_ok():
        result[0] = True
        win.destroy()

    def on_cancel():
        win.destroy()

    win = tk.Toplevel()
    win.title(title)
    win.transient()
    win.grab_set()

    screen_w = win.winfo_screenwidth()
    screen_h = win.winfo_screenheight()
    win.geometry(f"350x140+{screen_w//2-175}+{screen_h//2-70}")

    frm = tk.Frame(win, bg="#FFFFFF")
    frm.pack(fill=tk.BOTH, expand=True)

    tk.Label(frm, text=message, font=FONTS["body"], wraplength=320,
             bg="#FFFFFF").pack(pady=(20, 15), padx=20)

    btn_frame = tk.Frame(frm, bg="#FFFFFF")
    btn_frame.pack(pady=(0, 15))
    ttk.Button(btn_frame, text="取消", command=on_cancel, width=10).pack(side=tk.LEFT, padx=10)
    ttk.Button(btn_frame, text="确定", command=on_ok, width=10).pack(side=tk.LEFT, padx=10)

    win.wait_window()
    return result[0]


def _on_add_custom_type(key, combo, options):
    """弹窗添加自定义类型"""
    current_type = "产品类型" if key == "product_type" else "单位"
    custom_type_name = key.replace("product_type", "product_types").replace("material", "materials")

    # 弹出输入框
    input_win = tk.Toplevel()
    input_win.title(f"添加自定义{current_type}")
    input_win.geometry("380x130")
    input_win.transient()
    input_win.grab_set()
    input_win.resizable(False, False)

    # 居中
    input_win.update_idletasks()
    x = (input_win.winfo_screenwidth() // 2) - 190
    y = (input_win.winfo_screenheight() // 2) - 65
    input_win.geometry(f"380x130+{x}+{y}")

    tk.Label(input_win, text=f"输入新的{current_type}名称：",
             font=FONTS["body"], bg="#FFFFFF").pack(pady=(15, 5), padx=20)
    entry = ttk.Entry(input_win, font=FONTS["body"], width=30)
    entry.pack(padx=20, pady=5)
    entry.focus()

    from utils.custom_types import add_product_type, add_material

    def do_add():
        name = entry.get().strip()
        if not name:
            messagebox.showwarning("提示", "名称不能为空", parent=input_win)
            return
        if key == "product_type":
            success, msg = add_product_type(name)
        else:
            success, msg = add_material(name)
        if success:
            # 刷新当前下拉框选项
            from utils.custom_types import get_product_types, get_materials
            new_opts = get_product_types() if key == "product_type" else get_materials()
            combo["values"] = new_opts
            combo.set(name)
            input_win.destroy()
        else:
            messagebox.showinfo("提示", msg, parent=input_win)

    def on_enter(e):
        do_add()

    entry.bind("<Return>", on_enter)

    btn_frame = tk.Frame(input_win, bg="#FFFFFF")
    btn_frame.pack(pady=10)
    ttk.Button(btn_frame, text="取消", width=10,
               command=input_win.destroy).pack(side=tk.LEFT, padx=10)
    ttk.Button(btn_frame, text="添加", width=10,
               command=do_add, style="Accent.TButton").pack(side=tk.LEFT, padx=10)


def manage_custom_types_dialog(parent):
    """管理自定义产品类型和材质弹窗"""
    from utils.custom_types import (
        get_custom_product_types, get_custom_materials,
        add_product_type, add_material, remove_product_type, remove_material
    )
    from config import PRODUCT_TYPES, MATERIALS

    win = tk.Toplevel(parent)
    win.title("🛠 管理产品类型和材质")
    win.transient(parent)
    win.grab_set()
    setup_resizable_window(win, "custom_types_dialog", "550x480")

    # 标题
    tk.Label(win, text="🛠 自定义类型管理", font=("微软雅黑", 13, "bold"),
             bg="#FFFFFF", fg=COLORS["primary"]).pack(pady=12)

    # 左侧：产品类型
    left_frame = tk.Frame(win, bg="#FFFFFF")
    left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(15, 5), pady=10)

    tk.Label(left_frame, text="📋 产品类型", font=FONTS["subtitle"],
             bg="#FFFFFF", fg=COLORS["primary"]).pack(anchor="w", padx=10)
    tk.Label(left_frame, text="默认（不可删）：", font=FONTS["small"],
             bg="#FFFFFF", fg="#888").pack(anchor="w", padx=10, pady=(5, 0))
    tk.Label(left_frame, text="、".join(PRODUCT_TYPES), font=FONTS["small"],
             bg="#F5F5F5", fg="#666", wraplength=230, justify="left",
             padx=8, pady=5).pack(fill=tk.X, padx=10, pady=(0, 5))

    tk.Label(left_frame, text="自定义：", font=FONTS["small"],
             bg="#FFFFFF", fg="#888").pack(anchor="w", padx=10, pady=(8, 0))

    list_frame = tk.Frame(left_frame, bg="#FFFFFF")
    list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=3)

    pt_scroll = ttk.Scrollbar(list_frame)
    pt_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    pt_listbox = tk.Listbox(list_frame, font=FONTS["body"], bg="#FFFFFF",
                            yscrollcommand=pt_scroll.set, height=8,
                            selectbackground=COLORS["accent"],
                            selectforeground="white")
    pt_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    pt_scroll.config(command=pt_listbox.yview)

    pt_entry = ttk.Entry(left_frame, font=FONTS["body"], width=22)
    pt_entry.pack(fill=tk.X, padx=10, pady=(5, 0))

    def refresh_pt():
        pt_listbox.delete(0, tk.END)
        for t in get_custom_product_types():
            pt_listbox.insert(tk.END, t)

    def add_pt():
        name = pt_entry.get().strip()
        if not name:
            return
        success, msg = add_product_type(name)
        if success:
            pt_entry.delete(0, tk.END)
            refresh_pt()
        messagebox.showinfo("提示", msg, parent=win)

    def del_pt():
        idx = pt_listbox.curselection()
        if not idx:
            messagebox.showinfo("提示", "请先选择要删除的类型", parent=win)
            return
        name = pt_listbox.get(idx[0])
        if messagebox.askyesno("确认", f"确认删除「{name}」？", parent=win):
            success, msg = remove_product_type(name)
            refresh_pt()
            messagebox.showinfo("提示", msg, parent=win)

    pt_entry.bind("<Return>", lambda e: add_pt())
    tk.Frame(left_frame, height=2, bg="#E0E0E0").pack(fill=tk.X, padx=10, pady=5)
    btn_row = tk.Frame(left_frame, bg="#FFFFFF")
    btn_row.pack(fill=tk.X, padx=10, pady=3)
    tk.Button(btn_row, text="添加", command=add_pt, font=FONTS["body"],
             bg=COLORS["accent"], fg="white", relief=tk.FLAT,
             cursor="hand2", padx=10).pack(side=tk.LEFT)
    tk.Button(btn_row, text="删除", command=del_pt, font=FONTS["body"],
             bg="#F44336", fg="white", relief=tk.FLAT,
             cursor="hand2", padx=10).pack(side=tk.LEFT, padx=5)

    # 分隔线
    tk.Frame(win, width=1, bg="#E0E0E0").pack(side=tk.LEFT, fill=tk.Y, pady=10)

    # 右侧：材质
    right_frame = tk.Frame(win, bg="#FFFFFF")
    right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 15), pady=10)

    tk.Label(right_frame, text="🔩 材　　质", font=FONTS["subtitle"],
             bg="#FFFFFF", fg=COLORS["primary"]).pack(anchor="w", padx=10)
    tk.Label(right_frame, text="默认（不可删）：", font=FONTS["small"],
             bg="#FFFFFF", fg="#888").pack(anchor="w", padx=10, pady=(5, 0))
    tk.Label(right_frame, text="、".join(MATERIALS), font=FONTS["small"],
             bg="#F5F5F5", fg="#666", wraplength=230, justify="left",
             padx=8, pady=5).pack(fill=tk.X, padx=10, pady=(0, 5))

    tk.Label(right_frame, text="自定义：", font=FONTS["small"],
             bg="#FFFFFF", fg="#888").pack(anchor="w", padx=10, pady=(8, 0))

    list_frame2 = tk.Frame(right_frame, bg="#FFFFFF")
    list_frame2.pack(fill=tk.BOTH, expand=True, padx=10, pady=3)

    mt_scroll = ttk.Scrollbar(list_frame2)
    mt_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    mt_listbox = tk.Listbox(list_frame2, font=FONTS["body"], bg="#FFFFFF",
                            yscrollcommand=mt_scroll.set, height=8,
                            selectbackground=COLORS["accent"],
                            selectforeground="white")
    mt_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    mt_scroll.config(command=mt_listbox.yview)

    mt_entry = ttk.Entry(right_frame, font=FONTS["body"], width=22)
    mt_entry.pack(fill=tk.X, padx=10, pady=(5, 0))

    def refresh_mt():
        mt_listbox.delete(0, tk.END)
        for t in get_custom_materials():
            mt_listbox.insert(tk.END, t)

    def add_mt():
        name = mt_entry.get().strip()
        if not name:
            return
        success, msg = add_material(name)
        if success:
            mt_entry.delete(0, tk.END)
            refresh_mt()
        messagebox.showinfo("提示", msg, parent=win)

    def del_mt():
        idx = mt_listbox.curselection()
        if not idx:
            messagebox.showinfo("提示", "请先选择要删除的材质", parent=win)
            return
        name = mt_listbox.get(idx[0])
        if messagebox.askyesno("确认", f"确认删除「{name}」？", parent=win):
            success, msg = remove_material(name)
            refresh_mt()
            messagebox.showinfo("提示", msg, parent=win)

    mt_entry.bind("<Return>", lambda e: add_mt())
    tk.Frame(right_frame, height=2, bg="#E0E0E0").pack(fill=tk.X, padx=10, pady=5)
    btn_row2 = tk.Frame(right_frame, bg="#FFFFFF")
    btn_row2.pack(fill=tk.X, padx=10, pady=3)
    tk.Button(btn_row2, text="添加", command=add_mt, font=FONTS["body"],
              bg=COLORS["accent"], fg="white", relief=tk.FLAT,
              cursor="hand2", padx=10).pack(side=tk.LEFT)
    tk.Button(btn_row2, text="删除", command=del_mt, font=FONTS["body"],
              bg="#F44336", fg="white", relief=tk.FLAT,
              cursor="hand2", padx=10).pack(side=tk.LEFT, padx=5)

    # 底部关闭
    tk.Frame(win, height=2, bg="#E0E0E0").pack(fill=tk.X, side=tk.BOTTOM)
    tk.Button(win, text="关闭", command=win.destroy, font=FONTS["body"],
              bg="#9E9E9E", fg="white", relief=tk.FLAT,
              cursor="hand2", padx=20, pady=8).pack(pady=10, side=tk.BOTTOM)

    refresh_pt()
    refresh_mt()


def validate_field_config(func):
    """字段配置验证装饰器：在弹窗前校验字段定义的合法性"""
    VALID_TYPES = {"entry", "combo", "combo_editable", "date", "textarea", "number",
                   "readonly", "label", "grid_combo", "checkgroup", "attachment"}

    @functools.wraps(func)
    def wrapper(title, fields, *args, **kwargs):
        for i, field in enumerate(fields):
            if len(field) < 2:
                raise ValueError(f"字段 #{i}: 至少需要 (label, key)")
            key = field[1]
            ftype = field[3] if len(field) > 3 else "entry"
            if ftype not in VALID_TYPES:
                raise ValueError(f"字段 '{key}': 未知字段类型 '{ftype}'")
            if ftype == "combo" and len(field) < 5:
                raise ValueError(f"字段 '{key}': combo 类型需要提供 options 参数")
            if ftype == "grid_combo":
                opts = field[4] if len(field) > 4 else {}
                if not isinstance(opts, dict) or "depends_on" not in opts:
                    raise ValueError(f"字段 '{key}': grid_combo 需要 {{'depends_on': ..., 'options_fn': ...}}")
                if "options_fn" not in opts:
                    raise ValueError(f"字段 '{key}': grid_combo 需要 options_fn 回调函数")
        return func(title, fields, *args, **kwargs)
    return wrapper


def popup_form(title, fields, callback, width=650, height=None, resizable=True, on_confirm=None, window_key=None):
    """通用表单弹窗
    fields: [(label, key, default, type, options, placeholder)]
    type: entry/combo/combo_editable/date/textarea/number/readonly/label/grid_combo/checkgroup/attachment
    placeholder: 提示文字
    on_confirm: (按钮文本, 回调函数) 元组，用于显示第二个按钮（如"确认生产"）
    window_key: 窗口配置key，用于保存/恢复窗口大小位置
    """
    win = tk.Toplevel()
    win.title(title)
    win.withdraw()
    win.transient()
    win.grab_set()
    screen_w = win.winfo_screenwidth()
    screen_h = win.winfo_screenheight()
    win.resizable(resizable, resizable)

    style = ttk.Style(win)
    style.configure("Form.TLabel", font=FONTS["body"], background=COLORS["bg_main"])

    canvas = tk.Canvas(win, bg=COLORS["bg_main"], highlightthickness=0)
    scrollbar = ttk.Scrollbar(win, orient=tk.VERTICAL, command=canvas.yview)
    scroll_frame = tk.Frame(canvas, bg=COLORS["bg_main"])

    scroll_frame.bind("<Configure>",
                      lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    if height is None:
        row_count = len(fields)
        estimated_h = min(max(row_count * 32 + 100, 450), screen_h - 100)
    else:
        estimated_h = height

    if not window_key:
        win.geometry(f"{width}x{estimated_h}+{screen_w//2 - width//2}+{screen_h//2 - estimated_h//2}")
    else:
        setup_resizable_window(win, window_key, f"{width}x{estimated_h}")

    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    main_frame = tk.Frame(scroll_frame, bg=COLORS["bg_main"])
    main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

    # 网格权重
    main_frame.grid_columnconfigure(0, minsize=100)
    main_frame.grid_columnconfigure(1, weight=1)

    entries = {}
    row = 0

    for field in fields:
        label = field[0]
        key = field[1]
        default = field[2] if len(field) > 2 else ""
        ftype = field[3] if len(field) > 3 else "entry"
        options = field[4] if len(field) > 4 else []
        placeholder = field[5] if len(field) > 5 else ""

        # textarea: 标签在上，输入框在下
        if ftype == "textarea":
            tk.Label(main_frame, text=label, font=FONTS["body"],
                    bg=COLORS["bg_main"], anchor="w").grid(
                row=row, column=0, columnspan=2, sticky="w", pady=(5, 2))
            row += 1
            txt = tk.Text(main_frame, width=55, height=3,
                         font=FONTS["body"], wrap=tk.WORD)
            txt.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 5))
            if default:
                txt.insert("1.0", default)
            entries[key] = txt
            row += 1
            continue

        # 标签
        tk.Label(main_frame, text=label, font=FONTS["body"],
                bg=COLORS["bg_main"], anchor="w").grid(
            row=row, column=0, sticky="w", pady=5, padx=(0, 10))

        if ftype == "entry":
            ent = PlaceholderEntry(main_frame, placeholder=placeholder, width=30)
            ent.grid(row=row, column=1, sticky="ew", pady=5)
            if default:
                ent.set_value(default)
            entries[key] = ent

        elif ftype == "number":
            ph = placeholder if placeholder else "请输入数字"
            ent = PlaceholderEntry(main_frame, placeholder=ph, width=30)
            ent.grid(row=row, column=1, sticky="ew", pady=5)
            if default is not None and default != "":
                ent.set_value(str(default))
            entries[key] = ent

        elif ftype == "date":
            # 使用DateEntry日历选择器
            date_ent = DateEntry(main_frame, width=28, font=FONTS["body"],
                                background=COLORS["primary"], foreground="white",
                                borderwidth=2, date_pattern="yyyy-mm-dd",
                                showweeknumbers=False)
            date_ent.grid(row=row, column=1, sticky="ew", pady=5)
            if default:
                from datetime import datetime as dt
                default_str = str(default)[:10] if isinstance(default, dt) else str(default)
                if default_str.strip():
                    try:
                        date_ent.set_date(dt.strptime(default_str.strip(), "%Y-%m-%d").date())
                    except Exception:
                        pass
            entries[key] = date_ent

        elif ftype == "combo":
            cb = ttk.Combobox(main_frame, values=options, width=28,
                              font=FONTS["body"], state="readonly")
            cb.grid(row=row, column=1, sticky="ew", pady=5)
            if options:
                cb.current(0)
            entries[key] = cb

        elif ftype == "combo_editable":
            # 可编辑下拉框 + 添加按钮
            combo_frame = tk.Frame(main_frame, bg=COLORS["bg_main"])
            combo_frame.grid(row=row, column=1, sticky="ew", pady=5)

            cb = ttk.Combobox(combo_frame, values=options, width=24,
                              font=FONTS["body"], state="normal")
            cb.pack(side=tk.LEFT, fill=tk.X, expand=True)
            # 优先选中 default 值（编辑场景），找不到才用第一个
            if default and default in options:
                cb.set(default)
            elif options:
                cb.current(0)
            else:
                cb.set(default or "")

            # 添加按钮
            btn_add = tk.Button(combo_frame, text="+", font=("微软雅黑", 10, "bold"),
                               bg=COLORS["accent"], fg="white", relief=tk.FLAT,
                               cursor="hand2", padx=6, pady=0,
                               command=lambda k=key, c=cb, opts=options: _on_add_custom_type(k, c, opts))
            btn_add.pack(side=tk.LEFT, padx=(5, 0))
            entries[key] = cb

        elif ftype == "readonly":
            lb = tk.Label(main_frame, text=default or "", font=FONTS["body"],
                         bg="#EEEEEE", anchor="w", relief=tk.SUNKEN, padx=5)
            lb.grid(row=row, column=1, sticky="ew", pady=5)
            entries[key] = lb

        elif ftype == "label":
            # 只读纯文本标签（无边框，用于概览展示）
            lb = tk.Label(main_frame, text=default or "—", font=FONTS["body"],
                         bg=COLORS["bg_main"], anchor="w",
                         fg=COLORS.get("text_secondary", "#666666"))
            lb.grid(row=row, column=1, sticky="w", pady=5, padx=5)
            entries[key] = lb

        elif ftype == "grid_combo":
            child_opts = options if isinstance(options, dict) else {}
            depends_on = child_opts.get("depends_on", "")
            options_fn = child_opts.get("options_fn", lambda v: [])
            cb = ttk.Combobox(main_frame, values=[], width=28,
                              font=FONTS["body"], state="readonly")
            cb.grid(row=row, column=1, sticky="ew", pady=5)
            if default:
                cb.set(default)
            if depends_on and depends_on in entries:
                parent_cb = entries[depends_on]
                def on_parent_select(*args, child_cb=cb, fn=options_fn):
                    val = parent_cb.get()
                    child_cb["values"] = fn(val)
                    if child_cb["values"]:
                        child_cb.current(0)
                    else:
                        child_cb.set("")
                if isinstance(parent_cb, ttk.Combobox):
                    parent_cb.bind("<<ComboboxSelected>>", on_parent_select)
                    if parent_cb.get():
                        on_parent_select()
            entries[key] = cb

        elif ftype == "checkgroup":
            cb_frame = tk.Frame(main_frame, bg=COLORS["bg_main"])
            cb_frame.grid(row=row, column=1, sticky="w", pady=5)
            check_vars = {}
            opt_list = options if isinstance(options, list) else []
            default_sel = default if isinstance(default, list) else []
            for opt in opt_list:
                var = tk.BooleanVar(value=opt in default_sel)
                check_vars[opt] = var
                tk.Checkbutton(cb_frame, text=opt, variable=var, font=FONTS["body"],
                               bg=COLORS["bg_main"], cursor="hand2").pack(side=tk.LEFT, padx=5)
            entries[key] = check_vars

        elif ftype == "attachment":
            max_size_mb = options.get("max_size_mb", 2) if isinstance(options, dict) else 2
            ft = options.get("filetypes", [("所有文件", "*.*")]) if isinstance(options, dict) else [("所有文件", "*.*")]
            attach_frame = tk.Frame(main_frame, bg=COLORS["bg_main"])
            attach_frame.grid(row=row, column=1, sticky="ew", pady=5)
            file_var = tk.StringVar(value=default or "")
            file_entry = tk.Entry(attach_frame, textvariable=file_var, font=FONTS["body"], width=25)
            file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            def browse_file(var=file_var, max_mb=max_size_mb, ft=ft):
                path = filedialog.askopenfilename(filetypes=ft)
                if path:
                    size = os.path.getsize(path)
                    if size > max_mb * 1024 * 1024:
                        alert(f"附件大小不能超过{max_mb}MB", "提示")
                        return
                    var.set(path)
            tk.Button(attach_frame, text="浏览...", font=FONTS["small"],
                      bg=COLORS["accent"], fg="white", relief=tk.FLAT,
                      cursor="hand2", command=browse_file).pack(side=tk.LEFT, padx=5)
            entries[key] = file_var

        row += 1

    # 按钮行
    btn_frame = tk.Frame(main_frame, bg=COLORS["bg_main"])
    btn_frame.grid(row=row, column=0, columnspan=2, pady=15)

    # 鼠标滚轮支持
    def on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    win.bind_all("<MouseWheel>", on_mousewheel)
    win.bind("<Destroy>", lambda e: win.unbind_all("<MouseWheel>")
             if hasattr(win, 'winfo_exists') and win.winfo_exists() else None)

    def on_submit():
        result = {}
        for key, w in entries.items():
            if isinstance(w, PlaceholderEntry):
                result[key] = w.get_value()
            elif isinstance(w, tk.Text):
                result[key] = w.get("1.0", tk.END).strip()
            elif isinstance(w, tk.Label):
                result[key] = w.cget("text")
            elif isinstance(w, ttk.Combobox):
                result[key] = w.get()
            elif isinstance(w, DateEntry):
                result[key] = w.get()
            elif isinstance(w, dict):
                result[key] = [opt for opt, var in w.items() if var.get()]
            elif isinstance(w, tk.StringVar):
                result[key] = w.get()
            else:
                result[key] = w.get().strip()
        win.destroy()
        callback(result)

    def on_cancel():
        win.destroy()

    ttk.Button(btn_frame, text="取消", command=on_cancel, width=12).pack(side=tk.LEFT, padx=10)
    ttk.Button(btn_frame, text="保存", command=on_submit, width=12,
               style="Primary.TButton").pack(side=tk.LEFT, padx=10)
    
    # 第二个按钮（如"确认生产"）
    if on_confirm:
        confirm_text, confirm_cb = on_confirm
        def on_confirm_click():
            result = {}
            for key, w in entries.items():
                if isinstance(w, PlaceholderEntry):
                    result[key] = w.get_value()
                elif isinstance(w, tk.Text):
                    result[key] = w.get("1.0", tk.END).strip()
                elif isinstance(w, tk.Label):
                    result[key] = w.cget("text")
                elif isinstance(w, ttk.Combobox):
                    result[key] = w.get()
                elif isinstance(w, DateEntry):
                    result[key] = w.get()
                elif isinstance(w, dict):
                    result[key] = [opt for opt, var in w.items() if var.get()]
                elif isinstance(w, tk.StringVar):
                    result[key] = w.get()
                else:
                    result[key] = w.get().strip()
            win.destroy()
            confirm_cb(result)
        
        ttk.Button(btn_frame, text=confirm_text, command=on_confirm_click, width=14,
                   style="Accent.TButton").pack(side=tk.LEFT, padx=10)

    win.deiconify()
    win.wait_window()


def show_detail(parent, order, production=None, processes=None):
    """订单详情弹窗"""
    top = tk.Toplevel(parent)
    top.title(f"订单详情 - {order.get('order_no', '')}")
    top.transient()
    top.grab_set()
    setup_resizable_window(top, "show_detail", "550x650")

    canvas = tk.Canvas(top, bg=COLORS["bg_main"], highlightthickness=0)
    scrollbar = ttk.Scrollbar(top, orient=tk.VERTICAL, command=canvas.yview)
    content = tk.Frame(canvas, bg=COLORS["bg_main"])

    def on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    top.bind("<MouseWheel>", on_mousewheel)

    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.create_window((0, 0), window=content, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    def on_config(e):
        canvas.configure(scrollregion=canvas.bbox("all"))
    content.bind("<Configure>", on_config)

    # 标题
    tk.Label(content, text=f"订单号：{order.get('order_no', '')}",
             font=("微软雅黑", 14, "bold"), bg=COLORS["bg_main"],
             fg=COLORS["primary"]).pack(pady=10)

    status = order.get("status", OrderStatus.PENDING.value)
    status_color = "#FF9800" if status == OrderStatus.PENDING.value else "#4CAF50" if status == OrderStatus.CONFIRMED.value else "#2196F3"
    status_label = tk.Label(content, text=f"状态：{status}",
                            font=FONTS["body"], bg=COLORS["bg_main"], fg=status_color)
    status_label.pack()

    # 卡片
    card = tk.Frame(content, bg="white", relief=tk.RAISED, bd=1)
    card.pack(fill=tk.X, padx=15, pady=10, ipady=5)

    # 基本信息
    rows = [
        ("客户名称", order.get("customer_name", "")),
        ("联系电话", order.get("customer_phone", "") or "-"),
        ("客户地址", order.get("customer_address", "") or "-"),
        ("交货日期", order.get("delivery_date", "") or "-"),
    ]
    row_idx = 0
    for label, val in rows:
        tk.Label(card, text=label + "：", font=FONTS["body"], bg="white",
                anchor="w", width=10).grid(row=row_idx, column=0, padx=10, pady=4, sticky="w")
        tk.Label(card, text=val, font=FONTS["body"], bg="#F8F8F8",
                anchor="w", relief=tk.SUNKEN, padx=5).grid(row=row_idx, column=1, padx=(0, 10), pady=4, sticky="ew")
        row_idx += 1

    # 分隔线
    tk.Label(card, text="─── 产品信息 ───", font=FONTS["small"],
             bg="white", fg="#999999").grid(row=row_idx, column=0, columnspan=2, pady=8)
    row_idx += 1

    # 产品信息
    from utils.helpers import format_spec, format_amount
    prod_rows = [
        ("产品类型", order.get("product_type", "")),
        ("材　　质", order.get("material", "") or "-"),
        ("规　　格", format_spec(order)),
        ("数　　量", f"{order.get('quantity', 0)} {order.get('unit', '米')}"),
        ("单　　价", f"¥{order.get('unit_price', 0)}"),
        ("总　　价", format_amount(order.get("total_amount", 0))),
        ("表面处理", order.get("surface_treatment", "") or "-"),
    ]
    # 产品备注（固定字段）
    if order.get("product_remark"):
        prod_rows.append(("产品备注", order.get("product_remark", "")))
    for label, val in prod_rows:
        tk.Label(card, text=label + "：", font=FONTS["body"], bg="white",
                anchor="w", width=10).grid(row=row_idx, column=0, padx=10, pady=3, sticky="w")
        tk.Label(card, text=val, font=FONTS["body"], bg="#F8F8F8",
                anchor="w", relief=tk.SUNKEN, padx=5).grid(row=row_idx, column=1, padx=(0, 10), pady=3, sticky="ew")
        row_idx += 1

    # 特殊要求
    if order.get("special_requirements"):
        tk.Label(card, text="特殊要求：", font=FONTS["body"], bg="white",
                anchor="w", width=10).grid(row=row_idx, column=0, padx=10, pady=3, sticky="nw")
        tk.Label(card, text=order.get("special_requirements", ""), font=FONTS["body"], bg="#FFF8E1",
                anchor="w", relief=tk.SUNKEN, padx=5, justify="left").grid(row=row_idx, column=1, padx=(0, 10), pady=3, sticky="ew")
        row_idx += 1

    # 备注
    if order.get("remark"):
        tk.Label(card, text="备　　注：", font=FONTS["body"], bg="white",
                anchor="w", width=10).grid(row=row_idx, column=0, padx=10, pady=3, sticky="nw")
        tk.Label(card, text=order.get("remark", ""), font=FONTS["body"], bg="#F5F5F5",
                anchor="w", relief=tk.SUNKEN, padx=5, justify="left").grid(row=row_idx, column=1, padx=(0, 10), pady=3, sticky="ew")

    # 自定义扩展参数（extra_params）
    extra_params = order.get("extra_params", {})
    if extra_params:
        tk.Label(card, text="─── 扩展参数 ───", font=FONTS["small"],
                 bg="white", fg="#9C27B0").grid(row=row_idx, column=0, columnspan=2, pady=(10, 4))
        row_idx += 1
        for k, v in extra_params.items():
            tk.Label(card, text=str(k) + "：", font=FONTS["body"], bg="white",
                    anchor="w", width=10).grid(row=row_idx, column=0, padx=10, pady=3, sticky="w")
            tk.Label(card, text=str(v), font=FONTS["body"], bg="#F3E5F5",
                    anchor="w", relief=tk.SUNKEN, padx=5).grid(row=row_idx, column=1, padx=(0, 10), pady=3, sticky="ew")
            row_idx += 1

    # 生产信息
    if production:
        prod_card = tk.Frame(content, bg="white", relief=tk.RAISED, bd=1)
        prod_card.pack(fill=tk.X, padx=15, pady=(0, 10), ipady=5)

        tk.Label(prod_card, text="─── 生产信息 ───", font=FONTS["small"],
                 bg="white", fg="#2196F3").grid(row=0, column=0, columnspan=2, pady=8)

        prod_info = [
            ("订单号", production.get("order_no", "")),
            ("生产优先级", str(production.get("priority", 5))),
            ("创建时间", str(production.get("created_at", ""))[:16] if production.get("created_at") else "-"),
        ]
        for i, (label, val) in enumerate(prod_info):
            tk.Label(prod_card, text=label + "：", font=FONTS["body"], bg="white",
                    anchor="w", width=10).grid(row=i+1, column=0, padx=10, pady=3, sticky="w")
            tk.Label(prod_card, text=val, font=FONTS["body"], bg="#E3F2FD",
                    anchor="w", relief=tk.SUNKEN, padx=5).grid(row=i+1, column=1, padx=(0, 10), pady=3, sticky="ew")

    # 按钮
    btn_frame = tk.Frame(content, bg=COLORS["bg_main"])
    btn_frame.pack(pady=15)
    ttk.Button(btn_frame, text="关闭", command=top.destroy, width=12).pack()

    top.update_idletasks()


class BaseDialog:
    """对话框抽象基类

    封装 Toplevel 创建、居中定位、模态设置、键盘绑定
    提供模板方法: _build_ui() / _validate() / _on_confirm() / _on_cancel() / _on_close()
    统一绑定 Enter → _handle_confirm / Escape → _handle_cancel

    用法:
        class MyDialog(BaseDialog):
            def _build_ui(self):
                tk.Label(self.window, text="内容").pack()

            def _validate(self):
                return (True, "")  # 或 (False, "错误信息")

            def _on_confirm(self):
                print("确认")
                self.window.destroy()
    """

    def __init__(self, parent, title="", width=400, height=300, resizable=True, topmost=False, window_key=None):
        self._parent = parent
        self._width = width
        self._height = height
        self._window_key = window_key or self.__class__.__name__

        self.window = tk.Toplevel(parent)
        self.window.title(title)
        self.window.transient(parent)
        self.window.grab_set()

        if resizable:
            setup_resizable_window(self.window, self._window_key, f"{width}x{height}")
            if topmost:
                self.window.attributes("-topmost", True)
        else:
            self.window.resizable(False, False)
            center_window(self.window, width, height, topmost=topmost)

        self.window.protocol("WM_DELETE_WINDOW", self._handle_close)
        self.window.bind("<Return>", self._handle_confirm)
        self.window.bind("<Escape>", self._handle_cancel)

        self._build_ui()

    # ─── 模板方法（子类覆写） ───

    def _build_ui(self):
        raise NotImplementedError("子类必须实现 _build_ui()")

    def _validate(self):
        return True, ""

    def _on_confirm(self):
        self.window.destroy()

    def _on_cancel(self):
        self.window.destroy()

    def _on_close(self):
        self.window.destroy()

    # ─── 事件处理（不建议覆写） ───

    def _handle_confirm(self, event=None):
        valid, msg = self._validate()
        if valid:
            self._on_confirm()
        else:
            alert(msg, "提示")

    def _handle_cancel(self, event=None):
        self._on_cancel()

    def _handle_close(self):
        self._on_close()
