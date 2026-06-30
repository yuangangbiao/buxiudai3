# -*- coding: utf-8 -*-
"""
产品类型数据访问
"""
import os
from models.database import get_connection


class ProductTypeDAO:

    @staticmethod
    def create(name: str, description: str = "") -> int:
        """创建产品类型"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO product_types (name, description) VALUES (%s, %s)",
                (name, description)
            )
            conn.commit()
            cursor.execute("SELECT last_insert_id()")
            last_id = cursor.fetchone()
            cursor.close()
            return last_id[0] if last_id else 0
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def get_all() -> list:
        """获取所有产品类型"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM product_types ORDER BY name"
        )
        rows = cursor.fetchall()
        cursor.close()
        return [dict(r) for r in rows]

    @staticmethod
    def get_all_names() -> list:
        """获取所有产品类型名称"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM product_types ORDER BY name"
            )
            rows = cursor.fetchall()
            cursor.close()
            return [r['name'] for r in rows] if rows else []
        finally:
            conn.close()

    @staticmethod
    def exists(name: str) -> bool:
        """检查产品类型是否存在"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM product_types WHERE name = %s",
                (name,)
            )
            row = cursor.fetchone()
            cursor.close()
            return row['cnt'] > 0 if row else False
        finally:
            conn.close()

    @staticmethod
    def delete(name: str) -> bool:
        """删除产品类型"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM product_types WHERE name = %s", (name,))
            conn.commit()
            cursor.close()
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def update(name: str, new_name: str, description: str = "") -> bool:
        """更新产品类型"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE product_types SET name = %s, description = %s WHERE name = %s",
                (new_name, description, name)
            )
            conn.commit()
            cursor.close()
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def init_default_types():
        """初始化默认产品类型"""
        from config import PRODUCT_TYPES as DEFAULT_TYPES

        conn = get_connection()
        try:
            for name in DEFAULT_TYPES:
                if not ProductTypeDAO.exists(name):
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO product_types (name, description) VALUES (%s, %s)",
                        (name, "")
                    )
                    cursor.close()
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
