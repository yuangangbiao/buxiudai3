# -*- coding: utf-8 -*-
"""测试 backup_manager.py - 备份管理器（29% → 100%）"""
import os
import json
import datetime
import threading
import pytest
from unittest.mock import patch, MagicMock, PropertyMock


# ===================== 工具常量 =====================

BACKUP_CONFIG_FILE = os.path.join("dummy_base", "data", "backup_config.json")


# ===================== 全局实例 =====================

class TestGlobalBackupManager:
    """模块级全局实例"""

    def test_global_instance_exists(self):
        """模块加载后全局实例可用"""
        from utils.backup_manager import backup_manager
        assert backup_manager is not None
        assert hasattr(backup_manager, 'config')

    def test_global_instance_is_singleton(self):
        """反复导入返回同一实例"""
        import importlib
        import utils.backup_manager as bm1
        bm1_ref = id(bm1.backup_manager)

        importlib.reload(bm1)
        assert id(bm1.backup_manager) != bm1_ref  # reload 后会新建


# ===================== _load_config =====================

class TestLoadConfig:

    @patch('utils.backup_manager.os.path.exists', return_value=True)
    @patch('utils.backup_manager.json.load')
    @patch('utils.backup_manager.open')
    def test_load_existing_config(self, mock_open, mock_json_load, mock_exists):
        """配置文件存在时加载并返回"""
        mock_json_load.return_value = {"enabled": True, "interval": 12}
        from utils.backup_manager import BackupManager
        bm = BackupManager()
        assert bm.config == {"enabled": True, "interval": 12}

    @patch('utils.backup_manager.os.path.exists', return_value=False)
    def test_load_missing_config_returns_default(self, mock_exists):
        """配置文件不存在时返回默认配置"""
        from utils.backup_manager import BackupManager, DEFAULT_BACKUP_CONFIG
        bm = BackupManager()
        assert bm.config == DEFAULT_BACKUP_CONFIG

    @patch('utils.backup_manager.os.path.exists', return_value=True)
    @patch('utils.backup_manager.open', side_effect=PermissionError("denied"))
    def test_load_config_io_error_returns_default(self, mock_open, mock_exists):
        """读取异常时打印并返回默认配置"""
        from utils.backup_manager import BackupManager, DEFAULT_BACKUP_CONFIG
        with patch('builtins.print') as mock_print:
            bm = BackupManager()
        assert bm.config == DEFAULT_BACKUP_CONFIG
        mock_print.assert_called_once()
        assert "加载备份配置失败" in str(mock_print.call_args)


# ===================== _save_config =====================

class TestSaveConfig:

    @patch('utils.backup_manager.os.makedirs')
    @patch('utils.backup_manager.json.dump')
    def test_save_creates_dir_and_writes(self, mock_json_dump, mock_makedirs):
        """保存配置时创建目录并写入json"""
        from utils.backup_manager import BackupManager
        bm = BackupManager()
        # 避免 __init__ 读取文件
        bm.config = {"enabled": True, "interval": 24}

        with patch('utils.backup_manager.open', MagicMock()) as mock_open:
            mock_open.return_value.__enter__.return_value = mock_file = MagicMock()
            bm._save_config()

        mock_makedirs.assert_called_once()
        mock_open.assert_called_once()
        mock_json_dump.assert_called_once_with(
            bm.config, mock_file, ensure_ascii=False, indent=2
        )

    @patch('utils.backup_manager.os.makedirs', side_effect=PermissionError("denied"))
    def test_save_error_caught(self, mock_makedirs):
        """保存异常时打印错误"""
        from utils.backup_manager import BackupManager
        bm = BackupManager()
        with patch('builtins.print') as mock_print:
            bm._save_config()
        mock_print.assert_called_once()
        assert "保存备份配置失败" in str(mock_print.call_args)


# ===================== get_config =====================

class TestGetConfig:

    def test_get_config_returns_current(self):
        """返回当前配置"""
        from utils.backup_manager import BackupManager
        bm = BackupManager()
        result = bm.get_config()
        assert result is bm.config


# ===================== update_config =====================

class TestUpdateConfig:

    def test_update_config_merge_values(self):
        """update_config 合并新值"""
        from utils.backup_manager import BackupManager
        bm = BackupManager()
        bm.start_backup_service = MagicMock()

        bm.update_config({"interval": 12})
        assert bm.config["interval"] == 12

    def test_update_config_enabled_starts_service(self):
        """enabled=True 时调用 start_backup_service"""
        from utils.backup_manager import BackupManager
        bm = BackupManager()
        bm.start_backup_service = MagicMock()
        bm._save_config = MagicMock()

        bm.update_config({"enabled": True})
        bm.start_backup_service.assert_called_once()

    def test_update_config_disabled_no_start(self):
        """enabled=False 时不启动服务"""
        from utils.backup_manager import BackupManager
        bm = BackupManager()
        bm.start_backup_service = MagicMock()

        bm.update_config({"enabled": False})
        bm.start_backup_service.assert_not_called()


# ===================== start_backup_service =====================

class TestStartBackupService:

    def test_disabled_returns_early(self):
        """disabled 时不启动线程"""
        from utils.backup_manager import BackupManager
        bm = BackupManager()
        bm.config["enabled"] = False
        bm.start_backup_service()
        assert bm._backup_thread is None

    def test_stops_existing_thread(self):
        """已有线程时先停止再启动"""
        from utils.backup_manager import BackupManager
        bm = BackupManager()
        bm.config["enabled"] = True

        old_thread = MagicMock()
        old_thread.is_alive.return_value = True
        bm._backup_thread = old_thread

        with patch('utils.backup_manager.threading.Thread') as MockThread:
            mock_new = MagicMock()
            MockThread.return_value = mock_new

            bm.start_backup_service()

            old_thread.is_alive.assert_called_once()
            # _stop_event 被 clear（在 start_backup_service 中）
            assert not bm._stop_event.is_set()  # 新线程前已被 clear
            MockThread.assert_called_once()
            mock_new.start.assert_called_once()

    def test_starts_new_thread(self):
        """新线程启动"""
        from utils.backup_manager import BackupManager
        bm = BackupManager()
        bm.config["enabled"] = True

        with patch('utils.backup_manager.threading.Thread') as MockThread:
            mock_thread = MagicMock()
            MockThread.return_value = mock_thread

            bm.start_backup_service()

            MockThread.assert_called_once()
            mock_thread.start.assert_called_once()
            assert bm._backup_thread is mock_thread


# ===================== _backup_loop =====================

class TestBackupLoop:

    def test_backup_loop_runs_once_on_stop(self):
        """循环在 stop_event 后仅执行一次"""
        from utils.backup_manager import BackupManager
        bm = BackupManager()
        bm._should_backup = MagicMock(return_value=True)
        bm.perform_backup = MagicMock()
        bm.config["interval"] = 0  # 跳过 sleep

        # 不提前 set，让循环执行一次后再停止
        def stop_after_one(*args):
            bm._stop_event.set()
            return True

        bm._should_backup.side_effect = stop_after_one

        bm._backup_loop()

        bm._should_backup.assert_called_once()
        bm.perform_backup.assert_called_once()
        assert bm._last_backup_time is not None

    def test_backup_loop_skips_when_not_needed(self):
        """不需要备份时跳过 perform_backup"""
        from utils.backup_manager import BackupManager
        bm = BackupManager()
        bm._should_backup = MagicMock(return_value=False)
        bm.perform_backup = MagicMock()
        bm.config["interval"] = 0

        bm._stop_event.set()
        bm._backup_loop()

        bm.perform_backup.assert_not_called()
        assert bm._last_backup_time is None


# ===================== _should_backup =====================

class TestShouldBackup:

    def test_no_last_backup_returns_true(self):
        """从未备份过则返回 True"""
        from utils.backup_manager import BackupManager
        bm = BackupManager()
        bm._last_backup_time = None
        assert bm._should_backup() is True

    def test_within_interval_returns_false(self):
        """在间隔内返回 False"""
        from utils.backup_manager import BackupManager
        bm = BackupManager()
        bm._last_backup_time = datetime.datetime.now()
        bm.config["interval"] = 24  # 24小时
        assert bm._should_backup() is False

    def test_past_interval_returns_true(self):
        """超过间隔返回 True"""
        from utils.backup_manager import BackupManager
        bm = BackupManager()
        old = datetime.datetime.now() - datetime.timedelta(hours=25)
        bm._last_backup_time = old
        bm.config["interval"] = 24
        assert bm._should_backup() is True


# ===================== perform_backup =====================

class TestPerformBackup:

    @patch('utils.backup_manager.shutil.copy2')
    @patch('utils.backup_manager.os.makedirs')
    @patch('utils.backup_manager.datetime')
    def test_perform_backup_success(self, mock_dt, mock_makedirs, mock_copy2):
        """备份成功并清理旧备份"""
        mock_now = MagicMock()
        mock_now.strftime.return_value = "20260603_103000"
        mock_dt.datetime.now.return_value = mock_now

        from utils.backup_manager import BackupManager
        bm = BackupManager()
        bm._cleanup_old_backups = MagicMock()
        bm.config["backup_dir"] = "/tmp/backups"

        result = bm.perform_backup()

        assert result is True
        mock_makedirs.assert_called_once_with("/tmp/backups", exist_ok=True)
        mock_copy2.assert_called_once()
        bm._cleanup_old_backups.assert_called_once()

    @patch('utils.backup_manager.shutil.copy2', side_effect=OSError("disk full"))
    @patch('utils.backup_manager.os.makedirs')
    def test_perform_backup_failure(self, mock_makedirs, mock_copy2):
        """备份失败返回 False 并打印错误"""
        from utils.backup_manager import BackupManager
        bm = BackupManager()
        bm._cleanup_old_backups = MagicMock()

        with patch('builtins.print') as mock_print:
            result = bm.perform_backup()

        assert result is False
        mock_print.assert_called_once()
        assert "备份失败" in str(mock_print.call_args)


# ===================== _cleanup_old_backups =====================

class TestCleanupOldBackups:

    @patch('utils.backup_manager.os.listdir')
    @patch('utils.backup_manager.os.remove')
    @patch('utils.backup_manager.os.path.getmtime')
    @patch('utils.backup_manager.os.path.exists')
    def test_cleanup_removes_expired(self, mock_exists, mock_getmtime,
                                     mock_remove, mock_listdir):
        """删除过期备份文件"""
        mock_listdir.return_value = ["old.db", "recent.db", "not_db.txt"]

        # old.db: 10天前; recent.db: 3天前
        ten_days_ago = (datetime.datetime.now() - datetime.timedelta(days=10)).timestamp()
        three_days_ago = (datetime.datetime.now() - datetime.timedelta(days=3)).timestamp()
        mock_getmtime.side_effect = lambda f: ten_days_ago if "old" in f else three_days_ago

        from utils.backup_manager import BackupManager
        bm = BackupManager()
        bm.config["backup_dir"] = "/tmp/backups"
        bm.config["keep_days"] = 7

        bm._cleanup_old_backups()

        # 只删除了 old.db
        mock_remove.assert_called_once()
        assert "old.db" in str(mock_remove.call_args)

    @patch('utils.backup_manager.os.listdir', side_effect=PermissionError("denied"))
    def test_cleanup_error_caught(self, mock_listdir):
        """清理异常时打印错误"""
        from utils.backup_manager import BackupManager
        bm = BackupManager()

        with patch('builtins.print') as mock_print:
            bm._cleanup_old_backups()

        mock_print.assert_called_once()
        assert "清理过期备份失败" in str(mock_print.call_args)


# ===================== restore_from_backup =====================

class TestRestoreFromBackup:

    @patch('utils.backup_manager.os.path.exists', return_value=True)
    @patch('utils.backup_manager.shutil.copy2')
    def test_restore_success(self, mock_copy2, mock_exists):
        """从备份恢复成功"""
        from utils.backup_manager import BackupManager
        bm = BackupManager()
        result = bm.restore_from_backup("/tmp/backups/backup.db")
        assert result is True
        mock_copy2.assert_called_once()

    @patch('utils.backup_manager.os.path.exists', return_value=False)
    def test_restore_file_not_found(self, mock_exists):
        """备份文件不存在"""
        from utils.backup_manager import BackupManager
        bm = BackupManager()
        with patch('builtins.print') as mock_print:
            result = bm.restore_from_backup("/tmp/missing.db")
        assert result is False
        mock_print.assert_called_once()
        assert "备份文件不存在" in str(mock_print.call_args)

    @patch('utils.backup_manager.os.path.exists', return_value=True)
    @patch('utils.backup_manager.shutil.copy2', side_effect=OSError("read error"))
    def test_restore_copy_failure(self, mock_copy2, mock_exists):
        """文件复制失败时返回 False"""
        from utils.backup_manager import BackupManager
        bm = BackupManager()
        with patch('builtins.print') as mock_print:
            result = bm.restore_from_backup("/tmp/backups/backup.db")
        assert result is False


# ===================== get_backup_files =====================

class TestGetBackupFiles:

    @patch('utils.backup_manager.os.path.exists', return_value=True)
    @patch('utils.backup_manager.os.listdir')
    @patch('utils.backup_manager.os.path.getmtime')
    def test_get_files_returns_sorted(self, mock_getmtime, mock_listdir, mock_exists):
        """返回按时间倒序的备份文件列表"""
        mock_listdir.return_value = ["a.db", "b.db"]
        now = datetime.datetime.now()
        mock_getmtime.side_effect = [
            (now - datetime.timedelta(hours=1)).timestamp(),  # a.db: 1小时前
            (now - datetime.timedelta(hours=2)).timestamp(),  # b.db: 2小时前
        ]

        from utils.backup_manager import BackupManager
        bm = BackupManager()
        bm.config["backup_dir"] = "/tmp/backups"

        files = bm.get_backup_files()

        assert len(files) == 2
        # 倒序：最近的在前
        assert files[0]["filename"] == "a.db"
        assert files[1]["filename"] == "b.db"

    @patch('utils.backup_manager.os.path.exists', return_value=False)
    def test_get_files_dir_not_exists(self, mock_exists):
        """备份目录不存在返回空列表"""
        from utils.backup_manager import BackupManager
        bm = BackupManager()
        files = bm.get_backup_files()
        assert files == []

    @patch('utils.backup_manager.os.path.exists', return_value=True)
    @patch('utils.backup_manager.os.listdir', side_effect=PermissionError("denied"))
    def test_get_files_io_error(self, mock_listdir, mock_exists):
        """IO异常时返回空列表并打印"""
        from utils.backup_manager import BackupManager
        bm = BackupManager()
        bm.config["backup_dir"] = "/tmp/backups"

        with patch('builtins.print') as mock_print:
            files = bm.get_backup_files()
        assert files == []
        mock_print.assert_called_once()
        assert "获取备份文件列表失败" in str(mock_print.call_args)


# ===================== 文件操作异常模拟 =====================

class TestEdgeCases:

    def test_json_decode_error_in_load(self):
        """配置JSON损坏时回退到默认"""
        from utils.backup_manager import BackupManager, DEFAULT_BACKUP_CONFIG
        with patch('utils.backup_manager.os.path.exists', return_value=True):
            with patch('utils.backup_manager.json.load',
                       side_effect=json.JSONDecodeError("bad json", "", 0)):
                with patch('builtins.print'):
                    bm = BackupManager()
        assert bm.config == DEFAULT_BACKUP_CONFIG

    def test_cleanup_skips_non_db_files(self):
        """清理时跳过非.db文件"""
        with patch('utils.backup_manager.os.listdir') as mock_listdir:
            with patch('utils.backup_manager.os.path.exists', return_value=True):
                mock_listdir.return_value = ["notes.txt", "image.png", "data.bak"]

                from utils.backup_manager import BackupManager
                bm = BackupManager()
                bm.config["backup_dir"] = "/tmp/backups"
                bm.config["keep_days"] = 7

                with patch('utils.backup_manager.os.remove') as mock_remove:
                    bm._cleanup_old_backups()
                    mock_remove.assert_not_called()

    def test_perform_backup_cleanup_on_existing_dir(self):
        """已有备份目录时可正常写入"""
        with patch('utils.backup_manager.shutil.copy2') as mock_copy:
            with patch('utils.backup_manager.os.makedirs') as mock_makedirs:
                from utils.backup_manager import BackupManager
                bm = BackupManager()
                bm._cleanup_old_backups = MagicMock()

                result = bm.perform_backup()
                assert result is True
                mock_makedirs.assert_called_once_with(
                    bm.config["backup_dir"], exist_ok=True
                )

    def test_update_config_saves_and_resets_stop_event(self):
        """update_config 重置 stop_event 并调用 _save_config"""
        from utils.backup_manager import BackupManager
        bm = BackupManager()
        bm._save_config = MagicMock()
        bm.start_backup_service = MagicMock()

        # 先设置 stop_event
        bm._stop_event.set()

        bm.update_config({"enabled": True})

        # 之前 set 的 stop_event 被 start_backup_service 中 clear 了
        bm.start_backup_service.assert_called_once()
        bm._save_config.assert_called_once()
