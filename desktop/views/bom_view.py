# -*- coding: utf-8 -*-
"""
BOM物料清单视图
"""
import tkinter as tk
from tkinter import ttk
from config import COLORS, FONTS
from models.bom import BOMDAO
from desktop.views.dialogs import popup_form, alert
from utils.helpers import format_date


class BOMView(tk.Frame):
    """BOM物料清单管理视图"""

    def __init__(self, parent):
        super().__init__(parent, bg=COLORS["bg_main"])
        self.filters = {}
        self.init_ui()
        self.load_data()

    def init_ui(self):
        toolbar = tk.Frame(self, bg="#FFFFFF", height=50)
        toolbar.pack(fill=tk.X, side=tk.TOP)
        toolbar.pack_propagate(False)

        tk.Label(toolbar, text="📦 BOM物料清单", font=FONTS["large"], bg="#FFFFFF",
                fg=COLORS["primary"]).pack(side=tk.LEFT, padx=15, pady=10)

        btn_frame = tk.Frame(toolbar, bg="#FFFFFF")
        btn_frame.pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="➕ 新建BOM", command=self._create_bom).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="✏️ 编辑选中", command=self._edit_selected).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="🗑️ 删除选中", command=self._delete_selected).pack(side=tk.LEFT, padx=3)

        ttk.Button(toolbar, text="🔄 刷新", command=self.load_data).pack(side=tk.RIGHT, padx=10)

        filter_frame = tk.Frame(toolbar, bg="#FFFFFF")
        filter_frame.pack(side=tk.RIGHT, padx=10)

        tk.Label(filter_frame, text="产品类型:", font=FONTS["body"], bg="#FFFFFF").pack(side=tk.LEFT, padx=5)
        self.product_entry = ttk.Entry(filter_frame, width=12, font=FONTS["body"])
        self.product_entry.pack(side=tk.LEFT, padx=5)
        self.product_entry.bind("<Return>", lambda e: self.load_data())

        tk.Label(filter_frame, text="材质:", font=FONTS["body"], bg="#FFFFFF").pack(side=tk.LEFT, padx=5)
        self.material_entry = ttk.Entry(filter_frame, width=10, font=FONTS["body"])
        self.material_entry.pack(side=tk.LEFT, padx=5)
        self.material_entry.bind("<Return>", lambda e: self.load_data())

        ttk.Button(filter_frame, text="搜索", command=self.load_data).pack(side=tk.LEFT, padx=3)

        table_frame = tk.Frame(self, bg="#FFFFFF", padx=10, pady=5)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))

        cols = ("product", "material", "spec", "steel_weight", "waste_rate", "unit", "process", "packaging", "material_code", "price", "supplier", "remark")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=18)

        col_configs = [
            ("product", "产品类型", 100),
            ("material", "材质", 80),
            ("spec", "规格", 120),
            ("steel_weight", "用钢量(kg/米)", 100),
            ("waste_rate", "损耗率(%)", 80),
            ("unit", "计量单位", 70),
            ("process", "生产工艺", 120),
            ("packaging", "包装材料", 100),
            ("material_code", "物料编码", 100),
            ("price", "单价(元)", 80),
            ("supplier", "供应商", 100),
            ("remark", "备注", 100),
        ]
        for col, txt, w in col_configs:
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=w, anchor="w")

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        style = ttk.Style()
        style.configure("Treeview", font=("微软雅黑", 12), rowheight=32)

        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.show_context_menu)

        info_frame = tk.Frame(self, bg="#E3F2FD", padx=10, pady=8)
        info_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        tk.Label(info_frame,
                text="💡 提示：BOM（Bill of Materials）定义每种产品规格的原材料配比，用于自动计算材料需求",
                font=FONTS["small"], bg="#E3F2FD", fg="#1565C0").pack(anchor="w")

    def load_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.filters = {
            "product_type": self.product_entry.get().strip(),
            "material": self.material_entry.get().strip()
        }

        if self.filters["product_type"] or self.filters["material"]:
            bom_list = BOMDAO.get_all(self.filters)
        else:
            bom_list = BOMDAO.get_recent(limit=200)

        for bom in bom_list:
            self.tree.insert("", tk.END, values=(
                bom.get("product_type") or "无",
                bom.get("material") or "无",
                bom.get("specification") or "无",
                f"{bom.get('steel_weight') or 0:.2f}",
                f"{bom.get('waste_rate') or 0:.1f}",
                bom.get("unit") or "米",
                bom.get("production_process") or "无",
                bom.get("packaging_materials") or "无",
                bom.get("material_code") or "无",
                f"{bom.get('price') or 0:.2f}",
                bom.get("supplier") or "无",
                bom.get("remark") or "无",
            ), tags=(str(bom["id"]),))

    def on_double_click(self, event):
        self._edit_selected()

    def _create_bom(self):
        """创建新BOM"""
        fields = [
            ("产品类型 *", "product_type", "", "entry"),
            ("材　　质 *", "material", "", "entry"),
            ("用钢量(kg/米)", "steel_weight", "0", "number"),
            ("用钢量单位", "steel_unit", "kg/米", "entry"),
            ("损耗率(%)", "waste_rate", "5", "number"),
            ("计量单位", "unit", "米", "entry"),
            ("包装材料", "packaging_materials", "", "entry"),
            ("表面处理", "surface_treatment", "", "entry"),
            ("生产工艺", "production_process", "", "entry"),
            ("备　　注", "remark", "", "textarea"),
        ]

        def on_save(data):
            if not data.get("product_type") or not data.get("material"):
                alert("产品类型和材质为必填项！", "提示")
                return
            try:
                BOMDAO.create(data["product_type"], data["material"], data)
                self.load_data()
                alert("BOM创建成功！", "成功")
            except Exception as e:
                alert(f"创建失败: {e}", "错误")

        popup_form("新建BOM物料清单", fields, on_save, width=550)

    def _edit_selected(self):
        sel = self.tree.selection()
        if not sel:
            alert("请先选择要编辑的BOM", "提示")
            return

        item = self.tree.item(sel[0])
        bom_id = int(item["tags"][0])
        bom = BOMDAO.get_by_id(bom_id)
        if not bom:
            alert("BOM记录不存在", "错误")
            return

        fields = [
            ("产品类型 *", "product_type", bom.get("product_type", ""), "readonly"),
            ("材　　质 *", "material", bom.get("material", ""), "readonly"),
            ("用钢量(kg/米)", "steel_weight", str(bom.get("steel_weight", 0)), "number"),
            ("用钢量单位", "steel_unit", bom.get("steel_unit", "kg/米"), "entry"),
            ("损耗率(%)", "waste_rate", str(bom.get("waste_rate", 0)), "number"),
            ("计量单位", "unit", bom.get("unit", "米"), "entry"),
            ("包装材料", "packaging_materials", bom.get("packaging_materials", ""), "entry"),
            ("表面处理", "surface_treatment", bom.get("surface_treatment", ""), "entry"),
            ("生产工艺", "production_process", bom.get("production_process", ""), "entry"),
            ("备　　注", "remark", bom.get("remark", ""), "textarea"),
        ]

        def on_save(data):
            try:
                BOMDAO.update(bom_id, data)
                self.load_data()
                alert("BOM更新成功！", "成功")
            except Exception as e:
                alert(f"更新失败: {e}", "错误")

        popup_form("编辑BOM物料清单", fields, on_save, width=550)

    def _delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            alert("请先选择要删除的BOM", "提示")
            return
        
        item = self.tree.item(sel[0])
        bom_id = int(item["tags"][0])
        product = item["values"][0]
        material = item["values"][1]

        from tkinter import messagebox
        if messagebox.askyesno("确认删除", f"确定删除「{product} - {material}」的BOM吗？"):
            if BOMDAO.delete(bom_id):
                self.load_data()
                alert("删除成功", "成功")
            else:
                alert("删除失败", "错误")

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.tree.selection_set(item)
        
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="编辑BOM", command=self._edit_selected)
        menu.add_command(label="计算材料需求", command=self._calculate_requirement)
        menu.add_separator()
        menu.add_command(label="删除", command=self._delete_selected)
        menu.post(event.x_root, event.y_root)

    def _calculate_requirement(self):
        """计算材料需求"""
        sel = self.tree.selection()
        if not sel:
            alert("请先选择BOM", "提示")
            return
        
        item = self.tree.item(sel[0])
        product_type = item["values"][0]
        material = item["values"][1]
        
        # 输入数量弹窗
        fields = [
            ("产品", "product", product_type, "readonly"),
            ("材质", "material", material, "readonly"),
            ("订单数量", "quantity", "100", "number"),
            ("计量单位", "unit", "米", "readonly"),
        ]
        
        def on_calc(data):
            try:
                qty = float(data.get("quantity", 0))
                if qty <= 0:
                    alert("数量必须大于0", "提示")
                    return
                    
                result = BOMDAO.calculate_material_requirement(product_type, material, qty)
                if result:
                    self._show_requirement_result(result)
                else:
                    alert("未找到对应的BOM", "提示")
            except ValueError:
                alert("请输入有效的数量", "提示")
        
        popup_form("计算材料需求", fields, on_calc, width=400)

    def _show_requirement_result(self, result: dict):
        """显示计算结果"""
        win = tk.Toplevel(self)
        win.title("材料需求计算结果")
        win.geometry("450x350")
        win.transient(self.winfo_toplevel())
        win.grab_set()
        win.configure(bg="#FFFFFF")

        tk.Label(win, text="📋 材料需求清单", font=FONTS["subtitle"], bg="#FFFFFF").pack(pady=10)

        result_frame = tk.Frame(win, bg="#FFFFFF", relief=tk.RIDGE, bd=1)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        rows = [
            ("产品类型", result.get("product_type", "-")),
            ("材　　质", result.get("material", "-")),
            ("订单数量", f"{result.get('quantity', 0)} {result.get('unit', '米')}"),
            ("", ""),
            ("━ 基本需求 ━", ""),
            ("单位用钢量", f"{result.get('steel_weight_per_unit', 0):.4f} {result.get('steel_unit', 'kg/米')}"),
            ("总用钢量", f"{result.get('steel_weight_per_unit', 0) * result.get('quantity', 0):.2f} kg"),
            ("", ""),
            ("━ 含损耗 ━", ""),
            ("损耗率", f"{result.get('waste_rate', 0):.1f}%"),
            ("损耗量", f"{result.get('waste_amount', 0):.2f} kg"),
            ("实际需求", f"{result.get('total_steel_required', 0):.2f} kg"),
            ("", ""),
            ("━ 其他材料 ━", ""),
            ("包装材料", result.get("packaging_materials", "-") or "无"),
            ("表面处理", result.get("surface_treatment", "-") or "无"),
        ]

        for i, (label, value) in enumerate(rows):
            if not label and not value:
                tk.Frame(result_frame, height=5).grid(row=i, columnspan=2)
                continue
            tk.Label(result_frame, text=f"{label}：", font=FONTS["normal_bold"] if "━" not in label else FONTS["small"],
                    bg="#FFFFFF", anchor="e").grid(row=i, column=0, sticky="e", padx=10, pady=3)
            tk.Label(result_frame, text=value, font=FONTS["body"],
                    bg="#FFFFFF", fg=COLORS["primary"] if "实际需求" in label else "#333333").grid(
                    row=i, column=1, sticky="w", padx=10, pady=3)

        ttk.Button(win, text="关闭", command=win.destroy).pack(pady=15)
