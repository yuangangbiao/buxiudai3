# -*- coding: utf-8 -*-
"""
物料计算规则数据访问层
"""
from models.database import get_connection


class MaterialRulesDAO:
    """物料计算规则数据访问"""

    @staticmethod
    def create(product_type: str, material_param: str,
               material_name_template: str, spec_field: str = None,
               spec_unit: str = None, qty_field: str = None,
               qty_formula: str = None, qty_unit: str = None) -> int:
        """创建规则"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO material_rules
                (product_type, material_param, material_name_template, spec_field, spec_unit, qty_field, qty_formula, qty_unit)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (product_type, material_param, material_name_template, spec_field, spec_unit, qty_field, qty_formula, qty_unit))
            conn.commit()
            rule_id = cursor.lastrowid
            cursor.close()
            return rule_id
        finally:
            conn.close()

    @staticmethod
    def update(rule_id: int, data: dict) -> bool:
        """更新规则"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE material_rules SET
                    material_name_template = %s,
                    spec_field = %s,
                    spec_unit = %s,
                    qty_field = %s,
                    qty_formula = %s,
                    qty_unit = %s,
                    enabled = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (
                data.get("material_name_template"),
                data.get("spec_field"),
                data.get("spec_unit"),
                data.get("qty_field"),
                data.get("qty_formula"),
                data.get("qty_unit"),
                data.get("enabled", 1),
                rule_id
            ))
            conn.commit()
            success = cursor.rowcount > 0
            cursor.close()
            return success
        finally:
            conn.close()

    @staticmethod
    def delete(rule_id: int) -> bool:
        """删除规则"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM material_rules WHERE id = %s", (rule_id,))
            conn.commit()
            success = cursor.rowcount > 0
            cursor.close()
            return success
        finally:
            conn.close()

    @staticmethod
    def get_by_id(rule_id: int) -> dict:
        """根据ID获取规则"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM material_rules WHERE id = %s", (rule_id,))
            row = cursor.fetchone()
            cursor.close()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_by_product_type(product_type: str) -> list:
        """根据产品类型获取所有规则"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM material_rules WHERE product_type = %s AND enabled = 1 ORDER BY id",
                (product_type,)
            )
            rows = cursor.fetchall()
            cursor.close()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_all() -> list:
        """获取所有规则"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM material_rules ORDER BY product_type, id"
            )
            rows = cursor.fetchall()
            cursor.close()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_distinct_product_types() -> list:
        """获取所有已配置的产品类型"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT DISTINCT product_type FROM material_rules ORDER BY product_type"
            )
            rows = cursor.fetchall()
            cursor.close()
            return [r['product_type'] for r in rows] if rows else []
        finally:
            conn.close()

    @staticmethod
    def exists(product_type: str, material_param: str) -> bool:
        """检查规则是否存在"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM material_rules WHERE product_type = %s AND material_param = %s",
                (product_type, material_param)
            )
            row = cursor.fetchone()
            cursor.close()
            return row is not None
        finally:
            conn.close()
