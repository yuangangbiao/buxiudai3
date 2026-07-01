# -*- coding: utf-8 -*-
"""
云端备份存储模块

仅用于数据备份归档，不参与业务逻辑判断。
业务查询全部走本地容器端，此模块只做存储和查阅。

使用 SQLite 存储，自动管理数据库文件。
"""

import sqlite3
import os
import sys
import json
import logging
import threading
from datetime import datetime

logger = logging.getLogger(__name__)

_db_path = None
_local = threading.local()
_init_lock = threading.Lock()
_initialized = False


def _get_db_dir():
    """获取数据库文件路径（与 .env 同级目录）"""
    global _db_path
    if _db_path:
        return _db_path
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    _db_path = os.path.join(base_dir, 'cloud_backup.db')
    return _db_path


def _get_connection():
    """获取线程安全的数据库连接"""
    if not hasattr(_local, 'conn') or _local.conn is None:
        db_path = _get_db_dir()
        _local.conn = sqlite3.connect(db_path, timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10')))
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA synchronous=NORMAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
        _local.row_factory = sqlite3.Row
    return _local.conn


def init_db():
    """初始化数据库表结构（线程安全）"""
    global _initialized
    if _initialized:
        return True
    with _init_lock:
        if _initialized:
            return True
        try:
            conn = _get_connection()
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS wechat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    direction TEXT NOT NULL,
                    user_id TEXT,
                    content TEXT,
                    msg_type TEXT DEFAULT 'text',
                    msg_signature TEXT,
                    xml_raw TEXT,
                    reply_content TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS callback_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    msg_signature TEXT,
                    wx_timestamp TEXT,
                    nonce TEXT,
                    result TEXT,
                    xml_data TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS queue_backup (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_json TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_messages_created
                    ON wechat_messages(created_at);
                CREATE INDEX IF NOT EXISTS idx_messages_user
                    ON wechat_messages(user_id);
                CREATE INDEX IF NOT EXISTS idx_callback_created
                    ON callback_log(created_at);
            """)
            conn.commit()
            _initialized = True
            logger.info(f"[备份] 数据库初始化完成: {_get_db_dir()}")
            return True
        except Exception as e:
            logger.error(f"[备份] 数据库初始化失败: {e}")
            return False


def save_incoming_message(user_id, content, msg_type='text',
                          xml_raw='', msg_signature=''):
    """备份接收到的微信消息，不参与业务逻辑"""
    try:
        conn = _get_connection()
        conn.execute(
            """INSERT INTO wechat_messages
               (direction, user_id, content, msg_type, xml_raw,
                msg_signature, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ('incoming', user_id, content, msg_type,
             xml_raw if xml_raw else '',
             msg_signature or '',
             datetime.now().isoformat())
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"[备份] 保存入站消息失败: {e}")
        return False


def save_outgoing_message(user_id, content, reply_content='',
                          msg_type='text'):
    """备份发送给用户的回复消息，不参与业务逻辑"""
    try:
        conn = _get_connection()
        conn.execute(
            """INSERT INTO wechat_messages
               (direction, user_id, content, msg_type, reply_content, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ('outgoing', user_id, content, msg_type,
             reply_content if reply_content else '',
             datetime.now().isoformat())
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"[备份] 保存出站消息失败: {e}")
        return False


def save_callback_log(msg_signature, wx_timestamp, nonce, result,
                      xml_data=''):
    """备份回调日志，不参与业务逻辑"""
    try:
        conn = _get_connection()
        conn.execute(
            """INSERT INTO callback_log
               (msg_signature, wx_timestamp, nonce, result, xml_data, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (msg_signature or '', wx_timestamp or '', nonce or '',
             result or '', xml_data[:5000] if xml_data else '',
             datetime.now().isoformat())
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"[备份] 保存回调日志失败: {e}")
        return False


def save_queue_backup(data):
    """备份消息队列数据，不参与业务逻辑"""
    try:
        conn = _get_connection()
        conn.execute(
            """INSERT INTO queue_backup (data_json, created_at) VALUES (?, ?)""",
            (json.dumps(data, ensure_ascii=False)[:5000],
             datetime.now().isoformat())
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"[备份] 保存队列备份失败: {e}")
        return False


def get_backup_stats():
    """获取备份统计（仅用于管理端查看，不参与业务查询）"""
    try:
        conn = _get_connection()
        stats = {}
        cur = conn.execute(
            "SELECT direction, COUNT(*) as cnt FROM wechat_messages GROUP BY direction"
        )
        for row in cur.fetchall():
            stats[row[0]] = row[1]
        stats.setdefault('incoming', 0)
        stats.setdefault('outgoing', 0)

        cur = conn.execute("SELECT COUNT(*) as cnt FROM callback_log")
        stats['total_callbacks'] = cur.fetchone()[0]

        cur = conn.execute("SELECT COUNT(*) as cnt FROM queue_backup")
        stats['total_queue'] = cur.fetchone()[0]

        cur = conn.execute("SELECT COUNT(*) as cnt FROM wechat_messages")
        stats['total_messages'] = cur.fetchone()[0]

        db_path = _get_db_dir()
        if os.path.exists(db_path):
            stats['db_size_mb'] = round(os.path.getsize(db_path) / (1024 * 1024), 2)

        cur = conn.execute(
            "SELECT created_at FROM wechat_messages ORDER BY id ASC LIMIT 1"
        )
        row = cur.fetchone()
        stats['earliest'] = row[0] if row else None

        cur = conn.execute(
            "SELECT created_at FROM wechat_messages ORDER BY id DESC LIMIT 1"
        )
        row = cur.fetchone()
        stats['latest'] = row[0] if row else None

        return stats
    except Exception as e:
        logger.error(f"[备份] 获取统计失败: {e}")
        return {}
