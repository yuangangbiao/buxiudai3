# -*- coding: utf-8 -*-
"""精准补21行 → 30% - helpers/settings/json_store 剩余缺口"""
import sys, os, json, tempfile
import pytest
from unittest.mock import patch, MagicMock


class TestHelpersFinalGaps:
    def test_format_date_except(self):
        """line 49-50: format_date except branch"""
        from utils.helpers import format_date
        assert format_date("bad") == "bad"

    def test_urgency_orange_days_3_to_7(self):
        """line 70: elif days <= 7 → #FF9800"""
        from utils.helpers import get_urgency_color
        from datetime import date, timedelta
        f = (date.today() + timedelta(days=5)).strftime("%Y-%m-%d")
        assert get_urgency_color(f) == "#FF9800"

    def test_urgency_green_future(self):
        """line 72: else → #4CAF50"""
        from utils.helpers import get_urgency_color
        from datetime import date, timedelta
        f = (date.today() + timedelta(days=30)).strftime("%Y-%m-%d")
        assert get_urgency_color(f) == "#4CAF50"


class TestSettingsFinalGaps:
    def test_save_settings_failure(self, tmp_path, monkeypatch):
        """lines 85-87: save failure path"""
        from utils.settings_manager import SettingsManager
        import utils.settings_manager as sm_mod
        # Point to non-writable path to force save failure
        sm_mod.SettingsManager._instance = None
        monkeypatch.setattr(sm_mod, 'SETTINGS_FILE', './__nonexistent_test_path/settings.json')
        sm = SettingsManager()
        assert sm.save_settings() is False


class TestJsonStoreFinalGaps:
    def test_save_failure_no_dir(self, tmp_path):
        """lines 41-43: save failure - skip _ensure_dir so dir doesn't exist"""
        from utils.storage.json_store import JsonStore
        store = JsonStore.__new__(JsonStore)
        store.file_path = os.path.join(str(tmp_path), 'nonexistent_dir', 'z.json')
        store._ensure_dir = lambda: None  # skip dir creation
        assert store.save({"test": 1}) is False

    def test_update_non_dict(self, tmp_path):
        """line 52: data is not dict → use updates directly"""
        p = os.path.join(str(tmp_path), 'nondict.json')
        from utils.storage.json_store import JsonStore
        store = JsonStore(p)
        store.save([1, 2, 3])
        assert store.update({"x": 1}, merge=True) is True
        data = store.load()
        assert isinstance(data, dict)
        assert data["x"] == 1

    def test_ensure_dir_creates(self, tmp_path):
        """line 22: _ensure_dir creates directory"""
        d = os.path.join(str(tmp_path), 'subdir', 'deep')
        p = os.path.join(d, 'test.json')
        from utils.storage.json_store import JsonStore
        store = JsonStore(p)
        assert os.path.isdir(d)


class TestLogisticsFinalGaps:
    def test_add_and_remove_company(self, tmp_path, monkeypatch):
        """lines 73-76, 88-90: add/remove custom companies"""
        import utils.logistics_companies as lc
        data_file = os.path.join(str(tmp_path), 'logistics.json')
        monkeypatch.setattr(lc, 'DATA_FILE', data_file)

        # Add
        ok, msg = lc.add_company('测试物流')
        assert ok is True

        # Remove
        ok, msg = lc.remove_company('测试物流')
        assert ok is True
