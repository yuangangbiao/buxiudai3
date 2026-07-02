#!/usr/bin/env python3
"""
CI init schema - create 9 business tables if not exist
Run BEFORE run_stage_1_ddl.py
"""
import os
import pymysql

DB_CONFIG = {
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'port': 3306,
    'user': 'root',
    'password': '88888888',
    'database': 'container_center',
}

DDL_STATEMENTS = [
    # 1. process_sub_steps
    """CREATE TABLE IF NOT EXISTS process_sub_steps (
        id VARCHAR(50) NOT NULL PRIMARY KEY,
        order_no VARCHAR(50),
        process_code VARCHAR(10),
        step_name VARCHAR(100),
        quantity DECIMAL(10,2) DEFAULT 0.00,
        operator VARCHAR(50),
        status VARCHAR(20) NOT NULL DEFAULT 'pending',
        completed_qty DECIMAL(10,2) NOT NULL DEFAULT 0.00,
        qualified_qty DECIMAL(10,2) NOT NULL DEFAULT 0.00,
        flow_type VARCHAR(64) NOT NULL DEFAULT 'production',
        target_operator VARCHAR(64) NOT NULL DEFAULT '',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        is_deleted TINYINT(1) NOT NULL DEFAULT 0,
        created_by VARCHAR(64) NOT NULL DEFAULT 'system',
        updated_by VARCHAR(64) NOT NULL DEFAULT 'system',
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        KEY idx_status (status),
        KEY idx_target_operator (target_operator),
        KEY idx_created_by (created_by)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    # 2. material_records
    """CREATE TABLE IF NOT EXISTS material_records (
        id VARCHAR(64) NOT NULL PRIMARY KEY,
        order_no VARCHAR(64),
        title VARCHAR(255),
        status VARCHAR(32) DEFAULT 'pending',
        priority VARCHAR(32) DEFAULT 'normal',
        target_operator VARCHAR(64),
        operator_id VARCHAR(64),
        planned_qty INT DEFAULT 0,
        completed_qty INT DEFAULT 0,
        actual_qty INT DEFAULT 0,
        source VARCHAR(128),
        content JSON,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        distributed_at DATETIME,
        acknowledged_at DATETIME,
        completed_at DATETIME,
        is_deleted TINYINT(1) NOT NULL DEFAULT 0,
        created_by VARCHAR(64) NOT NULL DEFAULT 'system',
        updated_by VARCHAR(64) NOT NULL DEFAULT 'system',
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        KEY idx_status (status),
        KEY idx_order_no (order_no),
        KEY idx_target_operator (target_operator)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    # 3. quality_records
    """CREATE TABLE IF NOT EXISTS quality_records (
        id VARCHAR(64) NOT NULL PRIMARY KEY,
        order_no VARCHAR(64),
        status VARCHAR(32) DEFAULT 'pending',
        inspection_type VARCHAR(20),
        result VARCHAR(20),
        inspector VARCHAR(50),
        target_operator VARCHAR(64),
        operator_id VARCHAR(64),
        defect_description TEXT,
        defect_qty INT DEFAULT 0,
        handling_method TEXT,
        remark TEXT,
        record_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        is_deleted TINYINT(1) NOT NULL DEFAULT 0,
        created_by VARCHAR(64) NOT NULL DEFAULT 'system',
        updated_by VARCHAR(64) NOT NULL DEFAULT 'system',
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        KEY idx_order_no (order_no),
        KEY idx_status (status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    # 4. outsource_records
    """CREATE TABLE IF NOT EXISTS outsource_records (
        id VARCHAR(64) NOT NULL PRIMARY KEY,
        order_no VARCHAR(64),
        flow_type VARCHAR(20) DEFAULT 'outsource',
        task_code VARCHAR(20),
        title VARCHAR(255),
        status VARCHAR(32) DEFAULT 'pending',
        priority VARCHAR(20) DEFAULT 'normal',
        quantity DECIMAL(12,2) DEFAULT 0.00,
        completed_qty DECIMAL(12,2) DEFAULT 0.00,
        qualified_qty DECIMAL(12,2) DEFAULT 0.00,
        unit VARCHAR(20) DEFAULT '件',
        target_operator VARCHAR(64),
        operator_id VARCHAR(64),
        source VARCHAR(64),
        remark TEXT,
        supplier_name VARCHAR(200),
        outsource_type VARCHAR(50),
        outsource_fee DECIMAL(12,2) DEFAULT 0.00,
        send_date DATE,
        return_date DATE,
        qc_result VARCHAR(20),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        completed_at DATETIME,
        is_deleted TINYINT(1) NOT NULL DEFAULT 0,
        created_by VARCHAR(64) NOT NULL DEFAULT 'system',
        updated_by VARCHAR(64) NOT NULL DEFAULT 'system',
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        KEY idx_order_no (order_no),
        KEY idx_status (status),
        KEY idx_target_operator (target_operator)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    # 5. repair_records
    """CREATE TABLE IF NOT EXISTS repair_records (
        id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        equipment_name VARCHAR(128) NOT NULL,
        fault_desc TEXT NOT NULL,
        reporter VARCHAR(64) DEFAULT '',
        report_date DATETIME,
        severity VARCHAR(16) DEFAULT 'normal',
        status VARCHAR(16) DEFAULT 'reported',
        assigned_to VARCHAR(64) DEFAULT '',
        repair_desc TEXT,
        repair_date DATETIME,
        completed_by VARCHAR(64) DEFAULT '',
        remark TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        is_deleted TINYINT(1) NOT NULL DEFAULT 0,
        created_by VARCHAR(64) NOT NULL DEFAULT 'system',
        updated_by VARCHAR(64) NOT NULL DEFAULT 'system',
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        KEY idx_rr_status (status),
        KEY idx_rr_is_deleted (is_deleted)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    # 6. approval_records
    """CREATE TABLE IF NOT EXISTS approval_records (
        id VARCHAR(64) NOT NULL PRIMARY KEY,
        order_no VARCHAR(64),
        approval_type VARCHAR(32) NOT NULL,
        title VARCHAR(255),
        applicant VARCHAR(64),
        approver VARCHAR(64),
        status VARCHAR(32) NOT NULL DEFAULT 'pending',
        content JSON,
        related_order VARCHAR(64),
        related_process VARCHAR(100),
        reject_reason TEXT,
        created_by VARCHAR(64) NOT NULL DEFAULT 'system',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_by VARCHAR(64) NOT NULL DEFAULT 'system',
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        completed_at DATETIME,
        is_deleted TINYINT(1) NOT NULL DEFAULT 0,
        KEY idx_order_no (order_no),
        KEY idx_status (status),
        KEY idx_approver (approver),
        KEY idx_created_by (created_by)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    # 7. production_orders
    """CREATE TABLE IF NOT EXISTS production_orders (
        id INT PRIMARY KEY AUTO_INCREMENT,
        order_no VARCHAR(50) UNIQUE NOT NULL,
        priority INT DEFAULT 5,
        plan_start DATETIME,
        plan_end DATETIME,
        actual_start DATETIME,
        actual_end DATETIME,
        assigned_to VARCHAR(50),
        status VARCHAR(20) DEFAULT 'pending',
        remark TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        is_deleted TINYINT(1) NOT NULL DEFAULT 0,
        created_by VARCHAR(64) NOT NULL DEFAULT 'system',
        updated_by VARCHAR(64) NOT NULL DEFAULT 'system',
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    # 8. schedule_flow_logs
    """CREATE TABLE IF NOT EXISTS schedule_flow_logs (
        id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        order_no VARCHAR(64) NOT NULL,
        event_type VARCHAR(64),
        event_data JSON,
        operator VARCHAR(64),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        is_deleted TINYINT(1) NOT NULL DEFAULT 0,
        created_by VARCHAR(64) NOT NULL DEFAULT 'system',
        updated_by VARCHAR(64) NOT NULL DEFAULT 'system',
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        KEY idx_sfl_order_no (order_no)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    # 9. process_records
    """CREATE TABLE IF NOT EXISTS process_records (
        id VARCHAR(64) NOT NULL PRIMARY KEY,
        process_type VARCHAR(50) DEFAULT 'production',
        order_no VARCHAR(100) DEFAULT '',
        product_name VARCHAR(200) DEFAULT '',
        quantity DOUBLE DEFAULT 0,
        unit VARCHAR(50) DEFAULT '',
        customer_name VARCHAR(200) DEFAULT '',
        delivery_date DATE,
        priority VARCHAR(50) DEFAULT 'normal',
        status VARCHAR(50) DEFAULT 'created',
        current_step INT DEFAULT 0,
        steps JSON,
        task_count INT DEFAULT 0,
        completed_task_count INT DEFAULT 0,
        flow_type VARCHAR(100) DEFAULT '',
        plan_start DATE,
        plan_end DATE,
        customer_group VARCHAR(100) DEFAULT '',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        is_deleted TINYINT(1) NOT NULL DEFAULT 0,
        created_by VARCHAR(64) NOT NULL DEFAULT 'system',
        updated_by VARCHAR(64) NOT NULL DEFAULT 'system',
        KEY idx_order_no (order_no),
        KEY idx_status (status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
]


def main():
    print('===== CI Init Schema: Create 9 business tables =====')
    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor()

    for i, ddl in enumerate(DDL_STATEMENTS, 1):
        # Extract table name from DDL
        table_name = ddl.split('CREATE TABLE IF NOT EXISTS ')[1].split(' (')[0].strip()
        try:
            cur.execute(ddl)
            conn.commit()
            print('  [%d/9] %s: OK' % (i, table_name))
        except Exception as e:
            print('  [%d/9] %s: SKIP (%s)' % (i, table_name, e))

    cur.close()
    conn.close()
    print('\nDone: 9 tables ready')


if __name__ == '__main__':
    main()
