# QB-001: events 表 DDL 迁移
import os, sys, pymysql

MYSQL_CFG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'port': int(os.getenv('MYSQL_PORT', '3306')),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', ''),
    'database': os.getenv('MYSQL_DATABASE', 'steel_belt'),
    'charset': 'utf8mb4',
}

SQL = """
CREATE TABLE IF NOT EXISTS events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    aggregate_type VARCHAR(50) NOT NULL COMMENT '聚合类型(order/production/quality)',
    aggregate_id VARCHAR(100) NOT NULL COMMENT '聚合ID(订单号等)',
    event_type VARCHAR(100) NOT NULL COMMENT '事件类型',
    payload JSON COMMENT '事件载荷',
    occurred_at DATETIME(6) NOT NULL COMMENT '发生时间',
    INDEX idx_aggregate (aggregate_type, aggregate_id),
    INDEX idx_type (event_type),
    INDEX idx_occurred (occurred_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='领域事件存储';

CREATE TABLE IF NOT EXISTS saga_dead_letter (
    id INT AUTO_INCREMENT PRIMARY KEY,
    saga_name VARCHAR(100) NOT NULL,
    step_name VARCHAR(100) NOT NULL,
    error TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Saga补偿失败死信';
"""

if __name__ == '__main__':
    dry = '--dry-run' in sys.argv
    if dry:
        print('[DRY-RUN] events+saga_dead_letter DDL')
        print(SQL)
    else:
        conn = pymysql.connect(**MYSQL_CFG)
        for stmt in SQL.split(';'):
            stmt = stmt.strip()
            if stmt and not stmt.startswith('--'):
                conn.cursor().execute(stmt)
        conn.commit()
        conn.close()
        print('events + saga_dead_letter 表创建完成')
