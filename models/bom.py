# -*- coding: utf-8 -*-
"""
BOM物料清单模型
定义产品结构（产品 = 原材料 + 工艺 + 包装）
"""
from models.database import get_connection


class BOMDAO:
    """BOM物料清单数据访问"""

    @staticmethod
    def create(product_type: str, material: str, bom_data: dict) -> int:
        """创建BOM记录"""
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO bom_list (product_type, material,
                steel_weight, steel_unit,
                packaging_materials,
                surface_treatment,
                production_process,
                waste_rate, unit, remark,
                material_code, material_type, specification,
                unit_weight, standard_qty, actual_qty,
                price, supplier, lead_time, safety_stock,
                location, batch_no, expiry_date, draw_no, version)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            product_type,
            material,
            bom_data.get("steel_weight", 0),
            bom_data.get("steel_unit", "kg/米"),
            bom_data.get("packaging_materials", ""),
            bom_data.get("surface_treatment", ""),
            bom_data.get("production_process", ""),
            bom_data.get("waste_rate", 0),
            bom_data.get("unit", "米"),
            bom_data.get("remark", ""),
            bom_data.get("material_code", ""),
            bom_data.get("material_type", ""),
            bom_data.get("specification", ""),
            bom_data.get("unit_weight", 0),
            bom_data.get("standard_qty", 0),
            bom_data.get("actual_qty", 0),
            bom_data.get("price", 0),
            bom_data.get("supplier", ""),
            bom_data.get("lead_time", 0),
            bom_data.get("safety_stock", 0),
            bom_data.get("location", ""),
            bom_data.get("batch_no", ""),
            bom_data.get("expiry_date", ""),
            bom_data.get("draw_no", ""),
            bom_data.get("version", ""),
        ))
        conn.commit()
        bom_id = c.lastrowid
        conn.close()
        return bom_id

    @staticmethod
    def update(bom_id: int, bom_data: dict) -> bool:
        """更新BOM记录"""
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            UPDATE bom_list SET
                steel_weight = %s,
                steel_unit = %s,
                packaging_materials = %s,
                surface_treatment = %s,
                production_process = %s,
                waste_rate = %s,
                unit = %s,
                remark = %s,
                material_code = %s,
                material_type = %s,
                specification = %s,
                unit_weight = %s,
                standard_qty = %s,
                actual_qty = %s,
                price = %s,
                supplier = %s,
                lead_time = %s,
                safety_stock = %s,
                location = %s,
                batch_no = %s,
                expiry_date = %s,
                draw_no = %s,
                version = %s,
                updated_at = NOW()
            WHERE id = %s
        """, (
            bom_data.get("steel_weight", 0),
            bom_data.get("steel_unit", "kg/米"),
            bom_data.get("packaging_materials", ""),
            bom_data.get("surface_treatment", ""),
            bom_data.get("production_process", ""),
            bom_data.get("waste_rate", 0),
            bom_data.get("unit", "米"),
            bom_data.get("remark", ""),
            bom_data.get("material_code", ""),
            bom_data.get("material_type", ""),
            bom_data.get("specification", ""),
            bom_data.get("unit_weight", 0),
            bom_data.get("standard_qty", 0),
            bom_data.get("actual_qty", 0),
            bom_data.get("price", 0),
            bom_data.get("supplier", ""),
            bom_data.get("lead_time", 0),
            bom_data.get("safety_stock", 0),
            bom_data.get("location", ""),
            bom_data.get("batch_no", ""),
            bom_data.get("expiry_date", ""),
            bom_data.get("draw_no", ""),
            bom_data.get("version", ""),
            bom_id
        ))
        conn.commit()
        success = c.rowcount > 0
        conn.close()
        return success

    @staticmethod
    def delete(bom_id: int) -> bool:
        """删除BOM记录"""
        conn = get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM bom_list WHERE id = %s", (bom_id,))
        conn.commit()
        success = c.rowcount > 0
        conn.close()
        return success

    @staticmethod
    def get_by_id(bom_id: int) -> dict:
        """根据ID获取BOM"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bom_list WHERE id = %s", (bom_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def get_by_product(product_type: str, material: str = None) -> list:
        """根据产品类型获取BOM"""
        conn = get_connection()
        cursor = conn.cursor()
        if material:
            cursor.execute(
                "SELECT * FROM bom_list WHERE product_type = %s AND material = %s",
                (product_type, material)
            )
        else:
            cursor.execute(
                "SELECT * FROM bom_list WHERE product_type = %s",
                (product_type,)
            )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [dict(r) for r in rows] if rows else []

    @staticmethod
    def get_all(filters: dict = None) -> list:
        """获取所有BOM列表"""
        conn = get_connection()
        cursor = conn.cursor()
        sql = "SELECT * FROM bom_list WHERE 1=1"
        params = []

        if filters:
            if filters.get("product_type"):
                sql += " AND product_type LIKE %s"
                params.append(f"%{filters['product_type']}%")
            if filters.get("material"):
                sql += " AND material LIKE %s"
                params.append(f"%{filters['material']}%")

        sql += " ORDER BY product_type, material"
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def get_recent(limit: int = 200) -> list:
        """获取最近日期的BOM（默认加载限制）"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM bom_list
                   ORDER BY id DESC
                   LIMIT %s""",
                (limit,)
            )
            rows = cursor.fetchall()
            cursor.close()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def calculate_material_requirement(product_type: str, material: str,
                                        quantity: float) -> dict:
        """
        根据BOM计算材料需求
        返回：原材料需求量、损耗量、包装材料等
        """
        bom_list = BOMDAO.get_by_product(product_type, material)
        if not bom_list:
            return None

        bom = bom_list[0]
        waste_rate = bom.get("waste_rate", 0) / 100.0
        base_weight = bom.get("steel_weight", 0)

        actual_steel = base_weight * quantity * (1 + waste_rate)
        waste_amount = actual_steel - (base_weight * quantity)

        return {
            "product_type": product_type,
            "material": material,
            "quantity": quantity,
            "unit": bom.get("unit", "米"),
            "steel_weight_per_unit": base_weight,
            "steel_unit": bom.get("steel_unit", "kg/米"),
            "total_steel_required": actual_steel,
            "waste_rate": bom.get("waste_rate", 0),
            "waste_amount": waste_amount,
            "packaging_materials": bom.get("packaging_materials", ""),
            "surface_treatment": bom.get("surface_treatment", ""),
            "production_process": bom.get("production_process", ""),
        }


def init_bom_table():
    """初始化BOM表（仅创建表结构）"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS bom_list (
            id INT PRIMARY KEY AUTO_INCREMENT,
            product_type VARCHAR(50) NOT NULL,
            material VARCHAR(50) NOT NULL,
            steel_weight DECIMAL(10,2) DEFAULT 0,
            steel_unit VARCHAR(10) DEFAULT 'kg/米',
            packaging_materials TEXT,
            surface_treatment TEXT,
            production_process TEXT,
            waste_rate DECIMAL(5,2) DEFAULT 5,
            unit VARCHAR(10) DEFAULT '米',
            remark TEXT,
            material_code VARCHAR(50),
            material_type VARCHAR(50),
            specification VARCHAR(100),
            unit_weight DECIMAL(10,2) DEFAULT 0,
            standard_qty DECIMAL(10,2) DEFAULT 0,
            actual_qty DECIMAL(10,2) DEFAULT 0,
            price DECIMAL(10,2) DEFAULT 0,
            supplier VARCHAR(100),
            lead_time INT DEFAULT 0,
            safety_stock DECIMAL(10,2) DEFAULT 0,
            location VARCHAR(100),
            batch_no VARCHAR(50),
            expiry_date VARCHAR(20),
            draw_no VARCHAR(50),
            version VARCHAR(20),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_product_material (product_type, material)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    conn.commit()
    conn.close()
