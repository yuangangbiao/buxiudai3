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
        必须包含 ``data_type`` 和 ``related_process`` 字段,可选 ``content`` 字段。
    process_names_set : set[str]
        ``process_names.process_name`` 全集。
    flow_step_names_set : set[str]
        4 个流程模板的 step.name 并集。

    Returns
    -------
    str
        新 data_type 枚举值之一;不可识别时返回 ``"__contract_violation__"``。
    """
    if not isinstance(pkg, dict):
        return "__contract_violation__"
    dt = (pkg.get("data_type") or "").strip()
    rp = (pkg.get("related_process") or "").strip()

    # RE-008 修复: 流程步骤白名单永远最优先(异常 #9 — "质检审核" 不应被强归类)
    # 即便 data_type='quality'/'report'/... 只要 related_process 是流程步骤, 必须归 flow_step
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
