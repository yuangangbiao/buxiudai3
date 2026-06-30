"""
T0.2: 创建 schedule_records 表
"""
import os
import sys
import pymysql
from pymysql.cursors import DictCursor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import load_env, MYSQL_CONFIG

load_env()

def create_schedule_records_table():
    mysql_cfg = {
        'host': MYSQL_CONFIG.get('host'),
        'port': MYSQL_CONFIG.get('port'),
        'database': MYSQL_CONFIG.get('database'),
        'user': MYSQL_CONFIG.get('user'),
        'password': MYSQL_CONFIG.get('password'),
        'charset': 'utf8mb4',
    }

    conn = pymysql.connect(**mysql_cfg, cursorclass=DictCursor, connect_timeout=10)
    c = conn.cursor()

    print('[T0.2] 创建 schedule_records 表...\n')

    c.execute("SHOW TABLES LIKE 'schedule_records'")
    if c.fetchone():
        print('[T0.2] schedule_records 表已存在，跳过创建')
        conn.close()
        return True

    sql = """
    CREATE TABLE `schedule_records` (
      `id` INT AUTO_INCREMENT PRIMARY KEY,
      `uuid` VARCHAR(50) UNIQUE NOT NULL,
      `order_no` VARCHAR(50) NOT NULL,
      `process_name` VARCHAR(100),
      `product_name` VARCHAR(200),
      `schedule_date` DATE,
      `production_line` VARCHAR(50),
      `equipment_id` VARCHAR(50),
      `planned_qty` INT DEFAULT 0,
      `completed_qty` INT DEFAULT 0,
      `qualified_qty` INT DEFAULT 0,
      `status` VARCHAR(20) DEFAULT 'pending',
      `priority` VARCHAR(20) DEFAULT 'normal',
      `assigned_to` VARCHAR(50),
      `operator` VARCHAR(100),
      `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
      `started_at` DATETIME,
      `completed_at` DATETIME,
      `remark` TEXT,
      `is_deleted` TINYINT DEFAULT 0,
      `migrated_from` VARCHAR(100),
      INDEX idx_order (`order_no`),
      INDEX idx_date (`schedule_date`),
      INDEX idx_status (`status`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """

    try:
        c.execute(sql)
        conn.commit()
        print('[T0.2] schedule_records 表创建成功')
        return True
    except Exception as e:
        print(f'[T0.2] 创建失败: {e}')
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    success = create_schedule_records_table()
    sys.exit(0 if success else 1)
