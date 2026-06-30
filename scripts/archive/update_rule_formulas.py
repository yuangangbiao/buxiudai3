# -*- coding: utf-8 -*-
"""
批量更新工序规则公式 - 添加单位换算
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import get_connection
from models.process_calc_rule import ProcessCalcRuleDAO


def update_formulas():
    """更新所有使用 总长度/网带节距 的公式为 总长度*1000/网带节距"""
    conn = get_connection()
    try:
        cursor = conn.cursor()

        rules = ProcessCalcRuleDAO.get_all()
        print(f"共有 {len(rules)} 条规则")

        old_formula = "总长度/网带节距"
        new_formula = "总长度*1000/网带节距"

        update_count = 0
        for rule in rules:
            formula = rule.get("planned_qty_formula") or ""
            if old_formula in formula:
                new_formula_value = formula.replace(old_formula, new_formula)
                rule_id = rule.get("id")
                print(f"\n规则ID={rule_id}, 工序={rule.get('process_name')}")
                print(f"  旧公式: {formula}")
                print(f"  新公式: {new_formula_value}")

                cursor.execute(
                    "UPDATE process_calc_rules SET planned_qty_formula=%s WHERE id=%s",
                    (new_formula_value, rule_id)
                )
                update_count += 1

        conn.commit()
        print(f"\n✓ 成功更新 {update_count} 条规则")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        conn.rollback()
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = update_formulas()
    sys.exit(0 if success else 1)