# -*- coding: utf-8 -*-
"""
备份设置视图
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from config import COLORS, FONTS
from utils.backup_manager import backup_manager

class BackupSettingsView(tk.Toplevel):
    """备份设置窗口"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.title("数据备份设置")
        self.geometry("600x400")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg_main"])
        
        # 居中显示
        self.transient(parent)
        self.grab_set()
        
        self.setup_ui()
    
    def setup_ui(self):
        """构建UI"""
        # 主框架
        main_frame = tk.Frame(self, bg=COLORS["bg_main"])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 标题
        title_label = tk.Label(
            main_frame, 
            text="数据备份设置", 
            font=FONTS["title"], 
            bg=COLORS["bg_main"]
        )
        title_label.pack(pady=(0, 20))
        
        # 配置框架
        config_frame = tk.Frame(main_frame, bg=COLORS["bg_main"])
        config_frame.pack(fill=tk.X, pady=10)
        
        # 启用自动备份
        self.enable_var = tk.BooleanVar()
        enable_check = ttk.Checkbutton(
            config_frame, 
            text="启用自动备份", 
            variable=self.enable_var,
            style="TCheckbutton"
        )
        enable_check.pack(anchor="w", pady=5)
        
        # 备份间隔
        interval_frame = tk.Frame(config_frame, bg=COLORS["bg_main"])
        interval_frame.pack(anchor="w", pady=5)
        
        tk.Label(
            interval_frame, 
            text="备份间隔（小时）:", 
            font=FONTS["body"], 
            bg=COLORS["bg_main"]
        ).pack(side=tk.LEFT, padx=5)
        
        self.interval_var = tk.StringVar()
        interval_entry = ttk.Entry(
            interval_frame, 
            textvariable=self.interval_var, 
            width=10,
            style="TEntry"
        )
        interval_entry.pack(side=tk.LEFT, padx=5)
        
        # 备份目录
        backup_dir_frame = tk.Frame(config_frame, bg=COLORS["bg_main"])
        backup_dir_frame.pack(anchor="w", pady=5)
        
        tk.Label(
            backup_dir_frame, 
            text="备份目录:", 
            font=FONTS["body"], 
            bg=COLORS["bg_main"]
        ).pack(side=tk.LEFT, padx=5)
        
        self.backup_dir_var = tk.StringVar()
        backup_dir_entry = ttk.Entry(
            backup_dir_frame, 
            textvariable=self.backup_dir_var, 
            width=30,
            style="TEntry"
        )
        backup_dir_entry.pack(side=tk.LEFT, padx=5)
        
        browse_btn = ttk.Button(
            backup_dir_frame, 
            text="浏览", 
            command=self._browse_backup_dir,
            style="TButton"
        )
        browse_btn.pack(side=tk.LEFT, padx=5)
        
        # 保留备份天数
        keep_days_frame = tk.Frame(config_frame, bg=COLORS["bg_main"])
        keep_days_frame.pack(anchor="w", pady=5)
        
        tk.Label(
            keep_days_frame, 
            text="保留备份天数:", 
            font=FONTS["body"], 
            bg=COLORS["bg_main"]
        ).pack(side=tk.LEFT, padx=5)
        
        self.keep_days_var = tk.StringVar()
        keep_days_entry = ttk.Entry(
            keep_days_frame, 
            textvariable=self.keep_days_var, 
            width=10,
            style="TEntry"
        )
        keep_days_entry.pack(side=tk.LEFT, padx=5)
        
        # 备份文件列表
        backup_files_frame = tk.Frame(main_frame, bg=COLORS["bg_main"])
        backup_files_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        tk.Label(
            backup_files_frame, 
            text="备份文件列表", 
            font=FONTS["subtitle"], 
            bg=COLORS["bg_main"]
        ).pack(anchor="w", pady=5)
        
        # 列表框
        self.backup_list = ttk.Treeview(
            backup_files_frame, 
            columns=("filename", "date"), 
            show="headings",
            style="Treeview"
        )
        self.backup_list.heading("filename", text="文件名")
        self.backup_list.heading("date", text="备份时间")
        self.backup_list.column("filename", width=300)
        self.backup_list.column("date", width=200)
        self.backup_list.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(
            backup_files_frame, 
            orient=tk.VERTICAL, 
            command=self.backup_list.yview
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.backup_list.configure(yscrollcommand=scrollbar.set)
        
        # 按钮框架
        button_frame = tk.Frame(main_frame, bg=COLORS["bg_main"])
        button_frame.pack(fill=tk.X, pady=10)
        
        # 手动备份按钮
        backup_btn = ttk.Button(
            button_frame, 
            text="立即备份", 
            command=self._perform_backup,
            style="TButton"
        )
        backup_btn.pack(side=tk.LEFT, padx=5)
        
        # 恢复按钮
        restore_btn = ttk.Button(
            button_frame, 
            text="从备份恢复", 
            command=self._restore_from_backup,
            style="TButton"
        )
        restore_btn.pack(side=tk.LEFT, padx=5)
        
        # 刷新按钮
        refresh_btn = ttk.Button(
            button_frame, 
            text="刷新列表", 
            command=self._refresh_backup_list,
            style="TButton"
        )
        refresh_btn.pack(side=tk.LEFT, padx=5)
        
        # 右侧按钮
        right_frame = tk.Frame(button_frame, bg=COLORS["bg_main"])
        right_frame.pack(side=tk.RIGHT)
        
        # 保存按钮
        save_btn = ttk.Button(
            right_frame, 
            text="保存设置", 
            command=self._save_settings,
            style="TButton"
        )
        save_btn.pack(side=tk.RIGHT, padx=5)
        
        # 关闭按钮
        close_btn = ttk.Button(
            right_frame, 
            text="关闭", 
            command=self.destroy,
            style="TButton"
        )
        close_btn.pack(side=tk.RIGHT, padx=5)
        
        # 加载配置
        self._load_config()
        
        # 刷新备份列表
        self._refresh_backup_list()
    
    def _load_config(self):
        """加载配置"""
        config = backup_manager.get_config()
        self.enable_var.set(config["enabled"])
        self.interval_var.set(str(config["interval"]))
        self.backup_dir_var.set(config["backup_dir"])
        self.keep_days_var.set(str(config["keep_days"]))
    
    def _save_settings(self):
        """保存设置"""
        try:
            config = {
                "enabled": self.enable_var.get(),
                "interval": int(self.interval_var.get()),
                "backup_dir": self.backup_dir_var.get(),
                "keep_days": int(self.keep_days_var.get())
            }
            
            # 验证输入
            if config["interval"] <= 0:
                messagebox.showerror("错误", "备份间隔必须大于0")
                return
            
            if config["keep_days"] <= 0:
                messagebox.showerror("错误", "保留备份天数必须大于0")
                return
            
            if not config["backup_dir"]:
                messagebox.showerror("错误", "备份目录不能为空")
                return
            
            # 确保备份目录存在
            os.makedirs(config["backup_dir"], exist_ok=True)
            
            # 更新配置
            backup_manager.update_config(config)
            
            messagebox.showinfo("成功", "备份设置已保存")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
        except Exception as e:
            messagebox.showerror("错误", f"保存设置失败: {str(e)}")
    
    def _browse_backup_dir(self):
        """浏览备份目录"""
        dir_path = filedialog.askdirectory(
            title="选择备份目录",
            initialdir=self.backup_dir_var.get()
        )
        if dir_path:
            self.backup_dir_var.set(dir_path)
    
    def _perform_backup(self):
        """执行手动备份"""
        if backup_manager.perform_backup():
            messagebox.showinfo("成功", "备份已完成")
            self._refresh_backup_list()
        else:
            messagebox.showerror("错误", "备份失败")
    
    def _restore_from_backup(self):
        """从备份恢复"""
        selected_item = self.backup_list.selection()
        if not selected_item:
            messagebox.showerror("错误", "请选择要恢复的备份文件")
            return
        
        item = selected_item[0]
        backup_file = self.backup_list.item(item, "values")[2]
        
        if messagebox.askyesno(
            "确认恢复", 
            f"确定要从备份文件 {os.path.basename(backup_file)} 恢复数据吗？\n此操作将覆盖当前数据！"
        ):
            if backup_manager.restore_from_backup(backup_file):
                messagebox.showinfo("成功", "数据已从备份恢复\n请重启应用以应用更改")
            else:
                messagebox.showerror("错误", "恢复失败")
    
    def _refresh_backup_list(self):
        """刷新备份文件列表"""
        # 清空列表
        for item in self.backup_list.get_children():
            self.backup_list.delete(item)
        
        # 加载备份文件
        backup_files = backup_manager.get_backup_files()
        for backup in backup_files:
            self.backup_list.insert(
                "", 
                tk.END, 
                values=(
                    backup["filename"], 
                    backup["mtime"].strftime("%Y-%m-%d %H:%M:%S"),
                    backup["path"]
                )
            )