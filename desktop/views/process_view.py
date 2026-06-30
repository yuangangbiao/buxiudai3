# -*- coding: utf-8 -*-
"""
工序追踪视图
"""
import tkinter as tk
from tkinter import ttk, messagebox
import time
import threading
from config import COLORS, FONTS, PROCESSES, RESOURCE_DIR, LAYOUT
from constants import ProcessStatus, OrderStatus, ProductionStatus


def _calc_status(completed_qty, planned_qty):
    """根据数量计算工序状态（桌面端统一逻辑）"""
    c = float(completed_qty or 0)
    p = float(planned_qty or 0)
    if p > 0 and c >= p:
        return "已完成"
    if c > 0:
        return "生产中"
    return "待开始"
from i18n import t
from models.order import OrderDAO
from models.production import ProductionDAO
from models.process import ProcessDAO
from models.database import get_connection
from services.process_service import ProcessService
from desktop.views.dialogs import popup_form, alert, confirm
from utils.helpers import format_date
from utils.op_logger import log_ui
from utils.auto_refresh_mixin import AutoRefreshMixin
import json, os, logging

logger = logging.getLogger(__name__)


class ProcessView(AutoRefreshMixin, tk.Frame):

    def __init__(self, parent, load_orders_on_init=True):
        super().__init__(parent, bg=COLORS["bg_main"])
        self.current_order_id = None
        self.current_prod_id = None
        self.templates = None
        self._cached_order = None
        self._cached_records = None
        self._search_after_id = None
        self._load_orders_on_init = load_orders_on_init
        self.svc = ProcessService()
        self.init_ui()
        if self._load_orders_on_init:
            self.load_work_orders()
        self._start_auto_refresh()

    def _refresh_data(self):
        self.load_work_orders()

    def _load_templates(self):
        """延迟加载工序模板"""
        if self.templates is None:
            from utils.process_templates import get_all_process_templates
            self.templates = get_all_process_templates()
        return self.templates

    def _save_templates(self):
        """保存工序模板"""
        from utils.process_templates import save_process_templates
        save_process_templates(self.templates)

    def init_ui(self):
        # ═══════════════════════════════════════════════════════
        # 第一行：主工具栏（深蓝底，白字）
        # ═══════════════════════════════════════════════════════
        header = tk.Frame(self, bg=COLORS["primary"], height=48)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        tk.Label(header, text=t('process.title'), font=FONTS["large_bold"],
                fg=COLORS["text_white"], bg=COLORS["primary"]).pack(side=tk.LEFT, padx=LAYOUT["padding"]["large"])

        # 搜索框
        search_frame = tk.Frame(header, bg=COLORS["primary"])
        search_frame.pack(side=tk.LEFT, padx=LAYOUT["padding"]["medium"])
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                font=FONTS["body"], width=18, bg="#E8F0FE",
                insertbackground="#1A237E", relief=tk.FLAT, bd=0)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 4), ipady=2)
        self.search_entry.bind("<Return>", lambda e: self._do_search())
        self.search_entry.bind("<KeyRelease>", lambda e: self._on_search_change())
        tk.Button(search_frame, text="🔍", font=FONTS["body"], bg="#E8F0FE",
                fg=COLORS["primary"], relief=tk.FLAT, padx=6, pady=1,
                cursor="hand2", command=self._do_search).pack(side=tk.LEFT)
        self.search_hint = tk.Label(search_frame, text="", font=FONTS["small"],
                bg=COLORS["primary"], fg="#BBDEFB")
        self.search_hint.pack(side=tk.LEFT, padx=(4, 0))

        # 右侧按钮组
        header_right = tk.Frame(header, bg=COLORS["primary"])
        header_right.pack(side=tk.RIGHT, padx=LAYOUT["padding"]["medium"])

        # 功能按钮组
        btn_configs = [
            ("➕ 添加", self._add_process),
            ("✏️ 编辑", self._edit_process),
            ("🗑️ 删除", self._delete_process),
            ("📋 模板", self._show_template_dialog),
            ("⬆️ 上移", self._move_up),
            ("⬇️ 下移", self._move_down),
        ]
        btn_frame = tk.Frame(header_right, bg=COLORS["primary"])
        btn_frame.pack(side=tk.LEFT)
        for text, cmd in btn_configs:
            tk.Button(btn_frame, text=text, font=FONTS["body"], bg="#1565C0",
                    fg=COLORS["text_white"], relief=tk.FLAT, padx=8, pady=3,
                    cursor="hand2", command=cmd).pack(side=tk.LEFT, padx=2)

        tk.Frame(header, width=1, bg="#0D47A1").pack(side=tk.LEFT, padx=8, fill=tk.Y, pady=8)

        # 微信报工发布按钮
        tk.Button(header_right, text="💬 发布报工", font=FONTS["body"],
                bg="#7E57C2", fg=COLORS["text_white"], relief=tk.FLAT, padx=10, pady=3,
                cursor="hand2", command=self._publish_to_wechat).pack(side=tk.LEFT, padx=2)

        tk.Button(header_right, text="🔄 重发死信", font=FONTS["body"],
                bg="#E53935", fg=COLORS["text_white"], relief=tk.FLAT, padx=8, pady=3,
                cursor="hand2", command=self._retry_dead_tasks).pack(side=tk.LEFT, padx=2)

        # 发布模式切换
        self.publish_mode_var = tk.StringVar(value="manual")
        mode_frame = tk.Frame(header_right, bg=COLORS["primary"])
        mode_frame.pack(side=tk.LEFT, padx=2)
        ttk.Radiobutton(mode_frame, text="手动", variable=self.publish_mode_var, 
                       value="manual", style="TRadiobutton").pack(side=tk.LEFT, padx=2)
        ttk.Radiobutton(mode_frame, text="自动", variable=self.publish_mode_var, 
                       value="auto", style="TRadiobutton").pack(side=tk.LEFT, padx=2)

        tk.Frame(header, width=1, bg="#0D47A1").pack(side=tk.LEFT, padx=8, fill=tk.Y, pady=8)

        # 质检跳转
        tk.Button(header_right, text="✅ 质检", font=FONTS["body"],
                bg=COLORS["green_dark"], fg=COLORS["text_white"], relief=tk.FLAT, padx=10, pady=3,
                cursor="hand2", command=self._goto_quality).pack(side=tk.LEFT, padx=2)

        tk.Frame(header, width=1, bg="#0D47A1").pack(side=tk.LEFT, padx=8, fill=tk.Y, pady=8)

        # ⚙️ 工序规则配置
        tk.Button(header_right, text="⚙️ 规则", font=FONTS["body"],
                bg="#546E7A", fg=COLORS["text_white"], relief=tk.FLAT, padx=10, pady=3,
                cursor="hand2", command=self._open_process_calc_rules).pack(side=tk.LEFT, padx=2)

        # 🔧 计算工序
        tk.Button(header_right, text="🔧 计算", font=FONTS["body"],
                bg="#FF7043", fg=COLORS["text_white"], relief=tk.FLAT, padx=10, pady=3,
                cursor="hand2", command=self._recalculate_processes).pack(side=tk.LEFT, padx=2)

        tk.Button(header_right, text="🔄 刷新", font=FONTS["body"],
                bg=COLORS["gray_blue"], fg=COLORS["text_white"], relief=tk.FLAT, padx=10, pady=3,
                cursor="hand2", command=self.load_processes).pack(side=tk.LEFT, padx=(6, 0))
        tk.Button(header_right, text="🔄 状态同步", font=FONTS["body"],
                bg="#7E57C2", fg=COLORS["text_white"], relief=tk.FLAT, padx=10, pady=3,
                cursor="hand2", command=self._sync_status).pack(side=tk.LEFT, padx=(6, 0))

        # ═══════════════════════════════════════════════════════
        # 第二行：订单选择栏
        # ═══════════════════════════════════════════════════════
        order_bar = tk.Frame(self, bg="#F0F4FF", height=40)
        order_bar.pack(fill=tk.X, side=tk.TOP)
        order_bar.pack_propagate(False)

        self.order_combo = ttk.Combobox(order_bar, width=45, font=FONTS["body"],
                state="readonly", height=30)
        self.order_combo.pack(side=tk.LEFT, padx=LAYOUT["padding"]["large"], pady=6)
        self.order_combo.bind("<<ComboboxSelected>>", lambda e: self.on_order_changed())

        # 搜索按钮
        tk.Button(order_bar, text=t('process.search_work_order'), font=FONTS["body"],
                bg=COLORS["primary"], fg=COLORS["text_white"], relief=tk.FLAT, padx=8, pady=3,
                cursor="hand2", command=lambda: self.load_work_orders()).pack(side=tk.LEFT, padx=5)

        self.order_info_label = tk.Label(order_bar, text="",
                font=FONTS["body"], fg="#5C6BC0", bg="#F0F4FF",
                anchor="e")
        self.order_info_label.pack(side=tk.RIGHT, padx=LAYOUT["padding"]["large"], fill=tk.X, expand=True)

        # ═══════════════════════════════════════════════════════
        # 第三行：主内容区
        # ═══════════════════════════════════════════════════════
        self.content_frame = tk.Frame(self, bg=COLORS["bg_main"])
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=LAYOUT["padding"]["medium"], pady=(6, 6))

        # ── 左侧：工序进度列表 ──────────────────────────────
        left = tk.Frame(self.content_frame, bg=COLORS["bg_main"])
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 卡片标题
        card_header = tk.Frame(left, bg=COLORS["bg_main"])
        card_header.pack(fill=tk.X, pady=(0, 4))
        tk.Label(card_header, text="📋 工序进度表", font=FONTS["subtitle"],
                fg=COLORS["text_primary"], bg=COLORS["bg_main"]).pack(side=tk.LEFT)
        self.record_count_label = tk.Label(card_header, text=t('process.record_count', count="0"),
                font=FONTS["body"], fg="#90A4AE", bg=COLORS["bg_main"])
        self.record_count_label.pack(side=tk.RIGHT)

        # 工序列表（卡片式背景）
        list_card = tk.Frame(left, bg=COLORS["bg_card"], relief="solid", bd=1,
                            highlightbackground="#E0E0E0", highlightthickness=1)
        list_card.pack(fill=tk.BOTH, expand=True)

        self.process_tree = ttk.Treeview(list_card,
                columns=("seq", "name", "worker", "total", "unit", "completed", "today", "percent", "qualified", "hours", "status", "outsource"),
                show="headings", height=LAYOUT["heights"]["large"])
        for col, txt, w in [
            ("seq", "序", 38), ("name", "工序名称", 90), ("worker", "执行人", 72),
            ("total", "计划", 48), ("unit", "单位", 42),
            ("completed", "完成", 48), ("today", "今日", 42),
            ("percent", "进度", 46), ("qualified", "合格", 48),
            ("hours", "工时", 44), ("status", "状态", 58), ("outsource", "外协", 46)
        ]:
            self.process_tree.heading(col, text=txt)
            self.process_tree.column(col, width=w,
                anchor="center" if col not in ("name", "worker") else "w",
                minwidth=36)

        scrollbar = ttk.Scrollbar(list_card, orient=tk.VERTICAL, command=self.process_tree.yview)
        self.process_tree.configure(yscrollcommand=scrollbar.set)
        self.process_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.process_tree.bind("<Double-1>", self.on_process_double_click)
        self.process_tree.bind("<Button-3>", self._show_context_menu)
        self.process_tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.process_tree.tag_configure("done", background="#E8F5E9")
        self.process_tree.tag_configure("doing", background="#FFF8E1")
        self.process_tree.tag_configure("pending", background="#FAFAFA")
        self.process_tree.tag_configure("outsource", background="#FFEBEE")

        # ── 右侧：报工面板 ──────────────────────────────────
        right = tk.Frame(self.content_frame, bg="#ECEFF1", width=360)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(8, 0))
        right.pack_propagate(False)

        # 标题栏
        title_bar = tk.Frame(right, bg=COLORS["bg_card"], pady=8)
        title_bar.pack(fill=tk.X)
        tk.Label(title_bar, text="📝 工序报工", font=FONTS["subtitle"],
                fg=COLORS["primary"], bg=COLORS["bg_card"]).pack(side=tk.LEFT, padx=14)

        # 进度概览卡
        progress_card = tk.Frame(right, bg=COLORS["bg_card"], padx=14, pady=6)
        progress_card.pack(fill=tk.X)
        for col, lbl_text, key in [(0, t('process.labels.total'), "total"), (1, t('process.labels.completed'), "completed"), (2, t('process.labels.qualified'), "qualified")]:
            card = tk.Frame(progress_card, bg="#F5F5F5", padx=10, pady=6, relief="groove", bd=1)
            card.grid(row=0, column=col, sticky="ew", padx=2)
            tk.Label(card, text=lbl_text, font=FONTS["small"],
                    fg="#78909C", bg="#F5F5F5").pack()
            val_lbl = tk.Label(card, text="--", font=FONTS["large_bold"],
                    fg=COLORS["primary"], bg="#F5F5F5")
            val_lbl.pack()
            setattr(self, f"stat_{key}_label", val_lbl)
        progress_card.grid_columnconfigure(0, weight=1)
        progress_card.grid_columnconfigure(1, weight=1)
        progress_card.grid_columnconfigure(2, weight=1)

        tk.Frame(right, height=1, bg="#E0E0E0").pack(fill=tk.X, padx=14)

        # 报工表单
        form_card = tk.Frame(right, bg=COLORS["bg_card"], padx=14, pady=4)
        form_card.pack(fill=tk.X)

        def _form_row(parent, row, label, widget, **kw):
            tk.Label(parent, text=label, font=FONTS["body"], fg="#455A64",
                    bg=COLORS["bg_card"], anchor="e", width=8).grid(row=row, column=0, sticky="e", pady=4)
            widget.grid(row=row, column=1, sticky="ew", pady=4, padx=(4, 0))
            parent.grid_columnconfigure(1, weight=1)

        tk.Label(form_card, text=t('process.labels.process'), font=FONTS["body"], fg="#455A64",
                bg=COLORS["bg_card"], anchor="e", width=8).grid(row=0, column=0, sticky="e", pady=4)
        self.proc_combo = ttk.Combobox(form_card, values=PROCESSES,
                font=FONTS["body"], state="readonly")
        self.proc_combo.current(0)
        self.proc_combo.grid(row=0, column=1, sticky="ew", pady=4, padx=(4, 0))
        self.proc_combo.bind("<<ComboboxSelected>>", self._on_proc_selected)
        form_card.grid_columnconfigure(1, weight=1)

        tk.Label(form_card, text=t('process.labels.qty'), font=FONTS["body"], fg="#455A64",
                bg=COLORS["bg_card"], anchor="e", width=8).grid(row=1, column=0, sticky="e", pady=4)
        self.qty_entry = ttk.Entry(form_card, font=FONTS["body"])
        self.qty_entry.grid(row=1, column=1, sticky="ew", pady=4, padx=(4, 0))
        self.qty_entry.insert(0, "0")

        tk.Label(form_card, text=t('process.labels.qualified_qty'), font=FONTS["body"], fg="#455A64",
                bg=COLORS["bg_card"], anchor="e", width=8).grid(row=2, column=0, sticky="e", pady=4)
        self.qualified_entry = ttk.Entry(form_card, font=FONTS["body"])
        self.qualified_entry.grid(row=2, column=1, sticky="ew", pady=4, padx=(4, 0))
        self.qualified_entry.insert(0, "0")

        tk.Label(form_card, text=t('process.labels.hours'), font=FONTS["body"], fg="#455A64",
                bg=COLORS["bg_card"], anchor="e", width=8).grid(row=3, column=0, sticky="e", pady=4)
        self.hours_entry = ttk.Entry(form_card, font=FONTS["body"])
        self.hours_entry.grid(row=3, column=1, sticky="ew", pady=4, padx=(4, 0))
        self.hours_entry.insert(0, "0")

        tk.Label(form_card, text=t('process.labels.worker'), font=FONTS["body"], fg="#455A64",
                bg=COLORS["bg_card"], anchor="e", width=8).grid(row=4, column=0, sticky="e", pady=4)
        self.worker_entry = ttk.Entry(form_card, font=FONTS["body"])
        self.worker_entry.grid(row=4, column=1, sticky="ew", pady=4, padx=(4, 0))

        tk.Label(form_card, text=t('process.labels.remark'), font=FONTS["body"], fg="#455A64",
                bg=COLORS["bg_card"], anchor="e", width=8).grid(row=5, column=0, sticky="ne", pady=4)
        self.remark_text = tk.Text(form_card, font=FONTS["body"], height=2, relief="solid", bd=1)
        self.remark_text.grid(row=5, column=1, sticky="ew", pady=4, padx=(4, 0))

        # 提交按钮
        btn_submit = tk.Frame(right, bg=COLORS["bg_card"], pady=6)
        btn_submit.pack(fill=tk.X, padx=14)
        tk.Button(btn_submit, text=t('process.submit'), font=FONTS["body"],
                bg=COLORS["primary"], fg=COLORS["text_white"], relief=tk.FLAT, pady=7,
                cursor="hand2", command=self.submit_report).pack(fill=tk.X, ipady=2)

        # 进度条区
        progress_section = tk.Frame(right, bg="#ECEFF1", padx=14, pady=6)
        progress_section.pack(fill=tk.X, pady=(4, 8))
        self.progress_label = tk.Label(progress_section,
                text=t('process.overall_progress', percent="0%"), font=FONTS["body"],
                fg=COLORS["primary"], bg="#ECEFF1", anchor="w")
        self.progress_label.pack()
        self.progress_bar = ttk.Progressbar(progress_section, length=320, mode="determinate")
        self.progress_bar.pack(pady=(3, 0))

    def _publish_to_wechat(self):
        """发布工序报工任务到微信报工系统（异步后台线程，避免UI卡死）"""
        if not self.current_order_id:
            alert("请先选择一个订单！", "提示")
            return

        publish_mode = self.publish_mode_var.get()

        if not messagebox.askyesno("确认发布", f"确定要将订单 {self.current_order_id} 的工序任务发布到微信报工系统吗？\n发布模式: {'自动' if publish_mode == 'auto' else '手动'}"):
            return

        order = OrderDAO.get_by_id(self.current_order_id)
        if not order:
            messagebox.showerror("错误", f"找不到订单 {self.current_order_id}")
            return

        prod = ProductionDAO.get_by_order_id(self.current_order_id)
        if not prod:
            messagebox.showerror("错误", f"找不到订单 {self.current_order_id} 的生产记录")
            return

        processes = ProcessDAO.get_by_production(prod['id'])
        if not processes:
            messagebox.showinfo("提示", "该订单没有工序需要发布")
            return

        if hasattr(self, '_publishing') and self._publishing:
            alert("正在发布中，请稍候...", "提示")
            return

        self._publishing = True
        self._publish_status_label = tk.Label(
            self, text="⏳ 正在发布工序任务...",
            font=FONTS["body"], fg="#7E57C2", bg=COLORS["bg_main"]
        )
        self._publish_status_label.pack(pady=(4, 0))

        order_no = order.get('order_no', '')
        order_no = prod.get('order_no', '')
        quantity = prod.get('quantity', 0)

        def do_publish():
            """后台线程执行发布"""
            try:
                from services.wechat_report_service import WeChatReportService
                success_count = 0
                fail_count = 0
                fail_details = []

                for proc in processes:
                    is_outsource = proc.get('is_outsource', 0)
                    pcode = proc.get('process_code', '')
                    if is_outsource and (not pcode or pcode == ''):
                        pcode = 'X01'
                    task_data = {
                        'order_no': order_no,
                        'process_name': proc.get('process_name', ''),
                        'process_code': pcode,
                        'quantity': proc.get('planned_qty', quantity),
                        'planned_qty': proc.get('planned_qty', quantity),
                        'priority': 'normal',
                        'unit': proc.get('unit', ''),
                    }
                    operator_id = proc.get('operator_id', '') or 'OP001'
                    result = WeChatReportService.publish_task_to_operator(task_data, operator_id)
                    if result.get('success'):
                        success_count += 1
                    else:
                        fail_count += 1
                        fail_details.append(f"{proc.get('process_name', '')}: {result.get('message', '未知错误')}")
                    time.sleep(1)

                self.after(0, lambda sc=success_count, fc=fail_count, fd=fail_details:
                           self._on_publish_complete(sc, fc, fd))
            except Exception as e:
                logger.error(f"发布工序任务异常: {e}")
                self.after(0, lambda: self._on_publish_complete(0, len(processes), [f"系统异常: {e}"]))

        thread = threading.Thread(target=do_publish, daemon=True)
        thread.start()

    def _on_publish_complete(self, success_count, fail_count, fail_details):
        """发布完成回调（主线程执行）"""
        self._publishing = False
        if hasattr(self, '_publish_status_label') and self._publish_status_label:
            self._publish_status_label.destroy()
            self._publish_status_label = None

        log_ui("工序追踪", "发布报工任务",
               f"{self.current_order_id} (成功:{success_count}, 失败:{fail_count})")

        msg = f"订单 {self.current_order_id} 的工序任务发布完成\n✅ 成功: {success_count}\n❌ 失败: {fail_count}"
        if fail_details:
            msg += "\n\n失败详情:\n" + "\n".join(fail_details)

        if success_count > 0:
            messagebox.showinfo("发布结果", msg)
        else:
            messagebox.showerror("发布失败", msg)

    def _retry_dead_tasks(self):
        """重发死信 — 显示微信报工死信列表并支持批量重发"""
        from services.wechat_report_service import WeChatReportService

        try:
            dead_tasks = WeChatReportService.get_dead_tasks()
        except Exception as e:
            alert(f"查询死信失败：{e}", "错误")
            return

        if not dead_tasks:
            alert("当前没有死信任务", "提示")
            return

        dialog = tk.Toplevel(self)
        dialog.title("报工死信重发")
        dialog.geometry("820x420")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        dialog.configure(bg=COLORS["bg_main"])

        header = tk.Frame(dialog, bg=COLORS["bg_main"])
        header.pack(fill=tk.X, padx=LAYOUT["padding"]["medium"], pady=(LAYOUT["padding"]["medium"], 0))
        tk.Label(header, text=f"报工死信列表（共 {len(dead_tasks)} 条）",
                 font=FONTS["subtitle"], bg=COLORS["bg_main"],
                 fg="red").pack(anchor=tk.W)

        tree_frame = tk.Frame(dialog, bg=COLORS["bg_main"])
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=LAYOUT["padding"]["medium"], pady=LAYOUT["padding"]["medium"])

        columns = ("select", "order_no", "process", "retry", "error", "time")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=12)
        tree.heading("select", text="☑")
        tree.heading("order_no", text="订单号")
        tree.heading("process", text="工序")
        tree.heading("retry", text="重试")
        tree.heading("error", text="最后错误")
        tree.heading("time", text="更新时间")
        tree.column("select", width=30, anchor="center")
        tree.column("order_no", width=130)
        tree.column("process", width=100)
        tree.column("retry", width=50, anchor="center")
        tree.column("error", width=320)
        tree.column("time", width=130)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(fill=tk.BOTH, expand=True)

        select_vars = {}
        for i, dt in enumerate(dead_tasks):
            v = tk.BooleanVar(value=True)
            select_vars[dt['id']] = v
            error_text = (dt.get('last_error') or '未知')[:60]
            time_text = str(dt.get('updated_at') or dt.get('created_at', ''))[:19]
            tree.insert("", tk.END, iid=str(dt['id']),
                       values=("☑", dt.get('order_no', ''), dt.get('process_name', ''),
                               dt.get('retry_count', 0), error_text, time_text))

        def toggle_all():
            new_val = not all(v.get() for v in select_vars.values())
            for v in select_vars.values():
                v.set(new_val)
            for item in tree.get_children():
                tree.set(item, "select", "☑" if new_val else "☐")

        def do_retry():
            selected = [tid for tid, v in select_vars.items() if v.get()]
            if not selected:
                alert("请至少选择一条死信", "提示")
                return
            success_count = 0
            fail_count = 0
            for tid in selected:
                tree.set(str(tid), "select", "⏳")
                dialog.update()
                try:
                    result = WeChatReportService.retry_dead_task(tid)
                    if result.get('skipped'):
                        tree.set(str(tid), "select", "⏭")
                    elif result['success']:
                        tree.set(str(tid), "select", "✅")
                        success_count += 1
                    else:
                        tree.set(str(tid), "select", "❌")
                        fail_count += 1
                except Exception:
                    tree.set(str(tid), "select", "❌")
                    fail_count += 1
            dialog.destroy()
            alert(f"死信重发完成\n成功 {success_count} 条，失败 {fail_count} 条", "结果")

        btn_frame = tk.Frame(dialog, bg=COLORS["bg_main"])
        btn_frame.pack(fill=tk.X, padx=LAYOUT["padding"]["medium"], pady=(0, LAYOUT["padding"]["medium"]))
        ttk.Button(btn_frame, text="全选/取消", command=toggle_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🔄 重发选中", command=do_retry).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="关闭", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)

    def _goto_quality(self):
        """跳转到质检管理模块"""
        if not self.current_order_id:
            alert("请先选择一个订单！", "提示")
            return
        
        # 通过主窗口切换到质检模块
        root = self.winfo_toplevel()
        root.quality_track_order_id = self.current_order_id
        root.show_module("quality")

    def _do_search(self):
        """执行工单模糊搜索"""
        keyword = self.search_var.get().strip()
        self.load_work_orders(keyword=keyword)

    def _on_search_change(self, event=None):
        """搜索框按键松开时：输入中实时过滤（超过1字符时），带防抖"""
        if hasattr(self, '_search_after_id') and self._search_after_id:
            self.after_cancel(self._search_after_id)
        self._search_after_id = self.after(400, self._do_search)

    def load_work_orders(self, keyword=""):
        """加载生产工单列表，支持模糊搜索，默认显示所有活跃工单（生产中+待开始+已完成）"""
        log_ui("工序追踪", "加载工单列表", f"关键词='{keyword}'" if keyword else "全部")
        filters = {}
        if keyword:
            filters["keyword"] = keyword
        else:
            filters["status"] = [ProductionStatus.IN_PROGRESS.value, ProductionStatus.PENDING.value, ProductionStatus.SCHEDULED.value]

        prod_list = ProductionDAO.get_all_with_order(filters)

        relevant_prods = prod_list

        if not relevant_prods:
            self.orders_map = {}
            self.order_combo["values"] = []
            self.search_hint.config(text=t('process.no_work_order'))
            return

        prod_list_display = [f"{p['order_no']} - {(p.get('customer_group', '') or p.get('customer_name', '') or '无')}" for p in relevant_prods]
        self.orders_map = {f"{p['order_no']} - {(p.get('customer_group', '') or p.get('customer_name', '') or '无')}": p["id"] for p in relevant_prods}
        self.order_combo["values"] = prod_list_display

        if keyword:
            self.search_hint.config(text=f"找到 {len(prod_list_display)} 条")
        else:
            self.search_hint.config(text=f"共 {len(prod_list_display)} 条")

        if prod_list_display:
            self.order_combo.current(0)
            self.current_prod_id = self.orders_map[prod_list_display[0]]
            prod = ProductionDAO.get_by_id(self.current_prod_id)
            if prod:
                self.current_order_id = prod["order_id"]
                records = ProcessDAO.get_by_production(prod["id"])
                self._cached_order = OrderDAO.get_by_id(self.current_order_id)
                self._cached_records = records
                self.proc_combo["values"] = [r["process_name"] for r in records]
                if records:
                    self.proc_combo.current(0)
                self._update_proc_progress()
                self.load_processes(prod=prod, order=self._cached_order, records=records)
            else:
                self._cached_order = None
                self._cached_records = None
                self.load_processes(prod=None, order=None, records=None)
        else:
            self.current_order_id = None
            self.current_prod_id = None
            self.order_info_label.config(text=t('process.no_match_work_order'))
            for item in self.process_tree.get_children():
                self.process_tree.delete(item)
            self.progress_label.config(text=t('process.overall_progress', percent="0%"))
            self.progress_bar["value"] = 0
            self.record_count_label.config(text=t('process.record_count', count="0"))
            self.stat_total_label.config(text="--")
            self.stat_completed_label.config(text="--")
            self.stat_qualified_label.config(text="--")

    def on_order_changed(self):
        """工单选择改变时加载工序记录"""
        selected = self.order_combo.get()
        log_ui("工序追踪", "切换工单", f"工单='{selected}'")
        self.current_prod_id = self.orders_map.get(selected)
        self.order_info_label.config(text="")
        if self.current_prod_id:
            prod = ProductionDAO.get_by_id(self.current_prod_id)
            if prod:
                self.current_order_id = prod["order_id"]
                records = ProcessDAO.get_by_production(prod["id"])
                self._cached_order = OrderDAO.get_by_id(self.current_order_id)
                self._cached_records = records
                self.proc_combo["values"] = [r["process_name"] for r in records] if records else [""]
                if records:
                    self.proc_combo.current(0)
                self._update_proc_progress()
                self.load_processes(prod=prod, order=self._cached_order, records=records)
            else:
                self._cached_order = None
                self._cached_records = None
                self.load_processes(prod=None, order=None, records=None)
        else:
            self._cached_order = None
            self._cached_records = None
            self.load_processes(prod=None, order=None, records=None)

    def _on_tree_select(self, event=None):
        """点击工序列表时，同步更新右侧报工表单"""
        sel = self.process_tree.selection()
        if not sel:
            return
        
        values = self.process_tree.item(sel[0])["values"]
        proc_name = values[1]  # 工序名称在第二列
        
        # 查找该工序在 proc_combo 中的索引
        proc_values = self.proc_combo["values"]
        if proc_name in proc_values:
            index = proc_values.index(proc_name)
            self.proc_combo.current(index)
            self._update_proc_progress()
        else:
            self._update_proc_progress()

    def _on_proc_selected(self, event=None):
        """工序选择改变时更新进度显示，并同步左侧列表高亮"""
        self._update_proc_progress()
        
        # 同步左侧列表高亮
        proc_name = self.proc_combo.get()
        if proc_name:
            for item in self.process_tree.get_children():
                if self.process_tree.item(item)["values"][1] == proc_name:
                    self.process_tree.selection_set(item)
                    self.process_tree.see(item)  # 滚动到可见区域
                    break

    def _update_proc_progress(self):
        """更新当前工序的统计卡和订单信息（使用缓存）"""
        proc_name = self.proc_combo.get()

        order = self._cached_order
        if order:
            self.order_info_label.config(
                text=f"客户群：{order.get('customer_group', '-') or '-'}  │  "
                     f"数量：{order.get('quantity', '-')}  │  "
                     f"当前工序：{proc_name}"
            )

        if not proc_name or not self.current_prod_id:
            self.stat_total_label.config(text="--")
            self.stat_completed_label.config(text="--")
            self.stat_qualified_label.config(text="--")
            return

        records = self._cached_records or []
        for r in records:
            if r["process_name"] == proc_name:
                total = r.get("planned_qty", 0)
                completed = r.get("completed_qty", 0)
                qualified = r.get("qualified_qty", 0)
                
                self.stat_total_label.config(text=f"{total}")
                self.stat_completed_label.config(text=f"{completed}")
                q_rate = f"{int(qualified / completed * 100)}%" if completed > 0 else "--"
                self.stat_qualified_label.config(text=q_rate)
                return
        
        self.stat_total_label.config(text="--")
        self.stat_completed_label.config(text="--")
        self.stat_qualified_label.config(text="--")

    def load_processes(self, prod=None, order=None, records=None):
        log_ui("工序追踪", "加载工序列表", f"订单ID={self.current_order_id}")
        for item in self.process_tree.get_children():
            self.process_tree.delete(item)

        if not self.current_order_id:
            self.record_count_label.config(text=t('process.record_count', count="0"))
            self.progress_label.config(text=t('process.overall_progress', percent="0%"))
            self.progress_bar["value"] = 0
            return

        if prod is None:
            prod = ProductionDAO.get_by_order_id(self.current_order_id)
        if not prod:
            self.progress_label.config(text=t('process.not_scheduled'))
            self.progress_bar["value"] = 0
            return

        if order is None:
            order = OrderDAO.get_by_id(self.current_order_id)
        total_qty = order.get("quantity", 0) if order else 0

        if records is None:
            records = ProcessDAO.get_by_production(prod["id"])

        # 批量获取今日完成量（优化N+1查询）
        record_ids = [r.get("id") for r in records]
        today_completed_map = ProcessDAO.get_today_completed_batch(record_ids)

        # 更新统计卡
        total_completed_all = sum(float(r.get("completed_qty", 0) or 0) for r in records)
        total_qualified_all = sum(float(r.get("qualified_qty", 0) or 0) for r in records)
        self.stat_total_label.config(text=f"{total_qty}")
        self.stat_completed_label.config(text=f"{total_completed_all}")
        qual_rate = f"{int(total_qualified_all / total_completed_all * 100)}%" if total_completed_all > 0 else "--"
        self.stat_qualified_label.config(text=qual_rate)

        # 更新序号（处理重排后序号连续）
        seq_map = {r["process_name"]: r["process_seq"] for r in records}

        for i, r in enumerate(records):
            completed = float(r.get("completed_qty", 0) or 0)
            plan_qty = float(r.get("planned_qty", 0) or 1)
            status = _calc_status(r.get("completed_qty"), r.get("planned_qty"))
            is_outsource = r.get("is_outsource", 0)
            # 外协工序优先红色标签
            tag = "outsource" if is_outsource else ("done" if status == "已完成" else "doing" if status == "生产中" else "pending")
            outs_str = "是" if is_outsource else ""
            qualified = float(r.get("qualified_qty", 0) or 0)
            
            # 计算完成百分比
            plan_qty = r.get("planned_qty", total_qty) or total_qty
            percent = int(completed / plan_qty * 100) if plan_qty > 0 else 0

            # 获取今日完成量（使用批量查询结果）
            today_qty = today_completed_map.get(r.get("id"), 0)

            # 兼容旧数据
            worker_val = r.get("worker") or r.get("operator") or "-"
            unit_val = r.get("unit", "件")
            
            # 计算实际序号（从1开始的连续序号）
            actual_seq = seq_map[r["process_name"]]
            
            self.process_tree.insert("", tk.END, values=(
                actual_seq,
                r.get("process_name", ""),
                worker_val,
                f"{plan_qty}",
                unit_val,
                f"{completed}",
                f"{today_qty}",
                f"{percent}%",
                f"{qualified}",
                f"{r.get('work_hours', 0):.1f}",
                status,
                outs_str,
            ), tags=(tag,))

        # 更新序号统计
        self.record_count_label.config(text=f"共 {len(records)} 条工序")

        # 更新总体进度
        total_completed = sum(float(r.get("completed_qty", 0) or 0) for r in records)
        plan_total = sum(float(r.get("planned_qty", total_qty) or total_qty) for r in records)
        total_progress = int(total_completed / plan_total * 100) if plan_total > 0 else 0
        self.progress_label.config(text=f"整体生产进度：{total_progress}%  ({total_completed}/{plan_total})")
        self.progress_bar["value"] = total_progress

        # 同步更新报工下拉框为数据库中实际工序列表
        process_names = [r.get("process_name", "") for r in records if r.get("process_name")]
        self.proc_combo["values"] = process_names
        if process_names:
            current = self.proc_combo.get()
            if current not in process_names:
                self.proc_combo.current(0)
                self._on_proc_selected()

    def on_process_double_click(self, event):
        """双击工序打开编辑窗口"""
        self._edit_process()

    def submit_report(self):
        log_ui("工序追踪", "提交报工")
        if not self.current_order_id:
            alert("请先选择一个订单！", "提示")
            return

        proc_name = self.proc_combo.get()
        if not proc_name:
            alert("请选择要报工的工序！", "提示")
            return
        
        prod = ProductionDAO.get_by_order_id(self.current_order_id)
        if not prod:
            alert("该订单尚未排产！", "提示")
            return

        # 查找对应工序记录
        records = ProcessDAO.get_by_production(prod["id"])
        target_record = None
        for r in records:
            if r["process_name"] == proc_name:
                target_record = r
                break

        if not target_record:
            alert("未找到对应工序记录！", "错误")
            return

        try:
            qty = float(self.qty_entry.get() or 0)
            qualified = float(self.qualified_entry.get() or 0)
            hours = float(self.hours_entry.get() or 0)
        except ValueError:
            alert("请输入有效数字！", "输入错误")
            return

        if qty <= 0:
            alert("请输入报工数量！", "提示")
            return
        
        worker = self.worker_entry.get().strip()
        remark = self.remark_text.get("1.0", tk.END).strip()
        
        # 自动判断状态：累计完成>=计划数量则标记为已完成
        total_qty = float(target_record.get("planned_qty", 1) or 1)
        current_completed = float(target_record.get("completed_qty", 0) or 0)
        new_total = current_completed + qty
        status = _calc_status(new_total, total_qty)
        old_status = target_record.get("status", "")

        # 累加完成数量，而不是覆盖
        ProcessDAO.update_record(target_record["id"], {
            "completed_qty": new_total,
            "qualified_qty": float(target_record.get("qualified_qty", 0) or 0) + qualified,
            "work_hours": float(target_record.get("work_hours", 0) or 0) + hours,
            "worker": worker if worker else target_record.get("worker", ""),
            "status": status,
            "remark": remark,
        })

        from core.event_bus import EventBus
        from core.events import EventType
        event_data = {
            'process_id': target_record['id'],
            'order_id': self.current_order_id,
            'process_name': proc_name,
            'quantity': qty,
            'qualified': qualified,
            'worker': worker,
            'status': status,
            'old_status': old_status,
        }
        EventBus.publish(EventType.PROCESS_REPORTED, event_data)
        if old_status in (ProcessStatus.PENDING.value, "") and status in ("生产中", "已完成"):
            EventBus.publish(EventType.PROCESS_STARTED, event_data)
        if status == "已完成":
            EventBus.publish(EventType.PROCESS_COMPLETED, {**event_data, 'completed_qty': new_total, 'planned_qty': total_qty})

        # 清空表单
        self.qty_entry.delete(0, tk.END)
        self.qty_entry.insert(0, "0")
        self.qualified_entry.delete(0, tk.END)
        self.qualified_entry.insert(0, "0")
        self.hours_entry.delete(0, tk.END)
        self.hours_entry.insert(0, "0")
        self.worker_entry.delete(0, tk.END)
        self.remark_text.delete("1.0", tk.END)

        self._update_proc_progress()
        self.load_processes()
        alert(f"报工成功：{proc_name} | 本次：+{qty} | 累计：{new_total}/{total_qty}", "操作成功")

    def _quick_report(self, event=None):
        """快速报工 - 双击工序直接弹出报工窗口"""
        item = self.process_tree.selection()
        if not item:
            return
        
        values = self.process_tree.item(item[0])["values"]
        seq, proc_name = values[0], values[1]
        
        if not self.current_order_id:
            alert("请先选择一个订单！", "提示")
            return
        
        prod = ProductionDAO.get_by_order_id(self.current_order_id)
        if not prod:
            return
        
        records = ProcessDAO.get_by_production(prod["id"])
        target_record = None
        for r in records:
            if r["process_name"] == proc_name:
                target_record = r
                break
        
        if not target_record:
            return
        
        # 快速报工表单
        fields = [
            ("工序名称", "proc_name", proc_name, "label", [], ""),
            ("本次完成量", "qty", "0", "number", [], "输入本次完成数量"),
            ("合格数量", "qualified", "0", "number", [], "输入合格数量（可为空）"),
            ("工时(小时)", "hours", "0", "number", [], "输入本次工时"),
            ("实际材料用量", "material_usage", "0", "number", [], "输入实际材料用量"),
            ("材料单位", "material_unit", "kg", "combo", ["kg", "米", "件", "个", "条", "根", "卷", "套"], "选择材料单位"),
            ("操作员", "worker", target_record.get("worker", ""), "entry", [], "输入操作员姓名"),
            ("备注", "remark", "", "textarea", [], "输入备注信息"),
        ]
        
        def on_save(data):
            try:
                qty = float(data.get("qty", 0))
                qualified = float(data.get("qualified", 0))
                hours = float(data.get("hours", 0))
            except (ValueError, TypeError):
                alert("请输入有效数字！", "提示")
                return
            
            if qty <= 0:
                alert("完成数量必须大于0！", "提示")
                return
            
            from datetime import datetime

            # 使用 ProcessService 重新读取最新数据（防止并发覆盖）
            fresh_record = self.svc.get_record_by_id(target_record["id"])
            if not fresh_record:
                alert("工序记录不存在！", "错误")
                return

            total_qty = float(fresh_record.get("planned_qty", 1) or 1)
            material_usage = float(data.get("material_usage", 0)) or 0
            material_unit = data.get("material_unit", "kg") or "kg"
            worker_val = data.get("worker", "") or fresh_record.get("worker", "") or ""
            remark_val = data.get("remark", "")
            old_status = fresh_record.get("status", "")
            production_id = fresh_record.get("production_id")
            order_id = fresh_record.get("order_id")

            try:
                # 报工累加（service 内部重新读取并累加）
                result = self.svc.report_progress(
                    target_record["id"], int(qty), int(qualified), hours, worker_val, remark_val
                )
                new_total = result.get('completed_qty', 0)
                status = result.get('status', "生产中")

                # 补充 process_records 的 material 字段和 start_time
                extra_update = {
                    'material_usage': material_usage,
                    'material_unit': material_unit,
                    'record_date': datetime.now().isoformat(),
                }
                if old_status in (ProcessStatus.PENDING.value, "") and status in ("生产中", "已完成"):
                    if not fresh_record.get("start_time"):
                        extra_update['start_time'] = datetime.now().isoformat()
                self.svc.update_record(target_record["id"], extra_update)
            except ValueError as e:
                alert(f"报工失败：{e}", "错误")
                return
            except Exception as e:
                alert(f"报工失败：{e}", "错误")
                return

            # 非 process_records 表（production_orders / orders）仍需原始连接
            from models.database import get_connection
            conn = get_connection()
            cursor = conn.cursor()
            try:
                if status == "已完成":
                    # 检查是否所有工序都完成（用 service 取工序列表，Python 计数）
                    all_records = self.svc.get_records_by_production(production_id)
                    # 只检查有计划量的工序：排除 planned_qty=0（数量未确定），与 _calc_status 逻辑一致
                    unfinished_count = sum(1 for r in all_records
                        if (float(r.get('planned_qty', 0) or 0) > 0
                            and float(r.get('completed_qty', 0) or 0) < float(r.get('planned_qty', 1) or 1)))

                    if unfinished_count == 0:
                        cursor.execute(
                            "UPDATE production_orders SET status = %s, actual_end = %s, updated_at = %s WHERE id = %s",
                            (ProductionStatus.COMPLETED.value, datetime.now().isoformat(), datetime.now().isoformat(), production_id)
                        )
                        cursor.execute(
                            "UPDATE orders SET status = %s, updated_at = %s WHERE id = %s",
                            (OrderStatus.QC.value, datetime.now().isoformat(), order_id)
                        )
                        conn.commit()
                    else:
                        cursor.execute(
                            "UPDATE production_orders SET status = %s, actual_start = COALESCE(actual_start, %s), updated_at = %s WHERE id = %s",
                            (ProductionStatus.IN_PROGRESS.value, datetime.now().isoformat(), datetime.now().isoformat(), production_id)
                        )
                        cursor.execute(
                            "UPDATE orders SET status = %s, updated_at = %s WHERE id = %s AND status = %s",
                            (OrderStatus.PRODUCTION.value, datetime.now().isoformat(), order_id, OrderStatus.SCHEDULED.value)
                        )
                        conn.commit()
                elif status == "生产中":
                    cursor.execute(
                        "UPDATE production_orders SET status = %s, actual_start = COALESCE(actual_start, %s), updated_at = %s WHERE id = %s",
                        (ProductionStatus.IN_PROGRESS.value, datetime.now().isoformat(), datetime.now().isoformat(), production_id)
                    )
                    cursor.execute(
                        "UPDATE orders SET status = %s, updated_at = %s WHERE id = %s AND status = %s",
                        (OrderStatus.PRODUCTION.value, datetime.now().isoformat(), order_id, OrderStatus.SCHEDULED.value)
                    )
                    conn.commit()
            except Exception as e:
                conn.rollback()
                alert(f"状态同步失败：{e}", "错误")
            finally:
                cursor.close()
                conn.close()

            from core.event_bus import EventBus
            from core.events import EventType
            event_data = {
                'process_id': target_record['id'],
                'order_id': order_id,
                'process_name': proc_name,
                'quantity': qty,
                'qualified': qualified,
                'worker': data.get('worker', ''),
                'status': status,
                'old_status': old_status,
            }
            EventBus.publish(EventType.PROCESS_REPORTED, event_data)
            if old_status == ProcessStatus.PENDING.value and status in ("生产中", "已完成"):
                EventBus.publish(EventType.PROCESS_STARTED, event_data)
            if status == "已完成":
                EventBus.publish(EventType.PROCESS_COMPLETED, {**event_data, 'completed_qty': new_total, 'planned_qty': total_qty})

            self.load_processes()
            alert(f"报工成功！累计：{new_total}/{total_qty}", "操作成功")
        
        popup_form("快速报工", fields, on_save, width=380)

    # ==================== 自定义工序功能 ====================

    def _show_context_menu(self, event):
        """右键菜单"""
        item = self.process_tree.identify_row(event.y)
        if not item:
            return
        self.process_tree.selection_set(item)
        
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="✏️ 编辑工序", command=self._edit_process)
        menu.add_command(label="🔢 调整所需量", command=self._adjust_qty)
        menu.add_command(label="📝 添加备注", command=self._add_remark)
        menu.add_separator()
        menu.add_command(label="⬆️ 上移", command=self._move_up)
        menu.add_command(label="⬇️ 下移", command=self._move_down)
        menu.add_separator()
        menu.add_command(label="✅ 标记完成", command=lambda: self._quick_status("已完成"))
        menu.add_command(label="🔄 重新开始", command=lambda: self._quick_status("待开始"))
        menu.add_separator()
        menu.add_command(label="🗑️ 删除工序", command=self._delete_process)
        menu.post(event.x_root, event.y_root)

    def _get_selected_record(self):
        """获取选中的工序记录"""
        sel = self.process_tree.selection()
        if not sel:
            return None
        values = self.process_tree.item(sel[0])["values"]
        seq = values[0]
        if not self.current_order_id:
            return None
        prod = ProductionDAO.get_by_order_id(self.current_order_id)
        if not prod:
            return None
        records = ProcessDAO.get_by_production(prod["id"])
        for r in records:
            if r["process_seq"] == seq:
                return r
        return None

    def _add_process(self):
        """添加工序"""
        log_ui("工序追踪", "添加工序")
        if not self.current_order_id:
            alert("请先选择一个订单！", "提示")
            return
        
        prod = ProductionDAO.get_by_order_id(self.current_order_id)
        if not prod:
            alert("该订单尚未排产！", "提示")
            return
        
        # 获取当前最大序号
        records = ProcessDAO.get_by_production(prod["id"])
        max_seq = max((r["process_seq"] for r in records), default=0)
        seq_options = [str(i) for i in range(1, max_seq + 2)]  # 1 到 max_seq+1
        
        # 获取历史负责人列表
        from utils.custom_types import get_operators
        operator_options = get_operators()
        if not operator_options:
            operator_options = []
        
        # 单位选项
        unit_options = ["件", "个", "米", "卷", "套", "箱", "千克", "kg", "吨", "根"]
        
        # popup_form 使用元组格式: (label, key, default, type, options, placeholder)
        fields = [
            ("工序名称", "process_name", "", "entry", [], ""),
            ("执行人*", "worker", "", "combo_editable", operator_options, ""),
            ("排列第几", "process_seq", str(max_seq + 1), "combo", seq_options, ""),
            ("自定义单位", "unit", "件", "combo_editable", unit_options, ""),
            ("是否外协", "is_outsource", "否", "combo", ["否", "是"], ""),
            ("外协备注", "outsource_remark", "", "textarea", [], "外协厂家/联系人/电话..."),
            ("备注", "remark", "", "textarea", [], ""),
        ]
        
        def on_save(data):
            if not data.get("process_name", "").strip():
                alert("请输入工序名称！", "提示")
                return
            
            worker = data.get("worker", "").strip()
            if not worker:
                alert("请填写负责人（必填项）！", "提示")
                return
            
            # 记忆负责人
            from utils.custom_types import add_operator
            add_operator(worker)
            
            target_seq = int(data.get("process_seq", max_seq + 1))
            process_name = data.get("process_name", "")

            # 从规则引擎获取默认配置
            defaults = self.svc.get_process_defaults(process_name)
            planned_qty = float(data.get("planned_qty", 1))
            unit = (data.get("unit") or "").strip()
            if defaults:
                if defaults.get('default_qty', 0) > 0 and not data.get("planned_qty"):
                    planned_qty = float(defaults['default_qty'])
                if not unit:
                    unit = defaults.get('unit', '')
            if not unit:
                unit = "件"

            # 将 >= target_seq 的工序序号 +1（腾出位置）
            self.svc.shift_seq_up(prod["id"], target_seq)

            # 使用 service 插入新工序
            process_id = self.svc.insert_record({
                "order_id": self.current_order_id,
                "production_id": prod["id"],
                "process_name": process_name,
                "process_seq": target_seq,
                "planned_qty": planned_qty,
                "status": "待开始",
                "worker": worker,
                "remark": data.get("remark", ""),
                "unit": unit,
                "is_outsource": 1 if data.get("is_outsource") == "是" else 0,
                "outsource_remark": data.get("outsource_remark", ""),
            })
            from core.event_bus import EventBus
            EventBus.publish('process:created', {
                'process_id': process_id,
                'order_id': self.current_order_id,
                'production_id': prod['id'],
                'process_name': data.get('process_name', ''),
                'worker': worker,
                'process_seq': target_seq,
            })
            self.load_processes()
            alert("工序添加成功！", "操作成功")
        
        popup_form("添加工序", fields, on_save, width=400)

    def _edit_process(self):
        """编辑工序"""
        log_ui("工序追踪", "编辑工序")
        record = self._get_selected_record()
        if not record:
            alert("请先选择一道工序！", "提示")
            return
        
        # 单位选项
        unit_options = ["件", "个", "米", "卷", "套", "箱", "千克", "kg", "吨", "根"]
        
        # 获取历史负责人列表
        from utils.custom_types import get_operators
        operator_options = get_operators()
        if not operator_options:
            operator_options = []
        
        # popup_form 使用元组格式: (label, key, default, type, options, placeholder)
        fields = [
            ("工序名称", "process_name", record.get("process_name", ""), "entry", [], ""),
            ("计划数量", "planned_qty", str(record.get("planned_qty", 1)), "number", [], ""),
            ("单位", "unit", record.get("unit", "件"), "combo_editable", unit_options, ""),
            ("执行人*", "worker", record.get("worker", ""), "combo_editable", operator_options, ""),
            ("状态", "status", record.get("status", "待开始"), "combo", ["待开始", "生产中", "已完成"], ""),
            ("是否外协", "is_outsource", "是" if record.get("is_outsource") else "否", "combo", ["否", "是"], ""),
            ("外协备注", "outsource_remark", record.get("outsource_remark", ""), "textarea", [], "外协厂家/联系人/电话..."),
            ("备注", "remark", record.get("remark", ""), "textarea", [], ""),
        ]
        
        def on_save(data):
            # 负责人必填验证
            worker = data.get("worker", "").strip()
            if not worker:
                alert("请填写负责人（必填项）！", "提示")
                return
            
            # 记忆负责人
            from utils.custom_types import add_operator
            add_operator(worker)
            
            self.svc.update_record(record["id"], {
                "process_name": data.get("process_name", ""),
                "planned_qty": float(data.get("planned_qty", 1)),
                "unit": data.get("unit", "件"),
                "worker": worker,
                "status": data.get("status", ProcessStatus.PENDING.value),
                "remark": data.get("remark", ""),
                "is_outsource": 1 if data.get("is_outsource") == "是" else 0,
                "outsource_remark": data.get("outsource_remark", ""),
            })
            self.load_processes()
            alert("工序已更新！", "操作成功")
        
        popup_form("编辑工序", fields, on_save, width=500)

    def _delete_process(self):
        """删除工序"""
        log_ui("工序追踪", "删除工序")
        record = self._get_selected_record()
        if not record:
            alert("请先选择要删除的工序！", "提示")
            return
        
        # 有报工记录的工序不可删除
        completed = float(record.get("completed_qty", 0) or 0)
        if completed > 0:
            db_status = record.get("status", _calc_status(completed, record.get("planned_qty")))
            alert(f"「{record.get('process_name')}」已报工 {completed}，无法删除！", "提示")
            return
        
        if not confirm(f"确定要删除「{record.get('process_name')}」这道工序吗？", "确认删除"):
            return
        
        try:
            print(f"[DEBUG DELETE] 开始删除工序: id={record['id']}, name={record.get('process_name')}, production_id={record.get('production_id')}, order_id={record.get('order_id')}")
            
            # 检查是否有多个生产工单关联同一订单
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, order_no FROM production_orders WHERE order_id=%s", (record.get('order_id'),))
            prod_list = cursor.fetchall()
            print(f"[DEBUG DELETE] 该订单关联的生产工单数: {len(prod_list)}")
            for p in prod_list:
                print(f"[DEBUG DELETE]   - production_id={p['id']}, order_no={p['order_no']}")
            cursor.close()
            conn.close()

            # 使用 service 删除工序
            deleted = self.svc.delete_record(record["id"])
            print(f"[DEBUG DELETE] DELETE结果: {deleted}")

            # 验证删除是否成功
            exists = self.svc.get_record_by_id(record["id"])
            print(f"[DEBUG DELETE] 删除后记录是否存在: {exists is not None}")

            # 重新排序序号
            remaining = self.svc.get_records_by_production(record["production_id"])
            count_after = len(remaining)
            print(f"[DEBUG DELETE] 删除后剩余工序数: {count_after}")
            print(f"[DEBUG DELETE] 重新排序前工序: {[{'id': r['id'], 'process_name': r['process_name'], 'process_seq': r['process_seq']} for r in remaining]}")
            for i, r in enumerate(remaining, 1):
                self.svc.update_record(r["id"], {"process_seq": i})
            print(f"[DEBUG DELETE] 重新排序完成")

            from core.event_bus import EventBus
            from core.events import EventType
            EventBus.publish(EventType.PROCESS_DELETED, {
                'process_id': record['id'],
                'order_id': record.get('order_id'),
                'process_name': record.get('process_name', ''),
            })

            # 清空缓存
            self._cached_records = None
            print(f"[DEBUG DELETE] 缓存已清空")

            self.load_processes()
            alert("工序已删除！", "操作成功")
        except Exception as e:
            print(f"[DEBUG DELETE] 删除失败: {e}")
            alert(f"删除失败：{e}", "错误")

    def _adjust_qty(self):
        """调整工序所需数量"""
        record = self._get_selected_record()
        if not record:
            alert("请先选择一道工序！", "提示")
            return
        
        # 单位选项
        unit_options = ["件", "个", "米", "卷", "套", "箱", "千克", "kg", "吨", "根"]
        current_unit = record.get("unit", "件")
        
        fields = [
            ("工序名称", "process_name", record.get("process_name", ""), "label", [], ""),
            ("单位", "unit", current_unit, "combo_editable", unit_options, ""),
            ("计划数量", "planned_qty", str(record.get("planned_qty", 1)), "number", [], ""),
            ("调整原因", "reason", "", "textarea", [], "请输入调整原因..."),
        ]
        
        def on_save(data):
            self.svc.update_record(record["id"], {
                "planned_qty": float(data.get("planned_qty", 1)),
                "unit": data.get("unit", "件"),
            })
            self.load_processes()
            alert("数量和单位已调整！", "操作成功")
        
        popup_form("调整工序所需数量", fields, on_save, width=400)

    def _add_remark(self):
        """添加/查看备注"""
        record = self._get_selected_record()
        if not record:
            alert("请先选择一道工序！", "提示")
            return
        
        fields = [
            ("工序备注", "remark", record.get("remark", ""), "textarea", [], ""),
        ]
        
        def on_save(data):
            self.svc.update_remark(record["id"], data.get("remark", ""))
            self.load_processes()
            alert("备注已保存！", "操作成功")
        
        popup_form("工序备注", fields, on_save, width=400)

    def _quick_status(self, status):
        """快速修改状态"""
        log_ui("工序追踪", "快速修改状态", f"新状态={status}")
        record = self._get_selected_record()
        if not record:
            return
        
        ProcessDAO.update_record(record["id"], {"status": status})
        self.load_processes()
        alert(f"状态已更新为「{status}」", "操作成功")

    def _move_up(self):
        """将选中工序上移一位"""
        record = self._get_selected_record()
        if not record:
            alert("请先选择要调整顺序的工序！", "提示")
            return
        
        # 有报工记录的工序不可调整顺序
        completed = float(record.get("completed_qty", 0) or 0)
        if completed > 0:
            alert(f"「{record.get('process_name')}」已报工 {completed}，无法调整顺序！", "提示")
            return
        
        production_id = record["production_id"]
        current_seq = record["process_seq"]

        # 获取上一道工序（用 service 取列表，Python 筛选）
        all_records = self.svc.get_records_by_production(production_id)
        prev_record = None
        for r in sorted(all_records, key=lambda x: x.get("process_seq", 0), reverse=True):
            if r.get("process_seq", 0) < current_seq:
                prev_record = r
                break

        if not prev_record:
            alert("已经是第一道工序，无法上移！", "提示")
            return

        # 交换两道工序的序号
        self.svc.update_record(prev_record["id"], {"process_seq": current_seq})
        self.svc.update_record(record["id"], {"process_seq": prev_record["process_seq"]})

        self.load_processes()
        alert(f"「{record.get('process_name')}」已上移一位", "操作成功")

    def _move_down(self):
        """将选中工序下移一位"""
        record = self._get_selected_record()
        if not record:
            alert("请先选择要调整顺序的工序！", "提示")
            return
        
        # 有报工记录的工序不可调整顺序
        completed = float(record.get("completed_qty", 0) or 0)
        if completed > 0:
            alert(f"「{record.get('process_name')}」已报工 {completed}，无法调整顺序！", "提示")
            return
        
        production_id = record["production_id"]
        current_seq = record["process_seq"]

        # 获取下一道工序（用 service 取列表，Python 筛选）
        all_records = self.svc.get_records_by_production(production_id)
        next_record = None
        for r in sorted(all_records, key=lambda x: x.get("process_seq", 0)):
            if r.get("process_seq", 0) > current_seq:
                next_record = r
                break

        if not next_record:
            alert("已经是最后一道工序，无法下移！", "提示")
            return

        # 交换两道工序的序号
        self.svc.update_record(next_record["id"], {"process_seq": current_seq})
        self.svc.update_record(record["id"], {"process_seq": next_record["process_seq"]})

        self.load_processes()
        alert(f"「{record.get('process_name')}」已下移一位", "操作成功")

    def _show_template_dialog(self):
        """显示模板管理对话框"""
        win = tk.Toplevel(self)
        win.title("📋 工序模板管理")
        from utils.window_manager import setup_resizable_window
        setup_resizable_window(win, "process_template_manage", "500x400")
        win.transient(self)
        win.grab_set()
        
        # 左侧：模板列表
        left_frame = tk.Frame(win)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=10, pady=10)
        
        tk.Label(left_frame, text="已保存的模板", font=FONTS["subtitle"]).pack()
        
        list_frame = tk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        template_listbox = tk.Listbox(list_frame, font=FONTS["body"], yscrollcommand=scrollbar.set, width=25)
        template_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=template_listbox.yview)
        
        # 填充模板列表
        template_names = list(self.templates.keys())
        for name in template_names:
            template_listbox.insert(tk.END, name)
        
        # 右侧：操作区
        right_frame = tk.Frame(win)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=10, pady=10)
        
        tk.Label(right_frame, text="模板名称:", font=FONTS["body"]).grid(row=0, column=0, sticky="w", pady=5)
        name_entry = ttk.Entry(right_frame, width=20, font=FONTS["body"])
        name_entry.grid(row=0, column=1, pady=5)
        
        def _save_template():
            if not self.current_order_id:
                alert("请先选择一个订单！", "提示")
                return
            name = name_entry.get().strip()
            if not name:
                alert("请输入模板名称！", "提示")
                return
            if name in self.templates:
                alert(f"模板「{name}」已存在，请使用其他名称！", "提示")
                return
            
            prod = ProductionDAO.get_by_order_id(self.current_order_id)
            if not prod:
                alert("该订单尚未排产！", "提示")
                return
            
            records = ProcessDAO.get_by_production(prod["id"])
            self.templates[name] = [{
                "process_name": r.get("process_name", ""),
                "planned_qty": r.get("planned_qty", 1),
                "unit": r.get("unit", "件")
            } for r in records]
            self._save_templates()
            
            template_listbox.insert(tk.END, name)
            name_entry.delete(0, tk.END)
            alert(f"模板「{name}」已保存！", "操作成功")
        
        def _load_template():
            sel = template_listbox.curselection()
            if not sel:
                alert("请选择要加载的模板！", "提示")
                return
            
            name = template_listbox.get(sel[0])
            if not self.current_order_id:
                alert("请先选择一个订单！", "提示")
                return
            
            prod = ProductionDAO.get_by_order_id(self.current_order_id)
            if not prod:
                alert("该订单尚未排产！", "提示")
                return
            
            if not confirm(f"加载模板「{name}」将覆盖当前工序，确定继续？", "确认加载"):
                return
            
            template = self.templates.get(name, [])

            # 清空现有工序
            self.svc.batch_delete_by_production(prod["id"])

            # 添加模板工序
            order = OrderDAO.get_by_id(self.current_order_id)
            total_qty = order.get("quantity", 1) if order else 1

            for i, t in enumerate(template, 1):
                self.svc.insert_record({
                    "order_id": self.current_order_id,
                    "production_id": prod["id"],
                    "process_name": t["process_name"],
                    "process_seq": i,
                    "planned_qty": t.get("planned_qty", 1),
                    "status": "待开始",
                    "unit": t.get("unit", "件"),
                })

            self.load_processes()
            win.destroy()
            alert(f"模板「{name}」已加载！", "操作成功")
        
        def _delete_template():
            sel = template_listbox.curselection()
            if not sel:
                alert("请选择要删除的模板！", "提示")
                return
            
            name = template_listbox.get(sel[0])
            if not confirm(f"确定要删除模板「{name}」吗？", "确认删除"):
                return
            
            del self.templates[name]
            self._save_templates()
            template_listbox.delete(sel[0])
            alert("模板已删除！", "操作成功")
        
        ttk.Button(right_frame, text="💾 保存当前为模板", command=_save_template).grid(row=1, column=0, columnspan=2, pady=10, ipadx=10)
        ttk.Button(right_frame, text="📥 加载选中模板", command=_load_template).grid(row=2, column=0, columnspan=2, pady=5, ipadx=10)
        ttk.Button(right_frame, text="🗑️ 删除选中模板", command=_delete_template).grid(row=3, column=0, columnspan=2, pady=5, ipadx=10)
        
        ttk.Button(win, text="关闭", command=win.destroy).pack(side=tk.BOTTOM, pady=10)

    def _open_process_calc_rules(self):
        """打开工序计算规则配置界面"""
        log_ui("工序追踪", "打开工序计算规则配置")
        from desktop.views.process_calc_rule_view import ProcessCalcRuleView
        from utils.window_manager import setup_resizable_window
        
        dialog = tk.Toplevel(self)
        dialog.title("⚙️ 工序计算规则配置")
        setup_resizable_window(dialog, "process_calc_rule", "1000x600")
        dialog.transient(self)
        dialog.grab_set()
        
        ProcessCalcRuleView(dialog).pack(fill=tk.BOTH, expand=True)

    def _recalculate_processes(self):
        """重新计算当前订单的工序计划数量（从规则重新生成工序）"""
        log_ui("工序追踪", "重新计算工序", f"订单ID={self.current_order_id}")
        if not self.current_order_id:
            alert("请先选择一个订单！", "提示")
            return

        prod = ProductionDAO.get_by_order_id(self.current_order_id)
        if not prod:
            alert("该订单尚未排产！", "提示")
            return

        if not confirm("重新计算将根据工序规则重新生成所有工序，确定继续？", "确认计算"):
            return

        try:
            from models.process_calc_rule import ProcessCalcEngine, ProcessCalcRuleDAO

            order = OrderDAO.get_by_id(self.current_order_id)
            if not order:
                alert("订单信息不存在！", "提示")
                return

            import json
            extra_params = {}
            if order.get("extra_params"):
                try:
                    raw = order["extra_params"]
                    extra_params = json.loads(raw) if isinstance(raw, str) else raw
                except Exception:
                    pass

            order_data = {
                "order_id": order["id"],
                "quantity": order.get("quantity") or 0,
                "product_type": order.get("product_type") or "",
                "产品类型": order.get("product_type") or "",
                "specs": str(order.get("mesh_size")) if order.get("mesh_size") else "",
                "customer": order.get("customer_group") or order.get("customer_name") or "",
            }
            if extra_params:
                order_data.update(extra_params)
                log_ui("工序追踪", "订单参数", f"共{len(extra_params)}个: {', '.join(extra_params.keys())}")
            else:
                log_ui("工序追踪", "订单参数", "⚠️ 无extra_params!")

            rules = ProcessCalcRuleDAO.get_all()

            # 获取现有工序数
            all_existing = self.svc.get_records_by_production(prod["id"])
            existing_count = len(all_existing)
            log_ui("工序追踪", "现有工序", f"数据库中有 {existing_count} 条")

            # ── 去重：同工序名下保留第一条，删除多余重复 ──
            seen_names = {}
            dedup_deleted = 0
            for r in all_existing:
                pname = r["process_name"]
                if pname in seen_names:
                    self.svc.delete_record(r["id"])
                    dedup_deleted += 1
                else:
                    seen_names[pname] = r
            if dedup_deleted > 0:
                log_ui("工序追踪", "去重清理", f"删除了 {dedup_deleted} 条重复工序记录")
                all_existing = list(seen_names.values())

            generated = ProcessCalcEngine.generate_processes_from_order(order_data, list(PROCESSES))
            log_ui("工序追踪", "规则匹配生成", f"根据规则匹配生成 {len(generated)} 道工序")

            # 构建 process_name → existing_record 的映射
            existing_map = {r["process_name"]: r for r in all_existing}

            updated, inserted = 0, 0
            for proc_info in generated:
                existing = existing_map.get(proc_info["process_name"])
                if existing:
                    old_status = existing.get("status")
                    self.svc.update_record(existing["id"], {
                        "process_seq": proc_info["process_seq"],
                        "planned_qty": proc_info["planned_qty"],
                        "unit": proc_info.get("unit", "件"),
                        "default_worker": proc_info.get("default_worker", ""),
                    })
                    updated += 1
                    log_ui("工序追踪", "更新工序", f"{proc_info['process_seq']}. {proc_info['process_name']} → {proc_info['planned_qty']} {proc_info.get('unit', '件')} (保留状态:{old_status})")
                else:
                    self.svc.insert_record({
                        "order_id": self.current_order_id,
                        "production_id": prod["id"],
                        "process_name": proc_info["process_name"],
                        "process_seq": proc_info["process_seq"],
                        "planned_qty": proc_info["planned_qty"],
                        "status": "待开始",
                        "worker": proc_info.get("default_worker", ""),
                        "unit": proc_info.get("unit", "件"),
                    })
                    inserted += 1
                    log_ui("工序追踪", "新增工序", f"{proc_info['process_seq']}. {proc_info['process_name']} = {proc_info['planned_qty']} {proc_info.get('unit', '件')}")

            self.load_processes()
            log_ui("工序追踪", "✅ 重新计算完成",
                   f"去重{dedup_deleted}条, 更新{updated}道, 新增{inserted}道")
            alert(f"重新计算完成！\n去重清理: {dedup_deleted} 条重复工序\n更新: {updated} 道\n新增: {inserted} 道", "操作成功")
        except Exception as e:
            log_ui("工序追踪", "❌ 重新计算失败", str(e))
            alert(f"计算失败：{e}", "错误")
