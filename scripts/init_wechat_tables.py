# -*- coding: utf-8 -*-
"""
微信报工数据库初始化模块
"""
import os
import sys
import pymysql

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP_DIR)

try:
    from dotenv import load_dotenv
    env_path = os.path.join(APP_DIR, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)
except ImportError:
    pass

DB_CONFIG = {
    "host": os.getenv('MYSQL_HOST', 'localhost'),
    "port": int(os.getenv('MYSQL_PORT', 3306)),
    "database": os.getenv('MYSQL_DATABASE', 'steel_belt'),
    "user": os.getenv('MYSQL_USER', 'root'),
    "password": os.getenv('MYSQL_PASSWORD', ''),
    "charset": "utf8mb4"
}


def get_connection():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG)


def init_wechat_callback_log_table():
    """创建微信报工回调日志表"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wechat_callback_log (
                id INT AUTO_INCREMENT PRIMARY KEY,
                order_no VARCHAR(50) NOT NULL COMMENT '订单号',
                process_name VARCHAR(100) COMMENT '工序名称',
                status VARCHAR(20) COMMENT '状态',
                operator VARCHAR(50) COMMENT '操作员',
                remarks TEXT COMMENT '备注',
                received_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '接收时间',
                processed TINYINT DEFAULT 0 COMMENT '是否已处理',
                INDEX idx_order_no (order_no),
                INDEX idx_received_at (received_at),
                INDEX idx_processed (processed)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='微信报工回调日志'
        """)
        conn.commit()
        print("[✓] 微信报工回调日志表初始化完成")
        return True
    except Exception as e:
        print(f"[✗] 回调日志表初始化失败: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def init_process_status_history_table():
    """创建工序状态变更记录表"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS process_status_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                record_id INT NOT NULL COMMENT '工序记录ID',
                old_status VARCHAR(20) COMMENT '原状态',
                new_status VARCHAR(20) COMMENT '新状态',
                completed_qty DECIMAL(10,2) DEFAULT 0 COMMENT '完成数量',
                qualified_qty DECIMAL(10,2) DEFAULT 0 COMMENT '合格数量',
                worker VARCHAR(50) COMMENT '操作员',
                changed_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '变更时间',
                source VARCHAR(20) DEFAULT 'wechat' COMMENT '来源：wechat/manual/system',
                INDEX idx_record_id (record_id),
                INDEX idx_changed_at (changed_at),
                INDEX idx_source (source)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工序状态变更历史'
        """)
        conn.commit()
        print("[✓] 工序状态变更记录表初始化完成")
        return True
    except Exception as e:
        print(f"[✗] 状态变更记录表初始化失败: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def init_all_wechat_tables():
    """初始化所有微信报工相关表"""
    print("\n=== 初始化微信报工相关表 ===")
    init_wechat_callback_log_table()
    init_process_status_history_table()
    print("=== 初始化完成 ===\n")


if __name__ == "__main__":
    init_all_wechat_tables()