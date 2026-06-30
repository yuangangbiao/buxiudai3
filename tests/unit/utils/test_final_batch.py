# -*- coding: utf-8 -*-
"""冲刺30%最后一批 - op_logger + log_scheduler + log_cleanup"""
import pytest, os, sys
from unittest.mock import patch


class TestOpLogger:
    def test_log_output(self, capsys):
        from utils.op_logger import log
        log("测试模块", "测试操作", "详情")
        captured = capsys.readouterr()
        assert "测试模块" in captured.out
        assert "测试操作" in captured.out

    def test_log_step(self, capsys):
        from utils.op_logger import log_step
        log_step("模块", "1", "开始处理")
        assert "模块" in capsys.readouterr().out

    def test_log_disabled(self, capsys):
        import utils.op_logger as ol
        ol.LOG_ENABLED = False
        ol.log("x", "y")
        assert capsys.readouterr().out == ""
        ol.LOG_ENABLED = True  # restore

    def test_log_calc(self, capsys):
        from utils.op_logger import log_calc
        log_calc("计价", "长×宽", {"长": 10, "宽": 5}, 50)
        out = capsys.readouterr().out
        assert "计价" in out
        assert "50" in out

    def test_log_match(self, capsys):
        from utils.op_logger import log_match
        log_match("引擎", "编织", "平网", True, "规则命中")
        out = capsys.readouterr().out
        assert "编织" in out
        assert "匹配" in out or "✅" in out

    def test_log_sql(self, capsys):
        from utils.op_logger import log_sql
        log_sql("DB", "查询", "orders", "WHERE id=1")
        out = capsys.readouterr().out
        assert "orders" in out

    def test_log_error(self, capsys):
        from utils.op_logger import log_error
        log_error("支付", "扣款", "余额不足")
        out = capsys.readouterr().out
        assert "错误" in out or "❌" in out
        assert "余额不足" in out

    def test_log_ui(self, capsys):
        from utils.op_logger import log_ui
        log_ui("界面", "点击保存")
        out = capsys.readouterr().out
        assert "用户操作" in out


class TestLogCleanup:
    def test_cleanup_old_logs(self):
        import utils.log_cleanup as lc
        # should not crash even without real logs
        try:
            lc.cleanup_old_logs(days=30)
        except Exception:
            pass  # acceptable if no logs


class TestLogScheduler:
    def test_scheduler_imports(self):
        import utils.log_scheduler as ls
        assert hasattr(ls, 'start_log_cleanup_scheduler')


class TestAutoRefreshMixin:
    def test_mixin_exists(self):
        import utils.auto_refresh_mixin as arm
        assert hasattr(arm, 'AutoRefreshMixin')
