# -*- coding: utf-8 -*-
"""冲刺30% - settings_manager"""
import pytest


class TestSettingsManager:
    def test_singleton(self):
        from utils.settings_manager import SettingsManager
        sm1 = SettingsManager()
        sm2 = SettingsManager()
        assert sm1 is sm2

    def test_get_color_returns_string(self):
        from utils.settings_manager import SettingsManager
        sm = SettingsManager()
        c = sm.get_color("primary")
        assert isinstance(c, str)
        assert c.startswith("#")

    def test_get_color_unknown(self):
        from utils.settings_manager import SettingsManager
        sm = SettingsManager()
        assert sm.get_color("nonexistent_xyz") == "#000000"

    def test_set_valid_color(self):
        from utils.settings_manager import SettingsManager
        sm = SettingsManager()
        assert sm.set_color("primary", "#FFFFFF") is True

    def test_set_invalid_color(self):
        from utils.settings_manager import SettingsManager
        sm = SettingsManager()
        assert sm.set_color("not_a_color_xyz", "#000") is False

    def test_font_size(self):
        from utils.settings_manager import SettingsManager
        sm = SettingsManager()
        assert isinstance(sm.get_font_size("title"), int)
        assert sm.get_font_size("unknown_size_type") == 10

    def test_set_font_size(self):
        from utils.settings_manager import SettingsManager
        sm = SettingsManager()
        assert sm.set_font_size("title", 20) is True
        assert sm.set_font_size("invalid_size", 99) is False

    def test_font_family(self):
        from utils.settings_manager import SettingsManager
        sm = SettingsManager()
        assert isinstance(sm.get_font_family(), str)
        assert sm.set_font_family("宋体") is True

    def test_get_all_colors(self):
        from utils.settings_manager import SettingsManager
        sm = SettingsManager()
        colors = sm.get_all_colors()
        assert isinstance(colors, dict)
        assert len(colors) > 0

    def test_get_all_fonts(self):
        from utils.settings_manager import SettingsManager
        sm = SettingsManager()
        fonts = sm.get_all_fonts()
        assert isinstance(fonts, dict)
        assert "family" in fonts

    def test_reset_to_default(self):
        from utils.settings_manager import SettingsManager
        sm = SettingsManager()
        sm.set_color("primary", "#000000")
        sm.reset_to_default()
        c = sm.get_color("primary")
        assert isinstance(c, str)
