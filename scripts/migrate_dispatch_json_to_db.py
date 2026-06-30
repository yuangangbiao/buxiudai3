# -*- coding: utf-8 -*-
"""
迁移脚本：将 dispatch_center_data.json 数据迁移到 MySQL

从 JSON 文件中读取 flow_matching_rules、templates、messages 数据，
通过 INSERT IGNORE 写入 MySQL 对应表。
幂等设计：重复执行不会产生重复数据。

用法：
    python scripts/migrate_dispatch_json_to_db.py

迁移完成后，原 JSON 文件会被备份为 dispatch_center_data.json.bak
"""

import json
import os
import sys
import logging
import shutil

# 添加项目根目录到 sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('migrate_dispatch_json')


def get_json_file_path() -> str:
    """获取 JSON 数据文件路径"""
    return os.path.join(BASE_DIR, 'dispatch_center_data.json')


def get_mysql_config() -> dict:
    """获取 MySQL 连接配置（与 dispatch_center.py 保持一致）"""
    return {
        'host': os.environ.get('MYSQL_HOST', 'localhost'),
        'port': int(os.environ.get('MYSQL_PORT', 3306)),
        'user': os.environ.get('MYSQL_USER', 'root'),
        'password': os.environ.get('MYSQL_PASSWORD', ''),
        'database': os.environ.get('MYSQL_DATABASE', 'steel_belt'),
        'charset': 'utf8mb4',
    }


def get_db_connection():
    """获取 MySQL 数据库连接"""
    import pymysql
    from pymysql.cursors import DictCursor
    cfg = get_mysql_config()
    conn = pymysql.connect(**cfg, cursorclass=DictCursor, connect_timeout=5)
    return conn


def load_json_data(file_path: str) -> dict:
    """加载 JSON 文件数据"""
    if not os.path.exists(file_path):
        logger.warning('JSON 文件不存在: %s', file_path)
        return {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info('成功加载 JSON 文件: %s (%.1f KB)', file_path, os.path.getsize(file_path) / 1024)
        return data
    except (json.JSONDecodeError, IOError) as e:
        logger.error('加载 JSON 文件失败: %s', e)
        return {}


def ensure_tables(cursor):
    """确保目标表已创建（幂等）"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS flow_matching_rules (
            id VARCHAR(50) PRIMARY KEY,
            name VARCHAR(200) NOT NULL COMMENT '规则名称',
            match_field VARCHAR(50) NOT NULL COMMENT '匹配字段',
            match_value VARCHAR(200) NOT NULL COMMENT '匹配值',
            flow_type VARCHAR(50) NOT NULL COMMENT '流程类型',
            priority INT DEFAULT 10 COMMENT '优先级',
            enabled TINYINT(1) DEFAULT 1 COMMENT '是否启用',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='流程匹配规则'
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS flow_templates (
            id VARCHAR(50) PRIMARY KEY,
            name VARCHAR(200) NOT NULL COMMENT '模板名称',
            category VARCHAR(50) DEFAULT '' COMMENT '分类',
            channels_json TEXT DEFAULT '[]' COMMENT '渠道列表JSON',
            title VARCHAR(500) DEFAULT '' COMMENT '标题',
            content TEXT COMMENT '内容',
            receivers_json TEXT COMMENT '接收人配置JSON',
            sort_order INT DEFAULT 0 COMMENT '排序',
            is_default TINYINT(1) DEFAULT 0 COMMENT '是否默认模板',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='消息模板'
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS message_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            msg_id VARCHAR(50) NOT NULL COMMENT '消息ID',
            template_id VARCHAR(50) DEFAULT '' COMMENT '模板ID',
            content_preview VARCHAR(200) DEFAULT '' COMMENT '内容预览',
            channels_json TEXT COMMENT '渠道JSON',
            receivers_json TEXT COMMENT '接收人JSON',
            results_json TEXT COMMENT '发送结果JSON',
            errors_json TEXT COMMENT '错误信息JSON',
            sent_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '发送时间',
            INDEX idx_sent_at (sent_at),
            INDEX idx_msg_id (msg_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='消息发送历史'
    """)
    logger.info('目标表已就绪')


def migrate_flow_matching_rules(cursor, rules: list) -> int:
    """迁移流程匹配规则

    Args:
        cursor: 数据库游标
        rules: 规则列表

    Returns:
        迁移的记录数
    """
    count = 0
    for rule in rules:
        rule_id = rule.get('id', '')
        if not rule_id:
            continue
        try:
            cursor.execute("""
                INSERT IGNORE INTO flow_matching_rules
                (id, name, match_field, match_value, flow_type, priority, enabled)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                rule_id,
                rule.get('name', ''),
                rule.get('field', rule.get('match_field', '')),
                rule.get('value', rule.get('match_value', '')),
                rule.get('flow_type', 'production'),
                rule.get('priority', 10),
                1 if rule.get('enabled', True) else 0,
            ))
            if cursor.rowcount > 0:
                count += 1
        except Exception as e:
            logger.warning('跳过规则 %s: %s', rule_id, e)
    return count


def migrate_templates(cursor, templates: list) -> int:
    """迁移消息模板

    Args:
        cursor: 数据库游标
        templates: 模板列表

    Returns:
        迁移的记录数
    """
    count = 0
    for tmpl in templates:
        tmpl_id = tmpl.get('id', '')
        if not tmpl_id:
            continue
        try:
            channels_json = json.dumps(tmpl.get('channels', ['wechat_group']), ensure_ascii=False)
            receivers_json = json.dumps(tmpl.get('receivers')) if tmpl.get('receivers') else None
            cursor.execute("""
                INSERT IGNORE INTO flow_templates
                (id, name, category, channels_json, title, content, receivers_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                tmpl_id,
                tmpl.get('name', ''),
                tmpl.get('category', ''),
                channels_json,
                tmpl.get('title', ''),
                tmpl.get('content', ''),
                receivers_json,
            ))
            if cursor.rowcount > 0:
                count += 1
        except Exception as e:
            logger.warning('跳过模板 %s: %s', tmpl_id, e)
    return count


def migrate_messages(cursor, messages: list) -> int:
    """迁移消息历史

    Args:
        cursor: 数据库游标
        messages: 消息列表

    Returns:
        迁移的记录数
    """
    count = 0
    for msg in messages:
        msg_id = msg.get('id', '')
        if not msg_id:
            continue
        try:
            sent_at = msg.get('timestamp', '')
            cursor.execute("""
                INSERT IGNORE INTO message_history
                (msg_id, template_id, content_preview, channels_json,
                 receivers_json, results_json, errors_json, sent_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                msg_id,
                msg.get('template_id', ''),
                msg.get('content_preview', ''),
                json.dumps(msg.get('channels', []), ensure_ascii=False),
                json.dumps(msg.get('receivers', {}), ensure_ascii=False),
                json.dumps(msg.get('results', {}), ensure_ascii=False),
                json.dumps(msg.get('errors', []), ensure_ascii=False),
                sent_at if sent_at else None,
            ))
            if cursor.rowcount > 0:
                count += 1
        except Exception as e:
            logger.warning('跳过消息 %s: %s', msg_id, e)
    return count


def backup_json_file(file_path: str) -> bool:
    """备份 JSON 文件为 .bak

    Args:
        file_path: JSON 文件路径

    Returns:
        是否成功
    """
    if not os.path.exists(file_path):
        return True
    bak_path = file_path + '.bak'
    try:
        shutil.copy2(file_path, bak_path)
        logger.info('JSON 文件已备份为: %s', bak_path)
        return True
    except IOError as e:
        logger.error('备份 JSON 文件失败: %s', e)
        return False


def main():
    """主迁移流程"""
    logger.info('=' * 60)
    logger.info('开始迁移 dispatch_center_data.json 到 MySQL')
    logger.info('=' * 60)

    # 1. 加载 JSON
    json_path = get_json_file_path()
    data = load_json_data(json_path)
    if not data:
        logger.info('无数据可迁移，跳过')
        return

    # 2. 连接 MySQL
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 3. 确保表存在
        ensure_tables(cursor)
        conn.commit()

        # 4. 迁移流程匹配规则
        rules = data.get('flow_matching_rules', [])
        if rules:
            rules_count = migrate_flow_matching_rules(cursor, rules)
            conn.commit()
            logger.info('流程匹配规则迁移: %d / %d 条', rules_count, len(rules))
        else:
            logger.info('流程匹配规则: 无数据')

        # 5. 迁移模板
        templates = data.get('templates', [])
        if templates:
            tmpl_count = migrate_templates(cursor, templates)
            conn.commit()
            logger.info('消息模板迁移: %d / %d 条', tmpl_count, len(templates))
        else:
            logger.info('消息模板: 无数据')

        # 6. 迁移消息历史
        messages = data.get('messages', [])
        if messages:
            msg_count = migrate_messages(cursor, messages)
            conn.commit()
            logger.info('消息历史迁移: %d / %d 条', msg_count, len(messages))
        else:
            logger.info('消息历史: 无数据')

        # 7. 备份 JSON
        total = (len(rules) if rules else 0) + (len(templates) if templates else 0) + (len(messages) if messages else 0)
        if total > 0:
            backup_json_file(json_path)
            logger.info('迁移完成，共处理 %d 条记录', total)
        else:
            logger.info('迁移完成，无数据需处理')

    except Exception as e:
        logger.error('迁移过程出错: %s', e)
        if conn:
            conn.rollback()
        sys.exit(1)
    finally:
        if conn:
            conn.close()

    logger.info('=' * 60)
    logger.info('迁移完毕')
    logger.info('=' * 60)


if __name__ == '__main__':
    main()
