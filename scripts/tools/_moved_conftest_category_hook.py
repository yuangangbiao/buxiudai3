# -*- coding: utf-8 -*-
"""
pytest conftest.py - 自动分类更新钩子

功能：
- 每次 pytest 收集测试后自动分析新增测试用例
- 自动推断 case_type 和 boundary_cat
- 更新数据库

放置位置：
- 放在 tests/conftest.py 同级
- pytest 会自动加载
"""
import sys
from pathlib import Path

# 添加项目根目录到 sys.path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


def pytest_collection_finish(session):
    """pytest 收集完成后的钩子 - 自动更新分类"""
    try:
        from .workbuddy.tools.auto_update_test_categories import run_auto_update
        run_auto_update(mode='new')
    except Exception as e:
        # 不阻塞测试，只打印警告
        import warnings
        warnings.warn(f"自动分类更新失败: {e}")


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """pytest 结束后的钩子 - 输出提示"""
    if exitstatus == 0:
        print("\n[INFO] 所有测试通过！分类已自动更新。")
