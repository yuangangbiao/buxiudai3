# -*- coding: utf-8 -*-
"""
可视化大屏启动器 - UI面板
工厂大屏显示模块，提供图形界面管理服务器
支持系统托盘运行，隐藏到右下角
"""
import os
import sys
import webbrowser
import threading
import socket
import time
import json
import tkinter as tk
from tkinter import ttk, messagebox
import logging

logger = logging.getLogger(__name__)

try:
    from pystray import Icon, Menu, MenuItem
    from PIL import Image, ImageDraw
    PYSTRAY_AVAILABLE = True
except ImportError:
    PYSTRAY_AVAILABLE = False
    logger.warning("pystray not available, system tray will be disabled")

if getattr(sys, 'frozen', False):
    APP_DIR = sys._MEIPASS
    USER_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    USER_DIR = APP_DIR

sys.path.insert(0, os.path.dirname(APP_DIR) if APP_DIR != USER_DIR else APP_DIR)

APP_NAME = "不锈钢输送网带跟单系统"

DEFAULT_PORT = 5000
DEFAULT_HOST = "0.0.0.0"
CONFIG_FILE = os.path.join(USER_DIR, "launcher_config.json")
DB_CONFIG_FILE = os.path.join(USER_DIR, "db_config.json")


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class DashboardLauncherUI:
    """可视化大屏启动器UI"""

    def __init__(self):
        self.port = DEFAULT_PORT
        self.host = DEFAULT_HOST
        self.server_thread = None
        self.server_running = False
        self.local_ip = get_local_ip()
        self.config = self._load_config()
        self.tray_icon = None
        self.is_hidden_to_tray = False

        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} - 可视化大屏启动器")
        self.root.geometry(self.config.get("geometry", "520x500"))
        self.root.minsize(480, 460)
        self.root.configure(bg="#1a1a2e")
        self.root.resizable(True, True)

        self.host_var = tk.StringVar(value=self.config.get("host", DEFAULT_HOST))
        self.port_var = tk.StringVar(value=str(self.config.get("port", DEFAULT_PORT)))

        self.db_config = self._load_db_config()

        self._center_window()
        self._setup_ui()
        self._update_status()
        self.root.bind("<Configure>", self._on_resize)

        if PYSTRAY_AVAILABLE:
            self._setup_tray()
        else:
            logger.info("System tray disabled - pystray not installed")

    def _load_db_config(self):
        try:
            if os.path.exists(DB_CONFIG_FILE):
                with open(DB_CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {"host": "localhost", "port": 3306, "database": "steel_belt", "user": "root", "password": ""}

    def _save_db_config(self):
        try:
            with open(DB_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.db_config, f, ensure_ascii=False)
            return True
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败: {e}")
            return False

    def _show_db_settings(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("数据库配置")
        dialog.geometry("450x350")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg="#1a1a2e")

        frame = tk.Frame(dialog, bg="#1a1a2e", padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="🗄️ 数据库连接配置", font=("Microsoft YaHei", 14, "bold"),
                bg="#1a1a2e", fg="#00d4ff").pack(pady=(0, 15))

        db_frame = tk.Frame(frame, bg="#16213e", padx=15, pady=15)
        db_frame.pack(fill=tk.X, pady=10)

        tk.Label(db_frame, text="服务器地址:", font=("Microsoft YaHei", 10),
                bg="#16213e", fg="#e0e0e0", width=12, anchor="w").grid(row=0, column=0, pady=8, sticky="w")
        entry_host = ttk.Entry(db_frame, width=25, font=("Microsoft YaHei", 10))
        entry_host.insert(0, self.db_config.get("host", "localhost"))
        entry_host.grid(row=0, column=1, pady=8, padx=10, sticky="w")

        tk.Label(db_frame, text="端口:", font=("Microsoft YaHei", 10),
                bg="#16213e", fg="#e0e0e0", width=12, anchor="w").grid(row=1, column=0, pady=8, sticky="w")
        entry_port = ttk.Entry(db_frame, width=25, font=("Microsoft YaHei", 10))
        entry_port.insert(0, str(self.db_config.get("port", 3306)))
        entry_port.grid(row=1, column=1, pady=8, padx=10, sticky="w")

        tk.Label(db_frame, text="数据库名:", font=("Microsoft YaHei", 10),
                bg="#16213e", fg="#e0e0e0", width=12, anchor="w").grid(row=2, column=0, pady=8, sticky="w")
        entry_db = ttk.Entry(db_frame, width=25, font=("Microsoft YaHei", 10))
        entry_db.insert(0, self.db_config.get("database", "steel_belt"))
        entry_db.grid(row=2, column=1, pady=8, padx=10, sticky="w")

        tk.Label(db_frame, text="用户名:", font=("Microsoft YaHei", 10),
                bg="#16213e", fg="#e0e0e0", width=12, anchor="w").grid(row=3, column=0, pady=8, sticky="w")
        entry_user = ttk.Entry(db_frame, width=25, font=("Microsoft YaHei", 10))
        entry_user.insert(0, self.db_config.get("user", "root"))
        entry_user.grid(row=3, column=1, pady=8, padx=10, sticky="w")

        tk.Label(db_frame, text="密码:", font=("Microsoft YaHei", 10),
                bg="#16213e", fg="#e0e0e0", width=12, anchor="w").grid(row=4, column=0, pady=8, sticky="w")
        entry_pass = ttk.Entry(db_frame, show="*", width=25, font=("Microsoft YaHei", 10))
        entry_pass.insert(0, self.db_config.get("password", ""))
        entry_pass.grid(row=4, column=1, pady=8, padx=10, sticky="w")

        info_label = tk.Label(frame, text="💡 配置将保存到 db_config.json 文件",
                            font=("Microsoft YaHei", 9), bg="#1a1a2e", fg="#666666")
        info_label.pack(pady=(10, 0))

        btn_frame = tk.Frame(frame, bg="#1a1a2e")
        btn_frame.pack(pady=15)

        def do_save():
            self.db_config = {
                "host": entry_host.get().strip(),
                "port": int(entry_port.get().strip() or 3306),
                "database": entry_db.get().strip(),
                "user": entry_user.get().strip(),
                "password": entry_pass.get()
            }
            if self._save_db_config():
                self._update_db_env()
                messagebox.showinfo("成功", "数据库配置已保存！")
                dialog.destroy()

        tk.Button(btn_frame, text="💾 保存", font=("Microsoft YaHei", 11, "bold"),
                 bg="#27ae60", fg="white", bd=0, padx=25, pady=8,
                 activebackground="#219a52", command=do_save).pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="取消", font=("Microsoft YaHei", 11),
                 bg="#555555", fg="white", bd=0, padx=25, pady=8,
                 activebackground="#444444", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def _update_db_env(self):
        os.environ['MYSQL_HOST'] = self.db_config.get("host", "localhost")
        os.environ['MYSQL_PORT'] = str(self.db_config.get("port", 3306))
        os.environ['MYSQL_DATABASE'] = self.db_config.get("database", "steel_belt")
        os.environ['MYSQL_USER'] = self.db_config.get("user", "root")
        os.environ['MYSQL_PASSWORD'] = self.db_config.get("password", "")

    def _load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {"geometry": "520x500", "host": DEFAULT_HOST, "port": DEFAULT_PORT}

    def _save_config(self):
        try:
            geom = self.root.geometry()
            if "+" in geom:
                parts = geom.split("+")
                self.config["geometry"] = parts[0]
            else:
                self.config["geometry"] = geom
            self.config["host"] = self.host_var.get()
            self.config["port"] = int(self.port_var.get())
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False)
        except Exception:
            pass

    def _center_window(self):
        saved_geometry = self.config.get("geometry", "520x500")
        if "+" not in saved_geometry:
            self.root.geometry(saved_geometry)
            self.root.update_idletasks()
            width = self.root.winfo_width()
            height = self.root.winfo_height()
        else:
            parts = saved_geometry.split("+")
            if len(parts) >= 3:
                width = int(parts[0]) if parts[0].isdigit() else 520
                height = int(parts[1]) if parts[1].isdigit() else 500
            else:
                width = 520
                height = 500

        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _on_resize(self, event):
        if event.widget == self.root:
            if hasattr(self, '_setup_complete') and self._setup_complete:
                self.root.after(100, self._save_config)

    def _setup_ui(self):
        self.root.style = ttk.Style()
        self.root.style.theme_use('clam')

        main_canvas = tk.Canvas(self.root, bg="#1a1a2e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=main_canvas.yview)
        scrollable_frame = tk.Frame(main_canvas, bg="#1a1a2e")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )
        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)

        header_frame = tk.Frame(scrollable_frame, bg="#16213e", padx=20, pady=15)
        header_frame.pack(fill=tk.X)

        tk.Label(header_frame, text="🏭",
                font=("Microsoft YaHei", 28),
                bg="#16213e", fg="#00d4ff").pack(side=tk.LEFT, padx=(0, 10))

        title_frame = tk.Frame(header_frame, bg="#16213e")
        title_frame.pack(side=tk.LEFT)

        tk.Label(title_frame, text="可视化大屏启动器",
                font=("Microsoft YaHei", 18, "bold"),
                bg="#16213e", fg="#00d4ff").pack(anchor="w")

        tk.Label(title_frame, text="工厂生产监控大屏管理",
                font=("Microsoft YaHei", 10),
                bg="#16213e", fg="#4a7fa5").pack(anchor="w")

        card_frame = tk.Frame(scrollable_frame, bg="#1a1a2e", padx=20, pady=10)
        card_frame.pack(fill=tk.BOTH, expand=True)

        status_card = tk.Frame(card_frame, bg="#16213e", bd=0, relief=tk.FLAT)
        status_card.pack(fill=tk.X, pady=(0, 15))

        tk.Label(status_card, text="📊 服务器状态",
                font=("Microsoft YaHei", 12, "bold"),
                bg="#16213e", fg="#00d4ff").pack(anchor="w", padx=20, pady=(15, 10))

        self.status_label = tk.Label(status_card, text="● 已停止",
                                     font=("Microsoft YaHei", 24, "bold"),
                                     bg="#16213e", fg="#e74c3c")
        self.status_label.pack(anchor="w", padx=20, pady=(0, 15))

        settings_card = tk.Frame(card_frame, bg="#16213e", bd=0, relief=tk.FLAT)
        settings_card.pack(fill=tk.X, pady=(0, 15))

        tk.Label(settings_card, text="⚙️ 服务器设置",
                font=("Microsoft YaHei", 12, "bold"),
                bg="#16213e", fg="#00d4ff").pack(anchor="w", padx=20, pady=(15, 10))

        settings_inner = tk.Frame(settings_card, bg="#16213e")
        settings_inner.pack(fill=tk.X, padx=20, pady=(0, 15))

        tk.Label(settings_inner, text="服务器地址:",
                font=("Microsoft YaHei", 11),
                bg="#16213e", fg="#e0e0e0", width=12, anchor="w").grid(row=0, column=0, pady=8, sticky="w")

        host_entry = ttk.Entry(settings_inner, textvariable=self.host_var, width=18, font=("Microsoft YaHei", 11))
        host_entry.grid(row=0, column=1, pady=8, padx=(10, 0), sticky="w")

        tk.Label(settings_inner, text="(默认: 0.0.0.0)",
                font=("Microsoft YaHei", 9),
                bg="#16213e", fg="#666666").grid(row=0, column=2, pady=8, padx=(10, 0), sticky="w")

        tk.Label(settings_inner, text="端口号:",
                font=("Microsoft YaHei", 11),
                bg="#16213e", fg="#e0e0e0", width=12, anchor="w").grid(row=1, column=0, pady=8, sticky="w")

        port_entry = ttk.Entry(settings_inner, textvariable=self.port_var, width=12, font=("Microsoft YaHei", 11))
        port_entry.grid(row=1, column=1, pady=8, padx=(10, 0), sticky="w")

        tk.Label(settings_inner, text="(默认: 5000)",
                font=("Microsoft YaHei", 9),
                bg="#16213e", fg="#666666").grid(row=1, column=2, pady=8, padx=(10, 0), sticky="w")

        db_btn = tk.Button(settings_card, text="🗄️ 数据库设置",
                          font=("Microsoft YaHei", 10),
                          bg="#9b59b6", fg="white", bd=0, padx=15, pady=8,
                          activebackground="#8e44ad",
                          command=self._show_db_settings)
        db_btn.pack(anchor="w", padx=20, pady=(0, 15))

        url_card = tk.Frame(card_frame, bg="#16213e", bd=0, relief=tk.FLAT)
        url_card.pack(fill=tk.X, pady=(0, 15))

        tk.Label(url_card, text="🌐 大屏地址",
                font=("Microsoft YaHei", 12, "bold"),
                bg="#16213e", fg="#00d4ff").pack(anchor="w", padx=20, pady=(15, 10))

        url_inner = tk.Frame(url_card, bg="#16213e")
        url_inner.pack(fill=tk.X, padx=20, pady=(0, 15))

        self.local_url_var = tk.StringVar(value=f"http://127.0.0.1:{self.config.get('port', DEFAULT_PORT)}")
        self.network_url_var = tk.StringVar(value=f"http://{self.local_ip}:{self.config.get('port', DEFAULT_PORT)}")

        local_frame = tk.Frame(local_frame := url_inner, bg="#0f3460", bd=1, relief=tk.SOLID)
        local_frame.pack(fill=tk.X, pady=4)

        tk.Label(local_frame, text="本机访问:",
                font=("Microsoft YaHei", 10),
                bg="#0f3460", fg="#4a9fd4", width=10, anchor="w").pack(side=tk.LEFT, padx=10, pady=8)

        tk.Label(local_frame, textvariable=self.local_url_var,
                font=("Consolas", 11),
                bg="#0f3460", fg="#00ff88").pack(side=tk.LEFT, pady=8, fill=tk.X, expand=True)

        copy_local_btn = tk.Button(local_frame, text="📋 复制",
                                   font=("Microsoft YaHei", 9),
                                   bg="#1e5a8a", fg="white", bd=0, padx=10,
                                   command=lambda: self._copy_url(self.local_url_var.get()))
        copy_local_btn.pack(side=tk.RIGHT, padx=10, pady=8)

        network_frame = tk.Frame(url_inner, bg="#0f3460", bd=1, relief=tk.SOLID)
        network_frame.pack(fill=tk.X, pady=4)

        tk.Label(network_frame, text="局域网访问:",
                font=("Microsoft YaHei", 10),
                bg="#0f3460", fg="#4a9fd4", width=10, anchor="w").pack(side=tk.LEFT, padx=10, pady=8)

        tk.Label(network_frame, textvariable=self.network_url_var,
                font=("Consolas", 11),
                bg="#0f3460", fg="#ffcc00").pack(side=tk.LEFT, pady=8, fill=tk.X, expand=True)

        copy_net_btn = tk.Button(network_frame, text="📋 复制",
                                 font=("Microsoft YaHei", 9),
                                 bg="#1e5a8a", fg="white", bd=0, padx=10,
                                 command=lambda: self._copy_url(self.network_url_var.get()))
        copy_net_btn.pack(side=tk.RIGHT, padx=10, pady=8)

        btn_card = tk.Frame(card_frame, bg="#16213e", bd=0, relief=tk.FLAT)
        btn_card.pack(fill=tk.X, pady=(0, 15))

        btn_inner = tk.Frame(btn_card, bg="#16213e")
        btn_inner.pack(fill=tk.X, padx=20, pady=15)

        self.start_btn = tk.Button(btn_inner, text="▶ 启动服务器",
                                   font=("Microsoft YaHei", 12, "bold"),
                                   bg="#27ae60", fg="white", bd=0, pady=12,
                                   activebackground="#219a52", activeforeground="white",
                                   command=self.start_server)
        self.start_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))

        self.stop_btn = tk.Button(btn_inner, text="■ 停止服务器",
                                  font=("Microsoft YaHei", 12, "bold"),
                                  bg="#e74c3c", fg="white", bd=0, pady=12,
                                  activebackground="#c0392b", activeforeground="white",
                                  command=self.stop_server, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5, 0))

        self.open_btn = tk.Button(card_frame, text="🌐 打开大屏",
                                  font=("Microsoft YaHei", 12, "bold"),
                                  bg="#3498db", fg="white", bd=0, pady=12,
                                  activebackground="#2980b9", activeforeground="white",
                                  command=self.open_dashboard, state=tk.DISABLED)
        self.open_btn.pack(fill=tk.X, padx=20, pady=(0, 8))

        self.hide_btn = tk.Button(card_frame, text="📥 隐藏到托盘",
                                  font=("Microsoft YaHei", 11),
                                  bg="#6c5ce7", fg="white", bd=0, pady=10,
                                  activebackground="#5b4cdb", activeforeground="white",
                                  command=self._hide_to_tray)
        self.hide_btn.pack(fill=tk.X, padx=20, pady=(0, 15))

        version_label = tk.Label(scrollable_frame, text="v1.2  |  拖动调整大小  |  关闭窗口时提示隐藏到托盘",
                                font=("Microsoft YaHei", 8),
                                bg="#1a1a2e", fg="#555555")
        version_label.pack(pady=(0, 10))

        main_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._setup_complete = True

    def _copy_url(self, url):
        self.root.clipboard_clear()
        self.root.clipboard_append(url)
        messagebox.showinfo("复制成功", f"已复制: {url}")

    def _update_status(self):
        if self.server_running and self.is_port_in_use(self.port):
            self.status_label.config(text="● 运行中", fg="#27ae60")
            self.start_btn.config(state=tk.DISABLED, bg="#555555")
            self.stop_btn.config(state=tk.NORMAL, bg="#e74c3c")
            self.open_btn.config(state=tk.NORMAL, bg="#3498db")
        else:
            self.status_label.config(text="● 已停止", fg="#e74c3c")
            self.start_btn.config(state=tk.NORMAL, bg="#27ae60")
            self.stop_btn.config(state=tk.DISABLED, bg="#555555")
            self.open_btn.config(state=tk.DISABLED, bg="#555555")

    def _update_urls(self):
        self.local_url_var.set(f"http://127.0.0.1:{self.port}")
        self.network_url_var.set(f"http://{self.local_ip}:{self.port}")

    def is_port_in_use(self, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', port)) == 0

    def start_server(self):
        try:
            self.host = self.host_var.get().strip()
            self.port = int(self.port_var.get())
            if not (1024 <= self.port <= 65535):
                messagebox.showerror("错误", "端口号必须在 1024-65535 之间")
                return
        except ValueError:
            messagebox.showerror("错误", "端口号必须是数字")
            return

        self._update_urls()
        self._save_config()

        if self.is_port_in_use(self.port):
            messagebox.showwarning("警告", f"端口 {self.port} 已被占用，服务器可能已在运行")
            self._update_status()
            return

        self.server_running = True
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()

        self.root.after(1500, self._update_status)
        messagebox.showinfo("成功", f"服务器已启动\n本机: http://127.0.0.1:{self.port}\n局域网: http://{self.local_ip}:{self.port}")

    def _run_server(self):
        import traceback
        import sys
        import importlib.util
        try:
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
                root_dir = base_path
            else:
                base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                root_dir = os.path.dirname(base_path)

            sys.path.insert(0, root_dir)

            module_path = os.path.join(base_path, "desktop", "views", "dashboard", "dashboard_server.py")
            spec = importlib.util.spec_from_file_location("dashboard_server", module_path)
            dashboard_server = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(dashboard_server)

            msg = f"[DEBUG] Starting server on {self.host}:{self.port}"
            print(msg)
            self.root.update()
            dashboard_server.app.run(host=self.host, port=self.port, debug=False, use_reloader=False)
        except SystemExit:
            print("[INFO] Flask server exited normally")
        except Exception as e:
            error_msg = f"[ERROR] 服务器错误: {e}"
            print(error_msg)
            traceback.print_exc()
            import tkinter.messagebox as msgbox
            msgbox.showerror("服务器错误", str(e))
        finally:
            self.server_running = False
            self.root.after(100, self._update_status)

    def stop_server(self):
        import subprocess
        try:
            netstat = subprocess.run(
                ['netstat', '-ano'], capture_output=True, text=True
            )
            pids = []
            for line in netstat.stdout.split('\n'):
                if f':{self.port}' in line and 'LISTENING' in line:
                    parts = line.strip().split()
                    if parts:
                        pid = parts[-1]
                        if pid.isdigit():
                            pids.append(pid)
            for pid in pids:
                subprocess.run(['taskkill', '/PID', pid, '/F'], capture_output=True)
        except Exception as e:
            print(f"停止服务器出错: {e}")

        time.sleep(0.5)
        self.server_running = False
        self._update_status()

        if not self.is_port_in_use(self.port):
            messagebox.showinfo("成功", "服务器已停止")
        else:
            messagebox.showwarning("警告", "服务器可能仍在运行，请手动结束进程")

    def open_dashboard(self):
        if self.is_port_in_use(self.port):
            webbrowser.open(self.local_url_var.get())
        else:
            messagebox.showerror("错误", "服务器未启动，无法打开大屏")

    def _setup_tray(self):
        """初始化系统托盘"""
        try:
            icon_image = self._create_tray_icon_image()

            def show_callback(icon=None, item=None):
                self._show_window()

            def hide_callback(icon=None, item=None):
                self._hide_to_tray()

            def open_callback(icon=None, item=None):
                if self.is_port_in_use(self.port):
                    webbrowser.open(self.local_url_var.get())

            def stop_callback(icon=None, item=None):
                if self.server_running:
                    self.stop_server()
                if self.tray_icon:
                    self.tray_icon.stop()
                self.root.after(100, self.root.destroy)

            def quit_callback(icon=None, item=None):
                if self.server_running:
                    self.stop_server()
                if self.tray_icon:
                    self.tray_icon.stop()
                self.root.after(100, self.root.destroy)

            menu = Menu(
                MenuItem("显示窗口", show_callback),
                MenuItem("打开大屏", open_callback, enabled=self.server_running),
                MenuItem("隐藏到托盘", hide_callback),
                MenuItem("停止服务器", stop_callback, enabled=self.server_running),
                MenuItem("退出", quit_callback)
            )

            self.tray_icon = Icon(
                "dashboard_launcher",
                icon_image,
                "可视化大屏启动器 - 右键菜单",
                menu
            )

            logger.info("System tray initialized successfully")
        except Exception as e:
            logger.error(f"Failed to setup tray: {e}")
            self.tray_icon = None

    def _create_tray_icon_image(self):
        """创建托盘图标图像"""
        try:
            width = 64
            height = 64
            image = Image.new('RGB', (width, height), color='#1a1a2e')
            draw = ImageDraw.Draw(image)

            draw.ellipse([8, 8, 56, 56], fill='#00d4ff', outline='#007bb8')
            draw.rectangle([20, 24, 44, 40], fill='#1a1a2e')
            draw.polygon([(32, 30), (40, 38), (24, 38)], fill='#27ae60')

            return image
        except Exception as e:
            logger.error(f"Failed to create tray icon: {e}")
            return Image.new('RGB', (64, 64), color='#1a1a2e')

    def _show_window(self):
        """显示主窗口"""
        try:
            self.root.deiconify()
            self.root.state('normal')
            self.rootlift()
            self.root.focus_force()
            self.is_hidden_to_tray = False
            logger.info("Window restored from tray")
        except Exception as e:
            logger.error(f"Failed to show window: {e}")

    def _hide_to_tray(self):
        """隐藏窗口到系统托盘"""
        try:
            self.root.withdraw()
            self.is_hidden_to_tray = True
            logger.info("Window hidden to tray")

            if self.tray_icon:
                def run_tray():
                    if self.tray_icon:
                        self.tray_icon.run()
                threading.Thread(target=run_tray, daemon=True).start()
        except Exception as e:
            logger.error(f"Failed to hide to tray: {e}")

    def _update_tray_menu(self):
        """更新托盘菜单状态"""
        pass

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.root.mainloop()

    def _on_closing(self):
        """窗口关闭事件"""
        if messagebox.askyesno("退出确认", '是否要隐藏到系统托盘而不是完全退出？\n点击"否"将完全退出程序。'):
            self._hide_to_tray()
        else:
            if self.server_running and self.is_port_in_use(self.port):
                if messagebox.askyesno("退出确认", "服务器仍在运行，是否停止并退出？"):
                    self.stop_server()
            if self.tray_icon:
                self.tray_icon.stop()
            self.root.destroy()


if __name__ == "__main__":
    ui = DashboardLauncherUI()
    ui.run()
