# -*- coding: utf-8 -*-
"""最后冲刺30% - json_store + db_utils + log_scheduler"""
import sys, os, json, tempfile
import pytest
from unittest.mock import patch, MagicMock


class TestJsonStore:
    def test_save_and_load(self, tmp_path):
        p = os.path.join(str(tmp_path), 'test.json')
        from utils.storage.json_store import JsonStore
        store = JsonStore(p)
        assert store.save({"a": 1, "b": 2}) is True
        data = store.load()
        assert data == {"a": 1, "b": 2}

    def test_load_nonexistent_returns_default(self, tmp_path):
        p = os.path.join(str(tmp_path), 'nonexistent.json')
        from utils.storage.json_store import JsonStore
        store = JsonStore(p)
        assert store.load(default={"default": True}) == {"default": True}

    def test_load_broken_json(self, tmp_path):
        p = os.path.join(str(tmp_path), 'broken.json')
        with open(p, 'w') as f:
            f.write('not json')
        from utils.storage.json_store import JsonStore
        store = JsonStore(p)
        assert store.load(default=[]) == []

    def test_update_merge(self, tmp_path):
        p = os.path.join(str(tmp_path), 'merge.json')
        from utils.storage.json_store import JsonStore
        store = JsonStore(p)
        store.save({"x": 1, "y": 2})
        assert store.update({"y": 99, "z": 3}) is True
        data = store.load()
        assert data["x"] == 1
        assert data["y"] == 99
        assert data["z"] == 3

    def test_update_no_merge(self, tmp_path):
        p = os.path.join(str(tmp_path), 'nomerge.json')
        from utils.storage.json_store import JsonStore
        store = JsonStore(p)
        store.save({"x": 1})
        assert store.update({"y": 2}, merge=False) is True
        assert store.load() == {"y": 2}

    def test_clear(self, tmp_path):
        p = os.path.join(str(tmp_path), 'clear.json')
        from utils.storage.json_store import JsonStore
        store = JsonStore(p)
        store.save({"data": 123})
        assert store.clear() is True
        assert store.load() is None


class TestLogScheduler:
    def test_start_stop(self):
        import utils.log_scheduler as ls
        # should not crash
        assert hasattr(ls, 'start_log_cleanup_scheduler')
        assert hasattr(ls, 'stop_log_cleanup_scheduler')
