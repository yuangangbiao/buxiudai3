# -*- coding: utf-8 -*-
"""
物料备料模板管理模块 - 数据库版
支持模板的创建、保存、加载、修改和删除
"""
import json
from datetime import datetime
from models.database import get_connection


def _get_db():
    return get_connection()


def get_all_templates() -> list:
    """获取所有模板列表"""
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name, description, materials_json, created_at, updated_at FROM material_templates ORDER BY name")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    templates = []
    for row in rows:
        materials = json.loads(row["materials_json"]) if row["materials_json"] else []
        templates.append({
            "name": row["name"],
            "description": row["description"] or "",
            "materials": materials,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        })
    return templates


def get_template(name: str) -> dict:
    """获取指定模板"""
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name, description, materials_json, created_at, updated_at FROM material_templates WHERE name = %s", (name,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if not row:
        return None
    materials = json.loads(row["materials_json"]) if row["materials_json"] else []
    return {
        "name": row["name"],
        "description": row["description"] or "",
        "materials": materials,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"]
    }


def save_template(name: str, materials: list, description: str = "") -> tuple:
    """
    保存物料模板

    Args:
        name: 模板名称
        materials: 物料列表
        description: 模板描述

    Returns:
        tuple: (成功标志, 消息)
    """
    conn = _get_db()
    cursor = conn.cursor()
    materials_json = json.dumps(materials, ensure_ascii=False)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        cursor.execute("""
            INSERT INTO material_templates (name, description, materials_json, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (name, description, materials_json, now, now))
        conn.commit()
        cursor.close()
        conn.close()
        return True, f"模板「{name}」已保存"
    except Exception as e:
        cursor.close()
        conn.close()
        return False, f"模板「{name}」已存在，请使用其他名称"


def delete_template(name: str) -> tuple:
    """删除指定模板"""
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM material_templates WHERE name = %s", (name,))
    conn.commit()
    cursor.close()
    conn.close()
    return True, f"模板「{name}」已删除"


def rename_template(old_name: str, new_name: str) -> tuple:
    """重命名模板"""
    conn = _get_db()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE material_templates SET name = %s, updated_at = %s WHERE name = %s",
                 (new_name, now, old_name))
    conn.commit()
    cursor.close()
    conn.close()
    return True, "重命名成功"


def get_template_names() -> list:
    """获取所有模板名称列表"""
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM material_templates ORDER BY name")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [row["name"] for row in rows]
