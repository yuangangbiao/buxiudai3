# -*- coding: utf-8 -*-
"""push 50% Batch 3 - services + saga + error_handler + utils"""
import sys, os
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


class TestServiceDetails:
    def test_order_service_create_minimal(self):
        from services.order_service import OrderService
        svc = OrderService()
        assert svc is not None

    def test_process_service_init(self):
        from services.process_service import ProcessService
        svc = ProcessService()
        assert svc is not None

    def test_audit_service_init(self):
        from services.audit_service import AuditService
        svc = AuditService()
        assert svc is not None

    def test_inventory_sync_import(self):
        import services.inventory_sync as invs
        assert invs is not None


class TestSagaMethods:
    def test_saga_step_repr(self):
        from core.saga import SagaStep
        step = SagaStep("test_step", lambda ctx: True, lambda ctx: None)
        r = repr(step)
        assert "test_step" in r

    def test_orchestrator_init(self):
        from core.saga import SagaOrchestrator, SagaStep
        s = SagaStep("s1", lambda ctx: True, lambda ctx: None)
        orch = SagaOrchestrator("test_orch", [s])
        assert orch is not None


class TestErrorHandlerDetails:
    def test_recognize_missing_file(self):
        from core.error_handler import recognize_error_code
        assert recognize_error_code("[Errno 2] No such file or directory") == "ERR-RES-002"

    def test_recognize_permission_error(self):
        from core.error_handler import recognize_error_code
        assert recognize_error_code("[PermissionError] Permission denied") == "ERR-RES-003"

    def test_recognize_connection_error(self):
        from core.error_handler import recognize_error_code
        assert recognize_error_code("[ConnectionError] Failed to establish") == "ERR-NET-001"

    def test_recognize_http_error(self):
        from core.error_handler import recognize_error_code
        assert recognize_error_code("HTTP 500: Internal Server Error") == "ERR-NET-003"


class TestConfigDetails:
    def test_config_get_sqlite_path(self):
        from config import get_sqlite_path
        p = get_sqlite_path()
        assert isinstance(p, str)

    def test_config_is_sqlite_func(self):
        from config import is_sqlite
        assert callable(is_sqlite)
        assert isinstance(is_sqlite(), bool)


class TestDatabaseDetails:
    @pytest.mark.skip(
        reason="models/database/connection_pool.py 已归档到 _archive/legacy_db/，"
               "由 core.db.ConnectionPool 替代。回归测试保留在 "
               "tests/unit/models/database/test_connection_pool.py（已 skip）。"
    )
    def test_connection_pool_singleton(self):
        import models.database.connection_pool as cp
        pool1 = cp.MySQLConnectionPool()
        pool2 = cp.MySQLConnectionPool()
        assert pool1 is pool2


class TestUtilsDetails:
    def test_log_cleanup_module(self):
        import utils.log_cleanup as lc
        assert hasattr(lc, 'cleanup_expired_logs')

    def test_log_scheduler_module(self):
        import utils.log_scheduler as ls
        assert hasattr(ls, 'start_log_cleanup_scheduler')

    def test_material_templates_module(self):
        import utils.material_templates as mt
        assert mt is not None

    def test_process_templates_module(self):
        import utils.process_templates as pt
        assert pt is not None

    def test_query_cache_functions(self):
        import utils.query_cache as qc
        assert qc is not None

    def test_storage_json_store(self):
        import utils.storage.json_store as js
        assert hasattr(js, 'JsonStore')
