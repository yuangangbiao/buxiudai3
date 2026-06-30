# -*- coding: utf-8 -*-
"""
独立数据库设置窗口
用于配置数据库连接，支持动态重载
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox


class DatabaseSettingsWindow:
    def __init__(self, parent=None, on_save_callback=None):
        self.on_save_callback = on_save_callback
        self.window = tk.Toplevel(parent) if parent else tk.Tk()
        self.window.title("数据库设置")
        self.window.geometry("500x400")
        self.window.resizable(False, False)

        if not parent:
            self.window.protocol("WM_DELETE_WINDOW", self.on_cancel)
        else:
            self.window.transient(parent)
            self.window.grab_set()

        self._setup_ui()
        self._load_current_config()

    def _setup_ui(self):
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = ttk.Label(main_frame, text="数据库连接配置",
                                font=("微软雅黑", 14, "bold"))
        title_label.pack(pady=(0, 20))

        form_frame = ttk.Frame(main_frame)
        form_frame.pack(fill=tk.X)

        row = 0
        ttk.Label(form_frame, text="主机地址：").grid(
            row=row, column=0, sticky=tk.E, padx=5, pady=8)
        self.host_var = tk.StringVar(value='localhost')
        host_entry = ttk.Entry(form_frame, textvariable=self.host_var, width=30)
        host_entry.grid(row=row, column=1, sticky=tk.W, padx=5, pady=8)

        row += 1
        ttk.Label(form_frame, text="端口：").grid(
            row=row, column=0, sticky=tk.E, padx=5, pady=8)
        self.port_var = tk.StringVar(value='3306')
        port_entry = ttk.Entry(form_frame, textvariable=self.port_var, width=15)
        port_entry.grid(row=row, column=1, sticky=tk.W, padx=5, pady=8)

        row += 1
        ttk.Label(form_frame, text="用户名：").grid(
            row=row, column=0, sticky=tk.E, padx=5, pady=8)
        self.user_var = tk.StringVar(value='root')
        user_entry = ttk.Entry(form_frame, textvariable=self.user_var, width=25)
        user_entry.grid(row=row, column=1, sticky=tk.W, padx=5, pady=8)

        row += 1
        ttk.Label(form_frame, text="密码：").grid(
            row=row, column=0, sticky=tk.E, padx=5, pady=8)
        self.pass_var = tk.StringVar(value='')
        pass_entry = ttk.Entry(form_frame, textvariable=self.pass_var, width=25, show="*")
        pass_entry.grid(row=row, column=1, sticky=tk.W, padx=5, pady=8)

        row += 1
        ttk.Label(form_frame, text="数据库名：").grid(
            row=row, column=0, sticky=tk.E, padx=5, pady=8)
        self.db_var = tk.StringVar(value='steel_belt')
        db_entry = ttk.Entry(form_frame, textvariable=self.db_var, width=25)
        db_entry.grid(row=row, column=1, sticky=tk.W, padx=5, pady=8)

        self.status_label = ttk.Label(main_frame, text="", foreground="blue")
        self.status_label.pack(pady=10)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=20)

        ttk.Button(btn_frame, text="测试连接", command=self._test_connection).pack(
            side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="保存并连接", command=self._save_and_connect).pack(
            side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="取消", command=self.on_cancel).pack(
            side=tk.LEFT, padx=10)

    def _get_project_root(self):
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _load_current_config(self):
        env_path = os.path.join(self._get_project_root(), '.env')
        if os.path.exists(env_path):
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if '=' in line:
                                key, value = line.split('=', 1)
                                if key == 'MYSQL_HOST':
                                    self.host_var.set(value)
                                elif key == 'MYSQL_PORT':
                                    self.port_var.set(value)
                                elif key == 'MYSQL_USER':
                                    self.user_var.set(value)
                                elif key == 'MYSQL_PASSWORD':
                                    self.pass_var.set(value)
                                elif key == 'MYSQL_DATABASE':
                                    self.db_var.set(value)
            except Exception as e:
                self.status_label.config(text=f"加载配置失败: {e}", foreground="red")

    def _test_connection(self):
        try:
            from core.db import get_direct_connection
            conn = get_direct_connection(
                host=self.host_var.get(),
                port=int(self.port_var.get()),
                user=self.user_var.get(),
                password=self.pass_var.get(),
                database=self.db_var.get(),
                charset='utf8mb4',
                connect_timeout=5
            )
            conn.close()
            self.status_label.config(text="✓ 连接成功！", foreground="green")
        except Exception as e:
            self.status_label.config(text=f"✗ 连接失败: {str(e)[:50]}", foreground="red")

    def _save_and_connect(self):
        env_content = f"""MYSQL_HOST={self.host_var.get()}
MYSQL_PORT={self.port_var.get()}
MYSQL_USER={self.user_var.get()}
MYSQL_PASSWORD={self.pass_var.get()}
MYSQL_DATABASE={self.db_var.get()}
"""
        env_path = os.path.join(self._get_project_root(), '.env')
        try:
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write(env_content)

            self._reload_database_config()

            if self.on_save_callback:
                success = self.on_save_callback()
                if success:
                    self.window.destroy()
                else:
                    self.status_label.config(text="配置已保存，但连接失败", foreground="orange")
            else:
                self.window.destroy()

        except Exception as e:
            messagebox.showerror("保存失败", f"保存配置失败：{str(e)}")

    def _reload_database_config(self):
        try:
            from models.database import reload_db_config
            reload_db_config()
            return True
        except ImportError:
            try:
                from dotenv import load_dotenv
                load_dotenv(os.path.join(self._get_project_root(), '.env'))
                from models.database import _reset_pool
                _reset_pool()
                return True
            except Exception as e:
                return False

    def on_cancel(self):
        self.window.destroy()

    def show(self):
        self.window.wait_window()


def open_database_settings(parent=None, on_save_callback=None):
    window = DatabaseSettingsWindow(parent, on_save_callback)
    window.show()
    return window


if __name__ == "__main__":
    app = DatabaseSettingsWindow()
    app.window.mainloop()
