# -*- coding: utf-8 -*-
"""
三端订单状态统一计算真值源（v3.5.2 → v3.5.6）
================================================

设计目标
--------
dispatch_center / 手机端 / 容器中心 API 三端共享同一份状态判定逻辑，
避免因"调度员忘推进""报工数量已达标""兜底分支硬编码 i==0"等原因
造成的三端状态不一致。

判定优先级（从高到低）
---------------------
1. 强制完成（force_completed_list[i] == True）
2. 报工数量达标（sub_step_qty_map[step_name] >= required_qty）
3. 步骤索引推进（process_records.current_step, i < current_step）
4. 第一个"未完成"步骤标记为进行中
5. 其余步骤标记为待执行

副作用
------
- last_report_operator / last_report_time 仅在"进行中"步骤填入，
  已完成步骤返回空字符串（解决"显示老古董时间"问题）
- 返回结构与 legacy_routes.scan_info / dispatch_center.get_process_detail
  保持字段一致，三端可直接替换原判定循环

调用方式
--------
# 方式 A：流程节点状态（compute_step_statuses）
from api.step_status_helper import compute_step_statuses
statuses = compute_step_statuses(
    steps_list=steps,            # [{'name','role','status_key'}]
    sub_step_qty_map=qty_map,    # {'工序名': 已报工数量}
    current_step=current_step,   # int
    required_qty=required_qty,   # float
    sub_step_latest_map=latest,  # 可选 {工序名: 最新sub_step dict}
    force_completed_list=None,   # 可选 [bool, ...]
)
# 返回 [{'is_completed','is_current','completed_qty', ...}, ...]

# 方式 B：报工子步骤状态（compute_sub_step_statuses）
from api.step_status_helper import compute_sub_step_statuses
statuses = compute_sub_step_statuses(
    sub_step_qty_map=qty_map,    # {'工序名': 已报工数量}
    required_qty=required_qty,   # float
    sub_step_latest_map=latest,  # 可选 {工序名: 最新sub_step dict}
)

调用方清单（Caller Inventory）
-------------------------------
| # | 调用文件 | 函数 | 调用方式 | 用途 |
|---|---------|------|---------|------|
| 1 | app.py | all_process_tasks() | compute_sub_step_statuses | /api/all-process-tasks 工序任务页 |
| 2 | container_center_api.py | scan_info() | compute_sub_step_statuses | /api/scan-info 扫码报工详情 |
| 3 | container_center_api.py | get_process_detail() | compute_step_statuses | /api/container/process-detail 流程详情 |
| 4 | dispatch_center/_core.py | get_process_detail() | compute_step_statuses | 调度中心流程详情弹窗 |
| 5 | dispatch_center/_core.py | dispatch_loop() | compute_step_statuses | 调度循环自动判定 |

**迁移记录**：
- 2026-06-09 v3.5.6: 提取到独立文件 api/step_status_helper.py
- 此前逻辑内联在 app.py / container_center_api.py / _core.py 各端独立实现

演进历史（Changelog）
----------------------
| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-06-09 | v3.5.6 | 从 container_center_api.py / _core.py 提取到独立文件 |
| 2026-06-09 | v3.5.6 | 修复 self-OR 模式（14处）：重复 .get('key') or .get('key') 导致的假值丢失 |
| 2026-06-09 | v3.5.6 | 修复重复 dict key（22处）：同词典内两个相同 key，后值覆盖前值 |
| 2026-06-09 | v3.5.6 | 统一真值源后，三端（手机/桌面/调度中心）工序状态完全一致 |
| — | v3.5.2 | dispatch_center 首次提取公用函数（内联在 _core.py 中） |
| — | v3.5.0 | 首次发现三端状态不一致 bug（self-OR 漏洞导致 dispatch_center 状态漂移） |
"""
from typing import Dict, List, Optional


def compute_sub_step_statuses(
    sub_step_qty_map: Dict[str, float],
    required_qty: float,
    sub_step_latest_map: Optional[Dict[str, Dict]] = None,
) -> List[Dict]:
    """报工子步骤统一状态计算真值源（手机端 / 容器中心 / 工序任务页共享）

    与 compute_step_statuses 的差异：
    - 输入是已按工序名聚合的 sub_step_qty_map（而非 workflow 节点定义）
    - 不使用 current_step（子步骤无固定顺序，按是否完成判定）
    - 第一个未完成的子步骤标记为 current
    - status 字段用英文 (done/doing/wait)，与手机端 / 容器中心 API 约定一致

    参数:
        sub_step_qty_map: 工序名 → 累计已报工数量
        required_qty:    订单总需求数量
        sub_step_latest_map: 工序名 → 最新一条 sub_step 记录

    返回:
        与 sub_step_qty_map 等长的状态列表，每项字段:
        - is_completed / is_current / completed_qty / remaining_qty
        - last_report_operator / last_report_time / last_report_qty
        - status: 'done' / 'doing' / 'wait'
    """
    if not sub_step_qty_map:
        return []

    sub_step_latest_map = sub_step_latest_map or {}
    req = float(required_qty or 0)
    out = []
    first_active_assigned = False

    for name, qty in sub_step_qty_map.items():
        qty = float(qty or 0)
        # 子步骤：报工数量达标 → 已完成
        is_done = req > 0 and qty >= req
        # 第一个未完成子步骤标记为 current（导航用，提示下一步做哪个）
        # 语义说明：与 status 解耦 —— 多个子工序可同时 doing（并行生产），
        # is_current 只用于告诉前端"建议从这里开始"
        is_current = (not is_done) and (not first_active_assigned)
        if is_current:
            first_active_assigned = True

        if is_current:
            last = sub_step_latest_map.get(name) or {}
            op = last.get('operator', '') if isinstance(last, dict) else ''
            ts = last.get('created_at', '') if isinstance(last, dict) else ''
            lq = last.get('quantity', 0) if isinstance(last, dict) else 0
        else:
            op, ts, lq = '', '', 0

        # status 独立于 is_current：有量但未达标 → doing（并行生产常见）
        if is_done:
            status = 'done'
        elif qty > 0:
            status = 'doing'
        else:
            status = 'wait'

        out.append({
            'is_completed': is_done,
            'is_current': is_current,
            'completed_qty': qty,
            'remaining_qty': max(0.0, req - qty) if req > 0 else 0.0,
            'last_report_operator': op,
            'last_report_time': ts,
            'last_report_qty': lq,
            'status': status,
        })

    return out


def compute_step_statuses(
    steps_list: List[Dict],
    sub_step_qty_map: Dict[str, float],
    current_step: int,
    required_qty: float,
    sub_step_latest_map: Optional[Dict[str, Dict]] = None,
    force_completed_list: Optional[List[bool]] = None,
) -> List[Dict]:
    """三端统一的状态计算真值源。

    参数:
        steps_list: 工序定义列表，每项需含 'name' 字段
        sub_step_qty_map: 工序名 → 累计已报工数量
        current_step: process_records.current_step 索引（0-based）
        required_qty: 订单总需求数量
        sub_step_latest_map: 工序名 → 最新一条 sub_step 记录（用于填 last_report_*）
        force_completed_list: 强制完成标记列表（与 steps_list 等长）

    返回:
        与 steps_list 等长的状态列表，每项字段:
        - is_completed: bool
        - is_current: bool
        - completed_qty: float
        - remaining_qty: float
        - last_report_operator: str（仅进行中步骤填）
        - last_report_time: str（仅进行中步骤填）
        - last_report_qty: float（仅进行中步骤填）
        - status: '已完成' / '进行中' / '待执行'
    """
    if not steps_list:
        return []

    sub_step_latest_map = sub_step_latest_map or {}
    force_completed_list = force_completed_list or [False] * len(steps_list)
    # 长度对齐：steps 多了就补 False，force 多了就裁掉
    if len(force_completed_list) < len(steps_list):
        force_completed_list = force_completed_list + [False] * (len(steps_list) - len(force_completed_list))
    elif len(force_completed_list) > len(steps_list):
        force_completed_list = force_completed_list[:len(steps_list)]

    out = []
    first_active_assigned = False
    for i, step in enumerate(steps_list):
        name = step.get('name', str(step)) if isinstance(step, dict) else str(step)
        qty = float(sub_step_qty_map.get(name, 0) or 0)
        req = float(required_qty or 0)

        # 1+2+3 三个条件任一成立 → 已完成
        is_done = bool(
            force_completed_list[i]
            or (req > 0 and qty >= req)
            or (i < current_step)
        )

        # 4 第一个"未完成"步骤为进行中
        is_active = (not is_done) and (not first_active_assigned)
        if is_active:
            first_active_assigned = True

        # 已完成步骤不显示 last_report_*（修问题 C）
        if is_active:
            last = sub_step_latest_map.get(name) or {}
            op = last.get('operator', '') if isinstance(last, dict) else ''
            ts = last.get('created_at', '') if isinstance(last, dict) else ''
            lq = last.get('quantity', 0) if isinstance(last, dict) else 0
        else:
            op, ts, lq = '', '', 0

        out.append({
            'is_completed': is_done,
            'is_current': is_active,
            'completed_qty': qty,
            'remaining_qty': max(0.0, req - qty) if req > 0 else 0.0,
            'last_report_operator': op,
            'last_report_time': ts,
            'last_report_qty': lq,
            'status': '已完成' if is_done else ('进行中' if is_active else '待执行'),
        })

    return out
