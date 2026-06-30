# -*- coding: utf-8 -*-
"""
全字典中文化(API 显示层) v1.0
=============================

约定文档: docs/I18N_ZH.md

业务定义:
- API 返回的枚举值(英文代码) 在此统一翻译为中文,供前端直接显示。
- 不改数据库(规范化存储仍是英文),不改前端(改一处胜改多处)。
- 翻译遵循"显示友好、贴近业务口语"原则。

核心 API:
- ``STATUS_ZH``           : status 字典(pending→待开始 / in_progress→进行中 / ...)
- ``DATA_TYPE_ZH``        : data_type 字典(10 个新枚举 → 中文)
- ``PRIORITY_ZH``         : priority 字典
- ``STEP_STATUS_ZH``      : 流程步骤状态字典
- ``translate(value, kind)``  : 单值翻译
- ``translate_payload(obj)`` : 递归翻译 dict/list

使用示例::

    from utils.i18n_zh import translate, translate_payload, STATUS_ZH

    # 翻译单值
    print(translate('in_progress', 'status'))  # '进行中'

    # 递归翻译 API payload
    payload = {'status': 'pending', 'data_type': 'process_report'}
    translate_payload(payload)
    print(payload['status'])    # '待开始'
    print(payload['data_type']) # '工序报工'

约定: 同时保留原值于 ``*_code`` 字段(如 status_code),便于前端按需切换语言。
"""
from __future__ import annotations

from typing import Any, Dict, List, Set

# ────────────────────────────────────────────────────────────
# 1. status 字典(任务/工单通用)
# ────────────────────────────────────────────────────────────
STATUS_ZH: Dict[str, str] = {
    "pending":        "待开始",
    "distributed":    "已派单",
    "dispatched":     "已派单",
    "in_progress":    "进行中",
    "in_production":  "生产中",
    "in_produce":     "生产中",
    "paused":         "已暂停",
    "cancelled":      "已取消",
    "canceled":       "已取消",
    "completed":      "已完成",
    "done":           "已完成",
    "overdue":        "已逾期",
    "reported":       "已报工",
    "qc_passed":      "质检通过",
    "qc_failed":      "质检不通过",
    "failed":         "失败",
    "active":         "进行中",
    "published":      "已发布",
    "scheduled":      "已排产",
    "confirmed":      "已确认",
    "warehoused":     "已入库",
    "approved":       "已审核",
    "rejected":       "已驳回",
    "draft":          "草稿",
    # 物料状态
    "material_confirmed":  "物料已确认",
    "material_picking":    "领料中",
    "material_picked":     "已领料",
    "material_requested":  "已申请",
    "material_arrived":    "已到货",
    "material_shortage":   "物料不足",
    # 质检
    "inspection_pass":  "检验通过",
    "inspection_fail":  "检验不通过",
    "inspection_pending": "待检验",
    "first_inspection":   "首检",
    "final_inspection":   "终检",
    # 维修
    "repair_pending":   "待维修",
    "repair_in_progress": "维修中",
    "repair_done":      "维修完成",
    "repair_reopened":  "返修",
    # 外协
    "outsource_pending":  "待外协",
    "outsource_sent":     "已发外协",
    "outsource_received": "外协回厂",
    # 中文值防双重翻译
    "已发布":          "已发布",
    "已排产":          "已排产",
    "已确认":          "已确认",
    "生产中":          "生产中",
    "质检中":          "质检中",
    "质检通过":        "质检通过",
    "已完成":          "已完成",
    "已入库":          "已入库",
    "已完工":          "已完成",
    "生产完成":        "已完成",
    "已派单":          "已派单",
    "待开始":          "待开始",
    "进行中":          "进行中",
    "已暂停":          "已暂停",
    "已取消":          "已取消",
    "已驳回":          "已驳回",
    "草稿":            "草稿",
    "物料已确认":      "物料已确认",
    "已申请":          "已申请",
    "已到货":          "已到货",
    "待检验":          "待检验",
    "首检":            "首检",
    "终检":            "终检",
    "待维修":          "待维修",
    "维修中":          "维修中",
    "维修完成":        "维修完成",
    "待外协":          "待外协",
    "已发外协":        "已发外协",
    "外协回厂":        "外协回厂",
}

# ────────────────────────────────────────────────────────────
# 2. data_type 字典(契约 v1.0 的 10+1 个枚举)
# ────────────────────────────────────────────────────────────
DATA_TYPE_ZH: Dict[str, str] = {
    "process_report":     "工序报工",
    "flow_step":          "流程步骤",
    "flow_production":    "排产发布",
    "material_request":   "物料申请",
    "material_pickup":    "物料领取",
    "material_buy":       "物料采购",
    "quality_task":       "质检任务",
    "equipment_repair":   "设备报修",
    "outsource_task":     "外协任务",
    "approval":           "审批任务",
    "config":             "系统配置",
    # 兼容旧枚举
    "report":             "工序报工",
    "process_task":       "工序报工",
    "material":           "物料领取",
    "material_purchase":  "物料申请",
    "purchase":           "物料采购",
    "quality":            "质检任务",
    "quality_inspection": "质检任务",
    "repair":             "设备报修",
    "outsource":          "外协任务",
    "production":         "排产发布",
}

# ────────────────────────────────────────────────────────────
# 3. priority 字典
# ────────────────────────────────────────────────────────────
PRIORITY_ZH: Dict[str, str] = {
    "urgent":   "紧急",
    "high":     "高",
    "normal":   "普通",
    "low":      "低",
    "rush":     "加急",
    "常规":      "普通",
    "紧急":      "紧急",
    "加急":      "加急",
    "高":        "高",
    "低":        "低",
}

# ────────────────────────────────────────────────────────────
# 4. 流程步骤 status_key 字典(5 个流程模板的 step key)
# ────────────────────────────────────────────────────────────
STEP_STATUS_ZH: Dict[str, str] = {
    "tmpl_publish":            "工单发布",
    "tmpl_schedule":           "排产制定",
    "tmpl_dispatch":           "任务派发",
    "tmpl_production_start":   "生产开始",
    "tmpl_production_complete": "生产完成",
    "tmpl_qc_start":           "质检开始",
    "tmpl_qc_pass":            "质检通过",
    "tmpl_warehouse":          "完工入库",
    "repair_start":            "维修开始",
    "repair_in_progress":      "维修执行",
    "repair_done":             "维修完成",
    "delivery":                "发货",
    "completed":               "已完成",
}

# ────────────────────────────────────────────────────────────
# 5. 订单状态字典(orders.status)
# ────────────────────────────────────────────────────────────
ORDER_STATUS_ZH: Dict[str, str] = {
    "draft":            "草稿",
    "pending":          "待开始",
    "scheduled":        "已排产",
    "in_production":    "生产中",
    "completed":        "已完成",
    "cancelled":        "已取消",
    "warehoused":       "已入库",
    # 已有中文值
    "已排产":            "已排产",
    "生产中":            "生产中",
    "已完成":            "已完成",
    "已入库":            "已入库",
    "已完工":            "已完成",
    "生产完成":          "已完成",
    "草稿":              "草稿",
    "待开始":            "待开始",
    "已取消":            "已取消",
}

# ────────────────────────────────────────────────────────────
# 6. 翻译函数
# ────────────────────────────────────────────────────────────

_DICTS = {
    "status":      STATUS_ZH,
    "data_type":   DATA_TYPE_ZH,
    "priority":    PRIORITY_ZH,
    "step_status": STEP_STATUS_ZH,
    "order_status": ORDER_STATUS_ZH,
}


def translate(value: Any, kind: str) -> str:
    """单值翻译: 找不到映射时返回原值"""
    if value is None or value == "":
        return value
    table = _DICTS.get(kind, {})
    s = str(value).strip()
    if s in table:
        return table[s]
    return s  # 找不到就原样返回(不再 snake_to_zh)


# 递归扫描时需要识别的字段名
_STATUS_FIELDS: Set[str] = {"status", "current_status", "next_status", "operate_status"}
_STEP_STATUS_FIELDS: Set[str] = {"status_key", "step_status"}
_DATATYPE_FIELDS: Set[str] = {"data_type", "type", "category"}
_PRIORITY_FIELDS: Set[str] = {"priority", "level", "urgency"}


def translate_payload(obj: Any, *, save_code: bool = True) -> Any:
    """递归翻译 dict/list 中的枚举字段。

    约定:
    - 命中字典时: 把原值写入 ``<field>_code``(供 JS 回切),然后覆盖 ``<field>``。
    - 不识别的字段 / 不在字典的值,保持原样不动。
    """
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            if isinstance(v, (dict, list)):
                translate_payload(v, save_code=save_code)
                continue
            if not isinstance(v, (str, int)) or v == "":
                continue
            if k in _STATUS_FIELDS:
                zh = translate(v, "status")
                if save_code and str(v) != zh:
                    obj[f"{k}_code"] = v
                obj[k] = zh
            elif k in _STEP_STATUS_FIELDS:
                zh = translate(v, "step_status")
                if save_code and str(v) != zh:
                    obj[f"{k}_code"] = v
                obj[k] = zh
            elif k in _DATATYPE_FIELDS:
                zh = translate(v, "data_type")
                if save_code and str(v) != zh:
                    obj[f"{k}_code"] = v
                obj[k] = zh
            elif k in _PRIORITY_FIELDS:
                zh = translate(v, "priority")
                if save_code and str(v) != zh:
                    obj[f"{k}_code"] = v
                obj[k] = zh
        return obj
    if isinstance(obj, list):
        for item in obj:
            translate_payload(item, save_code=save_code)
        return obj
    return obj


# ────────────────────────────────────────────────────────────
# 7. 单元测试入口
# ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # 简单冒烟测试
    assert translate("pending", "status") == "待开始"
    assert translate("in_progress", "status") == "进行中"
    assert translate("completed", "status") == "已完成"
    assert translate("process_report", "data_type") == "工序报工"
    assert translate("quality_task", "data_type") == "质检任务"
    assert translate("urgent", "priority") == "紧急"
    assert translate("unknown_xxx", "status") == "unknown_xxx"  # 找不到原样返回

    # 递归翻译
    sample = {
        "order_no": "ORD-001",
        "status": "in_progress",
        "data_type": "process_report",
        "priority": "high",
        "tasks": [
            {"id": "1", "status": "completed"},
            {"id": "2", "status": "pending"},
        ],
    }
    translate_payload(sample)
    print("\n[冒烟测试] 翻译后:")
    import json
    print(json.dumps(sample, ensure_ascii=False, indent=2))
    assert sample["status"] == "进行中"
    assert sample["status_code"] == "in_progress"
    assert sample["data_type"] == "工序报工"
    assert sample["tasks"][0]["status"] == "已完成"
    print("\n[✓] 全部通过")
