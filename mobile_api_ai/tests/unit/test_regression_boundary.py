# -*- coding: utf-8 -*-
"""T9: 边界用例矩阵 — 报工数据回归 (add-feature 5类必覆盖)"""
import pytest
from datetime import datetime, timedelta
from regression.decision import decide_regression, INSERT, OVERWRITE, PROMPT, IDEMPOTENT, REJECT_TIMEOUT, REJECT_OVER_QTY, REJECT_LOCKED


class TestDecisionBoundary:
    """5类边界测试矩阵"""

    # ========== 1. 空 ==========
    def test_none_existing_inserts(self):
        action, ctx = decide_regression('张三', 50, 'B1', None, 100, 0, False, 0)
        assert action == INSERT

    def test_zero_quantity_none_existing(self):
        """quantity=0 应在上层拦截，此处测试决策树不崩溃"""
        action, ctx = decide_regression('张三', 0, 'B1', None, 100, 0, False, 0)
        assert action == INSERT

    def test_empty_batch_no_first_time(self):
        """无批次号的首次报工"""
        action, ctx = decide_regression('张三', 50, '', None, 100, 0, False, 0)
        assert action == INSERT

    # ========== 2. 单条 ==========
    def test_normal_first_insert(self):
        action, ctx = decide_regression('张三', 50, 'B1', None, 100, 0, False, 0)
        assert action == INSERT
        assert ctx == {}

    def test_normal_idempotent(self):
        existing = {'id': 1, 'operator': '张三', 'quantity': 50, 'batch_no': 'B1', 'created_at': str(datetime.now())}
        action, ctx = decide_regression('张三', 50, 'B1', existing, 100, 0, False, 0)
        assert action == IDEMPOTENT
        assert ctx.get('existing_id') == 1

    def test_same_operator_different_batch_inserts(self):
        """同人不同批次 → 允许分批报工（不覆盖）"""
        existing = {'id': 1, 'operator': '张三', 'quantity': 50, 'batch_no': 'B1', 'first_created_at': datetime.now().isoformat()}
        action, ctx = decide_regression('张三', 80, 'B2', existing, 200, 0, False, 0)
        assert action == INSERT  # 追加新记录，不覆盖旧批次

    # ========== 3. 阈值 ==========
    def test_grace_period_boundary(self):
        """30分钟内 → 同人追加新记录（分批报工）"""
        thirty_min_ago = datetime.now() - timedelta(minutes=29, seconds=59)
        existing = {'id': 1, 'operator': '张三', 'quantity': 50, 'batch_no': 'B1',
                     'first_created_at': thirty_min_ago.isoformat()}
        action, ctx = decide_regression('张三', 80, 'B2', existing, 200, 0, False, 0)
        assert action == INSERT  # 分批报工，追加不覆盖

    def test_audit_period_boundary(self):
        """刚好 23:59 前 → 可修正但不自由"""
        almost_24h = datetime.now() - timedelta(hours=23, minutes=59)
        existing = {'id': 1, 'operator': '李四', 'quantity': 50, 'batch_no': 'B1',
                     'first_created_at': almost_24h.isoformat()}
        action, ctx = decide_regression('王五', 30, 'B2', existing, 100, 0, False, 0)
        assert action == PROMPT

    def test_timeout_boundary(self):
        """刚好 24:01 前 → 拒绝"""
        over_24h = datetime.now() - timedelta(hours=24, minutes=1)
        existing = {'id': 1, 'operator': '李四', 'quantity': 50, 'batch_no': 'B1',
                     'first_created_at': over_24h.isoformat()}
        action, ctx = decide_regression('王五', 80, 'B2', existing, 100, 0, False, 0)
        assert action == REJECT_TIMEOUT

    # ========== 4. 上溢 ==========
    def test_quantity_overflow_append(self):
        """追加后超出需求 → 拒绝"""
        existing = {'id': 1, 'operator': '张三', 'quantity': 80, 'batch_no': 'B1', 'created_at': str(datetime.now())}
        action, ctx = decide_regression('李四', 50, 'B2', existing, 100, 0, False, 0)
        assert action == REJECT_OVER_QTY
        assert ctx.get('merged') == 130

    def test_malicious_threshold(self):
        """刚好到恶意阈值 → 冻结"""
        existing = {'id': 1, 'operator': '张三', 'quantity': 50, 'batch_no': 'B1', 'created_at': str(datetime.now())}
        action, ctx = decide_regression('李四', 30, 'B2', existing, 100, 3, False, 0)
        assert action == REJECT_LOCKED

    # ========== 5. 并发 ==========
    def test_qc_locked_rejects(self):
        """质检锁定中 → 拒绝"""
        existing = {'id': 1, 'operator': '张三', 'quantity': 50, 'batch_no': 'B1', 'created_at': str(datetime.now())}
        action, ctx = decide_regression('李四', 30, 'B2', existing, 100, 0, True, 0)
        assert action == REJECT_LOCKED
        assert '质检' in ctx.get('message', '')


class TestDecisionPrompt:
    """弹窗分支 (code=300)"""

    def test_other_operator_less_quantity_prompts(self):
        existing = {'id': 1, 'operator': '张三', 'quantity': 50, 'batch_no': 'B1', 'created_at': str(datetime.now())}
        action, ctx = decide_regression('李四', 30, 'B2', existing, 100, 0, False, 0)
        assert action == PROMPT
        assert ctx.get('prompt_type') == 'override_less'

    def test_other_operator_more_quantity_prompts_append(self):
        existing = {'id': 1, 'operator': '张三', 'quantity': 30, 'batch_no': 'B1', 'first_created_at': datetime.now().isoformat()}
        action, ctx = decide_regression('李四', 40, 'B2', existing, 100, 0, False, 0)
        assert action == PROMPT
        assert ctx.get('prompt_type') == 'append'
        assert ctx.get('merged') == 70
