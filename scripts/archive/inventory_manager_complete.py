# -*- coding: utf-8 -*-
"""
库存管理系统 - 完整GUI界面 (完善版)
支持MySQL数据库 + 完善打印功能 + 跟单系统对接
架构参考: D:\\JGB\\五金行业库存管理系统\\五金行业库存管理系统\\inventory_app.py
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
import sys
from datetime import datetime, date
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from inventory_db_complete import inv_db, InventoryDB
    from inventory_print import print_outbound, print_inbound, print_inventory_report
    from inventory_backup import backup_database, restore_database, export_to_excel, get_backup_files, get_backup_dir
except ImportError:
    from inventory_mysql_db import inv_db, InventoryDB
    from inventory_print import print_outbound, print_inbound, print_inventory_report


THEME = {
    "bg_dark": "#1A2742",
    "bg_mid": "#243454",
    "bg_light": "#2E4070",
    "accent": "#3B9EFF",
    "accent2": "#00D4AA",
    "warn": "#FF8C42",
    "danger": "#FF4B5C",
    "success": "#27AE60",
    "text_white": "#FFFFFF",
    "text_light": "#B0C4DE",
    "text_dark": "#1A2742",
    "row_alt": "#EBF5FB",
    "row_norm": "#FFFFFF",
    "border": "#AED6F1",
    "input_bg": "#F4F9FF",
    "header_bg": "#1F4E79",
}


class InventoryGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("宁津晨圣输送机械有限公司库存管理系统 V3.0 (MySQL版)")
        self.geometry("1320x840")
        self.minsize(1100, 680)
        self.configure(bg=THEME["bg_dark"])
        self.current_view = None
        self.running = True

        self.inventory_config = self._load_config()
        self.server_config = self.inventory_config.get("server", {})
        self.server_mode = tk.BooleanVar(value=False)
        self.server_api = None

        self._build_ui()
        self.center_window()
        self.load_dashboard()
        self.protocol("WM_DELETE_WINDOW", self._safe_quit)

        self.bind("<F5>", lambda e: self._refresh_current_view())
        self.bind("<Control-f>", lambda e: self._focus_search())

    def _load_config(self):
        """从配置文件加载所有配置参数"""
        import json
        import sys
        
        # PyInstaller打包时，__file__指向临时目录，需要用sys.executable获取EXE路径
        if hasattr(sys, '_MEIPASS'):
            app_dir = os.path.dirname(sys.executable)
        else:
            app_dir = os.path.dirname(__file__)
        
        config_file = os.path.join(app_dir, "data", "inventory_config.json")
        
        # 默认配置 - 所有参数都在这里定义，便于统一管理
        default_config = {
            "server": {
                "url": "http://localhost:8080",
                "api_key": os.getenv('INVENTORY_API_KEY', '')
            },
            "database": {
                "host": "localhost",
                "port": 3306,
                "user": "root",
                "password": os.getenv('MYSQL_PASSWORD', ''),
                "database": "inventory_db",
                "charset": "utf8mb4",
                "connect_timeout": 10,
                "read_timeout": 30,
                "write_timeout": 30
            },
            "container": {
                "url": "http://localhost:5003"
            },
            "app": {
                "title": "宁津晨圣输送机械有限公司库存管理系统 V3.0",
                "theme": "default"
            }
        }
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # 深度合并配置
                    return self._deep_merge(default_config, loaded)
            except Exception as e:
                # 配置文件读取失败，使用默认配置
                import traceback
                with open('app_config_error.log', 'a', encoding='utf-8') as f:
                    f.write(f"{datetime.now()} - 配置文件读取失败: {str(e)}\n{traceback.format_exc()}\n\n")
        
        return default_config
    
    def _deep_merge(self, default, loaded):
        """深度合并配置字典"""
        result = default.copy()
        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _load_server_config(self):
        return self.inventory_config.get("server", {})

    def _init_server_api(self):
        if not self.server_config.get("server_url"):
            return None
        try:
            import requests
            class ServerAPI:
                def __init__(self, config):
                    self.config = config
                    self.session = requests.Session()
                    self.session.headers.update({
                        "X-API-Key": config.get("api_key", ""),
                        "Content-Type": "application/json"
                    })

                def _request(self, method, endpoint, data=None, params=None):
                    url = f"{self.inventory_config.get('server_url', '').rstrip('/')}/{endpoint.lstrip('/')}"
                    try:
                        if method.upper() == "GET":
                            resp = self.session.get(url, params=params, timeout=30)
                        elif method.upper() == "POST":
                            resp = self.session.post(url, json=data, params=params, timeout=30)
                        else:
                            return {"error": "invalid_method"}
                        if resp.status_code == 200:
                            return resp.json()
                        return {"error": f"http_{resp.status_code}"}
                    except Exception as e:
                        return {"error": str(e)}

                def get_all_inventory(self, warehouse_id=None):
                    params = {}
                    if warehouse_id:
                        params["warehouse_id"] = warehouse_id
                    return self._request("GET", "/api/inventory/list", params=params)

                def get_statistics(self):
                    return self._request("GET", "/api/inventory/statistics")

                def get_low_stock_alerts(self):
                    return self._request("GET", "/api/inventory/low-stock")

                def get_products(self):
                    return self._request("GET", "/api/products")

                def get_warehouses(self):
                    return self._request("GET", "/api/warehouses")

                def get_suppliers(self):
                    return self._request("GET", "/api/suppliers")

                def get_categories(self):
                    return self._request("GET", "/api/categories")

                def get_transactions(self, trans_type=None, limit=100):
                    params = {"limit": limit}
                    if trans_type:
                        params["trans_type"] = trans_type
                    return self._request("GET", "/api/inventory/transactions", params=params)

                def add_inbound(self, data):
                    return self._request("POST", "/api/inventory/inbound", data=data)

                def add_outbound(self, data):
                    return self._request("POST", "/api/inventory/outbound", data=data)

                def check_connection(self):
                    return self._request("GET", "/api/health")

            return ServerAPI(self.server_config)
        except Exception as e:
            print(f"Server API init error: {e}")
            return None

    def center_window(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def _build_ui(self):
        self._create_menu()

        top = tk.Frame(self, bg=THEME["bg_dark"], height=64)
        top.pack(fill="x", side="top")
        top.pack_propagate(False)

        logo_lbl = tk.Label(top, text="  宁津晨圣输送机械有限公司库存管理系统  V3.0",
                            font=("微软雅黑", 18, "bold"),
                            fg=THEME["text_white"], bg=THEME["bg_dark"])
        logo_lbl.pack(side="left", padx=24, pady=12)

        date_lbl = tk.Label(top, text=f"当前日期：{date.today().strftime('%Y年%m月%d日')}",
                            font=("微软雅黑", 10),
                            fg=THEME["text_light"], bg=THEME["bg_dark"])
        date_lbl.pack(side="right", padx=24)

        sep = tk.Frame(self, bg=THEME["accent"], height=2)
        sep.pack(fill="x")

        body = tk.Frame(self, bg=THEME["bg_dark"])
        body.pack(fill="both", expand=True)

        nav = tk.Frame(body, bg=THEME["bg_mid"], width=180)
        nav.pack(side="left", fill="y")
        nav.pack_propagate(False)

        self.content = tk.Frame(body, bg="#F0F4F8")
        self.content.pack(side="left", fill="both", expand=True)

        self._build_nav(nav)

    def _create_menu(self):
        menubar = tk.Menu(self, bg=THEME["bg_mid"], fg=THEME["text_white"])
        self.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="刷新当前数据", command=self._refresh_current_view)
        file_menu.add_separator()
        file_menu.add_command(label="退出系统", command=self._safe_quit)

        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="工具", menu=tools_menu)
        tools_menu.add_command(label="打开Excel文件", command=self._open_excel)
        tools_menu.add_command(label="数据初始化", command=self._init_database)
        tools_menu.add_command(label="重建数据", command=self._rebuild_data)
        tools_menu.add_separator()
        tools_menu.add_command(label="出入库统计", command=self._open_io_stats)
        tools_menu.add_separator()
        tools_menu.add_command(label="数据备份", command=self.load_backup)
        tools_menu.add_command(label="库存数据导出", command=self._export_data)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于系统", command=self._about)

    def _build_nav(self, nav):
        tk.Label(nav, text="功能菜单", font=("微软雅黑", 11, "bold"),
                 fg=THEME["accent"], bg=THEME["bg_mid"]).pack(pady=(20, 8))

        nav_items = [
            ("首页概览", self.load_dashboard),
            ("库存台账", self.load_inventory),
            ("入库管理", self.load_inbound),
            ("出库管理", self.load_outbound),
            ("预警分析", self.load_alerts),
            ("商品管理", self.load_products),
            ("供应商管理", self.load_suppliers),
            ("产品分类", self.load_categories),
            ("基础数据", self.load_basics),
            ("数据备份", self.load_backup),
            ("打印管理", self.load_print),
            ("系统设置", self.load_settings),
        ]

        self.nav_btns = []
        for label, cmd in nav_items:
            btn = tk.Button(nav, text=f"  {label}",
                            font=("微软雅黑", 11), fg=THEME["text_light"],
                            bg=THEME["bg_mid"], relief="flat",
                            anchor="w", padx=12, pady=8, cursor="hand2",
                            activebackground=THEME["bg_light"],
                            activeforeground=THEME["text_white"],
                            command=lambda c=cmd: self._nav_click(c))
            btn.pack(fill="x", pady=1)
            self.nav_btns.append(btn)

        tk.Frame(nav, bg=THEME["bg_mid"]).pack(fill="y", expand=True)
        tk.Label(nav, text="V3.0 © 2026", font=("微软雅黑", 8),
                 fg=THEME["text_light"], bg=THEME["bg_mid"]).pack(pady=12)

    def _nav_click(self, cmd):
        for b in self.nav_btns:
            b.configure(bg=THEME["bg_mid"], fg=THEME["text_light"])
        self.current_view = cmd
        cmd()

    def _focus_search(self):
        if hasattr(self, '_search_var'):
            try:
                self._search_var.get().focus_set()
                self._search_var.get().select_range(0, "end")
            except:
                pass

    def _clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()

    def _safe_quit(self):
        self.running = False
        self.destroy()

    def _refresh_current_view(self):
        if hasattr(self, 'current_view') and self.current_view:
            self.current_view()

    def _init_database(self):
        if messagebox.askyesno("数据初始化", "是否初始化数据库？这将创建必要的表和示例数据。"):
            try:
                db = InventoryDB()
                db.init_database()
                db.insert_initial_data()
                messagebox.showinfo("成功", "数据库初始化完成！")
                self._refresh_current_view()
            except Exception as e:
                messagebox.showerror("错误", f"数据库初始化失败：\n{str(e)}")

    def _export_data(self):
        messagebox.showinfo("提示", "数据导出功能开发中...")

    def _open_io_stats(self):
        """打开出入库统计窗口"""
        win = tk.Toplevel(self)
        win.title("出入库统计")
        win.geometry("900x600")
        win.configure(bg=THEME["bg_dark"])
        win.transient(self)
        win.grab_set()

        tk.Label(win, text="出入库统计", font=("微软雅黑", 16, "bold"),
                bg=THEME["bg_dark"], fg=THEME["text_white"]).pack(pady=15)

        control_frame = tk.Frame(win, bg=THEME["bg_dark"])
        control_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(control_frame, text="日期范围:", font=("微软雅黑", 11),
                bg=THEME["bg_dark"], fg=THEME["text_white"]).pack(side="left", padx=5)

        self._stats_start_var = tk.StringVar(value=date.today().strftime("%Y-%m-01"))
        tk.Entry(control_frame, textvariable=self._stats_start_var, font=("微软雅黑", 11),
                width=12).pack(side="left", padx=5)

        tk.Label(control_frame, text="至", font=("微软雅黑", 11),
                bg=THEME["bg_dark"], fg=THEME["text_white"]).pack(side="left", padx=5)

        self._stats_end_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        tk.Entry(control_frame, textvariable=self._stats_end_var, font=("微软雅黑", 11),
                width=12).pack(side="left", padx=5)

        tk.Button(control_frame, text="查询", font=("微软雅黑", 11),
                 bg=THEME["accent"], fg="white", relief="flat",
                 padx=15, pady=4, cursor="hand2",
                 command=lambda: self._refresh_stats_tree(stats_tree)).pack(side="left", padx=20)

        columns = ["日期", "单号", "类型", "商品名称", "规格", "数量", "单价", "金额", "经手人", "仓库"]
        col_widths = [95, 120, 60, 150, 80, 60, 70, 85, 75, 70]

        stats_tree = self._build_stats_table(win, columns, col_widths, height=18)
        self._stats_tree = stats_tree
        self._refresh_stats_tree(stats_tree)

    def _build_stats_table(self, parent, columns, col_widths, height=14):
        frame = tk.Frame(parent, bg="#F0F4F8")
        frame.pack(fill="both", expand=True, padx=20, pady=10)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Custom.Treeview", background="white", foreground=THEME["text_dark"],
                        fieldbackground="white", font=("微软雅黑", 10), rowheight=28)
        style.configure("Custom.Treeview.Heading", background=THEME["header_bg"],
                        foreground="white", font=("微软雅黑", 10, "bold"), relief="flat")
        style.map("Custom.Treeview", background=[("selected", THEME["accent"])],
                  foreground=[("selected", "white")])

        tree = ttk.Treeview(frame, columns=tuple(columns), show="headings",
                           height=height, style="Custom.Treeview")

        for col, w in zip(columns, col_widths):
            tree.heading(col, text=col)
            tree.column(col, width=w, anchor="center", minwidth=60)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        tree.pack(side="left", fill="both", expand=True)

        return tree

    def _refresh_stats_tree(self, tree):
        for item in tree.get_children():
            tree.delete(item)

        try:
            start_date = self._stats_start_var.get().strip()
            end_date = self._stats_end_var.get().strip()

            trans = inv_db.get_inventory_transactions(limit=5000)
        except:
            trans = []

        filtered = []
        for t in trans:
            trans_date = str(t.get('trans_date', ''))[:10]
            if start_date and trans_date < start_date:
                continue
            if end_date and trans_date > end_date:
                continue
            filtered.append(t)

        total_in_qty = 0
        total_out_qty = 0
        total_in_amt = 0.0
        total_out_amt = 0.0

        for i, t in enumerate(filtered, 1):
            qty = float(t.get('qty', 0) or 0)
            price = float(t.get('unit_price', 0) or 0)
            amt = qty * price
            trans_type = t.get('trans_type', '')

            if trans_type == 'inbound':
                total_in_qty += qty
                total_in_amt += amt
            else:
                total_out_qty += qty
                total_out_amt += amt

            trans_type_cn = "入库" if trans_type == 'inbound' else "出库"

            tree.insert("", "end", values=[
                str(t.get('trans_date', ''))[:10],
                t.get('trans_no', ''),
                trans_type_cn,
                t.get('product_name', ''),
                t.get('spec', ''),
                f"{qty:.0f}",
                f"¥{price:.2f}",
                f"¥{amt:.2f}",
                t.get('operator', ''),
                t.get('warehouse_name', '')
            ], tags=("inbound" if trans_type == 'inbound' else "outbound",))

        tree.tag_configure("inbound", background="#EAFAF1")
        tree.tag_configure("outbound", background="#FEF9E7")

        summary_frame = tk.Frame(tree.master, bg="#F0F4F8")
        summary_frame.pack(fill="x", padx=20, pady=5)

        summary_text = f"入库合计: 数量 {total_in_qty:,.0f}  金额 ¥{total_in_amt:,.2f}     出库合计: 数量 {total_out_qty:,.0f}  金额 ¥{total_out_amt:,.2f}"
        tk.Label(summary_frame, text=summary_text, font=("微软雅黑", 11, "bold"),
                bg="#F0F4F8", fg=THEME["bg_dark"]).pack()

    def _about(self):
        messagebox.showinfo("关于",
            "宁津晨圣输送机械有限公司\n库存管理系统 V3.0 (MySQL版)\n\n功能完善的库存管理系统，包含:\n- 库存查询与管理\n- 入库/出库管理\n- 预警分析\n- 打印功能\n- 跟单系统对接")

    def _get_stagnant_items(self):
        """获取超过90天未变动的滞留商品"""
        from datetime import timedelta
        cutoff = date.today() - timedelta(days=90)
        try:
            all_inv = inv_db.get_all_inventory()
            all_trans = inv_db.get_inventory_transactions(limit=5000)
        except:
            return []

        recent_active = set()
        for t in all_trans:
            trans_date = t.get('trans_date', '')
            if trans_date:
                if isinstance(trans_date, str):
                    try:
                        dt = datetime.strptime(trans_date[:10], "%Y-%m-%d").date()
                    except:
                        continue
                else:
                    dt = trans_date
                if dt > cutoff:
                    product_name = t.get('product_name', '')
                    if product_name:
                        recent_active.add(product_name)

        stagnant = []
        alerted_codes = set()
        for inv in all_inv:
            current = float(inv.get('current_qty', 0) or 0)
            if current <= 0:
                continue
            product_name = inv.get('product_name', '')
            if product_name not in recent_active:
                stagnant.append({
                    'sku': inv.get('sku', ''),
                    'product_name': product_name,
                    'current_qty': current,
                    'safety_stock': '-',
                    'warehouse_name': inv.get('warehouse_name', ''),
                    'status': '滞留'
                })
                alerted_codes.add(inv.get('sku', ''))
        return stagnant

    def _get_all_alert_items(self):
        """获取所有预警商品（包括低库存、缺货、超储和滞留商品）"""
        items = []
        alerted_codes = set()

        try:
            if self.server_mode.get() and self.server_api:
                alerts = self.server_api.get_low_stock_alerts() or []
            else:
                alerts = inv_db.get_low_stock_alerts() or []
        except:
            alerts = []

        for a in alerts:
            sku = a.get('sku', '')
            current = float(a.get('current_qty', 0) or 0)
            safety = float(a.get('safety_stock', 0) or 0)
            max_stock = float(a.get('max_stock', 0) or 0)

            if current <= 0:
                status = "缺货"
            elif current < safety:
                status = "预警"
            elif current > max_stock:
                status = "超储"
            else:
                status = "正常"

            items.append({
                'sku': sku,
                'product_name': a.get('product_name', ''),
                'current_qty': current,
                'safety_stock': safety,
                'warehouse_name': a.get('warehouse_name', ''),
                'status': status
            })
            alerted_codes.add(sku)

        stagnant = self._get_stagnant_items()
        for s in stagnant:
            if s.get('sku', '') not in alerted_codes:
                items.append(s)

        return items

    def _open_excel(self):
        """打开Excel数据文件"""
        excel_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "宁津晨圣输送机械有限公司库存管理系统.xlsx")
        if os.path.exists(excel_file):
            try:
                os.startfile(excel_file)
            except Exception as e:
                messagebox.showerror("错误", f"无法打开Excel文件：\n{str(e)}")
        else:
            messagebox.showinfo("提示", f"Excel数据文件不存在：\n{excel_file}\n\n请先进行数据初始化！")

    def _rebuild_data(self):
        """重建数据 - 重新初始化数据库"""
        if messagebox.askyesno("重建数据", "确定要重建数据吗？\n\n这将清空所有库存数据并重新初始化！\n建议先备份重要数据。"):
            try:
                db = InventoryDB()
                db.init_database()
                db.insert_initial_data()
                messagebox.showinfo("成功", "数据重建完成！")
                self._refresh_current_view()
            except Exception as e:
                messagebox.showerror("错误", f"数据重建失败：\n{str(e)}")

    def _create_stat_card(self, parent, title, value, color):
        card = tk.Frame(parent, bg="white", relief="flat",
                        highlightbackground=color, highlightthickness=2)
        card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=8)
        tk.Label(card, text=title, font=("微软雅黑", 10),
                 fg="#6C757D", bg="white").pack(anchor="w", padx=16, pady=(12, 0))
        tk.Label(card, text=str(value), font=("微软雅黑", 24, "bold"),
                 fg=color, bg="white").pack(anchor="w", padx=16, pady=4)
        return card

    def _section_title(self, parent, title, sub=""):
        f = tk.Frame(parent, bg="#F0F4F8")
        f.pack(fill="x", padx=20, pady=(16, 4))
        tk.Label(f, text=title, font=("微软雅黑", 16, "bold"),
                 fg=THEME["bg_dark"], bg="#F0F4F8").pack(side="left")
        if sub:
            tk.Label(f, text=f"  {sub}", font=("微软雅黑", 10),
                     fg="#6C757D", bg="#F0F4F8").pack(side="left", pady=4)

    def _build_table(self, parent, columns, col_widths, data_func, height=14):
        frame = tk.Frame(parent, bg="#F0F4F8")
        frame.pack(fill="both", expand=True, padx=20, pady=4)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Custom.Treeview", background="white", foreground=THEME["text_dark"],
                        fieldbackground="white", font=("微软雅黑", 10), rowheight=28)
        style.configure("Custom.Treeview.Heading", background=THEME["header_bg"],
                        foreground="white", font=("微软雅黑", 10, "bold"), relief="flat")
        style.map("Custom.Treeview", background=[("selected", THEME["accent"])],
                  foreground=[("selected", "white")])

        tree = ttk.Treeview(frame, columns=tuple(columns), show="headings",
                           height=height, style="Custom.Treeview")

        for col, w in zip(columns, col_widths):
            tree.heading(col, text=col)
            tree.column(col, width=w, anchor="center", minwidth=60)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        tree.pack(side="left", fill="both", expand=True)

        data = data_func()
        for i, row in enumerate(data):
            tag = "alt" if i % 2 else "norm"
            tree.insert("", "end", values=[str(v) if v is not None else "" for v in row], tags=(tag,))

        tree.tag_configure("alt", background=THEME["row_alt"])
        tree.tag_configure("norm", background="white")

        return tree

    def _apply_status_colors(self, tree):
        for item in tree.get_children():
            vals = tree.item(item, "values")
            if vals and len(vals) > 0:
                last = vals[-1]
                if last in ("缺货", "预警", "超储", "正常"):
                    color_map = {
                        "缺货": ("#FDECEA", "#FF4B5C"),
                        "预警": ("#FFF3E0", "#FF8C42"),
                        "超储": ("#EAF4FB", "#2980B9"),
                        "正常": ("#EAFAF1", "#27AE60"),
                    }
                    bg, fg = color_map.get(last, ("white", "black"))
                    tree.item(item, tags=(last,))
                    tree.tag_configure(last, background=bg, foreground=fg)

    # ══════════════════════════════════════════
    # 首页概览
    # ══════════════════════════════════════════
    def load_dashboard(self):
        self.current_view = self.load_dashboard
        self._clear_content()
        self._section_title(self.content, "首页概览", "库存实时数据汇总")

        mode_txt = " [服务器模式]" if self.server_mode.get() else " [本地模式]"
        if hasattr(self, '_server_status_label') and self._server_status_label:
            self._server_status_label.configure(text=f"当前模式:{mode_txt}", fg=THEME["accent"])

        try:
            if self.server_mode.get() and self.server_api:
                stats = self.server_api.get_statistics() or {}
                alerts = self.server_api.get_low_stock_alerts() or []
            else:
                stats = inv_db.get_statistics()
                alerts = inv_db.get_low_stock_alerts()
        except Exception as e:
            # 添加调试日志
            import traceback
            error_msg = f"数据加载失败: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            # 写入日志文件
            try:
                with open('inventory_error.log', 'a', encoding='utf-8') as f:
                    f.write(f"{datetime.now()} - {error_msg}\n\n")
            except:
                pass
            stats = {"product_count": 0, "total_qty": 0, "total_value": 0, "low_stock_count": 0}
            alerts = []

        cards_frame = tk.Frame(self.content, bg="#F0F4F8")
        cards_frame.pack(fill="x", padx=20, pady=8)

        cards = [
            ("商品种类", stats.get('product_count', 0), THEME["accent"]),
            ("库存总量", f"{float(stats.get('total_qty', 0) or 0):,.0f}", THEME["accent2"]),
            ("库存总值", f"¥{float(stats.get('total_value', 0) or 0):,.2f}", THEME["success"]),
            ("低库存预警", stats.get('low_stock_count', 0), THEME["warn"]),
            ("缺货商品", stats.get('out_stock_count', 0), THEME["danger"]),
        ]

        stagnant = self._get_stagnant_items()
        stagnant_count = len(stagnant) if stagnant else 0
        cards.append(("滞留商品", stagnant_count, THEME["danger"]))

        for i, (title, val, color) in enumerate(cards):
            self._create_stat_card(cards_frame, title, val, color).pack(side="left", fill="both", expand=True, padx=4)

        self._section_title(self.content, "预警商品清单", "需关注的库存异常与滞留商品")
        all_alerts = self._get_all_alert_items()
        alert_tree = self._build_table(
            self.content,
            ["商品编码", "商品名称", "当前库存", "安全库存", "仓库", "状态"],
            [120, 250, 100, 100, 100, 80],
            lambda: [[a.get('sku', ''), a.get('product_name', ''),
                     f"{float(a.get('current_qty', 0) or 0):.0f}",
                     str(a.get('safety_stock', '-')),
                     a.get('warehouse_name', ''), a.get('status', '预警')] for a in all_alerts[:50]],
            height=12
        )
        self._apply_status_colors(alert_tree)

        self._section_title(self.content, "快捷操作")
        qf = tk.Frame(self.content, bg="#F0F4F8")
        qf.pack(fill="x", padx=20, pady=4)
        btns = [
            ("新增入库", self.load_inbound, THEME["success"]),
            ("新增出库", self.load_outbound, THEME["warn"]),
            ("查看库存", self.load_inventory, THEME["accent"]),
            ("预警分析", self.load_alerts, THEME["danger"]),
            ("新增商品", self.load_products, "#7D3C98"),
            ("打开Excel", self._open_excel, THEME["bg_dark"]),
            ("重建数据", self._rebuild_data, "#C0392B"),
            ("刷新数据", self._refresh_current_view, THEME["accent2"]),
        ]
        for lbl, cmd, color in btns:
            tk.Button(qf, text=lbl, font=("微软雅黑", 11, "bold"),
                      bg=color, fg="white", relief="flat",
                      padx=20, pady=8, cursor="hand2", command=cmd).pack(side="left", padx=6)

    # ══════════════════════════════════════════
    # 库存台账
    # ══════════════════════════════════════════
    def load_inventory(self):
        self.current_view = self.load_inventory
        self._clear_content()
        self._section_title(self.content, "库存台账", "全部商品库存实时状态")

        sf = tk.Frame(self.content, bg="#F0F4F8")
        sf.pack(fill="x", padx=20, pady=4)

        tk.Label(sf, text="搜索:", font=("微软雅黑", 10), bg="#F0F4F8").pack(side="left")
        self.inv_search_var = tk.StringVar()
        search_entry = tk.Entry(sf, textvariable=self.inv_search_var, font=("微软雅黑", 11),
                               width=20, bg="white", relief="solid")
        search_entry.pack(side="left", padx=8)

        tk.Button(sf, text="搜索", font=("微软雅黑", 10), bg=THEME["accent"], fg="white",
                  relief="flat", padx=12, pady=4, cursor="hand2",
                  command=self._search_inventory).pack(side="left", padx=4)
        tk.Button(sf, text="全部显示", font=("微软雅黑", 10), bg="#6C757D", fg="white",
                  relief="flat", padx=12, pady=4, cursor="hand2",
                  command=self.load_inventory).pack(side="left", padx=4)
        tk.Button(sf, text="刷新", font=("微软雅黑", 10), bg=THEME["accent2"], fg="white",
                  relief="flat", padx=12, pady=4, cursor="hand2",
                  command=self._refresh_current_view).pack(side="left", padx=4)

        self.inv_filter_var = tk.StringVar(value="全部")
        for txt, val in [("全部", "全部"), ("正常", "正常"), ("预警", "预警"), ("缺货", "缺货"), ("超储", "超储")]:
            tk.Radiobutton(sf, text=txt, variable=self.inv_filter_var, value=val,
                          font=("微软雅黑", 10), bg="#F0F4F8", selectcolor="#D6EAF8",
                          command=self._filter_inventory).pack(side="left", padx=6)

        self.inv_tree = self._build_table(
            self.content,
            ["#", "SKU编码", "商品名称", "规格型号", "单位", "当前库存", "安全库存", "最高库存", "单价", "状态", "仓库"],
            [40, 100, 200, 100, 50, 80, 80, 80, 80, 70, 80],
            self._get_inventory_data, height=16
        )
        self._apply_status_colors(self.inv_tree)

    def _get_inventory_data(self):
        try:
            if self.server_mode.get() and self.server_api:
                data = self.server_api.get_all_inventory()
                all_inv = data.get("inventory", []) if isinstance(data, dict) else []
            else:
                all_inv = inv_db.get_all_inventory()
        except:
            return []
        result = []
        for i, inv in enumerate(all_inv, 1):
            current = float(inv.get('current_qty', 0) or 0)
            safety = float(inv.get('safety_stock', 0) or 0)
            max_stock = float(inv.get('max_stock', 0) or 0)
            price = float(inv.get('unit_price', 0) or 0)
            if current <= 0:
                status = "缺货"
            elif current < safety:
                status = "预警"
            elif current > max_stock:
                status = "超储"
            else:
                status = "正常"

            filter_status = self.inv_filter_var.get() if hasattr(self, 'inv_filter_var') else "全部"
            if filter_status != "全部" and status != filter_status:
                continue

            search = self.inv_search_var.get().strip().lower() if hasattr(self, 'inv_search_var') else ""
            if search:
                match = any(search in str(v).lower() for v in [inv.get('sku', ''), inv.get('product_name', ''), inv.get('spec', '')] if v)
                if not match:
                    continue

            result.append([i, inv.get('sku', ''), inv.get('product_name', ''), inv.get('spec', ''),
                          inv.get('unit', ''), f"{current:.0f}", f"{safety:.0f}", f"{max_stock:.0f}",
                          f"¥{price:.2f}", status, inv.get('warehouse_name', '')])
        return result

    def _search_inventory(self):
        if hasattr(self, 'inv_tree'):
            self._reload_inv_tree()

    def _filter_inventory(self):
        self._reload_inv_tree()

    def _reload_inv_tree(self):
        if not hasattr(self, 'inv_tree'):
            return
        for item in self.inv_tree.get_children():
            self.inv_tree.delete(item)
        data = self._get_inventory_data()
        for i, row in enumerate(data):
            tag = "alt" if i % 2 else "norm"
            self.inv_tree.insert("", "end", values=row, tags=(tag,))
        self._apply_status_colors(self.inv_tree)

    # ══════════════════════════════════════════
    # 入库管理
    # ══════════════════════════════════════════
    def load_inbound(self):
        self.current_view = self.load_inbound
        self._clear_content()
        self._section_title(self.content, "入库管理", "新增入库 / 查看入库记录")

        form_frame = tk.LabelFrame(self.content, text=" 新增进库单 ",
                                  font=("微软雅黑", 11, "bold"),
                                  bg="white", fg=THEME["bg_dark"], relief="groove", bd=2)
        form_frame.pack(fill="x", padx=20, pady=8, ipady=8)

        fields = [
            ("入库单号", f"RK-{date.today().year}{date.today().month:02d}-001", True),
            ("入库日期", date.today().strftime("%Y-%m-%d"), True),
            ("商品名称", "", True),
            ("规格型号", "", True),
            ("入库数量", "", True),
            ("单价(元)", "", True),
            ("供应商", "", False),
            ("经手人", "", True),
            ("存放仓库", "", True),
            ("备注", "", False),
        ]

        self.in_vars = {}
        warehouses = inv_db.get_warehouses()
        warehouse_names = [w['name'] for w in warehouses] if warehouses else ["1号仓"]
        products = inv_db.get_all_products()
        product_names = [p['name'] for p in products] if products else []
        suppliers = inv_db.get_suppliers()
        supplier_names = [s['name'] for s in suppliers] if suppliers else []

        for i, (label, default, required) in enumerate(fields):
            row_idx = i // 3
            col_idx = (i % 3) * 2
            star = " *" if required else "  "
            tk.Label(form_frame, text=f"{label}{star}:", font=("微软雅黑", 10),
                     bg="white", fg="#333").grid(row=row_idx, column=col_idx, padx=12, pady=6, sticky="e")

            var = tk.StringVar(value=default)

            if label == "商品名称":
                cb = ttk.Combobox(form_frame, textvariable=var, values=product_names,
                                  font=("微软雅黑", 11), width=18, state="normal")
                cb.grid(row=row_idx, column=col_idx+1, padx=4, pady=6, sticky="w")
                cb.bind("<<ComboboxSelected>>", self._on_inbound_product_selected)
                self._inbound_name_cb = cb
            elif label == "规格型号":
                cb = ttk.Combobox(form_frame, textvariable=var, values=[],
                                  font=("微软雅黑", 11), width=18, state="readonly")
                cb.grid(row=row_idx, column=col_idx+1, padx=4, pady=6, sticky="w")
                self._inbound_spec_cb = cb
            elif label == "存放仓库":
                cb = ttk.Combobox(form_frame, textvariable=var, values=warehouse_names,
                                  font=("微软雅黑", 11), width=18, state="readonly")
                if warehouse_names:
                    cb.current(0)
                cb.grid(row=row_idx, column=col_idx+1, padx=4, pady=6, sticky="w")
            elif label == "供应商":
                cb = ttk.Combobox(form_frame, textvariable=var, values=supplier_names,
                                  font=("微软雅黑", 11), width=18, state="normal")
                cb.grid(row=row_idx, column=col_idx+1, padx=4, pady=6, sticky="w")
            else:
                entry = tk.Entry(form_frame, textvariable=var, font=("微软雅黑", 11),
                                width=20, bg=THEME["input_bg"], relief="solid")
                entry.grid(row=row_idx, column=col_idx+1, padx=4, pady=6, sticky="w")
            self.in_vars[label] = var

        self._auto_in_no()

        btn_frame = tk.Frame(form_frame, bg="white")
        btn_frame.grid(row=4, column=0, columnspan=6, pady=8)
        self._inbound_submitting = False

        def _safe_submit():
            if self._inbound_submitting:
                return
            self._inbound_submitting = True
            try:
                self._submit_inbound()
            finally:
                self._inbound_submitting = False

        def _batch_inbound():
            self._open_batch_inbound_window()

        tk.Button(btn_frame, text="  确认入库  ", font=("微软雅黑", 12, "bold"),
                  bg=THEME["success"], fg="white", relief="flat",
                  padx=20, pady=6, cursor="hand2", command=_safe_submit).pack(side="left", padx=12)
        tk.Button(btn_frame, text="  批量入库  ", font=("微软雅黑", 12),
                  bg=THEME["accent"], fg="white", relief="flat",
                  padx=20, pady=6, cursor="hand2", command=_batch_inbound).pack(side="left", padx=12)
        tk.Button(btn_frame, text="  清空表单  ", font=("微软雅黑", 12),
                  bg="#6C757D", fg="white", relief="flat",
                  padx=20, pady=6, cursor="hand2", command=self.load_inbound).pack(side="left", padx=12)

        self._section_title(self.content, "入库历史记录")
        sf_in = tk.Frame(self.content, bg="#F0F4F8")
        sf_in.pack(fill="x", padx=20, pady=4)

        tk.Label(sf_in, text="搜索:", font=("微软雅黑", 10), bg="#F0F4F8").pack(side="left")
        self._in_history_search_var = tk.StringVar()
        tk.Entry(sf_in, textvariable=self._in_history_search_var, font=("微软雅黑", 11),
                width=20, relief="solid", bg="white").pack(side="left", padx=4)
        tk.Button(sf_in, text="筛选", font=("微软雅黑", 10), bg=THEME["accent"], fg="white",
                  relief="flat", padx=12, cursor="hand2",
                  command=lambda: self._filter_history(self._in_history_tree, self._in_history_search_var)).pack(side="left", padx=6)

        columns = ["#", "单号", "日期", "商品名称", "规格", "数量", "单价", "金额", "供应商", "经手人", "仓库"]
        col_widths = [40, 110, 95, 150, 90, 60, 70, 85, 100, 75, 70]
        self._in_history_tree = self._build_table(self.content, columns, col_widths,
                          lambda: self._get_inbound_history(), height=10)

    def _auto_in_no(self):
        today = date.today()
        month_prefix = f"RK-{today.year}{today.month:02d}-"
        try:
            trans = inv_db.get_inventory_transactions(trans_type='inbound', limit=1000)
            count = sum(1 for t in trans if t.get('trans_no', '').startswith(month_prefix))
        except:
            count = 0
        no = f"{month_prefix}{count+1:03d}"
        if '入库单号' in self.in_vars:
            self.in_vars['入库单号'].set(no)

    def _on_inbound_product_selected(self, event=None):
        name = self.in_vars.get("商品名称", tk.StringVar()).get().strip()
        if not name:
            return
        products = inv_db.get_all_products()
        specs = list({p['spec'] for p in products if p.get('name') == name and p.get('spec')})
        if hasattr(self, '_inbound_spec_cb') and self._inbound_spec_cb:
            self._inbound_spec_cb['values'] = specs
            if len(specs) == 1:
                self.in_vars['规格型号'].set(specs[0])

    def _submit_inbound(self):
        name = self.in_vars.get("商品名称", tk.StringVar()).get().strip()
        spec = self.in_vars.get("规格型号", tk.StringVar()).get().strip()
        qty_s = self.in_vars.get("入库数量", tk.StringVar()).get().strip()
        price_s = self.in_vars.get("单价(元)", tk.StringVar()).get().strip()
        handler = self.in_vars.get("经手人", tk.StringVar()).get().strip()
        warehouse = self.in_vars.get("存放仓库", tk.StringVar()).get().strip()

        if not name or not qty_s:
            messagebox.showwarning("提示", "带 * 的字段为必填项！")
            return
        try:
            qty = float(qty_s)
            price = float(price_s) if price_s else 0
        except:
            messagebox.showerror("错误", "数量和单价必须为数字！")
            return
        if qty <= 0:
            messagebox.showerror("错误", "入库数量必须大于0！")
            return

        products = inv_db.get_all_products()
        product = next((p for p in products if p.get('name') == name and (not spec or p.get('spec') == spec)), None)
        if not product:
            messagebox.showerror("错误", f"找不到商品「{name}」！")
            return

        warehouses = inv_db.get_warehouses()
        warehouse_obj = next((w for w in warehouses if w['name'] == warehouse), warehouses[0] if warehouses else None)
        warehouse_id = warehouse_obj['id'] if warehouse_obj else 1

        try:
            trans_no = inv_db.add_inbound(product['id'], warehouse_id, qty, self.in_vars.get("备注", tk.StringVar()).get().strip(), handler)
            if trans_no:
                messagebox.showinfo("成功", f"入库成功！单号：{trans_no}")
                
                # 询问是否打印
                if messagebox.askyesno("打印", "是否打印入库单？"):
                    self._print_single_inbound(name, spec, qty, supplier, handler, warehouse, trans_no)
                
                self.load_inbound()
            else:
                messagebox.showerror("错误", "入库失败！")
        except Exception as e:
            messagebox.showerror("错误", f"入库失败：{str(e)}")

    def _print_single_inbound(self, name, spec, qty, supplier, handler, warehouse, trans_no):
        """打印单笔入库单"""
        data = {
            "order_no": trans_no,
            "date": date.today().strftime("%Y-%m-%d"),
            "supplier": supplier,
            "handler": handler,
            "warehouse": warehouse,
            "items": [{
                "name": name,
                "spec": spec,
                "qty": qty
            }]
        }
        print_inbound(data)

    def _open_batch_inbound_window(self):
        """打开批量入库窗口"""
        self.batch_inbound_window = tk.Toplevel(self)
        self.batch_inbound_window.title("批量入库")
        self.batch_inbound_window.geometry("1000x650")
        self.batch_inbound_window.resizable(True, True)
        self.batch_inbound_window.transient(self)
        self.batch_inbound_window.grab_set()
        self.batch_inbound_window.configure(bg="#F0F4F8")

        top_frame = tk.Frame(self.batch_inbound_window, bg="#F0F4F8")
        top_frame.pack(fill="x", padx=10, pady=8)

        tk.Label(top_frame, text="批量入库", font=("微软雅黑", 14, "bold"), bg="#F0F4F8", fg="#1A2742").pack(side="left")

        tip_text = tk.Label(top_frame, text="💡 双击商品名称列选择商品 | 点击数量列可直接编辑 | 支持批量粘贴", 
                           font=("微软雅黑", 9), bg="#E8F4FD", fg="#3B9EFF", padx=10, pady=5)
        tip_text.pack(side="right")

        header_frame = tk.Frame(self.batch_inbound_window, bg="#F0F4F8")
        header_frame.pack(fill="x", padx=10, pady=5)

        fields_frame = tk.Frame(header_frame, bg="#F0F4F8")
        fields_frame.pack(fill="x", pady=5)

        tk.Label(fields_frame, text="入库单号:", bg="#F0F4F8", font=("微软雅黑", 10)).grid(row=0, column=0, padx=5, pady=3)
        self.batch_in_no_var = tk.StringVar(value=f"RK-{date.today().year}{date.today().month:02d}-001")
        tk.Entry(fields_frame, textvariable=self.batch_in_no_var, width=22, font=("微软雅黑", 10), relief="solid", bd=1).grid(row=0, column=1, padx=5, pady=3)

        tk.Label(fields_frame, text="入库日期:", bg="#F0F4F8", font=("微软雅黑", 10)).grid(row=0, column=2, padx=5, pady=3)
        self.batch_in_date_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        tk.Entry(fields_frame, textvariable=self.batch_in_date_var, width=15, font=("微软雅黑", 10), relief="solid", bd=1).grid(row=0, column=3, padx=5, pady=3)

        tk.Label(fields_frame, text="经手人:", bg="#F0F4F8", font=("微软雅黑", 10)).grid(row=0, column=4, padx=5, pady=3)
        self.batch_handler_var = tk.StringVar()
        tk.Entry(fields_frame, textvariable=self.batch_handler_var, width=15, font=("微软雅黑", 10), relief="solid", bd=1).grid(row=0, column=5, padx=5, pady=3)

        tk.Label(fields_frame, text="存放仓库:", bg="#F0F4F8", font=("微软雅黑", 10)).grid(row=0, column=6, padx=5, pady=3)
        warehouses = inv_db.get_warehouses()
        warehouse_names = [w['name'] for w in warehouses] if warehouses else ["1号仓"]
        self.batch_warehouse_var = tk.StringVar(value=warehouse_names[0] if warehouse_names else "")
        ttk.Combobox(fields_frame, textvariable=self.batch_warehouse_var, values=warehouse_names, width=14, font=("微软雅黑", 10)).grid(row=0, column=7, padx=5, pady=3)

        tk.Label(fields_frame, text="备注:", bg="#F0F4F8", font=("微软雅黑", 10)).grid(row=0, column=8, padx=5, pady=3)
        self.batch_remark_var = tk.StringVar()
        tk.Entry(fields_frame, textvariable=self.batch_remark_var, width=22, font=("微软雅黑", 10), relief="solid", bd=1).grid(row=0, column=9, padx=5, pady=3)

        table_frame = tk.Frame(self.batch_inbound_window)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        scroll_y = tk.Scrollbar(table_frame, orient="vertical")
        scroll_y.pack(side="right", fill="y")
        scroll_x = tk.Scrollbar(table_frame, orient="horizontal")
        scroll_x.pack(side="bottom", fill="x")

        columns = ("#", "商品名称", "规格型号", "当前库存", "入库数量", "单价(元)", "金额", "供应商")
        self.batch_in_tree = ttk.Treeview(table_frame, columns=columns, show="headings",
                                         yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set, height=12)
        scroll_y.config(command=self.batch_in_tree.yview)
        scroll_x.config(command=self.batch_in_tree.xview)

        col_widths = [40, 180, 130, 80, 80, 80, 90, 120]
        for i, (col, width) in enumerate(zip(columns, col_widths)):
            self.batch_in_tree.heading(col, text=col, anchor="center")
            self.batch_in_tree.column(col, width=width, anchor="center" if i > 0 else "center")

        self.batch_in_tree.tag_configure("norm", background="#FFFFFF")
        self.batch_in_tree.tag_configure("alt", background="#F5F8FA")
        self.batch_in_tree.pack(fill="both", expand=True)

        def _add_rows(count=5):
            products = inv_db.get_all_products()
            if not products:
                messagebox.showwarning("提示", "请先添加商品！")
                return
            for i in range(count):
                row_id = len(self.batch_in_tree.get_children()) + 1
                tag = "alt" if row_id % 2 else "norm"
                self.batch_in_tree.insert("", "end", values=(row_id, "", "", "", "", "", "", ""), tags=(tag,))

        def add_row():
            _add_rows(1)

        def delete_row():
            selected = self.batch_in_tree.selection()
            if selected:
                self.batch_in_tree.delete(selected)
                for i, item in enumerate(self.batch_in_tree.get_children(), 1):
                    values = list(self.batch_in_tree.item(item)['values'])
                    values[0] = i
                    tag = "alt" if i % 2 else "norm"
                    self.batch_in_tree.item(item, values=values, tags=(tag,))

        def clear_all():
            for item in self.batch_in_tree.get_children():
                self.batch_in_tree.delete(item)

        def _recalc_tree(item):
            values = list(self.batch_in_tree.item(item)['values'])
            try:
                qty = float(values[4]) if values[4] else 0
                price = float(values[5]) if values[5] else 0
                values[6] = f"{qty * price:.2f}"
                self.batch_in_tree.item(item, values=values)
            except:
                pass

        def _on_cell_edit(event):
            item = self.batch_in_tree.identify_row(event.y)
            if not item:
                return
            column = self.batch_in_tree.identify_column(event.x)
            col_idx = int(column.replace("#", "")) - 1

            if col_idx == 4:
                x, y, w, h = self.batch_in_tree.bbox(item, column)
                entry = tk.Entry(self.batch_in_tree, width=w//8, font=("微软雅黑", 9), relief="solid", bd=2)
                entry.place(x=x, y=y, w=w, h=h)
                entry.focus_set()

                values = self.batch_in_tree.item(item)['values']
                entry.insert(0, values[4] if values[4] else "")

                def _on_enter(e):
                    new_val = entry.get()
                    val_list = list(self.batch_in_tree.item(item)['values'])
                    val_list[4] = new_val
                    try:
                        qty = float(new_val) if new_val else 0
                        price = float(val_list[5]) if val_list[5] else 0
                        val_list[6] = f"{qty * price:.2f}"
                    except:
                        pass
                    self.batch_in_tree.item(item, values=val_list)
                    entry.destroy()
                    _update_total()

                entry.bind("<Return>", _on_enter)
                entry.bind("<Escape>", lambda e: entry.destroy())
                entry.bind("<FocusOut>", _on_enter)

        def _on_product_select(event):
            selected = self.batch_in_tree.selection()
            if not selected:
                return
            item = selected[0]
            column = self.batch_in_tree.identify_column(event.x)
            if column == "#2":
                products = inv_db.get_all_products()
                if not products:
                    messagebox.showwarning("提示", "请先添加商品！")
                    return

                select_win = tk.Toplevel(self.batch_inbound_window)
                select_win.title("选择商品")
                select_win.geometry("600x500")
                select_win.transient(self.batch_inbound_window)
                select_win.grab_set()

                tk.Label(select_win, text="搜索商品:", font=("微软雅黑", 11), padx=10, pady=5).pack(fill="x")
                search_var = tk.StringVar()
                search_entry = tk.Entry(select_win, textvariable=search_var, font=("微软雅黑", 11), relief="solid", bd=1)
                search_entry.pack(fill="x", padx=10, pady=5)
                search_entry.focus_set()

                list_frame = tk.Frame(select_win)
                list_frame.pack(fill="both", expand=True, padx=10, pady=5)

                list_scroll_y = tk.Scrollbar(list_frame)
                list_scroll_y.pack(side="right", fill="y")
                product_list = tk.Listbox(list_frame, font=("微软雅黑", 10), yscrollcommand=list_scroll_y.set)
                product_list.pack(side="left", fill="both", expand=True)
                list_scroll_y.config(command=product_list.yview)

                def _filter_products(*args):
                    keyword = search_var.get().lower().strip()
                    product_list.delete(0, tk.END)
                    for p in products:
                        name = p.get('name', '')
                        spec = p.get('spec', '')
                        if keyword in name.lower() or keyword in spec.lower():
                            stock = inv_db.get_product_stock(p['id'])
                            product_list.insert(tk.END, f"{name} | {spec} | 库存:{stock:.0f} | 单价:¥{float(p.get('price', 0) or 0):.2f}")

                search_var.trace('w', _filter_products)

                def _on_select(*args):
                    idx = product_list.curselection()
                    if idx:
                        selected_text = product_list.get(idx[0])
                        name = selected_text.split(" | ")[0]
                        p = next((prod for prod in products if prod['name'] == name), None)
                        if p:
                            stock = inv_db.get_product_stock(p['id'])
                            values = list(self.batch_in_tree.item(item)['values'])
                            values[1] = p['name']
                            values[2] = p.get('spec', '')
                            values[3] = f"{stock:.0f}"
                            values[5] = f"{float(p.get('price', 0) or 0):.2f}"
                            try:
                                qty = float(values[4]) if values[4] else 0
                                price = float(values[5]) if values[5] else 0
                                values[6] = f"{qty * price:.2f}"
                            except:
                                pass
                            self.batch_in_tree.item(item, values=values)
                            _update_total()
                        select_win.destroy()

                product_list.bind("<Double-Button-1>", _on_select)
                product_list.bind("<<ListboxSelect>>", _on_select)
                _filter_products()

        self.batch_in_tree.bind("<Double-1>", _on_product_select)
        self.batch_in_tree.bind("<Button-1>", _on_cell_edit)

        def _update_total():
            total_qty = 0
            total_amt = 0
            for item in self.batch_in_tree.get_children():
                values = self.batch_in_tree.item(item)['values']
                if values[1]:
                    try:
                        total_qty += float(values[4]) if values[4] else 0
                        total_amt += float(values[6]) if values[6] else 0
                    except:
                        pass
            total_label.config(text=f"合计: {len(self.batch_in_tree.get_children())} 条 | 数量: {total_qty:.0f} | 金额: ¥{total_amt:.2f}")

        def submit_batch():
            items = []
            for item in self.batch_in_tree.get_children():
                values = self.batch_in_tree.item(item)['values']
                if len(values) >= 5 and values[1] and values[4]:
                    try:
                        items.append({
                            "name": values[1],
                            "spec": values[2] if len(values) > 2 else "",
                            "qty": float(values[4]),
                            "price": float(values[5]) if len(values) > 5 and values[5] else 0,
                            "amount": float(values[6]) if len(values) > 6 and values[6] else 0,
                            "supplier": values[7] if len(values) > 7 else ""
                        })
                    except ValueError:
                        messagebox.showwarning("数据错误", f"商品 '{values[1]}' 的数量或单价格式不正确！")
                        return

            if not items:
                messagebox.showwarning("提示", "请至少添加一条有效的入库记录！")
                return

            if not self.batch_handler_var.get().strip():
                messagebox.showwarning("提示", "请填写经手人！")
                return

            try:
                warehouses = inv_db.get_warehouses()
                warehouse_obj = next((w for w in warehouses if w['name'] == self.batch_warehouse_var.get()),
                                    warehouses[0] if warehouses else None)
                warehouse_id = warehouse_obj['id'] if warehouse_obj else 1

                success_count = 0
                fail_count = 0
                trans_nos = []

                for item in items:
                    products = inv_db.get_all_products()
                    product = next((p for p in products if p.get('name') == item['name'] and (not item['spec'] or p.get('spec') == item['spec'])), None)
                    if not product:
                        fail_count += 1
                        continue

                    trans_no = inv_db.add_inbound(product['id'], warehouse_id, item['qty'],
                                                  self.batch_remark_var.get().strip(),
                                                  self.batch_handler_var.get().strip())
                    if trans_no:
                        success_count += 1
                        trans_nos.append(trans_no)

                if success_count > 0:
                    msg = f"批量入库完成！\n成功: {success_count} 条\n失败: {fail_count} 条\n单号: {', '.join(trans_nos)}"
                    messagebox.showinfo("成功", msg)

                    if messagebox.askyesno("打印", "是否打印入库单？"):
                        self._print_batch_inbound(items, trans_nos)

                    self.load_inbound()
                    self.batch_inbound_window.destroy()
                else:
                    messagebox.showerror("错误", "批量入库全部失败！")
            except Exception as e:
                messagebox.showerror("错误", f"批量入库失败：\n{str(e)}")

        btn_frame = tk.Frame(self.batch_inbound_window, bg="#F0F4F8")
        btn_frame.pack(fill="x", padx=10, pady=8)

        left_btn_frame = tk.Frame(btn_frame, bg="#F0F4F8")
        left_btn_frame.pack(side="left")

        tk.Button(left_btn_frame, text="添加5行", command=lambda: _add_rows(5), bg=THEME["success"], fg="white",
                  font=("微软雅黑", 10), relief="flat", padx=12, pady=5, cursor="hand2").pack(side="left", padx=3)
        tk.Button(left_btn_frame, text="添加行", command=add_row, bg="#28A745", fg="white",
                  font=("微软雅黑", 10), relief="flat", padx=12, pady=5, cursor="hand2").pack(side="left", padx=3)
        tk.Button(left_btn_frame, text="删除行", command=delete_row, bg="#DC3545", fg="white",
                  font=("微软雅黑", 10), relief="flat", padx=12, pady=5, cursor="hand2").pack(side="left", padx=3)
        tk.Button(left_btn_frame, text="清空", command=clear_all, bg="#6C757D", fg="white",
                  font=("微软雅黑", 10), relief="flat", padx=12, pady=5, cursor="hand2").pack(side="left", padx=3)

        total_label = tk.Label(btn_frame, text="合计: 0 条 | 数量: 0 | 金额: ¥0.00",
                               font=("微软雅黑", 10, "bold"), bg="#F0F4F8", fg="#1A2742")
        total_label.pack(side="left", padx=20)

        tk.Button(btn_frame, text="确认批量入库", command=submit_batch, bg=THEME["accent"], fg="white",
                  font=("微软雅黑", 11, "bold"), relief="flat", padx=20, pady=6, cursor="hand2").pack(side="right", padx=5)

        _add_rows(5)
        self.batch_inbound_window.update()
        _update_total()

    def _print_batch_inbound(self, items, trans_nos):
        """打印批量入库单"""
        data = {
            "order_no": ", ".join(trans_nos),
            "date": date.today().strftime("%Y-%m-%d"),
            "handler": self.batch_handler_var.get(),
            "warehouse": self.batch_warehouse_var.get(),
            "remark": self.batch_remark_var.get(),
            "items": items
        }
        print_inbound(data)

    def _get_inbound_history(self):
        try:
            trans = inv_db.get_inventory_transactions(trans_type='inbound', limit=200)
        except:
            return []
        result = []
        for i, t in enumerate(trans, 1):
            result.append([i, t.get('trans_no', ''), str(t.get('trans_date', ''))[:10],
                         t.get('product_name', ''), t.get('spec', ''),
                         f"{float(t.get('qty', 0) or 0):.0f}",
                         f"¥{float(t.get('unit_price', 0) or 0):.2f}",
                         f"¥{float(t.get('qty', 0) or 0) * float(t.get('unit_price', 0) or 0):.2f}",
                         t.get('supplier_name', '-'), t.get('operator', ''), t.get('warehouse_name', '')])
        return result

    def _filter_history(self, tree, search_var):
        keyword = search_var.get().strip().lower()
        for item in tree.get_children():
            tree.delete(item)
        data = self._get_inbound_history() if tree == getattr(self, '_in_history_tree', None) else self._get_outbound_history()
        for i, row in enumerate(data):
            if not keyword or any(keyword in str(v).lower() for v in row):
                tag = "alt" if i % 2 else "norm"
                tree.insert("", "end", values=row, tags=(tag,))

    # ══════════════════════════════════════════
    # 出库管理
    # ══════════════════════════════════════════
    def load_outbound(self):
        self.current_view = self.load_outbound
        self._clear_content()
        self._section_title(self.content, "出库管理", "新增出库 / 查看出库记录")

        form_frame = tk.LabelFrame(self.content, text=" 新增出库单 ",
                                  font=("微软雅黑", 11, "bold"),
                                  bg="white", fg=THEME["bg_dark"], relief="groove", bd=2)
        form_frame.pack(fill="x", padx=20, pady=8, ipady=8)

        fields = [
            ("出库单号", f"CK-{date.today().year}{date.today().month:02d}-001", True),
            ("出库日期", date.today().strftime("%Y-%m-%d"), True),
            ("商品名称", "", True),
            ("规格型号", "", True),
            ("出库数量", "", True),
            ("客户/领用", "", True),
            ("经手人", "", True),
            ("存放仓库", "", True),
            ("备注", "", False),
        ]

        self.out_vars = {}
        warehouses = inv_db.get_warehouses()
        warehouse_names = [w['name'] for w in warehouses] if warehouses else ["1号仓"]
        products = inv_db.get_all_products()
        product_names = [p['name'] for p in products] if products else []

        for i, (label, default, required) in enumerate(fields):
            row_idx = i // 3
            col_idx = (i % 3) * 2
            star = " *" if required else "  "
            tk.Label(form_frame, text=f"{label}{star}:", font=("微软雅黑", 10),
                     bg="white", fg="#333").grid(row=row_idx, column=col_idx, padx=12, pady=6, sticky="e")

            var = tk.StringVar(value=default)

            if label == "商品名称":
                cb = ttk.Combobox(form_frame, textvariable=var, values=product_names,
                                  font=("微软雅黑", 11), width=18, state="normal")
                cb.grid(row=row_idx, column=col_idx+1, padx=4, pady=6, sticky="w")
                cb.bind("<<ComboboxSelected>>", self._on_outbound_product_selected)
                self._outbound_name_cb = cb
            elif label == "规格型号":
                cb = ttk.Combobox(form_frame, textvariable=var, values=[],
                                  font=("微软雅黑", 11), width=18, state="readonly")
                cb.grid(row=row_idx, column=col_idx+1, padx=4, pady=6, sticky="w")
                self._outbound_spec_cb = cb
            elif label == "存放仓库":
                cb = ttk.Combobox(form_frame, textvariable=var, values=warehouse_names,
                                  font=("微软雅黑", 11), width=18, state="readonly")
                if warehouse_names:
                    cb.current(0)
                cb.grid(row=row_idx, column=col_idx+1, padx=4, pady=6, sticky="w")
            else:
                entry = tk.Entry(form_frame, textvariable=var, font=("微软雅黑", 11),
                                width=20, bg=THEME["input_bg"], relief="solid")
                entry.grid(row=row_idx, column=col_idx+1, padx=4, pady=6, sticky="w")
            self.out_vars[label] = var

        self._auto_out_no()

        btn_frame = tk.Frame(form_frame, bg="white")
        btn_frame.grid(row=3, column=0, columnspan=6, pady=8)
        self._outbound_submitting = False

        def _safe_submit():
            if self._outbound_submitting:
                return
            self._outbound_submitting = True
            try:
                self._submit_outbound()
            finally:
                self._outbound_submitting = False

        def _batch_outbound():
            self._open_batch_outbound_window()

        tk.Button(btn_frame, text="  确认出库  ", font=("微软雅黑", 12, "bold"),
                  bg=THEME["warn"], fg="white", relief="flat",
                  padx=20, pady=6, cursor="hand2", command=_safe_submit).pack(side="left", padx=12)
        tk.Button(btn_frame, text="  批量出库  ", font=("微软雅黑", 12),
                  bg=THEME["accent"], fg="white", relief="flat",
                  padx=20, pady=6, cursor="hand2", command=_batch_outbound).pack(side="left", padx=12)
        tk.Button(btn_frame, text="  清空表单  ", font=("微软雅黑", 12),
                  bg="#6C757D", fg="white", relief="flat",
                  padx=20, pady=6, cursor="hand2", command=self.load_outbound).pack(side="left", padx=12)

        self._section_title(self.content, "出库历史记录")
        sf_out = tk.Frame(self.content, bg="#F0F4F8")
        sf_out.pack(fill="x", padx=20, pady=4)

        tk.Label(sf_out, text="搜索:", font=("微软雅黑", 10), bg="#F0F4F8").pack(side="left")
        self._out_history_search_var = tk.StringVar()
        tk.Entry(sf_out, textvariable=self._out_history_search_var, font=("微软雅黑", 11),
                width=20, relief="solid", bg="white").pack(side="left", padx=4)
        tk.Button(sf_out, text="筛选", font=("微软雅黑", 10), bg=THEME["accent"], fg="white",
                  relief="flat", padx=12, cursor="hand2",
                  command=lambda: self._filter_history(self._out_history_tree, self._out_history_search_var)).pack(side="left", padx=6)

        columns = ["#", "单号", "日期", "商品名称", "规格", "数量", "客户/领用", "经手人", "仓库"]
        col_widths = [40, 110, 95, 150, 90, 60, 100, 75, 70]
        self._out_history_tree = self._build_table(self.content, columns, col_widths,
                          lambda: self._get_outbound_history(), height=10)

    def _auto_out_no(self):
        today = date.today()
        month_prefix = f"CK-{today.year}{today.month:02d}-"
        try:
            trans = inv_db.get_inventory_transactions(trans_type='outbound', limit=1000)
            count = sum(1 for t in trans if t.get('trans_no', '').startswith(month_prefix))
        except:
            count = 0
        no = f"{month_prefix}{count+1:03d}"
        if '出库单号' in self.out_vars:
            self.out_vars['出库单号'].set(no)

    def _on_outbound_product_selected(self, event=None):
        name = self.out_vars.get("商品名称", tk.StringVar()).get().strip()
        if not name:
            return
        products = inv_db.get_all_products()
        specs = list({p['spec'] for p in products if p.get('name') == name and p.get('spec')})
        if hasattr(self, '_outbound_spec_cb') and self._outbound_spec_cb:
            self._outbound_spec_cb['values'] = specs
            if len(specs) == 1:
                self.out_vars['规格型号'].set(specs[0])

    def _submit_outbound(self):
        name = self.out_vars.get("商品名称", tk.StringVar()).get().strip()
        spec = self.out_vars.get("规格型号", tk.StringVar()).get().strip()
        qty_s = self.out_vars.get("出库数量", tk.StringVar()).get().strip()
        customer = self.out_vars.get("客户/领用", tk.StringVar()).get().strip()
        handler = self.out_vars.get("经手人", tk.StringVar()).get().strip()
        warehouse = self.out_vars.get("存放仓库", tk.StringVar()).get().strip()

        if not name or not qty_s:
            messagebox.showwarning("提示", "带 * 的字段为必填项！")
            return
        try:
            qty = float(qty_s)
        except:
            messagebox.showerror("错误", "出库数量必须为数字！")
            return
        if qty <= 0:
            messagebox.showerror("错误", "出库数量必须大于0！")
            return

        products = inv_db.get_all_products()
        product = next((p for p in products if p.get('name') == name and (not spec or p.get('spec') == spec)), None)
        if not product:
            messagebox.showerror("错误", f"找不到商品「{name}」！")
            return

        warehouses = inv_db.get_warehouses()
        warehouse_obj = next((w for w in warehouses if w['name'] == warehouse), warehouses[0] if warehouses else None)
        warehouse_id = warehouse_obj['id'] if warehouse_obj else 1

        try:
            trans_no = inv_db.add_outbound(product['id'], warehouse_id, qty, self.out_vars.get("备注", tk.StringVar()).get().strip(), handler)
            if trans_no:
                messagebox.showinfo("成功", f"出库成功！单号：{trans_no}")
                
                # 询问是否打印
                if messagebox.askyesno("打印", "是否打印出库单？"):
                    self._print_single_outbound(name, spec, qty, customer, handler, warehouse, trans_no)
                
                self.load_outbound()
            else:
                messagebox.showerror("错误", "出库失败（可能库存不足）！")
        except Exception as e:
            messagebox.showerror("错误", f"出库失败：{str(e)}")

    def _print_single_outbound(self, name, spec, qty, customer, handler, warehouse, trans_no):
        """打印单笔出库单"""
        data = {
            "order_no": trans_no,
            "date": date.today().strftime("%Y-%m-%d"),
            "customer": customer,
            "handler": handler,
            "warehouse": warehouse,
            "items": [{
                "name": name,
                "spec": spec,
                "qty": qty
            }]
        }
        print_outbound(data)

    def _open_batch_outbound_window(self):
        """打开批量出库窗口"""
        self.batch_outbound_window = tk.Toplevel(self)
        self.batch_outbound_window.title("批量出库")
        self.batch_outbound_window.geometry("1000x650")
        self.batch_outbound_window.resizable(True, True)
        self.batch_outbound_window.transient(self)
        self.batch_outbound_window.grab_set()
        self.batch_outbound_window.configure(bg="#F0F4F8")

        top_frame = tk.Frame(self.batch_outbound_window, bg="#F0F4F8")
        top_frame.pack(fill="x", padx=10, pady=8)

        tk.Label(top_frame, text="批量出库", font=("微软雅黑", 14, "bold"), bg="#F0F4F8", fg="#1A2742").pack(side="left")

        tip_text = tk.Label(top_frame, text="💡 双击商品名称列选择商品 | 点击数量列可直接编辑 | 库存不足时自动提醒",
                           font=("微软雅黑", 9), bg="#FFF3E0", fg="#E65100", padx=10, pady=5)
        tip_text.pack(side="right")

        header_frame = tk.Frame(self.batch_outbound_window, bg="#F0F4F8")
        header_frame.pack(fill="x", padx=10, pady=5)

        fields_frame = tk.Frame(header_frame, bg="#F0F4F8")
        fields_frame.pack(fill="x", pady=5)

        tk.Label(fields_frame, text="出库单号:", bg="#F0F4F8", font=("微软雅黑", 10)).grid(row=0, column=0, padx=5, pady=3)
        self.batch_out_no_var = tk.StringVar(value=f"CK-{date.today().year}{date.today().month:02d}-001")
        tk.Entry(fields_frame, textvariable=self.batch_out_no_var, width=22, font=("微软雅黑", 10), relief="solid", bd=1).grid(row=0, column=1, padx=5, pady=3)

        tk.Label(fields_frame, text="出库日期:", bg="#F0F4F8", font=("微软雅黑", 10)).grid(row=0, column=2, padx=5, pady=3)
        self.batch_out_date_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        tk.Entry(fields_frame, textvariable=self.batch_out_date_var, width=15, font=("微软雅黑", 10), relief="solid", bd=1).grid(row=0, column=3, padx=5, pady=3)

        tk.Label(fields_frame, text="客户/领用:", bg="#F0F4F8", font=("微软雅黑", 10)).grid(row=0, column=4, padx=5, pady=3)
        self.batch_customer_var = tk.StringVar()
        tk.Entry(fields_frame, textvariable=self.batch_customer_var, width=15, font=("微软雅黑", 10), relief="solid", bd=1).grid(row=0, column=5, padx=5, pady=3)

        tk.Label(fields_frame, text="经手人:", bg="#F0F4F8", font=("微软雅黑", 10)).grid(row=0, column=6, padx=5, pady=3)
        self.batch_out_handler_var = tk.StringVar()
        tk.Entry(fields_frame, textvariable=self.batch_out_handler_var, width=15, font=("微软雅黑", 10), relief="solid", bd=1).grid(row=0, column=7, padx=5, pady=3)

        tk.Label(fields_frame, text="存放仓库:", bg="#F0F4F8", font=("微软雅黑", 10)).grid(row=0, column=8, padx=5, pady=3)
        warehouses = inv_db.get_warehouses()
        warehouse_names = [w['name'] for w in warehouses] if warehouses else ["1号仓"]
        self.batch_out_warehouse_var = tk.StringVar(value=warehouse_names[0] if warehouse_names else "")
        ttk.Combobox(fields_frame, textvariable=self.batch_out_warehouse_var, values=warehouse_names, width=14, font=("微软雅黑", 10)).grid(row=0, column=9, padx=5, pady=3)

        tk.Label(fields_frame, text="备注:", bg="#F0F4F8", font=("微软雅黑", 10)).grid(row=0, column=10, padx=5, pady=3)
        self.batch_out_remark_var = tk.StringVar()
        tk.Entry(fields_frame, textvariable=self.batch_out_remark_var, width=22, font=("微软雅黑", 10), relief="solid", bd=1).grid(row=0, column=11, padx=5, pady=3)

        table_frame = tk.Frame(self.batch_outbound_window)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        scroll_y = tk.Scrollbar(table_frame, orient="vertical")
        scroll_y.pack(side="right", fill="y")
        scroll_x = tk.Scrollbar(table_frame, orient="horizontal")
        scroll_x.pack(side="bottom", fill="x")

        columns = ("#", "商品名称", "规格型号", "当前库存", "可出库量", "出库数量")
        self.batch_out_tree = ttk.Treeview(table_frame, columns=columns, show="headings",
                                          yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set, height=12)
        scroll_y.config(command=self.batch_out_tree.yview)
        scroll_x.config(command=self.batch_out_tree.xview)

        col_widths = [40, 200, 150, 80, 80, 100]
        for i, (col, width) in enumerate(zip(columns, col_widths)):
            self.batch_out_tree.heading(col, text=col, anchor="center")
            self.batch_out_tree.column(col, width=width, anchor="center")

        self.batch_out_tree.tag_configure("norm", background="#FFFFFF")
        self.batch_out_tree.tag_configure("alt", background="#F5F8FA")
        self.batch_out_tree.tag_configure("warning", background="#FFEBEE")
        self.batch_out_tree.tag_configure("success", background="#E8F5E9")
        self.batch_out_tree.pack(fill="both", expand=True)

        def _add_rows(count=5):
            products = inv_db.get_all_products()
            if not products:
                messagebox.showwarning("提示", "请先添加商品！")
                return
            for i in range(count):
                row_id = len(self.batch_out_tree.get_children()) + 1
                tag = "alt" if row_id % 2 else "norm"
                self.batch_out_tree.insert("", "end", values=(row_id, "", "", "", "", ""), tags=(tag,))

        def add_row():
            _add_rows(1)

        def delete_row():
            selected = self.batch_out_tree.selection()
            if selected:
                self.batch_out_tree.delete(selected)
                for i, item in enumerate(self.batch_out_tree.get_children(), 1):
                    values = list(self.batch_out_tree.item(item)['values'])
                    values[0] = i
                    tag = "alt" if i % 2 else "norm"
                    self.batch_out_tree.item(item, values=values, tags=(tag,))

        def clear_all():
            for item in self.batch_out_tree.get_children():
                self.batch_out_tree.delete(item)

        def _check_stock(item):
            values = self.batch_out_tree.item(item)['values']
            if not values[1]:
                return
            try:
                qty = float(values[4]) if values[4] else 0
                stock = float(values[3]) if values[3] else 0
                if qty > stock:
                    self.batch_out_tree.item(item, tags=("warning",))
                else:
                    self.batch_out_tree.item(item, tags=("success",))
            except:
                pass

        def _on_cell_edit(event):
            item = self.batch_out_tree.identify_row(event.y)
            if not item:
                return
            column = self.batch_out_tree.identify_column(event.x)
            col_idx = int(column.replace("#", "")) - 1

            if col_idx == 4:
                x, y, w, h = self.batch_out_tree.bbox(item, column)
                entry = tk.Entry(self.batch_out_tree, width=w // 8, font=("微软雅黑", 9), relief="solid", bd=2)
                entry.place(x=x, y=y, w=w, h=h)
                entry.focus_set()

                values = self.batch_out_tree.item(item)['values']
                entry.insert(0, values[4] if values[4] else "")

                def _on_enter(e):
                    new_val = entry.get()
                    val_list = list(self.batch_out_tree.item(item)['values'])
                    val_list[4] = new_val
                    try:
                        qty = float(new_val) if new_val else 0
                        stock = float(val_list[3]) if val_list[3] else 0
                        val_list[4] = f"{qty:.0f}"
                        if qty > stock and stock > 0:
                            val_list[4] = f"{qty:.0f} ⚠️"
                            self.batch_out_tree.item(item, values=val_list, tags=("warning",))
                        else:
                            self.batch_out_tree.item(item, values=val_list, tags=("success",))
                    except:
                        pass
                    entry.destroy()
                    _update_total()

                entry.bind("<Return>", _on_enter)
                entry.bind("<Escape>", lambda e: entry.destroy())
                entry.bind("<FocusOut>", _on_enter)

        def _on_product_select(event):
            selected = self.batch_out_tree.selection()
            if not selected:
                return
            item = selected[0]
            column = self.batch_out_tree.identify_column(event.x)
            if column == "#2":
                products = inv_db.get_all_products()
                if not products:
                    messagebox.showwarning("提示", "请先添加商品！")
                    return

                select_win = tk.Toplevel(self.batch_outbound_window)
                select_win.title("选择商品")
                select_win.geometry("650x500")
                select_win.transient(self.batch_outbound_window)
                select_win.grab_set()

                tk.Label(select_win, text="搜索商品:", font=("微软雅黑", 11), padx=10, pady=5).pack(fill="x")
                search_var = tk.StringVar()
                search_entry = tk.Entry(select_win, textvariable=search_var, font=("微软雅黑", 11), relief="solid", bd=1)
                search_entry.pack(fill="x", padx=10, pady=5)
                search_entry.focus_set()

                list_frame = tk.Frame(select_win)
                list_frame.pack(fill="both", expand=True, padx=10, pady=5)

                list_scroll_y = tk.Scrollbar(list_frame)
                list_scroll_y.pack(side="right", fill="y")
                product_list = tk.Listbox(list_frame, font=("微软雅黑", 10), yscrollcommand=list_scroll_y.set)
                product_list.pack(side="left", fill="both", expand=True)
                list_scroll_y.config(command=product_list.yview)

                def _filter_products(*args):
                    keyword = search_var.get().lower().strip()
                    product_list.delete(0, tk.END)
                    for p in products:
                        name = p.get('name', '')
                        spec = p.get('spec', '')
                        if keyword in name.lower() or keyword in spec.lower():
                            stock = inv_db.get_product_stock(p['id'])
                            price = float(p.get('price', 0) or 0)
                            stock_str = f"{stock:.0f}"
                            if stock <= 0:
                                stock_str = "0 (缺货)"
                            product_list.insert(tk.END, f"{name} | {spec} | 库存:{stock_str} | 单价:¥{price:.2f}")

                search_var.trace('w', _filter_products)

                def _on_select(*args):
                    idx = product_list.curselection()
                    if idx:
                        selected_text = product_list.get(idx[0])
                        name = selected_text.split(" | ")[0]
                        p = next((prod for prod in products if prod['name'] == name), None)
                        if p:
                            stock = inv_db.get_product_stock(p['id'])
                            values = list(self.batch_out_tree.item(item)['values'])
                            values[1] = p['name']
                            values[2] = p.get('spec', '')
                            values[3] = f"{stock:.0f}"
                            values[4] = ""
                            values[4] = f"{stock:.0f}" if stock > 0 else ""
                            if stock <= 0:
                                self.batch_out_tree.item(item, values=values, tags=("warning",))
                            else:
                                self.batch_out_tree.item(item, values=values, tags=("success",))
                            _update_total()
                        select_win.destroy()

                product_list.bind("<Double-Button-1>", _on_select)
                product_list.bind("<<ListboxSelect>>", _on_select)
                _filter_products()

        self.batch_out_tree.bind("<Double-1>", _on_product_select)
        self.batch_out_tree.bind("<Button-1>", _on_cell_edit)

        def _update_total():
            total_qty = 0
            warning_count = 0
            for item in self.batch_out_tree.get_children():
                values = self.batch_out_tree.item(item)['values']
                if values[1]:
                    try:
                        qty = float(values[4]) if values[4] else 0
                        stock = float(values[3]) if values[3] else 0
                        total_qty += qty
                        if qty > stock and stock > 0:
                            warning_count += 1
                    except:
                        pass
            warning_text = f" | ⚠️ {warning_count} 条库存不足" if warning_count > 0 else ""
            total_label.config(text=f"合计: {len(self.batch_out_tree.get_children())} 条 | 出库数量: {total_qty:.0f}{warning_text}")

        def submit_batch():
            items = []
            low_stock_items = []
            for item in self.batch_out_tree.get_children():
                values = self.batch_out_tree.item(item)['values']
                if len(values) >= 5 and values[1] and values[4]:
                    try:
                        qty = float(values[4])
                        stock = float(values[3]) if values[3] else 0
                        items.append({
                            "name": values[1],
                            "spec": values[2] if len(values) > 2 else "",
                            "stock": stock,
                            "qty": qty
                        })
                        if qty > stock and stock > 0:
                            low_stock_items.append(values[1])
                    except ValueError:
                        messagebox.showwarning("数据错误", f"商品 '{values[1]}' 的出库数量格式不正确！")
                        return

            if not items:
                messagebox.showwarning("提示", "请至少添加一条有效的出库记录！")
                return

            if not self.batch_out_handler_var.get().strip():
                messagebox.showwarning("提示", "请填写经手人！")
                return

            if low_stock_items:
                response = messagebox.askyesno("库存不足", f"以下商品库存不足：\n{', '.join(low_stock_items)}\n\n是否继续出库？")
                if not response:
                    return

            try:
                warehouses = inv_db.get_warehouses()
                warehouse_obj = next((w for w in warehouses if w['name'] == self.batch_out_warehouse_var.get()),
                                    warehouses[0] if warehouses else None)
                warehouse_id = warehouse_obj['id'] if warehouse_obj else 1

                success_count = 0
                fail_count = 0
                trans_nos = []

                for item in items:
                    products = inv_db.get_all_products()
                    product = next((p for p in products if p.get('name') == item['name'] and (not item['spec'] or p.get('spec') == item['spec'])), None)
                    if not product:
                        fail_count += 1
                        continue

                    try:
                        trans_no = inv_db.add_outbound(product['id'], warehouse_id, item['qty'],
                                                      self.batch_out_remark_var.get().strip(),
                                                      self.batch_out_handler_var.get().strip())
                        if trans_no:
                            success_count += 1
                            trans_nos.append(trans_no)
                        else:
                            fail_count += 1
                    except Exception as e:
                        fail_count += 1

                if success_count > 0:
                    msg = f"批量出库完成！\n成功: {success_count} 条\n失败: {fail_count} 条\n单号: {', '.join(trans_nos)}"
                    messagebox.showinfo("成功", msg)

                    if messagebox.askyesno("打印", "是否打印出库单？"):
                        self._print_batch_outbound(items, trans_nos)

                    self.load_outbound()
                    self.batch_outbound_window.destroy()
                else:
                    messagebox.showerror("错误", "批量出库全部失败！（可能库存不足）")
            except Exception as e:
                messagebox.showerror("错误", f"批量出库失败：\n{str(e)}")

        btn_frame = tk.Frame(self.batch_outbound_window, bg="#F0F4F8")
        btn_frame.pack(fill="x", padx=10, pady=8)

        left_btn_frame = tk.Frame(btn_frame, bg="#F0F4F8")
        left_btn_frame.pack(side="left")

        tk.Button(left_btn_frame, text="添加5行", command=lambda: _add_rows(5), bg=THEME["success"], fg="white",
                  font=("微软雅黑", 10), relief="flat", padx=12, pady=5, cursor="hand2").pack(side="left", padx=3)
        tk.Button(left_btn_frame, text="添加行", command=add_row, bg="#28A745", fg="white",
                  font=("微软雅黑", 10), relief="flat", padx=12, pady=5, cursor="hand2").pack(side="left", padx=3)
        tk.Button(left_btn_frame, text="删除行", command=delete_row, bg="#DC3545", fg="white",
                  font=("微软雅黑", 10), relief="flat", padx=12, pady=5, cursor="hand2").pack(side="left", padx=3)
        tk.Button(left_btn_frame, text="清空", command=clear_all, bg="#6C757D", fg="white",
                  font=("微软雅黑", 10), relief="flat", padx=12, pady=5, cursor="hand2").pack(side="left", padx=3)

        total_label = tk.Label(btn_frame, text="合计: 0 条 | 出库数量: 0",
                               font=("微软雅黑", 10, "bold"), bg="#F0F4F8", fg="#1A2742")
        total_label.pack(side="left", padx=20)

        tk.Button(btn_frame, text="确认批量出库", command=submit_batch, bg=THEME["warn"], fg="white",
                  font=("微软雅黑", 11, "bold"), relief="flat", padx=20, pady=6, cursor="hand2").pack(side="right", padx=5)

        _add_rows(5)
        self.batch_outbound_window.update()
        _update_total()

    def _print_batch_outbound(self, items, trans_nos):
        """打印批量出库单"""
        data = {
            "order_no": ", ".join(trans_nos),
            "date": date.today().strftime("%Y-%m-%d"),
            "customer": self.batch_customer_var.get(),
            "handler": self.batch_out_handler_var.get(),
            "warehouse": self.batch_out_warehouse_var.get(),
            "remark": self.batch_out_remark_var.get(),
            "items": items
        }
        print_outbound(data)

    def _get_outbound_history(self):
        try:
            trans = inv_db.get_inventory_transactions(trans_type='outbound', limit=200)
        except:
            return []
        result = []
        for i, t in enumerate(trans, 1):
            result.append([i, t.get('trans_no', ''), str(t.get('trans_date', ''))[:10],
                         t.get('product_name', ''), t.get('spec', ''),
                         f"{float(t.get('qty', 0) or 0):.0f}",
                         t.get('customer', '-'), t.get('operator', ''), t.get('warehouse_name', '')])
        return result

    # ══════════════════════════════════════════
    # 预警分析
    # ══════════════════════════════════════════
    def load_alerts(self):
        self.current_view = self.load_alerts
        self._clear_content()
        self._section_title(self.content, "预警分析", "库存异常商品汇总")

        try:
            alerts = inv_db.get_low_stock_alerts()
            stats = inv_db.get_statistics()
        except:
            alerts = []
            stats = {}

        cards_frame = tk.Frame(self.content, bg="#F0F4F8")
        cards_frame.pack(fill="x", padx=20, pady=8)

        self._create_stat_card(cards_frame, "低库存预警", stats.get('low_stock_count', 0), THEME["warn"]).pack(side="left", fill="both", expand=True, padx=4)
        self._create_stat_card(cards_frame, "缺货商品", stats.get('out_stock_count', 0), THEME["danger"]).pack(side="left", fill="both", expand=True, padx=4)
        self._create_stat_card(cards_frame, "商品种类", stats.get('product_count', 0), THEME["accent"]).pack(side="left", fill="both", expand=True, padx=4)

        self._section_title(self.content, "预警商品明细")

        tree = self._build_table(
            self.content,
            ["SKU编码", "商品名称", "规格", "当前库存", "安全库存", "仓库", "状态"],
            [120, 220, 100, 100, 100, 100, 80],
            lambda: [[a.get('sku', ''), a.get('product_name', ''), a.get('spec', ''),
                     f"{float(a.get('current_qty', 0) or 0):.0f}",
                     f"{float(a.get('safety_stock', 0) or 0):.0f}",
                     a.get('warehouse_name', ''), "预警"] for a in (alerts or [])],
            height=16
        )
        self._apply_status_colors(tree)

    # ══════════════════════════════════════════
    # 商品管理
    # ══════════════════════════════════════════
    def load_products(self):
        self.current_view = self.load_products
        self._clear_content()
        self._section_title(self.content, "商品管理", "商品信息维护")

        btn_frame = tk.Frame(self.content, bg="#F0F4F8")
        btn_frame.pack(fill="x", padx=20, pady=4)
        tk.Button(btn_frame, text="添加商品", font=("微软雅黑", 11, "bold"),
                 bg=THEME["accent"], fg="white", relief="flat", padx=20, pady=6, cursor="hand2",
                 command=self._add_product).pack(side="left", padx=8)
        tk.Button(btn_frame, text="刷新", font=("微软雅黑", 11),
                 bg="#6C757D", fg="white", relief="flat", padx=20, pady=6, cursor="hand2",
                 command=self.load_products).pack(side="left", padx=8)

        columns = ["SKU编码", "商品名称", "规格型号", "单位", "分类", "单价", "状态"]
        col_widths = [120, 200, 120, 60, 100, 80, 70]
        self._products_tree = self._build_table(self.content, columns, col_widths,
                                                self._get_products_data, height=18)

    def _get_products_data(self):
        try:
            products = inv_db.get_all_products()
        except:
            return []
        return [[p.get('sku', ''), p.get('name', ''), p.get('spec', ''),
                p.get('unit', ''), p.get('category_name', ''),
                f"¥{float(p.get('price', 0) or 0):.2f}", "正常"] for p in products]

    def _generate_sku(self):
        products = inv_db.get_all_products()
        max_num = 0
        if products:
            for p in products:
                sku = p.get('sku', '')
                if sku.startswith('SKU-'):
                    try:
                        num = int(sku.split('-')[1])
                        if num > max_num:
                            max_num = num
                    except ValueError:
                        continue
        return f"SKU-{max_num + 1:04d}"

    def _add_product(self):
        win = tk.Toplevel(self)
        win.title("添加商品")
        win.geometry("500x380")
        win.configure(bg=THEME["bg_dark"])
        win.transient(self)
        win.grab_set()

        fields = [("商品名称", "name"), ("规格型号", "spec"), ("单位", "unit"), ("单价", "price")]
        entries = {}
        for i, (label, key) in enumerate(fields):
            row, col = i // 2, (i % 2) * 2
            tk.Label(win, text=label + ":", font=("微软雅黑", 10), bg=THEME["bg_dark"],
                    fg=THEME["text_white"]).grid(row=row, column=col, sticky="e", padx=10, pady=8)
            e = tk.Entry(win, font=("微软雅黑", 10), width=25)
            e.grid(row=row, column=col+1, pady=8)
            entries[key] = e

        tk.Label(win, text="分类:", font=("微软雅黑", 10), bg=THEME["bg_dark"],
                fg=THEME["text_white"]).grid(row=1, column=2, sticky="e", padx=10, pady=8)
        category_combo = ttk.Combobox(win, font=("微软雅黑", 10), width=23)
        categories = inv_db.get_categories()
        category_names = [c['name'] for c in categories] if categories else []
        category_combo['values'] = category_names
        if category_names:
            category_combo.current(0)
        category_combo.grid(row=1, column=3, pady=8)

        tk.Label(win, text="仓库:", font=("微软雅黑", 10), bg=THEME["bg_dark"],
                fg=THEME["text_white"]).grid(row=3, column=0, sticky="e", padx=10, pady=8)
        warehouse_combo = ttk.Combobox(win, font=("微软雅黑", 10), width=23)
        warehouses = inv_db.get_warehouses()
        warehouse_combo['values'] = [w['name'] for w in warehouses] if warehouses else ["1号仓"]
        if warehouse_combo['values']:
            warehouse_combo.current(0)
        warehouse_combo.grid(row=3, column=1, pady=8)

        tk.Label(win, text="初始库存:", font=("微软雅黑", 10), bg=THEME["bg_dark"],
                fg=THEME["text_white"]).grid(row=4, column=0, sticky="e", padx=10, pady=8)
        qty_entry = tk.Entry(win, font=("微软雅黑", 10), width=25)
        qty_entry.insert(0, "0")
        qty_entry.grid(row=4, column=1, pady=8)

        def save():
            sku = self._generate_sku()
            name = entries['name'].get().strip()
            if not name:
                messagebox.showwarning("提示", "商品名称不能为空！")
                return
            try:
                price = float(entries['price'].get() or 0)
            except:
                price = 0
            warehouse_id = warehouses[warehouse_combo.current()]['id'] if warehouses else 1
            category_name = category_combo.get().strip()
            category_id = None
            if category_name:
                for c in categories:
                    if c['name'] == category_name:
                        category_id = c['id']
                        break
            if inv_db.add_product(sku, name, entries['spec'].get().strip(),
                                 entries['unit'].get().strip() or '个', price,
                                 category_id, warehouse_id,
                                 float(qty_entry.get() or 0)):
                messagebox.showinfo("成功", f"商品添加成功！\nSKU: {sku}")
                win.destroy()
                self.load_products()
            else:
                messagebox.showerror("错误", "商品添加失败！")

        btn_row = tk.Frame(win, bg=THEME["bg_dark"])
        btn_row.grid(row=5, column=0, columnspan=4, pady=20)
        tk.Button(btn_row, text="保存", font=("微软雅黑", 10), bg=THEME["accent"], fg="white",
                 relief="flat", padx=20, pady=5, cursor="hand2", command=save).pack(side="left", padx=12)
        tk.Button(btn_row, text="取消", font=("微软雅黑", 10), bg=THEME["bg_light"], fg="white",
                 relief="flat", padx=20, pady=5, cursor="hand2", command=win.destroy).pack(side="left", padx=12)

    # ══════════════════════════════════════════
    # 供应商管理
    # ══════════════════════════════════════════
    def load_suppliers(self):
        self.current_view = self.load_suppliers
        self._clear_content()
        self._section_title(self.content, "供应商管理", "供应商信息维护")

        btn_frame = tk.Frame(self.content, bg="#F0F4F8")
        btn_frame.pack(fill="x", padx=20, pady=4)
        tk.Button(btn_frame, text="添加供应商", font=("微软雅黑", 11, "bold"),
                 bg=THEME["accent"], fg="white", relief="flat", padx=20, pady=6, cursor="hand2",
                 command=self._add_supplier).pack(side="left", padx=8)

        columns = ["编码", "名称", "联系人", "电话", "地址", "备注"]
        col_widths = [100, 150, 100, 120, 200, 150]
        self._suppliers_tree = self._build_table(self.content, columns, col_widths,
                                                self._get_suppliers_data, height=18)

    def _get_suppliers_data(self):
        try:
            suppliers = inv_db.get_suppliers()
        except:
            return []
        return [[s.get('code', ''), s.get('name', ''), s.get('contact', ''),
                s.get('phone', ''), s.get('address', ''), s.get('remark', '')] for s in suppliers]

    def _add_supplier(self):
        win = tk.Toplevel(self)
        win.title("添加供应商")
        win.geometry("450x350")
        win.configure(bg=THEME["bg_dark"])
        win.transient(self)
        win.grab_set()

        fields = [("编码", "code"), ("名称", "name"), ("联系人", "contact"), ("电话", "phone"), ("地址", "address"), ("备注", "remark")]
        entries = {}
        for i, (label, key) in enumerate(fields):
            row, col = i // 2, (i % 2) * 2
            tk.Label(win, text=label + ":", font=("微软雅黑", 10), bg=THEME["bg_dark"],
                    fg=THEME["text_white"]).grid(row=row, column=col, sticky="e", padx=10, pady=8)
            e = tk.Entry(win, font=("微软雅黑", 10), width=25)
            e.grid(row=row, column=col+1, pady=8)
            entries[key] = e

        def save():
            if not entries['code'].get().strip() or not entries['name'].get().strip():
                messagebox.showwarning("提示", "编码和名称不能为空！")
                return
            if inv_db.add_supplier(entries['code'].get().strip(), entries['name'].get().strip(),
                                  entries['contact'].get().strip(), entries['phone'].get().strip(),
                                  entries['address'].get().strip()):
                messagebox.showinfo("成功", "供应商添加成功！")
                win.destroy()
                self.load_suppliers()
            else:
                messagebox.showerror("错误", "供应商添加失败！")

        btn_row = tk.Frame(win, bg=THEME["bg_dark"])
        btn_row.grid(row=3, column=0, columnspan=4, pady=20)
        tk.Button(btn_row, text="保存", font=("微软雅黑", 10), bg=THEME["accent"], fg="white",
                 relief="flat", padx=20, pady=5, cursor="hand2", command=save).pack(side="left", padx=12)
        tk.Button(btn_row, text="取消", font=("微软雅黑", 10), bg=THEME["bg_light"], fg="white",
                 relief="flat", padx=20, pady=5, cursor="hand2", command=win.destroy).pack(side="left", padx=12)

    # ══════════════════════════════════════════
    # 产品分类
    # ══════════════════════════════════════════
    def load_categories(self):
        self.current_view = self.load_categories
        self._clear_content()
        self._section_title(self.content, "产品分类", "商品分类管理")

        btn_frame = tk.Frame(self.content, bg="#F0F4F8")
        btn_frame.pack(fill="x", padx=20, pady=4)
        tk.Button(btn_frame, text="添加分类", font=("微软雅黑", 11, "bold"),
                 bg=THEME["accent"], fg="white", relief="flat", padx=20, pady=6, cursor="hand2",
                 command=self._add_category).pack(side="left", padx=8)

        columns = ["编号", "分类名称", "描述"]
        col_widths = [80, 200, 400]
        self._categories_tree = self._build_table(self.content, columns, col_widths,
                                                  self._get_categories_data, height=18)

    def _get_categories_data(self):
        try:
            categories = inv_db.get_categories()
        except:
            return []
        return [[c.get('id', ''), c.get('name', ''), c.get('description', '')] for c in categories]

    def _add_category(self):
        win = tk.Toplevel(self)
        win.title("添加分类")
        win.geometry("400x250")
        win.configure(bg=THEME["bg_dark"])
        win.transient(self)
        win.grab_set()

        tk.Label(win, text="分类名称:", font=("微软雅黑", 10), bg=THEME["bg_dark"],
                fg=THEME["text_white"]).grid(row=0, column=0, sticky="e", padx=10, pady=12)
        name_entry = tk.Entry(win, font=("微软雅黑", 10), width=25)
        name_entry.grid(row=0, column=1, pady=12)

        tk.Label(win, text="描述:", font=("微软雅黑", 10), bg=THEME["bg_dark"],
                fg=THEME["text_white"]).grid(row=1, column=0, sticky="e", padx=10, pady=12)
        desc_entry = tk.Entry(win, font=("微软雅黑", 10), width=25)
        desc_entry.grid(row=1, column=1, pady=12)

        def save():
            if not name_entry.get().strip():
                messagebox.showwarning("提示", "分类名称不能为空！")
                return
            if inv_db.add_category(desc_entry.get().strip(), name_entry.get().strip()):
                messagebox.showinfo("成功", "分类添加成功！")
                win.destroy()
                self.load_categories()
            else:
                messagebox.showerror("错误", "分类添加失败！")

        btn_row = tk.Frame(win, bg=THEME["bg_dark"])
        btn_row.grid(row=2, column=0, columnspan=2, pady=20)
        tk.Button(btn_row, text="保存", font=("微软雅黑", 10), bg=THEME["accent"], fg="white",
                 relief="flat", padx=20, pady=5, cursor="hand2", command=save).pack(side="left", padx=12)
        tk.Button(btn_row, text="取消", font=("微软雅黑", 10), bg=THEME["bg_light"], fg="white",
                 relief="flat", padx=20, pady=5, cursor="hand2", command=win.destroy).pack(side="left", padx=12)

    # ══════════════════════════════════════════
    # 基础数据
    # ══════════════════════════════════════════
    def load_basics(self):
        self.current_view = self.load_basics
        self._clear_content()
        self._section_title(self.content, "基础数据", "仓库设置与系统配置")

        tk.Label(self.content, text="仓库列表", font=("微软雅黑", 14, "bold"),
                bg="#F0F4F8", fg=THEME["bg_dark"]).pack(anchor="w", padx=20, pady=(10, 5))

        columns = ["编号", "仓库编码", "仓库名称", "描述"]
        col_widths = [60, 100, 150, 300]
        self._warehouses_tree = self._build_table(self.content, columns, col_widths,
                                                 self._get_warehouses_data, height=12)

        btn_row = tk.Frame(self.content, bg="#F0F4F8")
        btn_row.pack(fill="x", padx=20, pady=10)
        tk.Button(btn_row, text="添加仓库", font=("微软雅黑", 11),
                 bg=THEME["accent"], fg="white", relief="flat", padx=20, pady=5, cursor="hand2",
                 command=self._add_warehouse).pack(side="left", padx=8)
        tk.Button(btn_row, text="刷新", font=("微软雅黑", 11),
                 bg="#6C757D", fg="white", relief="flat", padx=20, pady=5, cursor="hand2",
                 command=self.load_basics).pack(side="left", padx=8)

        tk.Label(self.content, text="系统统计", font=("微软雅黑", 14, "bold"),
                bg="#F0F4F8", fg=THEME["bg_dark"]).pack(anchor="w", padx=20, pady=(20, 5))

        try:
            stats = inv_db.get_statistics()
            total_value = float(stats.get('total_value', 0) or 0)
            total_qty = float(stats.get('total_qty', 0) or 0)
            product_count = stats.get('product_count', 0)
            low_stock = stats.get('low_stock_count', 0)
            out_stock = stats.get('out_stock_count', 0)
        except:
            total_value = total_qty = product_count = low_stock = out_stock = 0

        stats_text = f"""
        商品种类: {product_count} 种
        库存总量: {total_qty:,.0f}
        库存总值: ¥{total_value:,.2f}
        低库存预警: {low_stock} 种
        缺货商品: {out_stock} 种
        """
        tk.Label(self.content, text=stats_text, font=("微软雅黑", 11),
                bg="#F0F4F8", fg=THEME["bg_dark"], justify="left").pack(anchor="w", padx=30)

    def _get_warehouses_data(self):
        try:
            warehouses = inv_db.get_warehouses()
        except:
            return []
        return [[w.get('id', ''), w.get('code', ''), w.get('name', ''), w.get('description', '')] for w in warehouses]

    def _add_warehouse(self):
        win = tk.Toplevel(self)
        win.title("添加仓库")
        win.geometry("400x250")
        win.configure(bg=THEME["bg_dark"])
        win.transient(self)
        win.grab_set()

        tk.Label(win, text="仓库编码:", font=("微软雅黑", 10), bg=THEME["bg_dark"],
                fg=THEME["text_white"]).grid(row=0, column=0, sticky="e", padx=10, pady=12)
        code_entry = tk.Entry(win, font=("微软雅黑", 10), width=25)
        code_entry.grid(row=0, column=1, pady=12)

        tk.Label(win, text="仓库名称:", font=("微软雅黑", 10), bg=THEME["bg_dark"],
                fg=THEME["text_white"]).grid(row=1, column=0, sticky="e", padx=10, pady=12)
        name_entry = tk.Entry(win, font=("微软雅黑", 10), width=25)
        name_entry.grid(row=1, column=1, pady=12)

        def save():
            if not code_entry.get().strip() or not name_entry.get().strip():
                messagebox.showwarning("提示", "编码和名称不能为空！")
                return
            if inv_db.add_warehouse(code_entry.get().strip(), name_entry.get().strip(), ""):
                messagebox.showinfo("成功", "仓库添加成功！")
                win.destroy()
                self.load_basics()
            else:
                messagebox.showerror("错误", "仓库添加失败！")

        btn_row = tk.Frame(win, bg=THEME["bg_dark"])
        btn_row.grid(row=2, column=0, columnspan=2, pady=20)
        tk.Button(btn_row, text="保存", font=("微软雅黑", 10), bg=THEME["accent"], fg="white",
                 relief="flat", padx=20, pady=5, cursor="hand2", command=save).pack(side="left", padx=12)
        tk.Button(btn_row, text="取消", font=("微软雅黑", 10), bg=THEME["bg_light"], fg="white",
                 relief="flat", padx=20, pady=5, cursor="hand2", command=win.destroy).pack(side="left", padx=12)

    # ══════════════════════════════════════════
    # 数据备份管理
    # ══════════════════════════════════════════
    def load_backup(self):
        self.current_view = self.load_backup
        self._clear_content()
        self._section_title(self.content, "数据备份", "数据库备份与恢复")

        btn_frame = tk.Frame(self.content, bg="#F0F4F8")
        btn_frame.pack(fill="x", padx=20, pady=10)

        tk.Button(btn_frame, text="立即备份", font=("微软雅黑", 11, "bold"),
                 bg=THEME["success"], fg="white", relief="flat",
                 padx=20, pady=8, cursor="hand2",
                 command=self._do_backup).pack(side="left", padx=10)

        tk.Button(btn_frame, text="导出Excel", font=("微软雅黑", 11),
                 bg=THEME["accent"], fg="white", relief="flat",
                 padx=20, pady=8, cursor="hand2",
                 command=self._do_export).pack(side="left", padx=10)

        tk.Button(btn_frame, text="刷新列表", font=("微软雅黑", 11),
                 bg="#6C757D", fg="white", relief="flat",
                 padx=20, pady=8, cursor="hand2",
                 command=self.load_backup).pack(side="left", padx=10)

        self._section_title(self.content, "备份文件列表", "自动保留最近30天的备份")

        columns = ["#", "文件名", "大小", "创建时间"]
        col_widths = [50, 300, 120, 180]
        self._backup_tree = self._build_table(
            self.content, columns, col_widths,
            self._get_backup_files_data, height=14
        )

        btn_row = tk.Frame(self.content, bg="#F0F4F8")
        btn_row.pack(fill="x", padx=20, pady=10)
        tk.Button(btn_row, text="恢复选中备份", font=("微软雅黑", 11),
                 bg=THEME["warn"], fg="white", relief="flat",
                 padx=20, pady=8, cursor="hand2",
                 command=self._restore_backup).pack(side="left", padx=10)
        tk.Button(btn_row, text="打开备份目录", font=("微软雅黑", 11),
                 bg=THEME["accent"], fg="white", relief="flat",
                 padx=20, pady=8, cursor="hand2",
                 command=self._open_backup_folder).pack(side="left", padx=10)

        info_text = """
        【备份说明】
        • 备份文件保存在: inventory_backups 文件夹
        • 自动保留最近30天的备份文件
        • 建议定期手动备份重要数据
        • 恢复操作会覆盖当前数据，请谨慎操作
        """
        tk.Label(self.content, text=info_text, font=("微软雅黑", 10),
                bg="#F0F4F8", fg="#666", justify="left").pack(anchor="w", padx=20, pady=10)

    def _get_backup_files_data(self):
        try:
            files = get_backup_files()
        except:
            return []
        result = []
        for i, f in enumerate(files, 1):
            size_str = self._format_size(f.get('size', 0))
            created_str = f.get('created', datetime.now()).strftime('%Y-%m-%d %H:%M:%S')
            result.append([i, f.get('filename', ''), size_str, created_str])
        return result

    def _format_size(self, size):
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f} GB"

    def _do_backup(self):
        def backup_thread():
            result = backup_database()
            self.after(0, lambda: self._show_backup_result(result))
        threading.Thread(target=backup_thread, daemon=True).start()

    def _do_export(self):
        def export_thread():
            result = export_to_excel()
            self.after(0, lambda: self._show_backup_result(result))
        threading.Thread(target=export_thread, daemon=True).start()

    def _show_backup_result(self, result):
        if result.get('success'):
            messagebox.showinfo("成功", result.get('message', '操作成功'))
            self.load_backup()
        else:
            messagebox.showerror("错误", result.get('message', '操作失败'))

    def _restore_backup(self):
        selected = self._backup_tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选择要恢复的备份文件！")
            return

        item = self._backup_tree.item(selected[0])
        values = item.get('values', [])
        if not values:
            return

        filename = values[1]
        files = get_backup_files()
        selected_file = next((f for f in files if f.get('filename') == filename), None)

        if not selected_file:
            messagebox.showerror("错误", "找不到选中的备份文件！")
            return

        confirm = messagebox.askyesno("确认恢复",
            f"确定要恢复数据库吗？\n\n此操作将覆盖当前所有数据！\n\n备份文件: {filename}\n\n建议：在恢复前先手动备份当前数据。")
        if not confirm:
            return

        def restore_thread():
            result = restore_database(selected_file.get('filepath'))
            self.after(0, lambda: self._show_backup_result(result))
        threading.Thread(target=restore_thread, daemon=True).start()

    def _open_backup_folder(self):
        backup_dir = get_backup_dir()
        if os.path.exists(backup_dir):
            os.startfile(backup_dir)
        else:
            messagebox.showinfo("提示", f"备份目录不存在: {backup_dir}")

    # ═════════════════════════════════════════=
    # 打印管理
    # ══════════════════════════════════════════
    def load_print(self):
        self.current_view = self.load_print
        self._clear_content()
        self._section_title(self.content, "打印管理", "库存报表打印")

        btn_frame = tk.Frame(self.content, bg="#F0F4F8")
        btn_frame.pack(fill="x", padx=20, pady=15)

        print_frame = tk.LabelFrame(btn_frame, text="报表打印", font=("微软雅黑", 11, "bold"),
                                   bg="#F0F4F8", fg=THEME["header_bg"])
        print_frame.pack(side="left", padx=10)

        tk.Button(print_frame, text="📊 打印库存报表", font=("微软雅黑", 11, "bold"),
                 bg=THEME["accent"], fg="white", relief="flat",
                 padx=20, pady=10, cursor="hand2",
                 command=self._print_inventory_report).pack(side="left", padx=5, pady=5)

        tk.Button(print_frame, text="📥 打印入库单", font=("微软雅黑", 11, "bold"),
                 bg=THEME["success"], fg="white", relief="flat",
                 padx=20, pady=10, cursor="hand2",
                 command=self._print_last_inbound).pack(side="left", padx=5, pady=5)

        tk.Button(print_frame, text="📤 打印出库单", font=("微软雅黑", 11, "bold"),
                 bg=THEME["warn"], fg="white", relief="flat",
                 padx=20, pady=10, cursor="hand2",
                 command=self._print_last_outbound).pack(side="left", padx=5, pady=5)

        preview_frame = tk.LabelFrame(btn_frame, text="预览导出", font=("微软雅黑", 11, "bold"),
                                     bg="#F0F4F8", fg=THEME["header_bg"])
        preview_frame.pack(side="left", padx=10)

        tk.Button(preview_frame, text="👁 预览库存报表", font=("微软雅黑", 11),
                 bg="#6C757D", fg="white", relief="flat",
                 padx=20, pady=10, cursor="hand2",
                 command=self._preview_inventory_report).pack(side="left", padx=5, pady=5)

        tk.Button(preview_frame, text="👁 预览入库单", font=("微软雅黑", 11),
                 bg="#6C757D", fg="white", relief="flat",
                 padx=20, pady=10, cursor="hand2",
                 command=self._preview_last_inbound).pack(side="left", padx=5, pady=5)

        tk.Button(preview_frame, text="👁 预览出库单", font=("微软雅黑", 11),
                 bg="#6C757D", fg="white", relief="flat",
                 padx=20, pady=10, cursor="hand2",
                 command=self._preview_last_outbound).pack(side="left", padx=5, pady=5)

        company_frame = tk.LabelFrame(self.content, text="公司信息设置", font=("微软雅黑", 11, "bold"),
                                     bg="#F0F4F8", fg=THEME["header_bg"])
        company_frame.pack(fill="x", padx=20, pady=10)

        info_inner = tk.Frame(company_frame, bg="#F0F4F8")
        info_inner.pack(fill="x", padx=10, pady=10)

        tk.Label(info_inner, text="公司名称:", font=("微软雅黑", 10), bg="#F0F4F8").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self._company_name_entry = tk.Entry(info_inner, font=("微软雅黑", 10), width=30)
        self._company_name_entry.grid(row=0, column=1, padx=5, pady=5)
        self._company_name_entry.insert(0, "宁津晨圣输送机械有限公司")

        tk.Label(info_inner, text="地址:", font=("微软雅黑", 10), bg="#F0F4F8").grid(row=0, column=2, sticky="e", padx=5, pady=5)
        self._company_addr_entry = tk.Entry(info_inner, font=("微软雅黑", 10), width=35)
        self._company_addr_entry.grid(row=0, column=3, padx=5, pady=5)
        self._company_addr_entry.insert(0, "山东省德州市宁津县")

        tk.Label(info_inner, text="电话:", font=("微软雅黑", 10), bg="#F0F4F8").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self._company_phone_entry = tk.Entry(info_inner, font=("微软雅黑", 10), width=30)
        self._company_phone_entry.grid(row=1, column=1, padx=5, pady=5)
        self._company_phone_entry.insert(0, os.getenv('COMPANY_PHONE', ''))

        tk.Button(info_inner, text="💾 保存设置", font=("微软雅黑", 10, "bold"),
                 bg=THEME["success"], fg="white", relief="flat",
                 padx=15, pady=5, cursor="hand2",
                 command=self._save_company_info).grid(row=1, column=2, padx=10, pady=5)

        info_text = """
        【打印说明】
        • 点击打印按钮将直接调用浏览器打印
        • 点击预览按钮将保存HTML文件到下载目录
        • 可在浏览器中导出PDF格式
        • 建议使用Chrome或Edge浏览器获得最佳打印效果
        """
        tk.Label(self.content, text=info_text, font=("微软雅黑", 10),
                bg="#F0F4F8", fg="#666", justify="left").pack(anchor="w", padx=20, pady=10)

    def _print_inventory_report(self):
        try:
            stats = inv_db.get_statistics()
            inventory = inv_db.get_all_inventory()
            self._preview_inventory_file({"stats": stats, "inventory": inventory})
        except Exception as e:
            messagebox.showerror("错误", f"生成库存报表失败：\n{str(e)}")

    def _preview_inventory_file(self, data):
        try:
            from inventory_print import generate_inventory_report_html, preview_in_browser
            html = generate_inventory_report_html(data)
            filepath = preview_in_browser(html, "库存报表预览")
            if filepath:
                messagebox.showinfo("成功", "已打开打印预览，请直接在浏览器中点击「打印」按钮。")
            return filepath
        except Exception as e:
            messagebox.showerror("错误", f"预览失败：\n{str(e)}")
            return None

    def _print_last_inbound(self):
        try:
            trans = inv_db.get_inventory_transactions(trans_type='inbound', limit=1)
            if trans:
                t = trans[0]
                data = {
                    "order_no": t.get('trans_no', ''),
                    "date": str(t.get('trans_date', ''))[:10],
                    "supplier": t.get('supplier_name', ''),
                    "handler": t.get('operator', ''),
                    "warehouse": t.get('warehouse_name', ''),
                    "items": [{"name": t.get('product_name', ''), "spec": t.get('spec', ''),
                              "qty": float(t.get('qty', 0) or 0), "price": float(t.get('unit_price', 0) or 0),
                              "amount": float(t.get('qty', 0) or 0) * float(t.get('unit_price', 0) or 0)}],
                    "operator": t.get('operator', '')
                }
                self._preview_inbound_file(data)
            else:
                messagebox.showinfo("提示", "没有入库记录！")
        except Exception as e:
            messagebox.showerror("错误", f"生成入库单失败：\n{str(e)}")

    def _preview_inbound_file(self, data):
        try:
            from inventory_print import generate_inbound_html, preview_in_browser
            html = generate_inbound_html(data)
            filepath = preview_in_browser(html, "入库单预览")
            if filepath:
                messagebox.showinfo("成功", "已打开打印预览，请直接在浏览器中点击「打印」按钮。")
            return filepath
        except Exception as e:
            messagebox.showerror("错误", f"预览失败：\n{str(e)}")
            return None

    def _print_last_outbound(self):
        try:
            trans = inv_db.get_inventory_transactions(trans_type='outbound', limit=1)
            if trans:
                t = trans[0]
                data = {
                    "order_no": t.get('trans_no', ''),
                    "date": str(t.get('trans_date', ''))[:10],
                    "customer": t.get('customer', ''),
                    "handler": t.get('operator', ''),
                    "warehouse": t.get('warehouse_name', ''),
                    "items": [{"name": t.get('product_name', ''), "spec": t.get('spec', ''),
                              "qty": float(t.get('qty', 0) or 0), "price": float(t.get('unit_price', 0) or 0),
                              "amount": float(t.get('qty', 0) or 0) * float(t.get('unit_price', 0) or 0)}],
                    "operator": t.get('operator', '')
                }
                self._preview_outbound_file(data)
            else:
                messagebox.showinfo("提示", "没有出库记录！")
        except Exception as e:
            messagebox.showerror("错误", f"生成出库单失败：\n{str(e)}")

    def _preview_outbound_file(self, data):
        try:
            from inventory_print import generate_outbound_html, preview_in_browser
            html = generate_outbound_html(data)
            filepath = preview_in_browser(html, "出库单预览")
            if filepath:
                messagebox.showinfo("成功", "已打开打印预览，请直接在浏览器中点击「打印」按钮。")
            return filepath
        except Exception as e:
            messagebox.showerror("错误", f"预览失败：\n{str(e)}")
            return None

    def _preview_inventory_report(self):
        try:
            from inventory_print import preview_inventory_report
            stats = inv_db.get_statistics()
            inventory = inv_db.get_all_inventory()
            filepath = preview_inventory_report({"stats": stats, "inventory": inventory})
            messagebox.showinfo("成功", f"库存报表已保存到：\n{filepath}")
        except Exception as e:
            messagebox.showerror("错误", f"预览失败：\n{str(e)}")

    def _preview_last_inbound(self):
        try:
            from inventory_print import preview_inbound
            trans = inv_db.get_inventory_transactions(trans_type='inbound', limit=1)
            if trans:
                t = trans[0]
                filepath = preview_inbound({
                    "order_no": t.get('trans_no', ''),
                    "date": str(t.get('trans_date', ''))[:10],
                    "supplier": t.get('supplier_name', ''),
                    "handler": t.get('operator', ''),
                    "warehouse": t.get('warehouse_name', ''),
                    "items": [{"name": t.get('product_name', ''), "spec": t.get('spec', ''),
                              "qty": float(t.get('qty', 0) or 0), "price": float(t.get('unit_price', 0) or 0),
                              "amount": float(t.get('qty', 0) or 0) * float(t.get('unit_price', 0) or 0)}],
                    "operator": t.get('operator', '')
                })
                messagebox.showinfo("成功", f"入库单已保存到：\n{filepath}")
            else:
                messagebox.showinfo("提示", "没有入库记录！")
        except Exception as e:
            messagebox.showerror("错误", f"预览失败：\n{str(e)}")

    def _preview_last_outbound(self):
        try:
            from inventory_print import preview_outbound
            trans = inv_db.get_inventory_transactions(trans_type='outbound', limit=1)
            if trans:
                t = trans[0]
                filepath = preview_outbound({
                    "order_no": t.get('trans_no', ''),
                    "date": str(t.get('trans_date', ''))[:10],
                    "customer": t.get('customer', ''),
                    "handler": t.get('operator', ''),
                    "warehouse": t.get('warehouse_name', ''),
                    "items": [{"name": t.get('product_name', ''), "spec": t.get('spec', ''),
                              "qty": float(t.get('qty', 0) or 0), "price": float(t.get('unit_price', 0) or 0),
                              "amount": float(t.get('qty', 0) or 0) * float(t.get('unit_price', 0) or 0)}],
                    "operator": t.get('operator', '')
                })
                messagebox.showinfo("成功", f"出库单已保存到：\n{filepath}")
            else:
                messagebox.showinfo("提示", "没有出库记录！")
        except Exception as e:
            messagebox.showerror("错误", f"预览失败：\n{str(e)}")

    def _save_company_info(self):
        try:
            from inventory_print import set_company_info
            name = self._company_name_entry.get().strip()
            addr = self._company_addr_entry.get().strip()
            phone = self._company_phone_entry.get().strip()
            set_company_info(name, addr, phone)
            messagebox.showinfo("成功", "公司信息已保存！")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败：\n{str(e)}")

    # ═════════════════════════════════════════=
    # 系统设置
    # ═════════════════════════════════════════=
    def load_settings(self):
        self.current_view = self.load_settings
        self._clear_content()
        self._section_title(self.content, "系统设置", "个性化配置与连接设置")

        settings_notebook = ttk.Notebook(self.content)
        settings_notebook.pack(fill="both", expand=True, padx=20, pady=15)

        appearance_frame = ttk.Frame(settings_notebook)
        server_frame = ttk.Frame(settings_notebook)
        database_frame = ttk.Frame(settings_notebook)
        container_frame = ttk.Frame(settings_notebook)

        settings_notebook.add(appearance_frame, text="  主题与外观  ")
        settings_notebook.add(server_frame, text="  服务器连接  ")
        settings_notebook.add(database_frame, text="  数据库直连  ")
        settings_notebook.add(container_frame, text="  容器中心连接  ")

        self._build_appearance_settings(appearance_frame)
        self._build_server_settings(server_frame)
        self._build_database_settings(database_frame)
        self._build_container_settings(container_frame)

    def _build_appearance_settings(self, parent):
        inner = tk.Frame(parent, bg="#F0F4F8")
        inner.pack(fill="both", expand=True, padx=20, pady=20)

        theme_frame = tk.LabelFrame(inner, text="主题颜色", font=("微软雅黑", 11, "bold"),
                                   bg="#F0F4F8", fg=THEME["header_bg"])
        theme_frame.pack(fill="x", padx=5, pady=10)

        theme_inner = tk.Frame(theme_frame, bg="#F0F4F8")
        theme_inner.pack(fill="x", padx=10, pady=10)

        self._theme_var = tk.StringVar(value="深蓝主题")

        themes = [
            ("深蓝主题", "#1A2742", "#243454", "#3B9EFF"),
            ("深灰主题", "#2D2D2D", "#3D3D3D", "#4A9FFF"),
            ("墨绿主题", "#1A2F2A", "#243D38", "#3BFFB0"),
            ("深紫主题", "#2A1A42", "#3D2454", "#9F4FFF"),
        ]

        for i, (name, bg, mid, accent) in enumerate(themes):
            rb = tk.Radiobutton(theme_inner, text=name, variable=self._theme_var,
                               value=name, font=("微软雅黑", 10),
                               bg="#F0F4F8", activebackground="#F0F4F8",
                               command=lambda n=name, b=bg, m=mid, a=accent: self._apply_theme(b, m, a))
            rb.grid(row=i//2, column=i%2, sticky="w", padx=20, pady=5)

        custom_frame = tk.LabelFrame(inner, text="自定义颜色", font=("微软雅黑", 11, "bold"),
                                    bg="#F0F4F8", fg=THEME["header_bg"])
        custom_frame.pack(fill="x", padx=5, pady=10)

        custom_inner = tk.Frame(custom_frame, bg="#F0F4F8")
        custom_inner.pack(fill="x", padx=10, pady=10)

        tk.Label(custom_inner, text="主色调:", font=("微软雅黑", 10), bg="#F0F4F8").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self._custom_primary = tk.Entry(custom_inner, font=("微软雅黑", 10), width=15)
        self._custom_primary.grid(row=0, column=1, padx=5, pady=5)
        self._custom_primary.insert(0, "#1A2742")

        tk.Label(custom_inner, text="强调色:", font=("微软雅黑", 10), bg="#F0F4F8").grid(row=0, column=2, sticky="e", padx=5, pady=5)
        self._custom_accent = tk.Entry(custom_inner, font=("微软雅黑", 10), width=15)
        self._custom_accent.grid(row=0, column=3, padx=5, pady=5)
        self._custom_accent.insert(0, "#3B9EFF")

        tk.Button(custom_inner, text="应用自定义颜色", font=("微软雅黑", 10, "bold"),
                 bg=THEME["accent"], fg="white", relief="flat",
                 padx=15, pady=5, cursor="hand2",
                 command=self._apply_custom_colors).grid(row=0, column=4, padx=20, pady=5)

        font_frame = tk.LabelFrame(inner, text="字体设置", font=("微软雅黑", 11, "bold"),
                                   bg="#F0F4F8", fg=THEME["header_bg"])
        font_frame.pack(fill="x", padx=5, pady=10)

        font_inner = tk.Frame(font_frame, bg="#F0F4F8")
        font_inner.pack(fill="x", padx=10, pady=10)

        tk.Label(font_inner, text="界面字体:", font=("微软雅黑", 10), bg="#F0F4F8").grid(row=0, column=0, sticky="e", padx=5, pady=5)

        fonts = ["微软雅黑", "宋体", "黑体", "楷体", "Arial", "Times New Roman"]
        self._font_var = tk.StringVar(value="微软雅黑")
        font_combo = ttk.Combobox(font_inner, textvariable=self._font_var, values=fonts,
                                  font=("微软雅黑", 10), width=15, state="readonly")
        font_combo.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(font_inner, text="字体大小:", font=("微软雅黑", 10), bg="#F0F4F8").grid(row=0, column=2, sticky="e", padx=5, pady=5)
        self._font_size_var = tk.StringVar(value="11")
        font_sizes = ["9", "10", "11", "12", "13", "14", "15", "16"]
        size_combo = ttk.Combobox(font_inner, textvariable=self._font_size_var, values=font_sizes,
                                  font=("微软雅黑", 10), width=10, state="readonly")
        size_combo.grid(row=0, column=3, padx=5, pady=5)

        tk.Button(font_inner, text="应用字体", font=("微软雅黑", 10, "bold"),
                 bg=THEME["success"], fg="white", relief="flat",
                 padx=15, pady=5, cursor="hand2",
                 command=self._apply_font).grid(row=0, column=4, padx=20, pady=5)

        reset_frame = tk.Frame(inner, bg="#F0F4F8")
        reset_frame.pack(fill="x", padx=5, pady=20)

        tk.Button(reset_frame, text="重置为默认", font=("微软雅黑", 10),
                 bg="#6C757D", fg="white", relief="flat",
                 padx=20, pady=8, cursor="hand2",
                 command=self._reset_appearance).pack(side="left", padx=5)

    def _build_server_settings(self, parent):
        inner = tk.Frame(parent, bg="#F0F4F8")
        inner.pack(fill="both", expand=True, padx=20, pady=20)

        mode_frame = tk.LabelFrame(inner, text="工作模式", font=("微软雅黑", 11, "bold"),
                                   bg="#F0F4F8", fg=THEME["header_bg"])
        mode_frame.pack(fill="x", padx=5, pady=10)

        mode_inner = tk.Frame(mode_frame, bg="#F0F4F8")
        mode_inner.pack(fill="x", padx=10, pady=10)

        tk.Label(mode_inner, text="启用服务器模式:", font=("微软雅黑", 10), bg="#F0F4F8").pack(side="left", padx=5)
        self.server_mode.set(False)
        mode_switch = tk.Checkbutton(mode_inner, variable=self.server_mode, onvalue=True, offvalue=False,
                                     bg="#F0F4F8", command=self._on_server_mode_changed)
        mode_switch.pack(side="left", padx=5)
        tk.Label(mode_inner, text="(启用后从服务器获取数据，否则使用本地数据库)",
                font=("微软雅黑", 9), bg="#F0F4F8", fg="#6C757D").pack(side="left", padx=5)

        info_frame = tk.LabelFrame(inner, text="服务器连接信息", font=("微软雅黑", 11, "bold"),
                                   bg="#F0F4F8", fg=THEME["header_bg"])
        info_frame.pack(fill="x", padx=5, pady=10)

        info_inner = tk.Frame(info_frame, bg="#F0F4F8")
        info_inner.pack(fill="x", padx=10, pady=10)

        tk.Label(info_inner, text="服务器地址:", font=("微软雅黑", 10), bg="#F0F4F8").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self._server_url_entry = tk.Entry(info_inner, font=("微软雅黑", 10), width=35)
        self._server_url_entry.grid(row=0, column=1, padx=5, pady=5)
        _default_server_url = os.environ.get('INVENTORY_SERVER_URL') or self.inventory_config.get("server", {}).get("url", "")
        self._server_url_entry.insert(0, _default_server_url)

        tk.Label(info_inner, text="API密钥:", font=("微软雅黑", 10), bg="#F0F4F8").grid(row=0, column=2, sticky="e", padx=5, pady=5)
        self._api_key_entry = tk.Entry(info_inner, font=("微软雅黑", 10), width=25)
        self._api_key_entry.grid(row=0, column=3, padx=5, pady=5)
        self._api_key_entry.insert(0, self.inventory_config.get("server", {}).get("api_key", ""))

        btn_row = tk.Frame(info_inner, bg="#F0F4F8")
        btn_row.grid(row=1, column=0, columnspan=4, pady=10)

        tk.Button(btn_row, text="检查连接", font=("微软雅黑", 10, "bold"),
                 bg=THEME["accent"], fg="white", relief="flat",
                 padx=15, pady=6, cursor="hand2",
                 command=self._check_server_connection).pack(side="left", padx=5)

        tk.Button(btn_row, text="保存设置", font=("微软雅黑", 10, "bold"),
                 bg=THEME["success"], fg="white", relief="flat",
                 padx=15, pady=6, cursor="hand2",
                 command=self._save_server_settings).pack(side="left", padx=5)

        tk.Button(btn_row, text="刷新连接", font=("微软雅黑", 10),
                 bg="#6C757D", fg="white", relief="flat",
                 padx=15, pady=6, cursor="hand2",
                 command=self._refresh_server_connection).pack(side="left", padx=5)

        status_frame = tk.LabelFrame(inner, text="连接状态", font=("微软雅黑", 11, "bold"),
                                     bg="#F0F4F8", fg=THEME["header_bg"])
        status_frame.pack(fill="x", padx=5, pady=10)

        self._server_status_label = tk.Label(status_frame, text="状态: 未检查",
                                              font=("微软雅黑", 11), bg="#F0F4F8", fg="#6C757D")
        self._server_status_label.pack(padx=10, pady=15)

    def _build_container_settings(self, parent):
        inner = tk.Frame(parent, bg="#F0F4F8")
        inner.pack(fill="both", expand=True, padx=20, pady=20)

        info_frame = tk.LabelFrame(inner, text="容器中心连接信息", font=("微软雅黑", 11, "bold"),
                                   bg="#F0F4F8", fg=THEME["header_bg"])
        info_frame.pack(fill="x", padx=5, pady=10)

        info_inner = tk.Frame(info_frame, bg="#F0F4F8")
        info_inner.pack(fill="x", padx=10, pady=10)

        tk.Label(info_inner, text="容器中心地址:", font=("微软雅黑", 10), bg="#F0F4F8").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self._container_url_entry = tk.Entry(info_inner, font=("微软雅黑", 10), width=35)
        self._container_url_entry.grid(row=0, column=1, padx=5, pady=5)
        _default_container_url = os.environ.get('INVENTORY_CONTAINER_URL') or self.inventory_config.get("container", {}).get("url", "")
        self._container_url_entry.insert(0, _default_container_url)

        tk.Label(info_inner, text="容器名称:", font=("微软雅黑", 10), bg="#F0F4F8").grid(row=0, column=2, sticky="e", padx=5, pady=5)
        self._container_name_entry = tk.Entry(info_inner, font=("微软雅黑", 10), width=25)
        self._container_name_entry.grid(row=0, column=3, padx=5, pady=5)
        self._container_name_entry.insert(0, "inventory_container")

        btn_row = tk.Frame(info_inner, bg="#F0F4F8")
        btn_row.grid(row=1, column=0, columnspan=4, pady=10)

        tk.Button(btn_row, text="检查容器连接", font=("微软雅黑", 10, "bold"),
                 bg=THEME["accent"], fg="white", relief="flat",
                 padx=15, pady=6, cursor="hand2",
                 command=self._check_container_connection).pack(side="left", padx=5)

        tk.Button(btn_row, text="保存设置", font=("微软雅黑", 10, "bold"),
                 bg=THEME["success"], fg="white", relief="flat",
                 padx=15, pady=6, cursor="hand2",
                 command=self._save_container_settings).pack(side="left", padx=5)

        tk.Button(btn_row, text="刷新容器列表", font=("微软雅黑", 10),
                 bg="#6C757D", fg="white", relief="flat",
                 padx=15, pady=6, cursor="hand2",
                 command=self._refresh_container_list).pack(side="left", padx=5)

        status_frame = tk.LabelFrame(inner, text="容器状态", font=("微软雅黑", 11, "bold"),
                                     bg="#F0F4F8", fg=THEME["header_bg"])
        status_frame.pack(fill="x", padx=5, pady=10)

        self._container_status_label = tk.Label(status_frame, text="状态: 未检查",
                                                font=("微软雅黑", 11), bg="#F0F4F8", fg="#6C757D")
        self._container_status_label.pack(padx=10, pady=15)

        list_frame = tk.LabelFrame(inner, text="容器列表", font=("微软雅黑", 11, "bold"),
                                   bg="#F0F4F8", fg=THEME["header_bg"])
        list_frame.pack(fill="both", expand=True, padx=5, pady=10)

        columns = ["容器名称", "状态", "端口", "IP地址", "创建时间"]
        col_widths = [150, 80, 80, 130, 150]

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Custom.Treeview", background="white", foreground=THEME["text_dark"],
                        fieldbackground="white", font=("微软雅黑", 10), rowheight=28)
        style.configure("Custom.Treeview.Heading", background=THEME["header_bg"],
                        foreground="white", font=("微软雅黑", 10, "bold"), relief="flat")

        tree_frame = tk.Frame(list_frame, bg="#F0F4F8")
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self._container_tree = ttk.Treeview(tree_frame, columns=tuple(columns), show="headings",
                                             height=8, style="Custom.Treeview")
        for col, w in zip(columns, col_widths):
            self._container_tree.heading(col, text=col)
            self._container_tree.column(col, width=w, anchor="center", minwidth=60)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._container_tree.yview)
        self._container_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._container_tree.pack(side="left", fill="both", expand=True)

    def _build_database_settings(self, parent):
        inner = tk.Frame(parent, bg="#F0F4F8")
        inner.pack(fill="both", expand=True, padx=20, pady=20)

        mode_frame = tk.LabelFrame(inner, text="连接模式", font=("微软雅黑", 11, "bold"),
                                   bg="#F0F4F8", fg=THEME["header_bg"])
        mode_frame.pack(fill="x", padx=5, pady=10)

        mode_inner = tk.Frame(mode_frame, bg="#F0F4F8")
        mode_inner.pack(fill="x", padx=10, pady=10)

        self._db_mode_var = tk.StringVar(value="api")
        tk.Radiobutton(mode_inner, text="API模式 (通过服务器)", variable=self._db_mode_var,
                      value="api", font=("微软雅黑", 10), bg="#F0F4F8",
                      command=self._on_db_mode_changed).grid(row=0, column=0, padx=20, pady=5)
        tk.Radiobutton(mode_inner, text="直连模式 (直接连接数据库，更快)", variable=self._db_mode_var,
                      value="direct", font=("微软雅黑", 10), bg="#F0F4F8",
                      command=self._on_db_mode_changed).grid(row=0, column=1, padx=20, pady=5)

        info_frame = tk.LabelFrame(inner, text="数据库连接信息", font=("微软雅黑", 11, "bold"),
                                   bg="#F0F4F8", fg=THEME["header_bg"])
        info_frame.pack(fill="x", padx=5, pady=10)

        info_inner = tk.Frame(info_frame, bg="#F0F4F8")
        info_inner.pack(fill="x", padx=10, pady=10)

        tk.Label(info_inner, text="主机地址:", font=("微软雅黑", 10), bg="#F0F4F8").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self._db_host_entry = tk.Entry(info_inner, font=("微软雅黑", 10), width=25)
        self._db_host_entry.grid(row=0, column=1, padx=5, pady=5)
        self._db_host_entry.insert(0, self.inventory_config.get("database", {}).get("host", "localhost"))

        tk.Label(info_inner, text="端口:", font=("微软雅黑", 10), bg="#F0F4F8").grid(row=0, column=2, sticky="e", padx=5, pady=5)
        self._db_port_entry = tk.Entry(info_inner, font=("微软雅黑", 10), width=10)
        self._db_port_entry.grid(row=0, column=3, padx=5, pady=5)
        self._db_port_entry.insert(0, str(self.inventory_config.get("database", {}).get("port", 3306)))

        tk.Label(info_inner, text="用户名:", font=("微软雅黑", 10), bg="#F0F4F8").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self._db_user_entry = tk.Entry(info_inner, font=("微软雅黑", 10), width=25)
        self._db_user_entry.grid(row=1, column=1, padx=5, pady=5)
        self._db_user_entry.insert(0, self.inventory_config.get("database", {}).get("user", "root"))

        tk.Label(info_inner, text="密码:", font=("微软雅黑", 10), bg="#F0F4F8").grid(row=1, column=2, sticky="e", padx=5, pady=5)
        self._db_pass_entry = tk.Entry(info_inner, font=("微软雅黑", 10), width=15, show="*")
        self._db_pass_entry.grid(row=1, column=3, padx=5, pady=5)
        self._db_pass_entry.insert(0, self.inventory_config.get("database", {}).get("password", ""))

        tk.Label(info_inner, text="数据库名:", font=("微软雅黑", 10), bg="#F0F4F8").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self._db_name_entry = tk.Entry(info_inner, font=("微软雅黑", 10), width=25)
        self._db_name_entry.grid(row=2, column=1, padx=5, pady=5)
        self._db_name_entry.insert(0, self.inventory_config.get("database", {}).get("database", "inventory_db"))

        btn_row = tk.Frame(info_inner, bg="#F0F4F8")
        btn_row.grid(row=3, column=0, columnspan=4, pady=15)

        tk.Button(btn_row, text="测试连接", font=("微软雅黑", 10, "bold"),
                 bg=THEME["accent"], fg="white", relief="flat",
                 padx=15, pady=6, cursor="hand2",
                 command=self._test_database_connection).pack(side="left", padx=5)

        tk.Button(btn_row, text="保存设置", font=("微软雅黑", 10, "bold"),
                 bg=THEME["success"], fg="white", relief="flat",
                 padx=15, pady=6, cursor="hand2",
                 command=self._save_database_settings).pack(side="left", padx=5)

        status_frame = tk.LabelFrame(inner, text="连接状态", font=("微软雅黑", 11, "bold"),
                                     bg="#F0F4F8", fg=THEME["header_bg"])
        status_frame.pack(fill="x", padx=5, pady=10)

        self._db_status_label = tk.Label(status_frame, text="状态: 未检查",
                                          font=("微软雅黑", 11), bg="#F0F4F8", fg="#6C757D")
        self._db_status_label.pack(padx=10, pady=15)

        self._load_database_config()

    def _load_database_config(self):
        db_config = self.inventory_config.get("database", {})
        self._db_mode_var.set("direct")
        self._db_host_entry.delete(0, tk.END)
        self._db_host_entry.insert(0, db_config.get("host", os.getenv('MYSQL_HOST', 'localhost')))
        self._db_port_entry.delete(0, tk.END)
        self._db_port_entry.insert(0, str(db_config.get("port", os.getenv('MYSQL_PORT', 3306))))
        self._db_user_entry.delete(0, tk.END)
        self._db_user_entry.insert(0, db_config.get("user", os.getenv('MYSQL_USER', 'root')))
        self._db_pass_entry.delete(0, tk.END)
        self._db_pass_entry.insert(0, db_config.get("password", os.getenv('MYSQL_PASSWORD', '')))
        self._db_name_entry.delete(0, tk.END)
        self._db_name_entry.insert(0, db_config.get("database", os.getenv('MYSQL_DATABASE', 'inventory_db')))

    def _on_db_mode_changed(self):
        pass

    def _test_database_connection(self):
        try:
            import mysql.connector
            conn = mysql.connector.connect(
                host=self._db_host_entry.get().strip(),
                port=int(self._db_port_entry.get().strip()),
                user=self._db_user_entry.get().strip(),
                password=self._db_pass_entry.get().strip(),
                database=self._db_name_entry.get().strip()
            )
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM products")
            count = cursor.fetchone()[0]
            conn.close()
            self._db_status_label.configure(text=f"状态: 连接成功！ (数据库有 {count} 个商品)", fg=THEME["success"])
        except Exception as e:
            self._db_status_label.configure(text=f"状态: 连接失败 - {str(e)[:50]}", fg=THEME["danger"])

    def _save_database_settings(self):
        try:
            import json
            import sys
            
            # 获取配置文件路径
            if hasattr(sys, '_MEIPASS'):
                app_dir = os.path.dirname(sys.executable)
            else:
                app_dir = os.path.dirname(__file__)
            
            config_file = os.path.join(app_dir, "data", "inventory_config.json")
            
            # 读取现有配置
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                config = {}
            
            # 更新数据库配置
            if "database" not in config:
                config["database"] = {}
            
            config["database"]["host"] = self._db_host_entry.get().strip()
            config["database"]["port"] = int(self._db_port_entry.get().strip())
            config["database"]["user"] = self._db_user_entry.get().strip()
            config["database"]["password"] = self._db_pass_entry.get().strip()
            config["database"]["database"] = self._db_name_entry.get().strip()
            
            # 写入配置文件
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            # 更新内存中的配置
            self.inventory_config = config
            
            messagebox.showinfo("成功", "数据库设置已保存！\n需要重启程序才能生效。")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败：\n{str(e)}")

    def _apply_theme(self, bg_dark, bg_mid, accent):
        THEME["bg_dark"] = bg_dark
        THEME["bg_mid"] = bg_mid
        THEME["accent"] = accent
        self.configure(bg=THEME["bg_dark"])
        messagebox.showinfo("提示", "主题已切换，需要重启才能完全生效！")

    def _apply_custom_colors(self):
        try:
            primary = self._custom_primary.get().strip()
            accent = self._custom_accent.get().strip()
            THEME["bg_dark"] = primary
            THEME["accent"] = accent
            self.configure(bg=THEME["bg_dark"])
            messagebox.showinfo("提示", "自定义颜色已应用，需要重启才能完全生效！")
        except Exception as e:
            messagebox.showerror("错误", f"颜色格式无效：\n{str(e)}")

    def _apply_font(self):
        font_name = self._font_var.get()
        font_size = int(self._font_size_var.get())
        THEME["font_name"] = font_name
        THEME["font_size"] = font_size
        messagebox.showinfo("提示", f"字体已切换为 {font_name} {font_size}pt，需要重启才能完全生效！")

    def _reset_appearance(self):
        THEME.update({
            "bg_dark": "#1A2742",
            "bg_mid": "#243454",
            "bg_light": "#2E4070",
            "accent": "#3B9EFF",
        })
        self.configure(bg=THEME["bg_dark"])
        messagebox.showinfo("提示", "外观已重置为默认，需要重启才能完全生效！")

    def _on_server_mode_changed(self):
        if self.server_mode.get():
            self.server_api = self._init_server_api()
            if self.server_api:
                result = self.server_api.check_connection()
                if "error" not in result:
                    self._server_status_label.configure(text="服务器模式: 已启用", fg=THEME["success"])
                    messagebox.showinfo("成功", "已切换到服务器模式！\n数据将从远程服务器获取。")
                else:
                    self.server_mode.set(False)
                    self._server_status_label.configure(text="服务器模式: 连接失败", fg=THEME["danger"])
                    messagebox.showwarning("警告", "无法连接到服务器，已取消切换。")
            else:
                self.server_mode.set(False)
                messagebox.showerror("错误", "服务器配置无效！")
        else:
            self.server_api = None
            self._server_status_label.configure(text="服务器模式: 已禁用 (本地模式)", fg="#6C757D")
            messagebox.showinfo("提示", "已切换到本地数据库模式。")

    def _check_server_connection(self):
        import requests
        url = self._server_url_entry.get().strip()
        api_key = self._api_key_entry.get().strip()

        try:
            response = requests.get(f"{url}/api/health",
                                  headers={"X-API-Key": api_key},
                                  timeout=5)
            if response.status_code == 200:
                self._server_status_label.configure(text="状态: 已连接", fg=THEME["success"])
            else:
                self._server_status_label.configure(text="状态: 连接失败", fg=THEME["danger"])
        except Exception as e:
            self._server_status_label.configure(text="状态: 连接失败", fg=THEME["danger"])

    def _save_server_settings(self):
        try:
            config = {
                "server_url": self._server_url_entry.get().strip(),
                "api_key": self._api_key_entry.get().strip()
            }
            config_file = os.path.join(os.path.dirname(__file__), "server_client_config.json")
            import json
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            messagebox.showinfo("成功", "服务器设置已保存！")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败：\n{str(e)}")

    def _refresh_server_connection(self):
        self._check_server_connection()

    def _check_container_connection(self):
        import requests
        url = self._container_url_entry.get().strip()

        try:
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                self._container_status_label.configure(text="状态: 已连接", fg=THEME["success"])
            else:
                self._container_status_label.configure(text="状态: 连接失败", fg=THEME["danger"])
        except Exception as e:
            self._container_status_label.configure(text="状态: 连接失败", fg=THEME["danger"])

    def _save_container_settings(self):
        try:
            config = {
                "container_url": self._container_url_entry.get().strip(),
                "container_name": self._container_name_entry.get().strip()
            }
            config_file = os.path.join(os.path.dirname(__file__), "container_config.json")
            import json
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            messagebox.showinfo("成功", "容器中心设置已保存！")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败：\n{str(e)}")

    def _refresh_container_list(self):
        for item in self._container_tree.get_children():
            self._container_tree.delete(item)

        containers = [
            {"name": "inventory_container", "status": "running", "port": "5003", "ip": "192.168.1.32", "time": "2026-04-30 10:00:00"},
            {"name": "report_container", "status": "running", "port": "5004", "ip": "192.168.1.32", "time": "2026-04-30 10:00:00"},
        ]

        for c in containers:
            self._container_tree.insert("", "end", values=(c["name"], c["status"], c["port"], c["ip"], c["time"]))


if __name__ == "__main__":
    import traceback
    try:
        print("Starting InventoryGUI...")
        app = InventoryGUI()
        print("InventoryGUI created successfully")
        app.mainloop()
        print("Mainloop exited")
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()