# -*- coding: utf-8 -*-
"""
utils/settings_manager.py 测试 - 覆盖缺口: L76-77 (save_settings 异常分支)
"""
import pytest
import os
from unittest.mock import patch, MagicMock


class TestSettingsManagerSave:
    """save_settings 异常分支测试 - 覆盖 L76-77"""

    def test_save_settings_success(self, tmp_path):
        """成功保存"""
        from utils.settings_manager import SettingsManager, DEFAULT_COLORS, DEFAULT_FONTS

        settings_file = tmp_path / "settings.json"
        with patch('utils.settings_manager.SETTINGS_FILE', str(settings_file)):
            sm = SettingsManager.__new__(SettingsManager)
            sm.settings = {
                "colors": DEFAULT_COLORS.copy(),
                "fonts": DEFAULT_FONTS.copy()
            }
            result = sm.save_settings()
            assert result is True
            assert settings_file.exists()

    def test_save_settings_io_error(self, tmp_path):
        """保存失败（IO异常）"""
        from utils.settings_manager import SettingsManager, DEFAULT_COLORS, DEFAULT_FONTS

        settings_file = tmp_path / "settings.json"
        with patch('utils.settings_manager.SETTINGS_FILE', str(settings_file)):
            with patch('builtins.open', side_effect=IOError("磁盘已满")):
                sm = SettingsManager.__new__(SettingsManager)
                sm.settings = {"colors": DEFAULT_COLORS.copy(), "fonts": DEFAULT_FONTS.copy()}
                result = sm.save_settings()
                assert result is False

    def test_save_settings_exception(self, tmp_path):
        """保存失败（其他异常）"""
        from utils.settings_manager import SettingsManager, DEFAULT_COLORS, DEFAULT_FONTS

        settings_file = tmp_path / "settings.json"
        with patch('utils.settings_manager.SETTINGS_FILE', str(settings_file)):
            with patch('builtins.open', side_effect=Exception("未知错误")):
                sm = SettingsManager.__new__(SettingsManager)
                sm.settings = {"colors": DEFAULT_COLORS.copy(), "fonts": DEFAULT_FONTS.copy()}
                result = sm.save_settings()
                assert result is False


class TestSettingsManagerLoad:
    """_load_settings 各种场景测试"""

    def test_load_settings_missing_file(self, tmp_path):
        """文件不存在时使用默认设置"""
        from utils.settings_manager import SettingsManager, DEFAULT_COLORS, DEFAULT_FONTS

        missing_file = tmp_path / "nonexistent.json"
        with patch('utils.settings_manager.SETTINGS_FILE', str(missing_file)):
            sm = SettingsManager.__new__(SettingsManager)
            sm._load_settings()
            assert "colors" in sm.settings
            assert "fonts" in sm.settings
            # 默认颜色应存在
            assert sm.settings["colors"].get("primary") == DEFAULT_COLORS["primary"]

    def test_load_settings_corrupt_json(self, tmp_path):
        """文件损坏时使用默认设置"""
        from utils.settings_manager import SettingsManager

        corrupt_file = tmp_path / "corrupt.json"
        corrupt_file.write_text("{ invalid json", encoding='utf-8')

        with patch('utils.settings_manager.SETTINGS_FILE', str(corrupt_file)):
            sm = SettingsManager.__new__(SettingsManager)
            sm._load_settings()
            assert "colors" in sm.settings


class TestSettingsManagerDefaults:
    """默认设置测试"""

    def test_default_colors_has_required_keys(self):
        from utils.settings_manager import DEFAULT_COLORS
        required = ["primary", "bg_main", "text_primary", "success", "warning", "danger"]
        for key in required:
            assert key in DEFAULT_COLORS

    def test_default_fonts_has_required_keys(self):
        from utils.settings_manager import DEFAULT_FONTS
        assert "family" in DEFAULT_FONTS
        assert "size" in DEFAULT_FONTS
        assert "title" in DEFAULT_FONTS["size"]

    def test_settings_manager_singleton(self):
        """单例模式"""
        from utils.settings_manager import SettingsManager
        instance1 = SettingsManager()
        instance2 = SettingsManager()
        assert instance1 is instance2
