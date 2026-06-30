# -*- coding: utf-8 -*-
"""
数据库初始化与管理 — 连接统一走 core.db
仅保留 init_db / ensure_*_indexes 等独特功能
"""
import os
import re
import tempfile
import atexit
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

_temp_files_to_cleanup = []

def _validate_sql_identifier(identifier):
    """验证SQL标识符（表名、列名等），防止SQL注入"""
    if not identifier:
        return False
    return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identifier))

def _safe_table_name(table):
    """安全的表名（仅限ASCII字母、数字和下划线）"""
    if not _validate_sql_identifier(table):
        raise ValueError(f"无效的表名: {table}")
    return table


def _cleanup_temp_files():
    """清理所有临时文件"""
    for temp_path in _temp_files_to_cleanup:
        try:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
        except Exception:
            pass

atexit.register(_cleanup_temp_files)


# ── 连接入口：统一走 core.db ──

def get_connection():
    """获取数据库连接 — 委托给 core.db"""
    from core.db import get_connection as _gc
    return _gc()


@contextmanager
def get_connection_context():
    """获取数据库连接的上下文管理器 — 委托给 core.db"""
    from core.db import get_connection_context as _gcc
    with _gcc() as conn:
        yield conn

def _migrate_tables(c, conn):
    """数据库表结构升级"""
    c.execute("SHOW TABLES")
    result = c.fetchall()
    existing_tables = set()
    if result:
        for row in result:
            for val in row.values():
                existing_tables.add(val)
    
    if "product_types" in existing_tables:
        c.execute("SHOW COLUMNS FROM product_types")
        columns = {row['Field'] for row in c.fetchall()}
        if "is_preset" not in columns:
            c.execute("ALTER TABLE product_types ADD COLUMN is_preset INT DEFAULT 0")
    
    if "material_densities" in existing_tables:
        c.execute("SHOW COLUMNS FROM material_densities")
        columns = {row['Field'] for row in c.fetchall()}
        if "is_preset" not in columns:
            c.execute("ALTER TABLE material_densities ADD COLUMN is_preset INT DEFAULT 0")
        if "updated_at" not in columns:
            c.execute("ALTER TABLE material_densities ADD COLUMN updated_at DATETIME")
    
    if "custom_dim_params" in existing_tables:
        c.execute("SHOW COLUMNS FROM custom_dim_params")
        columns = {row['Field'] for row in c.fetchall()}
        if "unit" not in columns:
            c.execute("ALTER TABLE custom_dim_params ADD COLUMN unit VARCHAR(20) DEFAULT 'mm'")
    
    if "order_templates" in existing_tables:
        c.execute("SHOW COLUMNS FROM order_templates")
        columns = {row['Field'] for row in c.fetchall()}
        if "values_json" not in columns:
            c.execute("ALTER TABLE order_templates ADD COLUMN values_json TEXT")
        if "order_json" not in columns:
            c.execute("ALTER TABLE order_templates ADD COLUMN order_json TEXT")
    
    if "custom_params" in existing_tables:
        c.execute("SHOW COLUMNS FROM custom_params")
        columns = {row['Field'] for row in c.fetchall()}
        if "params_json" not in columns:
            c.execute("ALTER TABLE custom_params ADD COLUMN params_json TEXT")
        # 补充审计字段
        audit_fields = {
            "created_by": "VARCHAR(50) COMMENT '创建人'",
            "updated_by": "VARCHAR(50) COMMENT '最后更新人'",
            "is_deleted": "TINYINT(1) DEFAULT 0 COMMENT '软删除标记'",
            "deleted_at": "DATETIME COMMENT '删除时间'",
            "deleted_by": "VARCHAR(50) COMMENT '删除人'",
            "version": "INT DEFAULT 1 COMMENT '版本号'",
        }
        for col_name, col_def in audit_fields.items():
            if col_name not in columns:
                c.execute(f"ALTER TABLE custom_params ADD COLUMN {col_name} {col_def}")
    
    if "material_templates" in existing_tables:
        c.execute("SHOW COLUMNS FROM material_templates")
        columns = {row['Field'] for row in c.fetchall()}
        if "materials_json" not in columns:
            c.execute("ALTER TABLE material_templates ADD COLUMN materials_json TEXT")
    
    if "process_templates" in existing_tables:
        c.execute("SHOW COLUMNS FROM process_templates")
        columns = {row['Field'] for row in c.fetchall()}
        if "data_json" not in columns:
            c.execute("ALTER TABLE process_templates ADD COLUMN data_json TEXT")
    
    if "material_rules_templates" in existing_tables:
        c.execute("SHOW COLUMNS FROM material_rules_templates")
        columns = {row['Field'] for row in c.fetchall()}
        if "rules_json" not in columns:
            c.execute("ALTER TABLE material_rules_templates ADD COLUMN rules_json TEXT")

    if "process_calc_rules" not in existing_tables:
        c.execute("""
            CREATE TABLE IF NOT EXISTS process_calc_rules (
                id INT PRIMARY KEY AUTO_INCREMENT,
                process_name VARCHAR(50) NOT NULL,
                product_types_json TEXT,
                condition_expr TEXT,
                planned_qty_formula TEXT,
                priority INT DEFAULT 5,
                enabled TINYINT(1) DEFAULT 1,
                created_at DATETIME DEFAULT NOW(),
                updated_at DATETIME DEFAULT NOW()
            )
        """)

    if "process_records" in existing_tables:
        c.execute("SHOW COLUMNS FROM process_records")
        columns = {row['Field'] for row in c.fetchall()}
        if "material_usage" not in columns:
            c.execute("ALTER TABLE process_records ADD COLUMN material_usage DECIMAL(12,2) DEFAULT 0")
        if "material_unit" not in columns:
            c.execute("ALTER TABLE process_records ADD COLUMN material_unit VARCHAR(20) DEFAULT 'kg'")

    if "quality_rules" in existing_tables:
        c.execute("SHOW COLUMNS FROM quality_rules")
        columns = {row['Field'] for row in c.fetchall()}
        if "process_name" not in columns:
            c.execute("ALTER TABLE quality_rules ADD COLUMN process_name VARCHAR(100)")

    if "quality_rules" not in existing_tables:
        c.execute("""
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
                created_at DATETIME DEFAULT NOW(),
                updated_at DATETIME DEFAULT NOW()
            )
        """)

    if "quality_rule_items" in existing_tables:
        c.execute("SHOW COLUMNS FROM quality_rule_items")
        columns = {row['Field'] for row in c.fetchall()}
        if "tolerance" not in columns:
            c.execute("ALTER TABLE quality_rule_items ADD COLUMN tolerance TEXT")

    if "quality_rule_items" not in existing_tables:
        c.execute("""
            CREATE TABLE IF NOT EXISTS quality_rule_items (
                id INT PRIMARY KEY AUTO_INCREMENT,
                rule_id INT NOT NULL,
                inspection_item VARCHAR(100) NOT NULL,
                check_formula TEXT,
                tolerance TEXT,
                FOREIGN KEY (rule_id) REFERENCES quality_rules(id) ON DELETE CASCADE
            )
        """)

    # ═══════════════════════════════════════════════════════════
    # 数据库结构优化迁移（根据 docs/数据库结构优化报告_20260501.md）
    # ═══════════════════════════════════════════════════════════

    # 1. 创建客户表 customers（高优先级）
    if "customers" not in existing_tables:
        c.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INT PRIMARY KEY AUTO_INCREMENT,
                customer_code VARCHAR(20) UNIQUE NOT NULL COMMENT '客户编码',
                name VARCHAR(100) NOT NULL COMMENT '客户名称',
                contact_person VARCHAR(50) COMMENT '联系人',
                phone VARCHAR(20) COMMENT '联系电话',
                mobile VARCHAR(20) COMMENT '手机',
                address VARCHAR(255) COMMENT '地址',
                customer_group VARCHAR(50) COMMENT '客户分组',
                credit_limit DECIMAL(12,2) DEFAULT 0 COMMENT '信用额度',
                payment_days INT DEFAULT 30 COMMENT '账期天数',
                tax_rate DECIMAL(5,2) DEFAULT 0 COMMENT '税率',
                bank_name VARCHAR(100) COMMENT '开户银行',
                bank_account VARCHAR(50) COMMENT '银行账号',
                salesperson VARCHAR(50) COMMENT '负责业务员',
                status VARCHAR(20) DEFAULT '正常' COMMENT '状态：正常/停用',
                remark TEXT COMMENT '备注',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                INDEX idx_customer_code (customer_code),
                INDEX idx_customer_name (name),
                INDEX idx_salesperson (salesperson),
                INDEX idx_status (status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客户信息表'
        """)

    # 2. 扩展 orders 表字段（高优先级）
    if "orders" in existing_tables:
        c.execute("SHOW COLUMNS FROM orders")
        columns = {row['Field'] for row in c.fetchall()}
        new_fields = {
            "product_type": "VARCHAR(100) COMMENT '产品类型'",
            "customer_id": "INT COMMENT '客户ID'",
            "salesperson": "VARCHAR(50) COMMENT '业务员'",
            "contact_person": "VARCHAR(50) COMMENT '联系人'",
            "priority_level": "VARCHAR(10) DEFAULT '中' COMMENT '优先级：高/中/低'",
            "cancel_reason": "TEXT COMMENT '取消原因'",
            "order_source": "VARCHAR(20) DEFAULT '线下' COMMENT '订单来源'",
            "payment_method": "VARCHAR(20) COMMENT '付款方式'",
            "invoice_type": "VARCHAR(30) COMMENT '发票类型'",
            "invoice_status": "VARCHAR(20) DEFAULT '未开票' COMMENT '发票状态'",
            "invoice_no": "VARCHAR(50) COMMENT '发票号码'",
            "is_deleted": "TINYINT(1) DEFAULT 0 COMMENT '软删除标记'",
            "deleted_at": "DATETIME COMMENT '删除时间'",
            "deleted_by": "VARCHAR(50) COMMENT '删除人'",
            "created_by": "VARCHAR(50) COMMENT '创建人'",
            "updated_by": "VARCHAR(50) COMMENT '最后更新人'",
            "version": "INT DEFAULT 1 COMMENT '版本号'",
        }
        for col_name, col_def in new_fields.items():
            if col_name not in columns:
                c.execute(f"ALTER TABLE orders ADD COLUMN {col_name} {col_def}")

    # 3. 扩展 production_orders 表字段（高优先级）
    if "production_orders" in existing_tables:
        c.execute("SHOW COLUMNS FROM production_orders")
        columns = {row['Field'] for row in c.fetchall()}
        new_fields = {
            "is_deleted": "TINYINT(1) DEFAULT 0 COMMENT '软删除标记'",
            "deleted_at": "DATETIME COMMENT '删除时间'",
            "deleted_by": "VARCHAR(50) COMMENT '删除人'",
            "created_by": "VARCHAR(50) COMMENT '创建人'",
            "updated_by": "VARCHAR(50) COMMENT '最后更新人'",
            "version": "INT DEFAULT 1 COMMENT '版本号'",
            "planned_start_date": "DATETIME COMMENT '计划开始日期'",
            "planned_end_date": "DATETIME COMMENT '计划结束日期'",
            "actual_start_date": "DATETIME COMMENT '实际开始日期'",
            "actual_end_date": "DATETIME COMMENT '实际结束日期'",
        }
        for col_name, col_def in new_fields.items():
            if col_name not in columns:
                c.execute(f"ALTER TABLE production_orders ADD COLUMN {col_name} {col_def}")

    # 4. 增强 process_records 表字段（高优先级）
    if "process_records" in existing_tables:
        c.execute("SHOW COLUMNS FROM process_records")
        columns = {row['Field'] for row in c.fetchall()}
        new_fields = {
            "planned_start": "DATETIME COMMENT '计划开始时间'",
            "planned_end": "DATETIME COMMENT '计划结束时间'",
            "actual_pause_minutes": "INT DEFAULT 0 COMMENT '暂停总时长(分钟)'",
            "pause_count": "INT DEFAULT 0 COMMENT '暂停次数'",
            "rework_qty": "INT DEFAULT 0 COMMENT '返工数量'",
            "scrap_qty": "INT DEFAULT 0 COMMENT '报废数量'",
            "efficiency": "DECIMAL(5,2) COMMENT '效率百分比'",
            "machine_no": "VARCHAR(30) COMMENT '机台编号'",
            "batch_no": "VARCHAR(50) COMMENT '生产批次号'",
            "shift": "VARCHAR(20) COMMENT '班次：早/中/晚'",
            "standard_minutes": "INT COMMENT '标准工时(分钟)'",
            "created_by": "VARCHAR(50) COMMENT '创建人'",
            "updated_by": "VARCHAR(50) COMMENT '更新人'",
            "is_deleted": "TINYINT(1) DEFAULT 0 COMMENT '软删除标记'",
            "deleted_at": "DATETIME COMMENT '删除时间'",
            "deleted_by": "VARCHAR(50) COMMENT '删除人'",
        }
        for col_name, col_def in new_fields.items():
            if col_name not in columns:
                c.execute(f"ALTER TABLE process_records ADD COLUMN {col_name} {col_def}")

        # 添加索引
        c.execute("SHOW INDEX FROM process_records")
        indexes = {idx['Key_name'] for idx in c.fetchall()}
        index_to_add = []
        if "batch_no" not in indexes:
            index_to_add.append("ADD INDEX idx_batch_no (batch_no)")
        if "machine_no" not in indexes:
            index_to_add.append("ADD INDEX idx_machine_no (machine_no)")
        for idx_sql in index_to_add:
            try:
                c.execute(f"ALTER TABLE process_records {idx_sql}")
            except Exception:
                pass

    # 5. 增强 inventory 表索引（中优先级）
    if "inventory" in existing_tables:
        c.execute("SHOW INDEX FROM inventory")
        indexes = {idx['Key_name'] for idx in c.fetchall()}
        index_to_add = []
        if "material_name" not in indexes:
            index_to_add.append("ADD INDEX idx_material_name (material_name)")
        if "material_type" not in indexes:
            index_to_add.append("ADD INDEX idx_material_type (material_type)")
        for idx_sql in index_to_add:
            try:
                c.execute(f"ALTER TABLE inventory {idx_sql}")
            except Exception:
                pass

    # 6. 增强 orders 表索引（中优先级）
    if "orders" in existing_tables:
        c.execute("SHOW INDEX FROM orders")
        indexes = {idx['Key_name'] for idx in c.fetchall()}
        index_to_add = []
        if "customer_name" not in indexes:
            index_to_add.append("ADD INDEX idx_customer_name (customer_name)")
        if "product_type" not in indexes:
            index_to_add.append("ADD INDEX idx_product_type (product_type)")
        if "delivery_date" not in indexes:
            index_to_add.append("ADD INDEX idx_delivery_date (delivery_date)")
        if "salesperson" not in indexes:
            index_to_add.append("ADD INDEX idx_salesperson (salesperson)")
        for idx_sql in index_to_add:
            try:
                c.execute(f"ALTER TABLE orders {idx_sql}")
            except Exception:
                pass

    # 7. 增强 shipments 表字段和索引（中优先级）
    if "shipments" in existing_tables:
        c.execute("SHOW COLUMNS FROM shipments")
        columns = {row['Field'] for row in c.fetchall()}
        if "shipment_date" not in columns:
            c.execute("ALTER TABLE shipments ADD COLUMN shipment_date DATE COMMENT '发货日期'")

        c.execute("SHOW INDEX FROM shipments")
        indexes = {idx['Key_name'] for idx in c.fetchall()}
        if "ship_date" not in indexes:
            try:
                c.execute("ALTER TABLE shipments ADD INDEX idx_ship_date (ship_date)")
            except Exception:
                pass

    # ═══════════════════════════════════════════════════════════
    # BOM物料清单扩展和生产数据收集（根据业务需求）
    # ═══════════════════════════════════════════════════════════

    # 1. 扩展 bom_list 表 - 添加更多物料属性字段
    if "bom_list" in existing_tables:
        c.execute("SHOW COLUMNS FROM bom_list")
        columns = {row['Field'] for row in c.fetchall()}
        new_fields = {
            "material_code": "VARCHAR(50) COMMENT '物料编码'",
            "material_type": "VARCHAR(50) COMMENT '物料类型'",
            "specification": "VARCHAR(100) COMMENT '规格型号'",
            "unit_weight": "DECIMAL(10,4) COMMENT '单位重量(kg/米)'",
            "standard_qty": "DECIMAL(10,4) COMMENT '标准用量'",
            "actual_qty": "DECIMAL(10,4) COMMENT '实际用量'",
            "price": "DECIMAL(10,2) COMMENT '单价'",
            "supplier": "VARCHAR(100) COMMENT '供应商'",
            "lead_time": "INT COMMENT '采购周期(天)'",
            "safety_stock": "DECIMAL(10,4) COMMENT '安全库存'",
            "location": "VARCHAR(50) COMMENT '仓库位置'",
            "batch_no": "VARCHAR(50) COMMENT '批次号'",
            "expiry_date": "DATE COMMENT '有效期'",
            "draw_no": "VARCHAR(50) COMMENT '图纸编号'",
            "version": "VARCHAR(20) COMMENT '版本号'",
        }
        for col_name, col_def in new_fields.items():
            if col_name not in columns:
                c.execute(f"ALTER TABLE bom_list ADD COLUMN {col_name} {col_def}")

    # 2. 扩展 process_records 表 - 添加用料和质量数据字段
    if "process_records" in existing_tables:
        c.execute("SHOW COLUMNS FROM process_records")
        columns = {row['Field'] for row in c.fetchall()}
        new_fields = {
            "calculated_qty": "DECIMAL(10,4) COMMENT '计算用料量'",
            "actual_used_qty": "DECIMAL(10,4) COMMENT '实际使用量'",
            "scrap_qty": "DECIMAL(10,4) COMMENT '报废量'",
            "waste_rate": "DECIMAL(5,2) COMMENT '废品率(%)'",
            "efficiency": "DECIMAL(5,2) COMMENT '效率(%)'",
            "setup_time": "DECIMAL(5,2) COMMENT '准备时间(小时)'",
            "machine_no": "VARCHAR(30) COMMENT '设备编号'",
            "shift": "VARCHAR(20) COMMENT '班次'",
            "defect_types": "TEXT COMMENT '缺陷类型记录'",
            "rework_count": "INT DEFAULT 0 COMMENT '返工次数'",
            "start_date": "DATE COMMENT '开始日期'",
            "end_date": "DATE COMMENT '结束日期'",
            "duration_days": "INT COMMENT '工序用时(自然天数)'",
        }
        for col_name, col_def in new_fields.items():
            if col_name not in columns:
                c.execute(f"ALTER TABLE process_records ADD COLUMN {col_name} {col_def}")

    # 2. 扩展 quality_records 表 - 添加工序名称字段（用于每个订单每道工序的终检唯一性）
    if "quality_records" in existing_tables:
        c.execute("SHOW COLUMNS FROM quality_records")
        columns = {row['Field'] for row in c.fetchall()}
        new_fields = {
            "process_name": "VARCHAR(50) COMMENT '工序名称'",
        }
        for col_name, col_def in new_fields.items():
            if col_name not in columns:
                c.execute(f"ALTER TABLE quality_records ADD COLUMN {col_name} {col_def}")

    # 3. 创建生产统计数据表 - 收集订单周期和质量数据
    if "production_stats" not in existing_tables:
        c.execute("""
            CREATE TABLE IF NOT EXISTS production_stats (
                id INT PRIMARY KEY AUTO_INCREMENT,
                order_id INT NOT NULL COMMENT '订单ID',
                production_id INT COMMENT '生产单ID',
                order_no VARCHAR(50) COMMENT '订单号',
                product_type VARCHAR(50) COMMENT '产品类型',
                
                -- 订单整体周期（按天计算）
                confirm_time DATETIME COMMENT '订单确认时间',
                ship_time DATETIME COMMENT '发货时间',
                receive_time DATETIME COMMENT '客户签收时间',
                order_cycle_days INT COMMENT '订单确认到发货天数',
                delivery_cycle_days INT COMMENT '发货到签收天数',
                total_cycle_days INT COMMENT '订单确认到签收总天数',
                
                -- 生产周期（按天计算）
                plan_confirm_time DATETIME COMMENT '排产确认时间',
                production_complete_time DATETIME COMMENT '生产完成时间',
                production_cycle_days INT COMMENT '排产到完成天数',
                
                -- 工序汇总数据
                total_process_count INT COMMENT '工序总数',
                avg_process_duration_days DECIMAL(5,2) COMMENT '平均工序用时(天)',
                max_process_duration_days INT COMMENT '最长工序用时(天)',
                min_process_duration_days INT COMMENT '最短工序用时(天)',
                
                -- 质量汇总数据
                total_qty INT COMMENT '总数量',
                qualified_qty INT COMMENT '合格数量',
                total_qualified_rate DECIMAL(5,2) COMMENT '总合格率(%)',
                avg_process_qualified_rate DECIMAL(5,2) COMMENT '平均工序合格率(%)',
                
                -- 用料差异汇总
                total_calculated_qty DECIMAL(12,4) COMMENT '总计算用料',
                total_actual_qty DECIMAL(12,4) COMMENT '总实际用料',
                total_material_diff DECIMAL(12,4) COMMENT '总用料差异',
                avg_material_diff_rate DECIMAL(5,2) COMMENT '平均用料差异率(%)',
                
                -- 效率数据
                total_work_hours DECIMAL(10,2) COMMENT '总工时(小时)',
                avg_efficiency DECIMAL(5,2) COMMENT '平均效率(%)',
                
                -- 状态
                stats_status VARCHAR(20) DEFAULT '计算中' COMMENT '统计状态',
                calculated_at DATETIME COMMENT '统计计算时间',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (production_id) REFERENCES production_orders(id),
                INDEX idx_order_id (order_id),
                INDEX idx_production_id (production_id),
                INDEX idx_order_no (order_no),
                INDEX idx_calculated_at (calculated_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='生产统计数据表'
        """)

    if "schedule_queue" not in existing_tables:
        c.execute("""
            CREATE TABLE IF NOT EXISTS schedule_queue (
                id INT PRIMARY KEY AUTO_INCREMENT,
                order_no VARCHAR(50) NOT NULL COMMENT '订单号',
                prod_id INT NOT NULL COMMENT '生产工单ID',
                payload TEXT COMMENT '排产数据JSON',
                status VARCHAR(20) DEFAULT 'pending' COMMENT 'pending/sending/success/failed',
                retry_count INT DEFAULT 0 COMMENT '已重试次数',
                last_error TEXT COMMENT '最后一次错误信息',
                created_at DATETIME DEFAULT NOW() COMMENT '创建时间',
                updated_at DATETIME DEFAULT NOW() COMMENT '更新时间',
                INDEX idx_order_no (order_no),
                INDEX idx_status (status),
                INDEX idx_created_at (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='排产任务发送队列'
        """)

    # ═══════════════════════════════════════════════════════════
    # 操作员表扩展 - 添加企业微信字段
    # ═══════════════════════════════════════════════════════════
    if "operators" in existing_tables:
        c.execute("SHOW COLUMNS FROM operators")
        columns = {row['Field'] for row in c.fetchall()}
        if "wechat_userid" not in columns:
            c.execute("ALTER TABLE operators ADD COLUMN wechat_userid VARCHAR(100) DEFAULT '' COMMENT '企业微信用户ID'")

    conn.commit()

def init_db():
    """初始化数据库，创建所有表"""
    conn = get_connection()
    c = conn.cursor()
    _migrate_tables(c, conn)

    c.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INT PRIMARY KEY AUTO_INCREMENT,
                order_no VARCHAR(50) UNIQUE NOT NULL,
                customer_name VARCHAR(100) NOT NULL,
                customer_phone VARCHAR(20),
                customer_address VARCHAR(255),
                customer_group VARCHAR(50),
                product_type VARCHAR(50) NOT NULL,
                material VARCHAR(50) DEFAULT '',
                mesh_size DECIMAL(10,2),
                wire_diameter DECIMAL(10,2),
                width DECIMAL(10,2),
                length DECIMAL(10,2),
                quantity INT DEFAULT 1,
                unit VARCHAR(10) DEFAULT '米',
                unit_price DECIMAL(10,2) DEFAULT 0,
                total_amount DECIMAL(10,2) DEFAULT 0,
                surface_treatment VARCHAR(50),
                special_requirements TEXT,
                delivery_date DATETIME,
                status VARCHAR(20) DEFAULT '待确认',
                remark TEXT,
                created_at DATETIME DEFAULT NOW(),
                updated_at DATETIME DEFAULT NOW(),
                extra_params TEXT
            )
        """)

    c.execute("""
            CREATE TABLE IF NOT EXISTS production_orders (
                id INT PRIMARY KEY AUTO_INCREMENT,
                order_no VARCHAR(50) UNIQUE NOT NULL,
                order_id INT NOT NULL,
                priority INT DEFAULT 5,
                plan_start DATETIME,
                plan_end DATETIME,
                actual_start DATETIME,
                actual_end DATETIME,
                assigned_to VARCHAR(50),
                status VARCHAR(20) DEFAULT '待开始',
                remark TEXT,
                created_at DATETIME DEFAULT NOW(),
                updated_at DATETIME DEFAULT NOW(),
                FOREIGN KEY (order_id) REFERENCES orders(id)
            )
        """)

    c.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INT PRIMARY KEY AUTO_INCREMENT,
                material_name VARCHAR(100) NOT NULL,
                material_type VARCHAR(50) NOT NULL,
                specification VARCHAR(100),
                quantity DECIMAL(10,2) DEFAULT 0,
                unit VARCHAR(10) DEFAULT 'kg',
                unit_price DECIMAL(10,2) DEFAULT 0,
                warehouse VARCHAR(50) DEFAULT '主仓库',
                warning_qty DECIMAL(10,2) DEFAULT 50,
                remark TEXT,
                updated_at DATETIME DEFAULT NOW()
            )
        """)

    c.execute("""
            CREATE TABLE IF NOT EXISTS inventory_records (
                id INT PRIMARY KEY AUTO_INCREMENT,
                inventory_id INT NOT NULL,
                order_id INT,
                record_type VARCHAR(20) NOT NULL,
                quantity DECIMAL(10,2) NOT NULL,
                before_qty DECIMAL(10,2),
                after_qty DECIMAL(10,2),
                operator VARCHAR(50),
                remark TEXT,
                record_date DATETIME DEFAULT NOW(),
                FOREIGN KEY (inventory_id) REFERENCES inventory(id),
                FOREIGN KEY (order_id) REFERENCES orders(id)
            )
        """)

    c.execute("""
            CREATE TABLE IF NOT EXISTS process_records (
                id INT PRIMARY KEY AUTO_INCREMENT,
                order_id INT NOT NULL,
                production_id INT,
                process_name VARCHAR(50) NOT NULL,
                process_seq INT DEFAULT 1,
                planned_qty INT,
                completed_qty INT DEFAULT 0,
                qualified_qty INT DEFAULT 0,
                worker VARCHAR(50),
                work_hours DECIMAL(10,2) DEFAULT 0,
                status VARCHAR(20) DEFAULT '待开始',
                remark TEXT,
                record_date DATETIME DEFAULT NOW(),
                start_time DATETIME,
                end_time DATETIME,
                is_outsource TINYINT(1) DEFAULT 0,
                outsource_remark TEXT,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (production_id) REFERENCES production_orders(id)
            )
        """)

    # 工序表（供微信报工使用）
    c.execute("""
            CREATE TABLE IF NOT EXISTS processes (
                id INT PRIMARY KEY AUTO_INCREMENT,
                prod_order_id INT NOT NULL,
                process_name VARCHAR(50) NOT NULL,
                process_seq INT DEFAULT 1,
                planned_qty INT DEFAULT 0,
                completed_qty DECIMAL(10,2) DEFAULT 0,
                qualified_qty DECIMAL(10,2) DEFAULT 0,
                status VARCHAR(20) DEFAULT '待开始',
                operator VARCHAR(50),
                remarks TEXT,
                actual_end DATETIME,
                created_at DATETIME DEFAULT NOW(),
                updated_at DATETIME DEFAULT NOW(),
                FOREIGN KEY (prod_order_id) REFERENCES production_orders(id)
            )
        """)

    c.execute("""
            CREATE TABLE IF NOT EXISTS quality_records (
                id INT PRIMARY KEY AUTO_INCREMENT,
                order_id INT NOT NULL,
                production_id INT,
                inspection_type VARCHAR(20) NOT NULL,
                inspection_items TEXT,
                result VARCHAR(20) NOT NULL,
                defect_description TEXT,
                defect_qty INT DEFAULT 0,
                handling_method TEXT,
                inspector VARCHAR(50),
                remark TEXT,
                record_date DATETIME DEFAULT NOW(),
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (production_id) REFERENCES production_orders(id)
            )
        """)

    c.execute("""
            CREATE TABLE IF NOT EXISTS quality_record_items (
                id INT PRIMARY KEY AUTO_INCREMENT,
                record_id INT NOT NULL,
                inspection_item VARCHAR(100) NOT NULL,
                measured_value TEXT,
                standard_value TEXT,
                tolerance TEXT,
                is_passed TINYINT(1) DEFAULT 1,
                FOREIGN KEY (record_id) REFERENCES quality_records(id) ON DELETE CASCADE
            )
        """)

    c.execute("""
            CREATE TABLE IF NOT EXISTS finished_goods (
                id INT PRIMARY KEY AUTO_INCREMENT,
                order_id INT NOT NULL,
                warehouse VARCHAR(50) DEFAULT '成品仓库',
                quantity DECIMAL(10,2) DEFAULT 0,
                unit VARCHAR(10) DEFAULT '米',
                in_date DATETIME DEFAULT NOW(),
                status VARCHAR(20) DEFAULT '在库',
                remark TEXT,
                FOREIGN KEY (order_id) REFERENCES orders(id)
            )
        """)

    c.execute("""
            CREATE TABLE IF NOT EXISTS shipments (
                id INT PRIMARY KEY AUTO_INCREMENT,
                shipment_no VARCHAR(50) UNIQUE NOT NULL,
                order_id INT NOT NULL,
                finished_goods_id INT,
                warehouse VARCHAR(50),
                ship_quantity DECIMAL(10,2),
                unit VARCHAR(10) DEFAULT '米',
                logistics_company VARCHAR(100),
                tracking_no VARCHAR(100),
                ship_date DATETIME,
                recipient VARCHAR(100),
                recipient_phone VARCHAR(20),
                recipient_address VARCHAR(255),
                freight DECIMAL(10,2) DEFAULT 0,
                status VARCHAR(20) DEFAULT '待发货',
                remark TEXT,
                created_at DATETIME DEFAULT NOW(),
                updated_at DATETIME DEFAULT NOW(),
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (finished_goods_id) REFERENCES finished_goods(id)
            )
        """)

    c.execute("""
            CREATE TABLE IF NOT EXISTS shipment_tracks (
                id INT PRIMARY KEY AUTO_INCREMENT,
                shipment_id INT NOT NULL,
                tracking_no VARCHAR(100),
                state VARCHAR(10) DEFAULT '0',
                state_text VARCHAR(50),
                traces TEXT,
                company_code VARCHAR(50),
                query_time DATETIME,
                created_at DATETIME DEFAULT NOW(),
                FOREIGN KEY (shipment_id) REFERENCES shipments(id)
            )
        """)

    c.execute("""
            CREATE TABLE IF NOT EXISTS status_logs (
                id INT PRIMARY KEY AUTO_INCREMENT,
                table_name VARCHAR(50) NOT NULL,
                record_id INT NOT NULL,
                old_status VARCHAR(50),
                new_status VARCHAR(50),
                operator VARCHAR(50),
                remark TEXT,
                created_at DATETIME DEFAULT NOW()
            )
        """)

    c.execute("""
            CREATE TABLE IF NOT EXISTS order_logs (
                id INT PRIMARY KEY AUTO_INCREMENT,
                order_id INT NOT NULL,
                order_no VARCHAR(50) NOT NULL,
                action VARCHAR(50) NOT NULL,
                operator VARCHAR(50) DEFAULT '系统',
                details TEXT,
                created_at DATETIME DEFAULT NOW(),
                FOREIGN KEY (order_id) REFERENCES orders(id)
            )
        """)

    c.execute("""
            CREATE TABLE IF NOT EXISTS operation_logs (
                id INT PRIMARY KEY AUTO_INCREMENT,
                order_id INT NOT NULL,
                order_no VARCHAR(50) NOT NULL,
                module VARCHAR(50) NOT NULL,
                action VARCHAR(50) NOT NULL,
                operator VARCHAR(50) DEFAULT '系统',
                details TEXT,
                created_at DATETIME DEFAULT NOW(),
                FOREIGN KEY (order_id) REFERENCES orders(id)
            )
        """)

    c.execute("""
            CREATE TABLE IF NOT EXISTS order_materials (
                id INT PRIMARY KEY AUTO_INCREMENT,
                order_id INT NOT NULL,
                material_name VARCHAR(100) NOT NULL,
                material_type VARCHAR(50) DEFAULT '原材料',
                spec VARCHAR(100),
                required_qty DECIMAL(10,2) DEFAULT 0,
                prepared_qty DECIMAL(10,2) DEFAULT 0,
                unit VARCHAR(10) DEFAULT 'kg',
                prep_status VARCHAR(20) DEFAULT '待备料',
                warehouse VARCHAR(50) DEFAULT '主仓库',
                locked TINYINT(1) DEFAULT 1,
                remark TEXT,
                created_at DATETIME DEFAULT NOW(),
                updated_at DATETIME DEFAULT NOW(),
                FOREIGN KEY (order_id) REFERENCES orders(id),
                UNIQUE(order_id, material_name)
            )
        """)

    c.execute("""
            CREATE TABLE IF NOT EXISTS material_history (
                id INT PRIMARY KEY AUTO_INCREMENT,
                order_id INT NOT NULL,
                action VARCHAR(50) NOT NULL,
                material_name VARCHAR(100),
                detail TEXT,
                operator VARCHAR(50) DEFAULT '系统',
                created_at DATETIME DEFAULT NOW(),
                FOREIGN KEY (order_id) REFERENCES orders(id)
            )
        """)

    c.execute("""
            CREATE TABLE IF NOT EXISTS bom_list (
                id INT PRIMARY KEY AUTO_INCREMENT,
                product_type VARCHAR(50) NOT NULL,
                material VARCHAR(50) NOT NULL,
                steel_weight DECIMAL(10,2) DEFAULT 0,
                steel_unit VARCHAR(10) DEFAULT 'kg/米',
                packaging_materials TEXT,
                surface_treatment TEXT,
                production_process TEXT,
                waste_rate DECIMAL(5,2) DEFAULT 5,
                unit VARCHAR(10) DEFAULT '米',
                remark TEXT,
                created_at DATETIME DEFAULT NOW(),
                updated_at DATETIME DEFAULT NOW(),
                UNIQUE(product_type, material)
            )
        """)

    c.execute("""
            CREATE TABLE IF NOT EXISTS product_types (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(50) UNIQUE NOT NULL,
                is_preset TINYINT(1) DEFAULT 0,
                created_at DATETIME DEFAULT NOW()
            )
        """)

    c.execute("""
            CREATE TABLE IF NOT EXISTS material_rules (
                id INT PRIMARY KEY AUTO_INCREMENT,
                product_type VARCHAR(50) NOT NULL,
                material_param VARCHAR(50) NOT NULL,
                material_name_template VARCHAR(100) NOT NULL,
                spec_field VARCHAR(50),
                spec_unit VARCHAR(20),
                qty_field VARCHAR(50),
                qty_formula VARCHAR(100),
                qty_unit VARCHAR(20),
                enabled TINYINT(1) DEFAULT 1,
                created_at DATETIME DEFAULT NOW(),
                updated_at DATETIME DEFAULT NOW(),
                UNIQUE(product_type, material_param)
            )
        """)

    c.execute("""
            CREATE TABLE IF NOT EXISTS alert_records (
                id INT PRIMARY KEY AUTO_INCREMENT,
                alert_type VARCHAR(50) NOT NULL,
                record_id INT NOT NULL,
                is_read TINYINT(1) DEFAULT 0,
                is_dismissed TINYINT(1) DEFAULT 0,
                created_at DATETIME DEFAULT NOW()
            )
        """)

    c.execute("""
            CREATE TABLE IF NOT EXISTS operators (
                id INT PRIMARY KEY AUTO_INCREMENT,
                operator_id VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(50) NOT NULL,
                role VARCHAR(20) DEFAULT '操作员',
                password VARCHAR(255) NOT NULL,
                password_salt VARCHAR(255) NOT NULL,
                status VARCHAR(20) DEFAULT '正常',
                created_at DATETIME DEFAULT NOW(),
                updated_at DATETIME DEFAULT NOW(),
                last_login DATETIME
            )
        """)

    c.execute("""
            CREATE TABLE IF NOT EXISTS operator_logs (
                id INT PRIMARY KEY AUTO_INCREMENT,
                operator_id VARCHAR(50),
                operator_name VARCHAR(50),
                action VARCHAR(100),
                target_type VARCHAR(50),
                target_id VARCHAR(50),
                details TEXT,
                ip_address VARCHAR(50),
                created_at DATETIME DEFAULT NOW()
            )
        """)

    c.execute("""
            CREATE TABLE IF NOT EXISTS material_densities (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(50) UNIQUE NOT NULL,
                density DECIMAL(10,2) NOT NULL,
                is_preset TINYINT(1) DEFAULT 0,
                created_at DATETIME DEFAULT NOW(),
                updated_at DATETIME DEFAULT NOW()
            )
        """)

    c.execute("""
            CREATE TABLE IF NOT EXISTS custom_dim_params (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(50) UNIQUE NOT NULL,
                unit VARCHAR(20) NOT NULL DEFAULT 'mm',
                created_at DATETIME DEFAULT NOW()
            )
        """)

    c.execute("""
            CREATE TABLE IF NOT EXISTS order_templates (
                id INT PRIMARY KEY AUTO_INCREMENT,
                product_type VARCHAR(50) NOT NULL,
                template_name VARCHAR(50) NOT NULL,
                values_json TEXT,
                order_json TEXT,
                created_at DATETIME DEFAULT NOW(),
                updated_at DATETIME DEFAULT NOW(),
                UNIQUE(product_type, template_name)
            )
        """)

    c.execute("""
            CREATE TABLE IF NOT EXISTS custom_params (
                id INT PRIMARY KEY AUTO_INCREMENT,
                params_json TEXT,
                created_at DATETIME DEFAULT NOW(),
                updated_at DATETIME DEFAULT NOW()
            )
        """)

    c.execute("""
            CREATE TABLE IF NOT EXISTS material_templates (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(50) UNIQUE NOT NULL,
                description TEXT,
                materials_json TEXT,
                created_at DATETIME DEFAULT NOW(),
                updated_at DATETIME DEFAULT NOW()
            )
        """)

    c.execute("""
            CREATE TABLE IF NOT EXISTS process_templates (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(50) UNIQUE NOT NULL,
                data_json TEXT,
                created_at DATETIME DEFAULT NOW(),
                updated_at DATETIME DEFAULT NOW()
            )
        """)

    c.execute("""
            CREATE TABLE IF NOT EXISTS process_rules (
                id INT PRIMARY KEY AUTO_INCREMENT,
                rule_name VARCHAR(100) NOT NULL,
                condition_json TEXT,
                action_json TEXT,
                priority INT DEFAULT 5,
                enabled TINYINT(1) DEFAULT 1,
                created_at DATETIME DEFAULT NOW(),
                updated_at DATETIME DEFAULT NOW()
            )
        """)

    c.execute("""
            CREATE TABLE IF NOT EXISTS material_rules_templates (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(50) UNIQUE NOT NULL,
                description TEXT,
                rules_json TEXT,
                created_at DATETIME DEFAULT NOW(),
                updated_at DATETIME DEFAULT NOW()
            )
        """)

    c.execute("""
            CREATE TABLE IF NOT EXISTS process_rules_templates (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100) NOT NULL,
                product_type VARCHAR(50) DEFAULT '',
                conditions_json TEXT,
                actions_json TEXT,
                priority INT DEFAULT 5,
                description TEXT,
                created_at DATETIME DEFAULT NOW(),
                updated_at DATETIME DEFAULT NOW()
            )
        """)

    c.execute("""
            CREATE TABLE IF NOT EXISTS custom_mat_params (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(50) UNIQUE NOT NULL,
                created_at DATETIME DEFAULT NOW()
            )
        """)

    c.execute("SELECT COUNT(*) FROM material_densities")
    result = c.fetchone()
    count = next(iter(result.values())) if result else 0
    if count == 0:
        preset_densities = [
            ("304不锈钢", 7930, 1),
            ("316不锈钢", 7980, 1),
            ("316L不锈钢", 7980, 1),
            ("310S不锈钢", 7980, 1),
            ("201不锈钢", 7930, 1),
            ("碳钢镀锌", 7850, 1),
            ("铝合金", 2700, 1),
            ("铜合金", 8500, 1),
            ("钛合金", 4510, 1),
        ]
        c.executemany("""
            INSERT INTO material_densities (name, density, is_preset) VALUES (%s, %s, %s)
        """, preset_densities)

    c.execute("SELECT COUNT(*) FROM product_types")
    result = c.fetchone()
    count = next(iter(result.values())) if result else 0
    if count == 0:
        preset_product_types = [
            ("眼镜网带", 1),
            ("工艺网带", 1),
            ("汽车配件", 1),
            ("食品网带", 1),
            ("工业网带", 1),
        ]
        c.executemany("""
            INSERT INTO product_types (name, is_preset) VALUES (%s, %s)
        """, preset_product_types)

    c.execute("SELECT COUNT(*) FROM operators WHERE operator_id='admin'")
    result = c.fetchone()
    count = next(iter(result.values())) if result else 0
    if count == 0:
        from utils.password_hasher import hash_password
        init_password = os.getenv('INIT_ADMIN_PASSWORD')
        if not init_password:
            logger.warning("[DB] 未设置INIT_ADMIN_PASSWORD环境变量，请通过.env文件配置管理员初始密码")
            init_password = None
        if init_password:
            pwd_hash, salt = hash_password(init_password)
            c.execute("""
                INSERT INTO operators (operator_id, name, role, password, password_salt, status)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, ('admin', '管理员', '管理员', pwd_hash, salt, '正常'))
        else:
            logger.warning("[DB] 管理员账号未创建，请先在.env中设置INIT_ADMIN_PASSWORD后重启系统")

    # ═══════════════════════════════════════════════════════════
    # Batch 1: 新增数据表（根据数据库结构优化计划）
    # ═══════════════════════════════════════════════════════════

    # T1.2.1: customer_contacts 客户联系人表
    c.execute("""
        CREATE TABLE IF NOT EXISTS customer_contacts (
            id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            customer_id INT UNSIGNED NOT NULL,
            name VARCHAR(64) NOT NULL,
            phone VARCHAR(32) DEFAULT '',
            email VARCHAR(128) DEFAULT '',
            position VARCHAR(64) DEFAULT '',
            is_primary TINYINT(1) DEFAULT 0,
            remark TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            created_by VARCHAR(64) DEFAULT '',
            updated_by VARCHAR(64) DEFAULT '',
            is_deleted TINYINT(1) DEFAULT 0,
            deleted_at DATETIME,
            deleted_by VARCHAR(64) DEFAULT '',
            version INT DEFAULT 1,
            INDEX idx_customer_id (customer_id),
            INDEX idx_is_deleted (is_deleted),
            FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE ON UPDATE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)

    # T1.2.2: customer_groups 客户分组表
    c.execute("""
        CREATE TABLE IF NOT EXISTS customer_groups (
            id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            group_name VARCHAR(64) NOT NULL,
            group_desc VARCHAR(256) DEFAULT '',
            sort_order INT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            created_by VARCHAR(64) DEFAULT '',
            updated_by VARCHAR(64) DEFAULT '',
            is_deleted TINYINT(1) DEFAULT 0,
            deleted_at DATETIME,
            deleted_by VARCHAR(64) DEFAULT '',
            version INT DEFAULT 1,
            UNIQUE KEY uk_group_name (group_name),
            INDEX idx_is_deleted (is_deleted)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)

    # T1.2.3: order_items 订单明细表
    c.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            order_id INT UNSIGNED NOT NULL,
            item_no INT DEFAULT 0,
            product_name VARCHAR(256) NOT NULL,
            material VARCHAR(128) DEFAULT '',
            spec VARCHAR(256) DEFAULT '',
            length DECIMAL(10,2) DEFAULT 0,
            width DECIMAL(10,2) DEFAULT 0,
            unit VARCHAR(16) DEFAULT '件',
            quantity DECIMAL(12,2) NOT NULL,
            unit_price DECIMAL(10,2) DEFAULT 0,
            amount DECIMAL(12,2) DEFAULT 0,
            delivery_date DATE,
            remark TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            created_by VARCHAR(64) DEFAULT '',
            updated_by VARCHAR(64) DEFAULT '',
            is_deleted TINYINT(1) DEFAULT 0,
            deleted_at DATETIME,
            deleted_by VARCHAR(64) DEFAULT '',
            version INT DEFAULT 1,
            INDEX idx_order_id (order_id),
            INDEX idx_is_deleted (is_deleted),
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE ON UPDATE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)

    # ═══════════════════════════════════════════════════════════
    # Batch 2: 流程管理 + 消息通知 + 报修管理表（根据 DESIGN_数据库架构优化.md）
    # ═══════════════════════════════════════════════════════════

    # T1.4.1: dispatch_rules 调度规则表
    c.execute("""
        CREATE TABLE IF NOT EXISTS dispatch_rules (
            id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            rule_key VARCHAR(64) NOT NULL UNIQUE COMMENT '规则键名',
            display_name VARCHAR(128) NOT NULL COMMENT '显示名称',
            rule_type VARCHAR(32) NOT NULL COMMENT '规则类型: string/number/boolean/select',
            rule_value TEXT NOT NULL COMMENT '规则值',
            default_value TEXT COMMENT '默认值',
            description VARCHAR(256) DEFAULT '' COMMENT '描述',
            sort_order INT DEFAULT 0 COMMENT '排序',
            is_active TINYINT(1) DEFAULT 1 COMMENT '是否启用',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            created_by VARCHAR(64) DEFAULT '' COMMENT '创建人',
            updated_by VARCHAR(64) DEFAULT '' COMMENT '最后更新人',
            is_deleted TINYINT(1) DEFAULT 0 COMMENT '软删除标记',
            deleted_at DATETIME COMMENT '删除时间',
            deleted_by VARCHAR(64) DEFAULT '' COMMENT '删除人',
            version INT DEFAULT 1 COMMENT '版本号',
            INDEX idx_dr_type (rule_type),
            INDEX idx_dr_is_deleted (is_deleted)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='调度规则表'
    """)

    # T1.4.2: flow_templates 流程模板表
    c.execute("""
        CREATE TABLE IF NOT EXISTS flow_templates (
            id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            template_id VARCHAR(64) NOT NULL UNIQUE COMMENT '模板标识',
            template_name VARCHAR(128) NOT NULL COMMENT '模板名称',
            flow_type VARCHAR(32) NOT NULL COMMENT '流程类型',
            steps TEXT NOT NULL COMMENT '步骤定义JSON',
            message_templates TEXT COMMENT '绑定的消息模板ID JSON',
            is_builtin TINYINT(1) DEFAULT 0 COMMENT '是否内置模板',
            is_active TINYINT(1) DEFAULT 1 COMMENT '是否启用',
            sort_order INT DEFAULT 0 COMMENT '排序',
            remark VARCHAR(256) DEFAULT '' COMMENT '备注',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            created_by VARCHAR(64) DEFAULT '' COMMENT '创建人',
            updated_by VARCHAR(64) DEFAULT '' COMMENT '最后更新人',
            is_deleted TINYINT(1) DEFAULT 0 COMMENT '软删除标记',
            deleted_at DATETIME COMMENT '删除时间',
            deleted_by VARCHAR(64) DEFAULT '' COMMENT '删除人',
            version INT DEFAULT 1 COMMENT '版本号',
            INDEX idx_ft_type (flow_type),
            INDEX idx_ft_is_deleted (is_deleted)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='流程模板表'
    """)

    # T1.4.3: flow_matching_rules 流程匹配规则表
    c.execute("""
        CREATE TABLE IF NOT EXISTS flow_matching_rules (
            id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            rule_name VARCHAR(128) NOT NULL COMMENT '规则名称',
            priority INT DEFAULT 0 COMMENT '优先级',
            match_conditions TEXT NOT NULL COMMENT '匹配条件JSON',
            template_id VARCHAR(64) NOT NULL COMMENT '关联 flow_templates.template_id',
            target_chat_id VARCHAR(64) DEFAULT '' COMMENT '目标群聊',
            is_active TINYINT(1) DEFAULT 1 COMMENT '是否启用',
            sort_order INT DEFAULT 0 COMMENT '排序',
            remark VARCHAR(256) DEFAULT '' COMMENT '备注',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            created_by VARCHAR(64) DEFAULT '' COMMENT '创建人',
            updated_by VARCHAR(64) DEFAULT '' COMMENT '最后更新人',
            is_deleted TINYINT(1) DEFAULT 0 COMMENT '软删除标记',
            deleted_at DATETIME COMMENT '删除时间',
            deleted_by VARCHAR(64) DEFAULT '' COMMENT '删除人',
            version INT DEFAULT 1 COMMENT '版本号',
            INDEX idx_fmr_priority (priority),
            INDEX idx_fmr_is_deleted (is_deleted)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='流程匹配规则表'
    """)

    # T1.3.1: message_templates 消息模板表
    c.execute("""
        CREATE TABLE IF NOT EXISTS message_templates (
            id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            template_id VARCHAR(64) NOT NULL UNIQUE COMMENT '模板标识',
            template_name VARCHAR(128) NOT NULL COMMENT '模板名称',
            template_type VARCHAR(32) DEFAULT 'text' COMMENT '模板类型: text/card/news',
            title VARCHAR(256) DEFAULT '' COMMENT '标题',
            content TEXT NOT NULL COMMENT '内容',
            variables TEXT COMMENT '变量定义JSON',
            is_builtin TINYINT(1) DEFAULT 0 COMMENT '是否内置模板',
            is_active TINYINT(1) DEFAULT 1 COMMENT '是否启用',
            sort_order INT DEFAULT 0 COMMENT '排序',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            created_by VARCHAR(64) DEFAULT '' COMMENT '创建人',
            updated_by VARCHAR(64) DEFAULT '' COMMENT '最后更新人',
            is_deleted TINYINT(1) DEFAULT 0 COMMENT '软删除标记',
            deleted_at DATETIME COMMENT '删除时间',
            deleted_by VARCHAR(64) DEFAULT '' COMMENT '删除人',
            version INT DEFAULT 1 COMMENT '版本号',
            INDEX idx_mt_type (template_type),
            INDEX idx_mt_is_deleted (is_deleted)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='消息模板表'
    """)

    # T1.3.2: message_logs 消息日志表（日志表，仅 created_at 审计字段）
    c.execute("""
        CREATE TABLE IF NOT EXISTS message_logs (
            id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            msg_id VARCHAR(64) COMMENT '微信消息ID',
            template_id VARCHAR(64) COMMENT '模板ID',
            target_type VARCHAR(32) NOT NULL COMMENT '目标类型: user/group',
            target_id VARCHAR(64) NOT NULL COMMENT '用户ID或群ID',
            title VARCHAR(256) DEFAULT '' COMMENT '标题',
            content TEXT COMMENT '内容',
            msg_type VARCHAR(16) DEFAULT 'text' COMMENT '消息类型: text/card/news',
            status VARCHAR(16) DEFAULT 'sent' COMMENT '状态: sent/delivered/failed',
            error_msg TEXT COMMENT '错误信息',
            related_type VARCHAR(32) DEFAULT '' COMMENT '关联业务类型',
            related_id VARCHAR(64) DEFAULT '' COMMENT '关联业务ID',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            sent_at DATETIME COMMENT '发送时间',
            INDEX idx_ml_target (target_id),
            INDEX idx_ml_status (status),
            INDEX idx_ml_created (created_at),
            INDEX idx_ml_related (related_type, related_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='消息发送日志表'
    """)

    # T1.3.3: notification_queue 通知队列表（队列表，仅 created_at 审计字段）
    c.execute("""
        CREATE TABLE IF NOT EXISTS notification_queue (
            id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            target_type VARCHAR(32) NOT NULL COMMENT '目标类型: user/group',
            target_id VARCHAR(64) NOT NULL COMMENT '目标ID',
            title VARCHAR(256) DEFAULT '' COMMENT '标题',
            content TEXT NOT NULL COMMENT '内容',
            msg_type VARCHAR(16) DEFAULT 'text' COMMENT '消息类型',
            priority INT DEFAULT 0 COMMENT '优先级',
            status VARCHAR(16) DEFAULT 'pending' COMMENT '状态: pending/sending/sent/failed',
            retry_count INT DEFAULT 0 COMMENT '已重试次数',
            max_retries INT DEFAULT 3 COMMENT '最大重试次数',
            error_msg TEXT COMMENT '错误信息',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            sent_at DATETIME COMMENT '发送时间',
            INDEX idx_nq_status (status, priority)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='通知队列表'
    """)

    # T1.5.1: repair_categories 报修分类表（引用表，仅 created_at/updated_at 审计字段）
    c.execute("""
        CREATE TABLE IF NOT EXISTS repair_categories (
            id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            category_name VARCHAR(128) NOT NULL UNIQUE COMMENT '分类名称',
            category_desc VARCHAR(256) DEFAULT '' COMMENT '分类描述',
            sort_order INT DEFAULT 0 COMMENT '排序',
            is_active TINYINT(1) DEFAULT 1 COMMENT '是否启用',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='报修分类表'
    """)

    # T1.5.2: repair_records 报修记录表（完整核心表，8字段审计）
    c.execute("""
        CREATE TABLE IF NOT EXISTS repair_records (
            id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            category_id INT UNSIGNED COMMENT '关联报修分类ID',
            equipment_name VARCHAR(128) NOT NULL COMMENT '设备名称',
            fault_desc TEXT NOT NULL COMMENT '故障描述',
            reporter VARCHAR(64) DEFAULT '' COMMENT '报修人',
            report_date DATETIME COMMENT '报修日期',
            severity VARCHAR(16) DEFAULT 'normal' COMMENT '严重程度: low/normal/high/emergency',
            status VARCHAR(16) DEFAULT 'reported' COMMENT '状态: reported/in_progress/completed/closed',
            assigned_to VARCHAR(64) DEFAULT '' COMMENT '指派给',
            repair_desc TEXT COMMENT '维修描述',
            repair_date DATETIME COMMENT '维修日期',
            completed_by VARCHAR(64) DEFAULT '' COMMENT '维修完成人',
            remark TEXT COMMENT '备注',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            created_by VARCHAR(64) DEFAULT '' COMMENT '创建人',
            updated_by VARCHAR(64) DEFAULT '' COMMENT '最后更新人',
            is_deleted TINYINT(1) DEFAULT 0 COMMENT '软删除标记',
            deleted_at DATETIME COMMENT '删除时间',
            deleted_by VARCHAR(64) DEFAULT '' COMMENT '删除人',
            version INT DEFAULT 1 COMMENT '版本号',
            INDEX idx_rr_status (status),
            INDEX idx_rr_reporter (reporter),
            INDEX idx_rr_is_deleted (is_deleted),
            FOREIGN KEY (category_id) REFERENCES repair_categories(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='报修记录表'
    """)

    conn.commit()
    conn.close()
    logger.info("[DB] 数据库初始化完成")

def generate_order_no():
    """生成订单号 格式: ORD-YYYYMMDDXXXX"""
    from datetime import datetime
    conn = get_connection()
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y%m%d")
    cursor.execute(
        "SELECT COUNT(*) as cnt FROM orders WHERE order_no LIKE %s",
        (f"ORD-{today}%",)
    )
    row = cursor.fetchone()
    seq = (row["cnt"] if row else 0) + 1
    cursor.close()
    conn.close()
    return f"ORD-{today}{seq:04d}"

def generate_shipment_no():
    """生成发货单号 格式: SHP-YYYYMMDDXXXX"""
    from datetime import datetime
    conn = get_connection()
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y%m%d")
    cursor.execute(
        "SELECT COUNT(*) as cnt FROM shipments WHERE shipment_no LIKE %s",
        (f"SHP-{today}%",)
    )
    row = cursor.fetchone()
    seq = (row["cnt"] if row else 0) + 1
    cursor.close()
    conn.close()
    return f"SHP-{today}{seq:04d}"

def log_status_change(table_name, record_id, old_status, new_status, operator="系统", remark=""):
    """记录状态变更日志"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO status_logs (table_name, record_id, old_status, new_status, operator, remark)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (table_name, record_id, old_status, new_status, operator, remark)
    )
    conn.commit()
    cursor.close()
    conn.close()

def ensure_unique_indexes():
    """确保数据库唯一约束索引存在"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        indexes = [
            ("idx_orders_order_no", "CREATE UNIQUE INDEX idx_orders_order_no ON orders(order_no)"),
            ("idx_production_orders_order_id", "CREATE UNIQUE INDEX idx_production_orders_order_id ON production_orders(order_id)"),
            ("idx_order_materials_unique", "CREATE UNIQUE INDEX idx_order_materials_unique ON order_materials(order_id, material_name)"),
            ("idx_shipments_shipment_no", "CREATE UNIQUE INDEX idx_shipments_shipment_no ON shipments(shipment_no)"),
            ("idx_shipment_tracks_shipment_id", "CREATE INDEX idx_shipment_tracks_shipment_id ON shipment_tracks(shipment_id)"),
            ("idx_shipment_tracks_tracking_no", "CREATE INDEX idx_shipment_tracks_tracking_no ON shipment_tracks(tracking_no)"),
            ("idx_material_rules_unique", "CREATE UNIQUE INDEX idx_material_rules_unique ON material_rules(product_type, material_param)"),
        ]
        for idx_name, create_sql in indexes:
            try:
                cursor.execute(f"DROP INDEX {idx_name} ON {idx_name.split('_')[2] if len(idx_name.split('_')) > 2 else idx_name}")
            except Exception as e:
                logger.debug(f"[DB] 删除索引 {idx_name} 失败(可能不存在): {e}")
            try:
                cursor.execute(create_sql)
            except Exception as e:
                logger.warning(f"[DB] 创建索引 {idx_name} 失败: {e}")
        
        conn.commit()
        cursor.close()
        logger.info("[DB] 唯一约束索引检查完成")
    except Exception as e:
        cursor.close()
        logger.error(f"[DB] 唯一约束索引检查异常: {e}")
    finally:
        conn.close()

def ensure_performance_indexes():
    """确保数据库性能索引存在，加速常见查询

    优化以下查询模式：
    - orders: status + delivery_date（工单筛选+排序）
    - orders: customer_name（客户搜索）
    - production_orders: order_no（订单号精确查询）
    - quality_records: order_id + result（质检统计）
    - inventory: material_name（物料查找）
    - shipments: status（发货状态筛选）
    - finished_goods: status + in_date（成品库存查询）
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        indexes = [
            ("idx_orders_status_delivery", "CREATE INDEX idx_orders_status_delivery ON orders(status, delivery_date)"),
            ("idx_orders_customer", "CREATE INDEX idx_orders_customer ON orders(customer_name)"),
            ("idx_production_wo_no", "CREATE INDEX idx_production_wo_no ON production_orders(order_no)"),
            ("idx_quality_order_result", "CREATE INDEX idx_quality_order_result ON quality_records(order_id, result)"),
            ("idx_inventory_name", "CREATE INDEX idx_inventory_name ON inventory(material_name)"),
            ("idx_shipments_status", "CREATE INDEX idx_shipments_status ON shipments(status)"),
            ("idx_finished_goods_status", "CREATE INDEX idx_finished_goods_status ON finished_goods(status)"),
            ("idx_finished_goods_order", "CREATE INDEX idx_finished_goods_order ON finished_goods(order_id)"),
        ]
        for idx_name, create_sql in indexes:
            try:
                cursor.execute(f"DROP INDEX {idx_name} ON {idx_name.split('_')[2] if len(idx_name.split('_')) > 2 else idx_name}")
            except Exception as e:
                logger.debug(f"[DB] 删除性能索引 {idx_name} 失败(可能不存在): {e}")
            try:
                cursor.execute(create_sql)
            except Exception as e:
                logger.warning(f"[DB] 创建性能索引 {idx_name} 失败: {e}")

        conn.commit()
        cursor.close()
        logger.info("[DB] 性能索引检查完成")
    except Exception as e:
        cursor.close()
        logger.error(f"[DB] 性能索引检查异常: {e}")
    finally:
        conn.close()