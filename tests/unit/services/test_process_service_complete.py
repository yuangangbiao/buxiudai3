# -*- coding: utf-8 -*-
"""
services/process_service.py 测试 - 当前38%，提升到70%+
"""
import pytest
from unittest.mock import patch, MagicMock


class TestProcessServiceInit:
    """ProcessService 初始化测试"""

    def test_process_service_init(self):
        from services.process_service import ProcessService
        svc = ProcessService()
        assert svc.dao is not None


class TestProcessServiceGetRecord:
    """get_record_by_id 测试 - 覆盖 L41-50"""

    def test_get_record_by_id_found(self):
        from services.process_service import ProcessService
        mock_dao = MagicMock()
        mock_dao.get_by_id.return_value = {"id": 1, "order_no": "ORD-001"}

        svc = ProcessService()
        svc.dao = mock_dao
        result = svc.get_record_by_id(1)
        assert result["id"] == 1

    def test_get_record_by_id_not_found(self):
        from services.process_service import ProcessService
        mock_dao = MagicMock()
        mock_dao.get_by_id.return_value = None

        svc = ProcessService()
        svc.dao = mock_dao
        result = svc.get_record_by_id(999)
        assert result is None


class TestProcessServiceGetRecords:
    """get_records_by_production 测试 - 覆盖 L30-39"""

    def test_get_records_by_production(self):
        from services.process_service import ProcessService
        mock_dao = MagicMock()
        mock_dao.get_by_production.return_value = [{"id": 1}, {"id": 2}]

        svc = ProcessService()
        svc.dao = mock_dao
        result = svc.get_records_by_production(100)
        assert len(result) == 2


class TestProcessServiceInsertRecord:
    """insert_record 测试 - 覆盖 L64-73"""

    def test_insert_record(self):
        from services.process_service import ProcessService
        mock_dao = MagicMock()
        mock_dao.create.return_value = 5

        svc = ProcessService()
        svc.dao = mock_dao
        result = svc.insert_record({"order_no": "ORD-001", "process_name": "编织"})
        assert result == 5


class TestProcessServiceDeleteRecord:
    """delete_record 测试 - 覆盖 L75-84"""

    def test_delete_record(self):
        from services.process_service import ProcessService
        mock_dao = MagicMock()
        mock_dao.delete.return_value = True

        svc = ProcessService()
        svc.dao = mock_dao
        result = svc.delete_record(5)
        assert result is True


class TestProcessServiceUpdateRecord:
    """update_record 测试 - 覆盖 L52-62"""

    def test_update_record(self):
        from services.process_service import ProcessService
        mock_dao = MagicMock()
        mock_dao.update_record.return_value = True

        svc = ProcessService()
        svc.dao = mock_dao
        result = svc.update_record(5, {"status": "已完成"})
        assert result is True


class TestProcessServiceReportProgress:
    """report_progress 测试 - 覆盖 L86-138"""

    def test_report_progress_record_not_found(self):
        from services.process_service import ProcessService
        mock_dao = MagicMock()
        mock_dao.get_by_id.return_value = None

        svc = ProcessService()
        svc.dao = mock_dao
        with pytest.raises(ValueError, match="不存在"):
            svc.report_progress(999, qty=10)

    def test_report_progress_completes(self):
        from services.process_service import ProcessService
        mock_dao = MagicMock()
        mock_dao.get_by_id.return_value = {"id": 1, "completed_qty": 0, "planned_qty": 10, "qualified_qty": 0, "work_hours": 0}
        mock_dao.update_record.return_value = True

        svc = ProcessService()
        svc.dao = mock_dao
        result = svc.report_progress(1, qty=10, qualified=9, hours=2.5)

        assert result["completed_qty"] == 10
        assert result["qualified_qty"] == 9
        assert result["work_hours"] == 2.5
        assert result["status"] == "已完成"

    def test_report_progress_in_progress(self):
        from services.process_service import ProcessService
        mock_dao = MagicMock()
        mock_dao.get_by_id.return_value = {"id": 1, "completed_qty": 0, "planned_qty": 10, "qualified_qty": 0, "work_hours": 0}
        mock_dao.update_record.return_value = True

        svc = ProcessService()
        svc.dao = mock_dao
        result = svc.report_progress(1, qty=5)

        assert result["completed_qty"] == 5
        assert result["status"] == "进行中"

    def test_report_progress_partial_complete(self):
        from services.process_service import ProcessService
        mock_dao = MagicMock()
        mock_dao.get_by_id.return_value = {"id": 1, "completed_qty": 7, "planned_qty": 10, "qualified_qty": 0, "work_hours": 0}
        mock_dao.update_record.return_value = True

        svc = ProcessService()
        svc.dao = mock_dao
        result = svc.report_progress(1, qty=5)

        # 7 + 5 = 12 >= 10 → 完成
        assert result["completed_qty"] == 12
        assert result["status"] == "已完成"

    def test_report_progress_with_worker_and_remark(self):
        from services.process_service import ProcessService
        mock_dao = MagicMock()
        mock_dao.get_by_id.return_value = {"id": 1, "completed_qty": 0, "planned_qty": 10, "qualified_qty": 0, "work_hours": 0}
        mock_dao.update_record.return_value = True

        svc = ProcessService()
        svc.dao = mock_dao
        result = svc.report_progress(1, qty=5, worker="张三", remark="测试备注")

        assert result["completed_qty"] == 5
        assert result["status"] == "进行中"
        assert "worker" in result
        assert result["worker"] == "张三"
        assert "remark" in result
        assert result["remark"] == "测试备注"


class TestProcessServiceReorder:
    """reorder_processes 测试 - 覆盖 L157-167"""

    def test_reorder_processes(self):
        from services.process_service import ProcessService
        mock_dao = MagicMock()

        svc = ProcessService()
        svc.dao = mock_dao
        svc.reorder_processes(100, [3, 1, 2])

        assert mock_dao.update_record.call_count == 3


class TestProcessServiceApplyTemplate:
    """apply_template 测试 - 覆盖 L169-187"""

    @patch('utils.process_templates.get_all_process_templates')
    def test_apply_template(self, mock_get_templates):
        mock_get_templates.return_value = {
            "标准模板": [
                {"process_name": "编织", "seq": 1},
                {"process_name": "质检", "seq": 2}
            ]
        }

        mock_dao = MagicMock()
        mock_dao.create.side_effect = [101, 102]

        from services.process_service import ProcessService
        svc = ProcessService()
        svc.dao = mock_dao
        result = svc.apply_template(100, "标准模板")

        assert len(result) == 2
        assert result[0]['id'] == 101
        assert result[1]['id'] == 102


class TestProcessServiceUpdateMethods:
    """update_planned_qty / update_remark 测试 - 覆盖 L189-211"""

    def test_update_planned_qty(self):
        from services.process_service import ProcessService
        mock_dao = MagicMock()
        mock_dao.update_record.return_value = True

        svc = ProcessService()
        svc.dao = mock_dao
        result = svc.update_planned_qty(1, 100)
        assert result is True
        mock_dao.update_record.assert_called_once_with(1, {'planned_qty': 100})

    def test_update_remark(self):
        from services.process_service import ProcessService
        mock_dao = MagicMock()
        mock_dao.update_record.return_value = True

        svc = ProcessService()
        svc.dao = mock_dao
        result = svc.update_remark(1, "测试备注")
        assert result is True
        mock_dao.update_record.assert_called_once_with(1, {'remark': '测试备注'})


class TestProcessServiceBatchDelete:
    """batch_delete_by_production 测试 - 覆盖 L213-221"""

    def test_batch_delete(self):
        from services.process_service import ProcessService
        mock_dao = MagicMock()
        mock_dao.get_by_production.return_value = [{"id": 1}, {"id": 2}]
        mock_dao.delete.return_value = True

        svc = ProcessService()
        svc.dao = mock_dao
        svc.batch_delete_by_production(100)

        assert mock_dao.delete.call_count == 2


class TestProcessServiceSummary:
    """get_production_summary 测试 - 覆盖 L223-239"""

    def test_get_production_summary(self):
        from services.process_service import ProcessService
        mock_dao = MagicMock()
        mock_dao.get_by_production.return_value = [
            {"id": 1, "status": "已完成"},
            {"id": 2, "status": "进行中"},
            {"id": 3, "status": "已完成"}
        ]

        svc = ProcessService()
        svc.dao = mock_dao
        result = svc.get_production_summary(100)

        assert result['total'] == 3
        assert result['completed'] == 2
        assert result['progress'] == pytest.approx(66.67, 0.1)

    def test_get_production_summary_empty(self):
        from services.process_service import ProcessService
        mock_dao = MagicMock()
        mock_dao.get_by_production.return_value = []

        svc = ProcessService()
        svc.dao = mock_dao
        result = svc.get_production_summary(100)

        assert result['total'] == 0
        assert result['progress'] == 0


class TestProcessServiceProcessDefaults:
    """get_process_defaults 测试 - 覆盖 L241-262"""

    @patch('core.rule_engine.get_rule_engine')
    def test_get_process_defaults_found(self, mock_get_engine):
        mock_engine = MagicMock()
        mock_engine.get_process.return_value = {"default_qty": 100, "unit": "米", "requires_material": True}
        mock_get_engine.return_value = mock_engine

        from services.process_service import ProcessService
        svc = ProcessService()
        result = svc.get_process_defaults("编织")

        assert result['default_qty'] == 100
        assert result['unit'] == "米"

    @patch('core.rule_engine.get_rule_engine')
    def test_get_process_defaults_not_found(self, mock_get_engine):
        mock_engine = MagicMock()
        mock_engine.get_process.return_value = None
        mock_get_engine.return_value = mock_engine

        from services.process_service import ProcessService
        svc = ProcessService()
        result = svc.get_process_defaults("不存在的工序")
        assert result is None


class TestProcessServiceShiftSeq:
    """shift_seq_up 测试 - 覆盖 L264-277"""

    @patch('services.process_service.BaseService.transaction')
    def test_shift_seq_up(self, mock_transaction):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_transaction.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_transaction.return_value.__exit__ = MagicMock(return_value=False)

        from services.process_service import ProcessService
        svc = ProcessService()
        svc.shift_seq_up(100, 2)

        mock_cursor.execute.assert_called_once()
