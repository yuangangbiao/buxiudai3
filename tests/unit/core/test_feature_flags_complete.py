# -*- coding: utf-8 -*-
"""
core/feature_flags.py 完整单元测试

覆盖模块:
- FeatureFlags
- load()
- is_enabled()
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest
from unittest.mock import patch


class TestFeatureFlagsExists:
    """FeatureFlags 存在性测试"""

    def test_feature_flags_module_exists(self):
        """测试feature_flags模块存在"""
        from core import feature_flags
        assert feature_flags is not None

    def test_feature_flags_class_exists(self):
        """测试FeatureFlags类存在"""
        from core.feature_flags import FeatureFlags
        assert FeatureFlags is not None


class TestFeatureFlagsLoad:
    """FeatureFlags load() 测试"""

    @patch.dict(os.environ, {'FEATURE_AI_REPORT': 'true', 'FEATURE_DEBUG': 'false'})
    def test_load_from_env_true(self):
        """测试加载环境变量为true"""
        from core.feature_flags import FeatureFlags
        FeatureFlags._flags.clear()
        FeatureFlags.load()
        assert FeatureFlags.is_enabled('ai_report') is True

    @patch.dict(os.environ, {'FEATURE_AI_REPORT': 'false', 'FEATURE_DEBUG': '0'})
    def test_load_from_env_false(self):
        """测试加载环境变量为false"""
        from core.feature_flags import FeatureFlags
        FeatureFlags._flags.clear()
        FeatureFlags.load()
        assert FeatureFlags.is_enabled('ai_report') is False

    @patch.dict(os.environ, {'FEATURE_AI_REPORT': '1', 'FEATURE_DEBUG': 'yes'})
    def test_load_various_true_values(self):
        """测试各种表示true的值"""
        from core.feature_flags import FeatureFlags
        FeatureFlags._flags.clear()
        FeatureFlags.load()
        assert FeatureFlags.is_enabled('ai_report') is True
        assert FeatureFlags.is_enabled('debug') is True

    @patch.dict(os.environ, {'FEATURE_TEST': 'no', 'FEATURE_FOO': 'off'})
    def test_load_various_false_values(self):
        """测试各种表示false的值"""
        from core.feature_flags import FeatureFlags
        FeatureFlags._flags.clear()
        FeatureFlags.load()
        assert FeatureFlags.is_enabled('test') is False
        assert FeatureFlags.is_enabled('foo') is False


class TestFeatureFlagsIsEnabled:
    """FeatureFlags is_enabled() 测试"""

    def test_is_enabled_default_false(self):
        """测试未配置时默认返回False"""
        from core.feature_flags import FeatureFlags
        FeatureFlags._flags.clear()
        assert FeatureFlags.is_enabled('unknown') is False

    def test_is_enabled_with_default_true(self):
        """测试自定义默认值"""
        from core.feature_flags import FeatureFlags
        FeatureFlags._flags.clear()
        assert FeatureFlags.is_enabled('unknown', default=True) is True

    def test_is_enabled_case_insensitive(self):
        """测试大小写不敏感"""
        from core.feature_flags import FeatureFlags
        FeatureFlags._flags.clear()
        FeatureFlags._flags['ai_report'] = True
        assert FeatureFlags.is_enabled('AI_REPORT') is True
        assert FeatureFlags.is_enabled('Ai_Report') is True


class TestFeatureFlagsComplete:
    """FeatureFlags 完整性测试"""

    def test_has_load_method(self):
        """测试有load方法"""
        from core.feature_flags import FeatureFlags
        assert hasattr(FeatureFlags, 'load')
        assert callable(FeatureFlags.load)

    def test_has_is_enabled_method(self):
        """测试有is_enabled方法"""
        from core.feature_flags import FeatureFlags
        assert hasattr(FeatureFlags, 'is_enabled')
        assert callable(FeatureFlags.is_enabled)

    def test_has_flags_dict(self):
        """测试有_flags字典"""
        from core.feature_flags import FeatureFlags
        assert hasattr(FeatureFlags, '_flags')
        assert isinstance(FeatureFlags._flags, dict)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
