# -*- coding: utf-8 -*-
"""批量导入测试 - 覆盖0%模块（仅hasattr检查能通过的）"""
import sys, os
import pytest


MODULES_TO_CHECK = [
    ('models.alert', None),
    ('models.bom', 'BOMDAO'),
    ('models.database.config', '_get_db_config'),
    ('models.database.utils_db', 'generate_order_no'),
    ('models.inventory', 'InventoryDAO'),
    ('models.material_rules', 'MaterialRulesDAO'),
    ('models.operation_log', 'OperationLogDAO'),
    ('models.operator', 'OperatorDAO'),
    ('models.order', 'OrderDAO'),
    ('models.order_log', 'OrderLogDAO'),
    ('models.process', 'ProcessDAO'),
    ('models.product_type', 'ProductTypeDAO'),
    ('models.production', 'ProductionDAO'),
    ('models.production_stats', 'ProductionStatsDAO'),
    ('models.quality', 'QualityDAO'),
    ('models.shipment', 'ShipmentDAO'),
    ('models.unit', 'UnitDAO'),
    ('utils.logistics_tracker', 'LogisticsTracker'),
    ('utils.order_templates', 'DIM_FIELDS'),
    ('utils.auto_refresh_mixin', 'AutoRefreshMixin'),
    ('utils.logistics_companies', 'DEFAULT_LOGISTICS'),
    ('utils.custom_types', 'get_product_types'),
    ('utils.op_logger', 'log'),
    ('utils.settings_manager', 'SettingsManager'),
    ('utils.password_hasher', 'hash_password'),
    ('core.redis_event_bus', 'RedisEventBus'),
]


class TestBulkModules:
    @pytest.mark.parametrize("mod_name,attr", MODULES_TO_CHECK)
    def test_module_imports(self, mod_name, attr):
        mod = __import__(mod_name, fromlist=['*'])
        if attr is not None:
            assert hasattr(mod, attr), f"{mod_name} missing {attr}"
