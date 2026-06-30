#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务器管理器 - 集成所有本地服务器的启动和管理
"""
import logging
import logging.handlers
import os
import socket
import subprocess
import shutil

# 加载 .env 环境变量
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / '.env')
import sys
import threading
import time

logger = logging.getLogger(__name__)
import webbrowser
import tkinter as tk
from tkinter import ttk, scrolledtext

# 项目根目录
_PROJECT_ROOT = Path(__file__).resolve().parent


def _kill_all_python():
    """启动前强制杀掉所有 Python 进程（除自身外），避免旧代码残留"""
    import signal
    my_pid = os.getpid()
    killed = 0
    try:
        result = subprocess.run(
            ['tasklist', '/FO', 'CSV', '/NH'],
            capture_output=True, text=True, shell=True
        )
        for line in result.stdout.splitlines():
            if 'python' not in line.lower():
                continue
            parts = line.replace('"', '').split(',')
            if len(parts) >= 2:
                pid_str = parts[1].strip()
                if pid_str.isdigit():
                    pid = int(pid_str)
                    if pid != my_pid:
                        subprocess.run(['taskkill', '/F', '/PID', str(pid)],
                                      capture_output=True, shell=True)
                        killed += 1
    except Exception:
        pass
    return killed

def _clear_all_pycache():
    """清理整个项目的 __pycache__ 和 .pyc 文件"""
    deleted = 0
    for d in _PROJECT_ROOT.rglob('__pycache__'):
        try:
            shutil.rmtree(d, ignore_errors=True)
            deleted += 1
        except Exception:
            pass
    for f in _PROJECT_ROOT.rglob('*.pyc'):
        try:
            f.unlink()
            deleted += 1
        except Exception:
            pass
    return deleted


class ServerManager:
    def __init__(self):
        self.servers = []
        self.processes = {}
        self.log_callback = None
        self._cleared = False

    def set_log_callback(self, callback):
        self.log_callback = callback

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)

    def _is_port_in_use(self, port):
        """检查端口是否被占用"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', port)) == 0

    def _kill_port_process(self, port):
        """强制关闭占用指定端口的进程（Windows）"""
        try:
            result = subprocess.run(
                ['netstat', '-ano'],
                capture_output=True,
                text=True,
                shell=True
            )
            for line in result.stdout.splitlines():
                if f':{port}' not in line:
                    continue
                if 'LISTENING' not in line and 'ESTABLISHED' not in line:
                    continue
                parts = line.strip().split()
                if not parts:
                    continue
                pid = parts[-1]
                if not pid.isdigit():
                    continue
                subprocess.run(['taskkill', '/F', '/PID', pid],
                              capture_output=True, text=True, shell=True)
                self.log(f'[端口清理] 已关闭端口 {port} 的进程 PID={pid}')
        except Exception as e:
            self.log(f'[端口清理] 关闭端口 {port} 时异常: {e}')

    def start_server(self, server):
        """启动服务器"""
        if server['name'] in self.processes:
            self.log(f"服务器 {server['name']} 已经在运行")
            return False

        # 启动前预检：必需环境变量缺失时直接拒绝启动
        # 避免子进程立刻崩溃浪费 2 秒 + 日志噪音
        missing = []
        for key in server.get('precheck_env', []):
            if not os.environ.get(key):
                missing.append(key)
        if missing:
            self.log(f"❌ {server['name']} 启动预检失败：缺少环境变量 {missing}")
            self.log(f"   请在 d:\\yuan\\不锈钢网带跟单3.0\\.env 中设置：")
            for k in missing:
                self.log(f"     {k}=<你的值>")
            self.log(f"   或运行：python d:\\yuan\\不锈钢网带跟单3.0\\scripts\\generate_secrets.py 生成")
            return False

        # 首次启动时清理全部缓存
        if not self._cleared:
            self._cleared = True
            self.log('[启动] 清理 Python 缓存...')
            n = _clear_all_pycache()
            self.log(f'[启动] 已删除 {n} 个缓存项')

        try:
            port = server.get('port')
            if port:
                self._kill_port_process(port)
                time.sleep(1)
                # 二次确认端口已释放
                for _ in range(3):
                    if not self._is_port_in_use(port):
                        break
                    self.log(f'[端口清理] 端口 {port} 仍被占用，重试...')
                    self._kill_port_process(port)
                    time.sleep(2)
                if self._is_port_in_use(port):
                    self.log(f'⚠️ 端口 {port} 无法释放，可能启动失败')

            script_path = os.path.join(os.path.dirname(__file__), server['script'])
            cwd_path = os.path.join(os.path.dirname(__file__), server['cwd'])

            self.log(f"正在启动 {server['name']}...")
            self.log(f"脚本路径: {script_path}")
            self.log(f"工作目录: {cwd_path}")

            python_path = sys.executable
            cmd = [python_path, '-B', script_path]
            port_flag = server.get('port_flag', '')
            if port_flag:
                cmd.extend([port_flag, str(server.get('port', ''))])
            env = os.environ.copy()
            env['PYTHONDONTWRITEBYTECODE'] = '1'  # 禁止 .pyc 缓存，强制从源文件加载
            if not port_flag and server.get('port'):
                env['PORT'] = str(server['port'])
            # 注入服务器特定的环境变量
            for key, value in server.get('env', {}).items():
                env[key] = value
                self.log(f"  ENV {key}={value}")
            proc = subprocess.Popen(
                cmd,
                cwd=cwd_path,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            self.processes[server['name']] = proc

            def monitor_log():
                try:
                    while proc.poll() is None:
                        line = proc.stdout.readline()
                        if line:
                            self.log(f"[{server['name']}] {line.strip()}")
                    for line in proc.stdout:
                        self.log(f"[{server['name']}] {line.strip()}")
                    self.log(f"⚠️ 服务器 {server['name']} 异常退出")
                    self.processes.pop(server['name'], None)
                except Exception as e:
                    self.log(f"日志监控异常: {e}")

            threading.Thread(target=monitor_log, daemon=True).start()

            time.sleep(2)

            if proc.poll() is None:
                self.log(f"✅ {server['name']} 启动成功")
                return True
            else:
                self.log(f"❌ {server['name']} 启动失败")
                del self.processes[server['name']]
                return False

        except Exception as e:
            self.log(f"启动 {server['name']} 时发生错误: {e}")
            return False

    def stop_server(self, server):
        """停止服务器"""
        if server['name'] not in self.processes:
            self.log(f"服务器 {server['name']} 未运行")
            return False

        try:
            proc = self.processes[server['name']]
            proc.terminate()
            proc.wait(timeout=5)
            del self.processes[server['name']]
            self.log(f"✅ {server['name']} 已停止")
            return True
        except subprocess.TimeoutExpired:
            proc.kill()
            del self.processes[server['name']]
            self.log(f"✅ {server['name']} 已强制停止")
            return True
        except Exception as e:
            self.log(f"停止 {server['name']} 时发生错误: {e}")
            return False

    def is_running(self, server_name):
        """检查服务器是否运行"""
        return server_name in self.processes

class ServerLauncherUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("不锈钢网带跟单系统 - 服务器管理器")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        if os.path.exists('icon.ico'):
            try:
                self.root.iconbitmap('icon.ico')
            except Exception:
                pass

        self.manager = ServerManager()
        self.manager.set_log_callback(self.add_log)

        self.server_buttons = {}
        self.port_entries = {}

        self._create_ui()

    def _create_ui(self):
        """创建UI界面"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = ttk.Label(main_frame, text="不锈钢网带跟单系统 - 服务器管理器",
                               font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 15))

        servers_frame = ttk.LabelFrame(main_frame, text="服务器列表", padding="10")
        servers_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        servers_inner = ttk.Frame(servers_frame)
        servers_inner.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        servers = [
            {
                'name': '报工程序',
                'script': 'mobile_api_ai/app.py',
                'cwd': 'mobile_api_ai',
                'port': 5008,
                'page_path': '/',
                'description': '现场报工签到系统 - 扫码报工、签到管理',
                'color': '#ff5722',
                'has_port_config': True,
                'port_key': 'backend'
            },
            {
                'name': '容器中心',
                'script': 'mobile_api_ai/container_center_api.py',
                'cwd': 'mobile_api_ai',
                'port': 5002,
                'page_path': '/',
                'description': '容器中心 - 流程数据接收与推送',
                'color': '#4caf50',
                'has_port_config': True,
                'port_key': 'container',
                'env': {'WECHAT_CLOUD_API_KEY': 'WkQ9-8X7Z-3K2M-5P6L'}
            },
            {
                'name': '调度中心',
                'script': 'mobile_api_ai/standalone_dispatch_server.py',
                'cwd': 'mobile_api_ai',
                'port': 5003,
                'page_path': '/api/dispatch-center/',
                'description': '调度中心 - 任务调度与消息分发(完整版)',
                'color': '#2196f3',
                'has_port_config': True,
                'port_key': 'dispatch_center',
                'env': {'MYSQL_PASSWORD': os.environ.get('MYSQL_PASSWORD', '')}
            },
            {
                'name': '库存管理',
                'script': 'mobile_api_ai/inventory_api_server.py',
                'cwd': 'mobile_api_ai',
                'port': 5010,
                'page_path': '/inventory/dashboard',
                'description': '库存管理系统 - 出入库查询/预警/流水',
                'color': '#795548',
                'has_port_config': True,
                'port_key': 'inventory',
                # 修复启动失败：注入 inventory_api_server.py 启动校验所需的全部环境变量
                # jgs7 修复：所有敏感配置从环境变量读取，不提供默认值
                'env': {
                    'MYSQL_PASSWORD': os.environ.get('MYSQL_PASSWORD', ''),
                    'MYSQL_USER': os.environ.get('MYSQL_USER', ''),
                    'INVENTORY_DB_NAME': 'inventory_db',
                    'FLASK_SECRET_KEY': os.environ.get('FLASK_SECRET_KEY', ''),
                    'INVENTORY_ADMIN_PASSWORD_HASH': os.environ.get('INVENTORY_ADMIN_PASSWORD_HASH', ''),
                },
                # 启动前预检（缺失关键变量时拒绝启动，避免子进程立即退出）
                'precheck_env': ['FLASK_SECRET_KEY', 'INVENTORY_ADMIN_PASSWORD_HASH', 'MYSQL_USER', 'INVENTORY_DB_NAME'],
            },
            {
                'name': 'Sync Bridge',
                'script': 'mobile_api_ai/sync_bridge_server.py',
                'cwd': 'mobile_api_ai',
                'port': 8008,
                'page_path': '/health',
                'description': '数据同步桥 - 容器中心状态同步到MySQL',
                'color': '#00bcd4',
                'has_port_config': True,
                'port_key': 'sync_bridge',
                'env': {'MYSQL_PASSWORD': os.environ.get('MYSQL_PASSWORD', '')}
            },
            {
                'name': '可视化大屏',
                'script': 'desktop/views/dashboard/dashboard_server.py',
                'cwd': 'desktop/views/dashboard',
                'port': 5000,
                'page_path': '/',
                'description': '工厂数据大屏 - 生产数据可视化展示',
                'color': '#ff9800',
                'has_port_config': True,
                'port_key': 'dashboard'
            }
        ]

        row = 0
        col = 0
        max_cols = 2

        for server in servers:
            card = ttk.Frame(servers_inner, padding="10", relief=tk.RIDGE)
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

            name_label = ttk.Label(card, text=server['name'], font=('Arial', 12, 'bold'))
            name_label.pack(side=tk.TOP, pady=(0, 5))

            desc_label = ttk.Label(card, text=server['description'], font=('Arial', 10))
            desc_label.pack(side=tk.TOP, pady=(0, 5))

            port_frame = ttk.Frame(card)
            port_frame.pack(side=tk.TOP, pady=(0, 5))

            port_label = ttk.Label(port_frame, text="端口:")
            port_label.pack(side=tk.LEFT, padx=(0, 5))

            port_var = tk.StringVar(value=str(server['port']))
            port_entry = ttk.Entry(port_frame, textvariable=port_var, width=8)
            port_entry.pack(side=tk.LEFT)

            if server.get('port_key'):
                self.port_entries[server['port_key']] = (port_entry, port_var)

            btn_frame = ttk.Frame(card)
            btn_frame.pack(side=tk.TOP)

            start_btn = ttk.Button(
                btn_frame,
                text="启动",
                width=8,
                command=lambda s=server, p=port_var: self._start_server(s, p)
            )
            start_btn.pack(side=tk.LEFT, padx=(0, 3))
            self.server_buttons[server['name']] = (start_btn, port_var)

            stop_btn = ttk.Button(
                btn_frame,
                text="停止",
                width=8,
                state='disabled',
                command=lambda s=server, p=port_var: self._stop_server(s, p)
            )
            stop_btn.pack(side=tk.LEFT, padx=(0, 3))
            self.server_buttons[server['name']] = (start_btn, stop_btn, port_var)

            if server.get('page_path'):
                link_btn = ttk.Button(
                    btn_frame,
                    text="打开页面",
                    width=10,
                    command=lambda s=server, p=port_var: self._open_browser(int(p.get()), s.get('page_path', '/'))
                )
                link_btn.pack(side=tk.LEFT, padx=(0, 3))

            if server.get('config_path'):
                config_btn = ttk.Button(
                    btn_frame,
                    text="配置",
                    width=8,
                    command=lambda s=server, p=port_var: self._open_browser(int(p.get()), s.get('config_path', '/'))
                )
                config_btn.pack(side=tk.LEFT)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        for i in range(max_cols):
            servers_inner.grid_columnconfigure(i, weight=1)
        for i in range(row + 1):
            servers_inner.grid_rowconfigure(i, weight=1)

        # ─── 独立服务区 ───
        sep_label = ttk.Label(servers_frame, text="─── 独立服务 ───", font=('Arial', 10))
        sep_label.pack(anchor=tk.W, pady=(10, 5))

        indie_frame = ttk.Frame(servers_frame, padding="10")
        indie_frame.pack(fill=tk.X, padx=5)

        indie_servers = [
            {
                'name': '人脸扫描',
                'script': 'mobile_api_ai/face_server.py',
                'cwd': 'mobile_api_ai',
                'port': 5009,
                'page_path': '/',
                'description': '人脸识别考勤 - 独立启动，按需使用',
                'color': '#9c27b0',
                'has_port_config': True,
                'port_key': 'face'
            },
        ]

        for server in indie_servers:
            card = ttk.Frame(indie_frame, padding="8", relief=tk.GROOVE)
            card.pack(side=tk.LEFT, padx=10, pady=5)

            name_label = ttk.Label(card, text=server['name'], font=('Arial', 11, 'bold'))
            name_label.pack(side=tk.TOP, pady=(0, 3))

            desc_label = ttk.Label(card, text=server['description'], font=('Arial', 9))
            desc_label.pack(side=tk.TOP, pady=(0, 3))

            port_frame = ttk.Frame(card)
            port_frame.pack(side=tk.TOP, pady=(0, 3))

            port_label = ttk.Label(port_frame, text="端口:")
            port_label.pack(side=tk.LEFT, padx=(0, 5))
            port_var = tk.StringVar(value=str(server['port']))
            port_entry = ttk.Entry(port_frame, textvariable=port_var, width=8)
            port_entry.pack(side=tk.LEFT)

            if server.get('port_key'):
                self.port_entries[server['port_key']] = (port_entry, port_var)

            btn_frame = ttk.Frame(card)
            btn_frame.pack(side=tk.TOP)

            start_btn = ttk.Button(btn_frame, text="启动", width=8,
                command=lambda s=server, p=port_var: self._start_server(s, p))
            start_btn.pack(side=tk.LEFT, padx=(0, 3))

            stop_btn = ttk.Button(btn_frame, text="停止", width=8, state='disabled',
                command=lambda s=server, p=port_var: self._stop_server(s, p))
            stop_btn.pack(side=tk.LEFT)

            self.server_buttons[server['name']] = (start_btn, stop_btn, port_var)

            if server.get('page_path'):
                link_btn = ttk.Button(btn_frame, text="打开", width=6,
                    command=lambda s=server, p=port_var: self._open_browser(int(p.get()), s.get('page_path', '/')))
                link_btn.pack(side=tk.LEFT, padx=(3, 0))

        log_frame = ttk.LabelFrame(main_frame, text="运行日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(log_frame, width=80, height=15)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.insert(tk.END, "服务器管理器已启动...\n")
        self.log_text.config(state=tk.DISABLED)

        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=(10, 0))

        stop_all_btn = ttk.Button(bottom_frame, text="🛑 关闭所有服务器", command=self._stop_all_servers)
        stop_all_btn.pack(side=tk.LEFT)

        clear_btn = ttk.Button(bottom_frame, text="清空日志", command=self._clear_log)
        clear_btn.pack(side=tk.RIGHT)

    def _start_server(self, server, port_var):
        """启动服务器"""
        server_name = server['name']
        start_btn, stop_btn, _ = self.server_buttons.get(server_name, (None, None, None))
        if not start_btn or not stop_btn:
            return

        new_port = int(port_var.get())
        server['port'] = new_port

        if self.manager.start_server(server):
            start_btn.config(state='disabled')
            stop_btn.config(state='normal')

    def _stop_server(self, server, port_var):
        """停止服务器"""
        server_name = server['name']
        start_btn, stop_btn, _ = self.server_buttons.get(server_name, (None, None, None))
        if not start_btn or not stop_btn:
            return

        if self.manager.stop_server(server):
            start_btn.config(state='normal')
            stop_btn.config(state='disabled')

    def _open_browser(self, port, page_path='/'):
        """打开浏览器访问服务器"""
        url = f"http://localhost:{port}{page_path}"
        self.add_log(f"正在打开: {url}")
        try:
            webbrowser.open(url)
        except Exception as e:
            self.add_log(f"打开浏览器失败: {e}")

    def add_log(self, message):
        """添加日志信息"""
        self.log_text.config(state=tk.NORMAL)
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _stop_all_servers(self):
        """关闭所有运行中的服务器"""
        servers = [
            {'name': '报工程序', 'script': 'mobile_api_ai/app.py', 'cwd': 'mobile_api_ai'},
            {'name': '容器中心', 'script': 'mobile_api_ai/container_center_api.py', 'cwd': 'mobile_api_ai'},
            {'name': '调度中心', 'script': 'mobile_api_ai/standalone_dispatch_server.py', 'cwd': 'mobile_api_ai'},
            {'name': '库存管理', 'script': 'mobile_api_ai/inventory_api_server.py', 'cwd': 'mobile_api_ai'},
            {'name': '人脸扫描', 'script': 'mobile_api_ai/face_server.py', 'cwd': 'mobile_api_ai'},
            {'name': 'Sync Bridge', 'script': 'mobile_api_ai/sync_bridge_server.py', 'cwd': 'mobile_api_ai'},
            {'name': '可视化大屏', 'script': 'desktop/views/dashboard/dashboard_server.py', 'cwd': 'desktop/views/dashboard'},
        ]

        stopped = []
        for server in servers:
            if self.manager.is_running(server['name']):
                if self.manager.stop_server(server):
                    stopped.append(server['name'])
                    start_btn, stop_btn, _ = self.server_buttons.get(server['name'], (None, None, None))
                    if start_btn and stop_btn:
                        start_btn.config(state='normal')
                        stop_btn.config(state='disabled')

        if stopped:
            self.add_log(f"✅ 已关闭: {', '.join(stopped)}")
        else:
            self.add_log("没有运行中的服务器")

    def _clear_log(self):
        """清空日志"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.insert(tk.END, "日志已清空\n")
        self.log_text.config(state=tk.DISABLED)

    def _on_close(self):
        """关闭窗口时停止所有服务器"""
        self.add_log("正在关闭所有服务器...")
        self._stop_all_servers()
        self.add_log("服务器管理器已关闭")
        self.root.destroy()

    def _heartbeat_check(self):
        """心跳线程：每120秒检查进程状态，崩溃自动重启"""
        server_list = [
            {'name': '报工程序', 'script': 'mobile_api_ai/app.py', 'cwd': 'mobile_api_ai', 'port': 5008},
            {'name': '容器中心', 'script': 'mobile_api_ai/container_center_api.py', 'cwd': 'mobile_api_ai',
             'env': {'WECHAT_CLOUD_API_KEY': 'WkQ9-8X7Z-3K2M-5P6L'}, 'port': 5002},
            {'name': '调度中心', 'script': 'mobile_api_ai/standalone_dispatch_server.py', 'cwd': 'mobile_api_ai', 'port': 5003},
            {'name': '库存管理', 'script': 'mobile_api_ai/inventory_api_server.py', 'cwd': 'mobile_api_ai',
             'env': {'MYSQL_PASSWORD': os.environ.get('MYSQL_PASSWORD', '')}, 'port': 5010},
            {'name': '人脸扫描', 'script': 'mobile_api_ai/face_server.py', 'cwd': 'mobile_api_ai', 'port': 5009},
            {'name': 'Sync Bridge', 'script': 'mobile_api_ai/sync_bridge_server.py', 'cwd': 'mobile_api_ai',
             'env': {'MYSQL_PASSWORD': os.environ.get('MYSQL_PASSWORD', '')}, 'port': 8008},
            {'name': '可视化大屏', 'script': 'desktop/views/dashboard/dashboard_server.py', 'cwd': 'desktop/views/dashboard', 'port': 5000},
        ]
        while True:
            time.sleep(120)
            for svr in server_list:
                name = svr['name']
                if name in self.server_buttons:
                    start_btn, stop_btn, port_var = self.server_buttons[name]
                    if not self.manager.is_running(name) and stop_btn.cget('state') == 'disabled':
                        continue
                    if name not in self.manager.processes:
                        self.add_log(f"🔄 检测到 {name} 已崩溃，正在自动重启...")
                        self.manager.processes.pop(name, None)
                        self._start_server(svr, port_var)

    def run(self):
        """运行UI"""
        threading.Thread(target=self._heartbeat_check, daemon=True).start()
        self.root.mainloop()

# ── 文件变更检测 ──
CRITICAL_FILES = [
    'mobile_api_ai/storage/mysql_storage.py',
    'mobile_api_ai/container_center_api.py',
    'mobile_api_ai/standalone_dispatch_server.py',
    'mobile_api_ai/api/quality_inspection.py',
    'models/quality.py',
    'models/quality_rule.py',
    'services/wechat_report_service.py',
    'services/schedule_dispatch_service.py',
]

def check_stale_code(project_root: str = None):
    """检查关键文件是否被修改但服务未重启"""
    if project_root is None:
        project_root = os.path.dirname(__file__)
    import hashlib
    warnings = []
    for rel_path in CRITICAL_FILES:
        full_path = os.path.join(project_root, rel_path)
        if not os.path.exists(full_path):
            continue
        mtime = os.path.getmtime(full_path)
        hash_path = full_path + '.hash'
        current_hash = hashlib.md5(open(full_path, 'rb').read()).hexdigest()
        if os.path.exists(hash_path):
            with open(hash_path) as f:
                stored = f.read().strip().split('\t')
            if stored[0] != current_hash:
                warnings.append(f'  ⚠ {rel_path} (已修改，需重启)')
        with open(hash_path, 'w') as f:
            f.write(f'{current_hash}\t{mtime}')
    if warnings:
        logger.warning('【文件变更检测】以下文件已被修改，建议重启服务:\n%s',
                       '\n'.join(warnings))
    return warnings


if __name__ == '__main__':
    # 启动前：杀旧进程 + 清缓存
    killed = _kill_all_python()
    if killed:
        print(f'[启动] 已清理 {killed} 个旧 Python 进程')
    n = _clear_all_pycache()
    print(f'[启动] 已删除 {n} 个缓存项')
    check_stale_code()
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'server_launcher.log')
    _file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
    )
    _file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    logging.basicConfig(level=logging.INFO, handlers=[
        _file_handler, logging.StreamHandler()
    ])
    logger.info('服务器管理器启动')

    app = ServerLauncherUI()
    app.run()