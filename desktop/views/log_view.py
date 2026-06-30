# -*- coding: utf-8 -*-
"""
后台日志查看视图
"""
import tkinter as tk
from tkinter import ttk
from config import COLORS, FONTS


def _format_date(val):
    """安全格式化日期，处理datetime对象或字符串"""
    if hasattr(val, 'strftime'):
        return val.strftime('%Y-%m-%d %H:%M:%S')
    elif val:
        return str(val)[:19]
    return "-"


class LogView(tk.Frame):

    def __init__(self, parent):
        super().__init__(parent, bg=COLORS["bg_main"])
        self.filters = {}
        self.init_ui()
        self.load_data()

    def init_ui(self):
        toolbar = tk.Frame(self, bg="#FFFFFF", height=50)
        toolbar.pack(fill=tk.X, side=tk.TOP)
        toolbar.pack_propagate(False)

        tk.Label(toolbar, text="📋 后台日志", font=FONTS["large"], bg="#FFFFFF",
                fg=COLORS["primary"]).pack(side=tk.LEFT, padx=15, pady=10)

        ttk.Button(toolbar, text="🔄 刷新", command=self.load_data).pack(side=tk.RIGHT, padx=10)

        # 筛选
        filter_frame = tk.Frame(toolbar, bg="#FFFFFF")
        filter_frame.pack(side=tk.RIGHT, padx=10)

        tk.Label(filter_frame, text="来源表:", font=FONTS["body"], bg="#FFFFFF").pack(side=tk.LEFT, padx=5)
        self.table_combo = ttk.Combobox(filter_frame, values=["全部", "orders", "production_orders", "shipments", "quality_records"],
                                        width=15, font=FONTS["body"], state="readonly")
        self.table_combo.current(0)
        self.table_combo.pack(side=tk.LEFT, padx=5)
        self.table_combo.bind("<<ComboboxSelected>>", lambda e: self.load_data())

        tk.Label(filter_frame, text="关键词:", font=FONTS["body"], bg="#FFFFFF").pack(side=tk.LEFT, padx=5)
        self.kw_entry = ttk.Entry(filter_frame, width=12, font=FONTS["body"])
        self.kw_entry.pack(side=tk.LEFT, padx=5)
        self.kw_entry.bind("<Return>", lambda e: self.load_data())
        ttk.Button(filter_frame, text="搜索", command=self.load_data).pack(side=tk.LEFT, padx=3)

        # 表格
        table_frame = tk.Frame(self, bg="#FFFFFF", padx=10, pady=5)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))

        cols = ("created_at", "table_name", "record_id", "old_status", "new_status", "operator", "remark")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=18)

        for col, txt, w in [
            ("created_at", "时间", 150), ("table_name", "来源表", 110),
            ("record_id", "记录ID", 70), ("old_status", "原状态", 90),
            ("new_status", "新状态", 90), ("operator", "操作人", 80), ("remark", "备注", 180)
        ]:
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=w, anchor="center" if col not in ("remark", "operator") else "w")

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        style = ttk.Style()
        style.configure("Treeview", font=("微软雅黑", 12), rowheight=32)

        # 统计
        self.stats_label = tk.Label(self, text="", font=FONTS["small"], bg=COLORS["bg_main"], fg="#666")
        self.stats_label.pack(fill=tk.X, padx=15, pady=(0, 5))

    def load_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        table_filter = self.table_combo.get()
        keyword = self.kw_entry.get().strip()

        from models.database import get_connection
        conn = get_connection()
        cursor = conn.cursor()

        if table_filter == "全部":
            cursor.execute("SELECT * FROM status_logs ORDER BY id DESC LIMIT 1000")
            rows = cursor.fetchall()
        else:
            cursor.execute(
                "SELECT * FROM status_logs WHERE table_name = %s ORDER BY id DESC LIMIT 1000",
                (table_filter,)
            )
            rows = cursor.fetchall()

        cursor.close()
        conn.close()

        if keyword:
            rows = [r for r in rows if keyword.lower() in str(r).lower()]

        table_map = {
            "orders": "订单",
            "production_orders": "生产工单",
            "shipments": "发货单",
            "quality_records": "质检记录",
        }

        count = 0
        for r in rows:
            table_name = table_map.get(r["table_name"], r["table_name"])
            self.tree.insert("", tk.END, values=(
                _format_date(r["created_at"]),
                table_name,
                r["record_id"],
                r["old_status"] or "-",
                r["new_status"] or "-",
                r["operator"] or "-",
                r["remark"] or "-",
            ))
            count += 1

        self.stats_label.config(text=f"共 {count} 条日志记录（显示最近 1000 条）")

    def refresh(self):
        self.load_data()
