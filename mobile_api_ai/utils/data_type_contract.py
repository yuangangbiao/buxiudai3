# -*- coding: utf-8 -*-
"""
data_type 严格分类契约 v1.0
===========================

约定文档: docs/DATA_TYPE_CONTRACT.md

业务定义:
- 物理工序 = `process_names` 表里登记的工序(P01~P16 + M01 + Q01 + X01)
- 流程步骤 = 4 个流程模板的 step.name 并集(工单发布/排产制定/...)

核心 API:
- ``classify_pkg(pkg, process_names_set, flow_step_names_set) -> str``
    将一条 data_package 按新契约归类,返回 10 个新 data_type 枚举之一。
- ``classify_payloads(payloads, ...) -> dict[str, list]``
    批量归类,返回按新 data_type 索引的 dict(便于 API 渲染)。
- ``NEW_DATA_TYPES``: 严格枚举 frozenset。
- ``LEGACY_TO_NEW``: 旧值→新值 兼容映射(供迁移期使用)。

使用示例::

    from utils.data_type_contract import classify_payloads, NEW_DATA_TYPES

    # 加载时
    process_names_set = {row['process_name'] for row in fetch_all("SELECT process_name FROM process_names")}
    flow_step_names_set = {name for names in PROCESS_FLOW_TEMPLATES.values() for name in names['steps']}
    grouped = classify_payloads(payloads, process_names_set, flow_step_names_set)
    process_reports = grouped['process_report']
    flow_steps = grouped['flow_step']
"""
from __future__ import annotations

from typing import Dict, FrozenSet, Iterable, List, Set

# ────────────────────────────────────────────────────────────
# 0. SSOT 单一事实源 — 工序名集合与编号反查
#    来源: core._config_domain.PROCESS_CODES (P01~P16 + M01 + Q01 + X01 + P_CS)
#    修 R10/R11: 撤掉 process_code_registry.py,统一从 core 读
# ────────────────────────────────────────────────────────────
try:
    from core._config_domain import (  # noqa: E402  允许函数定义后导入
        PROCESS_CODES as _CORE_PROCESS_CODES,
        get_all_process_codes as _core_get_all_process_codes,
    )
except Exception:  # 兜底: core 不可用时使用空 dict,避免循环导入
    _CORE_PROCESS_CODES = {}
    _core_get_all_process_codes = lambda: {}


def get_process_names_set() -> Set[str]:
    """SSOT: 返回全量已注册工序名集合 (P01~P16 + M01 + Q01 + X01 + P_CS + 自定义)

    单一来源: ``core._config_domain.PROCESS_CODES ∪ _custom_process_codes``
    通过 ``get_all_process_codes()`` 统一读取,后端任何模块应仅调用本函数
    而非自行读 DB / 缓存,以保证分类口径一致。
    """
    try:
        return set(_core_get_all_process_codes().keys())
    except Exception:
        return set(_CORE_PROCESS_CODES.keys())


def get_process_code_to_name() -> Dict[str, str]:
    """SSOT: 返回 process_code → process_name 反查字典

    示例: ``{"P01": "原材料准备", "P15": "质量检验", "M01": "备料", "P_CS": "测试"}``
    """
    return {v: k for k, v in _core_get_all_process_codes().items()}


# ────────────────────────────────────────────────────────────
# 1. 新契约严格枚举(10 类)
# ────────────────────────────────────────────────────────────
NEW_DATA_TYPES: FrozenSet[str] = frozenset({
    "process_report",     # 工序报工
    "flow_step",          # 流程步骤占位
    "flow_production",    # 排产发布
    "material_request",   # 物料申请
    "material_pickup",    # 领料/出库
    "material_buy",       # 物料采购
    "quality_task",       # 质检任务
    "equipment_repair",   # 设备报修
    "outsource_task",     # 外协任务
    "approval",           # 审批任务(RE-006 新增)
    "config",             # 系统配置(字典/模板)
})

# 卡片分组:6 张任务卡片对应的 data_type 集合
CARD_GROUPS: Dict[str, FrozenSet[str]] = {
    "process_tasks":   frozenset({"process_report"}),
    "flow_steps":      frozenset({"flow_step", "flow_production"}),
    "material_tasks":  frozenset({"material_request", "material_pickup", "material_buy"}),
    "quality_tasks":   frozenset({"quality_task"}),
    "repair_tasks":    frozenset({"equipment_repair"}),
    "outsource_tasks": frozenset({"outsource_task"}),
    # approval 不入业务卡片(归类"其他"),由专门审批流处理
}

# ────────────────────────────────────────────────────────────
# 2. 旧 → 新 兼容映射(迁移期内使用,1~2 版本后废弃)
# ────────────────────────────────────────────────────────────
LEGACY_TO_NEW: Dict[str, str] = {
    "report":             "__dynamic__",   # 动态判定,见 _classify_legacy_report
    "process_task":       "process_report",  # v5 storage 写入用
    "process_report":     "process_report",  # 已是新值
    "material":           "material_pickup",
    "material_purchase":  "material_request",
    "purchase":           "material_buy",
    "quality":            "quality_task",
    "quality_inspection": "quality_task",
    "repair":             "equipment_repair",
    "outsource":          "outsource_task",
    "approval":           "approval",
    "production":         "flow_production",
    "config":             "config",
    "":                   "config",
}


# ────────────────────────────────────────────────────────────
# 3. 核心判定函数
# ────────────────────────────────────────────────────────────
def _parse_content(pkg: dict) -> dict:
    """安全解析 content 字段(json string 或 dict)"""
    c = pkg.get("content")
    if c is None:
        return {}
    if isinstance(c, dict):
        return c
    if isinstance(c, str) and c.strip():
        try:
            import json as _j
            return _j.loads(c)
        except Exception:
            return {}
    return {}


def _classify_legacy_report(
    pkg: dict,
    process_names_set: Set[str],
    flow_step_names_set: Set[str],
) -> str:
    """旧 data_type='report' 拆分为物理工序 / 流程步骤 / 其他(基于 content 兜底)

    判定优先级(从高到低) — RE-007 调整(流程优先):
    0. related_process ∈ 流程步骤集合                 → flow_step    (RE-007: 提前到质检前,异常 #9)
    1. content.flow_type == 'production'              → flow_production
    2. related_process 以"质检-"开头 (或 content 含 inspection_type) → quality_task
    3. related_process 含"备料-"或"304不锈钢"等物料关键词 + quantity > 0 → material_request
    4. related_process ∈ process_names                → process_report
    5. 其他                                            → __contract_violation__
    """
    rp = (pkg.get("related_process") or "").strip()
    content = _parse_content(pkg)

    # 0. RE-007 流程步骤白名单优先(异常 #9: 质检审核不应被分到 quality_task)
    if rp in flow_step_names_set:
        return "flow_step"

    # 1. content.flow_type 强信号
    flow_type = (content.get("flow_type") or "").strip()
    if flow_type == "production":
        return "flow_production"

    # 2. 质检信号
    if rp.startswith("质检-") or content.get("inspection_type") or content.get("inspection_items"):
        return "quality_task"

    # 3. 物料信号: 物料名特征 + quantity 字段
    qty = content.get("quantity")
    try:
        qty_num = float(qty) if qty is not None else 0
    except (TypeError, ValueError):
        qty_num = 0
    material_kw = ("备料-", "物料")
    if (any(rp.startswith(k) for k in material_kw) or "不锈钢" in rp) and qty_num > 0:
        return "material_request"

    # 4. 物理工序白名单
    if rp in process_names_set:
        return "process_report"

    return "__contract_violation__"


def classify_pkg(
    pkg: dict,
    process_names_set: Set[str],
    flow_step_names_set: Set[str],
) -> str:
    """
    将一条 data_package 按新契约归类,返回新 data_type。

    Parameters
    ----------
    pkg : dict
        必须包含 ``data_type`` 和 ``related_process`` 字段,可选 ``content.process_code`` 字段。
    process_names_set : set[str]
        ``process_names.process_name`` 全集(SSOT: core.PROCESS_CODES keys)。
    flow_step_names_set : set[str]
        4 个流程模板的 step.name 并集。

    Returns
    -------
    str
        新 data_type 枚举值之一;不可识别时返回 ``"__contract_violation__"``。

    R12 分类优先级(从高到低):
      0. process_code 字段前缀精确判          → 对应卡片            (R12 SSOT 优先 — "质量检验" 既是 P15 工序也是流程步骤名,按 code 归类)
      1. related_process ∈ 流程步骤白名单    → flow_step           (RE-008, 无 process_code 时兜底)
      2. data_type 已是新契约值               → 直通
      3. 旧 data_type 兼容映射               → 静态映射 / dynamic 走 _classify_legacy_report
      4. 均不命中                            → __contract_violation__
    """
    if not isinstance(pkg, dict):
        return "__contract_violation__"
    dt = (pkg.get("data_type") or "").strip()
    rp = (pkg.get("related_process") or "").strip()

    # R12: process_code 优先分支 — P01~P16 / P_CS / M01 / Q01 / X01 严格分开
    # P15 质量检验 是工序报工(不归 quality_task), Q01 才是质检任务, 互不重叠
    # 例: "质量检验" 既是 P15 工序也是 6-step 流程步骤名, SSOT 主键 process_code 必须先判
    pc = (pkg.get("process_code") or "").strip().upper()
    if pc:
        pc_to_type = _PROCESS_CODE_TO_TYPE.get(pc)
        if pc_to_type:
            return pc_to_type

    # RE-008 兜底: 流程步骤白名单(无 process_code 时按 related_process 判定)
    # 异常 #9: "质检审核" 不应被强归 quality_task
    if rp and rp in flow_step_names_set:
        return "flow_step"

    # 已是新契约值,直接返回
    if dt in NEW_DATA_TYPES:
        return dt

    # 旧值兼容
    if dt in LEGACY_TO_NEW:
        target = LEGACY_TO_NEW[dt]
        if target == "__dynamic__":
            return _classify_legacy_report(pkg, process_names_set, flow_step_names_set)
        return target

    return "__contract_violation__"


# R12: process_code → data_type SSOT 映射表
# 原则: P01~P16 + P_CS → process_report (物理工序报工)
#       M01  → material_request (物料申请/备料)
#       Q01  → quality_task (质检任务,独立于 P15 质量检验)
#       X01  → outsource_task (外协任务)
# 动态 P17+ 代码(P + 数字)默认走 process_report,例外可在此表添加
def _build_process_code_type_map() -> Dict[str, str]:
    """构建 process_code → data_type 映射(从 core._config_domain 自动推导)"""
    mapping: Dict[str, str] = {}
    try:
        from core._config_domain import PROCESS_CODES  # 运行时 SSOT
        for _name, code in PROCESS_CODES.items():
            cu = (code or '').upper()
            if not cu:
                continue
            if cu.startswith('P'):  # P01~P16 + P17... + P_CS
                mapping[cu] = 'process_report'
            elif cu.startswith('M'):
                mapping[cu] = 'material_request'
            elif cu.startswith('Q'):
                mapping[cu] = 'quality_task'
            elif cu.startswith('X'):
                mapping[cu] = 'outsource_task'
    except Exception:
        pass
    return mapping


_PROCESS_CODE_TO_TYPE: Dict[str, str] = _build_process_code_type_map()


def classify_payloads(
    payloads: Iterable[dict],
    process_names_set: Set[str],
    flow_step_names_set: Set[str],
) -> Dict[str, List[dict]]:
    """
    批量归类,返回 ``{new_data_type: [pkg, ...]}`` 字典。

    未识别的 pkg 归到 ``"__contract_violation__"`` 键,方便审计。
    """
    out: Dict[str, List[dict]] = {dt: [] for dt in NEW_DATA_TYPES}
    out["__contract_violation__"] = []
    for pkg in payloads:
        if not isinstance(pkg, dict):
            continue
        cat = classify_pkg(pkg, process_names_set, flow_step_names_set)
        out[cat].append(pkg)
    return out


def group_by_card(
    payloads: Iterable[dict],
    process_names_set: Set[str],
    flow_step_names_set: Set[str],
) -> Dict[str, List[dict]]:
    """
    按 6 张任务卡片分组,直接给前端用::

        {
            "process_tasks":  [...],  # 工序报工
            "flow_steps":     [...],  # 流程步骤
            "material_tasks": [...],  # 物料
            "quality_tasks":  [...],  # 质检
            "repair_tasks":   [...],  # 维修
            "outsource_tasks": [...], # 外协
        }
    """
    classified = classify_payloads(payloads, process_names_set, flow_step_names_set)
    out = {card: [] for card in CARD_GROUPS}
    for card_name, dt_set in CARD_GROUPS.items():
        for dt in dt_set:
            out[card_name].extend(classified.get(dt, []))
    return out


# ────────────────────────────────────────────────────────────
# 4. 流程模板常量(供运行时和测试使用)
# ────────────────────────────────────────────────────────────
PROCESS_FLOW_TEMPLATES: Dict[str, Dict] = {
    "material_purchase": {
        "steps": ["物料申请", "任务确认", "回复采购期限", "入库通知", "物料出库"],
        "type": "purchase",
    },
    "production_6step": {
        "steps": ["工单发布", "排产制定", "生产执行", "报工完成", "质量检验", "完工入库"],
        "type": "production",
    },
    "production_7step": {
        "steps": ["工单发布", "排产制定", "排产确认", "生产执行", "报工完成", "质检审核", "完工入库"],
        "type": "production",
    },
    "production_8step": {
        "steps": ["工单发布", "排产制定", "排产确认", "生产执行", "质检审核", "报工完成", "完工入库", "发货"],
        "type": "production",
    },
}


def get_flow_step_names_set() -> Set[str]:
    """返回 4 个流程模板 step.name 并集"""
    s: Set[str] = set()
    for tpl in PROCESS_FLOW_TEMPLATES.values():
        s.update(tpl["steps"])
    return s
