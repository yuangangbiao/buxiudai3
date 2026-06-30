# -*- coding: utf-8 -*-
"""
core/_config_ui.py 完整单元测试

覆盖模块:
- ApiKeyConfig
- StyleConfig
- FONTS 字典
- LAYOUT 字典
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest


class TestConfigUiExists:
    """_config_ui 存在性测试"""

    def test_config_ui_module_exists(self):
        """测试_config_ui模块存在"""
        from core import _config_ui
        assert _config_ui is not None


class TestApiKeyConfig:
    """ApiKeyConfig 测试"""

    def test_api_key_config_exists(self):
        """测试ApiKeyConfig类存在"""
        from core._config_ui import ApiKeyConfig
        assert ApiKeyConfig is not None

    def test_inventory_api_key(self):
        """测试INVENTORY_API_KEY"""
        from core._config_ui import ApiKeyConfig
        assert hasattr(ApiKeyConfig, 'INVENTORY_API_KEY')

    def test_wechat_api_key(self):
        """测试WECHAT_API_KEY"""
        from core._config_ui import ApiKeyConfig
        assert hasattr(ApiKeyConfig, 'WECHAT_API_KEY')

    def test_ai_api_key(self):
        """测试AI_API_KEY"""
        from core._config_ui import ApiKeyConfig
        assert hasattr(ApiKeyConfig, 'AI_API_KEY')


class TestStyleConfig:
    """StyleConfig 测试"""

    def test_style_config_exists(self):
        """测试StyleConfig类存在"""
        from core._config_ui import StyleConfig
        assert StyleConfig is not None

    def test_font_family(self):
        """测试字体族"""
        from core._config_ui import StyleConfig
        assert hasattr(StyleConfig, 'FONT_FAMILY')

    def test_font_size(self):
        """测试字号"""
        from core._config_ui import StyleConfig
        assert hasattr(StyleConfig, 'FONT_SIZE_NORMAL')
        assert hasattr(StyleConfig, 'FONT_SIZE_TITLE')
        assert StyleConfig.FONT_SIZE_NORMAL > 0
        assert StyleConfig.FONT_SIZE_TITLE > StyleConfig.FONT_SIZE_NORMAL

    def test_colors(self):
        """测试颜色配置"""
        from core._config_ui import StyleConfig
        assert hasattr(StyleConfig, 'PRIMARY_COLOR')
        assert hasattr(StyleConfig, 'SUCCESS_COLOR')
        assert hasattr(StyleConfig, 'WARNING_COLOR')
        assert hasattr(StyleConfig, 'ERROR_COLOR')
        # 验证是颜色代码格式
        assert StyleConfig.PRIMARY_COLOR.startswith('#')


class TestFontsDict:
    """FONTS 字典测试"""

    def test_fonts_dict_exists(self):
        """测试FONTS字典存在"""
        from core._config_ui import FONTS
        assert FONTS is not None
        assert isinstance(FONTS, dict)

    def test_fonts_has_title(self):
        """测试有title字体"""
        from core._config_ui import FONTS
        assert 'title' in FONTS

    def test_fonts_has_body(self):
        """测试有body字体"""
        from core._config_ui import FONTS
        assert 'body' in FONTS

    def test_fonts_has_small(self):
        """测试有small字体"""
        from core._config_ui import FONTS
        assert 'small' in FONTS

    def test_fonts_count(self):
        """测试字体数量"""
        from core._config_ui import FONTS
        assert len(FONTS) >= 10


class TestLayoutDict:
    """LAYOUT 字典测试"""

    def test_layout_dict_exists(self):
        """测试LAYOUT字典存在"""
        from core._config_ui import LAYOUT
        assert LAYOUT is not None
        assert isinstance(LAYOUT, dict)

    def test_layout_has_padding(self):
        """测试有padding配置"""
        from core._config_ui import LAYOUT
        assert 'padding' in LAYOUT

    def test_layout_has_margin(self):
        """测试有margin配置"""
        from core._config_ui import LAYOUT
        assert 'margin' in LAYOUT

    def test_layout_has_widths(self):
        """测试有widths配置"""
        from core._config_ui import LAYOUT
        assert 'widths' in LAYOUT


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
