# -*- coding: utf-8 -*-
"""
物料计算引擎 v2.0
根据订单参数自动计算物料种类和数量
新逻辑：材质参数值 + 材质名称，数量由客户定义的计算规则决定
"""
import re
import logging
import ast
from operator import add, sub, mul, truediv
from models.material_rules import MaterialRulesDAO
from utils.order_templates import DIM_FIELDS, MATERIAL_FIELDS
from config import MATERIAL_DENSITIES

logger = logging.getLogger(__name__)

# 安全表达式求值
SAFE_OPS = {
    '+': add, '-': sub, '*': mul, '/': truediv,
}

def safe_eval_formula(formula: str) -> float:
    """安全公式计算 - 不使用eval"""
    if not formula:
        return 0.0

    formula = formula.replace('×', '*').replace('÷', '/').replace('X', '*').replace('x', '*')

    allowed_chars = set("0123456789.+-*/() ")
    if not all(c in allowed_chars for c in formula):
        raise ValueError("公式包含非法字符")

    try:
        tokens = tokenize(formula)
        return evaluate(tokens)
    except Exception as e:
        logger.warning(f"[WARN] 安全公式计算失败: {e}")
        return 0.0

def tokenize(formula: str) -> list:
    """词法分析：将公式字符串转换为token列表"""
    tokens = []
    num = ''
    for char in formula:
        if char.isdigit() or char == '.':
            num += char
        elif char in '+-*/() ':
            if num:
                tokens.append(('NUM', float(num)))
                num = ''
            if char != ' ':
                tokens.append(('OP', char))
    if num:
        tokens.append(('NUM', float(num)))
    return tokens

def evaluate(tokens: list) -> float:
    """基于逆波兰表达式求值"""
    if not tokens:
        return 0.0

    output = []
    ops = []
    
    precedence = {'+': 1, '-': 1, '*': 2, '/': 2}
    
    for token in tokens:
        if token[0] == 'NUM':
            output.append(token[1])
        elif token[1] == '(':
            ops.append(token[1])
        elif token[1] == ')':
            while ops and ops[-1] != '(':
                op = ops.pop()
                b = output.pop()
                a = output.pop()
                output.append(SAFE_OPS[op](a, b))
            ops.pop()  # 弹出 '('
        else:  # 操作符
            while ops and ops[-1] != '(' and precedence.get(ops[-1], 0) >= precedence.get(token[1], 0):
                op = ops.pop()
                b = output.pop()
                a = output.pop()
                output.append(SAFE_OPS[op](a, b))
            ops.append(token[1])
    
    while ops:
        op = ops.pop()
        b = output.pop()
        a = output.pop()
        output.append(SAFE_OPS[op](a, b))
    
    return output[0] if output else 0.0


class MaterialCalculator:
    """物料计算引擎 v2.0"""

    def __init__(self, order_params: dict):
        self.order_params = order_params
        self.product_type = order_params.get("product_type", "")
        self.materials = []
        self.dim_fields_map = {f["key"]: f for f in DIM_FIELDS}

    def calculate_material_types(self) -> list:
        """计算物料种类和数量"""
        rules = MaterialRulesDAO.get_by_product_type(self.product_type)
        rules_map = {r["material_param"]: r for r in rules}

        material_fields = {f["key"]: f for f in MATERIAL_FIELDS}

        for mat_param_key, mat_param_field in material_fields.items():
            mat_value = self.order_params.get(mat_param_key)
            if not mat_value:
                continue

            param_name = mat_param_key.replace("材质", "")
            material_name = f"{mat_value}{param_name}"

            rule = rules_map.get(mat_param_key, {})

            spec_value = None
            spec_unit = ""

            qty_value = None
            qty_unit = None
            missing_params = []

            if rule:
                spec_field = rule.get("spec_field")
                spec_value = None
                rule_spec_unit = rule.get("spec_unit")
                spec_unit = rule_spec_unit if rule_spec_unit else ""

                if spec_field:
                    spec_fields_list = [s.strip() for s in spec_field.split(",")]
                    missing_specs = [s for s in spec_fields_list if s not in self.order_params]
                    if missing_specs:
                        missing_params.extend([f"规格字段「{s}」" for s in missing_specs])
                    else:
                        spec_value = "".join([str(self.order_params[s]) for s in spec_fields_list])
                        if not rule_spec_unit:
                            for dim_field in DIM_FIELDS:
                                if dim_field["key"] == spec_fields_list[0]:
                                    spec_unit = dim_field.get("unit", "")
                                    break

                qty_field = rule.get("qty_field")
                qty_formula = rule.get("qty_formula")

                if qty_formula:
                    placeholders = re.findall(r'\{([^}]+)\}', qty_formula)
                    formula_missing = [p for p in placeholders if p not in self.order_params]
                    missing_params.extend([f"「{p}」" for p in formula_missing])
                    if not formula_missing:
                        base_value = self.order_params.get(qty_field, 1)
                        qty_value = self._calculate_qty(base_value, qty_formula, spec_value)
                        if rule.get("qty_unit"):
                            qty_unit = rule.get("qty_unit")
                        else:
                            dim_field = self.dim_fields_map.get(qty_field, {})
                            qty_unit = dim_field.get("unit")
                            if not qty_unit:
                                missing_params.append(f"数量单位「{qty_field}」未配置单位，请在 DIM_FIELDS 或 material_rules 中设置")
                elif qty_field:
                    base_value = self.order_params.get(qty_field, 1)
                    if base_value is not None and base_value != "":
                        qty_value = float(base_value)
                        if rule.get("qty_unit"):
                            qty_unit = rule.get("qty_unit")
                        else:
                            dim_field = self.dim_fields_map.get(qty_field, {})
                            qty_unit = dim_field.get("unit")
                            if not qty_unit:
                                missing_params.append(f"数量单位「{qty_field}」未配置单位，请在 DIM_FIELDS 或 material_rules 中设置")

            material_item = {
                "material_name": material_name,
                "material_param": mat_param_key,
                "material_value": mat_value,
                "spec_value": spec_value,
                "spec_unit": spec_unit,
                "qty_value": qty_value,
                "qty_unit": qty_unit,
                "rule_enabled": bool(rule),
                "missing_params": missing_params,
            }

            self.materials.append(material_item)

        return self.materials

    def _calculate_qty(self, base_value, formula: str = None, spec_value=None) -> float:
        """计算数量"""
        if formula:
            formula_str = formula.replace("{qty}", str(base_value))
            formula_str = formula_str.replace("{quantity}", str(base_value))
            formula_str = self._auto_brace_params(formula_str)
            spec_placeholders = re.findall(r'\{([^}]+)\}', formula_str)
            material_keys = {f["key"] for f in MATERIAL_FIELDS}
            for placeholder in spec_placeholders:
                if placeholder in material_keys:
                    mat_value = self.order_params.get(placeholder)
                    if mat_value:
                        density = MATERIAL_DENSITIES.get(mat_value, 0)
                        formula_str = formula_str.replace(f"{{{placeholder}}}", str(density))
                elif placeholder in MATERIAL_DENSITIES:
                    density = MATERIAL_DENSITIES.get(placeholder, 0)
                    formula_str = formula_str.replace(f"{{{placeholder}}}", str(density))
                elif placeholder in self.order_params:
                    formula_str = formula_str.replace(f"{{{placeholder}}}", str(self.order_params[placeholder]))
            for param_key, param_value in self.order_params.items():
                if isinstance(param_value, (int, float)):
                    formula_str = formula_str.replace(param_key, str(param_value))
                elif isinstance(param_value, str):
                    try:
                        numeric_value = float(param_value)
                        if numeric_value.is_integer():
                            numeric_value = int(numeric_value)
                        formula_str = formula_str.replace(param_key, str(numeric_value))
                    except (ValueError, TypeError):
                        pass
            if "密度" in formula_str:
                mat_value = self.order_params.get("网丝材质")
                if mat_value:
                    density = MATERIAL_DENSITIES.get(mat_value, 7930)
                    formula_str = formula_str.replace("密度", str(density))
            formula_str = formula_str.replace("×", "*").replace("÷", "/").replace("X", "*").replace("x", "*")

            allowed_chars = set("0123456789.+-*/() ")
            if all(c in allowed_chars for c in formula_str):
                try:
                    # 使用安全公式计算，替代eval
                    return round(safe_eval_formula(formula_str), 2)
                except Exception as e:
                    logger.warning(f"[WARN] 数量公式计算失败: {e}")
        return base_value

    def _auto_brace_params(self, formula_str: str) -> str:
        """自动为公式中的参数添加大括号（如果缺少）"""
        if not formula_str:
            return formula_str

        result = []
        i = 0
        while i < len(formula_str):
            if formula_str[i] == '{':
                j = i + 1
                depth = 1
                while j < len(formula_str) and depth > 0:
                    if formula_str[j] == '{':
                        depth += 1
                    elif formula_str[j] == '}':
                        depth -= 1
                    j += 1
                result.append(formula_str[i:j])
                i = j
            elif '\u4e00' <= formula_str[i] <= '\u9fa5':
                j = i
                while j < len(formula_str) and '\u4e00' <= formula_str[j] <= '\u9fa5':
                    j += 1
                chinese_word = formula_str[i:j]
                if len(chinese_word) >= 2 and chinese_word not in ['直径', '长度', '宽度', '高度', '厚度', '密度', '数量']:
                    result.append(f'{{{chinese_word}}}')
                else:
                    result.append(chinese_word)
                i = j
            else:
                result.append(formula_str[i])
                i += 1

        return ''.join(result)

    def get_materials_by_category(self) -> dict:
        """按类别获取物料"""
        materials = self.calculate_material_types()

        result = {
            "material_params": [],
            "dimension_params": []
        }

        material_param_fields = {f["key"] for f in MATERIAL_FIELDS}

        for m in materials:
            if m["material_param"] in material_param_fields:
                result["material_params"].append(m)
            else:
                result["dimension_params"].append(m)

        return result

    @staticmethod
    def preview_calculation(product_type: str, order_params: dict) -> dict:
        """预览计算结果"""
        calculator = MaterialCalculator(order_params)
        calculator.product_type = product_type
        materials = calculator.calculate_material_types()

        return {
            "product_type": product_type,
            "materials": materials,
            "total_count": len(materials)
        }

    @staticmethod
    def get_available_spec_fields() -> list:
        """获取可选的规格字段列表（包括材质类型字段）"""
        spec_fields = [
            {
                "key": field["key"],
                "label": field["label"],
                "unit": field.get("unit", ""),
                "group": field.get("group", "")
            }
            for field in DIM_FIELDS
        ]
        for field in MATERIAL_FIELDS:
            spec_fields.append({
                "key": field["key"],
                "label": field["label"],
                "unit": "kg/m³",
                "group": "材质密度"
            })
        return spec_fields

    @staticmethod
    def get_available_qty_fields() -> list:
        """获取可选的数量计算字段列表"""
        qty_fields = [{"key": "quantity", "label": "订单数量", "unit": "米"}]

        for field in DIM_FIELDS:
            qty_fields.append({
                "key": field["key"],
                "label": field["label"],
                "unit": field.get("unit", "")
            })

        return qty_fields

    @staticmethod
    def get_material_params_for_product(product_type: str) -> list:
        """获取某产品类型支持的材质参数"""
        return [
            {
                "key": field["key"],
                "label": field["label"],
                "type": field.get("type", "dropdown"),
                "options": field.get("options", [])
            }
            for field in MATERIAL_FIELDS
        ]

    @staticmethod
    def format_material_display(material: dict) -> str:
        """格式化物料显示"""
        name = material.get("material_name", "")
        spec_value = material.get("spec_value")
        spec_unit = material.get("spec_unit", "")

        if spec_value:
            return f"{name}（{spec_value}{spec_unit}）"
        return name

    @staticmethod
    def validate_order_params(order_params: dict) -> tuple:
        """验证订单参数是否完整"""
        errors = []

        if not order_params.get("product_type"):
            errors.append("产品类型不能为空")

        if not order_params.get("quantity"):
            errors.append("数量不能为空")

        return len(errors) == 0, errors
