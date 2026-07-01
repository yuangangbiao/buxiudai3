# -*- coding: utf-8 -*-
"""
R13 微信消息发送日志（wechat_msg_log）幂等写入模块

幂等策略：
- msg_hash = SHA256(scenario + "|" + SHA256(content))
- INSERT ... ON DUPLICATE KEY UPDATE 防止并发重复写入
- 表不存在时静默降级，不阻塞消息发送流程
"""
import hashlib
import logging
from typing import Optional

_logger = logging.getLogger(__name__)


def _compute_msg_hash(scenario: str, content: str) -> str:
    content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
    return hashlib.sha256(f"{scenario}|{content_hash}".encode('utf-8')).hexdigest()


def log_send_attempt(
    scenario: str,
    tmpl_id: str,
    content: str,
    operators: list,
    status: str = 'pending',
    sent_at: Optional[str] = None,
    frontend_confirmed_at: Optional[str] = None,
    err_msg: Optional[str] = None,
) -> bool:
    """
    记录微信消息发送尝试（幂等写入）。

    幂等键：msg_hash = SHA256(scenario + "|" + SHA256(content))
    同一 scenario + 同一 content 不会重复写入（UNIQUE INDEX + ON DUPLICATE KEY UPDATE）。

    表不存在时静默降级，不抛异常。

    Args:
        scenario: 场景名（如 schedule_notify / workorder_created）
        tmpl_id: 模板ID
        content: 实际发送内容（变量替换后）
        operators: 接收人列表
        status: pending / success / fail
        sent_at: 实际发送时间（ISO格式字符串或 None）
        frontend_confirmed_at: 前端确认时间（None = 未确认）
        err_msg: 错误信息（发送失败时填）

    Returns:
        True = 写入成功或已存在（幂等）
        False = 写入失败（静默）
    """
    try:
        import pymysql
        import os

        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        msg_hash = hashlib.sha256(f"{scenario}|{content_hash}".encode('utf-8')).hexdigest()

        # [T11 2026-06-14] 走 shim 连接池
        from core.db_compat import get_conn
        conn = get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO wechat_msg_log (
                    scenario, tmpl_id, content, operators,
                    content_hash, msg_hash,
                    send_status, sent_at, frontend_confirmed_at,
                    retry_count, err_msg
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    send_status = IF(VALUES(send_status) = 'fail', VALUES(send_status), send_status),
                    sent_at = IF(VALUES(sent_at) IS NOT NULL AND send_status = 'success',
                                  VALUES(sent_at), sent_at),
                    frontend_confirmed_at = IF(VALUES(frontend_confirmed_at) IS NOT NULL,
                                               VALUES(frontend_confirmed_at), frontend_confirmed_at),
                    err_msg = IF(VALUES(err_msg) IS NOT NULL, VALUES(err_msg), err_msg)
            """, (
                scenario, tmpl_id, content,
                __import__('json').dumps(operators, ensure_ascii=False),
                content_hash, msg_hash,
                status,
                sent_at, frontend_confirmed_at,
                0 if status == 'pending' else 0,
                err_msg,
            ))
            conn.commit()
            cursor.close()
            return True
        except Exception as ie:
            conn.close()
            raise ie
    except Exception as e:
        _logger.debug('[wechat_msg_log] 记录降级: %s', e)
        return False


def confirm_frontend_received(msg_hash: str) -> bool:
    """
    前端确认收到消息后，更新确认时间。

    Args:
        msg_hash: 消息哈希（log_send_attempt 返回的 msg_hash）

    Returns:
        True = 更新成功
        False = 更新失败（静默）
    """
    try:
        import pymysql
        import os

        # [T11 2026-06-14] 走 shim 连接池
        from core.db_compat import get_conn
        conn = get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE wechat_msg_log
                SET frontend_confirmed_at = CURRENT_TIMESTAMP
                WHERE msg_hash = %s
                  AND frontend_confirmed_at IS NULL
            """, (msg_hash,))
            conn.commit()
            cursor.close()
            return True
        except Exception as ie:
            conn.close()
            raise ie
    except Exception as e:
        _logger.debug('[wechat_msg_log] 前端确认更新降级: %s', e)
        return False
