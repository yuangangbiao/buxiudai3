# -*- coding: utf-8 -*-
"""
数据库结构备份工具 GUI - 仅备份表字段结构，不备份数据
"""
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db_schema_backup import (
    get_db_config,
    get_all_tables,
    backup_table_structure,
    verify_backup_file
)

class SchemaBackupGUI:
    """数据库结构备份工具 GUI"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("数据库结构备份工具 v1.0")
        self.root.geometry("700x550")
        self.root.resizable(True, True)

        self.pymysql = None
        self.conn = None
        self.tables = []

        self._create_widgets()
        self._load_defaults()
        self._import_pymysql()

    def _import_pymysql(self):
        """导入pymysql库"""
        try:
            import pymysql
            self.pymysql = pymysql
            self.log_message("✓ pymysql 模块已加载")
        except ImportError:
            self.log_message("✗ 错误：未安装 pymysql，请运行: pip install pymysql")
            messagebox.showerror("导入错误", "未安装 pymysql 模块\n请运行: pip install pymysql")
            self.pymysql = None

    def _load_defaults(self):
        """加载默认配置"""
        config = get_db_config()
        self.entry_host.insert(0, config.get('host', 'localhost'))
        self.entry_port.insert(0, str(config.get('port', 3306)))
        self.entry_user.insert(0, config.get('user', 'root'))
        self.entry_database.insert(0, config.get('database', 'steel_belt'))

    def _create_widgets(self):
        """创建界面组件"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        conn_frame = ttk.LabelFrame(main_frame, text="数据库连接配置", padding="10")
        conn_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        conn_frame.columnconfigure(1, weight=1)
        conn_frame.columnconfigure(3, weight=1)

        ttk.Label(conn_frame, text="主机地址:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        self.entry_host = ttk.Entry(conn_frame, width=25)
        self.entry_host.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=3)

        ttk.Label(conn_frame, text="端口:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=3)
        self.entry_port = ttk.Entry(conn_frame, width=10)
        self.entry_port.grid(row=0, column=3, sticky=(tk.W, tk.E), padx=5, pady=3)

        ttk.Label(conn_frame, text="用户名:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=3)
        self.entry_user = ttk.Entry(conn_frame, width=25)
        self.entry_user.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=3)

        ttk.Label(conn_frame, text="密码:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=3)
        self.entry_password = ttk.Entry(conn_frame, width=15, show="*")
        self.entry_password.grid(row=1, column=3, sticky=(tk.W, tk.E), padx=5, pady=3)

        ttk.Label(conn_frame, text="数据库名:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=3)
        self.entry_database = ttk.Entry(conn_frame, width=25)
        self.entry_database.grid(row=2, column=1, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=3)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=10)
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)
        btn_frame.columnconfigure(2, weight=1)

        self.btn_connect = ttk.Button(btn_frame, text="连接数据库", command=self._connect_database)
        self.btn_connect.grid(row=0, column=0, padx=5)

        self.btn_backup = ttk.Button(btn_frame, text="备份表结构", command=self._backup_structure, state=tk.DISABLED)
        self.btn_backup.grid(row=0, column=1, padx=5)

        self.btn_save = ttk.Button(btn_frame, text="保存到文件", command=self._save_to_file, state=tk.DISABLED)
        self.btn_save.grid(row=0, column=2, padx=5)

        tables_frame = ttk.LabelFrame(main_frame, text="数据库表列表", padding="10")
        tables_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        tables_frame.columnconfigure(0, weight=1)
        tables_frame.rowconfigure(0, weight=1)

        self.table_listbox = tk.Listbox(tables_frame, selectmode=tk.EXTENDED, height=12)
        self.table_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        scrollbar_y = ttk.Scrollbar(tables_frame, orient=tk.VERTICAL, command=self.table_listbox.yview)
        scrollbar_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.table_listbox.configure(yscrollcommand=scrollbar_y.set)

        scrollbar_x = ttk.Scrollbar(tables_frame, orient=tk.HORIZONTAL, command=self.table_listbox.xview)
        scrollbar_x.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self.table_listbox.configure(xscrollcommand=scrollbar_x.set)

        log_frame = ttk.LabelFrame(main_frame, text="操作日志", padding="10")
        log_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, width=70, state=tk.DISABLED)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        main_frame.rowconfigure(2, weight=1)

        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        self.status_label = ttk.Label(status_frame, text="就绪", foreground="gray")
        self.status_label.grid(row=0, column=0, sticky=tk.W)

    def log_message(self, msg):
        """添加日志消息"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{timestamp}] {msg}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)
        logger.info(msg)

    def _get_config(self):
        """获取当前配置"""
        return {
            "host": self.entry_host.get().strip(),
            "port": int(self.entry_port.get().strip() or 3306),
            "user": self.entry_user.get().strip(),
            "password": self.entry_password.get(),
            "database": self.entry_database.get().strip(),
            "charset": "utf8mb4"
        }

    def _connect_database(self):
        """连接数据库"""
        if not self.pymysql:
            messagebox.showerror("错误", "pymysql 模块未安装")
            return

        config = self._get_config()

        if not config['password']:
            messagebox.showwarning("警告", "请输入数据库密码")
            return

        if not config['database']:
            messagebox.showwarning("警告", "请输入数据库名")
            return

        self.log_message(f"正在连接 {config['host']}:{config['port']}/{config['database']}...")

        def connect_thread():
            try:
                if self.conn:
                    try:
                        self.conn.close()
                    except Exception as e:
                        logger.warning(f"[SchemaBackupGUI] 关闭旧连接失败: {e}")

                self.conn = self.pymysql.connect(**config)
                self.tables = get_all_tables(self.conn.cursor(), config['database'])

                self.root.after(0, self._on_connect_success)
            except Exception as e:
                self.root.after(0, lambda: self._on_connect_error(str(e)))

        threading.Thread(target=connect_thread, daemon=True).start()

    def _on_connect_success(self):
        """连接成功回调"""
        self.log_message("✓ 数据库连接成功")
        self.log_message(f"发现 {len(self.tables)} 个表")

        self.table_listbox.delete(0, tk.END)
        for table in self.tables:
            self.table_listbox.insert(tk.END, table)

        self.btn_backup.config(state=tk.NORMAL)
        self.status_label.config(text=f"已连接 - {len(self.tables)} 个表", foreground="green")

    def _on_connect_error(self, error_msg):
        """连接失败回调"""
        self.log_message(f"✗ 连接失败: {error_msg}")
        messagebox.showerror("连接失败", f"无法连接到数据库:\n{error_msg}")
        self.status_label.config(text="连接失败", foreground="red")

    def _backup_structure(self):
        """备份表结构"""
        if not self.conn:
            messagebox.showwarning("警告", "请先连接数据库")
            return

        selected_indices = self.table_listbox.curselection()
        if selected_indices:
            tables_to_backup = [self.tables[i] for i in selected_indices]
        else:
            tables_to_backup = self.tables

        if not tables_to_backup:
            messagebox.showwarning("警告", "没有选择要备份的表")
            return

        self.log_message(f"开始备份 {len(tables_to_backup)} 个表的结构...")

        self.btn_backup.config(state=tk.DISABLED)
        self.backup_content = []

        def backup_thread():
            try:
                cursor = self.conn.cursor()

                for i, table in enumerate(tables_to_backup):
                    self.root.after(0, lambda idx=i, t=table: self.log_message(f"  正在备份 [{idx+1}/{len(tables_to_backup)}]: {t}"))

                    sql = backup_table_structure(cursor, table)
                    self.backup_content.append(sql)

                cursor.close()
                self.root.after(0, self._on_backup_success)

            except Exception as e:
                self.root.after(0, lambda: self._on_backup_error(str(e)))

        threading.Thread(target=backup_thread, daemon=True).start()

    def _on_backup_success(self):
        """备份成功回调"""
        total_tables = len(self.backup_content)
        self.log_message(f"✓ 备份完成，共 {total_tables} 个表")

        full_content = "-- ===========================================================\n"
        full_content += f"-- 数据库结构备份\n"
        full_content += f"-- 备份时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        full_content += f"-- 数据库: {self.entry_database.get().strip()}\n"
        full_content += f"-- 表数量: {total_tables}\n"
        full_content += f"-- 警告: 此文件仅包含表结构，不包含任何数据！\n"
        full_content += "-- ===========================================================\n\n"
        full_content += "\n\n".join(self.backup_content)

        self.backup_content = full_content

        self.btn_save.config(state=tk.NORMAL)
        self.btn_backup.config(state=tk.NORMAL)
        self.status_label.config(text=f"备份完成 - {total_tables} 个表", foreground="green")

        messagebox.showinfo("备份成功", f"已备份 {total_tables} 个表的结构\n\n点击「保存到文件」可将备份保存到本地")

    def _on_backup_error(self, error_msg):
        """备份失败回调"""
        self.log_message(f"✗ 备份失败: {error_msg}")
        messagebox.showerror("备份失败", f"备份过程中出错:\n{error_msg}")
        self.btn_backup.config(state=tk.NORMAL)

    def _save_to_file(self):
        """保存到文件"""
        if not hasattr(self, 'backup_content') or not self.backup_content:
            messagebox.showwarning("警告", "没有可保存的备份内容")
            return

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        database = self.entry_database.get().strip()
        default_filename = f"structure_backup_{database}_{timestamp}.sql"

        filepath = filedialog.asksaveasfilename(
            title="保存数据库结构备份",
            defaultextension=".sql",
            filetypes=[("SQL文件", "*.sql"), ("所有文件", "*.*")],
            initialfile=default_filename
        )

        if not filepath:
            return

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(self.backup_content)

            self.log_message(f"✓ 已保存到: {filepath}")

            is_valid, count, _ = verify_backup_file(filepath)
            if is_valid:
                self.log_message(f"✓ 文件验证通过: 包含 {count} 个表的结构")

            messagebox.showinfo("保存成功", f"备份文件已保存:\n{filepath}")

        except Exception as e:
            self.log_message(f"✗ 保存失败: {e}")
            messagebox.showerror("保存失败", f"无法保存文件:\n{e}")

    def run(self):
        """运行应用"""
        self.root.mainloop()

if __name__ == "__main__":
    app = SchemaBackupGUI()
    app.run()