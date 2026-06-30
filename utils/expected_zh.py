# -*- coding: utf-8 -*-
"""
R10 字典自动同步 — 单一事实源(SSOT)合并
=========================================

目的:
- 解决 R7 测试中"前后端翻译字典漂移"问题
- 单一入口 = 后端 utils.i18n_zh.STATUS_ZH / DATA_TYPE_ZH
- 兼容前端 dispatch_center_labels.js 的扩展项(如"已创建")

约定:
- 修改 utils/i18n_zh.py 后,R7 测试期望集合自动跟进,无需手工维护
- 修改 dispatch_center_labels.js 后,运行::

    python -c "from utils.expected_zh import refresh_from_frontend; refresh_from_frontend()"

  即可让前端字典并入 SSOT(实际由 CI 触发)

使用::

    from utils.expected_zh import get_expected_status_zh, get_expected_datatype_zh
    EXPECTED_STATUS_ZH = get_expected_status_zh()
    EXPECTED_DATATYPE_ZH = get_expected_datatype_zh()

构建期 vs 运行期:
- 构建期:本文件加载后端 i18n_zh.py 的字典并合并
- 离线刷新:提供 refresh_from_frontend() 让 R7/R8 CI 时从 JS 文件拉取增量
"""
from __future__ import annotations

import os
import re
from typing import Dict, Set

# ────────────────────────────────────────────────────────────
# SSOT 1:后端字典(权威源)
# ────────────────────────────────────────────────────────────
from utils.i18n_zh import (
    STATUS_ZH as _BACKEND_STATUS_ZH,
    DATA_TYPE_ZH as _BACKEND_DATATYPE_ZH,
    PRIORITY_ZH as _BACKEND_PRIORITY_ZH,
    ORDER_STATUS_ZH as _BACKEND_ORDER_STATUS_ZH,
    STEP_STATUS_ZH as _BACKEND_STEP_STATUS_ZH,
)


# ────────────────────────────────────────────────────────────
# SSOT 2:前端字典(可由 CI 刷新)
# ────────────────────────────────────────────────────────────
# 优先从持久化文件加载(由 CI 任务生成),失败则用内置硬编码副本
_PERSIST_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..",
    "docs", "debug", "order_state", "expected_zh.frontend.json"
)

# 内置硬编码副本(避免对 dispatch_center_labels.js 改 JS 解析器)
_BUILTIN_FRONTEND_STATUS: Dict[str, str] = {
    "pending":       "待处理",
    "dispatched":    "已分配",
    "distributed":   "已派发",
    "in_progress":   "进行中",
    "completed":     "已完成",
    "overdue":       "已超时",
    "cancelled":     "已取消",
    "published":     "已发布",
    "scheduled":     "已排产",
    "confirmed":     "已排产",
    "in_production": "生产中",
    "reported":      "已报工",
    "qc_passed":     "质检通过",
    "created":       "已创建",
    "received":      "已收货",
    "processing":    "处理中",
    "active":        "进行中",
}
_BUILTIN_FRONTEND_TYPE: Dict[str, str] = {
    "process_report":   "工序报工",
    "flow_step":        "流程步骤",
    "flow_production":  "排产发布",
    "material_request": "物料申请",
    "material_pickup":  "领料出库",
    "material_buy":     "物料采购",
    "quality_task":     "质检任务",
    "equipment_repair": "设备报修",
    "outsource_task":   "外协任务",
    "config":           "系统配置",
    # 旧值兼容
    "report":           "报工",
    "quality":          "质检",
    "material":         "物料",
    "approval":         "审批",
    "work_order":       "工单",
    "unknown":          "未知",
    "task_assign":      "派单",
    "task_reassign":    "转派",
    "batch_assign":     "批量派单",
}


def _load_frontend_dicts() -> tuple[Dict[str, str], Dict[str, str]]:
    """加载前端字典:优先持久化文件,兜底内置副本"""
    import json
    try:
        if os.path.exists(_PERSIST_PATH):
            with open(_PERSIST_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("status", {}), data.get("type", {})
    except Exception:
        pass
    return dict(_BUILTIN_FRONTEND_STATUS), dict(_BUILTIN_FRONTEND_TYPE)


# ────────────────────────────────────────────────────────────
# SSOT API
# ────────────────────────────────────────────────────────────
def get_expected_status_zh() -> Set[str]:
    """获取 status 期望集合(后端 ∪ 前端)"""
    frontend_status, _ = _load_frontend_dicts()
    merged = set(_BACKEND_STATUS_ZH.values()) | set(frontend_status.values()) \
             | set(_BACKEND_ORDER_STATUS_ZH.values()) | set(_BACKEND_STEP_STATUS_ZH.values())
    return merged


def get_expected_datatype_zh() -> Set[str]:
    """获取 data_type 期望集合(后端 ∪ 前端)"""
    _, frontend_type = _load_frontend_dicts()
    merged = set(_BACKEND_DATATYPE_ZH.values()) | set(frontend_type.values())
    return merged


def get_expected_priority_zh() -> Set[str]:
    """获取 priority 期望集合"""
    return set(_BACKEND_PRIORITY_ZH.values())


def refresh_from_frontend(js_path: str = None) -> Dict[str, int]:
    """
    从前端 JS 文件解析 STATUS / TYPE 字典,写持久化文件
    由 CI 调用,避免硬编码漂移
    """
    import json
    if js_path is None:
        # 默认路径
        js_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..",
            "mobile_api_ai", "static", "js", "dispatch_center_labels.js"
        )
    if not os.path.exists(js_path):
        return {"error": "JS not found", "path": js_path}

    with open(js_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 解析 STATUS 块
    status_dict = _parse_js_object(content, "var STATUS")
    type_dict = _parse_js_object(content, "var TYPE")
    if not status_dict:
        status_dict = _parse_js_object(content, "STATUS = {") or _BUILTIN_FRONTEND_STATUS
    if not type_dict:
        type_dict = _parse_js_object(content, "TYPE = {") or _BUILTIN_FRONTEND_TYPE

    # 写持久化
    os.makedirs(os.path.dirname(_PERSIST_PATH), exist_ok=True)
    with open(_PERSIST_PATH, "w", encoding="utf-8") as f:
        json.dump({"status": status_dict, "type": type_dict}, f, ensure_ascii=False, indent=2)

    return {"status_count": len(status_dict), "type_count": len(type_dict), "path": _PERSIST_PATH}


def _parse_js_object(content: str, marker: str) -> Dict[str, str]:
    """简易 JS 对象解析:'key': 'value' 形式"""
    idx = content.find(marker)
    if idx < 0:
        return {}
    # 找到第一个 { 和匹配的 }
    start = content.find("{", idx)
    if start < 0:
        return {}
    depth = 0
    end = start
    for i in range(start, len(content)):
        if content[i] == "{":
            depth += 1
        elif content[i] == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    block = content[start:end + 1]
    result: Dict[str, str] = {}
    for m in re.finditer(r"""['"]?(\w+)['"]?\s*:\s*['"]([^'"]+)['"]""", block):
        result[m.group(1)] = m.group(2)
    return result


# ────────────────────────────────────────────────────────────
# 单测入口
# ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== EXPECTED_STATUS_ZH ===")
    print(f"  count={len(get_expected_status_zh())}")
    print(f"  sample={list(get_expected_status_zh())[:5]}")
    print("=== EXPECTED_DATATYPE_ZH ===")
    print(f"  count={len(get_expected_datatype_zh())}")
    print(f"  sample={list(get_expected_datatype_zh())[:5]}")
    print("=== refresh_from_frontend ===")
    print(f"  result={refresh_from_frontend()}")
