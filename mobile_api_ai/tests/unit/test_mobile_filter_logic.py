# -*- coding: utf-8 -*-
"""
T-04: 手机端任务过滤逻辑单元测试

覆盖范围（边界矩阵）：
- F-01: 登录人 enterprise_id === 任务 operatorId → 可见
- F-02: 登录人 enterprise_id !== 任务 operatorId → 不可见
- F-03: is_public=true 任务 → 始终可见（忽略 operatorId）
- F-04: currentUser=null（未登录）→ 只显示 is_public=true 任务
- F-05: currentUser.username=''（空）→ 不匹配任何指派任务，只显示全员
- F-06: operatorId 带空格 → trim 后比对
- F-07: operatorId=enterprise_id 全匹配，大小写敏感
- F-08: 混合场景 — 3 个任务（1 匹配 + 1 不匹配 + 1 全员）→ 只显示 2 个
- F-09: 阶段 3 迁移前历史姓名任务 → 阶段 1 不处理（返回 is_public=false + 旧姓名不可见）

实现策略：
- 将 mobile_unified.html:1074-1078 的过滤逻辑提取为纯函数
- 用 Python 模拟 JavaScript 的 String/Boolean 行为
- 每个 case 直接对应一个 filter 断言
"""
import pytest


# ============================================================================
# 纯函数：模拟 mobile_unified.html:1074-1078 的过滤逻辑
# ============================================================================

def _normalize(v):
    """模拟 JS String(v).trim() 行为"""
    if v is None:
        return ''
    return str(v).strip()


def _toBool(v):
    """模拟 JS !!(v) 行为"""
    return bool(v)


def filter_my_tasks(tasks, current_user):
    """
    模拟前端过滤逻辑（mobile_unified.html:1074-1078）

    参数:
        tasks: list[dict] - 任务列表
        current_user: dict | None - 登录用户，None 表示未登录

    返回:
        list[dict] - 过滤后的任务列表
    """
    current_op_id = _normalize(
        current_user.get('username', '') if current_user else ''
    ) if current_user else ''

    result = []
    for t in (tasks or []):
        op_id = _normalize(t.get('operatorId', ''))
        is_public = _toBool(t.get('isPublic', False))

        # 匹配条件：is_public=true OR (operatorId 非空 且 === currentOpId)
        visible = is_public or (op_id != '' and op_id == current_op_id)
        if visible:
            result.append(t)

    return result


# ============================================================================
# 测试用例
# ============================================================================

class TestMobileTaskFilter:
    """手机端任务过滤逻辑边界矩阵测试"""

    # ---------- F-01: ID 精确匹配 ----------
    def test_f01_id_match_visible(self):
        """登录人 enterprise_id === 任务 operatorId → 可见"""
        tasks = [
            {'operatorId': 'ZhangSan', 'isPublic': False, 'processName': '清洗'},
        ]
        user = {'username': 'ZhangSan', 'name': '张三'}
        result = filter_my_tasks(tasks, user)
        assert len(result) == 1
        assert result[0]['processName'] == '清洗'

    # ---------- F-02: ID 不匹配 ----------
    def test_f02_id_no_match_hidden(self):
        """登录人 enterprise_id !== 任务 operatorId → 不可见"""
        tasks = [
            {'operatorId': 'LiSi', 'isPublic': False, 'processName': '焊接'},
        ]
        user = {'username': 'ZhangSan', 'name': '张三'}
        result = filter_my_tasks(tasks, user)
        assert len(result) == 0

    # ---------- F-03: is_public=true 全员任务 ----------
    def test_f03_public_always_visible(self):
        """is_public=true 任务 → 始终可见（忽略 operatorId）"""
        tasks = [
            {'operatorId': 'OtherWorker', 'isPublic': True, 'processName': '质检'},
            {'operatorId': 'ZhangSan', 'isPublic': True, 'processName': '装配'},
        ]
        user = {'username': 'ZhangSan', 'name': '张三'}
        result = filter_my_tasks(tasks, user)
        assert len(result) == 2

    # ---------- F-04: 未登录 ----------
    def test_f04_no_user_shows_only_public(self):
        """currentUser=null（未登录）→ 只显示 is_public=true 任务"""
        tasks = [
            {'operatorId': 'ZhangSan', 'isPublic': False, 'processName': '清洗'},
            {'operatorId': '', 'isPublic': True, 'processName': '质检'},
        ]
        result = filter_my_tasks(tasks, None)
        assert len(result) == 1
        assert result[0]['processName'] == '质检'

    # ---------- F-05: 空 username ----------
    def test_f05_empty_username_no_match(self):
        """currentUser.username=''（空）→ 不匹配任何指派任务，只显示全员"""
        tasks = [
            {'operatorId': 'ZhangSan', 'isPublic': False, 'processName': '清洗'},
            {'operatorId': '', 'isPublic': True, 'processName': '质检'},
        ]
        user = {'username': '', 'name': ''}
        result = filter_my_tasks(tasks, user)
        assert len(result) == 1
        assert result[0]['processName'] == '质检'

    # ---------- F-06: operatorId 带空格（trim 处理） ----------
    def test_f06_operator_id_with_spaces_trimmed(self):
        """operatorId 带首尾空格 → trim 后比对（应匹配）"""
        tasks = [
            {'operatorId': ' ZhangSan ', 'isPublic': False, 'processName': '清洗'},
        ]
        user = {'username': 'ZhangSan', 'name': '张三'}
        result = filter_my_tasks(tasks, user)
        assert len(result) == 1

    # ---------- F-07: 大小写敏感 ----------
    def test_f07_case_sensitive_no_match(self):
        """enterprise_id 大小写敏感 → 'zhangsan' !== 'ZhangSan'（不匹配）"""
        tasks = [
            {'operatorId': 'ZhangSan', 'isPublic': False, 'processName': '清洗'},
        ]
        user = {'username': 'zhangsan', 'name': '张三'}
        result = filter_my_tasks(tasks, user)
        assert len(result) == 0

    # ---------- F-08: 混合场景 ----------
    def test_f08_mixed_tasks(self):
        """3 个任务（1 匹配 + 1 不匹配 + 1 全员）→ 只显示 2 个"""
        tasks = [
            {'operatorId': 'ZhangSan', 'isPublic': False, 'processName': '清洗'},
            {'operatorId': 'LiSi', 'isPublic': False, 'processName': '焊接'},
            {'operatorId': '', 'isPublic': True, 'processName': '质检'},
        ]
        user = {'username': 'ZhangSan', 'name': '张三'}
        result = filter_my_tasks(tasks, user)
        assert len(result) == 2
        names = [t['processName'] for t in result]
        assert '清洗' in names
        assert '质检' in names
        assert '焊接' not in names

    # ---------- F-09: 历史姓名任务（阶段 3 前） ----------
    def test_f09_old_name_task_not_visible(self):
        """历史姓名任务（target_operator 存的是中文姓名）
        → 阶段 1 不处理 → operatorId='张三' !== enterprise_id='ZhangSan' → 不可见"""
        tasks = [
            {'operatorId': '张三', 'isPublic': False, 'processName': '清洗'},  # 历史中文姓名
        ]
        user = {'username': 'ZhangSan', 'name': '张三'}
        result = filter_my_tasks(tasks, user)
        # 阶段 1: operatorId='张三' !== 'ZhangSan' → 不可见
        # 阶段 3 迁移后: target_operator 改为 'ZhangSan' → 可见
        assert len(result) == 0

    # ---------- 边界: is_public=false + operatorId='' ----------
    def test_f10_empty_operator_no_public_hidden(self):
        """is_public=false 且 operatorId='' → 既不是全员也不是有效指派 → 不可见"""
        tasks = [
            {'operatorId': '', 'isPublic': False, 'processName': '未知任务'},
        ]
        user = {'username': 'ZhangSan', 'name': '张三'}
        result = filter_my_tasks(tasks, user)
        assert len(result) == 0

    # ---------- 边界: operatorId 缺失字段 ----------
    def test_f11_missing_operator_id_field(self):
        """task 中没有 operatorId 字段 → 视为空字符串 → 不可见（除非 is_public）"""
        tasks = [
            {'isPublic': False, 'processName': '缺失字段任务'},
        ]
        user = {'username': 'ZhangSan', 'name': '张三'}
        result = filter_my_tasks(tasks, user)
        assert len(result) == 0

    # ---------- 边界: username 字段缺失 ----------
    def test_f12_missing_username_field(self):
        """currentUser 没有 username 字段 → 视为空 → 不匹配任何指派任务"""
        tasks = [
            {'operatorId': 'ZhangSan', 'isPublic': False, 'processName': '清洗'},
            {'operatorId': '', 'isPublic': True, 'processName': '质检'},
        ]
        user = {'name': '张三'}  # 没有 username
        result = filter_my_tasks(tasks, user)
        assert len(result) == 1  # 只有全员任务
        assert result[0]['processName'] == '质检'

    # ---------- 边界: isPublic 字段缺失 ----------
    def test_f13_missing_ispublic_field(self):
        """task.isPublic 字段缺失 → JS !!(undefined) = false → 等同 is_public=false"""
        tasks = [
            {'operatorId': 'ZhangSan', 'processName': '清洗'},  # 无 isPublic 字段
        ]
        user = {'username': 'ZhangSan', 'name': '张三'}
        result = filter_my_tasks(tasks, user)
        assert len(result) == 1  # operatorId 匹配所以可见

    # ---------- 边界: 数字 enterprise_id ----------
    def test_f14_numeric_enterprise_id(self):
        """enterprise_id 为纯数字字符串（如 '001'）→ 正常比对"""
        tasks = [
            {'operatorId': '001', 'isPublic': False, 'processName': '清洗'},
            {'operatorId': '002', 'isPublic': False, 'processName': '焊接'},
        ]
        user = {'username': '001', 'name': '张三'}
        result = filter_my_tasks(tasks, user)
        assert len(result) == 1
        assert result[0]['processName'] == '清洗'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
