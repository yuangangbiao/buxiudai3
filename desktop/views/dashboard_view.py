# -*- coding: utf-8 -*-
"""
生产监控大屏视图 - 启动提示
"""
import tkinter as tk
from tkinter import ttk, messagebox
import os, sys, socket, threading, webbrowser
import json


class DashboardView(tk.Frame):
    """仪表板占位视图（实际大屏在浏览器中）"""

    def __init__(self, parent):
        super().__init__(parent, bg="#f0f2f5")

        # 中央提示卡片
        card = tk.Frame(self, bg="white", padx=40, pady=40)
        card.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(card, text="📈", font=("Segoe UI Emoji", 48)).pack(pady=(0, 10))
        tk.Label(card, text="生产监控大屏", font=("Microsoft YaHei", 20, "bold"),
                bg="white", fg="#1E3A5F").pack()
        
        # 端口设置
        port_frame = tk.Frame(card, bg="white")
        port_frame.pack(pady=(15, 10))
        
        tk.Label(port_frame, text="端口设置:", font=("Microsoft YaHei", 12),
                bg="white", fg="#666666").pack(side=tk.LEFT, padx=(0, 10))
        
        self.port_var = tk.StringVar(value="5000")
        port_entry = ttk.Entry(port_frame, textvariable=self.port_var, width=10)
        port_entry.pack(side=tk.LEFT)
        
        # 按钮框架
        btn_frame = tk.Frame(card, bg="white")
        btn_frame.pack(pady=(20, 10))
        
        start_btn = ttk.Button(btn_frame, text="启动服务器", command=self.start_server)
        start_btn.pack(side=tk.LEFT, padx=10)
        
        stop_btn = ttk.Button(btn_frame, text="关闭服务器", command=self.stop_server)
        stop_btn.pack(side=tk.LEFT, padx=10)
        
        open_btn = ttk.Button(btn_frame, text="打开大屏", command=self.open_dashboard)
        open_btn.pack(side=tk.LEFT, padx=10)
        
        # 固化功能按钮框架
        solidify_btn_frame = tk.Frame(card, bg="white")
        solidify_btn_frame.pack(pady=(10, 0))
        
        solidify_material_btn = ttk.Button(solidify_btn_frame, text="🔧 固化管理材料备料",
                                          command=self.solidify_material_prep)
        solidify_material_btn.pack(side=tk.LEFT, padx=10)
        
        solidify_process_btn = ttk.Button(solidify_btn_frame, text="⚙️ 固化工序设置",
                                         command=self.solidify_process)
        solidify_process_btn.pack(side=tk.LEFT, padx=10)

        reorder_btn = ttk.Button(solidify_btn_frame, text="📋 工序排序",
                                command=self.reorder_processes_dialog)
        reorder_btn.pack(side=tk.LEFT, padx=10)
        
        # 状态标签
        self.status_label = tk.Label(card, text="✅ 就绪",
                                    font=("Microsoft YaHei", 10),
                                    bg="white", fg="#28a745")
        self.status_label.pack(pady=(15, 0))
        
        # 提示信息
        tk.Label(card, text="按 F11 可进入全屏模式\nESC 退出全屏\n页面每30秒自动刷新",
                font=("Microsoft YaHei", 10), bg="white", fg="#999999",
                justify="left").pack(pady=(10, 0))
        
        # 服务器进程
        self.server_thread = None
        self.server_running = False
        
        # 检查服务器状态
        self.check_server_status()
    
    def check_server_status(self):
        """检查服务器状态"""
        try:
            port = int(self.port_var.get())
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            
            if result == 0:
                self.status_label.config(text="✅ 服务器运行中", fg="#28a745")
                self.server_running = True
            else:
                self.status_label.config(text="⚠️ 服务器未运行", fg="#ffc107")
                self.server_running = False
        except Exception as e:
            self.status_label.config(text=f"❌ 错误: {e}", fg="#dc3545")
    
    def start_server(self):
        """启动服务器"""
        try:
            port = int(self.port_var.get())
            
            # 检查端口是否已被占用
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            
            if result == 0:
                messagebox.showinfo("提示", f"端口 {port} 已被占用，服务器可能已在运行")
                return
            
            # 启动Flask服务器（后台线程）
            def run_server():
                dashboard_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                sys.path.insert(0, dashboard_dir)
                
                # 修改dashboard_server.py的端口
                import dashboard_server
                dashboard_server.app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
            
            self.server_thread = threading.Thread(target=run_server, daemon=True)
            self.server_thread.start()
            
            # 更新状态
            self.status_label.config(text="🚀 服务器启动中...", fg="#17a2b8")
            
            # 延迟检查状态
            self.after(2000, self.check_server_status)
            
        except Exception as e:
            messagebox.showerror("错误", f"启动服务器失败: {e}")
    
    def stop_server(self):
        """关闭服务器"""
        try:
            port = int(self.port_var.get())
            
            # 检查服务器是否运行
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            
            if result != 0:
                messagebox.showinfo("提示", f"端口 {port} 上没有运行的服务器")
                return
            
            # 使用netstat命令查找占用端口的进程
            import subprocess
            import re
            
            # 执行netstat命令获取端口占用信息
            result = subprocess.run(
                ["netstat", "-ano"], 
                capture_output=True, 
                text=True
            )
            
            # 查找占用指定端口的进程ID
            pattern = rf":{port}.*LISTENING\s+(\d+)" 
            matches = re.findall(pattern, result.stdout)
            
            if matches:
                pid = matches[0]
                # 终止该进程
                subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
                
                # 更新状态
                self.status_label.config(text="🛑 服务器已关闭", fg="#dc3545")
                self.server_running = False
            else:
                messagebox.showinfo("提示", f"未找到占用端口 {port} 的进程")
                
        except Exception as e:
            messagebox.showerror("错误", f"关闭服务器失败: {e}")
    
    def open_dashboard(self):
        """打开大屏"""
        try:
            port = int(self.port_var.get())
            
            # 检查服务器是否运行
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            
            if result != 0:
                messagebox.showinfo("提示", f"服务器未运行，请先启动服务器")
                return
            
            # 打开浏览器
            webbrowser.open(f"http://localhost:{port}/v2")
            self.status_label.config(text="🌐 浏览器已打开", fg="#28a745")
            
        except Exception as e:
            messagebox.showerror("错误", f"打开浏览器失败: {e}")
    
    def solidify_material_prep(self):
        """固化材料备料设置"""
        from desktop.views.material_prep_view import MaterialPrepView
        
        # 创建一个对话框来管理材料备料固化
        dialog = tk.Toplevel(self)
        dialog.title("固化管理材料备料")
        from utils.window_manager import setup_resizable_window
        setup_resizable_window(dialog, "dashboard_material_prep", "600x500")
        dialog.transient(self)
        dialog.grab_set()
        
        # 创建材料备料视图
        try:
            prep_view = MaterialPrepView(dialog)
            prep_view.pack(fill=tk.BOTH, expand=True)
            messagebox.showinfo("提示", "材料备料固化功能已打开，请在大屏中进行固化配置", parent=dialog)
        except Exception as e:
            messagebox.showerror("错误", f"无法打开材料备料视图: {e}", parent=dialog)
    
    def solidify_process(self):
        """固化工序设置"""
        from desktop.views.process_view import ProcessView
        
        # 创建一个对话框来管理工序固化
        dialog = tk.Toplevel(self)
        dialog.title("固化工序设置")
        from utils.window_manager import setup_resizable_window
        setup_resizable_window(dialog, "dashboard_process", "800x600")
        dialog.transient(self)
        dialog.grab_set()
        
        # 创建工序视图
        try:
            process_view = ProcessView(dialog)
            process_view.pack(fill=tk.BOTH, expand=True)
            messagebox.showinfo("提示", "工序设置固化功能已打开，请在大屏中进行固化配置", parent=dialog)
        except Exception as e:
            messagebox.showerror("错误", f"无法打开工序视图: {e}", parent=dialog)

    def reorder_processes_dialog(self):
        """工序排序弹窗 — 拖拽不可用，用上下移动按钮"""
        import tkinter as tk
        from tkinter import ttk, messagebox

        dialog = tk.Toplevel(self)
        dialog.title("工序显示排序")
        dialog.geometry("500x600")
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(dialog, text="工序显示排序", font=("Microsoft YaHei", 14, "bold"),
                fg="#1E3A5F").pack(pady=(15, 5))
        tk.Label(dialog, text="调整工序在手机端和调度中心的显示顺序",
                font=("Microsoft YaHei", 10), fg="#666").pack(pady=(0, 10))

        # 工序列表
        list_frame = tk.Frame(dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        process_listbox = tk.Listbox(list_frame, font=("Microsoft YaHei", 11),
                                     selectmode=tk.SINGLE, yscrollcommand=scrollbar.set,
                                     activestyle='none')
        process_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=process_listbox.yview)

        # 加载工序
        try:
            from core.config import get_all_processes
            processes = get_all_processes(sort=True)
            for p in processes:
                process_listbox.insert(tk.END, p)
        except Exception as e:
            process_listbox.insert(tk.END, f"加载失败: {e}")

        def move_up():
            sel = process_listbox.curselection()
            if not sel or sel[0] == 0:
                return
            idx = sel[0]
            text = process_listbox.get(idx)
            process_listbox.delete(idx)
            process_listbox.insert(idx - 1, text)
            process_listbox.selection_set(idx - 1)

        def move_down():
            sel = process_listbox.curselection()
            if not sel or sel[0] == process_listbox.size() - 1:
                return
            idx = sel[0]
            text = process_listbox.get(idx)
            process_listbox.delete(idx)
            process_listbox.insert(idx + 1, text)
            process_listbox.selection_set(idx + 1)

        def move_top():
            sel = process_listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            text = process_listbox.get(idx)
            process_listbox.delete(idx)
            process_listbox.insert(0, text)
            process_listbox.selection_set(0)

        def move_bottom():
            sel = process_listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            text = process_listbox.get(idx)
            process_listbox.delete(idx)
            process_listbox.insert(tk.END, text)
            process_listbox.selection_set(tk.END)

        def save_order():
            ordered = [process_listbox.get(i) for i in range(process_listbox.size())]
            try:
                from core.config import reorder_processes, save_display_order_to_db, invalidate_display_seq_cache
                reorder_processes(ordered)
                cnt = save_display_order_to_db()
                invalidate_display_seq_cache()
                messagebox.showinfo("成功", f"排序已保存！({cnt} 条记录)")
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {e}")

        # 按钮栏
        btn_bar = tk.Frame(dialog)
        btn_bar.pack(pady=10)

        tk.Button(btn_bar, text="⏫ 置顶", command=move_top,
                 font=("Microsoft YaHei", 10), width=8).pack(side=tk.LEFT, padx=3)
        tk.Button(btn_bar, text="⬆ 上移", command=move_up,
                 font=("Microsoft YaHei", 10), width=8).pack(side=tk.LEFT, padx=3)
        tk.Button(btn_bar, text="⬇ 下移", command=move_down,
                 font=("Microsoft YaHei", 10), width=8).pack(side=tk.LEFT, padx=3)
        tk.Button(btn_bar, text="⏬ 置底", command=move_bottom,
                 font=("Microsoft YaHei", 10), width=8).pack(side=tk.LEFT, padx=3)

        save_bar = tk.Frame(dialog)
        save_bar.pack(pady=(0, 15))
        tk.Button(save_bar, text="💾 保存排序", command=save_order,
                 font=("Microsoft YaHei", 11, "bold"), bg="#4CAF50", fg="white",
                 width=20, height=2).pack()
