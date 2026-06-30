"""
T0.1: 创建 data_packages 表
用于存储 ContainerCenter 的核心任务数据
"""
import os
import sys
import pymysql
from pymysql.cursors import DictCursor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import load_env, MYSQL_CONFIG

load_env()

def create_data_packages_table():
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

    print('[T0.1] 创建 data_packages 表...\n')

    c.execute("SHOW TABLES LIKE 'data_packages'")
    if c.fetchone():
        print('[T0.1] data_packages 表已存在，跳过创建')
        conn.close()
        return True

    sql = """
    CREATE TABLE `data_packages` (
      `id` INT AUTO_INCREMENT PRIMARY KEY,
      `uuid` VARCHAR(50) UNIQUE NOT NULL COMMENT '与原 DataPackage.id 兼容',
      `package_type` VARCHAR(50) NOT NULL COMMENT 'report|quality|material|approval|repair|outsource',
      `title` VARCHAR(200) NOT NULL COMMENT '任务标题',
      `content` JSON COMMENT '任务内容数据',
      `order_no` VARCHAR(50) COMMENT '关联工单',
      `process_id` INT COMMENT '工序记录ID',
      `process_name` VARCHAR(100) COMMENT '工序名称',
      `target_operator_id` VARCHAR(50) COMMENT '目标操作员ID',
      `target_operator` VARCHAR(100) COMMENT '目标操作员名称',
      `target_device` VARCHAR(50) COMMENT '目标设备',
      `status` VARCHAR(20) DEFAULT 'pending' COMMENT 'pending|distributed|acknowledged|processing|completed|returned',
      `priority` VARCHAR(20) DEFAULT 'normal' COMMENT 'low|normal|high|urgent',
      `source` VARCHAR(50) COMMENT '数据来源',
      `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
      `distributed_at` DATETIME COMMENT '分发时间',
      `acknowledged_at` DATETIME COMMENT '确认时间',
      `completed_at` DATETIME COMMENT '完成时间',
      `last_reminded_at` DATETIME COMMENT '最后提醒时间',
      `tags` JSON COMMENT '标签列表',
      `is_deleted` TINYINT DEFAULT 0,
      `migrated_from` VARCHAR(100) COMMENT '迁移来源',
      INDEX idx_status (`status`),
      INDEX idx_operator (`target_operator_id`),
      INDEX idx_order (`order_no`),
      INDEX idx_type (`package_type`),
      INDEX idx_created (`created_at`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ContainerCenter 任务包表';
    """

    try:
        c.execute(sql)
        conn.commit()
        print('[T0.1] data_packages 表创建成功')
        c.execute("DESC `data_packages`")
        columns = c.fetchall()
        print(f'\n[T0.1] 表结构验证: {len(columns)} 列')
        return True
    except Exception as e:
        print(f'[T0.1] 创建失败: {e}')
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    success = create_data_packages_table()
    sys.exit(0 if success else 1)
