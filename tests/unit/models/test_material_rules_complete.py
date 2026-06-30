# -*- coding: utf-8 -*-
"""models/material_rules.py 全覆盖测试"""
import pytest
from unittest.mock import patch, MagicMock


class TestMaterialRulesDAO:
    """MaterialRulesDAO 测试 - 覆盖所有方法"""

    @pytest.fixture(autouse=True)
    def setup(self):
        import sys
        for m in list(sys.modules.keys()):
            if m.startswith('models.material_rules'):
                del sys.modules[m]
        self.mock_cursor = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor
        self.mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=self.mock_cursor)
        self.mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

    def _patch(self):
        p = patch('models.database.get_connection', return_value=self.mock_conn)
        p.start()
        return p

    def test_create(self):
        self.mock_cursor.lastrowid = 42
        p = self._patch()
        from models.material_rules import MaterialRulesDAO
        result = MaterialRulesDAO.create("不锈钢网带", "mesh_size", "网孔尺寸{mesh_size}")
        assert result == 42
        p.stop()

    def test_update(self):
        self.mock_cursor.rowcount = 1
        p = self._patch()
        from models.material_rules import MaterialRulesDAO
        result = MaterialRulesDAO.update(1, {
            "material_name_template": "新模板",
            "spec_field": "width",
            "spec_unit": "mm",
            "qty_field": "quantity",
            "qty_formula": "width*length",
            "qty_unit": "m2",
            "enabled": 1,
        })
        assert result is True
        p.stop()

    def test_update_no_rows(self):
        self.mock_cursor.rowcount = 0
        p = self._patch()
        from models.material_rules import MaterialRulesDAO
        result = MaterialRulesDAO.update(999, {"material_name_template": "x"})
        assert result is False
        p.stop()

    def test_delete(self):
        self.mock_cursor.rowcount = 1
        p = self._patch()
        from models.material_rules import MaterialRulesDAO
        result = MaterialRulesDAO.delete(1)
        assert result is True
        p.stop()

    def test_get_by_id(self):
        self.mock_cursor.fetchone.return_value = {"id": 1, "product_type": "test"}
        p = self._patch()
        from models.material_rules import MaterialRulesDAO
        result = MaterialRulesDAO.get_by_id(1)
        assert result["id"] == 1
        p.stop()

    def test_get_by_id_not_found(self):
        self.mock_cursor.fetchone.return_value = None
        p = self._patch()
        from models.material_rules import MaterialRulesDAO
        result = MaterialRulesDAO.get_by_id(999)
        assert result is None
        p.stop()

    def test_get_by_product_type(self):
        self.mock_cursor.fetchall.return_value = [{"id": 1}, {"id": 2}]
        p = self._patch()
        from models.material_rules import MaterialRulesDAO
        result = MaterialRulesDAO.get_by_product_type("test")
        assert len(result) == 2
        p.stop()

    def test_get_all(self):
        self.mock_cursor.fetchall.return_value = [{"id": 1}]
        p = self._patch()
        from models.material_rules import MaterialRulesDAO
        result = MaterialRulesDAO.get_all()
        assert len(result) == 1
        p.stop()

    def test_get_distinct_product_types(self):
        self.mock_cursor.fetchall.return_value = [{"product_type": "T1"}, {"product_type": "T2"}]
        p = self._patch()
        from models.material_rules import MaterialRulesDAO
        result = MaterialRulesDAO.get_distinct_product_types()
        assert result == ["T1", "T2"]
        p.stop()

    def test_get_distinct_product_types_empty(self):
        self.mock_cursor.fetchall.return_value = []
        p = self._patch()
        from models.material_rules import MaterialRulesDAO
        result = MaterialRulesDAO.get_distinct_product_types()
        assert result == []
        p.stop()

    def test_exists_true(self):
        self.mock_cursor.fetchone.return_value = {"1": 1}
        p = self._patch()
        from models.material_rules import MaterialRulesDAO
        result = MaterialRulesDAO.exists("test", "param")
        assert result is True
        p.stop()

    def test_exists_false(self):
        self.mock_cursor.fetchone.return_value = None
        p = self._patch()
        from models.material_rules import MaterialRulesDAO
        result = MaterialRulesDAO.exists("test", "param")
        assert result is False
        p.stop()
