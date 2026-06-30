# -*- coding: utf-8 -*-
"""单元测试：models/bom.py — BOMDAO + init_bom_table"""

import pytest
from unittest.mock import MagicMock, patch


SAMPLE_ROW = {
    "id": 1,
    "product_type": "网带",
    "material": "304不锈钢",
    "steel_weight": 2.5,
    "steel_unit": "kg/米",
    "packaging_materials": "木箱",
    "surface_treatment": "酸洗",
    "production_process": "编织",
    "waste_rate": 5.0,
    "unit": "米",
    "remark": "标准品",
    "material_code": "304-001",
    "material_type": "不锈钢",
    "specification": "1.0m*10m",
    "unit_weight": 2.5,
    "standard_qty": 100,
    "actual_qty": 95,
    "price": 25.0,
    "supplier": "供应商A",
    "lead_time": 7,
    "safety_stock": 50,
    "location": "A-01",
    "batch_no": "B2024001",
    "expiry_date": "2025-12-31",
    "draw_no": "DW-001",
    "version": "V1.0",
}

SAMPLE_DATA = {
    "steel_weight": 2.5,
    "steel_unit": "kg/米",
    "packaging_materials": "木箱",
    "surface_treatment": "酸洗",
    "production_process": "编织",
    "waste_rate": 5.0,
    "unit": "米",
    "remark": "标准品",
    "material_code": "304-001",
    "material_type": "不锈钢",
    "specification": "1.0m*10m",
    "unit_weight": 2.5,
    "standard_qty": 100,
    "actual_qty": 95,
    "price": 25.0,
    "supplier": "供应商A",
    "lead_time": 7,
    "safety_stock": 50,
    "location": "A-01",
    "batch_no": "B2024001",
    "expiry_date": "2025-12-31",
    "draw_no": "DW-001",
    "version": "V1.0",
}


class TestBOMDAO:
    """BOMDAO 全部方法单元测试"""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        self.mock_cursor = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor
        self.patcher = patch("models.bom.get_connection", return_value=self.mock_conn)
        self.patcher.start()
        yield
        self.patcher.stop()

    # ── create ──────────────────────────────────────────────────

    def test_create_returns_lastrowid(self):
        """create() 应返回 lastrowid"""
        from models.bom import BOMDAO

        self.mock_cursor.lastrowid = 42
        result = BOMDAO.create("网带", "304不锈钢", SAMPLE_DATA)
        assert result == 42
        self.mock_conn.commit.assert_called_once()
        self.mock_conn.close.assert_called_once()

    def test_create_with_minimal_data(self):
        """create() 使用空 dict，应使用默认值执行"""
        from models.bom import BOMDAO

        self.mock_cursor.lastrowid = 0
        result = BOMDAO.create("网带", "304不锈钢", {})
        assert result == 0
        self.mock_conn.commit.assert_called_once()

    # ── update ──────────────────────────────────────────────────

    def test_update_returns_true_when_row_affected(self):
        """update() 有行受影响时返回 True"""
        from models.bom import BOMDAO

        self.mock_cursor.rowcount = 1
        result = BOMDAO.update(1, SAMPLE_DATA)
        assert result is True
        self.mock_conn.commit.assert_called_once()
        self.mock_conn.close.assert_called_once()

    def test_update_returns_false_when_no_row_affected(self):
        """update() 无行受影响时返回 False"""
        from models.bom import BOMDAO

        self.mock_cursor.rowcount = 0
        result = BOMDAO.update(999, SAMPLE_DATA)
        assert result is False
        self.mock_conn.commit.assert_called_once()

    # ── delete ──────────────────────────────────────────────────

    def test_delete_returns_true_when_row_affected(self):
        """delete() 有行受影响时返回 True"""
        from models.bom import BOMDAO

        self.mock_cursor.rowcount = 1
        result = BOMDAO.delete(1)
        assert result is True
        self.mock_conn.commit.assert_called_once()
        self.mock_conn.close.assert_called_once()

    def test_delete_returns_false_when_no_row_affected(self):
        """delete() 无行受影响时返回 False"""
        from models.bom import BOMDAO

        self.mock_cursor.rowcount = 0
        result = BOMDAO.delete(999)
        assert result is False
        self.mock_conn.commit.assert_called_once()

    # ── get_by_id ────────────────────────────────────────────────

    def test_get_by_id_returns_dict(self):
        """get_by_id() 返回包含正确数据的 dict"""
        from models.bom import BOMDAO

        self.mock_cursor.fetchone.return_value = SAMPLE_ROW
        result = BOMDAO.get_by_id(1)
        assert result["id"] == 1
        assert result["product_type"] == "网带"
        assert result["material"] == "304不锈钢"
        self.mock_cursor.close.assert_called_once()
        self.mock_conn.close.assert_called_once()

    def test_get_by_id_returns_none_when_not_found(self):
        """get_by_id() 记录不存在时返回 None"""
        from models.bom import BOMDAO

        self.mock_cursor.fetchone.return_value = None
        result = BOMDAO.get_by_id(999)
        assert result is None
        self.mock_cursor.close.assert_called_once()
        self.mock_conn.close.assert_called_once()

    # ── get_by_product ──────────────────────────────────────────

    def test_get_by_product_with_material(self):
        """get_by_product() 带有 material 参数时返回匹配结果"""
        from models.bom import BOMDAO

        row1 = {**SAMPLE_ROW, "id": 1}
        row2 = {**SAMPLE_ROW, "id": 2}
        self.mock_cursor.fetchall.return_value = [row1, row2]
        result = BOMDAO.get_by_product("网带", "304不锈钢")
        assert len(result) == 2
        assert result[0]["id"] == 1
        self.mock_cursor.close.assert_called_once()
        self.mock_conn.close.assert_called_once()

    def test_get_by_product_without_material(self):
        """get_by_product() 不带 material 参数时返回匹配结果"""
        from models.bom import BOMDAO

        self.mock_cursor.fetchall.return_value = [SAMPLE_ROW]
        result = BOMDAO.get_by_product("网带")
        assert len(result) == 1
        assert result[0]["product_type"] == "网带"
        self.mock_cursor.close.assert_called_once()
        self.mock_conn.close.assert_called_once()

    def test_get_by_product_returns_empty_when_not_found(self):
        """get_by_product() 无匹配时返回空列表"""
        from models.bom import BOMDAO

        self.mock_cursor.fetchall.return_value = []
        result = BOMDAO.get_by_product("不存在")
        assert result == []
        self.mock_cursor.close.assert_called_once()
        self.mock_conn.close.assert_called_once()

    # ── get_all ─────────────────────────────────────────────────

    def test_get_all_without_filters(self):
        """get_all() 无过滤条件时返回全部记录"""
        from models.bom import BOMDAO

        rows = [{**SAMPLE_ROW, "id": i} for i in range(1, 4)]
        self.mock_cursor.fetchall.return_value = rows
        result = BOMDAO.get_all()
        assert len(result) == 3
        self.mock_cursor.close.assert_called_once()
        self.mock_conn.close.assert_called_once()

    def test_get_all_with_filters(self):
        """get_all() 带 product_type 和 material 过滤条件"""
        from models.bom import BOMDAO

        self.mock_cursor.fetchall.return_value = [SAMPLE_ROW]
        result = BOMDAO.get_all({"product_type": "网带", "material": "304"})
        assert len(result) == 1
        self.mock_cursor.close.assert_called_once()
        self.mock_conn.close.assert_called_once()

    def test_get_all_with_empty_filters(self):
        """get_all() filters 为空 dict 时返回全部记录"""
        from models.bom import BOMDAO

        self.mock_cursor.fetchall.return_value = [SAMPLE_ROW]
        result = BOMDAO.get_all({})
        assert len(result) == 1
        self.mock_cursor.close.assert_called_once()
        self.mock_conn.close.assert_called_once()

    def test_get_all_with_partial_filters(self):
        """get_all() 仅传入 product_type 时正确过滤"""
        from models.bom import BOMDAO

        self.mock_cursor.fetchall.return_value = [SAMPLE_ROW]
        result = BOMDAO.get_all({"product_type": "网带"})
        assert len(result) == 1
        self.mock_cursor.close.assert_called_once()
        self.mock_conn.close.assert_called_once()

    # ── get_recent ──────────────────────────────────────────────

    def test_get_recent_default_limit(self):
        """get_recent() 使用默认 limit=200"""
        from models.bom import BOMDAO

        rows = [{**SAMPLE_ROW, "id": i} for i in range(1, 3)]
        self.mock_cursor.fetchall.return_value = rows
        result = BOMDAO.get_recent()
        assert len(result) == 2
        self.mock_cursor.close.assert_called_once()
        self.mock_conn.close.assert_called_once()

    def test_get_recent_custom_limit(self):
        """get_recent() 使用自定义 limit"""
        from models.bom import BOMDAO

        self.mock_cursor.fetchall.return_value = [SAMPLE_ROW]
        result = BOMDAO.get_recent(limit=10)
        assert len(result) == 1
        self.mock_cursor.close.assert_called_once()
        self.mock_conn.close.assert_called_once()

    def test_get_recent_returns_empty(self):
        """get_recent() 无数据时返回空列表"""
        from models.bom import BOMDAO

        self.mock_cursor.fetchall.return_value = []
        result = BOMDAO.get_recent()
        assert result == []
        self.mock_cursor.close.assert_called_once()
        self.mock_conn.close.assert_called_once()

    # ── calculate_material_requirement ──────────────────────────

    def test_calculate_material_requirement_with_waste(self):
        """calculate_material_requirement() 计算包含损耗的材料需求"""
        from models.bom import BOMDAO

        self.mock_cursor.fetchall.return_value = [SAMPLE_ROW]
        result = BOMDAO.calculate_material_requirement("网带", "304不锈钢", 100)
        assert result is not None
        # base_weight=2.5, quantity=100, waste_rate=5% --> total = 2.5*100*1.05 = 262.5
        assert result["total_steel_required"] == 262.5
        # waste = 262.5 - 250 = 12.5
        assert result["waste_amount"] == 12.5
        assert result["product_type"] == "网带"
        assert result["material"] == "304不锈钢"
        assert result["quantity"] == 100
        self.mock_cursor.close.assert_called()
        self.mock_conn.close.assert_called()

    def test_calculate_material_requirement_zero_waste(self):
        """calculate_material_requirement() 损耗率 0%"""
        from models.bom import BOMDAO

        row_no_waste = {**SAMPLE_ROW, "waste_rate": 0}
        self.mock_cursor.fetchall.return_value = [row_no_waste]
        result = BOMDAO.calculate_material_requirement("网带", "304不锈钢", 50)
        assert result is not None
        # base_weight=2.5, quantity=50, waste_rate=0% --> total = 2.5*50*1.0 = 125
        assert result["total_steel_required"] == 125.0
        assert result["waste_amount"] == 0.0
        assert result["waste_rate"] == 0

    def test_calculate_material_requirement_returns_none_when_no_bom(self):
        """calculate_material_requirement() bom_list 为空时返回 None"""
        from models.bom import BOMDAO

        self.mock_cursor.fetchall.return_value = []
        result = BOMDAO.calculate_material_requirement("不存在", "未知", 100)
        assert result is None


class TestInitBomTable:
    """init_bom_table 函数单元测试"""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        self.mock_cursor = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor
        self.patcher = patch("models.bom.get_connection", return_value=self.mock_conn)
        self.patcher.start()
        yield
        self.patcher.stop()

    def test_init_bom_table_executes_create_table(self):
        """init_bom_table() 应执行 CREATE TABLE IF NOT EXISTS"""
        from models.bom import init_bom_table

        init_bom_table()
        # 验证 execute 被调用，且 SQL 包含 CREATE TABLE
        called_sql = self.mock_cursor.execute.call_args[0][0]
        assert "CREATE TABLE IF NOT EXISTS bom_list" in called_sql
        self.mock_conn.commit.assert_called_once()
        self.mock_conn.close.assert_called_once()

    def test_init_bom_table_has_all_columns(self):
        """init_bom_table() 应包含所有 25+ 字段定义"""
        from models.bom import init_bom_table

        init_bom_table()
        called_sql = self.mock_cursor.execute.call_args[0][0]
        key_columns = [
            "id INT PRIMARY KEY AUTO_INCREMENT",
            "product_type VARCHAR",
            "material VARCHAR",
            "steel_weight DECIMAL",
            "steel_unit VARCHAR",
            "packaging_materials TEXT",
            "surface_treatment TEXT",
            "production_process TEXT",
            "waste_rate DECIMAL",
            "unit VARCHAR",
            "remark TEXT",
            "material_code VARCHAR",
            "material_type VARCHAR",
            "specification VARCHAR",
            "unit_weight DECIMAL",
            "standard_qty DECIMAL",
            "actual_qty DECIMAL",
            "price DECIMAL",
            "supplier VARCHAR",
            "lead_time INT",
            "safety_stock DECIMAL",
            "location VARCHAR",
            "batch_no VARCHAR",
            "expiry_date VARCHAR",
            "draw_no VARCHAR",
            "version VARCHAR",
            "created_at DATETIME",
            "updated_at DATETIME",
            "uk_product_material",
        ]
        for col in key_columns:
            assert col in called_sql, f"缺少列定义: {col}"
