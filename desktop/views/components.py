# -*- coding: utf-8 -*-
"""
搜索型下拉框组件
第三阶段：下拉框搜索改造
"""
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional, List, Any
import threading

class SearchableCombobox(ttk.Combobox):
    """
    可搜索的下拉框组件

    特性：
    - 支持输入关键词过滤选项
    - 支持异步加载数据
    - 限制下拉选项数量（默认50条）
    - 避免大数据量导致的UI卡顿
    """

    def __init__(self, parent, loader: Callable[[str], List] = None,
                 max_items: int = 50, **kwargs):
        """
        Args:
            parent: 父窗口
            loader: 数据加载函数，接收 keyword 参数，返回选项列表
            max_items: 最大显示条目数
            **kwargs: ttk.Combobox 其他参数
        """
        self.loader = loader
        self.max_items = max_items
        self._all_items = []
        self._search_after_id = None

        super().__init__(parent, **kwargs)

        self._var = tk.StringVar()
        self.configure(textvariable=self._var)

        self.bind("<KeyRelease>", self._on_key_release)
        self.bind("<<ComboboxSelected>>", self._on_select)
        self.bind("<FocusIn>", self._on_focus_in)

        self._loaded = False
        self._pending_keyword = ""

    def _on_focus_in(self, event=None):
        """获取焦点时，如果尚未加载则加载数据"""
        if not self._loaded and self.loader:
            self._do_load("")

    def _on_key_release(self, event=None):
        """按键释放时，延迟搜索"""
        if self._search_after_id:
            self.after_cancel(self._search_after_id)

        keyword = self._var.get()

        if self._search_after_id:
            self.after_cancel(self._search_after_id)
        self._search_after_id = self.after(200, lambda: self._do_load(keyword))

    def _do_load(self, keyword: str):
        """执行加载"""
        if self.loader:
            items = self.loader(keyword)
            self._all_items = items[:self.max_items]
            self["values"] = self._all_items
            self._loaded = True

            if self._all_items:
                self.event_generate("<Down>")
        else:
            if keyword:
                filtered = [x for x in self._all_items if keyword in str(x)]
                self["values"] = filtered[:self.max_items]
            else:
                self["values"] = self._all_items[:self.max_items]

    def _on_select(self, event=None):
        """选中后触发回调"""
        pass

    def load_immediately(self):
        """立即加载数据（不等待焦点）"""
        if not self._loaded and self.loader:
            self._do_load("")

    def reload(self, keyword: str = ""):
        """重新加载数据"""
        self._loaded = False
        self._do_load(keyword)

    def set_items(self, items: List[str]):
        """直接设置选项列表"""
        self._all_items = items[:self.max_items]
        self["values"] = self._all_items
        self._loaded = True


class AsyncSearchableCombobox(SearchableCombobox):
    """
    异步搜索下拉框

    数据加载在线程中执行，避免阻塞UI
    """

    def __init__(self, parent, loader: Callable[[str], List] = None,
                 max_items: int = 50, **kwargs):
        super().__init__(parent, loader=None, max_items=max_items, **kwargs)
        self._async_loader = loader

    def _do_load(self, keyword: str):
        """异步执行加载"""
        def load_thread():
            items = self._async_loader(keyword) if self._async_loader else []
            items = items[:self.max_items]
            self.after(0, lambda: self._update_values(items))

        thread = threading.Thread(target=load_thread, daemon=True)
        thread.start()

    def _update_values(self, items: List):
        """在主线程更新选项"""
        self._all_items = items
        self["values"] = items
        self._loaded = True

        if items:
            self.event_generate("<Down>")


class LazyTreeview(ttk.Treeview):
    """
    带懒加载的 Treeview

    特性：
    - 支持大数据量分页显示
    - 提供「加载更多」功能
    - 限制最大渲染条数（默认1000条）
    """

    def __init__(self, parent, data_loader: Callable[[int, int], dict] = None,
                 max_visible: int = 1000, page_size: int = 100,
                 columns: tuple = None, show: str = "headings", **kwargs):
        """
        Args:
            parent: 父窗口
            data_loader: 数据加载函数，接收 (offset, limit) 参数，返回 {"data": [], "total": int}
            max_visible: 最大可见条数
            page_size: 每次加载的条数
            columns: 列定义
            show: 显示模式
            **kwargs: ttk.Treeview 其他参数
        """
        self.data_loader = data_loader
        self.max_visible = max_visible
        self.page_size = page_size
        self._loaded_count = 0
        self._total = float('inf')
        self._loading = False

        super().__init__(parent, columns=columns, show=show, **kwargs)

        self._load_btn_frame = None
        self._load_more_btn = None
        self._loading_label = None

    def setup_load_more(self, parent):
        """在 parent 中创建「加载更多」按钮"""
        self._load_btn_frame = tk.Frame(parent, bg="#FFFFFF")
        self._load_more_btn = ttk.Button(
            self._load_btn_frame,
            text="加载更多...",
            command=self._load_more
        )
        self._load_more_btn.pack(pady=5)
        self._loading_label = tk.Label(
            self._load_btn_frame,
            text="",
            font=("微软雅黑", 9),
            bg="#FFFFFF",
            fg="#666666"
        )
        self._loading_label.pack()
        return self._load_btn_frame

    def _load_more(self):
        """加载更多数据"""
        if self._loading or self._loaded_count >= self._total:
            return

        self._loading = True
        self._load_more_btn.config(state="disabled")
        self._loading_label.config(text="加载中...")

        def load_thread():
            result = self.data_loader(self._loaded_count, self.page_size)
            self.after(0, lambda: self._on_data_loaded(result))

        thread = threading.Thread(target=load_thread, daemon=True)
        thread.start()

    def _on_data_loaded(self, result: dict):
        """数据加载完成回调"""
        self._loading = False
        self._load_more_btn.config(state="normal")
        self._loading_label.config(text="")

        data = result.get("data", [])
        self._total = result.get("total", 0)

        for item in data:
            self.insert("", tk.END, values=item)

        self._loaded_count += len(data)

        if self._loaded_count >= self._total or self._loaded_count >= self.max_visible:
            self._load_btn_frame.pack_forget()
        else:
            self._load_btn_frame.pack()
            self._loading_label.config(text=f"已加载 {self._loaded_count}/{self._total} 条")

    def initial_load(self):
        """执行首次加载"""
        if self.data_loader:
            self._load_more()

    def clear_all(self):
        """清空所有数据"""
        for item in self.get_children():
            self.delete(item)
        self._loaded_count = 0
        self._total = float('inf')


class DebouncedEntry(ttk.Entry):
    """
    带防抖的输入框

    特性：
    - 输入停止 400ms 后才触发回调
    - 避免每次按键都执行搜索
    """

    def __init__(self, parent, callback: Callable[[str], None] = None,
                 debounce_ms: int = 400, **kwargs):
        """
        Args:
            parent: 父窗口
            callback: 输入变化回调函数，接收 keyword 参数
            debounce_ms: 防抖延迟（毫秒）
            **kwargs: ttk.Entry 其他参数
        """
        self.callback = callback
        self.debounce_ms = debounce_ms
        self._after_id = None

        super().__init__(parent, **kwargs)

        self._var = tk.StringVar()
        self.configure(textvariable=self._var)

        self.bind("<KeyRelease>", self._on_key_release)

    def _on_key_release(self, event=None):
        """按键释放时，延迟触发回调"""
        if self._after_id:
            self.after_cancel(self._after_id)

        keyword = self._var.get()

        self._after_id = self.after(self.debounce_ms, lambda: self._do_callback(keyword))

    def _do_callback(self, keyword: str):
        """执行回调"""
        if self.callback:
            self.callback(keyword)

    def get_value(self) -> str:
        """获取当前输入值"""
        return self._var.get()

    def clear(self):
        """清空输入"""
        self._var.set("")
