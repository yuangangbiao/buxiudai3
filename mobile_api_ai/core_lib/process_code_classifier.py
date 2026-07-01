# -*- coding: utf-8 -*-
"""
process_code 分类器

根据 process_code 的命名规则自动推断 product_type 和 flow_type。

[方案A 2026-06-15] 命名规则自动推断
- M 开头 → material_purchase（物料）
- Q 开头 → quality（质检）
- STOCK_IN / 包含 STOCK → warehousing（入库）
- P 开头 → production（生产）
- 含 OUTSOURCE / WX / OS → outsource（外协）[T2 2026-06-16]
- 其他（DBG/N/A/PX） → None（忽略/测试）
"""
import logging
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


# ── 已知映射（特殊处理，覆盖命名规则）──
# [方案A 2026-06-15] 命名规则 + 已知映射
# - P 编号都是工序进度，全部归 production（flow_type 和 product_type）
# - 只有 M/Q/STOCK_IN 等非 P 编号才走特殊归类
KNOWN_CODE_MAPPING = {
    # flow_type - 空（所有 P 走命名规则自动归 production）
    'flow_type': {
    },
    # product_type - 空（所有 P 走命名规则自动归 不锈钢网带）
    'product_type': {
    },
}


# ── 外协代码判断辅助函数 ─────────────────────────────────────────
# [T2 2026-06-16] OUTSOURCE/WX/OS 系列外协代码，大小写不敏感
def _is_outsource_code_str(code):
    """判断是否为外协类 process_code（大小写不敏感）"""
    if not code:
        return False
    code_upper = code.upper().strip()
    if code_upper.startswith('OUTSOURCE') or code_upper.startswith('WX') or code_upper.startswith('OS-'):
        return True
    if 'OUTSOURCE' in code_upper or '外协' in code:
        return True
    return False


# ── 命名规则 ──
# [2026-06-15 修正] M 编号 = 物料，P 编号 = 工序进度
# - M 开头 → 物料（material_purchase）
# - P 开头 → 工序进度（production，含 P01/P11/P15/P16）
# - Q 开头 → 质检委托（独立流程）
# - STOCK_IN / IN → 入库（独立流程）
# - PX*/N/A/DBG → 忽略
PROCESS_CODE_RULES = {
    # product_type 推断规则（按优先级匹配，命中即返回）
    # [T2 2026-06-16] 全部大小写不敏感 + 加 OUTSOURCE/WX/OS 外协
    'product_type': [
        # (匹配函数, 返回的 product_type)
        (lambda c: c and c.upper().startswith('M'), '物料'),  # M 开头 → 物料
        (lambda c: c and c.upper().startswith('Q'), '质检委托'),
        (lambda c: c and ('STOCK' in c.upper() or c.upper() == 'IN'), '不锈钢网带'),
        (lambda c: c and c.upper().startswith('P'), '不锈钢网带'),
        # [T2 2026-06-16] 外协代码 OUTSOURCE/WX/OS
        (lambda c: c and _is_outsource_code_str(c), '外协加工'),
    ],
    # flow_type 推断规则
    'flow_type': [
        (lambda c: c and c.upper().startswith('M'), 'material_purchase'),  # M 开头 → 物料流程
        (lambda c: c and c.upper().startswith('Q'), 'quality'),
        (lambda c: c and ('STOCK' in c.upper() or c.upper() == 'IN'), 'warehousing'),
        (lambda c: c and c.upper().startswith('P'), 'production'),
        # [T2 2026-06-16] 外协 flow_type
        (lambda c: c and _is_outsource_code_str(c), 'outsource'),
    ],
    # 忽略规则（测试/调试）
    'ignore': [
        lambda c: not c,  # 空
        lambda c: c and c.upper() in ('N/A', 'DBG', 'DEBUG', 'NULL', 'NONE'),
        lambda c: c and c.upper().startswith('PX'),  # 临时测试
        lambda c: c and c.upper().startswith('TEST'),
    ],
}


def is_ignored_code(code: str) -> bool:
    """判断是否为测试/调试 code"""
    if code is None:
        return True
    code_str = str(code).strip()
    if not code_str or code_str == 'None':
        return True
    for rule in PROCESS_CODE_RULES['ignore']:
        try:
            if rule(code_str):
                return True
        except Exception:
            pass
    return False


def infer_product_type_from_code(code: str) -> Optional[str]:
    """根据单个 process_code 推断 product_type

    优先级: 已知映射 > 命名规则
    """
    if is_ignored_code(code):
        return None
    code_str = str(code).strip()
    # 1. 优先查已知映射
    if code_str in KNOWN_CODE_MAPPING['product_type']:
        return KNOWN_CODE_MAPPING['product_type'][code_str]
    # 2. 命名规则推断
    for matcher, result in PROCESS_CODE_RULES['product_type']:
        try:
            if matcher(code_str):
                return result
        except Exception:
            pass
    return None


def infer_flow_type_from_code(code: str) -> Optional[str]:
    """根据单个 process_code 推断 flow_type

    优先级: 已知映射 > 命名规则
    """
    if is_ignored_code(code):
        return None
    code_str = str(code).strip()
    # 1. 优先查已知映射
    if code_str in KNOWN_CODE_MAPPING['flow_type']:
        return KNOWN_CODE_MAPPING['flow_type'][code_str]
    # 2. 命名规则推断
    for matcher, result in PROCESS_CODE_RULES['flow_type']:
        try:
            if matcher(code_str):
                return result
        except Exception:
            pass
    return None


def classify_process_codes(codes: List[str]) -> Dict[str, str]:
    """
    聚合多个 process_code 推断工单的 product_type 和 flow_type

    优先级：
    1. material_purchase（物料）
    2. quality（质检）
    3. warehousing（入库）
    4. production（生产）

    Args:
        codes: process_code 列表

    Returns:
        {'product_type': '...', 'flow_type': '...'}
        全部为空时返回 {'product_type': '不锈钢网带', 'flow_type': 'production'}（默认生产）
    """
    priority_order = [
        ('material_purchase', '物料'),
        ('quality', '质检委托'),
        ('warehousing', '不锈钢网带'),
        ('production', '不锈钢网带'),
    ]

    flow_type_counts = {}
    product_type_counts = {}

    for code in codes:
        ft = infer_flow_type_from_code(code)
        pt = infer_product_type_from_code(code)
        if ft:
            flow_type_counts[ft] = flow_type_counts.get(ft, 0) + 1
        if pt:
            product_type_counts[pt] = product_type_counts.get(pt, 0) + 1

    # 按优先级选择第一个有匹配的
    result_flow = None
    result_product = None
    for ft, pt in priority_order:
        if ft in flow_type_counts and result_flow is None:
            result_flow = ft
        if pt in product_type_counts and result_product is None:
            result_product = pt
        if result_flow and result_product:
            break

    # 默认值
    if not result_flow:
        result_flow = 'production'
        logger.debug(f'[classify] 无匹配 process_code, 默认 flow_type=production (codes={codes})')
    if not result_product:
        result_product = '不锈钢网带'
        logger.debug(f'[classify] 无匹配 process_code, 默认 product_type=不锈钢网带 (codes={codes})')

    return {
        'flow_type': result_flow,
        'product_type': result_product,
    }


def is_production_code(code: str) -> bool:
    """判断是否生产类 process_code（用于工序任务 API 过滤）"""
    return infer_flow_type_from_code(code) == 'production'


def is_material_code(code: str) -> bool:
    """判断是否物料类"""
    return infer_flow_type_from_code(code) == 'material_purchase'


def is_quality_code(code: str) -> bool:
    """判断是否质检类"""
    return infer_flow_type_from_code(code) == 'quality'


def is_warehousing_code(code: str) -> bool:
    """判断是否入库类"""
    return infer_flow_type_from_code(code) == 'warehousing'


def is_outsource_code(code: str) -> bool:
    """[T2 2026-06-16] 判断是否外协类 process_code"""
    if is_ignored_code(code):
        return False
    return _is_outsource_code_str(str(code).strip())


# ── 统一排序函数 ────────────────────────────────────────────────

def _letter_to_value(letter: str) -> int:
    """字母转数值：A=1, B=2, Z=26, AA=27..."""
    value = 0
    for i, c in enumerate(reversed(letter.upper())):
        value += (ord(c) - ord('A') + 1) * (26 ** i)
    return value


def _value_to_letter(value: int) -> str:
    """数值转字母：1=A, 2=B, 26=Z, 27=AA..."""
    if value <= 26:
        return chr(ord('A') + value - 1)
    result = ""
    v = value - 1
    while v >= 0:
        result = chr(ord('A') + v % 26) + result
        v = v // 26 - 1
    return result


def process_code_sort_key(code: str) -> tuple:
    """
    统一 process_code 排序键
    支持格式:
      P01, P02, P03         - 基准工序
      P03-B, P03-C, P03-D   - 自定义工序（首次插入从B开始）
      P03-A1, P03-A2        - 特殊位置插入（在B之前）

    排序规则:
      1. 前缀优先级 (P=1, M=2, Q=3, STOCK=4, 其他=5)
      2. 主数字
      3. 子字母（A=1, B=2... Z=26, AA=27）
      4. 子数字

    返回: (prefix_priority, num, sub_letter_value, sub_num)
    """
    import re
    code = (code or '').upper().strip()

    # 前缀优先级
    PREFIX_PRIORITY = {'P': 1, 'M': 2, 'Q': 3, 'STOCK': 4}
    prefix_priority = PREFIX_PRIORITY.get(code[:1], 5) if not code.startswith('STOCK') else 4

    # 匹配 P03 或 P03-B 或 P03-A1
    # (?:-([A-Z]+)(\d*))? 匹配 -A 或 -A1 或 -AB 等
    m = re.match(r'^([A-Z]+)(\d+)(?:-([A-Z]+)(\d*))?$', code)
    if m:
        prefix = m.group(1)
        num = int(m.group(2))
        sub_letter = m.group(3) or ''
        sub_num = int(m.group(4)) if m.group(4) else 0

        # 获取前缀优先级
        p_priority = PREFIX_PRIORITY.get(prefix, 5)

        # 多字母转数值
        sub_letter_value = _letter_to_value(sub_letter) if sub_letter else 0

        # A1 特殊处理：让 A1 排在 B 之前
        # P03-A1 → (1, 3, 1, 1) → 排序时 < P03-B → (1, 3, 2, 0)
        if sub_letter == 'A' and sub_num > 0:
            # A1, A2... 排在 B 之前
            return (p_priority, num, 1, sub_num)
        elif sub_letter == 'A' and sub_num == 0:
            # 单独的 P03-A（不推荐使用）
            return (p_priority, num, 1, 0)
        else:
            return (p_priority, num, sub_letter_value, sub_num)

    # STOCK_IN 等特殊格式
    if 'STOCK' in code or code == 'IN':
        return (4, 0, 0, 0)

    return (5, 0, 0, 0)  # 无法识别的排最后
