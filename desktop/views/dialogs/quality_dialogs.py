import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog
import os
from models.order import OrderDAO
from models.quality import QualityDAO
from models.quality_rule import QualityRuleDAO
from config import COLORS, FONTS, INSPECTION_ITEMS_BY_CATEGORY, INSPECTION_TYPES
from desktop.views.dialogs import alert
from desktop.views.dialogs.base import BaseDialog

def _fmt_date(val):
    if hasattr(val, 'strftime'): return val.strftime('%Y-%m-%d %H:%M')
    return str(val)[:16] if val else '-'


class QualityTaskCompileDialog(BaseDialog):
    def __init__(self, parent, on_task_created=None):
        self._on_task_created = on_task_created
        self._item_vars = {}
        self._custom_items = []
        super().__init__(parent, title="质检任务项编制", width=800, height=750, resizable=True, window_key="quality_task_compile")

    def _build_ui(self):
        main_frame = tk.Frame(self.window, bg="#FFFFFF", padx=20, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(main_frame, text="选择订单:", font=FONTS["body"],
                bg="#FFFFFF").grid(row=0, column=0, sticky="w", pady=10)

        orders = OrderDAO.get_all({})
        order_ids = [o["id"] for o in orders]
        work_no_map = QualityDAO.get_work_no_map(order_ids)
        order_options = []
        self._order_map = {}
        for o in orders:
            wn = work_no_map.get(o["id"], o["order_no"])
            label = f"{wn} - {o['customer_name']}"
            order_options.append(label)
            self._order_map[label] = o

        self._order_var = tk.StringVar(value=order_options[0] if order_options else "")
        order_combo = ttk.Combobox(main_frame, textvariable=self._order_var,
                                   values=order_options, width=40, font=FONTS["body"],
                                   state="readonly")
        order_combo.grid(row=0, column=1, sticky="w", pady=10)

        tk.Label(main_frame, text="选择工序:", font=FONTS["body"],
                bg="#FFFFFF").grid(row=1, column=0, sticky="w", pady=10)

        self._process_var = tk.StringVar(value="")
        self._process_combo = ttk.Combobox(main_frame, textvariable=self._process_var,
                                           values=[], width=40, font=FONTS["body"],
                                           state="readonly")
        self._process_combo.grid(row=1, column=1, sticky="w", pady=10)

        tk.Label(main_frame, text="选择/添加质检项目:", font=FONTS["body"],
                bg="#FFFFFF").grid(row=2, column=0, sticky="nw", pady=10)

        item_frame = tk.Frame(main_frame, bg="#F5F5F5", bd=1, relief="solid")
        item_frame.grid(row=2, column=1, sticky="nsew", pady=10)
        item_canvas = tk.Canvas(item_frame, bg="#F5F5F5", highlightthickness=0)
        item_scroll = ttk.Scrollbar(item_frame, orient="vertical", command=item_canvas.yview)
        self._item_inner = tk.Frame(item_canvas, bg="#F5F5F5")
        self._item_inner.bind("<Configure>", lambda e: item_canvas.configure(
            scrollregion=item_canvas.bbox("all")))
        item_canvas.create_window((0, 0), window=self._item_inner, anchor="nw")
        item_canvas.configure(yscrollcommand=item_scroll.set)
        item_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        item_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._item_canvas = item_canvas
        main_frame.grid_rowconfigure(2, weight=1)

        tk.Label(main_frame, text="质检类型:", font=FONTS["body"],
                bg="#FFFFFF").grid(row=3, column=0, sticky="w", pady=10)

        self._type_var = tk.StringVar(value=INSPECTION_TYPES[0])
        type_combo = ttk.Combobox(main_frame, textvariable=self._type_var,
                                   values=INSPECTION_TYPES, width=20, font=FONTS["body"],
                                   state="readonly")
        type_combo.grid(row=3, column=1, sticky="w", pady=10)

        tk.Label(main_frame, text="质检员:", font=FONTS["body"],
                bg="#FFFFFF").grid(row=4, column=0, sticky="w", pady=10)

        self._inspector_var = tk.StringVar(value="")
        inspector_entry = ttk.Entry(main_frame, textvariable=self._inspector_var, width=30)
        inspector_entry.grid(row=4, column=1, sticky="w", pady=10)

        self._custom_entry_var = tk.StringVar(value="")

        order_combo.bind("<<ComboboxSelected>>", lambda e: self._update_process_options())
        self._process_combo.bind("<<ComboboxSelected>>", lambda e: self._update_item_list())

        if order_options:
            self._update_process_options()

        btn_frame = tk.Frame(main_frame, bg="#FFFFFF")
        btn_frame.grid(row=5, column=0, columnspan=2, pady=20)

        tk.Button(btn_frame, text="生成质检任务", font=FONTS["body"],
                 bg="#4CAF50", fg="white", relief=tk.FLAT, cursor="hand2",
                 padx=20, pady=8, command=self._handle_confirm).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="取消", font=FONTS["body"],
                 bg="#9E9E9E", fg="white", relief=tk.FLAT, cursor="hand2",
                 padx=20, pady=8, command=self._on_cancel).pack(side=tk.LEFT, padx=5)

    def _update_process_options(self):
        selected_order_str = self._order_var.get()
        if not selected_order_str or selected_order_str not in self._order_map:
            self._process_combo.configure(values=[])
            self._process_var.set("")
            self._update_item_list()
            return
        order = self._order_map[selected_order_str]
        processes = QualityDAO.get_order_processes(order["id"])
        process_names = [p["process_name"] for p in processes if p.get("process_name")]
        self._process_combo.configure(values=process_names)
        if process_names:
            self._process_var.set(process_names[0])
        else:
            self._process_var.set("")
        self._update_item_list()

    def _update_item_list(self):
        for widget in self._item_inner.winfo_children():
            widget.destroy()
        self._item_vars.clear()
        self._custom_items.clear()

        selected_order_str = self._order_var.get()
        selected_process = self._process_var.get()

        if not selected_process:
            tk.Label(self._item_inner, text="请先选择工序", font=FONTS["body"],
                    bg="#F5F5F5", fg="#666").pack(pady=20)
            return

        row = 0

        def add_category_header(cat_name):
            nonlocal row
            tk.Label(self._item_inner, text=f"◆ {cat_name}", font=FONTS["small"],
                    bg="#F5F5F5", fg=COLORS["primary"], anchor="w").grid(
                row=row, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5)
            )
            row += 1

        def add_checkbox(item_name):
            nonlocal row
            var = tk.BooleanVar(value=False)
            self._item_vars[item_name] = var
            tk.Checkbutton(self._item_inner, text=item_name, variable=var,
                          font=FONTS["body"], bg="#F5F5F5", anchor="w").grid(
                row=row, column=0, sticky="w", padx=20, pady=3)
            row += 1

        preset_items = INSPECTION_ITEMS_BY_CATEGORY.get(selected_process, {})
        if preset_items:
            add_category_header("【预设质检项目】")
            for category, items in preset_items.items():
                add_category_header(f"  {category}")
                for item in items:
                    add_checkbox(item)

        rules = QualityRuleDAO.get_rules_by_process(selected_process)
        if rules:
            add_category_header("【质检规则检查项】")
            for rule in rules:
                add_category_header(f"  {rule['rule_name']}")
                rule_items = QualityRuleDAO.get_rule_items(rule["id"])
                for rule_item in rule_items:
                    item_name = rule_item.get("inspection_item", "")
                    if item_name and item_name not in self._item_vars:
                        add_checkbox(item_name)

        add_category_header("【自定义添加】")
        custom_frame = tk.Frame(self._item_inner, bg="#F5F5F5")
        custom_frame.grid(row=row, column=0, columnspan=2, sticky="w", padx=15, pady=5)

        def add_custom_item():
            nonlocal row
            new_item = self._custom_entry_var.get().strip()
            if new_item and new_item not in self._item_vars:
                self._custom_items.append(new_item)
                var = tk.BooleanVar(value=False)
                self._item_vars[new_item] = var
                cb = tk.Checkbutton(self._item_inner, text=f"[自定义] {new_item}", variable=var,
                                  font=FONTS["body"], bg="#F5F5F5", fg="#E65100", anchor="w")
                cb.grid(row=row, column=0, sticky="w", padx=20, pady=3)
                row += 1
                self._custom_entry_var.set("")
                self._item_canvas.configure(scrollregion=self._item_canvas.bbox("all"))

        tk.Entry(custom_frame, textvariable=self._custom_entry_var, font=FONTS["body"],
                width=25).pack(side=tk.LEFT, padx=5)
        tk.Button(custom_frame, text="+ 添加", font=FONTS["small"],
                bg="#FF9800", fg="white", relief=tk.FLAT, cursor="hand2",
                command=add_custom_item).pack(side=tk.LEFT, padx=5)

    def _validate(self):
        selected_order_str = self._order_var.get()
        if not selected_order_str or selected_order_str not in self._order_map:
            return False, "请选择工单"
        selected_process = self._process_var.get()
        if not selected_process:
            return False, "请选择工序"
        selected_items = [item for item, var in self._item_vars.items() if var.get()]
        if not selected_items:
            return False, "请至少选择一个质检项目"
        return True, ""

    def _on_confirm(self):
        selected_order_str = self._order_var.get()
        order = self._order_map[selected_order_str]
        selected_process = self._process_var.get()
        selected_items = [item for item, var in self._item_vars.items() if var.get()]

        prod = QualityDAO.get_production_by_order(order["id"])
        prod_id = prod["id"] if prod else None

        QualityDAO.create({
            "order_id": order["id"],
            "order_no": order.get("order_no", ""),
            "production_id": prod_id,
            "inspection_type": self._type_var.get(),
            "inspection_items": ",".join(selected_items),
            "result": "待检",
            "defect_description": "",
            "defect_qty": 0,
            "handling_method": "无",
            "inspector": self._inspector_var.get(),
            "remark": f"工序：{selected_process}"
        })

        self.window.destroy()
        alert(f"质检任务已编制！\n工序：{selected_process}\n项目：{', '.join(selected_items)}\n请点击「发布质检任务」发送到手机端", "成功")
        if self._on_task_created:
            self._on_task_created()

    def _on_cancel(self):
        self.window.destroy()


class QualityPublishDialog(BaseDialog):
    """选择已编制的质检任务，发布到手机端"""
    def __init__(self, parent, records, on_publish=None):
        self._records = records
        self._on_publish = on_publish
        self._selected_index = None
        super().__init__(parent, title="选择要发布的质检任务", width=700, height=500, resizable=True)

    def _build_ui(self):
        main_frame = tk.Frame(self.window, bg="#FFFFFF", padx=15, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(main_frame, text=f"共 {len(self._records)} 条待发布质检任务，选择一条后点击发送",
                font=FONTS["body"], bg="#FFFFFF", fg="#666").pack(anchor="w", pady=(0,10))

        # 列表
        list_frame = tk.Frame(main_frame, bg="#F5F5F5")
        list_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("日期", "订单号", "类型", "工序", "检查项", "质检员")
        self._tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=12)
        for col in columns:
            self._tree.heading(col, text=col)
        self._tree.column("日期", width=130)
        self._tree.column("订单号", width=120)
        self._tree.column("类型", width=60)
        self._tree.column("工序", width=80)
        self._tree.column("检查项", width=180)
        self._tree.column("质检员", width=70)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for r in self._records:
            self._tree.insert("", tk.END, values=(
                _fmt_date(r.get("record_date")),
                r.get("order_no", ""),
                r.get("inspection_type", ""),
                r.get("remark", "").replace("工序：", "") if r.get("remark") else "",
                r.get("inspection_items", ""),
                r.get("inspector", ""),
            ))

        self._tree.bind("<<TreeviewSelect>>", lambda e: self._set_footer(True))

        # 底部按钮
        btn_frame = tk.Frame(main_frame, bg="#FFFFFF")
        btn_frame.pack(fill=tk.X, pady=(10,0))
        tk.Button(btn_frame, text="取消", font=FONTS["body"], bg="#ccc", fg="#333",
                command=self._on_cancel).pack(side=tk.LEFT, padx=5)
        self._send_btn = tk.Button(btn_frame, text="📤 发送到移动端", font=FONTS["body"],
                bg="#7E57C2", fg="white", state="disabled",
                command=self._on_send)
        self._send_btn.pack(side=tk.RIGHT, padx=5)

    def _set_footer(self, enabled):
        self._send_btn.configure(state="normal" if enabled else "disabled")

    def _on_send(self):
        sel = self._tree.selection()
        if not sel:
            return
        idx = self._tree.index(sel[0])
        if 0 <= idx < len(self._records):
            if self._on_publish:
                self._on_publish(self._records[idx])
            self.window.destroy()

    def _on_cancel(self):
        self.window.destroy()


class QualityRecordFormDialog(BaseDialog):
    def __init__(self, parent, record_id, values, row_id=None, on_saved=None):
        self._record_id = record_id
        self._values = values
        self._row_id = row_id
        self._on_saved = on_saved

        _, order_no, customer, qc_type, seq, current_result, current_defect, \
            current_items, current_inspector, current_remark = values

        self._order_no = order_no
        self._customer = customer
        self._qc_type = qc_type
        self._seq = seq
        self._current_result = current_result
        self._current_defect = current_defect
        self._current_items = current_items
        self._current_inspector = current_inspector
        self._current_remark = current_remark

        super().__init__(parent, title=f"质检内容填写 - {qc_type} {seq}", width=650, height=700, resizable=True, window_key="qc_form")

    def _build_ui(self):
        main_frame = tk.Frame(self.window, bg="#FFFFFF", padx=20, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        row = 0
        tk.Label(main_frame, text="工单编号：", font=FONTS["body"], bg="#FFFFFF", anchor="w").grid(row=row, column=0, sticky="w", pady=8)
        tk.Label(main_frame, text=self._order_no, font=FONTS["body"], bg="#E3F2FD", anchor="w").grid(row=row, column=1, sticky="w", pady=8, padx=10)

        row += 1
        tk.Label(main_frame, text="客户群：", font=FONTS["body"], bg="#FFFFFF", anchor="w").grid(row=row, column=0, sticky="w", pady=8)
        tk.Label(main_frame, text=self._customer, font=FONTS["body"], bg="#E3F2FD", anchor="w").grid(row=row, column=1, sticky="w", pady=8, padx=10)

        row += 1
        tk.Label(main_frame, text="质检类型：", font=FONTS["body"], bg="#FFFFFF", anchor="w").grid(row=row, column=0, sticky="w", pady=8)
        tk.Label(main_frame, text=f"{self._qc_type} {self._seq}", font=FONTS["body"], bg="#E3F2FD", anchor="w").grid(row=row, column=1, sticky="w", pady=8, padx=10)

        row += 1
        tk.Label(main_frame, text="质检项目：", font=FONTS["body"], bg="#FFFFFF", anchor="w").grid(row=row, column=0, sticky="w", pady=8)
        tk.Label(main_frame, text=self._current_items or "无", font=FONTS["body"], bg="#FFF3E0", anchor="w", wraplength=400).grid(row=row, column=1, sticky="w", pady=8, padx=10)

        item_names = [item.strip() for item in (self._current_items or "").split(",") if item.strip()]
        self._item_input_vars = {}
        self._item_attach_vars = {}
        self._item_check_vars = {}

        for item_name in item_names:
            row += 1
            check_var = tk.BooleanVar(value=False)
            self._item_check_vars[item_name] = check_var

            tk.Checkbutton(main_frame, text=f"√ {item_name}", variable=check_var, font=FONTS["body"],
                          bg="#FFFFFF", cursor="hand2", command=lambda v=check_var, n=item_name: self._on_check(v, n)).grid(
                row=row, column=0, sticky="w", pady=8)
            item_row_frame = tk.Frame(main_frame, bg="#FFFFFF")
            item_row_frame.grid(row=row, column=1, sticky="w", pady=8, padx=10)

            item_var = tk.StringVar(value="")
            attach_var = tk.StringVar(value="")
            entry_widget = tk.Entry(item_row_frame, textvariable=item_var, font=FONTS["body"], width=32, state="disabled")
            entry_widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
            btn_widget = tk.Button(item_row_frame, text="📎", font=FONTS["body"],
                     command=lambda v=attach_var: self._add_attachment(v),
                     bg="#2196F3", fg="white", relief=tk.FLAT, cursor="hand2", width=4, state="disabled")
            btn_widget.pack(side=tk.LEFT, padx=5)

            self._item_input_vars[item_name] = (item_var, entry_widget)
            self._item_attach_vars[item_name] = (attach_var, btn_widget)

        row += 1
        tk.Label(main_frame, text="质检员 *：", font=FONTS["body"], bg="#FFFFFF", anchor="w").grid(row=row, column=0, sticky="w", pady=8)
        inspector_frame = tk.Frame(main_frame, bg="#FFFFFF")
        inspector_frame.grid(row=row, column=1, sticky="w", pady=8, padx=10)
        self._inspector_var = tk.StringVar(value=self._current_inspector or "")
        self._inspector_entry = tk.Entry(inspector_frame, textvariable=self._inspector_var, font=FONTS["body"], width=30)
        self._inspector_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(inspector_frame, text="*", font=FONTS["body"], fg="#F44336", bg="#FFFFFF").pack(side=tk.LEFT)

        row += 1
        tk.Label(main_frame, text="质检结果：", font=FONTS["body"], bg="#FFFFFF", anchor="w").grid(row=row, column=0, sticky="w", pady=8)
        self._result_var = tk.StringVar(value=self._current_result)
        result_frame = tk.Frame(main_frame, bg="#FFFFFF")
        result_frame.grid(row=row, column=1, sticky="w", pady=8, padx=10)
        for r_text, color in [("待检", "#FF9800"), ("合格", "#4CAF50"), ("不合格", "#F44336")]:
            tk.Radiobutton(result_frame, text=r_text, variable=self._result_var, value=r_text, font=FONTS["body"],
                          fg=color, bg="#FFFFFF", cursor="hand2").pack(side=tk.LEFT, padx=10)

        row += 1
        tk.Label(main_frame, text="不良数量：", font=FONTS["body"], bg="#FFFFFF", anchor="w").grid(row=row, column=0, sticky="w", pady=8)
        self._defect_var = tk.StringVar(value=str(self._current_defect) if self._current_defect else "0")
        tk.Entry(main_frame, textvariable=self._defect_var, font=FONTS["body"], width=15).grid(row=row, column=1, sticky="w", pady=8, padx=10)

        row += 1
        tk.Label(main_frame, text="不良描述：", font=FONTS["body"], bg="#FFFFFF", anchor="w").grid(row=row, column=0, sticky="nw", pady=8)
        defect_desc_frame = tk.Frame(main_frame, bg="#FFFFFF")
        defect_desc_frame.grid(row=row, column=1, sticky="w", pady=8, padx=10)
        self._defect_desc_text = tk.Text(defect_desc_frame, font=FONTS["body"], width=45, height=4, wrap=tk.WORD)
        self._defect_desc_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(defect_desc_frame, orient=tk.VERTICAL, command=self._defect_desc_text.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._defect_desc_text.configure(yscrollcommand=scroll.set)

        row += 1
        tk.Label(main_frame, text="处理方式：", font=FONTS["body"], bg="#FFFFFF", anchor="w").grid(row=row, column=0, sticky="w", pady=8)
        self._handling_var = tk.StringVar(value="无")
        handling_combo = ttk.Combobox(main_frame, textvariable=self._handling_var, font=FONTS["body"], width=28,
                                       values=["无", "返工", "报废", "让步接收", "降级处理"], state="readonly")
        handling_combo.grid(row=row, column=1, sticky="w", pady=8, padx=10)

        row += 1
        tk.Label(main_frame, text="备注：", font=FONTS["body"], bg="#FFFFFF", anchor="w").grid(row=row, column=0, sticky="nw", pady=8)
        remark_frame = tk.Frame(main_frame, bg="#FFFFFF")
        remark_frame.grid(row=row, column=1, sticky="w", pady=8, padx=10)
        self._remark_text = tk.Text(remark_frame, font=FONTS["body"], width=45, height=3, wrap=tk.WORD)
        self._remark_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._remark_text.insert("1.0", self._current_remark or "")

        btn_frame = tk.Frame(self.window, bg="#F5F5F5", pady=10)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)

        tk.Button(btn_frame, text="保存", font=FONTS["normal_bold"],
                 bg="#4CAF50", fg="white", relief=tk.FLAT, cursor="hand2",
                 padx=30, pady=8, command=self._handle_confirm).pack(side=tk.LEFT, padx=20)
        tk.Button(btn_frame, text="取消", font=FONTS["body"],
                 bg="#9E9E9E", fg="white", relief=tk.FLAT, cursor="hand2",
                 padx=20, pady=8, command=self._on_cancel).pack(side=tk.LEFT)

    def _on_check(self, check_var, item_name):
        if check_var.get():
            self._item_input_vars[item_name][1].config(state="normal")
            self._item_attach_vars[item_name][1].config(state="normal")
        else:
            self._item_input_vars[item_name][1].config(state="disabled")
            self._item_input_vars[item_name][0].set("")
            self._item_attach_vars[item_name][1].config(state="disabled")
            self._item_attach_vars[item_name][0].set("")

    def _add_attachment(self, target_var):
        file_path = filedialog.askopenfilename(
            title="选择附件（单个文件不超过2M）",
            filetypes=[("图片文件", "*.jpg *.jpeg *.png *.gif *.bmp"), ("所有文件", "*.*")]
        )
        if not file_path:
            return
        file_size = os.path.getsize(file_path)
        if file_size > 2 * 1024 * 1024:
            alert("附件大小不能超过2M", "提示")
            return
        target_var.set(file_path)

    def _validate(self):
        if not self._inspector_var.get().strip():
            return False, "请填写质检员（必填项）"
        checked_items = {k: v for k, v in self._item_check_vars.items() if v.get()}
        if not checked_items:
            return False, "请至少选择一项检验项进行填写"
        for item_name in checked_items:
            if not self._item_input_vars[item_name][0].get().strip():
                return False, f"请填写 {item_name} 的检验结果"
        return True, ""

    def _on_confirm(self):
        inspector_val = self._inspector_var.get().strip()
        checked_items = {k: v for k, v in self._item_check_vars.items() if v.get()}

        try:
            defect_qty = int(self._defect_var.get() or 0)
        except ValueError:
            defect_qty = 0

        update_data = {
            "result": self._result_var.get(),
            "defect_qty": defect_qty,
            "defect_description": self._defect_desc_text.get("1.0", tk.END).strip(),
            "handling_method": self._handling_var.get(),
            "inspector": inspector_val,
            "remark": self._remark_text.get("1.0", tk.END).strip(),
            "inspection_items": ";".join(
                [f"{k}:{self._item_input_vars[k][0].get().strip()}" for k in checked_items]),
            "attachment_path": "|".join(
                [f"{k}:{self._item_attach_vars[k][0].get().strip()}" for k in checked_items])
        }
        QualityDAO.update(self._record_id, update_data)
        self.window.destroy()
        alert("保存成功！", "完成")
        if self._on_saved:
            self._on_saved(self._record_id, update_data)

    def _on_cancel(self):
        self.window.destroy()


class CompletionConfirmDialog(BaseDialog):
    def __init__(self, parent, order_id, selected_order, data, defect_qty, on_confirmed=None, on_cancelled=None):
        from datetime import datetime

        self._order_id = order_id
        self._selected_order = selected_order
        self._data = data
        self._defect_qty = defect_qty
        self._on_confirmed = on_confirmed
        self._on_cancelled = on_cancelled
        self._now = datetime.now().strftime("%Y-%m-%d %H:%M")

        super().__init__(parent, title="✅ 终检合格 - 工单完成确认", width=460, height=380, topmost=True)

    def _build_ui(self):
        tk.Label(self.window, text="✅ 终检合格", font=FONTS["large_bold"],
                bg="#E8F5E9", fg="#2E7D32", pady=12).pack(fill=tk.X, padx=20, pady=(20, 10))
        tk.Label(self.window, text="请确认是否完成此工单", font=FONTS["body"],
                bg="#FAFAFA", fg="#555").pack()

        card = tk.Frame(self.window, bg="#F5F5F5", bd=1, relief="solid")
        card.pack(fill=tk.X, padx=20, pady=15)

        order_info_text = f"""📦 工单编号：{self._selected_order}
🔍 质检类型：终检
📊 质检结果：合格
⚠️ 不良数量：{self._defect_qty}
👤 质检员：{self._data.get('inspector', '-')}
🕐 质检时间：{self._now}"""

        tk.Label(card, text=order_info_text, font=FONTS["body"], justify=tk.LEFT,
                bg="#F5F5F5", fg="#333", anchor="w").pack(anchor="w", padx=15, pady=12)

        from constants import OrderStatus
        tk.Label(self.window,
                text=f"确认后系统将：自动创建成品入库，工单状态更新为「{OrderStatus.FINISHED.value}」",
                font=FONTS["small"], bg="#FFF8E1", fg="#F57C00",
                padx=10, pady=8).pack(fill=tk.X, padx=20, pady=(0, 10))

        btn_frame = tk.Frame(self.window, bg="#FFFFFF")
        btn_frame.pack(fill=tk.X, padx=20, pady=(5, 20))

        tk.Button(btn_frame, text="✅ 确认完成", font=FONTS["body"],
                 bg="#4CAF50", fg="white", relief=tk.FLAT, cursor="hand2",
                 padx=20, pady=8, command=self._handle_confirm).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="⏳ 暂不完成", font=FONTS["body"],
                 bg="#9E9E9E", fg="white", relief=tk.FLAT, cursor="hand2",
                 padx=20, pady=8, command=self._on_cancel).pack(side=tk.LEFT, padx=10)

    def _on_confirm(self):
        QualityDAO.confirm_order_completion(self._order_id)
        self.window.destroy()
        alert("工单已完成！", "操作成功")
        if self._on_confirmed:
            self._on_confirmed()

    def _on_cancel(self):
        self.window.destroy()
        if self._on_cancelled:
            self._on_cancelled()


class QualityRulesDialog(BaseDialog):
    """质量监督规则配置容器对话框"""

    def __init__(self, parent):
        super().__init__(parent, title="⚙️ 质量监督规则配置", width=1000, height=600, resizable=True)

    def _build_ui(self):
        from desktop.views.quality_rule_view import QualityRuleView
        QualityRuleView(self.window).pack(fill=tk.BOTH, expand=True)

    def _on_cancel(self):
        self.window.destroy()


class QualitySaveResultDialog(BaseDialog):
    """质检保存结果展示对话框"""

    def __init__(self, parent, record_info: str):
        self._record_info = record_info
        super().__init__(parent, title="保存成功", width=400, height=340)

    def _build_ui(self):
        tk.Label(self.window, text=self._record_info, font=FONTS["body"], justify=tk.LEFT,
                 bg="#f5f5f5", fg="#333").pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        tk.Frame(self.window, height=2, bg="#ddd").pack(fill=tk.X, padx=20)
        tk.Button(self.window, text="确定", command=self.window.destroy, font=FONTS["body"],
                  bg="#4CAF50", fg="white", relief=tk.FLAT, cursor="hand2").pack(pady=15)
        self.window.bind("<Return>", lambda e: self.window.destroy())

    def _on_cancel(self):
        self.window.destroy()
