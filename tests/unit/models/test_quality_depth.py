# -*- coding: utf-8 -*-
"""
models/quality.py QualityDAO 深度测试 — 覆盖所有未覆盖行
目标：100% 行覆盖率

关键：patch 路径必须是 ``models.quality.get_connection``（因为 quality.py
使用 ``from models.database import get_connection`` 将引用导入模块命名空间）。
"""
import pytest
from unittest.mock import patch, MagicMock, PropertyMock


class Row(dict):
    """模拟数据库行（支持 dict + attribute 访问）"""
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)


class TestQualityDepth:

    @pytest.fixture(autouse=True)
    def _setup(self):
        """标准 mock: patch models.quality.get_connection（模块级导入的引用）"""
        self.mock_cursor = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor
        # 注入自由变量到 quality 模块
        from models import quality
        quality.log_status_change = MagicMock()
        quality.OrderStatus = MagicMock()
        quality.OrderStatus.FINISHED = MagicMock(value='finished')
        quality.OrderStatus.QC = MagicMock(value='qc')
        quality.ProductionStatus = MagicMock()
        quality.ProductionStatus.COMPLETED = MagicMock(value='completed')
        # patch quality 模块命名空间中的 get_connection
        self._patchers = [
            patch('models.quality.get_connection', return_value=self.mock_conn),
            patch('models.quality.get_connection_context',
                  return_value=MagicMock(__enter__=MagicMock(return_value=self.mock_conn),
                                         __exit__=MagicMock(return_value=None))),
        ]
        for p in self._patchers:
            p.start()
        yield
        for p in self._patchers:
            p.stop()
        from models import quality as mod
        for attr in ['log_status_change', 'OrderStatus', 'ProductionStatus']:
            if hasattr(mod, attr):
                delattr(mod, attr)

    # ── create 深度覆盖 ──────────────────────────────────

    def test_create_with_record_items(self):
        """create: 带 record_items 的完整流程"""
        from models.quality import QualityDAO
        dao = QualityDAO()
        # 模拟 _ensure_inspection_columns: 3 次 fetchone 返回 None
        # 模拟 _get_next_inspection_seq: 1 次 fetchone
        self.mock_cursor.fetchone.side_effect = [
            None, None, None,
            {"next_seq": 1},
        ]
        self.mock_cursor.lastrowid = 100
        result = dao.create({
            "order_id": 10,
            "order_no": "ORD-001",
            "production_id": 5,
            "inspection_type": "终检",
            "result": "合格",
            "defect_qty": "0",
            "defect_description": "",
            "handling_method": "",
            "inspector": "张三",
            "remark": "",
            "process_name": "编织",
            "inspection_items": "",
            "record_items": [
                {"inspection_item": "尺寸", "measured_value": "100",
                 "standard_value": "100", "tolerance": "±1", "is_passed": True},
                {"inspection_item": "外观", "measured_value": "良好",
                 "standard_value": "良好", "tolerance": "", "is_passed": False},
            ],
        })
        assert result == 100
        # 验证插入 quality_record_items 被调用两次
        insert_calls = [c for c in self.mock_cursor.execute.call_args_list
                        if 'quality_record_items' in str(c)]
        assert len(insert_calls) == 2

    def test_create_defect_qty_exception(self):
        """create: defect_qty 异常路径 → 默认为 0"""
        from models.quality import QualityDAO
        self.mock_cursor.fetchone.side_effect = [None, None, None, {"next_seq": 1}]
        self.mock_cursor.lastrowid = 101
        result = QualityDAO().create({
            "order_id": 1,
            "defect_qty": "not_a_number",
            "production_id": None,
        })
        assert result == 101

    # ── confirm_order_completion 深度覆盖 ─────────────────

    def test_confirm_order_completion_full(self):
        """confirm_order_completion: 完整流程（订单存在）"""
        from models.quality import QualityDAO
        # 一个连接，多个 cursor（每 close 一次就换新）
        # confirm_order_completion 流程: SELECT(1次) → INSERT(1)+UPDATE(2) = 3次 execute
        self.mock_cursor.fetchone.return_value = {"quantity": 100, "unit": "米"}
        QualityDAO().confirm_order_completion(1)
        # 验证调用了 INSERT finished_goods
        calls = [c for c in self.mock_cursor.execute.call_args_list
                 if 'finished_goods' in str(c[0])]
        assert len(calls) == 1
        # 验证 UPDATE orders
        orders_calls = [c for c in self.mock_cursor.execute.call_args_list
                        if 'orders' in str(c[0]) and 'UPDATE' in str(c[0])]
        assert len(orders_calls) >= 1
        # 验证 UPDATE production_orders
        prod_calls = [c for c in self.mock_cursor.execute.call_args_list
                      if 'production_orders' in str(c[0])]
        assert len(prod_calls) >= 1
        # 验证 log_status_change 被调用
        from models import quality
        quality.log_status_change.assert_called_once()

    def test_confirm_order_completion_order_not_found(self):
        """confirm_order_completion: 订单不存在时提前返回"""
        from models.quality import QualityDAO
        self.mock_cursor.fetchone.return_value = None
        QualityDAO().confirm_order_completion(999)
        # 此时应只执行了 SELECT 查询，不应有 INSERT/UPDATE
        called_sqls = [str(c[0]) for c in self.mock_cursor.execute.call_args_list]
        assert all('finished_goods' not in s for s in called_sqls)
        assert all('UPDATE orders' not in s.upper() for s in called_sqls)

    # ── update 深度覆盖 ──────────────────────────────────

    def test_update_multiple_fields(self):
        """update: 多字段拼接"""
        from models.quality import QualityDAO
        self.mock_cursor.rowcount = 1
        QualityDAO().update(1, {
            "result": "合格",
            "defect_description": "无",
            "defect_qty": 1,
            "inspector": "李四",
        })
        call_sql = str(self.mock_cursor.execute.call_args[0][0])
        assert 'SET' in call_sql.upper()
        assert 'result=%s' in call_sql
        assert 'defect_qty=%s' in call_sql
        assert 'inspector=%s' in call_sql

    def test_update_no_fields(self):
        """update: 无有效字段时提前返回"""
        from models.quality import QualityDAO
        QualityDAO().update(1, {"invalid_key": "value"})
        self.mock_cursor.execute.assert_not_called()

    def test_update_single_field(self):
        """update: 单个字段"""
        from models.quality import QualityDAO
        self.mock_cursor.rowcount = 1
        QualityDAO().update(5, {"remark": "已复检"})
        call_params = self.mock_cursor.execute.call_args[0][1]
        assert call_params == ["已复检", 5]

    # ── delete ───────────────────────────────────────────

    def test_delete(self):
        """delete: 正常删除"""
        from models.quality import QualityDAO
        self.mock_cursor.rowcount = 1
        QualityDAO().delete(10)
        self.mock_cursor.execute.assert_called_once_with(
            "DELETE FROM quality_records WHERE id=%s", (10,)
        )

    # ── get_all 深度覆盖 ─────────────────────────────────

    def test_get_all_with_inspection_type_filter(self):
        """get_all: 按 inspection_type 过滤"""
        from models.quality import QualityDAO
        self.mock_cursor.fetchall.return_value = [{"id": 1, "result": "合格"}]
        result = QualityDAO().get_all(filters={"inspection_type": "终检"})
        assert len(result) == 1
        call_sql = str(self.mock_cursor.execute.call_args[0][0])
        assert 'inspection_type' in call_sql

    def test_get_all_with_keyword_filter(self):
        """get_all: 按 keyword 过滤"""
        from models.quality import QualityDAO
        self.mock_cursor.fetchall.return_value = [{"id": 1}]
        result = QualityDAO().get_all(filters={"keyword": "客户A"})
        assert len(result) == 1

    def test_get_all_with_all_filters(self):
        """get_all: 同时使用 inspection_type + result + keyword"""
        from models.quality import QualityDAO
        self.mock_cursor.fetchall.return_value = [{"id": 1}]
        result = QualityDAO().get_all(filters={
            "inspection_type": "首检",
            "result": "不合格",
            "keyword": "测试",
        })
        assert len(result) == 1

    def test_get_all_inspection_type_all(self):
        """get_all: inspection_type='全部' 时不追加条件"""
        from models.quality import QualityDAO
        self.mock_cursor.fetchall.return_value = [{"id": 1}]
        QualityDAO().get_all(filters={"inspection_type": "全部"})
        call_sql = str(self.mock_cursor.execute.call_args[0][0])
        assert 'qr.inspection_type=%s' not in call_sql

    def test_get_all_result_all(self):
        """get_all: result='全部' 时不追加条件"""
        from models.quality import QualityDAO
        self.mock_cursor.fetchall.return_value = [{"id": 1}]
        QualityDAO().get_all(filters={"result": "全部"})
        call_sql = str(self.mock_cursor.execute.call_args[0][0])
        assert 'qr.result=%s' not in call_sql

    # ── get_stats 深度覆盖 ───────────────────────────────

    def test_get_stats_normal(self):
        """get_stats: 正常数据"""
        from models.quality import QualityDAO
        self.mock_cursor.fetchone.return_value = {
            "total": 100, "passed": 70, "failed": 20, "pending": 10
        }
        result = QualityDAO().get_stats()
        assert result["total"] == 100
        assert result["passed"] == 70
        assert result["failed"] == 20
        assert result["pending"] == 10
        assert result["pass_rate"] == "70.0%"

    def test_get_stats_all_passed(self):
        """get_stats: 全部合格"""
        from models.quality import QualityDAO
        self.mock_cursor.fetchone.return_value = {
            "total": 50, "passed": 50, "failed": 0, "pending": 0
        }
        result = QualityDAO().get_stats()
        assert result["pass_rate"] == "100.0%"

    def test_get_stats_all_failed(self):
        """get_stats: 全部不合格"""
        from models.quality import QualityDAO
        self.mock_cursor.fetchone.return_value = {
            "total": 5, "passed": 0, "failed": 5, "pending": 0
        }
        result = QualityDAO().get_stats()
        assert result["pass_rate"] == "0.0%"

    def test_get_stats_no_data(self):
        """get_stats: 无数据时 pass_rate = 0%"""
        from models.quality import QualityDAO
        self.mock_cursor.fetchone.return_value = {
            "total": 0, "passed": 0, "failed": 0, "pending": 0
        }
        result = QualityDAO().get_stats()
        assert result["pass_rate"] == "0%"

    def test_get_stats_row_is_none(self):
        """get_stats: fetchone 返回 None"""
        from models.quality import QualityDAO
        self.mock_cursor.fetchone.return_value = None
        result = QualityDAO().get_stats()
        assert result["total"] == 0
        assert result["passed"] == 0
        assert result["pass_rate"] == "0%"

    # ── get_by_id ────────────────────────────────────────

    def test_get_by_id_found(self):
        """get_by_id: 记录存在"""
        from models.quality import QualityDAO
        self.mock_cursor.fetchone.return_value = {"id": 42, "result": "合格"}
        result = QualityDAO().get_by_id(42)
        assert result is not None
        assert result["id"] == 42

    def test_get_by_id_not_found(self):
        """get_by_id: 记录不存在"""
        from models.quality import QualityDAO
        self.mock_cursor.fetchone.return_value = None
        result = QualityDAO().get_by_id(999)
        assert result is None

    # ── get_record_items ─────────────────────────────────

    def test_get_record_items_found(self):
        """get_record_items: 有明细"""
        from models.quality import QualityDAO
        self.mock_cursor.fetchall.return_value = [
            {"id": 1, "inspection_item": "尺寸", "is_passed": 1},
            {"id": 2, "inspection_item": "外观", "is_passed": 0},
        ]
        result = QualityDAO().get_record_items(100)
        assert len(result) == 2

    def test_get_record_items_empty(self):
        """get_record_items: 无明细"""
        from models.quality import QualityDAO
        self.mock_cursor.fetchall.return_value = []
        result = QualityDAO().get_record_items(999)
        assert len(result) == 0

    # ── create_full 深度覆盖 ─────────────────────────────

    def test_create_full_without_items(self):
        """create_full: 无明细项"""
        from models.quality import QualityDAO
        self.mock_cursor.lastrowid = 200
        record_id = QualityDAO().create_full(
            order_no="ORD-001",
            inspection_type="首检",
            process_name="编织",
            inspector="王五",
            items=[],
        )
        assert record_id == 200

    def test_create_full_with_items(self):
        """create_full: 带明细项"""
        from models.quality import QualityDAO
        self.mock_cursor.lastrowid = 201
        record_id = QualityDAO().create_full(
            order_no="ORD-002",
            inspection_type="中检",
            process_name="焊接",
            inspector="赵六",
            items=[
                {"inspection_item": "强度", "measured_value": "500",
                 "standard_value": "500", "tolerance": "±10", "is_passed": True},
            ],
            overall_result="合格",
            defect_description="无异常",
            defect_qty=0,
            handling_method="",
            status="quality_reported",
        )
        assert record_id == 201
        has_item_insert = any(
            'quality_record_items' in str(c[0])
            for c in self.mock_cursor.execute.call_args_list
        )
        assert has_item_insert

    def test_create_full_rollback_on_exception(self):
        """create_full: 异常时回滚"""
        from models.quality import QualityDAO
        self.mock_cursor.execute.side_effect = RuntimeError("DB error")
        with pytest.raises(RuntimeError):
            QualityDAO().create_full(
                order_no="ORD-003",
                inspection_type="终检",
                process_name="组装",
                inspector="孙七",
                items=[],
            )
        self.mock_conn.rollback.assert_called_once()

    # ── get_timeline ────────────────────────────────────

    def test_get_timeline_found(self):
        """get_timeline: 有时间线数据"""
        from models.quality import QualityDAO
        self.mock_cursor.fetchall.return_value = [
            {"id": 1, "order_no": "ORD-001", "inspection_type": "首检",
             "result": "合格", "record_date": "2026-06-01"},
            {"id": 2, "order_no": "ORD-001", "inspection_type": "终检",
             "result": "合格", "record_date": "2026-06-02"},
        ]
        result = QualityDAO().get_timeline("ORD-001")
        assert len(result) == 2

    def test_get_timeline_empty(self):
        """get_timeline: 无数据"""
        from models.quality import QualityDAO
        self.mock_cursor.fetchall.return_value = []
        result = QualityDAO().get_timeline("ORD-NONEXIST")
        assert len(result) == 0

    # ── _private 方法覆盖 ────────────────────────────────

    def test_ensure_inspection_columns(self):
        """_ensure_inspection_columns: 全部不存在时创建列"""
        from models.quality import QualityDAO
        self.mock_cursor.fetchone.side_effect = [None, None, None]
        QualityDAO()._ensure_inspection_columns()
        alter_calls = [c for c in self.mock_cursor.execute.call_args_list
                       if 'ALTER TABLE' in str(c[0]).upper()]
        assert len(alter_calls) == 3

    def test_ensure_inspection_columns_all_exist(self):
        """_ensure_inspection_columns: 所有列已存在"""
        from models.quality import QualityDAO
        self.mock_cursor.fetchone.side_effect = [
            {"Field": "inspection_seq"},
            {"Field": "inspection_no"},
            {"Field": "attachment_path"},
        ]
        QualityDAO()._ensure_inspection_columns()
        alter_calls = [c for c in self.mock_cursor.execute.call_args_list
                       if 'ALTER TABLE' in str(c[0]).upper()]
        assert len(alter_calls) == 0

    def test_get_next_inspection_seq(self):
        """_get_next_inspection_seq: 正常获取序号"""
        from models.quality import QualityDAO
        self.mock_cursor.fetchone.return_value = {"next_seq": 3}
        seq, inspection_no = QualityDAO()._get_next_inspection_seq(1, "首检")
        assert seq == 3
        assert inspection_no == "首检-3"
