# -*- coding: utf-8 -*-
"""
工序服务单元测试 (ProcessService)
"""
import pytest
from unittest.mock import MagicMock, patch
import sys, os


class TestProcessService:
    """ProcessService 单元测试"""

    @pytest.fixture
    def svc(self):
        """创建 mock DAO 的 ProcessService 实例，patch 在 yield 期间保持活跃"""
        # 延迟导入避免 pytest 收集阶段命名冲突
        from services.process_service import ProcessService
        from models.process import ProcessDAO
        with patch.object(ProcessDAO, 'get_by_production', return_value=[]), \
             patch.object(ProcessDAO, 'get_by_id', return_value=None), \
             patch.object(ProcessDAO, 'create', return_value=1), \
             patch.object(ProcessDAO, 'update_record', return_value=True), \
             patch.object(ProcessDAO, 'delete', return_value=True):
            svc = ProcessService()
            yield svc

    def test_get_records_returns_list(self, svc):
        """get_records_by_production 应返回列表"""
        result = svc.get_records_by_production(1)
        assert isinstance(result, list)

    def test_report_progress_record_not_found(self, svc):
        """report_progress 在工序记录不存在时应抛出 ValueError"""
        with pytest.raises(ValueError):
            svc.report_progress(999, 10)

    def test_get_record_by_id_returns_none_for_missing(self, svc):
        """get_record_by_id 在记录不存在时返回 None"""
        result = svc.get_record_by_id(999)
        assert result is None

    def test_insert_record_returns_id(self, svc):
        """insert_record 应返回新记录 ID"""
        result = svc.insert_record({"process_name": "焊接", "planned_qty": 100})
        assert result == 1

    def test_delete_record_returns_true(self, svc):
        """delete_record 应返回 True"""
        result = svc.delete_record(1)
        assert result is True
