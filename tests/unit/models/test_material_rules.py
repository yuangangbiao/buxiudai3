# -*- coding: utf-8 -*-
"""models/material_rules.py MaterialRulesDAO 全覆盖测试"""
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def mock_conn():
    """模拟数据库连接，所有测试方法共享"""
    with patch('models.material_rules.get_connection') as mock_gc:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_gc.return_value = mock_conn
        yield mock_conn, mock_cursor, mock_gc


class TestMaterialRulesDAO:
    """MaterialRulesDAO 8 个静态方法全覆盖"""

    # ── create ──────────────────────────────────────────────

    def test_create_success(self, mock_conn):
        mock_conn[1].lastrowid = 42
        from models.material_rules import MaterialRulesDAO
        result = MaterialRulesDAO.create(
            "belt", "width", "belt_{width}mm",
            "width_mm", "mm", "qty", "width*2", "m"
        )
        assert result == 42
        mock_conn[1].execute.assert_called_once()
        mock_conn[0].commit.assert_called_once()

    def test_create_minimal(self, mock_conn):
        """仅传必需参数"""
        mock_conn[1].lastrowid = 1
        from models.material_rules import MaterialRulesDAO
        result = MaterialRulesDAO.create("belt", "length", "belt_{length}mm")
        assert result == 1

    # ── update ──────────────────────────────────────────────

    def test_update_success(self, mock_conn):
        mock_conn[1].rowcount = 1
        from models.material_rules import MaterialRulesDAO
        result = MaterialRulesDAO.update(1, {"material_name_template": "new", "enabled": 1})
        assert result is True

    def test_update_not_found(self, mock_conn):
        mock_conn[1].rowcount = 0
        from models.material_rules import MaterialRulesDAO
        result = MaterialRulesDAO.update(999, {"material_name_template": "x"})
        assert result is False

    def test_update_with_defaults(self, mock_conn):
        """不传 enabled 时默认 1"""
        mock_conn[1].rowcount = 1
        from models.material_rules import MaterialRulesDAO
        result = MaterialRulesDAO.update(1, {"material_name_template": "tpl"})
        assert result is True

    # ── delete ──────────────────────────────────────────────

    def test_delete_success(self, mock_conn):
        mock_conn[1].rowcount = 1
        from models.material_rules import MaterialRulesDAO
        result = MaterialRulesDAO.delete(1)
        assert result is True

    def test_delete_not_found(self, mock_conn):
        mock_conn[1].rowcount = 0
        from models.material_rules import MaterialRulesDAO
        result = MaterialRulesDAO.delete(999)
        assert result is False

    # ── get_by_id ───────────────────────────────────────────

    def test_get_by_id_found(self, mock_conn):
        mock_conn[1].fetchone.return_value = {"id": 1, "product_type": "belt"}
        from models.material_rules import MaterialRulesDAO
        result = MaterialRulesDAO.get_by_id(1)
        assert result["id"] == 1

    def test_get_by_id_not_found(self, mock_conn):
        mock_conn[1].fetchone.return_value = None
        from models.material_rules import MaterialRulesDAO
        result = MaterialRulesDAO.get_by_id(999)
        assert result is None

    # ── get_by_product_type ─────────────────────────────────

    def test_get_by_product_type(self, mock_conn):
        mock_conn[1].fetchall.return_value = [
            {"id": 1, "product_type": "belt"},
            {"id": 2, "product_type": "belt"},
        ]
        from models.material_rules import MaterialRulesDAO
        result = MaterialRulesDAO.get_by_product_type("belt")
        assert len(result) == 2

    def test_get_by_product_type_empty(self, mock_conn):
        mock_conn[1].fetchall.return_value = []
        from models.material_rules import MaterialRulesDAO
        result = MaterialRulesDAO.get_by_product_type("nonexistent")
        assert result == []

    # ── get_all ─────────────────────────────────────────────

    def test_get_all(self, mock_conn):
        mock_conn[1].fetchall.return_value = [
            {"id": 1, "product_type": "belt"},
            {"id": 2, "product_type": "mesh"},
        ]
        from models.material_rules import MaterialRulesDAO
        result = MaterialRulesDAO.get_all()
        assert len(result) == 2

    def test_get_all_empty(self, mock_conn):
        mock_conn[1].fetchall.return_value = []
        from models.material_rules import MaterialRulesDAO
        result = MaterialRulesDAO.get_all()
        assert result == []

    # ── get_distinct_product_types ──────────────────────────

    def test_get_distinct_product_types(self, mock_conn):
        mock_conn[1].fetchall.return_value = [
            {"product_type": "belt"},
            {"product_type": "mesh"},
        ]
        from models.material_rules import MaterialRulesDAO
        result = MaterialRulesDAO.get_distinct_product_types()
        assert result == ["belt", "mesh"]

    def test_get_distinct_product_types_empty(self, mock_conn):
        mock_conn[1].fetchall.return_value = []
        from models.material_rules import MaterialRulesDAO
        result = MaterialRulesDAO.get_distinct_product_types()
        assert result == []

    # ── exists ──────────────────────────────────────────────

    def test_exists_true(self, mock_conn):
        mock_conn[1].fetchone.return_value = {"1": 1}
        from models.material_rules import MaterialRulesDAO
        result = MaterialRulesDAO.exists("belt", "width")
        assert result is True

    def test_exists_false(self, mock_conn):
        mock_conn[1].fetchone.return_value = None
        from models.material_rules import MaterialRulesDAO
        result = MaterialRulesDAO.exists("belt", "nonexistent")
        assert result is False
