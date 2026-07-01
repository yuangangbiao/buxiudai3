# -*- coding: utf-8 -*-
"""
通知接收人预设服务 - R13 任务8
提供对 notification_recipient_preset 表的增删改查服务

表结构:
    id INT AUTO_INCREMENT PRIMARY KEY,
    scenario VARCHAR(128) NOT NULL COMMENT '触发场景',
    receivers JSON NOT NULL COMMENT '接收人列表["张三","李四"]',
    enabled TINYINT(1) NOT NULL DEFAULT 1 COMMENT '1=启用 0=禁用',
    force_by_assignee TINYINT(1) NOT NULL DEFAULT 0 COMMENT '1=强制按任务执行人发送',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_scenario (scenario)
"""
import json
import logging
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

import pymysql

logger = logging.getLogger(__name__)

_TABLE_NAME = 'notification_recipient_preset'
_DB_NAME = 'steel_belt'
_CONNECT_TIMEOUT = 5


def _get_db_config():
    return {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'port': int(os.getenv('MYSQL_PORT', 3306)),
        'user': os.getenv('MYSQL_USER', 'root'),
        'password': os.getenv('MYSQL_PASSWORD', ''),
        'database': _DB_NAME,
        'charset': 'utf8mb4',
        'connect_timeout': _CONNECT_TIMEOUT,
    }


class NotificationPresetService:

    def get_receivers_for_scenario(self, scenario: str) -> list:
        """查询某场景的接收人列表

        Args:
            scenario: 触发场景标识

        Returns:
            接收人列表；scenario 不存在或 enabled=0 时返回空列表
        """
        conn = None
        try:
            from core.db_compat import get_conn
            conn = get_conn()
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT receivers FROM {_TABLE_NAME} WHERE scenario=%s AND enabled=1",
                    (scenario,)
                )
                row = cur.fetchone()
                if not row:
                    return []
                receivers = row[0]
                if isinstance(receivers, str):
                    return json.loads(receivers)
                return receivers if isinstance(receivers, list) else []
        except Exception as e:
            logger.exception(f'[预设服务] get_receivers_for_scenario 失败: {scenario} ({e!r})')
            raise
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def get_force_by_assignee(self, scenario: str) -> bool:
        """查询某场景是否强制按任务执行人发送

        Args:
            scenario: 触发场景标识

        Returns:
            True=强制按执行人发送，False=按接收人列表发送
        """
        conn = None
        try:
            from core.db_compat import get_conn
            conn = get_conn()
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT force_by_assignee FROM {_TABLE_NAME} WHERE scenario=%s AND enabled=1",
                    (scenario,)
                )
                row = cur.fetchone()
                if not row:
                    return False
                return bool(row[0])
        except Exception as e:
            logger.exception(f'[预设服务] get_force_by_assignee 失败: {scenario} ({e!r})')
            return False
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def set_receivers_for_scenario(self, scenario: str, receivers: list, enabled: bool = True, force_by_assignee: bool = False) -> bool:
        """插入或更新某场景的接收人

        Args:
            scenario: 触发场景标识
            receivers: 接收人列表
            enabled: 是否启用
            force_by_assignee: 是否强制按任务执行人发送

        Returns:
            成功返回 True，失败返回 False（静默降级）
        """
        conn = None
        try:
            from core.db_compat import get_conn
            conn = get_conn()
            receivers_json = json.dumps(receivers, ensure_ascii=False)
            with conn.cursor() as cur:
                cur.execute(
                    f"""INSERT INTO {_TABLE_NAME} (scenario, receivers, enabled, force_by_assignee)
                        VALUES (%s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE receivers=VALUES(receivers), enabled=VALUES(enabled), force_by_assignee=VALUES(force_by_assignee)""",
                    (scenario, receivers_json, 1 if enabled else 0, 1 if force_by_assignee else 0)
                )
            conn.commit()
            return True
        except Exception as e:
            logger.exception(f'[预设服务] set_receivers_for_scenario 失败: {scenario} ({e!r})')
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            raise
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def delete_preset(self, scenario: str) -> bool:
        """删除某场景的预设

        Args:
            scenario: 触发场景标识

        Returns:
            成功返回 True，失败返回 False（静默降级）
        """
        conn = None
        try:
            from core.db_compat import get_conn
            conn = get_conn()
            with conn.cursor() as cur:
                cur.execute(f"DELETE FROM {_TABLE_NAME} WHERE scenario=%s", (scenario,))
            conn.commit()
            return True
        except Exception as e:
            logger.exception(f'[预设服务] delete_preset 失败: {scenario} ({e!r})')
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            raise
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def list_all_presets(self) -> list:
        """返回所有预设

        Returns:
            所有预设记录列表，每条记录包含 id/scenario/receivers/enabled/force_by_assignee
            表不存在时返回空列表（静默降级）
        """
        conn = None
        try:
            from core.db_compat import get_conn
            conn = get_conn()
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT id, scenario, receivers, enabled, force_by_assignee FROM {_TABLE_NAME}"
                )
                rows = cur.fetchall()
                result = []
                for row in rows:
                    receivers = row[2]
                    if isinstance(receivers, str):
                        receivers = json.loads(receivers)
                    result.append({
                        'id': row[0],
                        'scenario': row[1],
                        'receivers': receivers if isinstance(receivers, list) else [],
                        'enabled': bool(row[3]),
                        'force_by_assignee': bool(row[4]) if row[4] is not None else False,
                    })
                return result
        except Exception as e:
            logger.exception(f'[预设服务] list_all_presets 失败 ({e!r})')
            raise
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def toggle_enabled(self, scenario: str, enabled: bool) -> bool:
        """启用/禁用某场景

        Args:
            scenario: 触发场景标识
            enabled: True 启用，False 禁用

        Returns:
            成功返回 True，失败返回 False（静默降级）
        """
        conn = None
        try:
            from core.db_compat import get_conn
            conn = get_conn()
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE {_TABLE_NAME} SET enabled=%s WHERE scenario=%s",
                    (1 if enabled else 0, scenario)
                )
            conn.commit()
            return True
        except Exception as e:
            logger.exception(f'[预设服务] toggle_enabled 失败: {scenario} ({e!r})')
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            raise
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
