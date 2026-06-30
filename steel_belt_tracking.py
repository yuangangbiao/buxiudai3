# -*- coding: utf-8 -*-
"""
Steel Belt Tracking - 样式设置模块
"""
import tkinter as tk
from tkinter import ttk
from config import COLORS, FONTS

def setup_styles():
    """设置应用样式"""
    style = ttk.Style()
    
    # 设置全局样式
    style.theme_use('clam')
    
    # 自定义样式
    style.configure("Main.TFrame", background=COLORS["bg_main"])
    style.configure("Card.TFrame", background=COLORS["bg_card"])
    
    # 按钮样式
    style.configure(
        "Primary.TButton",
        font=FONTS["body"],
        background=COLORS["primary"],
        foreground=COLORS["text_white"],
        padding=8,
        borderwidth=0,
        focusthickness=0
    )
    style.map(
        "Primary.TButton",
        background=[('active', COLORS["primary_light"])],
        foreground=[('active', COLORS["text_white"])]
    )
    
    # 标签样式
    style.configure(
        "Title.TLabel",
        font=FONTS["title"],
        foreground=COLORS["text_primary"],
        background=COLORS["bg_main"]
    )
    
    style.configure(
        "Body.TLabel",
        font=FONTS["body"],
        foreground=COLORS["text_secondary"],
        background=COLORS["bg_main"]
    )
    
    # 树视图样式
    style.configure(
        "Treeview",
        font=FONTS["body"],
        rowheight=28,
        background=COLORS["bg_card"],
        foreground=COLORS["text_primary"],
        fieldbackground=COLORS["bg_card"]
    )
    
    style.configure(
        "Treeview.Heading",
        font=FONTS["subtitle"],
        foreground=COLORS["text_primary"],
        background=COLORS["bg_card"]
    )
    
    # 输入框样式
    style.configure(
        "TEntry",
        font=FONTS["body"],
        padding=6,
        fieldbackground=COLORS["bg_card"],
        foreground=COLORS["text_primary"]
    )
    
    # 组合框样式
    style.configure(
        "TCombobox",
        font=FONTS["body"],
        padding=6,
        fieldbackground=COLORS["bg_card"],
        foreground=COLORS["text_primary"]
    )