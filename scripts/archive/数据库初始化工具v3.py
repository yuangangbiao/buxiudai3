# -*- coding: utf-8 -*-
"""
不锈钢网带跟单系统 v3.0.0 - 数据库初始化程序
支持全新安装和增量升级
"""
import os
import sys
import logging
import hashlib
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

VERSION = "3.0.0"

def get_db_config():
    """获取数据库配置"""
    try:
        from db_config import MYSQL_CONFIG
        return MYSQL_CONFIG.copy()
    except ImportError:
        return {
            "host": os.getenv('MYSQL_HOST', 'localhost'),
            "port": int(os.getenv('MYSQL_PORT', 3306)),
            "user": os.getenv('MYSQL_USER', 'root'),
            "password": os.getenv('MYSQL_PASSWORD', ''),
            "database": os.getenv('MYSQL_DATABASE', 'steel_belt'),
            "charset": "utf8mb4"
        }

def import_module(name):
    """安全导入模块"""
    try:
        return __import__(name)
    except ImportError as e:
        logger.error(f"导入模块失败: {name} - {e}")
        return None

def check_dependencies():
    """检查依赖"""
    logger.info("检查依赖...")
    deps = ['pymysql']
    for dep in deps:
        if not import_module(dep):
            logger.error(f"缺少依赖: {dep}")
            return False
    logger.info("依赖检查通过")
    return True

def create_database_if_not_exists(config):
    """创建数据库（如果不存在）"""
    import pymysql

    db_name = config.pop('database', 'steel_belt')
    logger.info(f"检查数据库: {db_name}")

    try:
        conn = pymysql.connect(
            host=config.get('host', 'localhost'),
            port=config.get('port', 3306),
            user=config.get('user', 'root'),
            password=config.get('password', ''),
            charset='utf8mb4'
        )
        cursor = conn.cursor()

        safe_db_name = db_name.replace('`', '``')
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{safe_db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        logger.info(f"数据库 {db_name} 就绪")

        cursor.close()
        conn.close()

        config['database'] = db_name
        return True
    except Exception as e:
        logger.error(f"创建数据库失败: {e}")
        return False

TABLES_SQL = {
    "_migration_history": """
        CREATE TABLE IF NOT EXISTS _migration_history (
            id INT PRIMARY KEY AUTO_INCREMENT,
            migration_id VARCHAR(50) UNIQUE NOT NULL,
            migration_name VARCHAR(200),
            executed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            sql_statements TEXT,
            rollback_sql TEXT,
            status ENUM('success', 'failed', 'rolled_back') DEFAULT 'success',
            error_message TEXT,
            checksum VARCHAR(64)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    "process_calc_rules": """
        CREATE TABLE IF NOT EXISTS process_calc_rules (
            id INT PRIMARY KEY AUTO_INCREMENT,
            process_name VARCHAR(50) NOT NULL,
            product_types_json TEXT,
            condition_expr TEXT,
            planned_qty_formula TEXT,
            material_formula TEXT,
            qty_formula TEXT,
            spec_field TEXT,
            extra_field TEXT,
            enabled TINYINT(1) DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_process_product (process_name, product_types_json(100))
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    "material_calc_rules": """
        CREATE TABLE IF NOT EXISTS material_calc_rules (
            id INT PRIMARY KEY AUTO_INCREMENT,
            product_type VARCHAR(50) NOT NULL,
            material_param VARCHAR(50) NOT NULL,
            name VARCHAR(100) NOT NULL,
            density DECIMAL(10,4) DEFAULT NULL,
            spec_field TEXT,
            spec_unit VARCHAR(20),
            qty_formula TEXT,
            enabled TINYINT(1) DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_product_material (product_type, material_param, name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    "quality_rules": """
        CREATE TABLE IF NOT EXISTS quality_rules (
            id INT PRIMARY KEY AUTO_INCREMENT,
            rule_name VARCHAR(100) NOT NULL,
            process_name VARCHAR(100),
            product_types_json TEXT,
            condition_expr TEXT,
            inspection_items_json TEXT,
            check_formula TEXT,
            priority INT DEFAULT 5,
            enabled TINYINT(1) DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_process_name (process_name),
            INDEX idx_enabled (enabled)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    "quality_rule_items": """
        CREATE TABLE IF NOT EXISTS quality_rule_items (
            id INT PRIMARY KEY AUTO_INCREMENT,
            rule_id INT NOT NULL,
            inspection_item VARCHAR(100) NOT NULL,
            check_formula TEXT,
            tolerance TEXT,
            is_custom TINYINT(1) DEFAULT 0,
            sort_order INT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (rule_id) REFERENCES quality_rules(id) ON DELETE CASCADE,
            INDEX idx_rule_id (rule_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    "customers": """
        CREATE TABLE IF NOT EXISTS customers (
            id INT PRIMARY KEY AUTO_INCREMENT,
            customer_code VARCHAR(20) UNIQUE NOT NULL COMMENT '客户编码',
            name VARCHAR(100) NOT NULL COMMENT '客户名称',
            contact_person VARCHAR(50) COMMENT '联系人',
            phone VARCHAR(20) COMMENT '联系电话',
            address VARCHAR(255) COMMENT '地址',
            customer_group VARCHAR(50) COMMENT '客户分组',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_name (name),
            INDEX idx_customer_group (customer_group)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    "production_stats": """
        CREATE TABLE IF NOT EXISTS production_stats (
            id INT PRIMARY KEY AUTO_INCREMENT,
            order_id INT NOT NULL COMMENT '订单ID',
            production_id INT COMMENT '生产单ID',
            order_no VARCHAR(50) COMMENT '订单号',
            product_type VARCHAR(50) COMMENT '产品类型',
            material VARCHAR(50) COMMENT '材质',
            planned_qty DECIMAL(10,2) COMMENT '计划数量',
            completed_qty DECIMAL(10,2) DEFAULT 0 COMMENT '完成数量',
            in_progress_qty DECIMAL(10,2) DEFAULT 0 COMMENT '在制数量',
            qualified_qty DECIMAL(10,2) DEFAULT 0 COMMENT '合格数量',
            defective_qty DECIMAL(10,2) DEFAULT 0 COMMENT '不合格数量',
            production_rate DECIMAL(5,2) DEFAULT 0 COMMENT '生产进度%',
            qualified_rate DECIMAL(5,2) DEFAULT 0 COMMENT '合格率%',
            status VARCHAR(20) DEFAULT 'pending' COMMENT '状态',
            start_date DATE COMMENT '开始日期',
            end_date DATE COMMENT '结束日期',
            remarks TEXT COMMENT '备注',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_order_id (order_id),
            INDEX idx_production_id (production_id),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    "orders": """
        CREATE TABLE IF NOT EXISTS orders (
            id INT PRIMARY KEY AUTO_INCREMENT,
            order_no VARCHAR(50) UNIQUE NOT NULL,
            customer_name VARCHAR(100) NOT NULL,
            customer_phone VARCHAR(20),
            customer_address VARCHAR(255),
            customer_group VARCHAR(50),
            product_type VARCHAR(50) NOT NULL,
            material VARCHAR(50),
            mesh_size VARCHAR(50),
            wire_diameter VARCHAR(50),
            width VARCHAR(50),
            length VARCHAR(50),
            quantity DECIMAL(10,2) NOT NULL,
            unit VARCHAR(10) DEFAULT '米',
            unit_price DECIMAL(10,2) DEFAULT 0,
            total_amount DECIMAL(12,2) DEFAULT 0,
            surface_treatment VARCHAR(50),
            special_requirements TEXT,
            delivery_date DATE,
            status VARCHAR(20) DEFAULT 'pending',
            remark TEXT,
            extra_params TEXT,
            product_remark TEXT,
            created_by VARCHAR(50),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            is_deleted TINYINT(1) DEFAULT 0,
            deleted_at DATETIME,
            deleted_by VARCHAR(50),
            INDEX idx_order_no (order_no),
            INDEX idx_customer_name (customer_name),
            INDEX idx_status (status),
            INDEX idx_product_type (product_type),
            INDEX idx_delivery_date (delivery_date),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    "production_orders": """
        CREATE TABLE IF NOT EXISTS production_orders (
            id INT PRIMARY KEY AUTO_INCREMENT,
            work_order_no VARCHAR(50) UNIQUE NOT NULL,
            order_id INT NOT NULL,
            priority INT DEFAULT 5,
            plan_start DATETIME,
            plan_end DATETIME,
            actual_start DATETIME,
            actual_end DATETIME,
            status VARCHAR(20) DEFAULT 'pending',
            assigned_to VARCHAR(100),
            shift_type VARCHAR(20),
            output_qty DECIMAL(10,2) DEFAULT 0,
            qualified_qty DECIMAL(10,2) DEFAULT 0,
            remark TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_order_id (order_id),
            INDEX idx_work_order_no (work_order_no),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    "inventory": """
        CREATE TABLE IF NOT EXISTS inventory (
            id INT PRIMARY KEY AUTO_INCREMENT,
            material_name VARCHAR(100) NOT NULL,
            material_type VARCHAR(50) NOT NULL,
            specification VARCHAR(100),
            quantity DECIMAL(10,2) DEFAULT 0,
            unit VARCHAR(20) DEFAULT '米',
            location VARCHAR(100),
            warehouse VARCHAR(50) DEFAULT '原材料仓库',
            min_stock DECIMAL(10,2) DEFAULT 0,
            max_stock DECIMAL(10,2) DEFAULT 0,
            unit_cost DECIMAL(10,2) DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_material_name (material_name),
            INDEX idx_material_type (material_type),
            INDEX idx_warehouse (warehouse)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    "inventory_records": """
        CREATE TABLE IF NOT EXISTS inventory_records (
            id INT PRIMARY KEY AUTO_INCREMENT,
            inventory_id INT NOT NULL,
            order_id INT,
            record_type VARCHAR(20) NOT NULL,
            quantity DECIMAL(10,2) NOT NULL,
            balance_after DECIMAL(10,2),
            operator VARCHAR(50),
            remark TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_inventory_id (inventory_id),
            INDEX idx_order_id (order_id),
            INDEX idx_record_type (record_type),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    "process_records": """
        CREATE TABLE IF NOT EXISTS process_records (
            id INT PRIMARY KEY AUTO_INCREMENT,
            order_id INT NOT NULL,
            production_id INT,
            process_name VARCHAR(50) NOT NULL,
            process_seq INT DEFAULT 1,
            worker VARCHAR(50),
            output_qty DECIMAL(10,2) DEFAULT 0,
            qualified_qty DECIMAL(10,2) DEFAULT 0,
            defective_qty DECIMAL(10,2) DEFAULT 0,
            work_hours DECIMAL(8,2) DEFAULT 0,
            start_time DATETIME,
            end_time DATETIME,
            remark TEXT,
            status VARCHAR(20) DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_order_id (order_id),
            INDEX idx_production_id (production_id),
            INDEX idx_process_name (process_name),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    "quality_records": """
        CREATE TABLE IF NOT EXISTS quality_records (
            id INT PRIMARY KEY AUTO_INCREMENT,
            order_id INT NOT NULL,
            production_id INT,
            inspection_type VARCHAR(20) NOT NULL,
            inspection_items TEXT,
            inspector VARCHAR(50),
            inspection_date DATETIME,
            result VARCHAR(20) DEFAULT 'pending',
            remark TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_order_id (order_id),
            INDEX idx_production_id (production_id),
            INDEX idx_inspection_type (inspection_type),
            INDEX idx_inspection_date (inspection_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    "quality_record_items": """
        CREATE TABLE IF NOT EXISTS quality_record_items (
            id INT PRIMARY KEY AUTO_INCREMENT,
            record_id INT NOT NULL,
            inspection_item VARCHAR(100) NOT NULL,
            measured_value TEXT,
            standard_value TEXT,
            tolerance TEXT,
            is_qualified TINYINT(1) DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (record_id) REFERENCES quality_records(id) ON DELETE CASCADE,
            INDEX idx_record_id (record_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    "finished_goods": """
        CREATE TABLE IF NOT EXISTS finished_goods (
            id INT PRIMARY KEY AUTO_INCREMENT,
            order_id INT NOT NULL,
            warehouse VARCHAR(50) DEFAULT '成品仓库',
            quantity DECIMAL(10,2) DEFAULT 0,
            unit VARCHAR(10) DEFAULT '米',
            location VARCHAR(100),
            status VARCHAR(20) DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_order_id (order_id),
            INDEX idx_warehouse (warehouse),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    "shipments": """
        CREATE TABLE IF NOT EXISTS shipments (
            id INT PRIMARY KEY AUTO_INCREMENT,
            shipment_no VARCHAR(50) UNIQUE NOT NULL,
            order_id INT NOT NULL,
            finished_goods_id INT,
            warehouse VARCHAR(50),
            quantity DECIMAL(10,2) NOT NULL,
            unit VARCHAR(10) DEFAULT '米',
            shipment_date DATE,
            receiver_name VARCHAR(100),
            receiver_phone VARCHAR(20),
            receiver_address VARCHAR(255),
            logistics_company VARCHAR(50),
            tracking_no VARCHAR(100),
            status VARCHAR(20) DEFAULT 'pending',
            remark TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_order_id (order_id),
            INDEX idx_shipment_no (shipment_no),
            INDEX idx_tracking_no (tracking_no),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    "shipment_tracks": """
        CREATE TABLE IF NOT EXISTS shipment_tracks (
            id INT PRIMARY KEY AUTO_INCREMENT,
            shipment_id INT NOT NULL,
            tracking_no VARCHAR(100),
            status VARCHAR(50),
            location VARCHAR(100),
            description TEXT,
            event_time DATETIME,
            raw_data TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (shipment_id) REFERENCES shipments(id) ON DELETE CASCADE,
            INDEX idx_shipment_id (shipment_id),
            INDEX idx_tracking_no (tracking_no),
            INDEX idx_event_time (event_time)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    "custom_mat_params": """
        CREATE TABLE IF NOT EXISTS custom_mat_params (
            id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(50) UNIQUE NOT NULL,
            display_name VARCHAR(100),
            category VARCHAR(50),
            is_active TINYINT(1) DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_name (name),
            INDEX idx_category (category)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    "custom_spec_fields": """
        CREATE TABLE IF NOT EXISTS custom_spec_fields (
            id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(50) UNIQUE NOT NULL,
            display_name VARCHAR(100),
            field_type VARCHAR(20) DEFAULT 'text',
            is_active TINYINT(1) DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_name (name),
            INDEX idx_is_active (is_active)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    "surface_treatment_options": """
        CREATE TABLE IF NOT EXISTS surface_treatment_options (
            id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(50) UNIQUE NOT NULL,
            is_preset TINYINT(1) DEFAULT 0,
            is_active TINYINT(1) DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_name (name),
            INDEX idx_is_active (is_active)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    "status_logs": """
        CREATE TABLE IF NOT EXISTS status_logs (
            id INT PRIMARY KEY AUTO_INCREMENT,
            table_name VARCHAR(50) NOT NULL,
            record_id INT NOT NULL,
            old_status VARCHAR(50),
            new_status VARCHAR(50) NOT NULL,
            operator VARCHAR(50),
            remark TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_table_record (table_name, record_id),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    "audit_logs": """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_name VARCHAR(50),
            action VARCHAR(50) NOT NULL,
            table_name VARCHAR(50),
            record_id INT,
            changes TEXT,
            ip_address VARCHAR(50),
            user_agent TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_user_name (user_name),
            INDEX idx_action (action),
            INDEX idx_table_name (table_name),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    "logistics_settings": """
        CREATE TABLE IF NOT EXISTS logistics_settings (
            id INT PRIMARY KEY AUTO_INCREMENT,
            setting_key VARCHAR(100) UNIQUE NOT NULL,
            setting_value TEXT,
            description VARCHAR(255),
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    "alert_rules": """
        CREATE TABLE IF NOT EXISTS alert_rules (
            id INT PRIMARY KEY AUTO_INCREMENT,
            rule_name VARCHAR(100) NOT NULL,
            alert_type VARCHAR(50) NOT NULL,
            condition_expr TEXT NOT NULL,
            threshold_value DECIMAL(12,4),
            message_template TEXT,
            enabled TINYINT(1) DEFAULT 1,
            priority INT DEFAULT 5,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_alert_type (alert_type),
            INDEX idx_enabled (enabled)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    "alerts": """
        CREATE TABLE IF NOT EXISTS alerts (
            id INT PRIMARY KEY AUTO_INCREMENT,
            rule_id INT,
            alert_type VARCHAR(50) NOT NULL,
            title VARCHAR(200),
            message TEXT,
            severity VARCHAR(20) DEFAULT 'info',
            is_read TINYINT(1) DEFAULT 0,
            is_resolved TINYINT(1) DEFAULT 0,
            resolved_at DATETIME,
            resolved_by VARCHAR(50),
            related_table VARCHAR(50),
            related_id INT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_rule_id (rule_id),
            INDEX idx_is_read (is_read),
            INDEX idx_is_resolved (is_resolved),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """
}

INIT_DATA_SQL = {
    "_migration_history": """
        INSERT INTO _migration_history (migration_id, migration_name, sql_statements, status, checksum)
        VALUES (%s, %s, %s, 'success', %s)
    """,

    "logistics_settings": """
        INSERT IGNORE INTO logistics_settings (setting_key, setting_value, description)
        VALUES
            ('default_logistics', 'kuaidi100', '默认物流平台'),
            ('auto_track', 'true', '自动追踪'),
            ('track_interval', '3600', '追踪间隔(秒)')
    """,

    "alert_rules": """
        INSERT IGNORE INTO alert_rules (rule_name, alert_type, condition_expr, threshold_value, message_template, priority)
        VALUES
            ('库存不足告警', 'inventory_low', 'qty < min_stock', 0, '物料 {material_name} 库存不足，当前库存: {quantity}', 5),
            ('交货期临近', 'delivery_soon', 'DATEDIFF(delivery_date, NOW()) <= 3', 0, '订单 {order_no} 交货期临近', 5),
            ('质量超差告警', 'quality_overtolerance', 'is_qualified = 0', 0, '质检记录发现超差项目: {inspection_item}', 5)
    """
}

def get_table_columns(cursor, db_name, table_name):
    """获取表的所有列"""
    try:
        safe_table = table_name.replace('`', '``')
        cursor.execute(f"""
            SELECT COLUMN_NAME
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
        """, (db_name, safe_table))
        return {row[0] for row in cursor.fetchall()}
    except Exception:
        return set()

def init_database():
    """初始化数据库"""
    logger.info("=" * 60)
    logger.info(f"  不锈钢网带跟单系统 v{VERSION} - 数据库初始化")
    logger.info("=" * 60)
    logger.info("")

    if not check_dependencies():
        logger.error("依赖检查失败")
        return False

    config = get_db_config()

    if not create_database_if_not_exists(config.copy()):
        logger.error("数据库创建失败")
        return False

    import pymysql
    config["cursorclass"] = pymysql.cursors.DictCursor

    try:
        conn = pymysql.connect(**config)
        cursor = conn.cursor()

        db_name = config["database"]
        existing_tables = set()

        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s
        """, (db_name,))
        for row in cursor.fetchall():
            existing_tables.add(row['TABLE_NAME'])

        logger.info(f"现有表: {len(existing_tables)}")
        logger.info("")

        created_count = 0
        updated_count = 0

        for table_name, create_sql in TABLES_SQL.items():
            if table_name == "_migration_history":
                cursor.execute(create_sql)
                logger.info(f"  [新建] {table_name}")
                created_count += 1
                continue

            if table_name in existing_tables:
                logger.info(f"  [跳过] {table_name} (已存在)")
                continue

            cursor.execute(create_sql)
            logger.info(f"  [新建] {table_name}")
            created_count += 1

        conn.commit()

        logger.info("")
        logger.info("-" * 60)
        logger.info("插入初始数据...")
        logger.info("-" * 60)

        for table_name, insert_sql in INIT_DATA_SQL.items():
            if table_name == "_migration_history":
                migration_id = f"init_v{VERSION.replace('.', '')}"
                checksum = hashlib.md5(f"init_v{VERSION}".encode()).hexdigest()
                try:
                    cursor.execute(insert_sql, (migration_id, f"初始版本 v{VERSION}", create_sql if 'TABLES_SQL' in dir() else "", checksum))
                    conn.commit()
                    logger.info(f"  [记录] 迁移历史")
                except Exception as e:
                    if "Duplicate" in str(e):
                        logger.info(f"  [跳过] 迁移历史 (已存在)")
                    else:
                        logger.warning(f"  [警告] 迁移历史: {e}")
                continue

            try:
                cursor.execute(insert_sql)
                conn.commit()
                logger.info(f"  [插入] {table_name}")
            except Exception as e:
                if "Duplicate" in str(e) or "doesn't exist" in str(e):
                    logger.info(f"  [跳过] {table_name} (数据已存在)")
                else:
                    logger.warning(f"  [警告] {table_name}: {e}")

        cursor.close()
        conn.close()

        logger.info("")
        logger.info("=" * 60)
        logger.info(f"  数据库初始化完成!")
        logger.info(f"  新建表: {created_count}")
        logger.info(f"  数据库: {db_name}")
        logger.info("=" * 60)
        logger.info("")
        logger.info("下一步:")
        logger.info("  1. 复制 EXE 和配置文件到目标机器")
        logger.info("  2. 确保 MySQL 服务运行中")
        logger.info("  3. 运行主程序")
        logger.info("")
        return True

    except Exception as e:
        logger.error(f"初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print()
    print("=" * 60)
    print(f"  不锈钢网带跟单系统 v{VERSION}")
    print(f"  数据库初始化程序")
    print("=" * 60)
    print()

    success = init_database()

    if success:
        print()
        print("按 Enter 键退出...")
        input()
    else:
        print()
        print("初始化失败，请检查错误信息")
        print("按 Enter 键退出...")
        input()
        sys.exit(1)

if __name__ == "__main__":
    main()