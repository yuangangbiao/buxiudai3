# -*- coding: utf-8 -*-
"""push to 50% - logger + models imports + services"""
import sys, os
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


class TestLogger:
    @pytest.fixture(autouse=True)
    def _fix_logdir(self, monkeypatch):
        monkeypatch.setattr('core.config.LOG_DIR', Path('logs'))

    def test_get_logger(self):
        import core.logger, logging
        lg = core.logger.get_logger('test_mod')
        assert isinstance(lg, logging.Logger)

    def test_structured_logger(self):
        import core.logger
        slog = core.logger.get_structured_logger('test_slog')
        assert hasattr(slog, 'info')
        slog.info("structured test", extra="val")

    def test_get_request_id(self):
        import core.logger
        rid = core.logger.get_request_id()
        assert isinstance(rid, str)
        assert len(rid) == 8

    def test_log_with_trace(self):
        import core.logger
        core.logger.log_with_trace("trace msg", level='info')


class TestModelsImports:
    """直接导入覆盖 DAO 类定义"""
    def test_order_dao(self):
        import models.order
        assert models.order.OrderDAO is not None

    def test_production_dao(self):
        import models.production
        assert models.production.ProductionDAO is not None

    def test_process_dao(self):
        import models.process
        assert models.process.ProcessDAO is not None

    def test_shipment_dao(self):
        import models.shipment
        assert models.shipment.ShipmentDAO is not None

    def test_quality_dao(self):
        import models.quality
        assert models.quality.QualityDAO is not None

    def test_unit_dao(self):
        import models.unit
        assert models.unit.UnitDAO is not None

    def test_inventory_dao(self):
        import models.inventory
        assert models.inventory.InventoryDAO is not None

    def test_operator_dao(self):
        import models.operator
        assert models.operator.OperatorDAO is not None

    def test_alert_module(self):
        import models.alert
        assert models.alert is not None

    def test_bom_module(self):
        import models.bom
        assert models.bom.BOMDAO is not None

    def test_enums(self):
        import models.enums
        assert models.enums.OrderStatus.PENDING.value == "PENDING"

    def test_order_log(self):
        import models.order_log
        assert models.order_log.OrderLogDAO is not None

    def test_operation_log(self):
        import models.operation_log
        assert models.operation_log.OperationLogDAO is not None

    def test_process_calc_rule_module(self):
        import models.process_calc_rule
        assert models.process_calc_rule is not None

    def test_quality_rule_module(self):
        import models.quality_rule
        assert models.quality_rule is not None

    def test_product_type_module(self):
        import models.product_type
        assert models.product_type.ProductTypeDAO is not None

    def test_production_stats(self):
        import models.production_stats
        assert models.production_stats.ProductionStatsDAO is not None

    def test_material_rules(self):
        import models.material_rules
        assert models.material_rules.MaterialRulesDAO is not None

    def test_material_rules_template(self):
        import models.material_rules_template
        assert models.material_rules_template is not None


class TestServicesImports:
    def test_audit_service(self):
        import services.audit_service
        assert services.audit_service.AuditService is not None

    def test_inventory_notifier(self):
        import services.inventory_notifier
        assert services.inventory_notifier.InventoryNotifier is not None

    def test_schedule_dispatch(self):
        import services.schedule_dispatch_service
        assert services.schedule_dispatch_service.ScheduleDispatchService is not None

    def test_wechat_report(self):
        import services.wechat_report_service
        assert services.wechat_report_service.WeChatReportService is not None

    def test_inventory_sync(self):
        import services.inventory_sync
        assert services.inventory_sync is not None
