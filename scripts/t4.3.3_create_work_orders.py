"""
T0.3: 创建 work_orders 表
"""
import os
import sys
import pymysql
from pymysql.cursors import DictCursor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import load_env, MYSQL_CONFIG

load_env()

def create_work_orders_table():
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

    print('[T0.3] 创建 work_orders 表...\n')

    c.execute("SHOW TABLES LIKE 'work_orders'")
    if c.fetchone():
        print('[T0.3] work_orders 表已存在，跳过创建')
        conn.close()
        return True

    sql = """
    CREATE TABLE `work_orders` (
      `id` INT AUTO_INCREMENT PRIMARY KEY,
      `uuid` VARCHAR(50) UNIQUE NOT NULL,
      `order_no` VARCHAR(50) NOT NULL,
      `work_order_no` VARCHAR(50),
      `product_name` VARCHAR(200),
      `product_spec` VARCHAR(200),
      `quantity` INT DEFAULT 0,
      `completed_qty` INT DEFAULT 0,
      `qualified_qty` INT DEFAULT 0,
      `status` VARCHAR(20) DEFAULT 'pending',
      `priority` VARCHAR(20) DEFAULT 'normal',
      `due_date` DATE,
      `started_at` DATETIME,
      `completed_at` DATETIME,
      `assigned_to` VARCHAR(50),
      `operator` VARCHAR(100),
      `customer_name` VARCHAR(200),
      `remark` TEXT,
      `is_deleted` TINYINT DEFAULT 0,
      `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
      `updated_at` DATETIME ON UPDATE CURRENT_TIMESTAMP,
      `migrated_from` VARCHAR(100),
      INDEX idx_order (`order_no`),
      INDEX idx_work_order (`work_order_no`),
      INDEX idx_status (`status`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """

    try:
        c.execute(sql)
        conn.commit()
        print('[T0.3] work_orders 表创建成功')
        return True
    except Exception as e:
        print(f'[T0.3] 创建失败: {e}')
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    success = create_work_orders_table()
    sys.exit(0 if success else 1)
