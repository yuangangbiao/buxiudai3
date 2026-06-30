# -*- coding: utf-8 -*-
"""
单位管理数据访问层
"""
from models.database import get_connection
from datetime import datetime


class UnitDAO:
    """单位数据访问"""

    @staticmethod
    def get_all():
        """获取所有单位"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT code, name, category, is_preset FROM units ORDER BY category, code")
            rows = cursor.fetchall()
            cursor.close()
            return [(row['code'], row['name'], row['category'], bool(row['is_preset'])) for row in rows]
        finally:
            conn.close()

    @staticmethod
    def get_by_category(category: str):
        """按类别获取单位"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT code, name, category FROM units WHERE category = %s ORDER BY is_preset DESC, code", (category,))
            rows = cursor.fetchall()
            cursor.close()
            return [(row['code'], row['name'], row['category']) for row in rows]
        finally:
            conn.close()

    @staticmethod
    def get_by_code(code: str):
        """根据代码获取单位"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT code, name, category, is_preset FROM units WHERE code = %s", (code,))
            row = cursor.fetchone()
            cursor.close()
            if row:
                return {"code": row['code'], "name": row['name'], "category": row['category'], "is_preset": bool(row['is_preset'])}
            return None
        finally:
            conn.close()

    @staticmethod
    def add(code: str, name: str, category: str = "count") -> tuple:
        """添加自定义单位"""
        code = code.strip()
        name = name.strip()
        if not code:
            return False, "单位代码不能为空"
        if not name:
            return False, "单位名称不能为空"
        if len(code) > 20:
            return False, "单位代码过长"
        if len(name) > 50:
            return False, "单位名称过长"

        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, is_preset FROM units WHERE code = %s", (code,))
            existing = cursor.fetchone()
            if existing:
                if existing['is_preset']:
                    return False, f"「{code}」是预设单位，无法重复添加"
                return False, f"「{code}」已存在"

            cursor.execute("""
                INSERT INTO units (code, name, category, is_preset, created_at)
                VALUES (%s, %s, %s, 0, NOW())
            """, (code, name, category))
            conn.commit()
            cursor.close()
            return True, f"已添加单位「{name}」({code})"
        finally:
            conn.close()

    @staticmethod
    def remove(code: str) -> tuple:
        """删除自定义单位"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT is_preset FROM units WHERE code = %s", (code,))
            row = cursor.fetchone()
            if not row:
                cursor.close()
                return False, f"「{code}」不存在"
            if row['is_preset']:
                cursor.close()
                return False, f"「{code}」是预设单位，无法删除"

            cursor.execute("DELETE FROM units WHERE code = %s", (code,))
            conn.commit()
            success = cursor.rowcount > 0
            cursor.close()
            if success:
                return True, f"已删除「{code}」"
            return False, f"「{code}」删除失败"
        finally:
            conn.close()

    @staticmethod
    def update(code: str, name: str = None, category: str = None) -> tuple:
        """更新单位信息"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT is_preset FROM units WHERE code = %s", (code,))
            row = cursor.fetchone()
            if not row:
                cursor.close()
                return False, f"「{code}」不存在"
            if row['is_preset']:
                cursor.close()
                return False, f"「{code}」是预设单位，无法修改"

            updates = []
            params = []
            if name:
                updates.append("name = %s")
                params.append(name)
            if category:
                updates.append("category = %s")
                params.append(category)

            if updates:
                params.append(code)
                cursor.execute(f"UPDATE units SET {', '.join(updates)} WHERE code = %s", params)
                conn.commit()

            cursor.close()
            return True, f"已更新「{code}」"
        finally:
            conn.close()

    @staticmethod
    def get_categories():
        """获取所有单位类别"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT category FROM units ORDER BY category")
            rows = cursor.fetchall()
            cursor.close()
            return [row['category'] for row in rows]
        finally:
            conn.close()
