# -*- coding: utf-8 -*-
"""
工序计算规则数据访问层
每个工序可配置：
1. 生效条件（产品类型列表）
2. 工序计划数量计算（尺寸参数表达式，遵循括号先算原则）
"""
import json
from datetime import datetime
from models.database import get_connection
from utils.op_logger import log, log_match, log_calc, log_error


class ProcessCalcRuleDAO:

    @staticmethod
    def get_all() -> list:
        """获取所有工序计算规则"""
        conn = get_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, process_name, product_types_json, condition_expr,
                       planned_qty_formula, priority, enabled, created_at, updated_at,
                       default_worker, unit
                FROM process_calc_rules
                ORDER BY priority DESC
            """)
            rows = cursor.fetchall()
            result = []
            for row in rows:
                if isinstance(row, dict):
                    result.append(row)
                elif isinstance(row, (list, tuple)) and len(row) >= 9:
                    result.append({
                        "id": row[0],
                        "process_name": row[1],
                        "product_types_json": row[2],
                        "condition_expr": row[3],
                        "planned_qty_formula": row[4],
                        "priority": row[5],
                        "enabled": bool(row[6]),
                        "created_at": row[7],
                        "updated_at": row[8],
                        "default_worker": row[9] if len(row) > 9 else "",
                        "unit": row[10] if len(row) > 10 else "件",
                    })
            return result
        finally:
            if cursor:
                cursor.close()
            conn.close()

    @staticmethod
    def get_by_process(process_name: str) -> dict:
        """获取指定工序的规则"""
        conn = get_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, process_name, product_types_json, condition_expr,
                       planned_qty_formula, priority, enabled, created_at, updated_at,
                       default_worker, unit
                FROM process_calc_rules
                WHERE process_name = %s
            """, (process_name,))
            row = cursor.fetchone()
            if row:
                if isinstance(row, dict):
                    return row
                return {
                    "id": row[0],
                    "process_name": row[1],
                    "product_types_json": row[2],
                    "condition_expr": row[3],
                    "planned_qty_formula": row[4],
                    "priority": row[5],
                    "enabled": bool(row[6]),
                    "created_at": row[7],
                    "updated_at": row[8],
                    "default_worker": row[9] if len(row) > 9 else "",
                    "unit": row[10] if len(row) > 10 else "件",
                }
            return None
        finally:
            if cursor:
                cursor.close()
            conn.close()

    @staticmethod
    def create(process_name: str, product_types: list, condition_expr: str,
               planned_qty_formula: str, priority: int = 5, enabled: bool = True,
               default_worker: str = "", unit: str = "件") -> tuple:
        """创建工序计算规则"""
        if not process_name:
            return False, "工序名称不能为空", None

        conn = get_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            product_types_json = json.dumps(product_types, ensure_ascii=False)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("""
                INSERT INTO process_calc_rules
                (process_name, product_types_json, condition_expr, planned_qty_formula,
                 priority, enabled, created_at, updated_at, default_worker, unit)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (process_name, product_types_json, condition_expr, planned_qty_formula,
                  priority, enabled, now, now, default_worker, unit))

            conn.commit()
            rule_id = cursor.lastrowid
            return True, f"规则「{process_name}」已创建", rule_id
        except Exception as e:
            conn.rollback()
            return False, f"创建失败：{str(e)}", None
        finally:
            if cursor:
                cursor.close()
            conn.close()

    @staticmethod
    def update(rule_id: int, process_name: str, product_types: list, condition_expr: str,
              planned_qty_formula: str, priority: int = 5, enabled: bool = True,
              default_worker: str = "", unit: str = "件") -> tuple:
        """更新工序计算规则"""
        if not process_name:
            return False, "工序名称不能为空"

        conn = get_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            product_types_json = json.dumps(product_types, ensure_ascii=False)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("""
                UPDATE process_calc_rules
                SET process_name=%s, product_types_json=%s, condition_expr=%s,
                    planned_qty_formula=%s, priority=%s, enabled=%s, updated_at=%s,
                    default_worker=%s, unit=%s
                WHERE id=%s
            """, (process_name, product_types_json, condition_expr, planned_qty_formula,
                  priority, enabled, now, default_worker, unit, rule_id))

            conn.commit()

            if cursor.rowcount == 0:
                return False, "规则不存在或未修改"

            return True, f"规则「{process_name}」已更新"
        except Exception as e:
            conn.rollback()
            return False, f"更新失败：{str(e)}"
        finally:
            if cursor:
                cursor.close()
            conn.close()

    @staticmethod
    def delete(rule_id: int) -> tuple:
        """删除规则"""
        conn = get_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM process_calc_rules WHERE id=%s", (rule_id,))
            conn.commit()
            return True, "规则已删除"
        except Exception as e:
            conn.rollback()
            return False, f"删除失败：{str(e)}"
        finally:
            if cursor:
                cursor.close()
            conn.close()

    @staticmethod
    def exists_for_process(process_name: str) -> bool:
        """检查指定工序是否已有规则"""
        conn = get_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM process_calc_rules WHERE process_name=%s", (process_name,))
            result = cursor.fetchone()
            count = result[0] if isinstance(result, tuple) else result.get("COUNT(*)", 0)
            return count > 0
        finally:
            if cursor:
                cursor.close()
            conn.close()

    @staticmethod
    def init_default_rules(processes: list):
        """初始化默认规则（如果不存在）"""
        for proc in processes:
            if not ProcessCalcRuleDAO.exists_for_process(proc):
                conn = get_connection()
                cursor = None
                try:
                    cursor = conn.cursor()
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cursor.execute("""
                        INSERT INTO process_calc_rules
                        (process_name, product_types_json, condition_expr, planned_qty_formula, priority, enabled, created_at, updated_at, default_worker, unit)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (proc, "[]", "所有产品类型", "物料种类数量", 5, True, now, now, "", "件"))
                    conn.commit()
                except Exception:
                    conn.rollback()
                finally:
                    if cursor:
                        cursor.close()
                    conn.close()


class ProcessCalcEngine:
    """工序计算引擎 - 解析条件表达式并计算工序数量"""

    COND_OPERATORS = {
        "等于": lambda a, b: a == b,
        "不等于": lambda a, b: a != b,
        "大于": lambda a, b: float(a) > float(b),
        "小于": lambda a, b: float(a) < float(b),
        "大于等于": lambda a, b: float(a) >= float(b),
        "小于等于": lambda a, b: float(a) <= float(b),
        "包含": lambda a, b: b in str(a),
        "不包含": lambda a, b: b not in str(a),
    }

    COND_OPERATORS_EN = {
        ">": lambda a, b: float(a) > float(b),
        "<": lambda a, b: float(a) < float(b),
        ">=": lambda a, b: float(a) >= float(b),
        "<=": lambda a, b: float(a) <= float(b),
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
        "contains": lambda a, b: b in str(a),
        "not contains": lambda a, b: b not in str(a),
    }

    CALC_OPERATORS = {
        "+": lambda a, b: a + b,
        "-": lambda a, b: a - b,
        "*": lambda a, b: a * b,
        "/": lambda a, b: a / b if b != 0 else 0,
    }

    @classmethod
    def calculate_planned_qty(cls, formula: str, order_data: dict) -> float:
        """根据公式计算工序计划数量（向上取整）"""
        if not formula or not formula.strip():
            return 0.0

        try:
            import math
            import re
            calc_data = dict(order_data)
            calc_data["物料数量"] = cls._get_material_count(order_data.get("order_id"))

            resolved_formula = formula.strip()
            params_in_formula = re.findall(r'\{([^}]+)\}', resolved_formula)
            for param in params_in_formula:
                if param in calc_data and calc_data.get(param) is not None:
                    val = calc_data[param]
                    if isinstance(val, str):
                        try:
                            val = float(val)
                        except (ValueError, TypeError):
                            val = 0
                    resolved_formula = resolved_formula.replace(f"{{{param}}}", str(val))

            result = cls._calc_expr(resolved_formula, calc_data)
            final = math.ceil(result) if result > 0 else 0
            relevant_params = {k: v for k, v in calc_data.items() if k in params_in_formula}
            log_calc("工序计算", formula, relevant_params, f"{result} → 向上取整={final}")
            return final
        except Exception as e:
            return 0.0

    @classmethod
    def _get_material_count(cls, order_id):
        """获取订单的物料种类数（order_materials表中该订单的物料记录数）"""
        if not order_id:
            return 0
        try:
            from models.database import get_connection
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM order_materials WHERE order_id=%s AND required_qty > 0",
                (order_id,)
            )
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if row:
                if isinstance(row, dict):
                    return row.get("cnt", 0)
                return row[0] if row else 0
            return 0
        except Exception as e:
            return 0

    @classmethod
    def _calc_expr(cls, expr: str, data: dict) -> float:
        """递归计算数学表达式"""
        expr = expr.strip()

        if expr.startswith("{") and expr.endswith("}"):
            inner = expr[1:-1]
            expr = inner

        if expr.startswith("(") and expr.endswith(")"):
            inner = expr[1:-1]
            if cls._balanced_parens(inner):
                return cls._calc_expr(inner, data)

        for op in ["+", "-"]:
            if op in expr:
                parts = expr.split(op)
                if len(parts) > 1:
                    left = cls._calc_expr(parts[0].strip(), data)
                    right = cls._calc_expr(op.join(parts[1:]).strip(), data)
                    return cls.CALC_OPERATORS[op](left, right)

        for op in ["*", "/"]:
            if op in expr:
                parts = expr.split(op)
                if len(parts) > 1:
                    result = float(parts[0].strip()) if parts[0].strip().replace(".", "").replace("-", "").isdigit() else cls._calc_expr(parts[0].strip(), data)
                    for p in parts[1:]:
                        val = float(p.strip()) if p.strip().replace(".", "").replace("-", "").isdigit() else cls._calc_expr(p.strip(), data)
                        result = cls.CALC_OPERATORS[op](result, val)
                    return result

        if expr in data:
            try:
                val = data[expr]
                if isinstance(val, (int, float)):
                    return float(val)
                if isinstance(val, str):
                    val = val.strip()
                    if val:
                        return float(val)
                return 0.0
            except (ValueError, TypeError):
                return 0.0

        try:
            return float(expr)
        except Exception:
            pass

        return 0.0

    @classmethod
    def evaluate_condition(cls, condition_expr: str, order_data: dict) -> bool:
        """评估条件表达式"""
        if not condition_expr or not condition_expr.strip():
            return True

        expr = condition_expr.strip()

        if expr in ("所有产品类型", "无", "不限", "默认"):
            return True

        return cls._eval_expr(expr, order_data)

    @classmethod
    def _eval_expr(cls, expr: str, data: dict) -> bool:
        """递归解析表达式"""
        expr = expr.strip()

        if expr.startswith("(") and expr.endswith(")"):
            inner = expr[1:-1]
            if cls._balanced_parens(inner):
                return cls._eval_expr(inner, data)

        for op in [" AND ", " OR ", " and ", " or "]:
            parts = expr.split(op)
            if len(parts) > 1:
                results = [cls._eval_expr(p.strip(), data) for p in parts]
                return all(results) if "AND" in op.upper() else any(results)

        all_ops = {}
        all_ops.update(cls.COND_OPERATORS)
        all_ops.update(cls.COND_OPERATORS_EN)

        sorted_ops = sorted(all_ops.keys(), key=len, reverse=True)
        for op_name in sorted_ops:
            if op_name in expr:
                idx = expr.index(op_name)
                field = expr[:idx].strip()
                value = expr[idx + len(op_name):].strip()
                if field in data:
                    try:
                        field_val = data[field]
                        if isinstance(field_val, (int, float)):
                            return all_ops[op_name](float(field_val), float(value))
                        return all_ops[op_name](field_val, value)
                    except (ValueError, TypeError) as e:
                        return False
                return False

        return False

    @classmethod
    def _balanced_parens(cls, s: str) -> bool:
        """检查括号是否平衡"""
        count = 0
        for c in s:
            if c == "(":
                count += 1
            elif c == ")":
                count -= 1
            if count < 0:
                return False
        return count == 0

    @classmethod
    def should_include_process(cls, process_name: str, order_data: dict, rules: list) -> bool:
        """判断订单是否应该包含某个工序
        规则：只根据 product_types_json 是否包含订单产品类型来判断
        """
        import json

        for rule in rules:
            if rule.get("process_name") == process_name:
                product_types_json = rule.get("product_types_json")
                if not product_types_json:
                    log_match("工序匹配", process_name, order_data.get("product_type", ""), False, "规则的product_types_json为空")
                    return False

                try:
                    product_types = json.loads(product_types_json) if isinstance(product_types_json, str) else product_types_json
                    if not product_types:
                        log_match("工序匹配", process_name, order_data.get("product_type", ""), False, "产品类型列表为空")
                        return False

                    order_product_type = order_data.get("product_type") or order_data.get("产品类型", "")
                    matched = bool(order_product_type and order_product_type in product_types)
                    log_match("工序匹配", process_name, order_product_type, matched,
                              f"在规则列表 {product_types} 中" if matched else f"产品类型='{order_product_type}' 不在规则列表 {product_types} 中")
                    if matched:
                        return True
                    return False
                except Exception as e:
                    log_match("工序匹配", process_name, order_data.get("product_type", ""), False, f"解析异常: {e}")
                    return False
        log_match("工序匹配", process_name, order_data.get("product_type", ""), False, "该工序没有配置规则")
        return False

    @classmethod
    def generate_processes_from_order(cls, order_data: dict, all_processes: list) -> list:
        """根据订单数据和规则生成工序列表"""
        rules = ProcessCalcRuleDAO.get_all()
        result = []

        for idx, process_name in enumerate(all_processes, 1):
            if cls.should_include_process(process_name, order_data, rules):
                planned_qty = cls.calculate_planned_qty_for_process(process_name, rules, order_data)
                default_worker, unit = cls.get_rule_extra(process_name, rules)
                from core.config import get_process_code, get_process_seq
                result.append({
                    "process_name": process_name,
                    "process_code": get_process_code(process_name),
                    "process_seq": idx,
                    "display_seq": get_process_seq(process_name),
                    "planned_qty": planned_qty,
                    "default_worker": default_worker,
                    "unit": unit
                })

        return result

    @classmethod
    def get_rule_extra(cls, process_name: str, rules: list) -> tuple:
        """获取工序规则的默认负责人和单位"""
        for rule in rules:
            if rule.get("process_name") == process_name:
                return (
                    rule.get("default_worker", "") or "",
                    rule.get("unit", "件") or "件"
                )
        return ("", "件")

    @classmethod
    def calculate_planned_qty_for_process(cls, process_name: str, rules: list, order_data: dict) -> float:
        """获取指定工序的计划数量"""
        for rule in rules:
            if rule.get("process_name") == process_name:
                formula = rule.get("planned_qty_formula") or ""
                if formula:
                    return cls.calculate_planned_qty(formula, order_data)
                return 1.0
        return 1.0