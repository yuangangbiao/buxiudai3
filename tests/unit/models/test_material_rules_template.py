# -*- coding: utf-8 -*-
"""models/material_rules_template.py 全覆盖测试"""
import pytest
from unittest.mock import patch, MagicMock


class TestMaterialRulesTemplate:
    """material_rules_template 模块全覆盖测试 - 6个函数"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mock_cursor = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor

    def _import_mod(self):
        """每次导入前先清除缓存，确保用最新的 mock"""
        import sys
        for m in list(sys.modules.keys()):
            if 'material_rules_template' in m:
                del sys.modules[m]
        p = patch('models.material_rules_template._get_db', return_value=self.mock_conn)
        p.start()
        from models import material_rules_template
        self.mod = material_rules_template
        return p

    # ── get_all_templates ──────────────────────────────────

    def test_get_all_templates(self):
        p = self._import_mod()
        self.mock_cursor.fetchall.return_value = [
            ("t1", "desc1", '{"key":"val1"}', "2026-01-01", "2026-01-02"),
            ("t2", "", '[]', None, None),
        ]
        result = self.mod.get_all_templates()
        assert len(result) == 2
        assert result[0]["name"] == "t1"
        assert result[0]["rules"] == {"key": "val1"}
        assert result[1]["name"] == "t2"
        assert result[1]["rules"] == []
        assert result[1]["description"] == ""
        p.stop()

    def test_get_all_templates_empty(self):
        p = self._import_mod()
        self.mock_cursor.fetchall.return_value = []
        result = self.mod.get_all_templates()
        assert result == []
        p.stop()

    # ── get_template ───────────────────────────────────────

    def test_get_template_found(self):
        p = self._import_mod()
        self.mock_cursor.fetchone.return_value = (
            "my_template", "my desc", '[1,2,3]', "2026-01-01", "2026-01-02"
        )
        result = self.mod.get_template("my_template")
        assert result["name"] == "my_template"
        assert result["rules"] == [1, 2, 3]
        p.stop()

    def test_get_template_not_found(self):
        p = self._import_mod()
        self.mock_cursor.fetchone.return_value = None
        result = self.mod.get_template("nonexistent")
        assert result is None
        p.stop()

    # ── save_template ──────────────────────────────────────

    def test_save_template_success(self):
        p = self._import_mod()
        rules = [{"field": "width", "operator": "gt", "value": 10}]
        result = self.mod.save_template("新模板", rules, "测试描述")
        assert result == (True, "模板「新模板」已保存")
        p.stop()

    def test_save_template_empty_name(self):
        p = self._import_mod()
        result = self.mod.save_template("  ", [])
        assert result == (False, "模板名称不能为空")
        p.stop()

    def test_save_template_duplicate_name(self):
        p = self._import_mod()
        self.mock_cursor.execute.side_effect = Exception("UNIQUE constraint")
        result = self.mod.save_template("dup", [])
        assert result == (False, "模板「dup」已存在，请使用其他名称")
        p.stop()

    # ── update_template ────────────────────────────────────

    def test_update_template_success(self):
        p = self._import_mod()
        self.mock_cursor.rowcount = 1
        result = self.mod.update_template("t1", [{"k": "v"}], "新描述")
        assert result == (True, "模板「t1」已更新")
        p.stop()

    def test_update_template_not_found(self):
        p = self._import_mod()
        self.mock_cursor.rowcount = 0
        result = self.mod.update_template("nonexistent", [])
        assert result == (False, "模板「nonexistent」不存在")
        p.stop()

    # ── delete_template ────────────────────────────────────

    def test_delete_template_success(self):
        p = self._import_mod()
        self.mock_cursor.rowcount = 1
        result = self.mod.delete_template("t1")
        assert result == (True, "模板「t1」已删除")
        p.stop()

    def test_delete_template_not_found(self):
        p = self._import_mod()
        self.mock_cursor.rowcount = 0
        result = self.mod.delete_template("nonexistent")
        assert result == (False, "模板「nonexistent」不存在")
        p.stop()

    # ── rename_template ────────────────────────────────────

    def test_rename_template_success(self):
        p = self._import_mod()
        self.mock_cursor.rowcount = 1
        result = self.mod.rename_template("旧名称", "新名称")
        assert result == (True, "已重命名为「新名称」")
        p.stop()

    def test_rename_template_empty_new_name(self):
        p = self._import_mod()
        result = self.mod.rename_template("旧名称", "  ")
        assert result == (False, "新名称不能为空")
        p.stop()

    def test_rename_template_not_found(self):
        p = self._import_mod()
        self.mock_cursor.rowcount = 0
        result = self.mod.rename_template("nonexistent", "新名称")
        assert result == (False, "模板「nonexistent」不存在")
        p.stop()

    # ── get_template_names ─────────────────────────────────

    def test_get_template_names(self):
        p = self._import_mod()
        self.mock_cursor.fetchall.return_value = [("a",), ("b",), ("c",)]
        result = self.mod.get_template_names()
        assert result == ["a", "b", "c"]
        p.stop()

    def test_get_template_names_empty(self):
        p = self._import_mod()
        self.mock_cursor.fetchall.return_value = []
        result = self.mod.get_template_names()
        assert result == []
        p.stop()


# ============================================================
# _get_db 函数覆盖（不 mock _get_db 本身，而是 mock get_connection）
# ============================================================
class TestGetDb:
    """覆盖 _get_db 函数体（L10-12）"""

    def test_get_db_returns_connection(self):
        """_get_db 内部调用 get_connection 返回连接（覆盖 L10-12）"""
        from unittest.mock import patch, MagicMock
        with patch('models.database.get_connection') as mock_gc:
            mock_conn = MagicMock()
            mock_gc.return_value = mock_conn
            from models.material_rules_template import _get_db
            result = _get_db()
            assert result is mock_conn
            mock_gc.assert_called_once()


# ============================================================
# clean_for_json 覆盖（datetime 对象参数触发 default 函数）
# ============================================================
class TestCleanForJson:
    """覆盖 save_template 和 update_template 内部的 clean_for_json 函数体"""

    def _import_without_mock_get_db(self):
        """导入模块但不 mock _get_db（需外部 mock get_connection）"""
        import sys
        for m in list(sys.modules.keys()):
            if 'material_rules_template' in m:
                del sys.modules[m]
        from models import material_rules_template
        self.mod = material_rules_template

    def test_save_template_with_datetime_in_rules(self):
        """save_template 规则中包含 datetime 对象→触发 clean_for_json（覆盖 L77-79）"""
        from unittest.mock import patch, MagicMock
        with patch('models.database.get_connection') as mock_gc:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_gc.return_value = mock_conn
            self._import_without_mock_get_db()
            from datetime import datetime as dt
            rules = [{"date": dt(2026, 6, 1, 10, 30, 0)}]
            result = self.mod.save_template("dt-test", rules, "含datetime")
            assert result == (True, "模板「dt-test」已保存")

    def test_update_template_with_datetime_in_rules(self):
        """update_template 规则中包含 datetime 对象→触发 clean_for_json（覆盖 L113-115）"""
        from unittest.mock import patch, MagicMock
        with patch('models.database.get_connection') as mock_gc:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 1
            mock_conn.cursor.return_value = mock_cursor
            mock_gc.return_value = mock_conn
            self._import_without_mock_get_db()
            from datetime import datetime as dt
            new_rules = [{"timestamp": dt(2026, 6, 1, 14, 0, 0)}]
            result = self.mod.update_template("dt-test", new_rules, "含datetime")
            assert result == (True, "模板「dt-test」已更新")

    def test_save_template_clean_for_json_fallthrough(self):
        """save_template 规则含非datetime不可序列化对象→触发 fallthrough（覆盖 L79）"""
        import json, pytest
        from unittest.mock import patch, MagicMock
        with patch('models.database.get_connection') as mock_gc:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_gc.return_value = mock_conn
            self._import_without_mock_get_db()

            class CustomObj:
                pass

            with pytest.raises((TypeError, ValueError)):
                # clean_for_json 返回 obj，json.dumps 无法序列化 → 报错
                self.mod.save_template("fallthrough-test", [{"obj": CustomObj()}], "fallthrough")

    def test_update_template_clean_for_json_fallthrough(self):
        """update_template 规则含非datetime不可序列化对象→触发 fallthrough（覆盖 L115）"""
        import pytest
        from unittest.mock import patch, MagicMock
        with patch('models.database.get_connection') as mock_gc:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 1
            mock_conn.cursor.return_value = mock_cursor
            mock_gc.return_value = mock_conn
            self._import_without_mock_get_db()

            class CustomObj:
                pass

            with pytest.raises((TypeError, ValueError)):
                # clean_for_json 返回 obj，json.dumps 无法序列化 → 报错
                self.mod.update_template("fallthrough-test", [{"obj": CustomObj()}], "fallthrough")
