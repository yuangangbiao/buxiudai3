# -*- coding: utf-8 -*-
"""
审计日志服务 - 统一记录所有操作日志
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from models.database import get_connection

logger = logging.getLogger(__name__)


class AuditService:
    """审计日志服务"""
    
    # 操作类型常量
    ACTION_CREATE = 'CREATE'
    ACTION_UPDATE = 'UPDATE'
    ACTION_DELETE = 'DELETE'
    ACTION_STATUS_CHANGE = 'STATUS_CHANGE'
    ACTION_LOGIN = 'LOGIN'
    ACTION_LOGOUT = 'LOGOUT'
    ACTION_IMPORT = 'IMPORT'
    ACTION_EXPORT = 'EXPORT'
    
    # 实体类型常量
    ENTITY_ORDER = 'ORDER'
    ENTITY_INVENTORY = 'INVENTORY'
    ENTITY_PROCESS = 'PROCESS'
    ENTITY_OPERATOR = 'OPERATOR'
    ENTITY_BOM = 'BOM'
    ENTITY_ALERT = 'ALERT'
    
    @classmethod
    def _ensure_table(cls) -> None:
        """确保审计日志表存在"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                timestamp TEXT NOT NULL,
                operator TEXT,
                action TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT,
                before_data TEXT,
                after_data TEXT,
                remark TEXT,
                ip_address TEXT,
                extra_info TEXT
            )
        ''')
        conn.commit()
        conn.close()
    
    @classmethod
    def log(
        cls,
        action: str,
        entity_type: str,
        entity_id: str = None,
        before_data: Dict = None,
        after_data: Dict = None,
        operator: str = None,
        remark: str = None,
        **kwargs
    ) -> bool:
        """
        记录审计日志
        
        Args:
            action: 操作类型
            entity_type: 实体类型
            entity_id: 实体ID
            before_data: 操作前数据
            after_data: 操作后数据
            operator: 操作人
            remark: 备注
            
        Returns:
            是否成功
        """
        try:
            cls._ensure_table()
            
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO audit_logs 
                (timestamp, operator, action, entity_type, entity_id, 
                 before_data, after_data, remark, extra_info)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                operator,
                action,
                entity_type,
                entity_id,
                str(before_data) if before_data else None,
                str(after_data) if after_data else None,
                remark,
                str(kwargs) if kwargs else None
            ))
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(
                f"审计日志记录失败: {e}",
                exc_info=True,
                extra={
                    "entity_type": entity_type,
                    "entity_id": entity_id or "",
                    "operator": operator or "",
                    "action": action
                }
            )
            return False
    
    @classmethod
    def get_logs(
        cls,
        entity_type: str = None,
        entity_id: str = None,
        action: str = None,
        operator: str = None,
        start_date: str = None,
        end_date: str = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        查询审计日志
        
        Args:
            entity_type: 实体类型
            entity_id: 实体ID
            action: 操作类型
            operator: 操作人
            start_date: 开始日期
            end_date: 结束日期
            limit: 返回数量
            offset: 偏移量
        """
        cls._ensure_table()
        
        conditions = []
        params = []
        
        if entity_type:
            conditions.append("entity_type = ?")
            params.append(entity_type)
        if entity_id:
            conditions.append("entity_id = ?")
            params.append(entity_id)
        if action:
            conditions.append("action = ?")
            params.append(action)
        if operator:
            conditions.append("operator = ?")
            params.append(operator)
        if start_date:
            conditions.append("timestamp >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("timestamp <= ?")
            params.append(end_date + " 23:59:59")
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT * FROM audit_logs 
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        ''', params + [limit, offset])
        
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    @classmethod
    def get_entity_history(cls, entity_type: str, entity_id: str) -> List[Dict[str, Any]]:
        """获取实体的变更历史"""
        return cls.get_logs(entity_type=entity_type, entity_id=entity_id)
    
    @classmethod
    def get_operator_logs(cls, operator: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取操作员的操作日志"""
        return cls.get_logs(operator=operator, limit=limit)
    
    @classmethod
    def get_recent_logs(cls, hours: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
        """获取最近的操作日志"""
        start_time = (datetime.now() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
        return cls.get_logs(start_date=start_time, limit=limit)
    
    @classmethod
    def clear_old_logs(cls, days: int = 90) -> int:
        """
        清理旧日志
        
        Args:
            days: 保留天数
            
        Returns:
            删除的记录数
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        cls._ensure_table()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM audit_logs WHERE timestamp < ?', (cutoff_date,))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted


def audit_log(action: str, entity_type: str, **kwargs):
    """记录审计日志的便捷函数"""
    return AuditService.log(action, entity_type, **kwargs)
