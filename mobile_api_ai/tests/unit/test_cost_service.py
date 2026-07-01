# -*- coding: utf-8 -*-
"""
cost_service 单元测试

覆盖：
- CostService 初始化
- 材料/人工价格缓存
- 缓存失效
- 工单成本查询/保存/删除
- 分页查询
"""
import pytest
from unittest.mock import MagicMock


class TestCostServiceInit:
    """CostService 初始化测试"""

    def test_init(self):
        from services.cost_service import CostService
        storage = MagicMock()
        service = CostService(storage)
        assert service.storage is storage
        assert service._material_price_cache == {}
        assert service._labor_price_cache == {}

    def test_cost_types(self):
        from services.cost_service import CostService
        assert 'material' in CostService.COST_TYPES
        assert 'labor' in CostService.COST_TYPES

    def test_cost_labels(self):
        from services.cost_service import CostService
        assert CostService.COST_LABELS['material'] == '材料成本'


class TestMaterialPriceCache:
    """材料价格缓存测试"""

    def test_get_cached_material_price(self):
        from services.cost_service import CostService
        storage = MagicMock()
        storage.get_material_unit_price.return_value = 15.5
        service = CostService(storage)

        price1 = service._get_cached_material_price('钢板')
        price2 = service._get_cached_material_price('钢板')
        assert price1 == 15.5
        assert price2 == 15.5
        assert storage.get_material_unit_price.call_count == 1

    def test_get_cached_material_price_none(self):
        from services.cost_service import CostService
        storage = MagicMock()
        storage.get_material_unit_price.return_value = None
        service = CostService(storage)
        assert service._get_cached_material_price('钢板') == 0

    def test_cache_separate_keys(self):
        from services.cost_service import CostService
        storage = MagicMock()
        storage.get_material_unit_price.side_effect = lambda n: 10.0 if n == '钢板' else 20.0
        service = CostService(storage)
        assert service._get_cached_material_price('钢板') == 10.0
        assert service._get_cached_material_price('铝板') == 20.0


class TestLaborPriceCache:
    """人工价格缓存测试"""

    def test_get_cached_labor_price(self):
        from services.cost_service import CostService
        storage = MagicMock()
        storage.get_labor_unit_price.return_value = 25.0
        service = CostService(storage)
        assert service._get_cached_labor_price('焊接') == 25.0

    def test_labor_cache_reuse(self):
        from services.cost_service import CostService
        storage = MagicMock()
        storage.get_labor_unit_price.return_value = 25.0
        service = CostService(storage)
        service._get_cached_labor_price('焊接')
        service._get_cached_labor_price('焊接')
        assert storage.get_labor_unit_price.call_count == 1

    def test_labor_cache_none(self):
        from services.cost_service import CostService
        storage = MagicMock()
        storage.get_labor_unit_price.return_value = None
        service = CostService(storage)
        assert service._get_cached_labor_price('焊接') == 0


class TestInvalidatePriceCache:
    """缓存失效测试"""

    def test_invalidate(self):
        from services.cost_service import CostService
        storage = MagicMock()
        service = CostService(storage)
        service._material_price_cache['a'] = 10
        service._labor_price_cache['b'] = 20
        service.invalidate_price_cache()
        assert service._material_price_cache == {}
        assert service._labor_price_cache == {}


class TestOrderCostCRUD:
    """工单成本 CRUD 测试"""

    def test_get_order_cost(self):
        from services.cost_service import CostService
        storage = MagicMock()
        storage.get_order_cost.return_value = {'order_no': 'ORD001', 'total': 1000}
        service = CostService(storage)
        result = service.get_order_cost('ORD001')
        assert result['order_no'] == 'ORD001'

    def test_get_order_cost_none(self):
        from services.cost_service import CostService
        storage = MagicMock()
        storage.get_order_cost.return_value = None
        service = CostService(storage)
        assert service.get_order_cost('ORD999') is None

    def test_save_order_cost(self):
        from services.cost_service import CostService
        storage = MagicMock()
        storage.save_order_cost.return_value = True
        service = CostService(storage)
        result = service.save_order_cost({'order_no': 'ORD001', 'total': 1000})
        assert result is True

    def test_save_order_cost_adds_created_at(self):
        from services.cost_service import CostService
        storage = MagicMock()
        service = CostService(storage)
        service.save_order_cost({'order_no': 'ORD001'})
        assert 'created_at' in storage.save_order_cost.call_args[0][0]

    def test_save_order_cost_keeps_existing_created_at(self):
        from services.cost_service import CostService
        storage = MagicMock()
        service = CostService(storage)
        service.save_order_cost({'order_no': 'ORD001', 'created_at': '2026-01-01'})
        assert storage.save_order_cost.call_args[0][0]['created_at'] == '2026-01-01'

    def test_delete_order_cost(self):
        from services.cost_service import CostService
        storage = MagicMock()
        storage.delete_order_cost.return_value = True
        service = CostService(storage)
        assert service.delete_order_cost('ORD001') is True


class TestGetAllOrderCosts:
    """分页查询测试"""

    def test_pagination(self):
        from services.cost_service import CostService
        storage = MagicMock()
        storage.get_all_order_costs.return_value = [{'order_no': 'ORD001'}]
        storage.count_order_costs.return_value = 50
        service = CostService(storage)
        result = service.get_all_order_costs(page=2, page_size=20)
        assert result['page'] == 2
        assert result['page_size'] == 20
        assert result['total'] == 50
        assert result['total_pages'] == 3

    def test_pagination_zero_total(self):
        from services.cost_service import CostService
        storage = MagicMock()
        storage.get_all_order_costs.return_value = []
        storage.count_order_costs.return_value = 0
        service = CostService(storage)
        result = service.get_all_order_costs()
        assert result['total_pages'] == 0

    def test_pagination_exact_page(self):
        from services.cost_service import CostService
        storage = MagicMock()
        storage.get_all_order_costs.return_value = []
        storage.count_order_costs.return_value = 40
        service = CostService(storage)
        result = service.get_all_order_costs(page_size=20)
        assert result['total_pages'] == 2

    def test_query_with_filters(self):
        from services.cost_service import CostService
        storage = MagicMock()
        storage.get_all_order_costs.return_value = []
        storage.count_order_costs.return_value = 0
        service = CostService(storage)
        service.get_all_order_costs(status='active', search='ORD', sort_by='total', sort_order='desc')
        kwargs = storage.get_all_order_costs.call_args.kwargs
        assert kwargs['status'] == 'active'
        assert kwargs['search'] == 'ORD'
        assert kwargs['sort_by'] == 'total'
        assert kwargs['sort_order'] == 'desc'
