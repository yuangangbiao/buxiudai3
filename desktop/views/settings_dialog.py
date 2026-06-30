# -*- coding: utf-8 -*-
"""
设置对话框 - 字体颜色设置界面
"""
import tkinter as tk
from tkinter import ttk, colorchooser, messagebox
from utils.settings_manager import settings_manager, DEFAULT_COLORS, DEFAULT_FONTS
from config import FONTS

PRESET_THEMES = {
    "默认蓝色": {
        "primary": "#1E3A5F",
        "primary_light": "#2E5A8F",
        "accent": "#4A90D9",
        "bg_main": "#F0F2F5",
        "bg_card": "#FFFFFF",
        "bg_sidebar": "#1E3A5F",
        "text_primary": "#1A1A2E",
        "text_secondary": "#666666",
        "text_white": "#FFFFFF",
        "success": "#4CAF50",
        "warning": "#FF9800",
        "danger": "#F44336",
        "info": "#2196F3",
        "table_header": "#F5F5F5",
        "table_row_odd": "#FFFFFF",
        "table_row_even": "#F9F9F9",
    },
    "科技深蓝": {
        "primary": "#0D2137",
        "primary_light": "#1A3A5C",
        "accent": "#00D4FF",
        "bg_main": "#E8F4F8",
        "bg_card": "#FFFFFF",
        "bg_sidebar": "#0D2137",
        "text_primary": "#0D2137",
        "text_secondary": "#5A6C7D",
        "text_white": "#FFFFFF",
        "success": "#00C853",
        "warning": "#FFAB00",
        "danger": "#FF5252",
        "info": "#00D4FF",
        "table_header": "#E8F4F8",
        "table_row_odd": "#FFFFFF",
        "table_row_even": "#F0F8FC",
    },
    "商务灰": {
        "primary": "#37474F",
        "primary_light": "#546E7A",
        "accent": "#78909C",
        "bg_main": "#F5F5F5",
        "bg_card": "#FFFFFF",
        "bg_sidebar": "#37474F",
        "text_primary": "#263238",
        "text_secondary": "#607D8B",
        "text_white": "#FFFFFF",
        "success": "#66BB6A",
        "warning": "#FFA726",
        "danger": "#EF5350",
        "info": "#42A5F5",
        "table_header": "#ECEFF1",
        "table_row_odd": "#FFFFFF",
        "table_row_even": "#F5F5F5",
    },
    "温暖橙": {
        "primary": "#E65100",
        "primary_light": "#FF7043",
        "accent": "#FF9800",
        "bg_main": "#FFF8E1",
        "bg_card": "#FFFFFF",
        "bg_sidebar": "#E65100",
        "text_primary": "#BF360C",
        "text_secondary": "#8D6E63",
        "text_white": "#FFFFFF",
        "success": "#4CAF50",
        "warning": "#FF9800",
        "danger": "#F44336",
        "info": "#2196F3",
        "table_header": "#FFF8E1",
        "table_row_odd": "#FFFFFF",
        "table_row_even": "#FFF3E0",
    },
    "自然绿": {
        "primary": "#2E7D32",
        "primary_light": "#43A047",
        "accent": "#66BB6A",
        "bg_main": "#E8F5E9",
        "bg_card": "#FFFFFF",
        "bg_sidebar": "#2E7D32",
        "text_primary": "#1B5E20",
        "text_secondary": "#66BB6A",
        "text_white": "#FFFFFF",
        "success": "#4CAF50",
        "warning": "#FFC107",
        "danger": "#E53935",
        "info": "#1E88E5",
        "table_header": "#E8F5E9",
        "table_row_odd": "#FFFFFF",
        "table_row_even": "#F1F8E9",
    },
    "深色模式": {
        "primary": "#1A237E",
        "primary_light": "#3949AB",
        "accent": "#5C6BC0",
        "bg_main": "#1A1A2E",
        "bg_card": "#16213E",
        "bg_sidebar": "#0F0F1A",
        "text_primary": "#E8E8E8",
        "text_secondary": "#888899",
        "text_white": "#FFFFFF",
        "success": "#4CAF50",
        "warning": "#FF9800",
        "danger": "#F44336",
        "info": "#2196F3",
        "table_header": "#16213E",
        "table_row_odd": "#1A1A2E",
        "table_row_even": "#16213E",
    },
}

def show_settings_dialog(parent):
    """显示设置对话框"""
    dialog = tk.Toplevel(parent)
    dialog.title("系统设置")
    dialog.geometry("800x650")
    dialog.resizable(True, True)
    
    def on_close():
        dialog.destroy()
    
    dialog.protocol("WM_DELETE_WINDOW", on_close)
    
    main_frame = ttk.Notebook(dialog)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    colors = settings_manager.get_all_colors()
    
    theme_frame = ttk.Frame(main_frame)
    main_frame.add(theme_frame, text="主题预设")
    init_theme_settings(theme_frame, dialog)
    
    color_frame = ttk.Frame(main_frame)
    main_frame.add(color_frame, text="自定义颜色")
    init_color_settings(color_frame, colors)
    
    font_frame = ttk.Frame(main_frame)
    main_frame.add(font_frame, text="字体设置")
    init_font_settings(font_frame)
    
    db_frame = ttk.Frame(main_frame)
    main_frame.add(db_frame, text="数据库连接")
    init_database_settings(db_frame, dialog)
    
    container_frame = ttk.Frame(main_frame)
    main_frame.add(container_frame, text="容器中心")
    init_container_settings(container_frame, dialog)
    
    btn_frame = tk.Frame(dialog, bg="#F5F5F5")
    btn_frame.pack(fill=tk.X, padx=10, pady=10)
    
    def reset_to_default():
        settings_manager.reset_to_default()
        on_close()
    
    def apply_settings():
        fonts = settings_manager.get_all_fonts()
        fonts["family"] = font_family_var.get()
        for key in ["title", "subtitle", "body", "small", "large"]:
            var = font_size_vars.get(key)
            if var:
                fonts["size"][key] = var.get()
        settings_manager.save_settings()
    
    def save_and_close():
        apply_settings()
        on_close()
    
    ttk.Button(btn_frame, text="重置默认", command=reset_to_default).pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="应用", command=apply_settings).pack(side=tk.RIGHT, padx=5)
    ttk.Button(btn_frame, text="确定", command=save_and_close).pack(side=tk.RIGHT, padx=5)
    ttk.Button(btn_frame, text="取消", command=on_close).pack(side=tk.RIGHT, padx=5)
    
    dialog.focus_set()
    parent.wait_window(dialog)

def init_theme_settings(parent, dialog):
    canvas = tk.Canvas(parent)
    scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    scroll_frame = ttk.Frame(canvas)
    
    scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    ttk.Label(scroll_frame, text="选择预设主题：", font=FONTS["normal_bold"]).grid(
        row=0, column=0, columnspan=3, sticky="w", padx=15, pady=(15, 10))
    
    row = 1
    col = 0
    theme_list = list(PRESET_THEMES.items())
    
    def apply_theme(index):
        theme_name, theme_colors = theme_list[index]
        for key, value in theme_colors.items():
            settings_manager.set_color(key, value)
        
        fonts = settings_manager.get_all_fonts()
        fonts["family"] = font_family_var.get()
        for key in ["title", "subtitle", "body", "small", "large"]:
            var = font_size_vars.get(key)
            if var:
                fonts["size"][key] = var.get()
        settings_manager.save_settings()
        
        messagebox.showinfo("主题应用成功", f"已应用「{theme_name}」主题", parent=dialog)
    
    for i, (theme_name, theme_colors) in enumerate(theme_list):
        card = ttk.Frame(scroll_frame, borderwidth=2, relief="groove", padding=10)
        card.grid(row=row, column=col, padx=10, pady=10)
        
        ttk.Label(card, text=theme_name, font=FONTS["normal_bold"]).pack(pady=(0, 8))
        
        color_bar = tk.Frame(card, height=40)
        color_bar.pack(fill=tk.X, pady=(0, 8))
        
        tk.Button(color_bar, bg=theme_colors["primary"], width=8, height=2, bd=0).pack(side=tk.LEFT, padx=1)
        tk.Button(color_bar, bg=theme_colors["accent"], width=6, height=2, bd=0).pack(side=tk.LEFT, padx=1)
        tk.Button(color_bar, bg=theme_colors["bg_main"], width=6, height=2, bd=1, relief="solid").pack(side=tk.LEFT, padx=1)
        tk.Button(color_bar, bg=theme_colors["text_primary"], width=6, height=2, bd=1, relief="solid").pack(side=tk.LEFT, padx=1)
        
        ttk.Button(card, text="应用", command=lambda idx=i: apply_theme(idx)).pack()
        
        col += 1
        if col >= 2:
            col = 0
            row += 1

def init_color_settings(parent, colors):
    canvas = tk.Canvas(parent)
    scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    scroll_frame = ttk.Frame(canvas)
    
    scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    ttk.Label(scroll_frame, text="自定义各项颜色：", font=FONTS["normal_bold"]).grid(
        row=0, column=0, columnspan=4, sticky="w", padx=15, pady=(15, 10))
    
    labels = {
        "primary": "主色",
        "primary_light": "主色亮",
        "accent": "强调色",
        "bg_main": "主背景",
        "bg_card": "卡片背景",
        "bg_sidebar": "侧边栏",
        "text_primary": "主文字",
        "text_secondary": "次要文字",
        "text_white": "白色文字",
        "success": "成功",
        "warning": "警告",
        "danger": "危险",
        "info": "信息",
        "table_header": "表头",
        "table_row_odd": "奇数行",
        "table_row_even": "偶数行",
    }
    
    groups = {
        "主色调": ["primary", "primary_light", "accent"],
        "背景色": ["bg_main", "bg_card", "bg_sidebar"],
        "文字颜色": ["text_primary", "text_secondary", "text_white"],
        "状态颜色": ["success", "warning", "danger", "info"],
        "表格颜色": ["table_header", "table_row_odd", "table_row_even"],
    }
    
    def choose_color(key, button):
        current_color = settings_manager.get_color(key)
        color = colorchooser.askcolor(title=f"选择 {labels.get(key, key)} 颜色", initialcolor=current_color)
        if color[1]:
            button.configure(bg=color[1])
            settings_manager.set_color(key, color[1])
    
    row = 1
    for group_name, color_keys in groups.items():
        ttk.Label(scroll_frame, text=group_name, font=FONTS["normal_bold"]).grid(
            row=row, column=0, columnspan=4, sticky="w", pady=(15, 8), padx=10)
        row += 1
        
        col = 0
        for key in color_keys:
            frame = ttk.Frame(scroll_frame, borderwidth=1, relief="groove", padding=5)
            frame.grid(row=row, column=col, padx=8, pady=5)
            
            color = colors.get(key, DEFAULT_COLORS.get(key, "#000000"))
            
            btn = tk.Button(frame, bg=color, width=12, height=3, bd=2, relief="solid")
            btn.config(command=lambda k=key, b=btn: choose_color(k, b))
            btn.pack(padx=5, pady=5)
            
            ttk.Label(frame, text=labels.get(key, key), font=FONTS["small"]).pack(pady=2)
            
            col += 1
            if col >= 4:
                col = 0
                row += 1
        if col > 0:
            row += 1

font_family_var = None
font_size_vars = {}

def init_font_settings(parent):
    global font_family_var
    fonts = settings_manager.get_all_fonts()
    
    canvas = tk.Canvas(parent)
    scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    scroll_frame = ttk.Frame(canvas)
    
    scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    row = 0
    ttk.Label(scroll_frame, text="字体名称：", font=FONTS["body"]).grid(
        row=row, column=0, sticky="e", padx=15, pady=(15, 10))
    font_family_var = tk.StringVar(value=fonts["family"])
    font_combo = ttk.Combobox(scroll_frame, textvariable=font_family_var, 
                               values=["微软雅黑", "宋体", "黑体", "Arial", "Times New Roman", "楷体", "仿宋"],
                               state="readonly", width=20)
    font_combo.grid(row=row, column=1, sticky="w", padx=15, pady=(15, 10))
    
    row += 1
    ttk.Label(scroll_frame, text="字体大小设置：", font=FONTS["normal_bold"]).grid(
        row=row, column=0, columnspan=2, sticky="w", padx=15, pady=(20, 10))
    
    size_types = [("标题", "title"), ("副标题", "subtitle"), ("正文", "body"), ("小号", "small"), ("大号", "large")]
    
    for label, key in size_types:
        row += 1
        ttk.Label(scroll_frame, text=label + "：", font=FONTS["body"]).grid(
            row=row, column=0, sticky="e", padx=15, pady=8)
        
        var = tk.IntVar(value=fonts["size"][key])
        font_size_vars[key] = var
        
        spinbox = ttk.Spinbox(scroll_frame, from_=8, to=36, textvariable=var, width=8)
        spinbox.grid(row=row, column=1, sticky="w", padx=15, pady=8)
        ttk.Label(scroll_frame, text="pt").grid(row=row, column=2, sticky="w", padx=5)

def init_database_settings(parent, dialog):
    """初始化数据库连接设置界面"""
    import os
    
    canvas = tk.Canvas(parent)
    scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    scroll_frame = ttk.Frame(canvas)
    
    scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    row = 0
    ttk.Label(scroll_frame, text="数据库连接配置", font=FONTS["heading"]).grid(
        row=row, column=0, columnspan=3, sticky="w", padx=15, pady=(15, 15))
    
    row += 1
    ttk.Label(scroll_frame, text="数据库类型：", font=FONTS["body"]).grid(
        row=row, column=0, sticky="e", padx=15, pady=8)
    db_type_var = tk.StringVar(value="MySQL")
    db_type_combo = ttk.Combobox(scroll_frame, textvariable=db_type_var,
                                  values=["MySQL"], state="readonly", width=25)
    db_type_combo.grid(row=row, column=1, sticky="w", padx=15, pady=8)
    
    row += 1
    ttk.Label(scroll_frame, text="主机地址：", font=FONTS["body"]).grid(
        row=row, column=0, sticky="e", padx=15, pady=8)
    host_var = tk.StringVar(value=os.getenv('MYSQL_HOST', 'localhost'))
    host_entry = ttk.Entry(scroll_frame, textvariable=host_var, width=30)
    host_entry.grid(row=row, column=1, sticky="w", padx=15, pady=8)
    
    row += 1
    ttk.Label(scroll_frame, text="端口：", font=FONTS["body"]).grid(
        row=row, column=0, sticky="e", padx=15, pady=8)
    port_var = tk.StringVar(value=str(os.getenv('MYSQL_PORT', 3306)))
    port_entry = ttk.Entry(scroll_frame, textvariable=port_var, width=15)
    port_entry.grid(row=row, column=1, sticky="w", padx=15, pady=8)
    
    row += 1
    ttk.Label(scroll_frame, text="用户名：", font=FONTS["body"]).grid(
        row=row, column=0, sticky="e", padx=15, pady=8)
    user_var = tk.StringVar(value=os.getenv('MYSQL_USER', 'root'))
    user_entry = ttk.Entry(scroll_frame, textvariable=user_var, width=25)
    user_entry.grid(row=row, column=1, sticky="w", padx=15, pady=8)
    
    row += 1
    ttk.Label(scroll_frame, text="密码：", font=FONTS["body"]).grid(
        row=row, column=0, sticky="e", padx=15, pady=8)
    pass_var = tk.StringVar(value=os.getenv('MYSQL_PASSWORD', ''))
    pass_entry = ttk.Entry(scroll_frame, textvariable=pass_var, width=25, show="*")
    pass_entry.grid(row=row, column=1, sticky="w", padx=15, pady=8)
    
    row += 1
    ttk.Label(scroll_frame, text="数据库名：", font=FONTS["body"]).grid(
        row=row, column=0, sticky="e", padx=15, pady=8)
    db_var = tk.StringVar(value=os.getenv('MYSQL_DATABASE', 'steel_belt'))
    db_entry = ttk.Entry(scroll_frame, textvariable=db_var, width=25)
    db_entry.grid(row=row, column=1, sticky="w", padx=15, pady=8)
    
    row += 2
    btn_frame = ttk.Frame(scroll_frame)
    btn_frame.grid(row=row, column=0, columnspan=2, pady=20)
    
    def test_connection():
        try:
            from core.db import get_direct_connection
            conn = get_direct_connection(
                host=host_var.get(),
                port=int(port_var.get()),
                user=user_var.get(),
                password=pass_var.get(),
                database=db_var.get(),
                charset='utf8mb4'
            )
            conn.close()
            messagebox.showinfo("连接测试", "数据库连接成功！", parent=dialog)
        except Exception as e:
            messagebox.showerror("连接失败", f"数据库连接失败：{str(e)}", parent=dialog)
    
    def save_db_settings():
        env_content = f"""MYSQL_HOST={host_var.get()}
MYSQL_PORT={port_var.get()}
MYSQL_USER={user_var.get()}
MYSQL_PASSWORD={pass_var.get()}
MYSQL_DATABASE={db_var.get()}
"""
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
        try:
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write(env_content)
            messagebox.showinfo("保存成功", "数据库配置已保存到 .env 文件\n需要重启应用才能生效", parent=dialog)
        except Exception as e:
            messagebox.showerror("保存失败", f"保存配置失败：{str(e)}", parent=dialog)
    
    ttk.Button(btn_frame, text="测试连接", command=test_connection).pack(side=tk.LEFT, padx=10)
    ttk.Button(btn_frame, text="保存配置", command=save_db_settings).pack(side=tk.LEFT, padx=10)
    
    row += 1
    hint_label = ttk.Label(scroll_frame, text="⚠️  注意：修改数据库配置后需要重启应用才能生效",
                           font=FONTS["small"], foreground="#E65100")
    hint_label.grid(row=row, column=0, columnspan=2, sticky="w", padx=15)

def init_container_settings(parent, dialog):
    """初始化容器中心连接设置界面"""
    import os
    
    canvas = tk.Canvas(parent)
    scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    scroll_frame = ttk.Frame(canvas)
    
    scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    row = 0
    ttk.Label(scroll_frame, text="容器中心连接配置", font=FONTS["heading"]).grid(
        row=row, column=0, columnspan=3, sticky="w", padx=15, pady=(15, 15))
    
    row += 1
    ttk.Label(scroll_frame, text="容器服务地址：", font=FONTS["body"]).grid(
        row=row, column=0, sticky="e", padx=15, pady=8)
    container_url_var = tk.StringVar(value=os.getenv('CONTAINER_URL', 'http://localhost:5002'))
    container_url_entry = ttk.Entry(scroll_frame, textvariable=container_url_var, width=40)
    container_url_entry.grid(row=row, column=1, sticky="w", padx=15, pady=8)
    
    row += 1
    ttk.Label(scroll_frame, text="容器API密钥：", font=FONTS["body"]).grid(
        row=row, column=0, sticky="e", padx=15, pady=8)
    container_key_var = tk.StringVar(value=os.getenv('CONTAINER_API_KEY', ''))
    container_key_entry = ttk.Entry(scroll_frame, textvariable=container_key_var, width=40)
    container_key_entry.grid(row=row, column=1, sticky="w", padx=15, pady=8)
    
    row += 1
    ttk.Label(scroll_frame, text="超时时间（秒）：", font=FONTS["body"]).grid(
        row=row, column=0, sticky="e", padx=15, pady=8)
    timeout_var = tk.StringVar(value=os.getenv('CONTAINER_TIMEOUT', '30'))
    timeout_entry = ttk.Entry(scroll_frame, textvariable=timeout_var, width=10)
    timeout_entry.grid(row=row, column=1, sticky="w", padx=15, pady=8)
    
    row += 2
    btn_frame = ttk.Frame(scroll_frame)
    btn_frame.grid(row=row, column=0, columnspan=2, pady=20)
    
    def test_container_connection():
        import requests
        try:
            url = container_url_var.get().rstrip('/') + '/api/health'
            response = requests.get(url, timeout=int(timeout_var.get()))
            if response.status_code == 200:
                messagebox.showinfo("连接测试", "容器中心连接成功！", parent=dialog)
            else:
                messagebox.showerror("连接失败", f"容器中心返回错误：{response.status_code}", parent=dialog)
        except requests.exceptions.RequestException as e:
            messagebox.showerror("连接失败", f"无法连接到容器中心：{str(e)}", parent=dialog)
    
    def save_container_settings():
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
        try:
            if os.path.exists(env_path):
                with open(env_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            else:
                lines = []
            
            new_lines = []
            env_vars = {
                'CONTAINER_URL': container_url_var.get(),
                'CONTAINER_API_KEY': container_key_var.get(),
                'CONTAINER_TIMEOUT': timeout_var.get()
            }
            
            for line in lines:
                key = line.split('=')[0] if '=' in line else ''
                if key in env_vars:
                    new_lines.append(f"{key}={env_vars[key]}\n")
                    del env_vars[key]
                else:
                    new_lines.append(line)
            
            for key, value in env_vars.items():
                new_lines.append(f"{key}={value}\n")
            
            with open(env_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            messagebox.showinfo("保存成功", "容器中心配置已保存\n需要重启应用才能生效", parent=dialog)
        except Exception as e:
            messagebox.showerror("保存失败", f"保存配置失败：{str(e)}", parent=dialog)
    
    ttk.Button(btn_frame, text="测试连接", command=test_container_connection).pack(side=tk.LEFT, padx=10)
    ttk.Button(btn_frame, text="保存配置", command=save_container_settings).pack(side=tk.LEFT, padx=10)
    
    row += 1
    hint_label = ttk.Label(scroll_frame, text="⚠️  注意：修改容器配置后需要重启应用才能生效",
                           font=FONTS["small"], foreground="#E65100")
    hint_label.grid(row=row, column=0, columnspan=2, sticky="w", padx=15)

    row += 2
    ttk.Separator(scroll_frame, orient='horizontal').grid(row=row, column=0, columnspan=2, sticky='ew', padx=15, pady=10)

    row += 1
    ttk.Label(scroll_frame, text="自动发布设置", font=FONTS["normal_bold"]).grid(
        row=row, column=0, columnspan=2, sticky="w", padx=15, pady=(10, 5))

    row += 1
    auto_publish_var = tk.BooleanVar(value=os.getenv('AUTO_PUBLISH_ORDER', '0') == '1')
    ttk.Checkbutton(scroll_frame, text="订单确认后自动发布任务到调度中心",
                    variable=auto_publish_var,
                    command=lambda: _save_auto_publish_setting(auto_publish_var.get())
                   ).grid(row=row, column=0, columnspan=2, sticky="w", padx=15, pady=5)

    row += 1
    ttk.Label(scroll_frame, text="（开启后，订单确认时自动发布排产任务，任务内容隐藏客户信息）",
              font=FONTS["small"], foreground="#666666").grid(
        row=row, column=0, columnspan=2, sticky="w", padx=35, pady=(0, 5))

    def _save_auto_publish_setting(enabled):
        try:
            env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
            if os.path.exists(env_path):
                with open(env_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            else:
                lines = []

            new_lines = []
            found = False
            for line in lines:
                key = line.split('=')[0] if '=' in line else ''
                if key == 'AUTO_PUBLISH_ORDER':
                    new_lines.append(f"AUTO_PUBLISH_ORDER={'1' if enabled else '0'}\n")
                    found = True
                else:
                    new_lines.append(line)

            if not found:
                new_lines.append(f"AUTO_PUBLISH_ORDER={'1' if enabled else '0'}\n")

            with open(env_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
        except Exception as e:
            messagebox.showerror("保存失败", f"保存自动发布设置失败：{str(e)}", parent=dialog)

    row += 2
    ttk.Label(scroll_frame, text="容器服务状态：", font=FONTS["normal_bold"]).grid(
        row=row, column=0, sticky="w", padx=15, pady=(15, 10))
    
    row += 1
    status_frame = ttk.Frame(scroll_frame, borderwidth=1, relief="groove", padding=15)
    status_frame.grid(row=row, column=0, columnspan=2, sticky="w", padx=15, pady=5)
    
    status_vars = {
        'version': tk.StringVar(value="未知"),
        'status': tk.StringVar(value="未检查"),
        'containers': tk.StringVar(value="0"),
        'active_tasks': tk.StringVar(value="0")
    }
    
    def refresh_status():
        import requests
        try:
            url = container_url_var.get().rstrip('/') + '/api/status'
            response = requests.get(url, timeout=int(timeout_var.get()))
            if response.status_code == 200:
                data = response.json()
                status_vars['version'].set(data.get('version', '未知'))
                status_vars['status'].set(data.get('status', '运行中'))
                status_vars['containers'].set(str(data.get('containers', 0)))
                status_vars['active_tasks'].set(str(data.get('active_tasks', 0)))
                messagebox.showinfo("状态刷新", "容器状态已更新", parent=dialog)
            else:
                messagebox.showerror("获取状态失败", f"HTTP错误：{response.status_code}", parent=dialog)
        except Exception as e:
            messagebox.showerror("获取状态失败", f"无法获取容器状态：{str(e)}", parent=dialog)
    
    ttk.Button(status_frame, text="🔄 刷新状态", command=refresh_status).grid(
        row=0, column=0, columnspan=4, pady=(0, 10))
    
    status_items = [
        ("版本", 'version'),
        ("状态", 'status'),
        ("容器数量", 'containers'),
        ("活跃任务", 'active_tasks')
    ]
    
    status_col = 0
    for label, key in status_items:
        ttk.Label(status_frame, text=f"{label}：", font=FONTS["body"]).grid(
            row=1, column=status_col*2, sticky="e", padx=5)
        ttk.Label(status_frame, textvariable=status_vars[key], 
                  font=FONTS["normal_bold"], foreground="#2E7D32").grid(
            row=1, column=status_col*2+1, sticky="w", padx=5)
        status_col += 1