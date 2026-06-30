# -*- coding: utf-8 -*-
"""
错误编码查询界面
用户可通过此界面根据错误编码查询解决方案
"""

import tkinter as tk
from tkinter import ttk, messagebox


class ErrorLookupView:
    """错误编码查询对话框"""

    def __init__(self, parent=None):
        self.parent = parent
        self.window = None
        self.code_entry = None
        self.result_text = None
        self.all_codes_listbox = None

    def show(self):
        """显示错误查询对话框"""
        if self.window is not None:
            self.window.lift()
            return

        self.window = tk.Toplevel(self.parent)
        self.window.title("错误编码查询")
        self.window.geometry("900x700")
        self.window.resizable(True, True)

        try:
            self.window.iconbitmap('icon.ico')
        except Exception as e:
            logger.warning(f"无法加载窗口图标: {e}")

        main_frame = tk.Frame(self.window, bg="#F5F5F5")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        title_label = tk.Label(
            main_frame,
            text="错误编码查询系统",
            font=("微软雅黑", 16, "bold"),
            bg="#F5F5F5",
            fg="#333333"
        )
        title_label.pack(pady=(0, 10))

        search_frame = tk.Frame(main_frame, bg="#FFFFFF")
        search_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            search_frame,
            text="错误编码:",
            font=("微软雅黑", 11),
            bg="#FFFFFF"
        ).pack(side=tk.LEFT, padx=(10, 5), pady=10)

        self.code_entry = ttk.Entry(search_frame, width=20, font=("微软雅黑", 11))
        self.code_entry.pack(side=tk.LEFT, padx=5, pady=10)
        self.code_entry.bind("<Return>", lambda e: self.lookup())

        ttk.Button(
            search_frame,
            text="查询",
            command=self.lookup
        ).pack(side=tk.LEFT, padx=5, pady=10)

        ttk.Button(
            search_frame,
            text="清除",
            command=self.clear_result
        ).pack(side=tk.LEFT, padx=5, pady=10)

        content_frame = tk.Frame(main_frame, bg="#F5F5F5")
        content_frame.pack(fill=tk.BOTH, expand=True)

        list_frame = tk.LabelFrame(
            content_frame,
            text="常见错误编码",
            font=("微软雅黑", 10),
            bg="#F5F5F5",
            padx=5,
            pady=5
        )
        list_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        scrollbar_y = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)

        self.all_codes_listbox = tk.Listbox(
            list_frame,
            width=25,
            height=30,
            font=("Consolas", 9),
            yscrollcommand=scrollbar_y.set,
            selectbackground="#4CAF50",
            selectforeground="#FFFFFF"
        )
        self.all_codes_listbox.pack(side=tk.LEFT, fill=tk.Y)
        scrollbar_y.config(command=self.all_codes_listbox.yview)

        self.all_codes_listbox.bind("<Double-Button-1>", lambda e: self.select_code())

        result_frame = tk.LabelFrame(
            content_frame,
            text="详细信息",
            font=("微软雅黑", 10),
            bg="#F5F5F5",
            padx=5,
            pady=5
        )
        result_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.result_text = tk.Text(
            result_frame,
            width=70,
            height=30,
            font=("微软雅黑", 10),
            wrap=tk.WORD,
            bg="#FAFAFA",
            fg="#333333",
            insertbackground="#333333"
        )
        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar_result = ttk.Scrollbar(result_frame, orient=tk.VERTICAL)
        scrollbar_result.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_text.config(yscrollcommand=scrollbar_result.set)
        scrollbar_result.config(command=self.result_text.yview)

        self.load_all_codes()

        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_all_codes(self):
        """加载所有错误编码到列表"""
        try:
            from core.error_codes import ERROR_CODES, get_error_summary

            codes = sorted(ERROR_CODES.keys())

            for code in codes:
                error = ERROR_CODES[code]
                severity_emoji = {
                    "CRITICAL": "🔴",
                    "HIGH": "🟠",
                    "MEDIUM": "🟡"
                }.get(error.severity, "⚪")

                display = f"{severity_emoji} {code}"
                self.all_codes_listbox.insert(tk.END, display)

        except ImportError as e:
            self.result_text.insert(tk.END, f"加载错误编码失败: {e}\n")
            self.result_text.insert(tk.END, "请确保 core/error_codes.py 文件存在\n")

    def lookup(self):
        """执行查询"""
        try:
            from core.error_codes import format_error_for_display, get_error_info

            code = self.code_entry.get().strip().upper()

            if not code:
                messagebox.showwarning("提示", "请输入错误编码")
                return

            error_info = get_error_info(code)

            self.result_text.delete(1.0, tk.END)

            if error_info:
                result = format_error_for_display(code)
                self.result_text.insert(tk.END, result)
            else:
                self.result_text.insert(tk.END, f"错误编码 '{code}' 不存在\n\n")
                self.result_text.insert(tk.END, "请检查编码格式，正确的格式如: ERR-SYS-001\n")
                self.result_text.insert(tk.END, "\n【提示】双击左侧列表中的编码可快速查看详情\n")

        except ImportError as e:
            messagebox.showerror("错误", f"无法导入错误编码模块: {e}")

    def clear_result(self):
        """清除结果"""
        self.result_text.delete(1.0, tk.END)
        self.code_entry.delete(0, tk.END)

    def select_code(self):
        """从列表中选择代码"""
        selection = self.all_codes_listbox.curselection()
        if selection:
            display_text = self.all_codes_listbox.get(selection[0])
            code = display_text.split(" ")[-1]
            self.code_entry.delete(0, tk.END)
            self.code_entry.insert(0, code)
            self.lookup()

    def on_close(self):
        """关闭窗口"""
        self.window = None
        if self.parent:
            self.parent.lift()


def show_error_lookup(parent=None):
    """显示错误查询窗口的便捷函数"""
    view = ErrorLookupView(parent)
    view.show()
    return view


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()

    view = ErrorLookupView(root)
    view.show()

    root.mainloop()
