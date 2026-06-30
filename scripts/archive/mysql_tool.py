# -*- coding: utf-8 -*-
"""
MySQL数据库工具 - 服务器端管理工具
功能：
1. MySQL连接测试
2. 数据库初始化（创建表结构）
3. 密码修改
4. 用户创建与读写授权
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import logging
import socket

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MySQLTool:
    """MySQL数据库管理工具"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("MySQL数据库管理工具 v1.0")
        self.root.geometry("800x600")
        self.root.resizable(True, True)

        self.pymysql = None
        self.conn = None
        self.current_config = {}

        self._create_widgets()
        self._load_defaults()
        self._import_pymysql()

    def _import_pymysql(self):
        """导入pymysql库"""
        try:
            import pymysql
            self.pymysql = pymysql
            self.log_message("✓ pymysql 模块已加载")
        except ImportError:
            self.log_message("✗ 错误：未安装 pymysql，请运行: pip install pymysql")
            messagebox.showerror("导入错误", "未安装 pymysql 模块\n请运行: pip install pymysql")
            self.pymysql = None

    def _load_defaults(self):
        """加载默认配置"""
        self.entry_host.insert(0, os.environ.get('MYSQL_HOST', ''))
        self.entry_port.insert(0, os.environ.get('MYSQL_PORT', '3306'))
        self.entry_user.insert(0, os.environ.get('MYSQL_USER', 'root'))
        self.entry_password.insert(0, os.environ.get('MYSQL_PASSWORD', ''))
        self.entry_database.insert(0, os.environ.get('MYSQL_DATABASE', 'steel_belt'))

    def _create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # === 连接配置区域 ===
        conn_frame = ttk.LabelFrame(main_frame, text="数据库连接配置", padding="10")
        conn_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        conn_frame.columnconfigure(1, weight=1)
        conn_frame.columnconfigure(3, weight=1)

        ttk.Label(conn_frame, text="主机地址:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        self.entry_host = ttk.Entry(conn_frame, width=25)
        self.entry_host.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=3)

        ttk.Label(conn_frame, text="端口:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=3)
        self.entry_port = ttk.Entry(conn_frame, width=10)
        self.entry_port.grid(row=0, column=3, sticky=tk.W, padx=5, pady=3)

        ttk.Label(conn_frame, text="用户名:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=3)
        self.entry_user = ttk.Entry(conn_frame, width=25)
        self.entry_user.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=3)

        ttk.Label(conn_frame, text="密码:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=3)
        self.entry_password = ttk.Entry(conn_frame, show="*", width=15)
        self.entry_password.grid(row=1, column=3, sticky=tk.W, padx=5, pady=3)

        ttk.Label(conn_frame, text="数据库:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=3)
        self.entry_database = ttk.Entry(conn_frame, width=25)
        self.entry_database.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5, pady=3)

        # 连接按钮
        btn_frame = ttk.Frame(conn_frame)
        btn_frame.grid(row=3, column=0, columnspan=4, pady=10)

        self.btn_connect = ttk.Button(btn_frame, text="连接数据库", command=self._connect_database)
        self.btn_connect.pack(side=tk.LEFT, padx=5)

        self.btn_disconnect = ttk.Button(btn_frame, text="断开连接", command=self._disconnect_database, state=tk.DISABLED)
        self.btn_disconnect.pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text="测试连接", command=self._test_connection).pack(side=tk.LEFT, padx=5)

        # === 功能区域 ===
        func_frame = ttk.LabelFrame(main_frame, text="功能操作", padding="10")
        func_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        func_frame.columnconfigure(0, weight=1)

        # 第一行功能按钮
        row1 = ttk.Frame(func_frame)
        row1.pack(fill=tk.X, pady=5)

        ttk.Button(row1, text="1. 初始化数据库表", command=self._init_database,
                   width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(row1, text="2. 修改Root密码", command=self._show_change_password_dialog,
                   width=20).pack(side=tk.LEFT, padx=5)

        # 第二行功能按钮
        row2 = ttk.Frame(func_frame)
        row2.pack(fill=tk.X, pady=5)

        ttk.Button(row2, text="3. 创建应用用户", command=self._show_create_user_dialog,
                   width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(row2, text="4. 授予读写权限", command=self._grant_privileges,
                   width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(row2, text="5. 撤销权限", command=self._revoke_privileges,
                   width=20).pack(side=tk.LEFT, padx=5)

        # 第三行功能按钮
        row3 = ttk.Frame(func_frame)
        row3.pack(fill=tk.X, pady=5)

        ttk.Button(row3, text="6. 查看所有用户", command=self._show_users,
                   width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(row3, text="7. 查看所有数据库", command=self._show_databases,
                   width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(row3, text="8. 查看表结构", command=self._show_tables,
                   width=20).pack(side=tk.LEFT, padx=5)

        # 第四行功能按钮
        row4 = ttk.Frame(func_frame)
        row4.pack(fill=tk.X, pady=5)

        ttk.Button(row4, text="9. 启用局域网访问", command=self._enable_remote_access,
                   width=20).pack(side=tk.LEFT, padx=5)

        # === 日志区域 ===
        log_frame = ttk.LabelFrame(main_frame, text="操作日志", padding="5")
        log_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        main_frame.rowconfigure(2, weight=1)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80,
                                                  font=("Consolas", 9))
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 状态栏
        self.status_var = tk.StringVar(value="未连接")
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var,
                                       foreground="gray")
        self.status_label.grid(row=3, column=0, columnspan=2, sticky=tk.W)

    def _get_connection_config(self):
        """获取连接配置"""
        return {
            "host": self.entry_host.get().strip(),
            "port": int(self.entry_port.get().strip() or "3306"),
            "user": self.entry_user.get().strip(),
            "password": self.entry_password.get(),
            "charset": "utf8mb4"
        }

    def _connect_database(self):
        """连接数据库"""
        if not self.pymysql:
            self.log_message("✗ pymysql 模块未安装")
            return

        try:
            config = self._get_connection_config()
            self.log_message(f"正在连接 {config['host']}:{config['port']} ...")

            self.conn = self.pymysql.connect(**config)

            # 保存当前配置
            self.current_config = config.copy()

            self.log_message("✓ 连接成功！")
            self.status_var.set(f"已连接: {config['user']}@{config['host']}")
            self.btn_connect.config(state=tk.DISABLED)
            self.btn_disconnect.config(state=tk.NORMAL)

            # 尝试选择数据库
            db_name = self.entry_database.get().strip()
            if db_name:
                try:
                    self.conn.select_db(db_name)
                    self.log_message(f"✓ 已选择数据库: {db_name}")
                except Exception as e:
                    self.log_message(f"⚠ 选择数据库失败: {e}")

        except Exception as e:
            self.log_message(f"✗ 连接失败: {e}")
            self.status_var.set("连接失败")
            messagebox.showerror("连接错误", f"连接数据库失败:\n{e}")

    def _disconnect_database(self):
        """断开连接"""
        if self.conn:
            try:
                self.conn.close()
                self.conn = None
                self.log_message("✓ 已断开连接")
                self.status_var.set("未连接")
                self.btn_connect.config(state=tk.NORMAL)
                self.btn_disconnect.config(state=tk.DISABLED)
            except Exception as e:
                self.log_message(f"✗ 断开连接失败: {e}")

    def _test_connection(self):
        """测试连接"""
        if not self.pymysql:
            self.log_message("✗ pymysql 模块未安装")
            return

        config = self._get_connection_config()
        self.log_message(f"正在测试连接 {config['host']}:{config['port']} ...")

        try:
            test_conn = self.pymysql.connect(**config)
            version = test_conn.get_server_info()
            test_conn.close()
            self.log_message(f"✓ 连接测试成功！MySQL版本: {version}")
            messagebox.showinfo("连接测试", f"连接成功！\nMySQL版本: {version}")
        except Exception as e:
            self.log_message(f"✗ 连接测试失败: {e}")
            messagebox.showerror("连接测试失败", f"连接失败:\n{e}")

    def _ensure_connection(self):
        """确保有有效连接"""
        if not self.conn:
            self.log_message("✗ 请先连接数据库")
            return False
        try:
            self.conn.ping(reconnect=True)
            return True
        except Exception as e:
            self.log_message(f"✗ 连接已断开: {e}")
            self.conn = None
            return False

    def log_message(self, message):
        """输出日志消息"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def _init_database(self):
        """初始化数据库表"""
        if not self._ensure_connection():
            return

        db_name = self.entry_database.get().strip()
        if not db_name:
            messagebox.showerror("错误", "请输入数据库名称")
            return

        threading.Thread(target=self._init_database_thread, args=(db_name,), daemon=True).start()

    def _init_database_thread(self, db_name):
        """在后台线程初始化数据库"""
        self.log_message("=" * 50)
        self.log_message("开始初始化数据库...")

        try:
            # 创建数据库
            self.log_message(f"创建数据库: {db_name}")
            with self.conn.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                self.conn.commit()
            self.log_message(f"✓ 数据库 {db_name} 已创建/已存在")

            # 选择数据库
            self.conn.select_db(db_name)
            self.log_message(f"已选择数据库: {db_name}")

            # 创建表
            tables = {
                "operators": """
                    CREATE TABLE IF NOT EXISTS operators (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        operator_id VARCHAR(50) UNIQUE NOT NULL COMMENT '工号',
                        name VARCHAR(100) NOT NULL COMMENT '姓名',
                        role VARCHAR(20) DEFAULT '操作员' COMMENT '角色',
                        password VARCHAR(255) NOT NULL COMMENT '密码哈希',
                        password_salt VARCHAR(50) COMMENT '盐值',
                        status VARCHAR(20) DEFAULT '正常' COMMENT '状态',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP NULL,
                        INDEX idx_operator_id (operator_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='操作员表'
                """,
                "orders": """
                    CREATE TABLE IF NOT EXISTS orders (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        order_no VARCHAR(50) UNIQUE NOT NULL COMMENT '订单号',
                        customer_name VARCHAR(200) COMMENT '客户名称',
                        customer_phone VARCHAR(50) COMMENT '客户电话',
                        customer_address VARCHAR(500) COMMENT '客户地址',
                        product_type VARCHAR(100) COMMENT '产品类型',
                        material VARCHAR(50) COMMENT '材质',
                        mesh_size VARCHAR(50) COMMENT '网孔尺寸',
                        wire_diameter VARCHAR(50) COMMENT '钢丝直径',
                        width DECIMAL(10,2) COMMENT '宽度',
                        length DECIMAL(10,2) COMMENT '长度',
                        quantity DECIMAL(10,2) DEFAULT 1 COMMENT '数量',
                        unit VARCHAR(20) DEFAULT '米' COMMENT '单位',
                        unit_price DECIMAL(12,2) DEFAULT 0 COMMENT '单价',
                        total_amount DECIMAL(12,2) DEFAULT 0 COMMENT '总价',
                        surface_treatment VARCHAR(100) COMMENT '表面处理',
                        special_requirements TEXT COMMENT '特殊要求',
                        delivery_date DATE COMMENT '交货日期',
                        status VARCHAR(30) DEFAULT '待确认' COMMENT '状态',
                        remark TEXT COMMENT '备注',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_order_no (order_no),
                        INDEX idx_customer (customer_name),
                        INDEX idx_status (status)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表'
                """,
                "production": """
                    CREATE TABLE IF NOT EXISTS production (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        order_id INT NOT NULL COMMENT '订单ID',
                        process_name VARCHAR(100) COMMENT '工序名称',
                        scheduled_date DATE COMMENT '计划日期',
                        actual_start TIMESTAMP NULL COMMENT '实际开始',
                        actual_end TIMESTAMP NULL COMMENT '实际结束',
                        status VARCHAR(30) DEFAULT '待开始' COMMENT '状态',
                        operator_id VARCHAR(50) COMMENT '操作员ID',
                        output_quantity DECIMAL(10,2) DEFAULT 0 COMMENT '产出数量',
                        remark TEXT COMMENT '备注',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_order_id (order_id),
                        INDEX idx_status (status),
                        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='生产记录表'
                """,
                "quality": """
                    CREATE TABLE IF NOT EXISTS quality (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        order_id INT NOT NULL COMMENT '订单ID',
                        check_date DATE COMMENT '检验日期',
                        inspector VARCHAR(100) COMMENT '检验员',
                        quantity_checked DECIMAL(10,2) DEFAULT 0 COMMENT '检验数量',
                        qualified_quantity DECIMAL(10,2) DEFAULT 0 COMMENT '合格数量',
                        defective_quantity DECIMAL(10,2) DEFAULT 0 COMMENT '不合格数量',
                        defect_type VARCHAR(200) COMMENT '不合格类型',
                        result VARCHAR(20) DEFAULT '待检' COMMENT '检验结果',
                        remark TEXT COMMENT '备注',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_order_id (order_id),
                        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='质检记录表'
                """,
                "shipments": """
                    CREATE TABLE IF NOT EXISTS shipments (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        order_id INT NOT NULL COMMENT '订单ID',
                        shipment_no VARCHAR(50) UNIQUE NOT NULL COMMENT '发货单号',
                        shipment_date DATE COMMENT '发货日期',
                        quantity DECIMAL(10,2) COMMENT '发货数量',
                        recipient_name VARCHAR(100) COMMENT '收货人',
                        recipient_phone VARCHAR(50) COMMENT '收货电话',
                        recipient_address VARCHAR(500) COMMENT '收货地址',
                        tracking_no VARCHAR(100) COMMENT '物流单号',
                        status VARCHAR(30) DEFAULT '待发货' COMMENT '状态',
                        remark TEXT COMMENT '备注',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_order_id (order_id),
                        INDEX idx_shipment_no (shipment_no),
                        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='发货记录表'
                """,
                "inventory": """
                    CREATE TABLE IF NOT EXISTS inventory (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        material_code VARCHAR(50) COMMENT '物料编码',
                        material_name VARCHAR(200) COMMENT '物料名称',
                        category VARCHAR(50) COMMENT '分类',
                        quantity DECIMAL(10,2) DEFAULT 0 COMMENT '数量',
                        unit VARCHAR(20) COMMENT '单位',
                        location VARCHAR(100) COMMENT '存放位置',
                        min_stock DECIMAL(10,2) DEFAULT 0 COMMENT '最低库存',
                        max_stock DECIMAL(10,2) DEFAULT 0 COMMENT '最高库存',
                        status VARCHAR(20) DEFAULT '在库' COMMENT '状态',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_material_code (material_code),
                        INDEX idx_category (category)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='库存表'
                """,
                "operation_logs": """
                    CREATE TABLE IF NOT EXISTS operation_logs (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        operator VARCHAR(100) COMMENT '操作员',
                        action VARCHAR(100) NOT NULL COMMENT '操作类型',
                        entity_type VARCHAR(50) COMMENT '实体类型',
                        entity_id VARCHAR(50) COMMENT '实体ID',
                        before_data TEXT COMMENT '操作前数据',
                        after_data TEXT COMMENT '操作后数据',
                        ip_address VARCHAR(50) COMMENT 'IP地址',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_operator (operator),
                        INDEX idx_created (created_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='操作日志表'
                """,
                "product_types": """
                    CREATE TABLE IF NOT EXISTS product_types (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(50) UNIQUE NOT NULL,
                        is_preset TINYINT(1) DEFAULT 0,
                        created_at DATETIME DEFAULT NOW()
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='产品类型表'
                """,
                "material_densities": """
                    CREATE TABLE IF NOT EXISTS material_densities (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        material_name VARCHAR(50) NOT NULL,
                        density DECIMAL(10,4) DEFAULT 7.85,
                        unit VARCHAR(20) DEFAULT 'g/cm³',
                        created_at DATETIME DEFAULT NOW()
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='材料密度表'
                """,
                "custom_dim_params": """
                    CREATE TABLE IF NOT EXISTS custom_dim_params (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        product_type VARCHAR(50) NOT NULL,
                        param_key VARCHAR(50) NOT NULL,
                        param_label VARCHAR(100),
                        param_unit VARCHAR(20),
                        param_group VARCHAR(50),
                        required TINYINT(1) DEFAULT 0,
                        created_at DATETIME DEFAULT NOW(),
                        UNIQUE(product_type, param_key)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='自定义尺寸参数表'
                """,
                "custom_mat_params": """
                    CREATE TABLE IF NOT EXISTS custom_mat_params (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        product_type VARCHAR(50) NOT NULL,
                        param_key VARCHAR(50) NOT NULL,
                        param_label VARCHAR(100),
                        param_group VARCHAR(50),
                        options_json TEXT,
                        created_at DATETIME DEFAULT NOW(),
                        UNIQUE(product_type, param_key)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='自定义材质参数表'
                """,
                "order_templates": """
                    CREATE TABLE IF NOT EXISTS order_templates (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        product_type VARCHAR(50) NOT NULL,
                        template_name VARCHAR(50) NOT NULL,
                        values_json TEXT,
                        order_json TEXT,
                        created_at DATETIME DEFAULT NOW(),
                        updated_at DATETIME DEFAULT NOW(),
                        UNIQUE(product_type, template_name)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单模板表'
                """,
                "custom_params": """
                    CREATE TABLE IF NOT EXISTS custom_params (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        params_json TEXT,
                        created_at DATETIME DEFAULT NOW(),
                        updated_at DATETIME DEFAULT NOW()
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='自定义参数表'
                """,
                "material_templates": """
                    CREATE TABLE IF NOT EXISTS material_templates (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(50) UNIQUE NOT NULL,
                        description TEXT,
                        materials_json TEXT,
                        created_at DATETIME DEFAULT NOW(),
                        updated_at DATETIME DEFAULT NOW()
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='材质模板表'
                """,
                "process_templates": """
                    CREATE TABLE IF NOT EXISTS process_templates (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(50) UNIQUE NOT NULL,
                        data_json TEXT,
                        created_at DATETIME DEFAULT NOW(),
                        updated_at DATETIME DEFAULT NOW()
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工序模板表'
                """,
                "process_calc_rules": """
                    CREATE TABLE IF NOT EXISTS process_calc_rules (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        rule_name VARCHAR(100) NOT NULL,
                        product_types_json TEXT,
                        condition_expr TEXT,
                        planned_qty_formula TEXT,
                        priority INT DEFAULT 5,
                        enabled TINYINT(1) DEFAULT 1,
                        created_at DATETIME DEFAULT NOW()
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工序计算规则表'
                """,
                "quality_rules": """
                    CREATE TABLE IF NOT EXISTS quality_rules (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        rule_name VARCHAR(100) NOT NULL,
                        product_types_json TEXT,
                        condition_expr TEXT,
                        inspection_items_json TEXT,
                        check_formula TEXT,
                        priority INT DEFAULT 5,
                        enabled TINYINT(1) DEFAULT 1,
                        created_at DATETIME DEFAULT NOW()
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='质检规则表'
                """,
                "material_rules": """
                    CREATE TABLE IF NOT EXISTS material_rules (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        product_type VARCHAR(50) NOT NULL,
                        material_param VARCHAR(50) NOT NULL,
                        material_name_template VARCHAR(100) NOT NULL,
                        spec_field VARCHAR(50),
                        spec_unit VARCHAR(20),
                        qty_field VARCHAR(50),
                        created_at DATETIME DEFAULT NOW(),
                        UNIQUE(product_type, material_param)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='材质规则表'
                """,
                "material_rules_templates": """
                    CREATE TABLE IF NOT EXISTS material_rules_templates (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(50) UNIQUE NOT NULL,
                        data_json TEXT,
                        created_at DATETIME DEFAULT NOW(),
                        updated_at DATETIME DEFAULT NOW()
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='材质规则模板表'
                """,
                "process_rules_templates": """
                    CREATE TABLE IF NOT EXISTS process_rules_templates (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(50) UNIQUE NOT NULL,
                        product_type VARCHAR(50) DEFAULT '',
                        conditions_json TEXT,
                        actions_json TEXT,
                        priority INT DEFAULT 5,
                        description TEXT,
                        created_at DATETIME DEFAULT NOW()
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工序规则模板表'
                """,
                "production_orders": """
                    CREATE TABLE IF NOT EXISTS production_orders (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        order_id INT NOT NULL,
                        process_name VARCHAR(100),
                        scheduled_date DATE,
                        actual_start DATETIME,
                        actual_end DATETIME,
                        status VARCHAR(30) DEFAULT '待开始',
                        operator_id VARCHAR(50),
                        output_quantity DECIMAL(10,2) DEFAULT 0,
                        remark TEXT,
                        created_at DATETIME DEFAULT NOW(),
                        INDEX idx_order_id (order_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='生产工序表'
                """,
                "inventory_records": """
                    CREATE TABLE IF NOT EXISTS inventory_records (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        inventory_id INT NOT NULL,
                        change_type VARCHAR(30),
                        quantity_change DECIMAL(10,2),
                        before_quantity DECIMAL(10,2),
                        after_quantity DECIMAL(10,2),
                        operator VARCHAR(100),
                        remark TEXT,
                        created_at DATETIME DEFAULT NOW(),
                        INDEX idx_inventory_id (inventory_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='库存记录表'
                """,
                "process_records": """
                    CREATE TABLE IF NOT EXISTS process_records (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        production_order_id INT NOT NULL,
                        process_name VARCHAR(100),
                        start_time DATETIME,
                        end_time DATETIME,
                        output_quantity DECIMAL(10,2),
                        operator_id VARCHAR(50),
                        status VARCHAR(30),
                        remark TEXT,
                        created_at DATETIME DEFAULT NOW(),
                        INDEX idx_production_order_id (production_order_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工序记录表'
                """,
                "quality_records": """
                    CREATE TABLE IF NOT EXISTS quality_records (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        order_id INT NOT NULL,
                        check_date DATE,
                        inspector VARCHAR(100),
                        quantity_checked DECIMAL(10,2),
                        qualified_quantity DECIMAL(10,2),
                        defective_quantity DECIMAL(10,2),
                        defect_type VARCHAR(200),
                        result VARCHAR(20) DEFAULT '待检',
                        remark TEXT,
                        created_at DATETIME DEFAULT NOW(),
                        INDEX idx_order_id (order_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='质检记录表'
                """,
                "finished_goods": """
                    CREATE TABLE IF NOT EXISTS finished_goods (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        order_id INT,
                        product_name VARCHAR(200),
                        quantity DECIMAL(10,2),
                        unit VARCHAR(20),
                        warehouse_location VARCHAR(100),
                        status VARCHAR(20) DEFAULT '在库',
                        created_at DATETIME DEFAULT NOW()
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='成品库存表'
                """,
                "shipment_tracks": """
                    CREATE TABLE IF NOT EXISTS shipment_tracks (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        shipment_id INT NOT NULL,
                        track_time DATETIME,
                        location VARCHAR(200),
                        status VARCHAR(50),
                        remark TEXT,
                        created_at DATETIME DEFAULT NOW(),
                        INDEX idx_shipment_id (shipment_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='发货跟踪表'
                """,
                "status_logs": """
                    CREATE TABLE IF NOT EXISTS status_logs (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        entity_type VARCHAR(50),
                        entity_id VARCHAR(50),
                        old_status VARCHAR(30),
                        new_status VARCHAR(30),
                        operator VARCHAR(100),
                        change_time DATETIME DEFAULT NOW(),
                        remark TEXT
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='状态变更日志表'
                """,
                "order_logs": """
                    CREATE TABLE IF NOT EXISTS order_logs (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        order_id INT NOT NULL,
                        action VARCHAR(50),
                        old_value TEXT,
                        new_value TEXT,
                        operator VARCHAR(100),
                        created_at DATETIME DEFAULT NOW(),
                        INDEX idx_order_id (order_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单日志表'
                """,
                "order_materials": """
                    CREATE TABLE IF NOT EXISTS order_materials (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        order_id INT NOT NULL,
                        material_name VARCHAR(100),
                        material_spec VARCHAR(100),
                        quantity DECIMAL(10,2),
                        unit VARCHAR(20),
                        remark TEXT,
                        created_at DATETIME DEFAULT NOW(),
                        INDEX idx_order_id (order_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单物料表'
                """,
                "material_history": """
                    CREATE TABLE IF NOT EXISTS material_history (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        material_code VARCHAR(50),
                        change_type VARCHAR(30),
                        quantity_change DECIMAL(10,2),
                        before_quantity DECIMAL(10,2),
                        after_quantity DECIMAL(10,2),
                        operator VARCHAR(100),
                        created_at DATETIME DEFAULT NOW(),
                        INDEX idx_material_code (material_code)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='物料历史表'
                """,
                "bom_list": """
                    CREATE TABLE IF NOT EXISTS bom_list (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        product_type VARCHAR(50) NOT NULL,
                        material VARCHAR(50) NOT NULL,
                        steel_weight DECIMAL(10,2) DEFAULT 0,
                        steel_unit VARCHAR(10) DEFAULT 'kg/米',
                        packaging_materials TEXT,
                        surface_treatment TEXT,
                        created_at DATETIME DEFAULT NOW(),
                        UNIQUE(product_type, material)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='BOM清单表'
                """,
                "alert_records": """
                    CREATE TABLE IF NOT EXISTS alert_records (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        alert_type VARCHAR(50),
                        alert_level VARCHAR(20),
                        title VARCHAR(200),
                        content TEXT,
                        entity_type VARCHAR(50),
                        entity_id VARCHAR(50),
                        is_read TINYINT(1) DEFAULT 0,
                        created_at DATETIME DEFAULT NOW()
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='预警记录表'
                """,
                "operator_logs": """
                    CREATE TABLE IF NOT EXISTS operator_logs (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        operator_id VARCHAR(50),
                        action VARCHAR(100),
                        ip_address VARCHAR(50),
                        created_at DATETIME DEFAULT NOW(),
                        INDEX idx_operator_id (operator_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='操作员日志表'
                """,
                "production_stats": """
                    CREATE TABLE IF NOT EXISTS production_stats (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        stat_date DATE,
                        total_orders INT DEFAULT 0,
                        completed_orders INT DEFAULT 0,
                        pending_orders INT DEFAULT 0,
                        total_output DECIMAL(10,2) DEFAULT 0,
                        qualified_output DECIMAL(10,2) DEFAULT 0,
                        created_at DATETIME DEFAULT NOW()
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='生产统计表'
                """,
                "quality_record_items": """
                    CREATE TABLE IF NOT EXISTS quality_record_items (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        quality_record_id INT NOT NULL,
                        item_name VARCHAR(100),
                        check_value VARCHAR(100),
                        is_qualified TINYINT(1),
                        remark TEXT,
                        INDEX idx_quality_record_id (quality_record_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='质检记录项表'
                """,
                "process_rules": """
                    CREATE TABLE IF NOT EXISTS process_rules (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        rule_name VARCHAR(100) NOT NULL,
                        product_type VARCHAR(50) DEFAULT '',
                        conditions_json TEXT,
                        actions_json TEXT,
                        priority INT DEFAULT 5,
                        description TEXT,
                        created_at DATETIME DEFAULT NOW()
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工序规则表'
                """
            }

            for table_name, create_sql in tables.items():
                self.log_message(f"创建表: {table_name}")
                with self.conn.cursor() as cursor:
                    cursor.execute(create_sql)
                self.conn.commit()
                self.log_message(f"✓ 表 {table_name} 已创建/已存在")

            # 初始化预设产品类型
            self.log_message("初始化预设数据...")
            try:
                with self.conn.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM product_types")
                    if cursor.fetchone()[0] == 0:
                        preset_types = ["眼镜网带", "人字形网带", "乙字形网带", "平板型网带", "链板式网带", "冷冻螺旋网"]
                        for name in preset_types:
                            cursor.execute("INSERT INTO product_types (name, is_preset) VALUES (%s, 1)", (name,))
                        self.conn.commit()
                        self.log_message(f"✓ 已添加 {len(preset_types)} 个预设产品类型")

                    # 初始化预设材质
                    cursor.execute("SELECT COUNT(*) FROM material_densities")
                    if cursor.fetchone()[0] == 0:
                        materials = [
                            ("304不锈钢", 7.93), ("316不锈钢", 7.98), ("316L不锈钢", 7.95),
                            ("310S不锈钢", 7.98), ("201不锈钢", 7.93), ("碳钢镀锌", 7.85),
                            ("铝合金", 2.7), ("铜合金", 8.9), ("钛合金", 4.5)
                        ]
                        for name, density in materials:
                            cursor.execute("INSERT INTO material_densities (material_name, density) VALUES (%s, %s)", (name, density))
                        self.conn.commit()
                        self.log_message(f"✓ 已添加 {len(materials)} 种预设材质密度")
            except Exception as e:
                self.log_message(f"⚠ 预设数据初始化跳过: {e}")

            self.log_message("=" * 50)
            self.log_message("✓ 数据库初始化完成！")
            messagebox.showinfo("成功", "数据库初始化完成！")

        except Exception as e:
            self.log_message(f"✗ 初始化失败: {e}")
            messagebox.showerror("错误", f"初始化失败:\n{e}")

    def _show_change_password_dialog(self):
        """显示修改密码对话框"""
        if not self._ensure_connection():
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("修改MySQL用户密码")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="用户名:").grid(row=0, column=0, sticky=tk.W, pady=5)
        entry_user = ttk.Entry(frame, width=30)
        entry_user.insert(0, self.entry_user.get())
        entry_user.grid(row=0, column=1, pady=5)

        ttk.Label(frame, text="新密码:").grid(row=1, column=0, sticky=tk.W, pady=5)
        entry_new_pass = ttk.Entry(frame, show="*", width=30)
        entry_new_pass.grid(row=1, column=1, pady=5)

        ttk.Label(frame, text="确认密码:").grid(row=2, column=0, sticky=tk.W, pady=5)
        entry_confirm = ttk.Entry(frame, show="*", width=30)
        entry_confirm.grid(row=2, column=1, pady=5)

        def do_change():
            username = entry_user.get().strip()
            new_pass = entry_new_pass.get()
            confirm = entry_confirm.get()

            if not username or not new_pass:
                messagebox.showerror("错误", "请填写所有字段")
                return

            if new_pass != confirm:
                messagebox.showerror("错误", "两次输入的密码不一致")
                return

            try:
                with self.conn.cursor() as cursor:
                    cursor.execute(f"ALTER USER '{username}'@'%' IDENTIFIED BY %s", (new_pass,))
                    cursor.execute("FLUSH PRIVILEGES")
                self.conn.commit()
                self.log_message(f"✓ 用户 {username} 的密码已修改")
                messagebox.showinfo("成功", f"用户 {username} 的密码已修改")
                dialog.destroy()
            except Exception as e:
                # 尝试使用旧语法
                try:
                    with self.conn.cursor() as cursor:
                        cursor.execute(f"SET PASSWORD FOR '{username}'@'%' = PASSWORD(%s)", (new_pass,))
                        cursor.execute("FLUSH PRIVILEGES")
                    self.conn.commit()
                    self.log_message(f"✓ 用户 {username} 的密码已修改（使用旧语法）")
                    messagebox.showinfo("成功", f"用户 {username} 的密码已修改")
                    dialog.destroy()
                except Exception as e2:
                    self.log_message(f"✗ 修改密码失败: {e2}")
                    messagebox.showerror("错误", f"修改密码失败:\n{e2}")

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=20)

        ttk.Button(btn_frame, text="确定", command=do_change).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=10)

    def _show_create_user_dialog(self):
        """显示创建用户对话框"""
        if not self._ensure_connection():
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("创建MySQL用户")
        dialog.geometry("450x280")
        dialog.transient(self.root)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="用户名:").grid(row=0, column=0, sticky=tk.W, pady=5)
        entry_username = ttk.Entry(frame, width=30)
        entry_username.grid(row=0, column=1, pady=5)

        ttk.Label(frame, text="密码:").grid(row=1, column=0, sticky=tk.W, pady=5)
        entry_password = ttk.Entry(frame, show="*", width=30)
        entry_password.grid(row=1, column=1, pady=5)

        ttk.Label(frame, text="允许访问的主机:").grid(row=2, column=0, sticky=tk.W, pady=5)
        combo_host = ttk.Combobox(frame, width=28, values=['%', 'localhost', '192.168.%', '指定IP'])
        combo_host.current(0)
        combo_host.grid(row=2, column=1, pady=5)

        ttk.Label(frame, text="授权访问的数据库:").grid(row=3, column=0, sticky=tk.W, pady=5)
        entry_database = ttk.Entry(frame, width=30)
        entry_database.insert(0, self.entry_database.get().strip())
        entry_database.grid(row=3, column=1, pady=5)

        ttk.Label(frame, text="权限类型:").grid(row=4, column=0, sticky=tk.W, pady=5)
        combo_privilege = ttk.Combobox(frame, width=28, values=['读写权限 (SELECT,INSERT,UPDATE,DELETE)', '只读权限 (SELECT)', '所有权限 (ALL PRIVILEGES)'])
        combo_privilege.current(0)
        combo_privilege.grid(row=4, column=1, pady=5)

        def do_create():
            username = entry_username.get().strip()
            password = entry_password.get()
            host = combo_host.get()
            database = entry_database.get().strip()
            privilege_type = combo_privilege.current()

            if not username or not password:
                messagebox.showerror("错误", "请填写用户名和密码")
                return

            if not database:
                messagebox.showerror("错误", "请输入数据库名称")
                return

            # 确定权限
            if privilege_type == 0:
                privileges = "SELECT, INSERT, UPDATE, DELETE"
            elif privilege_type == 1:
                privileges = "SELECT"
            else:
                privileges = "ALL PRIVILEGES"

            try:
                with self.conn.cursor() as cursor:
                    # 创建用户
                    cursor.execute(f"CREATE USER IF NOT EXISTS '{username}'@'{host}' IDENTIFIED BY %s", (password,))
                    # 授予权限
                    cursor.execute(f"GRANT {privileges} ON `{database}`.* TO '{username}'@'{host}'")
                    cursor.execute("FLUSH PRIVILEGES")
                self.conn.commit()

                self.log_message(f"✓ 用户 {username} 已创建并授予 {database} 的 {privileges}")
                messagebox.showinfo("成功", f"用户 {username} 已创建！\n已授予 {database} 数据库的 {privileges}")
                dialog.destroy()
            except Exception as e:
                self.log_message(f"✗ 创建用户失败: {e}")
                messagebox.showerror("错误", f"创建用户失败:\n{e}")

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=20)

        ttk.Button(btn_frame, text="创建", command=do_create).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=10)

    def _grant_privileges(self):
        """授予数据库权限"""
        if not self._ensure_connection():
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("授予数据库权限")
        dialog.geometry("400x220")
        dialog.transient(self.root)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="用户名:").grid(row=0, column=0, sticky=tk.W, pady=5)
        entry_user = ttk.Entry(frame, width=30)
        entry_user.grid(row=0, column=1, pady=5)

        ttk.Label(frame, text="主机:").grid(row=1, column=0, sticky=tk.W, pady=5)
        entry_host = ttk.Entry(frame, width=30)
        entry_host.insert(0, "%")
        entry_host.grid(row=1, column=1, pady=5)

        ttk.Label(frame, text="数据库:").grid(row=2, column=0, sticky=tk.W, pady=5)
        entry_db = ttk.Entry(frame, width=30)
        entry_db.insert(0, self.entry_database.get().strip())
        entry_db.grid(row=2, column=1, pady=5)

        ttk.Label(frame, text="权限:").grid(row=3, column=0, sticky=tk.W, pady=5)
        combo_priv = ttk.Combobox(frame, width=28, values=['SELECT,INSERT,UPDATE,DELETE', 'SELECT', 'ALL PRIVILEGES'])
        combo_priv.current(0)
        combo_priv.grid(row=3, column=1, pady=5)

        def do_grant():
            user = entry_user.get().strip()
            host = entry_host.get().strip() or "%"
            db = entry_db.get().strip()
            privs = combo_priv.get()

            if not user or not db:
                messagebox.showerror("错误", "请填写用户名和数据库")
                return

            try:
                with self.conn.cursor() as cursor:
                    cursor.execute(f"GRANT {privs} ON `{db}`.* TO '{user}'@'{host}'")
                    cursor.execute("FLUSH PRIVILEGES")
                self.conn.commit()
                self.log_message(f"✓ 已授予 {user}@{host} 对 {db} 的 {privs} 权限")
                messagebox.showinfo("成功", f"权限授予成功！")
                dialog.destroy()
            except Exception as e:
                self.log_message(f"✗ 授权失败: {e}")
                messagebox.showerror("错误", f"授权失败:\n{e}")

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=20)

        ttk.Button(btn_frame, text="授予", command=do_grant).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=10)

    def _revoke_privileges(self):
        """撤销数据库权限"""
        if not self._ensure_connection():
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("撤销数据库权限")
        dialog.geometry("400x220")
        dialog.transient(self.root)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="用户名:").grid(row=0, column=0, sticky=tk.W, pady=5)
        entry_user = ttk.Entry(frame, width=30)
        entry_user.grid(row=0, column=1, pady=5)

        ttk.Label(frame, text="主机:").grid(row=1, column=0, sticky=tk.W, pady=5)
        entry_host = ttk.Entry(frame, width=30)
        entry_host.insert(0, "%")
        entry_host.grid(row=1, column=1, pady=5)

        ttk.Label(frame, text="数据库:").grid(row=2, column=0, sticky=tk.W, pady=5)
        entry_db = ttk.Entry(frame, width=30)
        entry_db.insert(0, self.entry_database.get().strip())
        entry_db.grid(row=2, column=1, pady=5)

        ttk.Label(frame, text="权限:").grid(row=3, column=0, sticky=tk.W, pady=5)
        combo_priv = ttk.Combobox(frame, width=28, values=['SELECT,INSERT,UPDATE,DELETE', 'SELECT', 'ALL PRIVILEGES'])
        combo_priv.current(0)
        combo_priv.grid(row=3, column=1, pady=5)

        def do_revoke():
            user = entry_user.get().strip()
            host = entry_host.get().strip() or "%"
            db = entry_db.get().strip()
            privs = combo_priv.get()

            if not user or not db:
                messagebox.showerror("错误", "请填写用户名和数据库")
                return

            try:
                with self.conn.cursor() as cursor:
                    cursor.execute(f"REVOKE {privs} ON `{db}`.* FROM '{user}'@'{host}'")
                    cursor.execute("FLUSH PRIVILEGES")
                self.conn.commit()
                self.log_message(f"✓ 已撤销 {user}@{host} 对 {db} 的 {privs} 权限")
                messagebox.showinfo("成功", f"权限撤销成功！")
                dialog.destroy()
            except Exception as e:
                self.log_message(f"✗ 撤销权限失败: {e}")
                messagebox.showerror("错误", f"撤销权限失败:\n{e}")

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=20)

        ttk.Button(btn_frame, text="撤销", command=do_revoke).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=10)

    def _enable_remote_access(self):
        """启用局域网远程访问"""
        if not self._ensure_connection():
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("启用局域网访问")
        dialog.geometry("450x300")
        dialog.transient(self.root)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="创建远程访问用户", font=("Microsoft YaHei", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=10)

        ttk.Label(frame, text="用户名:").grid(row=1, column=0, sticky=tk.W, pady=5)
        entry_user = ttk.Entry(frame, width=30)
        entry_user.grid(row=1, column=1, pady=5)

        ttk.Label(frame, text="密码:").grid(row=2, column=0, sticky=tk.W, pady=5)
        entry_pass = ttk.Entry(frame, show="*", width=30)
        entry_pass.grid(row=2, column=1, pady=5)

        ttk.Label(frame, text="授权数据库:").grid(row=3, column=0, sticky=tk.W, pady=5)
        entry_db = ttk.Entry(frame, width=30)
        entry_db.insert(0, self.entry_database.get().strip() or "steel_belt")
        entry_db.grid(row=3, column=1, pady=5)

        info_frame = ttk.LabelFrame(frame, text="说明", padding="10")
        info_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=15)

        info_text = """
1. 创建的用户可以从局域网任何电脑访问
2. 主机地址填写 % 表示允许任何IP
3. 请确保MySQL服务已绑定到局域网IP
4. 客户端需要开放3306端口防火墙
        """
        ttk.Label(info_frame, text=info_text, justify=tk.LEFT, font=("Consolas", 9)).pack(anchor=tk.W)

        def do_enable():
            user = entry_user.get().strip()
            password = entry_pass.get()
            db = entry_db.get().strip() or "steel_belt"

            if not user or not password:
                messagebox.showerror("错误", "请填写用户名和密码")
                return

            try:
                with self.conn.cursor() as cursor:
                    cursor.execute(f"CREATE USER IF NOT EXISTS '{user}'@'%' IDENTIFIED BY '{password}'")
                    cursor.execute(f"GRANT ALL PRIVILEGES ON `{db}`.* TO '{user}'@'%' WITH GRANT OPTION")
                    cursor.execute("FLUSH PRIVILEGES")
                self.conn.commit()
                self.log_message(f"✓ 已创建远程用户: {user}")
                self.log_message(f"✓ 已授权数据库: {db}")
                self.log_message(f"✓ 连接方式: {user}@'<局域网IP>'")
                messagebox.showinfo("成功", f"局域网访问已启用！\n\n用户: {user}\n数据库: {db}\n\n连接示例:\nhost=192.168.0.100\nuser={user}\npassword={password}")
                dialog.destroy()
            except Exception as e:
                self.log_message(f"✗ 启用失败: {e}")
                messagebox.showerror("错误", f"启用失败:\n{e}")

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=10)

        ttk.Button(btn_frame, text="创建并授权", command=do_enable).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=10)

    def _show_users(self):
        """显示所有用户"""
        if not self._ensure_connection():
            return

        self.log_message("=" * 50)
        self.log_message("查询所有用户...")

        try:
            with self.conn.cursor() as cursor:
                cursor.execute("SELECT user, host, account_locked FROM mysql.user WHERE user NOT IN ('mysql.infoschema', 'mysql.session', 'mysql.sys')")
                users = cursor.fetchall()

            self.log_message(f"共 {len(users)} 个用户:")
            self.log_message("-" * 50)

            for user in users:
                self.log_message(f"  {user['user']}@{user['host']} (锁定: {user['account_locked']})")

                # 查询该用户的权限
                try:
                    with self.conn.cursor() as cursor:
                        cursor.execute(f"SHOW GRANTS FOR '{user['user']}'@'{user['host']}'")
                        grants = cursor.fetchall()
                    for grant in grants:
                        grant_key = list(grant.keys())[0]
                        grant_value = grant[grant_key]
                        self.log_message(f"    -> {grant_value}")
                except Exception as e:
                    self.log_message(f"查询用户授权失败: {e}")

            self.log_message("=" * 50)

        except Exception as e:
            self.log_message(f"✗ 查询用户失败: {e}")

    def _show_databases(self):
        """显示所有数据库"""
        if not self._ensure_connection():
            return

        self.log_message("=" * 50)
        self.log_message("查询所有数据库...")

        try:
            with self.conn.cursor() as cursor:
                cursor.execute("SHOW DATABASES")
                dbs = cursor.fetchall()

            self.log_message(f"共 {len(dbs)} 个数据库:")
            for db in dbs:
                db_name = db['Database']
                marker = " ← 当前数据库" if db_name == self.entry_database.get().strip() else ""
                self.log_message(f"  {db_name}{marker}")

            self.log_message("=" * 50)

        except Exception as e:
            self.log_message(f"✗ 查询数据库失败: {e}")

    def _show_tables(self):
        """显示当前数据库的表"""
        if not self._ensure_connection():
            return

        db_name = self.entry_database.get().strip()
        if not db_name:
            messagebox.showerror("错误", "请输入数据库名称")
            return

        try:
            self.conn.select_db(db_name)
        except Exception as e:
            self.log_message(f"✗ 选择数据库失败: {e}")
            return

        self.log_message("=" * 50)
        self.log_message(f"查询数据库 {db_name} 的表...")

        try:
            with self.conn.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()

            self.log_message(f"共 {len(tables)} 个表:")
            for table in tables:
                table_name = list(table.values())[0]
                self.log_message(f"  {table_name}")

            self.log_message("=" * 50)

        except Exception as e:
            self.log_message(f"✗ 查询表失败: {e}")

    def run(self):
        """运行程序"""
        self.log_message("MySQL数据库管理工具已启动")
        self.log_message("请先配置连接信息并连接数据库")
        self.root.mainloop()


if __name__ == "__main__":
    app = MySQLTool()
    app.run()