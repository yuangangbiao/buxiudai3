# -*- coding: utf-8 -*-
"""
微信消息持久化存储（MySQL 集中存储）
所有消息存储在 MySQL container_center 数据库中
"""
import os
import pymysql
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict
from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
from core.db import get_direct_connection
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class WechatMessageStore:
    _instance = None

    def __new__(cls, db_dir: str = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_dir: str = None):
        if self._initialized:
            return
        self._initialized = True

        self._conn = None

    def _get_current_db(self):
        """确保 MySQL 数据库连接"""
        if self._conn is None:
            self._conn = get_direct_connection(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
            self._init_db()
        else:
            try:
                self._conn.ping(reconnect=True)
            except Exception:
                self._conn = get_direct_connection(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)

    @property
    def conn(self):
        """获取当前数据库连接"""
        self._get_current_db()
        return self._conn

    def _init_db(self):
        """初始化数据库表"""
        try:
            cursor = self._conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS wechat_messages (
                    id INTEGER PRIMARY KEY AUTO_INCREMENT,
                    msg_id TEXT NOT NULL DEFAULT '',
                    user_id TEXT NOT NULL,
                    content TEXT,
                    msg_type TEXT DEFAULT 'text',
                    event TEXT,
                    raw_xml TEXT,
                    latitude DOUBLE DEFAULT 0,
                    longitude DOUBLE DEFAULT 0,
                    `precision` DOUBLE DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    source TEXT DEFAULT 'wechat',
                    chunk_id INTEGER DEFAULT 1,
                    total_chunks INTEGER DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    polled_at DATETIME,
                    processed_at DATETIME,
                    response_content TEXT,
                    error_message TEXT,
                    metadata TEXT DEFAULT '{}',
                    poll_token TEXT DEFAULT '',
                    UNIQUE KEY uk_msg_chunk (msg_id, chunk_id)
                )
            ''')
            self._migrate_wechat_messages(cursor)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS outgoing_messages (
                    id INTEGER PRIMARY KEY AUTO_INCREMENT,
                    msg_id TEXT,
                    user_id TEXT NOT NULL,
                    content TEXT,
                    msg_type TEXT DEFAULT 'text',
                    status TEXT DEFAULT 'pending',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    sent_at DATETIME,
                    confirmed_at DATETIME,
                    confirmed TINYINT(1) DEFAULT 0,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    last_retry_at DATETIME,
                    dead_at DATETIME,
                    expired_at DATETIME,
                    error TEXT
                )
            ''')
            # MySQL 8.0+ 支持 IF NOT EXISTS 创建索引
            try:
                cursor.execute('CREATE INDEX idx_status ON wechat_messages(status)')
            except Exception:
                pass
            try:
                cursor.execute('CREATE INDEX idx_user_id ON wechat_messages(user_id)')
            except Exception:
                pass
            try:
                cursor.execute('CREATE INDEX idx_created_at ON wechat_messages(created_at)')
            except Exception:
                pass
            try:
                cursor.execute('CREATE INDEX idx_msg_id ON wechat_messages(msg_id)')
            except Exception:
                pass
            try:
                cursor.execute('CREATE INDEX idx_outgoing_status ON outgoing_messages(status)')
            except Exception:
                pass
            try:
                cursor.execute('CREATE INDEX idx_outgoing_user ON outgoing_messages(user_id)')
            except Exception:
                pass
            self._conn.commit()
            cursor.close()
            logger.info('[WechatStore] 数据库初始化 (MySQL)')
        except Exception as e:
            logger.error(f'[WechatStore] 数据库初始化失败: {e}')
            raise

    def _migrate_wechat_messages(self, cursor):
        try:
            cursor.execute('SELECT metadata FROM wechat_messages LIMIT 1')
        except pymysql.err.OperationalError:
            logger.info('[WechatStore] 迁移: 添加 metadata 列')
            cursor.execute("ALTER TABLE wechat_messages ADD COLUMN metadata TEXT DEFAULT '{}'")

        try:
            cursor.execute('SELECT poll_token FROM wechat_messages LIMIT 1')
        except pymysql.err.OperationalError:
            logger.info('[WechatStore] 迁移: 添加 poll_token 列')
            cursor.execute("ALTER TABLE wechat_messages ADD COLUMN poll_token TEXT DEFAULT ''")

    def _add_unique_index_safe(self, cursor, table: str, index_name: str, columns: str):
        """MySQL 安全添加 UNIQUE 索引（避免重复键错误）"""
        try:
            cursor.execute(f'CREATE UNIQUE INDEX {index_name} ON {table} ({columns})')
        except Exception:
            pass

    @contextmanager
    def get_cursor(self):
        """获取数据库cursor"""
        cursor = self.conn.cursor()
        try:
            yield cursor
            self._conn.commit()
        except Exception as e:
            self._conn.rollback()
            raise e
        finally:
            cursor.close()

    CHUNK_SIZE = 1700

    def save_message(self, msg_data: Dict) -> Optional[int]:
        """保存消息到 MySQL（自动分段）"""
        try:
            content = msg_data.get('content', '')
            msg_type = msg_data.get('msg_type', 'text')
            chunks = self._split_content(content, msg_type)
            total_chunks = len(chunks)
            msg_id = msg_data.get('msg_signature', '') or self._generate_msg_id()

            _standard_keys = {
                'msg_id', 'msg_signature', 'user_id', 'content', 'msg_type',
                'event', 'raw_xml', 'latitude', 'longitude', 'precision',
                'source', 'chunk_id', 'total_chunks'
            }
            metadata = {k: v for k, v in msg_data.items() if k not in _standard_keys}
            metadata_json = json.dumps(metadata, ensure_ascii=False, default=str)

            self._get_current_db()
            first_id = None
            with self.get_cursor() as cursor:
                for i, chunk in enumerate(chunks, 1):
                    cursor.execute('''
                        INSERT INTO wechat_messages (
                            msg_id, user_id, content, msg_type, event, raw_xml,
                            latitude, longitude, `precision`, source,
                            chunk_id, total_chunks, metadata
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (
                        msg_id,
                        msg_data.get('user_id', ''),
                        chunk,
                        msg_data.get('msg_type', 'text'),
                        msg_data.get('event', ''),
                        msg_data.get('raw_xml', ''),
                        msg_data.get('latitude', 0),
                        msg_data.get('longitude', 0),
                        msg_data.get('precision', 0),
                        'wechat',
                        i,
                        total_chunks,
                        metadata_json
                    ))
                    if first_id is None:
                        first_id = cursor.lastrowid
            return first_id
        except pymysql.err.IntegrityError:
            logger.warning(f'[WechatStore] 消息已存在: {msg_data.get("msg_signature", "")}')
            return None
        except Exception as e:
            logger.error(f'[WechatStore] 保存消息失败: {e}')
            return None

    def _split_content(self, content: str, msg_type: str = 'text') -> List[str]:
        """将超长内容分段"""
        if not content:
            return ['']
        if len(content) <= self.CHUNK_SIZE:
            return [content]
        chunks = []
        for i in range(0, len(content), self.CHUNK_SIZE):
            chunks.append(content[i:i + self.CHUNK_SIZE])
        return chunks

    def _generate_msg_id(self) -> str:
        """生成唯一消息ID"""
        import time
        import random
        return f"chunk_{int(time.time())}_{random.randint(1000, 9999)}"

    def poll_messages(self, limit: int = 10) -> List[Dict]:
        """获取待处理消息（按分段返回，每段独立）"""
        try:
            self._get_current_db()
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT * FROM wechat_messages
                WHERE status = 'pending'
                ORDER BY msg_id, chunk_id, created_at ASC
                LIMIT %s
            ''', (limit,))
            rows = cursor.fetchall()
            messages = []
            for row in rows:
                msg = dict(row)
                if msg.get('total_chunks', 1) > 1:
                    msg['content'] = f'[{msg["chunk_id"]}/{msg["total_chunks"]}]{msg["content"]}'
                metadata_str = msg.pop('metadata', None)
                if metadata_str and metadata_str != '{}':
                    try:
                        extra = json.loads(metadata_str)
                        if isinstance(extra, dict):
                            msg.update(extra)
                    except (json.JSONDecodeError, TypeError):
                        pass
                messages.append(msg)
            return messages
        except Exception as e:
            logger.error(f'[WechatStore] 查询消息失败: {e}')
            return []

    def reassemble_message(self, msg_id: str) -> Optional[Dict]:
        """重组分段消息为完整消息（去除格式头）"""
        try:
            self._get_current_db()
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT * FROM wechat_messages
                WHERE msg_id = %s AND status = 'pending'
                ORDER BY chunk_id
            ''', (msg_id,))
            rows = cursor.fetchall()
            if not rows:
                return None
            import re
            full_content = ''.join(re.sub(r'^\[\d+/\d+\]', '', row['content']) for row in rows)
            first = dict(rows[0])
            first['content'] = full_content
            first['chunks'] = len(rows)
            return first
        except Exception as e:
            logger.error(f'[WechatStore] 重组消息失败: {e}')
            return None

    def _generate_poll_token(self) -> str:
        """生成唯一轮询令牌"""
        import time
        import random
        return f"PT_{int(time.time() * 1000000)}_{random.randint(10000, 99999)}"

    def claim_messages(self, limit: int = 10) -> List[Dict]:
        """原子claim：将 pending 消息标记为 polled 并返回（含 poll_token）"""
        try:
            self._get_current_db()
            poll_token = self._generate_poll_token()
            with self.get_cursor() as cursor:
                cursor.execute('''
                    UPDATE wechat_messages
                    SET status = 'polled', poll_token = %s, polled_at = CURRENT_TIMESTAMP
                    WHERE id IN (
                        SELECT id FROM (
                            SELECT id FROM wechat_messages
                            WHERE status = 'pending'
                            ORDER BY msg_id, chunk_id, created_at ASC
                            LIMIT %s
                        ) AS sub
                    )
                ''', (poll_token, limit))
                if cursor.rowcount == 0:
                    return []

                cursor.execute('''
                    SELECT * FROM wechat_messages
                    WHERE poll_token = %s
                    ORDER BY msg_id, chunk_id, created_at ASC
                ''', (poll_token,))
                rows = cursor.fetchall()

            messages = []
            for row in rows:
                msg = dict(row)
                if msg.get('total_chunks', 1) > 1:
                    msg['content'] = f'[{msg["chunk_id"]}/{msg["total_chunks"]}]{msg["content"]}'
                metadata_str = msg.pop('metadata', None)
                if metadata_str and metadata_str != '{}':
                    try:
                        extra = json.loads(metadata_str)
                        if isinstance(extra, dict):
                            msg.update(extra)
                    except (json.JSONDecodeError, TypeError):
                        pass
                msg['poll_token'] = poll_token
                messages.append(msg)

            logger.info(f'[WechatStore] 原子claim: {len(messages)}条, token={poll_token[:16]}...')
            return messages
        except Exception as e:
            logger.error(f'[WechatStore] 原子claim失败: {e}')
            return []

    def mark_processed(self, msg_ids: List[int], response_content: str = None,
                       poll_token: str = None) -> bool:
        """标记消息已处理（需校验 poll_token）"""
        try:
            self._get_current_db()
            with self.get_cursor() as cursor:
                placeholders = ','.join('%s' for _ in msg_ids)
                params = []
                if poll_token:
                    if response_content:
                        cursor.execute(f'''
                            UPDATE wechat_messages
                            SET status = 'processed', processed_at = CURRENT_TIMESTAMP,
                                response_content = %s
                            WHERE id IN ({placeholders}) AND poll_token = %s AND status = 'polled'
                        ''', [response_content] + msg_ids + [poll_token])
                    else:
                        cursor.execute(f'''
                            UPDATE wechat_messages
                            SET status = 'processed', processed_at = CURRENT_TIMESTAMP
                            WHERE id IN ({placeholders}) AND poll_token = %s AND status = 'polled'
                        ''', msg_ids + [poll_token])
                else:
                    if response_content:
                        cursor.execute(f'''
                            UPDATE wechat_messages
                            SET status = 'processed', processed_at = CURRENT_TIMESTAMP,
                                response_content = %s
                            WHERE id IN ({placeholders})
                        ''', [response_content] + msg_ids)
                    else:
                        cursor.execute(f'''
                            UPDATE wechat_messages
                            SET status = 'processed', processed_at = CURRENT_TIMESTAMP
                            WHERE id IN ({placeholders})
                        ''', msg_ids)
                updated = cursor.rowcount
                if poll_token and updated != len(msg_ids):
                    logger.warning(f'[WechatStore] token校验失败: 期望{len(msg_ids)}条, 实际更新{updated}条')
                    return False
                return True
        except Exception as e:
            logger.error(f'[WechatStore] 标记处理失败: {e}')
            return False

    def release_orphaned_polled(self, timeout_seconds: int = 120) -> int:
        """释放超时未被确认的 polled 消息（回退为 pending）"""
        try:
            self._get_current_db()
            with self.get_cursor() as cursor:
                cursor.execute('''
                    UPDATE wechat_messages
                    SET status = 'pending', poll_token = '', polled_at = NULL
                    WHERE status = 'polled'
                    AND (UNIX_TIMESTAMP() - UNIX_TIMESTAMP(polled_at)) >= %s
                ''', (timeout_seconds,))
                released = cursor.rowcount
                if released > 0:
                    logger.info(f'[WechatStore] 释放孤儿polled消息: {released}条')
                return released
        except Exception as e:
            logger.error(f'[WechatStore] 释放孤儿消息失败: {e}')
            return 0

    def mark_error(self, msg_ids: List[int], error: str) -> bool:
        """标记消息处理出错"""
        try:
            self._get_current_db()
            with self.get_cursor() as cursor:
                placeholders = ','.join('%s' for _ in msg_ids)
                cursor.execute(f'''
                    UPDATE wechat_messages
                    SET status = 'error', error_message = %s
                    WHERE id IN ({placeholders})
                ''', [error] + msg_ids)
                return True
        except Exception as e:
            logger.error(f'[WechatStore] 标记错误失败: {e}')
            return False

    def get_db_files(self) -> List[Dict]:
        """MySQL 集中存储，无月份分文件"""
        return []

    def query_history(self, year: int, month: int, user_id: str = None,
                     status: str = None, limit: int = 100) -> List[Dict]:
        """查询指定月份的历史数据（MySQL 按时间过滤）"""
        try:
            self._get_current_db()
            cursor = self.conn.cursor()
            sql = 'SELECT * FROM wechat_messages WHERE YEAR(created_at) = %s AND MONTH(created_at) = %s'
            params = [year, month]
            if user_id:
                sql += ' AND user_id = %s'
                params.append(user_id)
            if status:
                sql += ' AND status = %s'
                params.append(status)
            sql += ' ORDER BY created_at DESC LIMIT %s'
            params.append(limit)

            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return rows  # DictCursor 已返回字典
        except Exception as e:
            logger.error(f'[WechatStore] 查询历史失败: {e}')
            return []

    def get_message_count(self, status: str = None) -> Dict:
        """获取当月消息统计"""
        try:
            cursor = self.conn.cursor()
            if status:
                cursor.execute('SELECT COUNT(*) AS cnt FROM wechat_messages WHERE status = %s', (status,))
                return {status: cursor.fetchone()['cnt']}
            else:
                cursor.execute('''
                    SELECT status, COUNT(*) as count
                    FROM wechat_messages
                    GROUP BY status
                ''')
                return {row['status']: row['count'] for row in cursor.fetchall()}
        except Exception as e:
            logger.error(f'[WechatStore] 统计失败: {e}')
            return {}

    def poll_by_cursor(self, since_id: int = 0, limit: int = 5) -> Dict:
        """游标式轮询：按 MySQL id 顺序拉取消息（不更改消息状态）

        Args:
            since_id: 上次拉取的最大 id，0 表示从头开始
            limit: 最大拉取条数

        Returns:
            dict: {messages, max_rowid, archived, has_more}
        """
        try:
            self._get_current_db()
            messages = []
            max_rowid = since_id
            archived = False
            with self.get_cursor() as cursor:
                cursor.execute('''
                    SELECT * FROM wechat_messages
                    WHERE id > %s
                    ORDER BY id ASC
                    LIMIT %s
                ''', (since_id, limit))
                rows = cursor.fetchall()

                for row in rows:
                    msg = dict(row)
                    if msg.get('total_chunks', 1) > 1:
                        msg['content'] = f'[{msg["chunk_id"]}/{msg["total_chunks"]}]{msg["content"]}'
                    metadata_str = msg.pop('metadata', None)
                    if metadata_str and metadata_str != '{}':
                        try:
                            extra = json.loads(metadata_str)
                            if isinstance(extra, dict):
                                msg.update(extra)
                        except (json.JSONDecodeError, TypeError):
                            pass
                    messages.append(msg)
                    max_rowid = row['id']

                if not archived and since_id > 0 and not rows:
                    count_row = cursor.execute('SELECT COUNT(*) as cnt FROM wechat_messages').fetchone()
                    if count_row and count_row['cnt'] > 0:
                        max_in_db = cursor.execute('SELECT MAX(id) as mx FROM wechat_messages').fetchone()
                        if max_in_db and max_in_db['mx'] is not None and max_in_db['mx'] < since_id:
                            archived = True

            return {
                'messages': messages,
                'max_rowid': max_rowid,
                'archived': archived,
                'has_more': len(messages) >= limit
            }
        except Exception as e:
            logger.error(f'[WechatStore] 游标轮询异常: {e}')
            return {'messages': [], 'max_rowid': since_id, 'archived': False, 'has_more': False}

    def save_outgoing_message(self, user_id: str, content: str, msg_type: str = 'text') -> Optional[int]:
        """保存待发送的消息到数据库"""
        try:
            self._get_current_db()
            import time
            import random
            msg_id = f"out_{int(time.time())}_{random.randint(1000, 9999)}"
            with self.get_cursor() as cursor:
                cursor.execute('''
                    INSERT INTO outgoing_messages (msg_id, user_id, content, msg_type, status)
                    VALUES (%s, %s, %s, %s, 'pending')
                ''', (msg_id, user_id, content, msg_type))
                return cursor.lastrowid
        except pymysql.err.IntegrityError:
            logger.warning(f'[WechatStore] 出站消息已存在: {user_id}')
            return None
        except Exception as e:
            logger.error(f'[WechatStore] 保存出站消息失败: {e}')
            return None

    def mark_outgoing_sent(self, msg_id: str, success: bool = True, error: str = None) -> bool:
        """标记出站消息已发送"""
        try:
            self._get_current_db()
            with self.get_cursor() as cursor:
                if success:
                    cursor.execute('''
                        UPDATE outgoing_messages
                        SET status = 'sent', sent_at = CURRENT_TIMESTAMP
                        WHERE msg_id = %s
                    ''', (msg_id,))
                else:
                    cursor.execute('''
                        UPDATE outgoing_messages
                        SET status = 'failed', error_message = %s,
                            retry_count = retry_count + 1,
                            last_retry_at = CURRENT_TIMESTAMP
                        WHERE msg_id = %s
                    ''', (error, msg_id))
                return True
        except Exception as e:
            logger.error(f'[WechatStore] 标记出站消息失败: {e}')
            return False

    def mark_dead_message(self, msg_id: str, reason: str = None) -> bool:
        """标记消息为死信，需要人工介入"""
        try:
            self._get_current_db()
            with self.get_cursor() as cursor:
                cursor.execute('''
                    UPDATE outgoing_messages
                    SET status = 'dead', dead_at = CURRENT_TIMESTAMP,
                        error_message = CONCAT(COALESCE(error_message, ''), ' [死信: ', %s, ']')
                    WHERE msg_id = %s
                ''', (reason or '超过最大重试次数', msg_id))
                return True
        except Exception as e:
            logger.error(f'[WechatStore] 标记死信失败: {e}')
            return False

    def get_dead_messages(self, limit: int = 100) -> List[Dict]:
        """获取死信消息列表"""
        try:
            self._get_current_db()
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT * FROM outgoing_messages
                WHERE status = 'dead'
                ORDER BY dead_at DESC LIMIT %s
            ''', (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f'[WechatStore] 查询死信失败: {e}')
            return []

    def get_outgoing_message(self, msg_id: str) -> Optional[Dict]:
        """获取单个出站消息"""
        try:
            self._get_current_db()
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM outgoing_messages WHERE msg_id = %s', (msg_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f'[WechatStore] 查询消息失败: {e}')
            return None

    def confirm_outgoing_message(self, msg_id: str) -> bool:
        """确认出站消息送达"""
        try:
            self._get_current_db()
            with self.get_cursor() as cursor:
                cursor.execute('''
                    UPDATE outgoing_messages
                    SET status = 'confirmed', confirmed = 1, confirmed_at = CURRENT_TIMESTAMP
                    WHERE msg_id = %s
                ''', (msg_id,))
                return True
        except Exception as e:
            logger.error(f'[WechatStore] 确认出站消息失败: {e}')
            return False

    def get_pending_outgoing(self, user_id: str = None, limit: int = 10) -> List[Dict]:
        """获取待确认的出站消息"""
        try:
            self._get_current_db()
            cursor = self.conn.cursor()
            if user_id:
                cursor.execute('''
                    SELECT * FROM outgoing_messages
                    WHERE user_id = %s AND status IN ('pending', 'sent')
                    ORDER BY created_at ASC LIMIT %s
                ''', (user_id, limit))
            else:
                cursor.execute('''
                    SELECT * FROM outgoing_messages
                    WHERE status IN ('pending', 'sent')
                    ORDER BY created_at ASC LIMIT %s
                ''', (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f'[WechatStore] 查询待发消息失败: {e}')
            return []

    def get_timeout_outgoing(self, timeout_seconds: int = 180, limit: int = 20) -> List[Dict]:
        """获取超时的出站消息（超过指定秒数未被拉取）"""
        try:
            self._get_current_db()
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT * FROM outgoing_messages
                WHERE status = 'pending'
                AND (UNIX_TIMESTAMP() - UNIX_TIMESTAMP(created_at)) >= %s
                ORDER BY created_at ASC LIMIT %s
            ''', (timeout_seconds, limit))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f'[WechatStore] 查询超时消息失败: {e}')
            return []

    def mark_expired_message(self, msg_id: str, reason: str = '') -> bool:
        """标记消息为超时无法送达"""
        try:
            self._get_current_db()
            with self.get_cursor() as cursor:
                cursor.execute('''
                    UPDATE outgoing_messages
                    SET status = 'expired',
                        error = %s,
                        expired_at = CURRENT_TIMESTAMP
                    WHERE msg_id = %s AND status = 'pending'
                ''', (reason, msg_id))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f'[WechatStore] 标记超时消息失败: {e}')
            return False

    def get_failed_outgoing(self, max_retries: int = 3, limit: int = 10) -> List[Dict]:
        """获取可重试的失败消息"""
        try:
            self._get_current_db()
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT * FROM outgoing_messages
                WHERE status = 'failed' AND retry_count < %s
                ORDER BY created_at ASC LIMIT %s
            ''', (max_retries, limit))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f'[WechatStore] 查询失败消息失败: {e}')
            return []

    def reset_for_retry(self, msg_id: str) -> bool:
        """重置消息状态以便重试"""
        try:
            self._get_current_db()
            with self.get_cursor() as cursor:
                cursor.execute('''
                    UPDATE outgoing_messages
                    SET status = 'pending'
                    WHERE msg_id = %s AND retry_count < 3
                ''', (msg_id,))
                return True
        except Exception as e:
            logger.error(f'[WechatStore] 重置消息失败: {e}')
            return False

    def get_outgoing_messages_by_status(self, status: str, limit: int = 50) -> List[Dict]:
        """按状态获取出站消息"""
        try:
            self._get_current_db()
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT * FROM outgoing_messages
                WHERE status = %s
                ORDER BY created_at DESC LIMIT %s
            ''', (status, limit))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f'[WechatStore] 按状态查询消息失败: {e}')
            return []

    def get_recent_outgoing_messages(self, limit: int = 50) -> List[Dict]:
        """获取最近的出站消息"""
        try:
            self._get_current_db()
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT * FROM outgoing_messages
                ORDER BY created_at DESC LIMIT %s
            ''', (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f'[WechatStore] 查询最近消息失败: {e}')
            return []

    def get_statistics(self, days: int = 7) -> Dict:
        """获取消息发送统计"""
        try:
            self._get_current_db()
            cursor = self.conn.cursor()

            cursor.execute('''
                SELECT status, COUNT(*) as count
                FROM outgoing_messages
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                GROUP BY status
            ''', (days,))
            status_counts = {row['status']: row['count'] for row in cursor.fetchall()}

            cursor.execute('''
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as success,
                       SUM(CASE WHEN status = 'dead' THEN 1 ELSE 0 END) as dead,
                       SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM outgoing_messages
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            ''', (days,))
            row = cursor.fetchone()

            total = row['total'] or 0
            success = row['success'] or 0
            success_rate = round(success / total * 100, 1) if total > 0 else 0

            return {
                'total': total,
                'success': success,
                'failed': row['failed'] or 0,
                'dead': row['dead'] or 0,
                'pending': status_counts.get('pending', 0),
                'success_rate': success_rate,
                'days': days
            }
        except Exception as e:
            logger.error(f'[WechatStore] 统计查询失败: {e}')
            return {'total': 0, 'success': 0, 'failed': 0, 'dead': 0, 'success_rate': 0}

    def close(self):
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
            self._conn = None
