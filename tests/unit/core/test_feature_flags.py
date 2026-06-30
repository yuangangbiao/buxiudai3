# -*- coding: utf-8 -*-
"""core/feature_flags.py 的集成测试（真业务，不 mock 业务路径）。

测试覆盖:
- 5 个 test 函数,期望 100% 覆盖 core/feature_flags.py
- 按 F16 §1:不 mock FeatureFlags 业务方法(只清理测试间状态污染)
"""
import pytest

from core.feature_flags import FeatureFlags


@pytest.fixture(autouse=True)
def _isolate_flags_state():
    """每个 test 前清空 _flags,test 后再清空(避免跨测试污染)。"""
    FeatureFlags._flags.clear()
    yield
    FeatureFlags._flags.clear()


def test_is_enabled_returns_default_when_unconfigured():
    """未配置的特性开关应返回 default 参数值(默认 False)。"""
    assert FeatureFlags.is_enabled("nonexistent_feature") is False
    assert FeatureFlags.is_enabled("nonexistent_feature", default=True) is True


def test_load_parses_all_truthy_variants(monkeypatch):
    """load() 必须把 true/1/yes/on 都解析为 True,falsy 值解析为 False。"""
    monkeypatch.setenv("FEATURE_AI_REPORT", "true")
    monkeypatch.setenv("FEATURE_REDIS_BUS", "1")
    monkeypatch.setenv("FEATURE_OLD_MODULE", "yes")
    monkeypatch.setenv("FEATURE_BETA_OPT", "on")
    monkeypatch.setenv("FEATURE_DISABLED_A", "false")
    monkeypatch.setenv("FEATURE_DISABLED_B", "0")
    FeatureFlags.load()
    assert FeatureFlags.is_enabled("ai_report") is True
    assert FeatureFlags.is_enabled("redis_bus") is True
    assert FeatureFlags.is_enabled("old_module") is True
    assert FeatureFlags.is_enabled("beta_opt") is True
    assert FeatureFlags.is_enabled("disabled_a") is False
    assert FeatureFlags.is_enabled("disabled_b") is False


def test_is_enabled_is_case_insensitive(monkeypatch):
    """is_enabled 大小写不敏感(env FEATURE_AI_REPORT → is_enabled('ai_report'))。"""
    monkeypatch.setenv("FEATURE_NewFeature", "true")
    FeatureFlags.load()
    assert FeatureFlags.is_enabled("newfeature") is True
    assert FeatureFlags.is_enabled("NEWFEATURE") is True
    assert FeatureFlags.is_enabled("NewFeature") is True


def test_all_returns_shallow_copy_not_reference():
    """all() 必须返浅拷贝——修改返回值不能污染内部 _flags。"""
    FeatureFlags._flags["x"] = True
    snapshot = FeatureFlags.all()
    snapshot["x"] = False
    snapshot["y"] = True
    assert FeatureFlags._flags["x"] is True
    assert "y" not in FeatureFlags._flags


def test_all_initially_empty():
    """未加载时 all() 返空 dict(确保隔离 fixture 生效)。"""
    assert FeatureFlags.all() == {}
