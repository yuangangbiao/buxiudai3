# -*- coding: utf-8 -*-
"""
工序模板管理 - 数据库版
"""
import json
from datetime import datetime
from models.database import get_connection


def _get_db():
    return get_connection()


def get_all_process_templates() -> dict:
    """获取所有工序模板"""
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name, data_json FROM process_templates ORDER BY name")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    templates = {}
    for row in rows:
        data = json.loads(row["data_json"]) if row["data_json"] else []
        templates[row["name"]] = data
    return templates


def save_process_templates(templates: dict) -> tuple:
    """保存所有工序模板"""
    conn = _get_db()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        cursor.execute("DELETE FROM process_templates")
        for name, data in templates.items():
            data_json = json.dumps(data, ensure_ascii=False)
            cursor.execute("""
                INSERT INTO process_templates (name, data_json, created_at, updated_at)
                VALUES (%s, %s, %s, %s)
            """, (name, data_json, now, now))
        conn.commit()
        cursor.close()
        conn.close()
        return True, "工序模板已保存"
    except Exception as e:
        cursor.close()
        conn.close()
        return False, str(e)


def add_process_template(name: str, data: list) -> tuple:
    """添加一个工序模板"""
    conn = _get_db()
    cursor = conn.cursor()
    data_json = json.dumps(data, ensure_ascii=False)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        cursor.execute("""
            INSERT INTO process_templates (name, data_json, created_at, updated_at)
            VALUES (%s, %s, %s, %s)
        """, (name, data_json, now, now))
        conn.commit()
        cursor.close()
        conn.close()
        return True, f"模板「{name}」已添加"
    except Exception as e:
        cursor.close()
        conn.close()
        return False, f"模板「{name}」已存在"


def delete_process_template(name: str) -> tuple:
    """删除一个工序模板"""
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM process_templates WHERE name = %s", (name,))
    conn.commit()
    cursor.close()
    conn.close()
    return True, f"模板「{name}」已删除"


def rename_process_template(old_name: str, new_name: str) -> tuple:
    """重命名工序模板"""
    conn = _get_db()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE process_templates SET name = %s, updated_at = %s WHERE name = %s",
                 (new_name, now, old_name))
    conn.commit()
    cursor.close()
    conn.close()
    return True, "重命名成功"
