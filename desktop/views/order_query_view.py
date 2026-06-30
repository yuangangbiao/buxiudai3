# -*- coding: utf-8 -*-
"""
订单查询视图 - 统一查询入口
支持模糊搜索 + 订单全生命周期详情
"""
import tkinter as tk
from tkinter import ttk, messagebox
import sys, os

from config import COLORS, FONTS
from constants import OrderStatus
from models.order import OrderDAO
from utils.auto_refresh_mixin import AutoRefreshMixin


def _format_date(val):
    """安全格式化日期，处理datetime对象或字符串"""
    if hasattr(val, 'strftime'):
        return val.strftime('%Y-%m-%d')
    elif val:
        return str(val)[:10]
    return "-"


# ─── OrderDetailDialog 动态导入（兼容开发/打包环境）───
def _get_detail_dialog_class():
    """获取订单详情弹窗类，兼容 _MEIPASS 打包路径（pathlib 规范化中文路径）"""
    _internal = getattr(sys, '_MEIPASS', None)
    if _internal:
        # 打包环境：order_lookup 在 _MEIPASS 同级目录
        lookup_path = str(__import__('pathlib').Path(_internal).parent)
    else:
        # 开发环境：order_lookup 在 steel_belt_tracking 的上级目录
        lookup_path = str(__import__('pathlib').Path(__file__).resolve().parent.parent.parent)

    lookup_path = os.path.normpath(lookup_path)
    if lookup_path not in sys.path:
        sys.path.insert(0, lookup_path)

    try:
        from order_lookup.ui.order_detail import OrderDetailDialog
        return OrderDetailDialog
    except (ImportError, ModuleNotFoundError) as e:
        print(f"导入OrderDetailDialog失败: {e}")
        return None


class OrderQueryView(tk.Frame):
    """订单查询视图"""

    MAX_VISIBLE_ROWS = 1000
    PAGE_SIZE = 100

    def __init__(self, parent):
        super().__init__(parent, bg=COLORS["bg_main"])
        self.parent = parent
        self.current_page = 1
        self.total_pages = 0
        self.total_count = 0
        self.current_keyword = ""
        self.current_filters = {}
        self._build_ui()
        self._refresh()
        # trace 放在初始化完成后，避免占位文本误触发搜索
        self.search_var.trace_add("write", lambda *_: self._on_keyword_change())

    # ─── UI 构建 ──────────────────────────────────────────

    def _build_ui(self):
        # ── 顶部搜索栏 ──
        top = tk.Frame(self, bg="#2c3e50", height=56)
        top.pack(fill="x", padx=0, pady=0)
        top.pack_propagate(False)

        tk.Label(top, text="🔍 订单全程查询",
                font=FONTS["large_bold"],
                fg="white", bg="#2c3e50").pack(side="left", padx=16)

        search_frame = tk.Frame(top, bg="#2c3e50")
        search_frame.pack(side="right", padx=16)

        self.search_var = tk.StringVar()
        ent = tk.Entry(search_frame, textvariable=self.search_var,
                      font=FONTS["body"], width=30,
                      bg="white", fg="#1E293B",
                      insertbackground="#2c3e50",
                      relief="flat", bd=0)
        ent.pack(side="left", padx=(0, 6), pady=14)
        ent.insert(0, "输入订单号 / 客户名称 / 产品类型...")
        ent.bind("<FocusIn>", lambda e: self._on_search_focus_in(ent))
        ent.bind("<FocusOut>", lambda e: self._on_search_focus_out(ent))
        ent.bind("<Return>", lambda e: self._do_search())
        # 绑定输入事件，确保输入时直接显示结果
        ent.bind("<KeyRelease>", lambda e: self._on_keyword_change())
        self.search_entry = ent

        tk.Button(search_frame, text="查询", command=self._do_search,
                font=FONTS["normal_bold"],
                bg=COLORS["accent"], fg="white",
                activebackground="#1565C0",
                relief="flat", padx=16, pady=4,
                cursor="hand2").pack(side="left", pady=14)
        tk.Button(search_frame, text="🔄 重新加载", command=self.load_data,
                font=FONTS["normal_bold"],
                bg="#7E57C2", fg="white",
                activebackground="#5E35B1",
                relief="flat", padx=16, pady=4,
                cursor="hand2").pack(side="left", pady=14)

        # ── 主体：左右布局 ──
        body = tk.Frame(self, bg=COLORS["bg_main"])
        body.pack(fill="both", expand=True, padx=12, pady=12)

        # 左侧：搜索结果列表
        left = tk.Frame(body, bg=COLORS["bg_main"])
        left.pack(side="left", fill="both", expand=True)

        tk.Label(left, text="📋 搜索结果",
                font=FONTS["subtitle"], fg=COLORS["text_secondary"],
                bg=COLORS["bg_main"]).pack(anchor="w", pady=(0, 6))

        # 结果表格
        table_frame = tk.Frame(left, bg="white", bd=1, relief="solid")
        table_frame.pack(fill="both", expand=True)

        cols = ["order_no", "customer_name", "product_type", "status", "delivery_date"]
        headers = ["订单号", "客户名称", "产品类型", "状态", "交货日期"]

        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings",
                                 height=18, style="OrderQuery.Treeview")
        for col, hdr in zip(cols, headers):
            self.tree.heading(col, text=hdr)
            self.tree.column(col, width=160 if col == "customer_name" else 120,
                           anchor="center" if col != "customer_name" else "w")
        self.tree.pack(side="left", fill="both", expand=True)

        scroll_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scroll_y.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scroll_y.set)

        self.tree.tag_configure("even", background="#F8FAFC")
        self.tree.tag_configure("odd", background="white")

        self.tree.bind("<<TreeviewSelect>>", self._on_row_select)
        self.tree.bind("<Double-Button-1>", lambda e: self._open_detail())

        # 结果数量提示
        self.result_label = tk.Label(left, text="",
                font=FONTS["small"], fg="#888", bg=COLORS["bg_main"])
        self.result_label.pack(anchor="w", pady=(6, 0))

        # 分页控件
        pager_frame = tk.Frame(left, bg=COLORS["bg_main"])
        pager_frame.pack(anchor="w", pady=(4, 0))
        self.prev_btn = tk.Button(pager_frame, text="上一页", command=self._prev_page,
                                 state="disabled", font=FONTS["small"],
                                 relief="flat", bg="#E5E7EB")
        self.prev_btn.pack(side="left", padx=2)
        self.page_label = tk.Label(pager_frame, text="第 1 / 1 页",
                                   font=FONTS["small"], fg="#666", bg=COLORS["bg_main"])
        self.page_label.pack(side="left", padx=8)
        self.next_btn = tk.Button(pager_frame, text="下一页", command=self._next_page,
                                 state="disabled", font=FONTS["small"],
                                 relief="flat", bg="#E5E7EB")
        self.next_btn.pack(side="left", padx=2)
        tk.Button(pager_frame, text="加载全部", command=self._load_all,
                 font=FONTS["small"], fg="#666", relief="flat",
                 bg="#F3F4F6").pack(side="left", padx=(8, 2))

        # 右侧：快速预览卡片
        right = tk.Frame(body, bg=COLORS["bg_main"], width=280)
        right.pack(side="right", fill="y", padx=(12, 0))
        right.pack_propagate(False)

        tk.Label(right, text="📌 订单预览",
                font=FONTS["subtitle"], fg=COLORS["text_secondary"],
                bg=COLORS["bg_main"]).pack(anchor="w", pady=(0, 6))

        self.preview_card = tk.Frame(right, bg="white", bd=1, relief="solid",
                                     padx=12, pady=12)
        self.preview_card.pack(fill="x")

        self.preview_fields = {}
        preview_labels = [
            ("order_no", "订单号"), ("customer_name", "客户名称"),
            ("product_type", "产品类型"), ("status", "状态"),
            ("quantity", "数量"), ("unit", "单位"),
            ("total_amount", "总金额"), ("delivery_date", "交货日期"),
        ]
        for key, label in preview_labels:
            row = tk.Frame(self.preview_card, bg="white")
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"{label}：",
                    font=FONTS["small"], fg="#666", bg="white",
                    width=8, anchor="e").pack(side="left")
            val = tk.Label(row, text="-",
                          font=FONTS["small_bold"], fg=COLORS["text_primary"],
                          bg="white", anchor="w")
            val.pack(side="left", fill="x", expand=True)
            self.preview_fields[key] = val

        # 状态标签
        status_row = tk.Frame(self.preview_card, bg="white")
        status_row.pack(fill="x", pady=(8, 0))
        self.status_badge = tk.Label(status_row, text="",
                font=FONTS["normal_bold"], fg="white",
                bg="#6B7280", padx=8, pady=2)
        self.status_badge.pack(anchor="w")

        # 查看详情按钮
        btn_frame = tk.Frame(right, bg=COLORS["bg_main"], pady=12)
        btn_frame.pack(fill="x")
        self.detail_btn = tk.Button(btn_frame, text="🔎 查看完整详情",
                font=FONTS["normal_bold"],
                bg=COLORS["accent"], fg="white",
                activebackground="#1565C0",
                relief="flat", pady=8,
                state="disabled", cursor="arrow",
                command=self._open_detail)
        self.detail_btn.pack(fill="x")

        tk.Label(btn_frame, text="双击列表行也可打开详情",
                font=FONTS["tiny"], fg="#999",
                bg=COLORS["bg_main"]).pack(pady=(6, 0))

        self._clear_preview()
        self.selected_order = None

    # ─── 数据刷新 ─────────────────────────────────────────

    def _refresh(self, keyword: str = "", page: int = 1):
        """刷新列表（分页版本）"""
        for row in self.tree.get_children():
            self.tree.delete(row)

        self.current_keyword = keyword
        self.current_page = page

        filters = {}
        if keyword.strip():
            filters["keyword"] = keyword.strip()

        result = OrderDAO.get_all_paginated(
            filters=filters,
            page=page,
            page_size=self.PAGE_SIZE,
            max_total=self.MAX_VISIBLE_ROWS
        )

        rows = result["data"]
        self.total_count = result["total"]
        self.total_pages = result["total_pages"]

        status_colors = {
            OrderStatus.PENDING.value: "#94A3B8", OrderStatus.CONFIRMED.value: "#3B82F6", OrderStatus.SCHEDULED.value: "#8B5CF6",
            OrderStatus.PRODUCTION.value: "#F59E0B", OrderStatus.QC.value: "#06B6D4", OrderStatus.PENDING_SHIP.value: "#10B981",
            OrderStatus.SHIPPED.value: "#22C55E", OrderStatus.FINISHED.value: "#16A34A", OrderStatus.CANCELLED.value: "#EF4444",
        }

        for i, row in enumerate(rows):
            tags = ("even" if i % 2 == 0 else "odd",)
            status = row.get("status", "")
            self.tree.insert("", "end", values=[
                row.get("order_no", ""),
                row.get("customer_name", ""),
                row.get("product_type", ""),
                status,
                _format_date(row.get("delivery_date")),
            ], tags=tags, iid=str(row.get("id", "")))

        has_more = self.total_count > self.MAX_VISIBLE_ROWS
        if keyword.strip():
            info = f"共 {len(rows)} 条匹配结果"
            if has_more:
                info += f"（已限制显示 {self.MAX_VISIBLE_ROWS} 条，请使用精确搜索）"
            self.result_label.config(text=info)
        else:
            self.result_label.config(
                text=f"共 {self.total_count} 条订单" +
                     (f"（已限制显示前 {self.MAX_VISIBLE_ROWS} 条）" if has_more else ""))

        self._update_pager()

    def _update_pager(self):
        """更新分页控件状态"""
        self.page_label.config(text=f"第 {self.current_page} / {max(1, self.total_pages)} 页")
        self.prev_btn.config(state="normal" if self.total_pages > 1 and self.current_page > 1 else "disabled")
        self.next_btn.config(state="normal" if self.current_page < self.total_pages else "disabled")

    def _prev_page(self):
        """上一页"""
        if self.current_page > 1:
            self.current_page -= 1
            self._refresh(self.current_keyword, self.current_page)

    def _next_page(self):
        """下一页"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self._refresh(self.current_keyword, self.current_page)

    def _load_all(self):
        """用户主动加载全部（按当前筛选条件）"""
        self.next_btn.config(state="disabled", text="加载中...")
        self.after(50, lambda: self._do_load_all())

    def _do_load_all(self):
        """执行全部加载"""
        for row in self.tree.get_children():
            self.tree.delete(row)

        filters = {}
        if self.current_keyword.strip():
            filters["keyword"] = self.current_keyword.strip()

        rows = OrderDAO.get_all(filters)

        status_colors = {
            OrderStatus.PENDING.value: "#94A3B8", OrderStatus.CONFIRMED.value: "#3B82F6", OrderStatus.SCHEDULED.value: "#8B5CF6",
            OrderStatus.PRODUCTION.value: "#F59E0B", OrderStatus.QC.value: "#06B6D4", OrderStatus.PENDING_SHIP.value: "#10B981",
            OrderStatus.SHIPPED.value: "#22C55E", OrderStatus.FINISHED.value: "#16A34A", OrderStatus.CANCELLED.value: "#EF4444",
        }

        for i, row in enumerate(rows):
            tags = ("even" if i % 2 == 0 else "odd",)
            status = row.get("status", "")
            self.tree.insert("", "end", values=[
                row.get("order_no", ""),
                row.get("customer_name", ""),
                row.get("product_type", ""),
                status,
                _format_date(row.get("delivery_date")),
            ], tags=tags, iid=str(row.get("id", "")))

        self.result_label.config(text=f"已加载全部 {len(rows)} 条数据")
        self.next_btn.config(state="disabled", text="已全部加载")

    def _on_keyword_change(self):
        """实时搜索（300ms 防抖）"""
        self._after_id = self.after(300, self._do_search)

    def load_data(self):
        """从MySQL重新加载全部数据"""
        self._refresh(keyword=self.current_keyword or "", page=self.current_page or 1)

    def _do_search(self):
        """执行搜索"""
        if hasattr(self, '_after_id'):
            self.after_cancel(self._after_id)
        self.current_page = 1
        self._refresh(self.search_var.get(), page=1)

    def _on_search_focus_in(self, entry):
        if entry.get() == "输入订单号 / 客户名称 / 产品类型...":
            entry.delete(0, tk.END)
            entry.config(fg="#1E293B")

    def _on_search_focus_out(self, entry):
        if not entry.get():
            entry.insert(0, "输入订单号 / 客户名称 / 产品类型...")
            entry.config(fg="#999")

    # ─── 行选中 ───────────────────────────────────────────

    def _on_row_select(self, event):
        selection = self.tree.selection()
        if not selection:
            return
        order_id = int(selection[0])
        order = OrderDAO.get_by_id(order_id)
        if not order:
            return
        self.selected_order = order
        self._show_preview(order)

    def _show_preview(self, order: dict):
        """显示右侧预览卡片"""
        preview_map = {
            "order_no": order.get("order_no", "-"),
            "customer_name": order.get("customer_name", "-"),
            "product_type": order.get("product_type", "-"),
            "quantity": str(order.get("quantity", "-")),
            "unit": order.get("unit", "-"),
            "total_amount": f"¥{order.get('total_amount', 0):,.2f}",
            "delivery_date": _format_date(order.get("delivery_date")),
        }
        for key, val in preview_map.items():
            self.preview_fields[key].config(text=val)

        status = order.get("status", "")
        color = {
            OrderStatus.PENDING.value: "#94A3B8", OrderStatus.CONFIRMED.value: "#3B82F6", OrderStatus.SCHEDULED.value: "#8B5CF6",
            OrderStatus.PRODUCTION.value: "#F59E0B", OrderStatus.QC.value: "#06B6D4", OrderStatus.PENDING_SHIP.value: "#10B981",
            OrderStatus.SHIPPED.value: "#22C55E", OrderStatus.FINISHED.value: "#16A34A", OrderStatus.CANCELLED.value: "#EF4444",
        }.get(status, "#6B7280")
        self.status_badge.config(text=f"【{status}】", bg=color)
        self.detail_btn.config(state="normal", cursor="hand2")

    def _clear_preview(self):
        for key in self.preview_fields:
            self.preview_fields[key].config(text="-")
        self.status_badge.config(text="【--】", bg="#6B7280")
        self.detail_btn.config(state="disabled", cursor="arrow")

    # ─── 状态同步 ─────────────────────────────────────────

    def _sync_status(self):
        """从生产系统同步订单状态"""
        try:
            from utils.op_logger import log_ui
            from models.process import ProcessDAO
            from models.order import OrderDAO
            from models.database import get_connection

            conn = get_connection()
            cursor = conn.cursor()
            updated = 0

            cursor.execute("SELECT DISTINCT order_id FROM process_records WHERE order_id IS NOT NULL")
            order_ids = [r['order_id'] for r in cursor.fetchall()]

            for oid in order_ids:
                cursor.execute("""
                    SELECT COUNT(*) as total,
                           SUM(CASE WHEN status = '已完成' THEN 1 ELSE 0 END) as done
                    FROM process_records WHERE order_id = %s
                """, (oid,))
                row = cursor.fetchone()
                if row and row['total'] > 0 and row['total'] == row['done']:
                    cursor.execute("UPDATE orders SET status = '生产中' WHERE id = %s AND status NOT IN ('已完成','已取消')", (oid,))
                    if cursor.rowcount:
                        updated += 1

            conn.commit()
            cursor.close()
            conn.close()

            log_ui("订单查询", "状态同步", f"更新 {updated} 条订单状态")
            messagebox.showinfo("同步完成", f"状态同步完成\n共更新 {updated} 条订单状态")
            self._refresh(self.current_keyword, self.current_page)
        except Exception as e:
            import traceback
            messagebox.showerror("同步失败", f"状态同步失败: {str(e)}\n{traceback.format_exc()}")

    # ─── 打开详情 ─────────────────────────────────────────

    def _open_detail(self):
        if not self.selected_order:
            return
        OrderDetailDialog = _get_detail_dialog_class()
        if OrderDetailDialog is None:
            messagebox.showwarning("提示", "订单详情组件未找到，请确认系统完整安装。")
            return
        OrderDetailDialog(self, self.selected_order)
