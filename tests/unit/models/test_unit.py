# -*- coding: utf-8 -*-
"""models/unit.py UnitDAO 全覆盖测试"""
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def mock_conn():
    """模拟数据库连接"""
    with patch('models.unit.get_connection') as mock_gc:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_gc.return_value = mock_conn
        yield mock_conn, mock_cursor, mock_gc


class TestUnitDAO:
    """UnitDAO 8 个静态方法全覆盖"""

    # ── get_all ─────────────────────────────────────────────

    def test_get_all(self, mock_conn):
        mock_conn[1].fetchall.return_value = [
            {"code": "m", "name": "米", "category": "length", "is_preset": 1},
            {"code": "kg", "name": "千克", "category": "weight", "is_preset": 1},
        ]
        from models.unit import UnitDAO
        result = UnitDAO.get_all()
        assert len(result) == 2
        assert result[0] == ("m", "米", "length", True)

    def test_get_all_empty(self, mock_conn):
        mock_conn[1].fetchall.return_value = []
        from models.unit import UnitDAO
        result = UnitDAO.get_all()
        assert result == []

    # ── get_by_category ─────────────────────────────────────

    def test_get_by_category(self, mock_conn):
        mock_conn[1].fetchall.return_value = [
            {"code": "m", "name": "米", "category": "length"},
        ]
        from models.unit import UnitDAO
        result = UnitDAO.get_by_category("length")
        assert result == [("m", "米", "length")]

    def test_get_by_category_empty(self, mock_conn):
        mock_conn[1].fetchall.return_value = []
        from models.unit import UnitDAO
        result = UnitDAO.get_by_category("nonexistent")
        assert result == []

    # ── get_by_code ─────────────────────────────────────────

    def test_get_by_code_found(self, mock_conn):
        mock_conn[1].fetchone.return_value = {
            "code": "m", "name": "米", "category": "length", "is_preset": 1
        }
        from models.unit import UnitDAO
        result = UnitDAO.get_by_code("m")
        assert result["code"] == "m"
        assert result["is_preset"] is True

    def test_get_by_code_not_found(self, mock_conn):
        mock_conn[1].fetchone.return_value = None
        from models.unit import UnitDAO
        result = UnitDAO.get_by_code("nonexistent")
        assert result is None

    # ── add ─────────────────────────────────────────────────

    def test_add_success(self, mock_conn):
        mock_conn[1].fetchone.return_value = None  # 不存在
        from models.unit import UnitDAO
        success, msg = UnitDAO.add("pc", "个")
        assert success is True
        assert "已添加" in msg

    def test_add_empty_code(self, mock_conn):
        from models.unit import UnitDAO
        success, msg = UnitDAO.add("  ", "个")
        assert success is False
        assert "不能为空" in msg

    def test_add_empty_name(self, mock_conn):
        from models.unit import UnitDAO
        success, msg = UnitDAO.add("pc", "  ")
        assert success is False
        assert "不能为空" in msg

    def test_add_code_too_long(self, mock_conn):
        from models.unit import UnitDAO
        success, msg = UnitDAO.add("a" * 21, "test")
        assert success is False
        assert "过长" in msg

    def test_add_name_too_long(self, mock_conn):
        from models.unit import UnitDAO
        success, msg = UnitDAO.add("ok", "n" * 51)
        assert success is False
        assert "过长" in msg

    def test_add_preset_exists(self, mock_conn):
        mock_conn[1].fetchone.return_value = {"id": 1, "is_preset": 1}
        from models.unit import UnitDAO
        success, msg = UnitDAO.add("m", "米")
        assert success is False
        assert "预设单位" in msg

    def test_add_duplicate(self, mock_conn):
        mock_conn[1].fetchone.return_value = {"id": 1, "is_preset": 0}
        from models.unit import UnitDAO
        success, msg = UnitDAO.add("pc", "个")
        assert success is False
        assert "已存在" in msg

    # ── remove ──────────────────────────────────────────────

    def test_remove_success(self, mock_conn):
        mock_conn[1].fetchone.return_value = {"is_preset": 0}
        mock_conn[1].rowcount = 1
        from models.unit import UnitDAO
        success, msg = UnitDAO.remove("custom")
        assert success is True
        assert "已删除" in msg

    def test_remove_not_found(self, mock_conn):
        mock_conn[1].fetchone.return_value = None
        from models.unit import UnitDAO
        success, msg = UnitDAO.remove("nonexistent")
        assert success is False
        assert "不存在" in msg

    def test_remove_preset(self, mock_conn):
        mock_conn[1].fetchone.return_value = {"is_preset": 1}
        from models.unit import UnitDAO
        success, msg = UnitDAO.remove("m")
        assert success is False
        assert "预设单位" in msg

    def test_remove_delete_failed(self, mock_conn):
        mock_conn[1].fetchone.return_value = {"is_preset": 0}
        mock_conn[1].rowcount = 0
        from models.unit import UnitDAO
        success, msg = UnitDAO.remove("custom")
        assert success is False
        assert "删除失败" in msg

    # ── update ──────────────────────────────────────────────

    def test_update_name_and_category(self, mock_conn):
        mock_conn[1].fetchone.return_value = {"is_preset": 0}
        mock_conn[1].rowcount = 1
        from models.unit import UnitDAO
        success, msg = UnitDAO.update("custom", "new_name", "new_cat")
        assert success is True
        assert "已更新" in msg

    def test_update_name_only(self, mock_conn):
        mock_conn[1].fetchone.return_value = {"is_preset": 0}
        from models.unit import UnitDAO
        success, msg = UnitDAO.update("custom", "new_name")
        assert success is True

    def test_update_category_only(self, mock_conn):
        mock_conn[1].fetchone.return_value = {"is_preset": 0}
        from models.unit import UnitDAO
        success, msg = UnitDAO.update("custom", None, "new_cat")
        assert success is True

    def test_update_no_changes(self, mock_conn):
        """不传 name 也不传 category → updates 列表空 → 不执行 SQL 但返回成功"""
        mock_conn[1].fetchone.return_value = {"is_preset": 0}
        from models.unit import UnitDAO
        success, msg = UnitDAO.update("custom")
        assert success is True

    def test_update_not_found(self, mock_conn):
        mock_conn[1].fetchone.return_value = None
        from models.unit import UnitDAO
        success, msg = UnitDAO.update("nonexistent", "x")
        assert success is False
        assert "不存在" in msg

    def test_update_preset(self, mock_conn):
        mock_conn[1].fetchone.return_value = {"is_preset": 1}
        from models.unit import UnitDAO
        success, msg = UnitDAO.update("m", "x")
        assert success is False
        assert "预设单位" in msg

    # ── get_categories ──────────────────────────────────────

    def test_get_categories(self, mock_conn):
        mock_conn[1].fetchall.return_value = [
            {"category": "length"},
            {"category": "weight"},
        ]
        from models.unit import UnitDAO
        result = UnitDAO.get_categories()
        assert result == ["length", "weight"]

    def test_get_categories_empty(self, mock_conn):
        mock_conn[1].fetchall.return_value = []
        from models.unit import UnitDAO
        result = UnitDAO.get_categories()
        assert result == []
