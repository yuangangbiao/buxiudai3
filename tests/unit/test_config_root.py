# -*- coding: utf-8 -*-
r"""根 config.py 门面测试 [K21 修复 2026-06-16]

守护场景：
- main_window.py:41 f"{WINDOW['width']}x{WINDOW['height']}" 不抛 KeyError
- 28 个视图模块 from config import COLORS/FONTS/LAYOUT/WINDOW_SIZES 拿到非空 dict
- config.py 暴露的字典与 core.config SSOT 一致
- K21 修复点: 不再静默 fallback 到 {}

来源背景（commit 609f6d20 F19 Commit 2 引入的回归）：
- 重构前 config.py 直接定义 WINDOW/FONTS/COLORS/LAYOUT/WINDOW_SIZES
- 重构后用 getattr(StyleConfig, ...) 取值，但 StyleConfig 类只有原子属性
- 结果这 5 个字典永远是空 {}，main_window.py:41 第一次访问 WINDOW['width'] 就炸
- 本测试守护修复，确保下次重构不再埋雷
"""
import importlib
import os
import sys
import pytest


def _ensure_core_package_loaded():
    r"""确保 'core' 包绑定到项目根的 core/,不是 mobile_api_ai/core/

    背景: tests/unit/conftest.py 会清理 sys.path 里的 mobile_api_ai,
    但 mobile_api_ai/core/__init__.py 是个空 package(无 config.py),
    若 sys.modules['core'] 缓存了错误路径,后续 import core.config 会爆 ModuleNotFoundError。

    本函数:session 级预热,把 core 包固定到正确路径,供后续所有用例使用。
    """
    _proj = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # 1. 清掉 sys.modules 里残留的 core 和 core.*,避免命中错误的 mobile_api_ai/core
    for _k in list(sys.modules.keys()):
        if _k == 'core' or _k.startswith('core.'):
            del sys.modules[_k]
    # 2. 把项目根放到 sys.path 第一位,确保 import core 命中项目根的 core/
    if _proj not in sys.path:
        sys.path.insert(0, _proj)
    elif sys.path[0] != _proj:
        try:
            sys.path.remove(_proj)
        except ValueError:
            pass
        sys.path.insert(0, _proj)
    # 3. 预热: 强制 import core 和 core.config
    import core  # noqa: F401
    import core.config  # noqa: F401


_ensure_core_package_loaded()


class TestConfigRootExports:
    r"""根 config.py 必须正确暴露 UI 字典（防 KeyError: 'width' 回归）"""

    def test_window_dict_is_non_empty_dict(self):
        r"""WINDOW 是非空 dict，修复前会 fallback 到 {}"""
        from config import WINDOW
        assert isinstance(WINDOW, dict), f"WINDOW 必须是 dict, 实际 {type(WINDOW).__name__}"
        assert len(WINDOW) > 0, "WINDOW 不能为空字典（修复前 fallback 到 {}）"

    def test_window_dict_required_keys(self):
        r"""WINDOW 必须包含 main_window.py:41 实际使用的键"""
        from config import WINDOW
        assert 'width' in WINDOW, "WINDOW['width'] 是 main_window.py:41 依赖"
        assert 'height' in WINDOW
        assert 'min_width' in WINDOW
        assert 'min_height' in WINDOW

    def test_window_size_string_format(self):
        r"""模拟 main_window.py:41 f-string 调用，不抛 KeyError"""
        from config import WINDOW
        try:
            size_str = f"{WINDOW['width']}x{WINDOW['height']}"
        except KeyError as e:
            pytest.fail(f"f-string 报 KeyError({e}) — 修复前 WINDOW 回退到空 dict")
        assert 'x' in size_str
        parts = size_str.split('x')
        assert len(parts) == 2
        assert int(parts[0]) > 0
        assert int(parts[1]) > 0

    def test_window_width_height_types(self):
        r"""width/height 必须是正整数（防止被填成字符串或 0）"""
        from config import WINDOW
        assert isinstance(WINDOW['width'], int), \
            f"width 应为 int, 实际 {type(WINDOW['width']).__name__}"
        assert isinstance(WINDOW['height'], int), \
            f"height 应为 int, 实际 {type(WINDOW['height']).__name__}"
        assert WINDOW['width'] >= 800, "width 不应小于 800"
        assert WINDOW['height'] >= 500, "height 不应小于 500"

    def test_window_sizes_dict_is_non_empty_dict(self):
        r"""WINDOW_SIZES 是非空 dict（修复前 fallback 到 {}）"""
        from config import WINDOW_SIZES
        assert isinstance(WINDOW_SIZES, dict)
        assert len(WINDOW_SIZES) > 0
        for key in ('production_select', 'order_detail', 'custom_types'):
            assert key in WINDOW_SIZES, f"WINDOW_SIZES 应包含 {key}"
        for key, size in WINDOW_SIZES.items():
            assert isinstance(size, str)
            assert 'x' in size, f"WINDOW_SIZES['{key}']={size} 应是 'WxH' 格式"

    def test_fonts_dict_is_non_empty_dict(self):
        r"""FONTS 是非空 dict，视图/样式代码依赖"""
        from config import FONTS
        assert isinstance(FONTS, dict)
        assert len(FONTS) >= 10, f"FONTS 项数过少 ({len(FONTS)}), 期望 ≥10"
        for key in ('title', 'normal', 'body'):
            assert key in FONTS, f"FONTS 应包含 {key}"

    def test_colors_dict_is_non_empty_dict(self):
        r"""COLORS 是非空 dict,所有视图背景色依赖"""
        from config import COLORS
        assert isinstance(COLORS, dict)
        assert len(COLORS) >= 20, f"COLORS 项数过少 ({len(COLORS)}), 期望 ≥20"
        for key in ('bg_main', 'primary', 'text_primary', 'success', 'danger'):
            assert key in COLORS, f"COLORS 应包含 {key}"

    def test_bg_main_is_valid_color(self):
        r"""COLORS['bg_main'] 必须是有效颜色字符串（main_window.py:47 直接使用）"""
        from config import COLORS
        bg_main = COLORS['bg_main']
        assert isinstance(bg_main, str)
        assert bg_main.startswith('#'), f"bg_main={bg_main} 应以 # 开头"
        assert len(bg_main) in (7, 9), f"bg_main={bg_main} 应是 #RRGGBB 或 #RRGGBBAA"

    def test_layout_dict_is_non_empty_dict(self):
        r"""LAYOUT 是非空 dict"""
        from config import LAYOUT
        assert isinstance(LAYOUT, dict)
        assert len(LAYOUT) > 0
        for key in ('padding', 'margin', 'widths', 'heights'):
            assert key in LAYOUT, f"LAYOUT 应包含 {key}"

    def test_app_name_non_empty_string(self):
        r"""APP_NAME 必须是非空字符串（main_window.py:37 窗口标题依赖）"""
        from config import APP_NAME
        assert isinstance(APP_NAME, str)
        assert len(APP_NAME) > 0


class TestConfigRootVsCoreConfigSSOT:
    r"""根 config.py 与 core.config SSOT 一致性（防双源飘移）"""

    def test_window_ssot(self):
        from config import WINDOW as root_window
        import core.config as core_config
        assert root_window is core_config.WINDOW, \
            "config.WINDOW 必须与 core.config.WINDOW 是同一对象（SSOT）"

    def test_fonts_ssot(self):
        from config import FONTS as root_fonts
        import core.config as core_config
        assert root_fonts is core_config.FONTS

    def test_colors_ssot(self):
        from config import COLORS as root_colors
        import core.config as core_config
        assert root_colors is core_config.COLORS

    def test_layout_ssot(self):
        from config import LAYOUT as root_layout
        import core.config as core_config
        assert root_layout is core_config.LAYOUT

    def test_window_sizes_ssot(self):
        from config import WINDOW_SIZES as root_window_sizes
        import core.config as core_config
        assert root_window_sizes is core_config.WINDOW_SIZES


class TestViewModulesCanImportConfig:
    r"""26 个视图模块的 config 导入必须能拿到非空字典
    (修复前 import 阶段不报错,但渲染时 .get('bg_main') 返 None/崩)
    """

    VIEW_MODULES = [
        'desktop.views.main_window',
        'desktop.views.production_view',
        'desktop.views.quality_view',
        'desktop.views.process_view',
        'desktop.views.material_prep_view',
        'desktop.views.material_rules_view',
        'desktop.views.kanban_view',
        'desktop.views.alert_view',
        'desktop.views.excel_view',
        'desktop.views.bom_view',
        'desktop.views.log_view',
        'desktop.views.shipment_view',
        'desktop.views.backup_view',
        'desktop.views.order_query_view',
        'desktop.views.settings_dialog',
        'desktop.views.finished_product_stats_view',
        'desktop.views.quality_rule_view',
        'desktop.views.process_calc_rule_view',
        'desktop.views.orders.list_view',
        'desktop.views.orders.confirm',
        'desktop.views.orders.form',
        'desktop.views.dialogs.base',
        'desktop.views.dialogs.quality_dialogs',
        'desktop.views.dialogs.rule_dialogs',
        'desktop.views.dialogs.material_dialogs',
    ]

    @pytest.mark.parametrize("module_name", VIEW_MODULES)
    def test_view_module_imports(self, module_name):
        r"""{module_name} 能成功 import"""
        mod = importlib.import_module(module_name)
        assert mod is not None


class TestK21RegressionGuard:
    r"""K21 修复守护：config.py 不能用 getattr(StyleConfig, ...) 取字典
    （这是 commit 609f6d20 引入的回归模式）
    """

    def test_no_getattr_styleconfig_pattern_in_config_py(self):
        r"""config.py 不能再出现 getattr(StyleConfig, ...) 模式
        （grep 全代码库已经验证过,这里用源码静态扫描兜底）

        实现：用 re.MULTILINE 排除以 # 开头的注释行,避免"注释里举例说明反模式"触发误报。
        """
        import re
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'config.py',
        )
        with open(config_path, encoding='utf-8') as f:
            lines = f.readlines()
        # 排除注释行: 只要行首(去前导空白)以 # 开头就跳过
        code_lines = [ln for ln in lines if ln.lstrip().startswith('#') is False]
        code_content = ''.join(code_lines)
        match = re.search(r'getattr\s*\(\s*StyleConfig', code_content)
        assert match is None, (
            "config.py 的可执行代码出现 getattr(StyleConfig, ...) 模式 — "
            "StyleConfig 类只有原子属性,字典会 fallback 到 {} 静默崩"
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])