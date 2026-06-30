# -*- coding: utf-8 -*-
"""
Excel导入导出视图
"""
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from config import COLORS, FONTS
from utils.excel_utils import ExcelExporter, ExcelImporter, create_template, get_template_path
from desktop.views.dialogs import alert


class ExcelView(tk.Frame):
    """Excel导入导出视图"""

    def __init__(self, parent, refresh_callback=None):
        super().__init__(parent, bg=COLORS["bg_main"])
        self.refresh_callback = refresh_callback
        self.init_ui()

    def init_ui(self):
        # 主容器
        main_frame = tk.Frame(self, bg="#FFFFFF", relief=tk.RIDGE, bd=1)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        tk.Label(main_frame, text="📊 Excel数据导入导出", font=FONTS["large"],
                bg="#FFFFFF", fg=COLORS["primary"]).pack(pady=15)

        # 说明
        info = tk.Label(main_frame, 
            text="💡 支持批量导入订单、库存、BOM数据，也可导出现有数据为Excel",
            font=FONTS["small"], bg="#E3F2FD", fg="#1565C0", padx=10, pady=8)
        info.pack(fill=tk.X, padx=20, pady=(0, 15))

        # 导出区域
        export_frame = tk.LabelFrame(main_frame, text="📤 导出数据", font=FONTS["subtitle"],
                                     bg="#FFFFFF", padx=15, pady=10)
        export_frame.pack(fill=tk.X, padx=20, pady=10)

        export_btns = [
            ("📋 导出订单列表", "orders", self._export_orders),
            ("📦 导出库存数据", "inventory", self._export_inventory),
            ("📄 导出BOM清单", "bom", self._export_bom),
            ("📝 导出备料清单", "material_prep", self._export_material_prep),
        ]

        for text, key, cmd in export_btns:
            ttk.Button(export_frame, text=text, command=cmd, width=18).pack(side=tk.LEFT, padx=5, pady=5)

        # 导入区域
        import_frame = tk.LabelFrame(main_frame, text="📥 导入数据", font=FONTS["subtitle"],
                                    bg="#FFFFFF", padx=15, pady=10)
        import_frame.pack(fill=tk.X, padx=20, pady=10)

        import_btns = [
            ("📋 导入订单", "orders", self._import_orders),
            ("📦 导入库存", "inventory", self._import_inventory),
            ("📄 导入BOM", "bom", self._import_bom),
        ]

        for text, key, cmd in import_btns:
            ttk.Button(import_frame, text=text, command=cmd, width=18).pack(side=tk.LEFT, padx=5, pady=5)

        # 模板区域
        template_frame = tk.LabelFrame(main_frame, text="📑 下载模板", font=FONTS["subtitle"],
                                       bg="#FFFFFF", padx=15, pady=10)
        template_frame.pack(fill=tk.X, padx=20, pady=10)

        template_btns = [
            ("📋 订单模板", "orders"),
            ("📦 库存模板", "inventory"),
            ("📄 BOM模板", "bom"),
        ]

        for text, key in template_btns:
            ttk.Button(template_frame, text=text, 
                      command=lambda k=key: self._download_template(k), 
                      width=18).pack(side=tk.LEFT, padx=5, pady=5)

        # 操作记录
        log_frame = tk.LabelFrame(main_frame, text="📝 操作记录", font=FONTS["subtitle"],
                                 bg="#FFFFFF", padx=15, pady=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        self.log_text = tk.Text(log_frame, font=FONTS["small"], height=10, 
                                relief=tk.SUNKEN, bd=1, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        scroll = ttk.Scrollbar(self.log_text, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)

        self._log("系统就绪，请选择导入或导出操作")

    def _log(self, message: str):
        """添加日志"""
        self.log_text.config(state=tk.NORMAL)
        timestamp = __import__('datetime').datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _get_save_path(self, default_name: str, file_type: str = "Excel") -> str:
        """获取保存路径"""
        file_path = filedialog.asksaveasfilename(
            title=f"保存{file_type}文件",
            defaultextension=".xlsx",
            filetypes=[("Excel文件", "*.xlsx"), ("所有文件", "*.*")],
            initialfile=default_name
        )
        return file_path

    def _get_open_path(self, file_type: str = "Excel") -> str:
        """获取打开文件路径"""
        file_path = filedialog.askopenfilename(
            title=f"选择{file_type}文件",
            filetypes=[("Excel文件", "*.xlsx"), ("所有文件", "*.*")],
        )
        return file_path

    def _export_orders(self):
        """导出订单"""
        default_name = f"订单列表_{__import__('datetime').datetime.now().strftime('%Y%m%d')}.xlsx"
        file_path = self._get_save_path(default_name)
        if not file_path:
            return
        
        try:
            ExcelExporter.export_orders(file_path)
            self._log(f"✅ 订单导出成功: {file_path}")
            messagebox.showinfo("成功", f"订单已导出到:\n{file_path}")
        except Exception as e:
            self._log(f"❌ 导出失败: {str(e)}")
            alert(f"导出失败: {e}", "错误")

    def _export_inventory(self):
        """导出库存"""
        default_name = f"库存数据_{__import__('datetime').datetime.now().strftime('%Y%m%d')}.xlsx"
        file_path = self._get_save_path(default_name)
        if not file_path:
            return
        
        try:
            ExcelExporter.export_inventory(file_path)
            self._log(f"✅ 库存导出成功: {file_path}")
            messagebox.showinfo("成功", f"库存已导出到:\n{file_path}")
        except Exception as e:
            self._log(f"❌ 导出失败: {str(e)}")
            alert(f"导出失败: {e}", "错误")

    def _export_bom(self):
        """导出BOM"""
        default_name = f"BOM清单_{__import__('datetime').datetime.now().strftime('%Y%m%d')}.xlsx"
        file_path = self._get_save_path(default_name)
        if not file_path:
            return
        
        try:
            ExcelExporter.export_bom(file_path)
            self._log(f"✅ BOM导出成功: {file_path}")
            messagebox.showinfo("成功", f"BOM已导出到:\n{file_path}")
        except Exception as e:
            self._log(f"❌ 导出失败: {str(e)}")
            alert(f"导出失败: {e}", "错误")

    def _export_material_prep(self):
        """导出备料清单"""
        default_name = f"备料清单_{__import__('datetime').datetime.now().strftime('%Y%m%d')}.xlsx"
        file_path = self._get_save_path(default_name)
        if not file_path:
            return
        
        try:
            ExcelExporter.export_material_prep(file_path)
            self._log(f"✅ 备料清单导出成功: {file_path}")
            messagebox.showinfo("成功", f"备料清单已导出到:\n{file_path}")
        except Exception as e:
            self._log(f"❌ 导出失败: {str(e)}")
            alert(f"导出失败: {e}", "错误")

    def _import_orders(self):
        """导入订单"""
        file_path = self._get_open_path("订单Excel")
        if not file_path:
            return
        
        try:
            self._log(f"正在导入订单...")
            result = ExcelImporter.import_orders(file_path)
            msg = f"成功导入 {result['imported']} 条订单"
            if result['errors']:
                msg += f"\n有 {len(result['errors'])} 条错误"
                self._log(f"⚠️ {msg}")
                for err in result['errors'][:5]:
                    self._log(f"   {err}")
            else:
                self._log(f"✅ {msg}")
            messagebox.showinfo("导入完成", msg)
            
            if self.refresh_callback:
                self.refresh_callback()
        except Exception as e:
            self._log(f"❌ 导入失败: {str(e)}")
            alert(f"导入失败: {e}", "错误")

    def _import_inventory(self):
        """导入库存"""
        file_path = self._get_open_path("库存Excel")
        if not file_path:
            return
        
        try:
            self._log(f"正在导入库存...")
            result = ExcelImporter.import_inventory(file_path)
            msg = f"成功导入 {result['imported']} 条库存"
            if result['errors']:
                msg += f"\n有 {len(result['errors'])} 条错误"
                self._log(f"⚠️ {msg}")
                for err in result['errors'][:5]:
                    self._log(f"   {err}")
            else:
                self._log(f"✅ {msg}")
            messagebox.showinfo("导入完成", msg)
            
            if self.refresh_callback:
                self.refresh_callback()
        except Exception as e:
            self._log(f"❌ 导入失败: {str(e)}")
            alert(f"导入失败: {e}", "错误")

    def _import_bom(self):
        """导入BOM"""
        file_path = self._get_open_path("BOM Excel")
        if not file_path:
            return
        
        try:
            self._log(f"正在导入BOM...")
            result = ExcelImporter.import_bom(file_path)
            msg = f"成功导入 {result['imported']} 条BOM"
            if result['errors']:
                msg += f"\n有 {len(result['errors'])} 条错误"
                self._log(f"⚠️ {msg}")
                for err in result['errors'][:5]:
                    self._log(f"   {err}")
            else:
                self._log(f"✅ {msg}")
            messagebox.showinfo("导入完成", msg)
            
            if self.refresh_callback:
                self.refresh_callback()
        except Exception as e:
            self._log(f"❌ 导入失败: {str(e)}")
            alert(f"导入失败: {e}", "错误")

    def _download_template(self, template_type: str):
        """下载模板"""
        try:
            file_path = create_template(template_type)
            self._log(f"✅ 模板已生成: {file_path}")
            messagebox.showinfo("成功", f"模板已生成:\n{file_path}\n\n请使用Excel打开并填写数据")
        except Exception as e:
            self._log(f"❌ 模板生成失败: {str(e)}")
            alert(f"模板生成失败: {e}", "错误")
