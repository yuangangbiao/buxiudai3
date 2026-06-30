# -*- coding: utf-8 -*-
"""
库存管理系统 - 数据库初始化工具
用于创建数据库和初始化数据模板
"""
import os
import sys
import json
from datetime import datetime

try:
    import pymysql
    from pymysql.cursors import DictCursor
    PYMysql_AVAILABLE = True
except ImportError:
    PYMysql_AVAILABLE = False
    print("[ERROR] pymysql 模块未安装，请运行: pip install pymysql")


def load_config():
    """加载配置文件"""
    if hasattr(sys, '_MEIPASS'):
        app_dir = os.path.dirname(sys.executable)
    else:
        app_dir = os.path.dirname(os.path.abspath(__file__))

    config_file = os.path.join(app_dir, "server_config.json")

    default_config = {
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password": os.getenv('MYSQL_PASSWORD', ''),
        "database": "inventory_db",
        "charset": "utf8mb4"
    }

    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                db_config = config.get("database", {})
                if db_config:
                    for key in ["host", "port", "user", "password", "database"]:
                        if key in db_config:
                            if key == "port":
                                default_config[key] = int(db_config[key])
                            else:
                                default_config[key] = db_config[key]
        except Exception as e:
            print(f"[WARN] 配置文件读取失败: {e}")

    return default_config


def create_database(config):
    """创建数据库"""
    print("\n" + "=" * 50)
    print("  数据库初始化工具")
    print("=" * 50)
    print(f"\n数据库配置:")
    print(f"  主机: {config['host']}")
    print(f"  端口: {config['port']}")
    print(f"  用户: {config['user']}")
    print(f"  数据库: {config['database']}")
    print()

    try:
        print("[1/4] 连接MySQL服务器...")
        conn = pymysql.connect(
            host=config['host'],
            port=config['port'],
            user=config['user'],
            password=config['password'],
            charset=config['charset']
        )
        print("      [OK] 连接成功")
        cursor = conn.cursor()

        print(f"[2/4] 创建数据库 '{config['database']}'...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{config['database']}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print("      [OK] 数据库创建成功")
        cursor.close()
        conn.close()

        print("[3/4] 连接到目标数据库...")
        conn = pymysql.connect(
            host=config['host'],
            port=config['port'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            charset=config['charset']
        )
        cursor = conn.cursor()

        print("[4/4] 创建数据表...")

        tables = [
            # 产品分类表
            """CREATE TABLE IF NOT EXISTS product_categories (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL COMMENT '分类名称',
                parent_id INT DEFAULT 0 COMMENT '父分类ID',
                sort_order INT DEFAULT 0 COMMENT '排序',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='产品分类表'""",

            # 产品表
            """CREATE TABLE IF NOT EXISTS products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                product_code VARCHAR(50) UNIQUE NOT NULL COMMENT '产品编码',
                product_name VARCHAR(200) NOT NULL COMMENT '产品名称',
                category_id INT COMMENT '分类ID',
                unit VARCHAR(20) DEFAULT '件' COMMENT '单位',
                spec VARCHAR(200) COMMENT '规格',
                price DECIMAL(10,2) DEFAULT 0 COMMENT '单价',
                cost DECIMAL(10,2) DEFAULT 0 COMMENT '成本',
                stock_quantity INT DEFAULT 0 COMMENT '库存数量',
                min_stock INT DEFAULT 0 COMMENT '最小库存',
                max_stock INT DEFAULT 0 COMMENT '最大库存',
                location VARCHAR(100) COMMENT '存放位置',
                supplier VARCHAR(200) COMMENT '供应商',
                remark TEXT COMMENT '备注',
                status TINYINT DEFAULT 1 COMMENT '状态 1启用 0禁用',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_code (product_code),
                INDEX idx_category (category_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='产品表'""",

            # 仓库表
            """CREATE TABLE IF NOT EXISTS warehouses (
                id INT AUTO_INCREMENT PRIMARY KEY,
                warehouse_code VARCHAR(50) UNIQUE NOT NULL COMMENT '仓库编码',
                warehouse_name VARCHAR(100) NOT NULL COMMENT '仓库名称',
                address VARCHAR(200) COMMENT '地址',
                manager VARCHAR(50) COMMENT '负责人',
                phone VARCHAR(20) COMMENT '联系电话',
                status TINYINT DEFAULT 1 COMMENT '状态',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='仓库表'""",

            # 库存表
            """CREATE TABLE IF NOT EXISTS inventory (
                id INT AUTO_INCREMENT PRIMARY KEY,
                product_id INT NOT NULL COMMENT '产品ID',
                warehouse_id INT NOT NULL COMMENT '仓库ID',
                quantity INT DEFAULT 0 COMMENT '库存数量',
                reserved_quantity INT DEFAULT 0 COMMENT '预留数量',
                available_quantity INT GENERATED ALWAYS AS (quantity - reserved_quantity) STORED COMMENT '可用数量',
                last_in_date DATE COMMENT '最后入库日期',
                last_out_date DATE COMMENT '最后出库日期',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_product_warehouse (product_id, warehouse_id),
                INDEX idx_warehouse (warehouse_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='库存表'""",

            # 库存变动记录表
            """CREATE TABLE IF NOT EXISTS inventory_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                product_id INT NOT NULL COMMENT '产品ID',
                warehouse_id INT NOT NULL COMMENT '仓库ID',
                change_type VARCHAR(20) NOT NULL COMMENT '变动类型 in/out/adjust',
                quantity INT NOT NULL COMMENT '变动数量',
                before_quantity INT DEFAULT 0 COMMENT '变动前数量',
                after_quantity INT DEFAULT 0 COMMENT '变动后数量',
                order_no VARCHAR(50) COMMENT '关联单据号',
                remark TEXT COMMENT '备注',
                operator VARCHAR(50) COMMENT '操作人',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_product (product_id),
                INDEX idx_warehouse (warehouse_id),
                INDEX idx_created (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='库存变动记录表'""",

            # 客户表
            """CREATE TABLE IF NOT EXISTS customers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                customer_code VARCHAR(50) UNIQUE NOT NULL COMMENT '客户编码',
                customer_name VARCHAR(200) NOT NULL COMMENT '客户名称',
                contact VARCHAR(50) COMMENT '联系人',
                phone VARCHAR(20) COMMENT '电话',
                mobile VARCHAR(20) COMMENT '手机',
                address VARCHAR(300) COMMENT '地址',
                email VARCHAR(100) COMMENT '邮箱',
                customer_type VARCHAR(20) DEFAULT '普通' COMMENT '客户类型',
                credit_limit DECIMAL(10,2) DEFAULT 0 COMMENT '信用额度',
                status TINYINT DEFAULT 1 COMMENT '状态',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客户表'""",

            # 供应商表
            """CREATE TABLE IF NOT EXISTS suppliers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                supplier_code VARCHAR(50) UNIQUE NOT NULL COMMENT '供应商编码',
                supplier_name VARCHAR(200) NOT NULL COMMENT '供应商名称',
                contact VARCHAR(50) COMMENT '联系人',
                phone VARCHAR(20) COMMENT '电话',
                mobile VARCHAR(20) COMMENT '手机',
                address VARCHAR(300) COMMENT '地址',
                email VARCHAR(100) COMMENT '邮箱',
                status TINYINT DEFAULT 1 COMMENT '状态',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='供应商表'""",

            # 入库单表
            """CREATE TABLE IF NOT EXISTS inbound_orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                order_no VARCHAR(50) UNIQUE NOT NULL COMMENT '单据号',
                supplier_id INT COMMENT '供应商ID',
                warehouse_id INT NOT NULL COMMENT '仓库ID',
                total_amount DECIMAL(12,2) DEFAULT 0 COMMENT '总金额',
                status VARCHAR(20) DEFAULT 'pending' COMMENT '状态 pending/confirmed/completed/cancelled',
                inbound_date DATE COMMENT '入库日期',
                remark TEXT COMMENT '备注',
                operator VARCHAR(50) COMMENT '操作人',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_order_no (order_no),
                INDEX idx_supplier (supplier_id),
                INDEX idx_warehouse (warehouse_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='入库单表'""",

            # 入库明细表
            """CREATE TABLE IF NOT EXISTS inbound_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                inbound_id INT NOT NULL COMMENT '入库单ID',
                product_id INT NOT NULL COMMENT '产品ID',
                quantity INT NOT NULL COMMENT '数量',
                price DECIMAL(10,2) DEFAULT 0 COMMENT '单价',
                amount DECIMAL(12,2) DEFAULT 0 COMMENT '金额',
                remark TEXT COMMENT '备注',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='入库明细表'""",

            # 出库单表
            """CREATE TABLE IF NOT EXISTS outbound_orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                order_no VARCHAR(50) UNIQUE NOT NULL COMMENT '单据号',
                customer_id INT COMMENT '客户ID',
                warehouse_id INT NOT NULL COMMENT '仓库ID',
                total_amount DECIMAL(12,2) DEFAULT 0 COMMENT '总金额',
                status VARCHAR(20) DEFAULT 'pending' COMMENT '状态 pending/confirmed/completed/cancelled',
                outbound_date DATE COMMENT '出库日期',
                remark TEXT COMMENT '备注',
                operator VARCHAR(50) COMMENT '操作人',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_order_no (order_no),
                INDEX idx_customer (customer_id),
                INDEX idx_warehouse (warehouse_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='出库单表'""",

            # 出库明细表
            """CREATE TABLE IF NOT EXISTS outbound_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                outbound_id INT NOT NULL COMMENT '出库单ID',
                product_id INT NOT NULL COMMENT '产品ID',
                quantity INT NOT NULL COMMENT '数量',
                price DECIMAL(10,2) DEFAULT 0 COMMENT '单价',
                amount DECIMAL(12,2) DEFAULT 0 COMMENT '金额',
                remark TEXT COMMENT '备注',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='出库明细表'""",
        ]

        for i, sql in enumerate(tables, 1):
            cursor.execute(sql)
            print(f"      [OK] 表 {i}/{len(tables)} 创建完成")

        cursor.close()
        conn.close()

        print("\n" + "=" * 50)
        print("  数据库初始化完成!")
        print("=" * 50)
        print("\n初始化内容:")
        print("  - 产品分类表 (product_categories)")
        print("  - 产品表 (products)")
        print("  - 仓库表 (warehouses)")
        print("  - 库存表 (inventory)")
        print("  - 库存变动记录表 (inventory_logs)")
        print("  - 客户表 (customers)")
        print("  - 供应商表 (suppliers)")
        print("  - 入库单表 (inbound_orders)")
        print("  - 入库明细表 (inbound_items)")
        print("  - 出库单表 (outbound_orders)")
        print("  - 出库明细表 (outbound_items)")
        print("\n下一步:")
        print("  1. 启动服务器端")
        print("  2. 使用客户端连接")
        print("=" * 50)

        return True

    except pymysql.err.OperationalError as e:
        print(f"\n[ERROR] 数据库连接失败: {e}")
        print("\n请检查:")
        print("  1. MySQL服务是否已启动")
        print("  2. 用户名密码是否正确")
        print("  3. 配置文件中的数据库设置是否正确")
        return False
    except Exception as e:
        print(f"\n[ERROR] 初始化失败: {e}")
        return False


def main():
    """主函数"""
    if not PYMysql_AVAILABLE:
        print("[ERROR] 缺少必要的pymysql模块")
        input("\n按回车键退出...")
        sys.exit(1)

    config = load_config()
    success = create_database(config)

    if success:
        print("\n数据库初始化成功!")
    else:
        print("\n数据库初始化失败，请检查错误信息")

    input("\n按回车键退出...")


if __name__ == "__main__":
    main()
