# -*- coding: utf-8 -*-
"""
质检管理视图
"""
import tkinter as tk
from tkinter import ttk
import time
from config import COLORS, FONTS, INSPECTION_TYPES, INSPECTION_RESULTS
from constants import OrderStatus, ProductionStatus
from models.order import OrderDAO
from models.quality import QualityDAO
from desktop.views.dialogs import popup_form, alert, confirm, center_window
from desktop.views.dialogs.quality_dialogs import (QualityTaskCompileDialog, QualityRecordFormDialog,
                                           CompletionConfirmDialog)
from utils.auto_refresh_mixin import AutoRefreshMixin

def _format_date(val):
    """安全格式化日期，处理datetime对象或字符串"""
    if hasattr(val, 'strftime'):
        return val.strftime('%Y-%m-%d %H:%M')
    elif val:
        return str(val)[:16]
    return "-"


class QualityView(AutoRefreshMixin, tk.Frame):

    def __init__(self, parent):
        super().__init__(parent, bg=COLORS["bg_main"])
        self.filters = {}
        self.init_ui()
        self.load_data()
        self.update_stats()
        self._start_auto_refresh()

    def init_ui(self):
        toolbar = tk.Frame(self, bg="#FFFFFF", height=50)
        toolbar.pack(fill=tk.X, side=tk.TOP)
        toolbar.pack_propagate(False)

        tk.Label(toolbar, text="✅ 质检管理", font=FONTS["large"], bg="#FFFFFF",
                fg=COLORS["primary"]).pack(side=tk.LEFT, padx=15, pady=10)

        ttk.Button(toolbar, text="+ 质检记录", command=self.add_record,
                  style="Accent.TButton").pack(side=tk.LEFT, padx=8)
        tk.Button(toolbar, text="📝 发布任务项编制", font=FONTS["body"],
                bg="#1976D2", fg=COLORS["text_white"], relief=tk.FLAT, padx=10, pady=3,
                cursor="hand2", command=self._open_task_compile).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="💬 发布质检任务", font=FONTS["body"],
                bg="#7E57C2", fg=COLORS["text_white"], relief=tk.FLAT, padx=10, pady=3,
                cursor="hand2", command=self._publish_quality_task).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="⚙️ 质量规则", font=FONTS["body"],
                bg="#00897B", fg=COLORS["text_white"], relief=tk.FLAT, padx=10, pady=3,
                cursor="hand2", command=self._open_quality_rules).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🔄 刷新", command=self.load_data).pack(side=tk.RIGHT, padx=10)
        ttk.Button(toolbar, text="🔄 状态同步", command=self._sync_status,
                  style="Accent.TButton").pack(side=tk.RIGHT, padx=10)

        self.stats_frame = tk.Frame(toolbar, bg="#FFFFFF")
        self.stats_frame.pack(side=tk.RIGHT, padx=15)

        filter_frame = tk.Frame(self, bg="#FFFFFF", padx=10, pady=5)
        filter_frame.pack(fill=tk.X, padx=10, pady=(5, 0))

        tk.Label(filter_frame, text="质检类型:", font=FONTS["body"], bg="#FFFFFF").pack(side=tk.LEFT, padx=5)
        self.type_combo = ttk.Combobox(filter_frame, values=["全部"] + INSPECTION_TYPES,
                                       width=10, font=FONTS["body"], state="readonly")
        self.type_combo.current(0)
        self.type_combo.pack(side=tk.LEFT, padx=5)
        self.type_combo.bind("<<ComboboxSelected>>", lambda e: self.load_data())

        tk.Label(filter_frame, text="结果:", font=FONTS["body"], bg="#FFFFFF").pack(side=tk.LEFT, padx=5)
        self.result_combo = ttk.Combobox(filter_frame, values=["全部"] + INSPECTION_RESULTS,
                                         width=8, font=FONTS["body"], state="readonly")
        self.result_combo.current(0)
        self.result_combo.pack(side=tk.LEFT, padx=5)
        self.result_combo.bind("<<ComboboxSelected>>", lambda e: self.load_data())

        tk.Label(filter_frame, text="关键词:", font=FONTS["body"], bg="#FFFFFF").pack(side=tk.LEFT, padx=5)
        self.kw_entry = ttk.Entry(filter_frame, width=15, font=FONTS["body"])
        self.kw_entry.pack(side=tk.LEFT, padx=5)
        self.kw_entry.bind("<Return>", lambda e: self.load_data())
        ttk.Button(filter_frame, text="搜索", command=self.load_data).pack(side=tk.LEFT, padx=3)

        table_frame = tk.Frame(self, bg="#FFFFFF", padx=10, pady=5)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))

        cols = ("date", "order_no", "customer", "type", "seq", "result", "defect",
                "items", "inspector", "remark")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings",
                                 height=18, style="Quality.Treeview")

        for col, txt, w in [
            ("date", "日期", 100), ("order_no", "订单号", 130), ("customer", "客户群", 100),
            ("type", "质检类型", 80), ("seq", "编号", 70), ("result", "结果", 70), ("defect", "不良数量", 70),
            ("items", "质检项目", 120), ("inspector", "质检员", 80), ("remark", "备注", 130)
        ]:
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=w, anchor="center" if col not in ("customer", "items", "remark") else "w")

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        style = ttk.Style()
        style.configure("Quality.Treeview", font=FONTS["subtitle"], rowheight=32)
        style.configure("Quality.Treeview.Heading", font=FONTS["heading"])
        self.tree.tag_configure("passed", foreground="#4CAF50")
        self.tree.tag_configure("failed", foreground="#F44336")
        self.tree.tag_configure("pending", foreground="#FF9800")

        self.tree.bind("<Double-Button-1>", self._on_dbl_click)
        self.tree.bind("<Button-3>", self._on_right_click)

    def _open_task_compile(self):
        QualityTaskCompileDialog(self, on_task_created=lambda: (self.load_data(), self.update_stats()))

    def _open_quality_rules(self):
        from .dialogs.quality_dialogs import QualityRulesDialog
        QualityRulesDialog(self)

    def _publish_quality_task(self):
        """发布已编制的质检任务到手机端"""
        from models.quality import QualityDAO
        from models.database import get_connection_context
        import json

        # 查待发布的质检记录
        records = QualityDAO.get_all({'result': '待检'})
        if not records:
            alert("没有待发布的质检任务\n请先使用「发布任务项编制」创建任务", "提示")
            return

        # 显示选择对话框
        from .dialogs.quality_dialogs import QualityPublishDialog
        QualityPublishDialog(self, records, on_publish=self._do_publish)

    def _do_publish(self, record):
        """发送质检任务到调度中心"""
        import os
        import requests
        order_no = (record.get('order_no') or '').strip()
        # 旧记录可能没有 order_no，从 orders 表反查
        if not order_no and record.get('order_id'):
            try:
                from models.order import OrderDAO
                orders = OrderDAO.get_all({})
                for o in orders:
                    if o.get('id') == record['order_id']:
                        order_no = o.get('order_no', '')
                        break
            except Exception:
                pass
        if not order_no:
            alert("该记录没有订单号，无法发布", "错误")
            return
        dispatch_url = os.environ.get('DISPATCH_CENTER_URL', 'http://localhost:5003')
        items = (record.get('inspection_items') or '')
        remark = (record.get('remark') or '')
        payload = {
            'order_no': order_no,
            'inspection_type': record.get('inspection_type') or '终检',
            'inspection_items': items,
            'inspector': (record.get('inspector') or ''),
            'process_name': remark.replace('工序：', '') or (record.get('process_name') or ''),
            'customer_group': (record.get('customer_name') or ''),
        }
        try:
            r = requests.post(f'{dispatch_url}/api/dispatch-center/quality/create', json=payload, timeout=10)
            if r.status_code == 200 and r.json().get('code') == 0:
                alert(f"✅ 质检任务已发布\n\n订单: {order_no}\n类型: {payload['inspection_type']}", "发布成功")
                self.load_data()
            else:
                alert(f"发布失败: {r.text[:200]}", "错误")
        except Exception as e:
            alert(f"发布失败: {str(e)}", "错误")

    def load_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        filters = {}
        filters["inspection_type"] = self.type_combo.get()
        filters["result"] = self.result_combo.get()
        filters["keyword"] = self.kw_entry.get().strip()

        records = QualityDAO.get_all(filters)
        self.record_map = {}
        for r in records:
            result = r.get("result", "待检")
            tag = "passed" if result == "合格" else "failed" if result == "不合格" else "pending"
            iid = self.tree.insert("", tk.END, values=(
                _format_date(r.get("record_date")),
                r.get("order_no", "") or r.get("order_no", ""),
                r.get("customer_name", ""),
                r.get("inspection_type", ""),
                r.get("inspection_no", ""),
                result,
                r.get("defect_qty", 0),
                r.get("inspection_items", ""),
                r.get("inspector", ""),
                r.get("remark", ""),
            ), tags=(tag,))
            self.record_map[iid] = r.get("id")

        self.update_stats()

    def update_stats(self):
        stats = QualityDAO.get_stats()
        for widget in self.stats_frame.winfo_children():
            widget.destroy()

        tk.Label(self.stats_frame, text=f"总计: {stats['total']} 条",
                font=FONTS["small"], bg="#FFFFFF", fg="#666").pack(side=tk.LEFT, padx=8)
        tk.Label(self.stats_frame, text=f"✅合格: {stats['passed']}",
                font=FONTS["small"], bg="#FFFFFF", fg="#4CAF50").pack(side=tk.LEFT, padx=8)
        tk.Label(self.stats_frame, text=f"❌不合格: {stats['failed']}",
                font=FONTS["small"], bg="#FFFFFF", fg="#F44336").pack(side=tk.LEFT, padx=8)
        tk.Label(self.stats_frame, text=f"⏳待复检: {stats['pending']}",
                font=FONTS["small"], bg="#FFFFFF", fg="#FF9800").pack(side=tk.LEFT, padx=8)
        tk.Label(self.stats_frame, text=f"合格率: {stats['pass_rate']}",
                font=FONTS["small"], bg="#FFFFFF", fg=COLORS["primary"]).pack(side=tk.LEFT, padx=8)

    def add_record(self):
        orders = OrderDAO.get_all({})
        pending_orders = [
            o for o in orders if o.get("status") in [
                OrderStatus.CONFIRMED.value,
                OrderStatus.SCHEDULED.value,
                OrderStatus.PRODUCTION.value,
                OrderStatus.QC.value,
            ]
        ]
        if not pending_orders:
            alert("暂无可质检的工单！\n\n可质检状态：待排产/已排产/生产中/质检中", "提示")
            return

        order_ids = [o["id"] for o in pending_orders]
        work_no_map = QualityDAO.get_work_no_map(order_ids)

        order_options = []
        order_map = {}
        for o in pending_orders:
            wn = work_no_map.get(o["id"], o["order_no"])
            label = f"{wn} - {o['customer_name']}"
            order_options.append(label)
            order_map[label] = o["id"]

        def get_order_processes(order_id):
            try:
                return QualityDAO.get_order_processes(order_id)
            except Exception:
                return []

        all_processes = {}
        for o in pending_orders:
            try:
                procs = QualityDAO.get_order_processes(o["id"])
                all_processes[o["id"]] = [p["process_name"] for p in procs if p.get("process_name")]
            except Exception:
                all_processes[o["id"]] = []

        default_procs = all_processes.get(pending_orders[0]["id"], ["原材料", "生产过程", "最终检验"]) if pending_orders else ["原材料", "生产过程", "最终检验"]

        fields = [
            ("选择工单 *", "order", order_options[0], "combo", order_options),
            ("选择工序 *", "process_name", default_procs[0] if default_procs else "最终检验", "combo", default_procs),
            ("质检类型 *", "inspection_type", INSPECTION_TYPES[0], "combo", INSPECTION_TYPES),
            ("质检结果 *", "result", INSPECTION_RESULTS[0], "combo", INSPECTION_RESULTS),
            ("质检项目", "inspection_items", "外观检验,尺寸检验", "textarea"),
            ("不良描述", "defect_description", "", "textarea"),
            ("不良数量(>=0整数)", "defect_qty", "0", "number"),
            ("处理方式", "handling_method", "无", "combo",
             ["返工", "降级使用", "报废", "特采放行", "无"]),
            ("质检员", "inspector", "", "entry"),
            ("备注", "remark", "", "entry"),
        ]

        def on_save(data):
            order_str = data.get("order", "")
            if order_str and order_str in order_map:
                data["order_id"] = order_map[order_str]
            del data["order"]

            selected_order = order_str.split(" - ")[0] if order_str else ""
            inspection_type = data.get("inspection_type", "")
            inspection_result = data.get("result", "")
            defect_qty = int(data.get("defect_qty", 0) or 0)

            record_id = QualityDAO.create(data)
            if inspection_result == "合格" and inspection_type == "终检":
                self._show_completion_confirm(data["order_id"], selected_order, data, defect_qty)
            elif inspection_result == "不合格":
                new_status = OrderStatus.QC.value
                QualityDAO.update_order_status(data["order_id"], new_status)

            self.load_data()
            self.update_stats()

            from datetime import datetime
            now = datetime.now().strftime("%Y-%m-%d %H:%M")

            if inspection_result == "合格":
                new_status = OrderStatus.FINISHED.value
                display_status = new_status
            elif inspection_result == "待复检":
                display_status = OrderStatus.QC.value
            else:
                display_status = "（状态不变）"

            record_info = f"""━━━━━━━━━━━━━━━━━━━━
📋 质检记录已保存

🕐 保存时间：{now}
📦 工单编号：{selected_order}
🔍 质检类型：{inspection_type}
📊 质检结果：{inspection_result}
👤 质检员：{data.get('inspector', '-')}
📝 备注：{data.get('remark', '-')}"""

            if inspection_result == "合格":
                record_info += f"\n\n✅ 工单状态已更新：{display_status}"
            elif inspection_result == "待复检":
                record_info += f"\n\n⏳ 工单状态：{display_status}"
            elif inspection_result == "不合格":
                defect_info = f"⚠️ 不合格数量：{defect_qty}\n🔧 处理方式：{data.get('handling_method', '-')}"
                record_info = record_info.replace("📝 备注", defect_info + "\n📝 备注")

            record_info += "\n━━━━━━━━━━━━━━━━━━━━"

            from .dialogs.quality_dialogs import QualitySaveResultDialog
            QualitySaveResultDialog(self, record_info)

        popup_form("新增质检记录", fields, on_save, width=550, window_key="quality_add_record")

    def _show_completion_confirm(self, order_id, selected_order, data, defect_qty):
        CompletionConfirmDialog(
            self, order_id, selected_order, data, defect_qty,
            on_confirmed=lambda: (self.load_data(), self.update_stats()),
            on_cancelled=lambda: (self.load_data(), self.update_stats())
        )

    def _on_dbl_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return
        values = self.tree.item(row_id, "values")
        if not values:
            return

    def _on_right_click(self, event):
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return
        self.tree.selection_set(row_id)
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="填写内容", command=lambda: self._open_qc_from_menu(row_id))
        menu.add_command(label="查看详情", command=lambda: self._view_detail(row_id))
        menu.add_command(label="删除", command=lambda: self._delete_record(row_id))
        menu.tk_popup(event.x_root, event.y_root)

    def _view_detail(self, row_id):
        values = self.tree.item(row_id, "values")
        if not values:
            return
        _, order_no, customer, qc_type, seq, result, defect, items, inspector, remark = values
        detail = f"""━━━━━━━━━━━━━━━━━━━━
📋 质检详情

📦 工单编号：{order_no}
👤 客户群：{customer}
🔍 质检类型：{qc_type}
🔢 编号：{seq}
📊 质检结果：{result}
⚠️ 不良数量：{defect}
📝 质检项目：{items}
👤 质检员：{inspector}
📋 备注：{remark}
━━━━━━━━━━━━━━━━━━━━"""
        alert(detail, "质检详情")

    def _open_qc_from_menu(self, row_id):
        """从右键菜单打开质检内容填写"""
        values = self.tree.item(row_id, "values")
        if not values:
            return
        record_id = self._get_record_id(row_id)
        self._open_qc_form(record_id, values, row_id)

    def _open_qc_form(self, record_id, values, row_id=None):
        QualityRecordFormDialog(
            self, record_id, values, row_id,
            on_saved=lambda rid, data: (self.load_data(), self.update_stats())
        )

    def _delete_record(self, row_id):
        values = self.tree.item(row_id, "values")
        if not values:
            return
        if not confirm(f"确定要删除这条质检记录吗？\n订单：{values[1]}", "删除确认"):
            return
        record_id = self._get_record_id(row_id)
        if record_id:
            QualityDAO.delete(record_id)
            self.load_data()
            self.update_stats()
            alert("删除成功", "操作完成")

    def _get_record_id(self, row_id):
        return self.record_map.get(row_id)
