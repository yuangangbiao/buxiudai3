# -*- coding: utf-8 -*-
"""
自定义组件
"""
import tkinter as tk
from tkinter import ttk


class PlaceholderEntry(ttk.Entry):
    """带占位提示的输入框"""

    def __init__(self, parent, placeholder="", **kwargs):
        super().__init__(parent, **kwargs)
        self.placeholder = placeholder
        self.placeholder_color = "#AAAAAA"
        self.default_color = self.cget("foreground")

        if placeholder:
            self._show_placeholder()

        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)

    def _show_placeholder(self):
        if not self.get():
            self.insert(0, self.placeholder)
            self.config(foreground=self.placeholder_color)

    def _on_focus_in(self, event):
        if self.get() == self.placeholder:
            self.delete(0, tk.END)
            self.config(foreground=self.default_color)

    def _on_focus_out(self, event):
        if not self.get():
            self._show_placeholder()

    def get_value(self):
        """获取实际值（过滤占位文字）"""
        value = self.get()
        if value == self.placeholder:
            return ""
        return value

    def set_value(self, value):
        """设置值"""
        self.delete(0, tk.END)
        if value:
            self.insert(0, value)
            self.config(foreground=self.default_color)
