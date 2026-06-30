# -*- coding: utf-8 -*-
"""
质量监督规则数据访问层
每个规则可配置：
1. 规则名称
2. 生效条件（产品类型列表）
3. 质检项目列表（inspection_items_json）
4. 质检判定公式（check_formula）
"""
import json
from datetime import datetime
from models.database import get_connection
from utils.op_logger import log, log_error


class QualityRuleDAO:

    @staticmethod
    def get_all() -> list:
        """获取所有质量监督规则"""
        conn = get_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, rule_name, process_name, product_types_json, condition_expr,
                       inspection_items_json, check_formula, priority, enabled,
                       created_at, updated_at
                FROM quality_rules
                ORDER BY priority DESC, id ASC
            """)
            rows = cursor.fetchall()
            result = []
            for row in rows:
                if isinstance(row, dict):
                    result.append(row)
                elif isinstance(row, (list, tuple)) and len(row) >= 10:
                    result.append({
                        "id": row[0],
                        "rule_name": row[1],
                        "process_name": row[2],
                        "product_types_json": row[3],
                        "condition_expr": row[4],
                        "inspection_items_json": row[5],
                        "check_formula": row[6],
                        "priority": row[7],
                        "enabled": bool(row[8]),
                        "created_at": row[9],
                        "updated_at": row[10],
                    })
            return result
        finally:
            if cursor:
                cursor.close()
            conn.close()

    @staticmethod
    def get_by_id(rule_id: int) -> dict:
        """获取指定ID的规则"""
        conn = get_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, rule_name, process_name, product_types_json, condition_expr,
                       inspection_items_json, check_formula, priority, enabled,
                       created_at, updated_at
                FROM quality_rules
                WHERE id = %s
            """, (rule_id,))
            row = cursor.fetchone()
            if row:
                if isinstance(row, dict):
                    return row
                return {
                    "id": row[0],
                    "rule_name": row[1],
                    "process_name": row[2],
                    "product_types_json": row[3],
                    "condition_expr": row[4],
                    "inspection_items_json": row[5],
                    "check_formula": row[6],
                    "priority": row[7],
                    "enabled": bool(row[8]),
                    "created_at": row[9],
                    "updated_at": row[10],
                }
            return None
        finally:
            if cursor:
                cursor.close()
            conn.close()

    @staticmethod
    def get_rules_by_process(process_name: str) -> list:
        """获取指定工序的质检规则"""
        all_rules = QualityRuleDAO.get_all()
        matching = []
        for rule in all_rules:
            if not rule.get("enabled", True):
                continue
            if rule.get("process_name") == process_name:
                matching.append(rule)
        return matching

    @staticmethod
    def create(rule_name: str, product_types: list, condition_expr: str,
               inspection_items: list, check_formula: str = "",
               priority: int = 5, enabled: bool = True, process_name: str = "") -> tuple:
        """创建质量监督规则"""
        if not rule_name:
            return False, "规则名称不能为空", None

        conn = get_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO quality_rules
                (rule_name, process_name, product_types_json, condition_expr, inspection_items_json,
                 check_formula, priority, enabled)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                rule_name,
                process_name,
                json.dumps(product_types, ensure_ascii=False),
                condition_expr,
                json.dumps(inspection_items, ensure_ascii=False),
                check_formula,
                priority,
                1 if enabled else 0
            ))
            rule_id = cursor.lastrowid
            conn.commit()
            log("质量规则", "创建规则", f"规则ID={rule_id}, 名称={rule_name}")
            return True, "规则创建成功", rule_id
        except Exception as e:
            conn.rollback()
            log_error("质量规则", "创建失败", str(e))
            return False, f"创建失败：{e}", None
        finally:
            if cursor:
                cursor.close()
            conn.close()

    @staticmethod
    def update(rule_id: int, rule_name: str, product_types: list, condition_expr: str,
              inspection_items: list, check_formula: str = "",
              priority: int = 5, enabled: bool = True, process_name: str = "") -> tuple:
        """更新质量监督规则"""
        conn = get_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE quality_rules
                SET rule_name=%s, process_name=%s, product_types_json=%s, condition_expr=%s,
                    inspection_items_json=%s, check_formula=%s,
                    priority=%s, enabled=%s, updated_at=NOW()
                WHERE id=%s
            """, (
                rule_name,
                process_name,
                json.dumps(product_types, ensure_ascii=False),
                condition_expr,
                json.dumps(inspection_items, ensure_ascii=False),
                check_formula,
                priority,
                1 if enabled else 0,
                rule_id
            ))
            conn.commit()
            log("质量规则", "更新规则", f"规则ID={rule_id}, 名称={rule_name}")
            return True, "规则更新成功", rule_id
        except Exception as e:
            conn.rollback()
            log_error("质量规则", "更新失败", str(e))
            return False, f"更新失败：{e}", None
        finally:
            if cursor:
                cursor.close()
            conn.close()

    @staticmethod
    def delete(rule_id: int) -> tuple:
        """删除质量监督规则"""
        conn = get_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM quality_rules WHERE id=%s", (rule_id,))
            conn.commit()
            log("质量规则", "删除规则", f"规则ID={rule_id}")
            return True, "规则删除成功"
        except Exception as e:
            conn.rollback()
            log_error("质量规则", "删除失败", str(e))
            return False, f"删除失败：{e}"
        finally:
            if cursor:
                cursor.close()
            conn.close()

    @staticmethod
    def get_rule_items(rule_id: int) -> list:
        """获取规则的所有检查项公式"""
        conn = get_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, inspection_item, check_formula, tolerance
                FROM quality_rule_items
                WHERE rule_id = %s
                ORDER BY id
            """, (rule_id,))
            rows = cursor.fetchall()
            result = []
            for row in rows:
                if isinstance(row, dict):
                    result.append(row)
                elif isinstance(row, (list, tuple)):
                    result.append({
                        "id": row[0],
                        "inspection_item": row[1],
                        "check_formula": row[2],
                        "tolerance": row[3] if len(row) > 3 else None
                    })
            return result
        finally:
            if cursor:
                cursor.close()
            conn.close()

    @staticmethod
    def save_rule_items(rule_id: int, items_data: dict) -> bool:
        """保存规则的检查项公式和公差 {item_name: {"formula": ..., "tolerance": ...}}"""
        conn = get_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM quality_rule_items WHERE rule_id = %s", (rule_id,))
            for item_name, data in items_data.items():
                if isinstance(data, dict):
                    formula = data.get("formula", "")
                    tolerance = data.get("tolerance", "")
                else:
                    formula = data
                    tolerance = ""
                if formula and formula.strip():
                    cursor.execute("""
                        INSERT INTO quality_rule_items (rule_id, inspection_item, check_formula, tolerance)
                        VALUES (%s, %s, %s, %s)
                    """, (rule_id, item_name, formula.strip(), tolerance.strip() if tolerance else ""))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            log_error("质量规则", "保存检查项公式失败", str(e))
            return False
        finally:
            if cursor:
                cursor.close()
            conn.close()

    @staticmethod
    def add_rule_item(rule_id: int, inspection_item: str, check_formula: str = "", tolerance: str = "") -> bool:
        """添加单个规则检查项"""
        if not inspection_item:
            return False
        conn = get_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO quality_rule_items (rule_id, inspection_item, check_formula, tolerance)
                VALUES (%s, %s, %s, %s)
            """, (rule_id, inspection_item, check_formula or "", tolerance or ""))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            log_error("质量规则", "添加检查项失败", str(e))
            return False
        finally:
            if cursor:
                cursor.close()
            conn.close()

    @staticmethod
    def get_matching_rules(product_type: str) -> list:
        """获取适用于指定产品类型的质检规则"""
        all_rules = QualityRuleDAO.get_all()
        matching = []
        for rule in all_rules:
            if not rule.get("enabled", True):
                continue
            product_types_json = rule.get("product_types_json")
            if not product_types_json:
                continue
            try:
                product_types = json.loads(product_types_json) if isinstance(product_types_json, str) else product_types_json
                if product_type in product_types:
                    matching.append(rule)
            except Exception:
                continue
        return matching

    @staticmethod
    def evaluate_quality_rules(order_id: int, measured_values: dict) -> dict:
        """
        评估质检规则，返回各检查项的判定结果
        order_id: 订单ID
        measured_values: {检查项名称: 实测值}
        返回: {
            "passed": True/False,
            "alerts": [{"item": "检查项", "measured": 802, "standard": 800, "tolerance": "±5", "is_passed": False}],
            "record_items": [{"inspection_item": ..., "measured_value": ..., "standard_value": ..., "tolerance": ..., "is_passed": ...}]
        }
        """
        from models.order import OrderDAO
        from models.process_calc_rule import ProcessCalcEngine

        order = OrderDAO.get_by_id(order_id)
        if not order:
            return {"passed": True, "alerts": [], "record_items": []}

        product_type = order.get("product_type", "")
        rules = QualityRuleDAO.get_matching_rules(product_type)
        if not rules:
            return {"passed": True, "alerts": [], "record_items": []}

        rule = rules[0]
        rule_items = QualityRuleDAO.get_rule_items(rule["id"])

        order_data = {
            "宽度": order.get("width") or order.get("宽度", 0),
            "长度": order.get("length") or order.get("长度", 0),
            "目数": order.get("mesh_count") or order.get("目数", 0),
            "丝径": order.get("wire_diameter") or order.get("丝径", 0),
            "螺距": order.get("pitch") or order.get("螺距", 0),
            "边高": order.get("edge_height") or order.get("边高", 0),
            "翻边宽度": order.get("flange_width") or order.get("翻边宽度", 0),
            "材质": order.get("material", ""),
            "表面处理": order.get("surface_finish", ""),
        }

        alerts = []
        record_items = []

        for item in rule_items:
            item_name = item["inspection_item"]
            formula = item.get("check_formula", "")
            tolerance = item.get("tolerance", "")

            if not formula:
                record_items.append({
                    "inspection_item": item_name,
                    "measured_value": measured_values.get(item_name, ""),
                    "standard_value": "",
                    "tolerance": tolerance,
                    "is_passed": True
                })
                continue

            try:
                calc_result = ProcessCalcEngine._calc_expr(formula.strip(), order_data)
                standard_value = calc_result
            except Exception:
                standard_value = 0

            measured_str = measured_values.get(item_name, "")
            try:
                measured = float(measured_str) if measured_str else 0
            except (ValueError, TypeError):
                measured = 0

            is_passed = True
            if tolerance and standard_value:
                try:
                    tol_val = abs(float(tolerance.replace("±", "").replace("+", "").replace("-", "")))
                    is_passed = abs(measured - standard_value) <= tol_val
                except Exception:
                    is_passed = True

            record_items.append({
                "inspection_item": item_name,
                "measured_value": measured_str,
                "standard_value": str(standard_value),
                "tolerance": tolerance,
                "is_passed": is_passed
            })

            if not is_passed:
                alerts.append({
                    "item": item_name,
                    "measured": measured,
                    "standard": standard_value,
                    "tolerance": tolerance,
                    "is_passed": False
                })

        return {
            "passed": len(alerts) == 0,
            "alerts": alerts,
            "record_items": record_items
        }

    @staticmethod
    def init_default_rules():
        """初始化默认质检规则（如果表为空）"""
        conn = get_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM quality_rules")
            row = cursor.fetchone()
            count = row[0] if row else 0
            if count > 0:
                return
            default_rules = [
                {
                    "rule_name": "原材料检验",
                    "process_name": "原材料检验",
                    "product_types": ["冷冻网带", "冷冻螺旋网", "勾子链网带", "平板型网带",
                                     "弹簧网", "眼镜网带", "螺旋网带", "链板式网带",
                                     "链网", "马蹄形网带", "乙字形网带", "人字形网带"],
                    "inspection_items": ["材质核对", "外观检查", "尺寸核对"],
                    "check_formula": "",
                    "priority": 10
                },
                {
                    "rule_name": "过程检验",
                    "process_name": "生产过程",
                    "product_types": ["冷冻网带", "冷冻螺旋网", "勾子链网带", "平板型网带",
                                     "弹簧网", "眼镜网带", "螺旋网带", "链板式网带",
                                     "链网", "马蹄形网带"],
                    "inspection_items": ["尺寸检验", "外观检验"],
                    "check_formula": "",
                    "priority": 8
                },
                {
                    "rule_name": "终检",
                    "process_name": "最终检验",
                    "product_types": ["冷冻网带", "冷冻螺旋网", "勾子链网带", "平板型网带",
                                     "弹簧网", "眼镜网带", "螺旋网带", "链板式网带",
                                     "链网", "马蹄形网带", "乙字形网带", "人字形网带"],
                    "inspection_items": ["全面检查", "性能测试", "包装检查"],
                    "check_formula": "",
                    "priority": 5
                },
            ]
            for rule in default_rules:
                cursor.execute("""
                    INSERT INTO quality_rules
                    (rule_name, process_name, product_types_json, condition_expr, inspection_items_json,
                     check_formula, priority, enabled)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 1)
                """, (
                    rule["rule_name"],
                    rule["process_name"],
                    json.dumps(rule["product_types"], ensure_ascii=False),
                    "",
                    json.dumps(rule["inspection_items"], ensure_ascii=False),
                    rule["check_formula"],
                    rule["priority"]
                ))
            conn.commit()
            log("质量规则", "初始化", f"已创建 {len(default_rules)} 条默认规则")
        except Exception as e:
            conn.rollback()
            log_error("质量规则", "初始化失败", str(e))
        finally:
            if cursor:
                cursor.close()
            conn.close()
