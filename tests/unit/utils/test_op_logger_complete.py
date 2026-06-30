# -*- coding: utf-8 -*-
"""
utils/op_logger.py 测试 - 覆盖缺口: LOG_ENABLED=False 分支
"""
import pytest
import io
import sys
from unittest.mock import patch


class TestOpLoggerFunctions:
    """op_logger 所有函数测试 - 覆盖 LOG_ENABLED=False 分支"""

    def test_log_disabled(self):
        import utils.op_logger as op
        old_enabled = op.LOG_ENABLED
        op.LOG_ENABLED = False

        # 不应输出任何内容
        with patch('sys.stdout', new_callable=io.StringIO) as mock_out:
            op.log("测试模块", "测试动作", "详情")
            output = mock_out.getvalue()
        assert output == ""

        op.LOG_ENABLED = old_enabled

    def test_log_step_disabled(self):
        import utils.op_logger as op
        old_enabled = op.LOG_ENABLED
        op.LOG_ENABLED = False

        with patch('sys.stdout', new_callable=io.StringIO) as mock_out:
            op.log_step("模块", 1, "步骤1", "详情")
            output = mock_out.getvalue()
        assert output == ""

        op.LOG_ENABLED = old_enabled

    def test_log_calc_disabled(self):
        import utils.op_logger as op
        old_enabled = op.LOG_ENABLED
        op.LOG_ENABLED = False

        with patch('sys.stdout', new_callable=io.StringIO) as mock_out:
            op.log_calc("模块", "公式", {"a": 1}, 10)
            output = mock_out.getvalue()
        assert output == ""

        op.LOG_ENABLED = old_enabled

    def test_log_match_disabled(self):
        import utils.op_logger as op
        old_enabled = op.LOG_ENABLED
        op.LOG_ENABLED = False

        with patch('sys.stdout', new_callable=io.StringIO) as mock_out:
            op.log_match("模块", "编织", "标准网", True, "理由")
            output = mock_out.getvalue()
        assert output == ""

        op.LOG_ENABLED = old_enabled

    def test_log_sql_disabled(self):
        import utils.op_logger as op
        old_enabled = op.LOG_ENABLED
        op.LOG_ENABLED = False

        with patch('sys.stdout', new_callable=io.StringIO) as mock_out:
            op.log_sql("模块", "SELECT", "orders", "id=1")
            output = mock_out.getvalue()
        assert output == ""

        op.LOG_ENABLED = old_enabled

    def test_log_error_disabled(self):
        import utils.op_logger as op
        old_enabled = op.LOG_ENABLED
        op.LOG_ENABLED = False

        with patch('sys.stdout', new_callable=io.StringIO) as mock_out:
            op.log_error("模块", "动作", "错误信息")
            output = mock_out.getvalue()
        assert output == ""

        op.LOG_ENABLED = old_enabled

    def test_log_ui_disabled(self):
        import utils.op_logger as op
        old_enabled = op.LOG_ENABLED
        op.LOG_ENABLED = False

        with patch('sys.stdout', new_callable=io.StringIO) as mock_out:
            op.log_ui("模块", "点击按钮", "参数")
            output = mock_out.getvalue()
        assert output == ""

        op.LOG_ENABLED = old_enabled

    def test_log_calc_with_params(self):
        """log_calc 正常输出分支"""
        import utils.op_logger as op
        old_enabled = op.LOG_ENABLED
        op.LOG_ENABLED = True

        with patch('sys.stdout', new_callable=io.StringIO) as mock_out:
            op.log_calc("物料计算", "面积公式", {"长": 10, "宽": 5}, 50)
            output = mock_out.getvalue()
        assert "面积公式" in output
        assert "50" in output

        op.LOG_ENABLED = old_enabled

    def test_log_match_true(self):
        """log_match 匹配分支"""
        import utils.op_logger as op
        old_enabled = op.LOG_ENABLED
        op.LOG_ENABLED = True

        with patch('sys.stdout', new_callable=io.StringIO) as mock_out:
            op.log_match("规则引擎", "编织", "重型", True, "材质匹配")
            output = mock_out.getvalue()
        assert "✅匹配" in output

        op.LOG_ENABLED = old_enabled

    def test_log_match_false(self):
        """log_match 不匹配分支"""
        import utils.op_logger as op
        old_enabled = op.LOG_ENABLED
        op.LOG_ENABLED = True

        with patch('sys.stdout', new_callable=io.StringIO) as mock_out:
            op.log_match("规则引擎", "编织", "未知", False, "材质不匹配")
            output = mock_out.getvalue()
        assert "❌不匹配" in output

        op.LOG_ENABLED = old_enabled
