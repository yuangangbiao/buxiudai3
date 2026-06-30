# -*- coding: utf-8 -*-
"""
三端订单状态统一计算 - 单测

覆盖 5 个核心 case:
1. test_all_zero: 全新工单（无推进、零报工）→ 全部待执行
2. test_partial_reported: 报工数达标但 current_step=0 → 强制完成
3. test_advanced_step: current_step=3 → 前 3 步完成、第 4 步进行中
4. test_force_completed: 强制标记 + current=0 → 强制那步完成
5. test_fallback_path: fallback 分支（修问题 B：不再硬编码 i==0）

修问题 A/B/C:
- A: 报工数达标即完成，调度员忘推进也能正确显示
- B: fallback 路径不再硬编码 is_current=(i==0)
- C: 已完成步骤的 last_report_* 置空（仅进行中填）
"""
import sys
import os
import pytest

# 路径注入（与项目其他单测一致）
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
_MOBILE_ROOT = os.path.join(_PROJECT_ROOT, 'mobile_api_ai')
for p in (_PROJECT_ROOT, _MOBILE_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from api.step_status_helper import compute_step_statuses


# 7 步生产流程模板（与 dispatch_center.PROCESS_FLOW_TEMPLATES['production'] 一致）
STEPS_7 = [
    {'name': '工单发布',  'role': '计划部', 'status_key': 'published'},
    {'name': '排产制定',  'role': '生产部', 'status_key': 'scheduled'},
    {'name': '排产确认',  'role': '计划部', 'status_key': 'confirmed'},
    {'name': '生产执行',  'role': '生产部', 'status_key': 'in_production'},
    {'name': '报工完成',  'role': '生产部', 'status_key': 'reported'},
    {'name': '质检审核',  'role': '质检部', 'status_key': 'qc_passed'},
    {'name': '完工入库',  'role': '仓库',   'status_key': 'completed'},
]


def test_all_zero():
    """case 1: 全新工单（无推进、零报工）→ 仅第 1 步进行中，其余 6 步待执行"""
    statuses = compute_step_statuses(
        steps_list=STEPS_7,
        sub_step_qty_map={},
        current_step=0,
        required_qty=1000,
    )
    assert len(statuses) == 7
    # 所有步骤都不应已完成
    for i, st in enumerate(statuses):
        assert st['is_completed'] is False, f"step {i} should not be completed"
    # 第 0 步（i==0）应被标记为进行中
    assert statuses[0]['is_current'] is True
    assert statuses[0]['status'] == '进行中'
    # 其余 6 步（i=1..6）应为待执行
    for i in range(1, 7):
        assert statuses[i]['is_current'] is False, f"step {i} should not be current"
        assert statuses[i]['status'] == '待执行', f"step {i} should be 待执行, got {statuses[i]['status']}"


def test_partial_reported():
    """case 2: 报工数达标但 current_step=0 → 强制完成（修问题 A）"""
    # 工序"生产执行"已报工 1000/1000，但调度员忘点推进，current_step 仍为 0
    qty_map = {
        '工单发布': 1000, '排产制定': 1000, '排产确认': 1000,
        '生产执行': 1000,  # 达标
        # 后续步骤未报工
    }
    statuses = compute_step_statuses(
        steps_list=STEPS_7,
        sub_step_qty_map=qty_map,
        current_step=0,           # ⚠️ 调度员忘推进
        required_qty=1000,
    )
    # 前 4 步（含生产执行）应被标记为已完成（数量达标）
    for i in range(0, 4):
        assert statuses[i]['is_completed'] is True, f"step {i} should be completed (qty reached)"
        assert statuses[i]['is_current'] is False
        assert statuses[i]['status'] == '已完成'
    # 第 5 步（报工完成）应是进行中
    assert statuses[4]['is_completed'] is False
    assert statuses[4]['is_current'] is True
    assert statuses[4]['status'] == '进行中'
    # 后续步骤待执行
    for i in range(5, 7):
        assert statuses[i]['is_completed'] is False
        assert statuses[i]['is_current'] is False


def test_advanced_step():
    """case 3: current_step=3 → 前 3 步完成、第 4 步进行中"""
    statuses = compute_step_statuses(
        steps_list=STEPS_7,
        sub_step_qty_map={},  # 零报工，纯靠 current_step 推算
        current_step=3,
        required_qty=1000,
    )
    # 前 3 步完成
    for i in range(3):
        assert statuses[i]['is_completed'] is True
        assert statuses[i]['status'] == '已完成'
    # 第 4 步（index 3）进行中
    assert statuses[3]['is_completed'] is False
    assert statuses[3]['is_current'] is True
    assert statuses[3]['status'] == '进行中'
    # 后续待执行
    for i in range(4, 7):
        assert statuses[i]['is_completed'] is False
        assert statuses[i]['is_current'] is False


def test_force_completed():
    """case 4: 强制标记 + current=0 → 强制那步完成（修预留扩展位）"""
    # 强制第 2 步（排产制定）完成
    force = [False, True, False, False, False, False, False]
    statuses = compute_step_statuses(
        steps_list=STEPS_7,
        sub_step_qty_map={},
        current_step=0,
        required_qty=1000,
        force_completed_list=force,
    )
    # 第 0 步（i==0）应被标记为进行中
    assert statuses[0]['is_current'] is True
    # 第 1 步（强制完成）→ 已完成
    assert statuses[1]['is_completed'] is True
    assert statuses[1]['status'] == '已完成'
    # 其余待执行
    for i in range(2, 7):
        assert statuses[i]['is_completed'] is False


def test_fallback_path():
    """case 5: fallback 分支 — 修问题 B（不再硬编码 is_current=(i==0)）"""
    # 模拟老工单数据：前 3 步报工数已达标，但 current_step 仍为 0（兜底场景）
    qty_map = {
        '工单发布': 100, '排产制定': 100, '排产确认': 100,
        # 后续步骤零报工
    }
    statuses = compute_step_statuses(
        steps_list=STEPS_7,
        sub_step_qty_map=qty_map,
        current_step=0,  # fallback 默认 0
        required_qty=100,
    )
    # 前 3 步因数量达标，标记为已完成（不再是硬编码 i==0）
    for i in range(3):
        assert statuses[i]['is_completed'] is True, (
            f"fallback 路径 step {i} 应被标记为已完成（报工数达标），"
            f"但实际是 is_completed={statuses[i]['is_completed']}"
        )
    # 第 4 步（index 3）进行中
    assert statuses[3]['is_current'] is True
    # 后续待执行
    for i in range(4, 7):
        assert statuses[i]['is_completed'] is False
        assert statuses[i]['is_current'] is False


def test_last_report_only_for_active():
    """case 6 (附加): 修问题 C — 已完成步骤的 last_report_* 置空"""
    latest_map = {
        '工单发布': {'operator': '张三', 'created_at': '2026-06-01 10:00:00', 'quantity': 100},
        '排产制定': {'operator': '李四', 'created_at': '2026-06-02 11:00:00', 'quantity': 100},
        '排产确认': {'operator': '王五', 'created_at': '2026-06-03 12:00:00', 'quantity': 100},
        '生产执行': {'operator': '赵六', 'created_at': '2026-06-04 13:00:00', 'quantity': 100},
        '报工完成': {'operator': '钱七', 'created_at': '2026-06-05 14:00:00', 'quantity': 50},
    }
    qty_map = {k: 100 for k in ['工单发布', '排产制定', '排产确认', '生产执行']}
    statuses = compute_step_statuses(
        steps_list=STEPS_7,
        sub_step_qty_map=qty_map,
        current_step=0,  # 调度员忘推进
        required_qty=100,
        sub_step_latest_map=latest_map,
    )
    # 前 4 步已完成 → last_report_* 应为空
    for i in range(4):
        assert statuses[i]['is_completed'] is True
        assert statuses[i]['last_report_operator'] == '', (
            f"已完成步骤 {i} 的 last_report_operator 应为空，实际: {statuses[i]['last_report_operator']}"
        )
        assert statuses[i]['last_report_time'] == ''
    # 第 5 步（报工完成）进行中 → last_report_* 保留
    assert statuses[4]['is_current'] is True
    assert statuses[4]['last_report_operator'] == '钱七'
    assert statuses[4]['last_report_time'] == '2026-06-05 14:00:00'
    assert statuses[4]['last_report_qty'] == 50


def test_empty_steps_list():
    """case 7 (边界): 空 steps_list → 返回空列表，不抛异常"""
    statuses = compute_step_statuses(
        steps_list=[],
        sub_step_qty_map={},
        current_step=0,
        required_qty=1000,
    )
    assert statuses == []


def test_force_list_length_mismatch():
    """case 8 (边界): force_completed_list 长度不匹配 → 自动对齐"""
    force = [True]  # 长度 1，steps 长度 7
    statuses = compute_step_statuses(
        steps_list=STEPS_7,
        sub_step_qty_map={},
        current_step=0,
        required_qty=1000,
        force_completed_list=force,
    )
    # 第 0 步被强制完成
    assert statuses[0]['is_completed'] is True
    # 其余 6 步待执行
    for i in range(1, 7):
        assert statuses[i]['is_completed'] is False


if __name__ == '__main__':
    # 允许直接 python 执行（不依赖 pytest）
    test_all_zero()
    test_partial_reported()
    test_advanced_step()
    test_force_completed()
    test_fallback_path()
    test_last_report_only_for_active()
    test_empty_steps_list()
    test_force_list_length_mismatch()
    print("✓ 所有 8 个 case 全部通过")
