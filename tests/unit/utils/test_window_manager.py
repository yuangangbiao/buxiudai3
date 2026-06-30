# -*- coding: utf-8 -*-
"""测试 window_manager.py - 窗口大小管理（13.73% → ~95%）"""
import sys, os, json, pytest
from unittest.mock import patch, MagicMock, mock_open


class TestGetWindowConfigPath:
    def test_returns_path_from_config(self):
        """get_window_config_path 返回 DB_PATHS 中的路径"""
        from utils.window_manager import get_window_config_path
        # DB_PATHS 有配置
        with patch('utils.window_manager.DB_PATHS', {'window_config': '/fake/config.json'}):
            assert get_window_config_path() == '/fake/config.json'


class TestLoadWindowSize:
    def test_load_existing_config(self, tmp_path):
        """配置文件存在且包含该窗口的尺寸"""
        cfg = tmp_path / 'win_cfg.json'
        cfg.write_text(json.dumps({"main": "1024x768"}), encoding='utf-8')
        from utils.window_manager import load_window_size
        with patch('utils.window_manager.DB_PATHS', {'window_config': str(cfg)}):
            size = load_window_size("main", "800x600")
            assert size == "1024x768"

    def test_load_nonexistent_key_returns_default(self, tmp_path):
        """配置文件存在但找不到该窗口的 key"""
        cfg = tmp_path / 'win_cfg.json'
        cfg.write_text(json.dumps({"other": "400x300"}), encoding='utf-8')
        from utils.window_manager import load_window_size
        with patch('utils.window_manager.DB_PATHS', {'window_config': str(cfg)}):
            size = load_window_size("main", "800x600")
            assert size == "800x600"

    def test_load_no_config_file(self):
        """配置文件不存在，返回默认值"""
        from utils.window_manager import load_window_size
        with patch('utils.window_manager.DB_PATHS', {'window_config': '/nonexistent/cfg.json'}):
            size = load_window_size("main", "1024x768")
            assert size == "1024x768"

    def test_load_corrupted_json_returns_default(self, tmp_path):
        """配置文件损坏（非 JSON），返回默认值"""
        cfg = tmp_path / 'corrupt.json'
        cfg.write_text("this is not json", encoding='utf-8')
        from utils.window_manager import load_window_size
        with patch('utils.window_manager.DB_PATHS', {'window_config': str(cfg)}):
            size = load_window_size("main", "800x600")
            assert size == "800x600"


class TestSaveWindowSize:
    def test_save_new_key(self, tmp_path):
        """保存新窗口尺寸到新配置文件"""
        cfg = tmp_path / 'win_cfg.json'
        cfg.parent.mkdir(parents=True, exist_ok=True)
        from utils.window_manager import save_window_size
        with patch('utils.window_manager.DB_PATHS', {'window_config': str(cfg)}):
            save_window_size("main", "1024x768")
            data = json.loads(cfg.read_text(encoding='utf-8'))
            assert data["main"] == "1024x768"

    def test_save_append_to_existing(self, tmp_path):
        """追加到已有配置文件"""
        cfg = tmp_path / 'win_cfg.json'
        cfg.write_text(json.dumps({"win1": "800x600"}), encoding='utf-8')
        from utils.window_manager import save_window_size
        with patch('utils.window_manager.DB_PATHS', {'window_config': str(cfg)}):
            save_window_size("win2", "1200x800")
            data = json.loads(cfg.read_text(encoding='utf-8'))
            assert data["win1"] == "800x600"
            assert data["win2"] == "1200x800"

    def test_save_update_existing_key(self, tmp_path):
        """更新已有窗口尺寸"""
        cfg = tmp_path / 'win_cfg.json'
        cfg.write_text(json.dumps({"main": "800x600"}), encoding='utf-8')
        from utils.window_manager import save_window_size
        with patch('utils.window_manager.DB_PATHS', {'window_config': str(cfg)}):
            save_window_size("main", "1920x1080")
            data = json.loads(cfg.read_text(encoding='utf-8'))
            assert data["main"] == "1920x1080"

    def test_save_creates_directory(self, tmp_path):
        """保存时自动创建目录"""
        cfg = tmp_path / 'sub' / 'deep' / 'cfg.json'
        from utils.window_manager import save_window_size
        with patch('utils.window_manager.DB_PATHS', {'window_config': str(cfg)}):
            save_window_size("main", "800x600")
            assert cfg.exists()


class TestSetupResizableWindow:
    """测试 setup_resizable_window（更复杂，因为涉及 tkinter）"""

    def test_no_position_info_centers_window(self):
        """saved_size 不含位置信息，居中窗口"""
        from utils.window_manager import setup_resizable_window

        mock_win = MagicMock()
        mock_win.geometry.return_value = ""
        mock_win.winfo_screenwidth.return_value = 1920
        mock_win.winfo_screenheight.return_value = 1080

        with patch('utils.window_manager.load_window_size', return_value="800x600"):
            setup_resizable_window(mock_win, "test_win")

        mock_win.resizable.assert_called_once_with(True, True)
        # 验证居中几何参数
        set_geo = mock_win.geometry.call_args_list[0][0][0]
        # 800x600+560+240 = (1920-800)/2 和 (1080-600)/2
        assert set_geo == "800x600+560+240"

    def test_geometry_parse_fallback(self):
        """解析 geometry 失败时回退到默认值"""
        from utils.window_manager import setup_resizable_window

        mock_win = MagicMock()
        mock_win.winfo_screenwidth.return_value = 1920
        mock_win.winfo_screenheight.return_value = 1080

        with patch('utils.window_manager.load_window_size', return_value=None):
            setup_resizable_window(mock_win, "test_win")

        # 默认 800x600
        set_geo = mock_win.geometry.call_args_list[0][0][0]
        assert "800x600" in set_geo

    def test_on_resize_saves(self):
        """resize 事件触发保存"""
        from utils.window_manager import setup_resizable_window

        mock_win = MagicMock()
        mock_win.geometry.return_value = "1024x768+100+50"

        with patch('utils.window_manager.load_window_size', return_value="1024x768"):
            with patch('utils.window_manager.save_window_size') as mock_save:
                setup_resizable_window(mock_win, "test_win")

                # 触发绑定的 <Configure> 回调
                event = MagicMock()
                event.widget = mock_win
                bind_call = mock_win.bind.call_args_list[0]
                func = bind_call[0][1]
                func(event)

                mock_save.assert_called_once_with("test_win", "1024x768+100+50")
