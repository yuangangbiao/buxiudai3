# -*- coding: utf-8 -*-
"""
质检记录数据模型单元测试 (QualityDAO)
"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock


class TestQualityDAO:
    """QualityDAO 单元测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """设置 mock 数据库连接（直接 cursor 模式）"""
        self.cursor = MagicMock()
        self.conn = MagicMock()
        self.conn.cursor.return_value = self.cursor
        self.p = patch('models.quality.get_connection', return_value=self.conn)
        self.p.start()
        yield
        self.p.stop()

    @pytest.fixture
    def dao(self):
        """获取 QualityDAO 实例"""
        from models.quality import QualityDAO
        return QualityDAO()

    def test_get_by_order(self, dao):
        """get_by_order 应返回记录列表"""
        self.cursor.fetchall.return_value = [
            {"id": 1, "result": "合格"},
        ]
        result = dao.get_by_order(1)
        assert result is not None

    def test_create_record(self, dao):
        """create 应返回新记录 ID（int 类型）

        注意：create 内部会调用 _ensure_inspection_columns 和
        _get_next_inspection_seq，它们各自调用 get_connection()。
        由于都返回同一个 self.conn，cursor.fetchone 需要 side_effect
        来模拟多次调用返回不同值。
        """
        # _ensure_inspection_columns: 3x SHOW COLUMNS → 3x fetchone → 3x None
        # _get_next_inspection_seq: 1x SELECT MAX → fetchone → (0,)
        # 共需要 4 个 fetchone 返回值（前3个 for column checks, 第4个 for seq）
        self.cursor.fetchone.side_effect = [
            None,           # inspection_seq column check
            None,           # inspection_no column check
            None,           # attachment_path column check
            {"next_seq": 0},  # _get_next_inspection_seq: COALESCE(MAX(...), 0) + 1
        ]
        type(self.cursor).lastrowid = PropertyMock(return_value=99)
        result = dao.create({"order_id": 1, "result": "合格"})
        assert isinstance(result, int)
