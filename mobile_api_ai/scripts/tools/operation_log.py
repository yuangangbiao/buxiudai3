# -*- coding: utf-8 -*-
"""
操作日志模块 - 独立数据库存储

记录所有上下游指令操作日志
"""

import sqlite3
import json
import os
import sys
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class OperationLogDB:
    """操作日志数据库"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(base_dir, 'operation_logs.db')
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """初始化数据库表"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS operation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                direction TEXT NOT NULL,
                source TEXT NOT NULL,
                operation_type TEXT NOT NULL,
                content TEXT,
                details TEXT,
                result TEXT,
                user_id TEXT,
                wechat_name TEXT,
                order_no TEXT,
                process TEXT,
                quantity INTEGER,
                status TEXT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_direction ON operation_logs(direction)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_created_at ON operation_logs(created_at)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_order_no ON operation_logs(order_no)
        ''')
        conn.commit()
        conn.close()
        logger.info(f"[LogDB] 操作日志数据库初始化完成: {self.db_path}")

    def log_operation(self, direction: str, source: str, operation_type: str,
                     content: str = None, details: Dict = None,
                     result: str = None, user_id: str = None,
                     order_no: str = None, process: str = None,
                     quantity: int = None, status: str = None,
                     error_message: str = None,
                     wechat_name: str = None) -> int:
        """
        记录操作日志

        Args:
            direction: 方向 ('上游'/'下游')
            source: 来源 ('微信'/'主软件'/'系统')
            operation_type: 操作类型 ('下达任务'/'报工'/'查询'/'回调')
            content: 操作内容摘要
            details: 详细信息(JSON)
            result: 操作结果
            user_id: 用户ID
            order_no: 订单号
            process: 工序
            quantity: 数量
            status: 状态 ('成功'/'失败')
            error_message: 错误信息
            wechat_name: 微信用户名称

        Returns:
            日志ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO operation_logs 
            (direction, source, operation_type, content, details, result, 
             user_id, wechat_name, order_no, process, quantity, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            direction, source, operation_type, content,
            json.dumps(details, ensure_ascii=False) if details else None,
            result, user_id, wechat_name, order_no, process, quantity, status, error_message
        ))
        log_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return log_id

    def get_logs(self, direction: str = None, source: str = None,
                 operation_type: str = None, order_no: str = None,
                 start_date: str = None, end_date: str = None,
                 limit: int = 100, offset: int = 0) -> List[Dict]:
        """查询操作日志"""
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = 'SELECT * FROM operation_logs WHERE 1=1'
        params = []

        if direction:
            query += ' AND direction = ?'
            params.append(direction)
        if source:
            query += ' AND source = ?'
            params.append(source)
        if operation_type:
            query += ' AND operation_type = ?'
            params.append(operation_type)
        if order_no:
            query += ' AND order_no = ?'
            params.append(order_no)
        if start_date:
            query += ' AND created_at >= ?'
            params.append(start_date)
        if end_date:
            query += ' AND created_at <= ?'
            params.append(end_date)

        query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_stats(self, start_date: str = None, end_date: str = None) -> Dict:
        """获取统计信息"""
        conn = self._get_connection()
        cursor = conn.cursor()

        base_query = ''
        params = []
        if start_date:
            base_query += ' WHERE created_at >= ?'
            params.append(start_date)
        if end_date:
            if base_query:
                base_query += ' AND created_at <= ?'
            else:
                base_query += ' WHERE created_at <= ?'
            params.append(end_date)

        cursor.execute(f'SELECT COUNT(*) FROM operation_logs{base_query}', params)
        total = cursor.fetchone()[0]

        cursor.execute(f'''
            SELECT direction, COUNT(*) as count 
            FROM operation_logs{base_query}
            GROUP BY direction
        ''', params)
        by_direction = {row[0]: row[1] for row in cursor.fetchall()}

        cursor.execute(f'''
            SELECT operation_type, COUNT(*) as count 
            FROM operation_logs{base_query}
            GROUP BY operation_type
        ''', params)
        by_type = {row[0]: row[1] for row in cursor.fetchall()}

        cursor.execute(f'''
            SELECT status, COUNT(*) as count 
            FROM operation_logs{base_query}
            GROUP BY status
        ''', params)
        by_status = {row[0]: row[1] for row in cursor.fetchall()}

        conn.close()

        return {
            'total': total,
            'by_direction': by_direction,
            'by_type': by_type,
            'by_status': by_status
        }

_operation_log_db = None
_static_dir = None

def set_static_dir(static_dir: str):
    """设置静态文件目录（在初始化时调用）"""
    global _static_dir
    _static_dir = static_dir

def get_operation_log_db(db_path: str = None) -> OperationLogDB:
    """获取操作日志数据库实例"""
    global _operation_log_db, _static_dir
    if _operation_log_db is None:
        if db_path is None:
            if _static_dir:
                db_path = os.path.join(_static_dir, 'DAT', 'operation_logs.db')
            else:
                if getattr(sys, 'frozen', False):
                    base_dir = os.path.dirname(sys.executable)
                    db_path = os.path.join(base_dir, 'DAT', 'operation_logs.db')
                else:
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    db_path = os.path.join(base_dir, 'operation_logs.db')
        _operation_log_db = OperationLogDB(db_path)
    return _operation_log_db

def log_upstream(source: str, operation_type: str, content: str = None,
                details: Dict = None, result: str = None,
                user_id: str = None, order_no: str = None,
                process: str = None, quantity: int = None,
                status: str = '成功', error_message: str = None) -> int:
    """记录上游操作日志（主软件 -> 云端）"""
    return get_operation_log_db().log_operation(
        direction='上游', source=source, operation_type=operation_type,
        content=content, details=details, result=result,
        user_id=user_id, order_no=order_no, process=process,
        quantity=quantity, status=status, error_message=error_message
    )

def log_downstream(source: str, operation_type: str, content: str = None,
                  details: Dict = None, result: str = None,
                  user_id: str = None, order_no: str = None,
                  process: str = None, quantity: int = None,
                  status: str = '成功', error_message: str = None) -> int:
    """记录下游操作日志（云端 -> 微信）"""
    return get_operation_log_db().log_operation(
        direction='下游', source=source, operation_type=operation_type,
        content=content, details=details, result=result,
        user_id=user_id, order_no=order_no, process=process,
        quantity=quantity, status=status, error_message=error_message
    )