# -*- coding: utf-8 -*-
"""
发货数据模型单元测试 (ShipmentDAO)
"""
import pytest
from unittest.mock import MagicMock, patch


class TestShipmentDAO:
    """ShipmentDAO 单元测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """设置 mock 数据库连接（直接 cursor 模式）"""
        self.cursor = MagicMock()
        self.conn = MagicMock()
        self.conn.cursor.return_value = self.cursor
        self.p = patch('models.shipment.get_connection', return_value=self.conn)
        self.p.start()
        yield
        self.p.stop()

    @pytest.fixture
    def dao(self):
        """获取 ShipmentDAO 实例"""
        from models.shipment import ShipmentDAO
        return ShipmentDAO()

    def test_get_by_id(self, dao):
        """get_by_id 在记录存在时返回字典"""
        self.cursor.fetchone.return_value = {
            "id": 1, "shipment_no": "SH-001",
        }
        result = dao.get_by_id(1)
        assert result is not None
