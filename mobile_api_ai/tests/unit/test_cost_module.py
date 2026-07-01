# -*- coding: utf-8 -*-
import os
import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from flask import Flask

os.environ['CONTAINER_DB_PATH'] = ':memory:'
os.environ['USE_SQLITE'] = 'true'  # 测试环境使用 SQLite 内存模式


@pytest.fixture(scope='function')
def storage():
    # [F6 P7 物理清理 2026-06-10] SQLiteStorage 已物理移除, 改用 MemoryStorage (内存 dict 模拟)
    from storage_layer import MemoryStorage
    s = MemoryStorage()
    s.connect()
    yield s
    s.disconnect()


@pytest.fixture(scope='function')
def service(storage):
    from services.cost_service import CostService
    return CostService(storage)


@pytest.fixture(scope='function')
def app():
    _app = Flask(__name__)
    _app.config['TESTING'] = True
    from api.cost import bp
    _app.register_blueprint(bp)
    return _app


@pytest.fixture(scope='function')
def client(app):
    return app.test_client()


@pytest.fixture(scope='function')
def app_with_auth_disabled(app):
    from api.decorators import require_auth
    original = require_auth
    def dummy_decorator(f):
        return f
    import api.decorators
    api.decorators.require_auth = dummy_decorator
    yield app
    api.decorators.require_auth = original


@pytest.fixture(scope='function')
def client_without_auth(app_with_auth_disabled):
    return app_with_auth_disabled.test_client()


class TestStorageCostTables:
    """Storage Layer: 4 cost tables CRUD"""

    def test_save_and_get_order_cost(self, storage):
        ok = storage.save_order_cost({
            'order_no': 'ORD001', 'customer_name': 'CustomerA',
            'product_name': 'ProductX', 'quantity': 100, 'unit': 'meter'
        })
        assert ok is True
        cost = storage.get_order_cost('ORD001')
        assert cost is not None
        assert cost['order_no'] == 'ORD001'
        assert cost['customer_name'] == 'CustomerA'
        assert cost['quantity'] == 100

    def test_get_order_cost_not_found(self, storage):
        assert storage.get_order_cost('NOT_EXIST') is None

    def test_save_order_cost_update(self, storage):
        storage.save_order_cost({'order_no': 'ORD001', 'revenue': 1000})
        storage.save_order_cost({'order_no': 'ORD001', 'revenue': 2000})
        cost = storage.get_order_cost('ORD001')
        assert cost['revenue'] == 2000

    def test_get_all_order_costs_pagination(self, storage):
        for i in range(5):
            storage.save_order_cost({'order_no': f'ORD{i}', 'revenue': i * 100})
        items = storage.get_all_order_costs(limit=3, offset=0)
        assert len(items) == 3
        total = storage.count_order_costs()
        assert total == 5

    def test_get_all_order_costs_search(self, storage):
        storage.save_order_cost({'order_no': 'ORD001', 'customer_name': 'Huawei'})
        storage.save_order_cost({'order_no': 'ORD002', 'customer_name': 'Alibaba'})
        items = storage.get_all_order_costs(search='Huawei')
        assert len(items) == 1
        assert items[0]['order_no'] == 'ORD001'

    def test_get_all_order_costs_filter_by_status(self, storage):
        storage.save_order_cost({'order_no': 'ORD001', 'status': 'calculated'})
        storage.save_order_cost({'order_no': 'ORD002', 'status': 'draft'})
        items = storage.get_all_order_costs(status='calculated')
        assert len(items) == 1

    def test_count_order_costs(self, storage):
        assert storage.count_order_costs() == 0
        storage.save_order_cost({'order_no': 'ORD001'})
        assert storage.count_order_costs() == 1
        storage.save_order_cost({'order_no': 'ORD002', 'status': 'calculated'})
        assert storage.count_order_costs(status='calculated') == 1

    def test_delete_order_cost_cascades_details(self, storage):
        storage.save_order_cost({'order_no': 'ORD001'})
        storage.save_order_cost_detail({'order_no': 'ORD001', 'cost_type': 'material', 'amount': 100})
        ok = storage.delete_order_cost('ORD001')
        assert ok is True
        assert storage.get_order_cost('ORD001') is None
        assert storage.get_order_cost_details('ORD001') == []

    def test_save_and_get_order_cost_details(self, storage):
        ok = storage.save_order_cost_detail({
            'order_no': 'ORD001', 'cost_type': 'material',
            'source_type': 'auto_material', 'source_id': 'wire',
            'description': 'material: wire x 50', 'quantity': 50,
            'unit': 'meter', 'unit_price': 20, 'amount': 1000
        })
        assert ok is True
        details = storage.get_order_cost_details('ORD001')
        assert len(details) == 1
        assert details[0]['cost_type'] == 'material'
        assert details[0]['amount'] == 1000

    def test_get_order_cost_details_empty(self, storage):
        assert storage.get_order_cost_details('NO_COST') == []

    def test_delete_order_cost_detail(self, storage):
        storage.save_order_cost_detail({
            'order_no': 'ORD001', 'cost_type': 'material', 'amount': 500
        })
        details = storage.get_order_cost_details('ORD001')
        detail_id = details[0]['id']
        ok = storage.delete_order_cost_detail(detail_id)
        assert ok is True
        assert storage.get_order_cost_details('ORD001') == []

    def test_delete_nonexistent_detail(self, storage):
        assert storage.delete_order_cost_detail(99999) is False

    def test_material_price_crud(self, storage):
        ok = storage.save_material_unit_price('wire', 25.5, 'meter')
        assert ok is True
        price = storage.get_material_unit_price('wire')
        assert price == 25.5
        prices = storage.get_all_material_prices()
        assert len(prices) == 1
        assert prices[0]['material_name'] == 'wire'

    def test_material_price_not_found(self, storage):
        assert storage.get_material_unit_price('not_exist') is None

    def test_material_price_update(self, storage):
        storage.save_material_unit_price('wire', 25.5, 'meter')
        storage.save_material_unit_price('wire', 30.0, 'meter')
        assert storage.get_material_unit_price('wire') == 30.0
        assert len(storage.get_all_material_prices()) == 1

    def test_labor_price_crud(self, storage):
        ok = storage.save_labor_unit_price('welding', 15.0, 'meter')
        assert ok is True
        price = storage.get_labor_unit_price('welding')
        assert price == 15.0
        prices = storage.get_all_labor_prices()
        assert len(prices) == 1
        assert prices[0]['process_name'] == 'welding'

    def test_labor_price_not_found(self, storage):
        assert storage.get_labor_unit_price('not_exist') is None

    def test_get_cost_summary_empty(self, storage):
        summary = storage.get_cost_summary()
        assert summary['total_orders'] == 0
        assert summary['total_revenue'] == 0
        assert summary['loss_count'] == 0

    def test_get_cost_summary_with_data(self, storage):
        storage.save_order_cost({
            'order_no': 'ORD001', 'revenue': 10000, 'total_cost': 8000,
            'profit': 2000, 'margin_rate': 20, 'status': 'confirmed',
            'material_cost': 5000, 'labor_cost': 2000
        })
        storage.save_order_cost({
            'order_no': 'ORD002', 'revenue': 5000, 'total_cost': 3000,
            'profit': 2000, 'margin_rate': 40, 'status': 'calculated',
            'material_cost': 2000, 'labor_cost': 1000
        })
        summary = storage.get_cost_summary()
        assert summary['total_orders'] == 2
        assert summary['total_revenue'] == 15000
        assert summary['total_material'] == 7000
        assert summary['total_labor'] == 3000
        assert summary['confirmed_count'] == 1
        assert summary['loss_count'] == 0


class TestCostService:
    """CostService business logic"""

    def test_get_order_cost(self, service, storage):
        storage.save_order_cost({'order_no': 'ORD001'})
        cost = service.get_order_cost('ORD001')
        assert cost['order_no'] == 'ORD001'

    def test_get_order_cost_not_found(self, service):
        assert service.get_order_cost('NOT_EXIST') is None

    def test_save_and_delete_order_cost(self, service, storage):
        ok = service.save_order_cost({'order_no': 'ORD001'})
        assert ok is True
        assert storage.get_order_cost('ORD001') is not None
        ok = service.delete_order_cost('ORD001')
        assert ok is True
        assert storage.get_order_cost('ORD001') is None

    def test_get_all_order_costs(self, service, storage):
        for i in range(3):
            storage.save_order_cost({'order_no': f'ORD{i}'})
        result = service.get_all_order_costs(page=1, page_size=2)
        assert result['total'] == 3
        assert len(result['items']) == 2
        assert result['total_pages'] == 2

    def test_add_cost_detail_triggers_recalculate(self, service, storage):
        storage.save_order_cost({
            'order_no': 'ORD001', 'material_cost': 0, 'labor_cost': 0,
            'overhead_cost': 0, 'outsourcing_cost': 0, 'other_cost': 0,
            'total_cost': 0, 'profit': 0, 'margin_rate': 0, 'revenue': 0
        })
        ok = service.add_cost_detail({
            'order_no': 'ORD001', 'cost_type': 'material', 'amount': 1000
        })
        assert ok is True
        cost = storage.get_order_cost('ORD001')
        assert cost['material_cost'] == 1000
        assert cost['total_cost'] == 1000

    def test_delete_cost_detail_triggers_recalculate(self, service, storage):
        storage.save_order_cost({
            'order_no': 'ORD001', 'material_cost': 0, 'labor_cost': 0,
            'overhead_cost': 0, 'outsourcing_cost': 0, 'other_cost': 0,
            'total_cost': 0, 'profit': 0, 'margin_rate': 0, 'revenue': 0
        })
        service.add_cost_detail({
            'order_no': 'ORD001', 'cost_type': 'material', 'amount': 1000
        })
        detail = storage.get_order_cost_details('ORD001')[0]
        ok = service.delete_cost_detail(detail['id'])
        assert ok is True
        cost = storage.get_order_cost('ORD001')
        assert cost['material_cost'] == 0
        assert cost['total_cost'] == 0

    def test_set_revenue(self, service, storage):
        storage.save_order_cost({
            'order_no': 'ORD001', 'revenue': 0, 'total_cost': 8000,
            'material_cost': 5000, 'labor_cost': 3000,
            'overhead_cost': 0, 'outsourcing_cost': 0, 'other_cost': 0,
            'profit': 0, 'margin_rate': 0
        })
        ok = service.set_revenue('ORD001', 10000)
        assert ok is True
        cost = storage.get_order_cost('ORD001')
        assert cost['revenue'] == 10000
        assert cost['profit'] == 2000
        assert cost['margin_rate'] == 20.0

    def test_set_revenue_new_order(self, service, storage):
        ok = service.set_revenue('ORD_NEW', 5000)
        assert ok is True
        cost = storage.get_order_cost('ORD_NEW')
        assert cost['revenue'] == 5000

    def test_get_cost_details(self, service, storage):
        storage.save_order_cost_detail({
            'order_no': 'ORD001', 'cost_type': 'material', 'amount': 500
        })
        details = service.get_cost_details('ORD001')
        assert len(details) == 1

    def test_material_price_crud(self, service, storage):
        ok = service.save_material_price('steel', 25.5, 'meter')
        assert ok is True
        prices = service.get_material_prices()
        assert len(prices) == 1
        assert prices[0]['unit_price'] == 25.5

    def test_labor_price_crud(self, service, storage):
        ok = service.save_labor_price('welding', 15.0, 'meter')
        assert ok is True
        prices = service.get_labor_prices()
        assert len(prices) == 1
        assert prices[0]['unit_price'] == 15.0

    def test_batch_save_material_prices(self, service, storage):
        prices = [
            {'material_name': 'steel', 'unit_price': 25.5, 'unit': 'meter'},
            {'material_name': 'wire', 'unit_price': 8.0, 'unit': 'kg'},
        ]
        count = service.batch_save_material_prices(prices)
        assert count == 2
        assert len(service.get_material_prices()) == 2

    def test_batch_save_labor_prices(self, service, storage):
        prices = [
            {'process_name': 'welding', 'unit_price': 15.0, 'unit': 'meter'},
            {'process_name': 'weaving', 'unit_price': 12.0, 'unit': 'meter'},
        ]
        count = service.batch_save_labor_prices(prices)
        assert count == 2
        assert len(service.get_labor_prices()) == 2

    def test_get_summary(self, service, storage):
        summary = service.get_summary()
        assert summary.get('total_orders', 0) == 0
        storage.save_order_cost({
            'order_no': 'ORD001', 'revenue': 10000, 'total_cost': 8000,
            'profit': 2000, 'margin_rate': 20, 'status': 'confirmed'
        })
        summary = service.get_summary()
        assert summary['total_orders'] == 1
        assert summary['total_revenue'] == 10000

    def test_recalculate_order_one_pass(self, service, storage):
        storage.save_order_cost({
            'order_no': 'ORD001', 'material_cost': 0, 'labor_cost': 0,
            'overhead_cost': 0, 'outsourcing_cost': 0, 'other_cost': 0,
            'total_cost': 0, 'profit': 0, 'margin_rate': 0, 'revenue': 20000
        })
        service.add_cost_detail({'order_no': 'ORD001', 'cost_type': 'material', 'amount': 3000})
        service.add_cost_detail({'order_no': 'ORD001', 'cost_type': 'material', 'amount': 2000})
        service.add_cost_detail({'order_no': 'ORD001', 'cost_type': 'labor', 'amount': 4000})
        service.add_cost_detail({'order_no': 'ORD001', 'cost_type': 'overhead', 'amount': 1000})
        cost = storage.get_order_cost('ORD001')
        assert cost['material_cost'] == 5000
        assert cost['labor_cost'] == 4000
        assert cost['overhead_cost'] == 1000
        assert cost['total_cost'] == 10000
        assert cost['profit'] == 10000
        assert cost['margin_rate'] == 50.0

    def test_price_cache_invalidation_on_save(self, service, storage):
        storage.save_material_unit_price('steel', 25.5, 'meter')
        price = service._get_cached_material_price('steel')
        assert price == 25.5
        assert 'steel' in service._material_price_cache
        service.save_material_price('steel', 30.0, 'meter')
        assert 'steel' not in service._material_price_cache
        price = service._get_cached_material_price('steel')
        assert price == 30.0

    def test_price_cache_thread_safe(self, service, storage):
        import threading
        def set_price():
            service._get_cached_material_price('wire')
        threads = [threading.Thread(target=set_price) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert 'wire' in service._material_price_cache


class TestCostServiceAutoCollect:
    """Auto-collection with dedup logic (Plan A core)"""

    def _setup_material_log(self, storage):
        cursor = storage._conn.cursor()
        cursor.execute('DROP TABLE IF EXISTS material_usage_log')
        cursor.execute('''
            CREATE TABLE material_usage_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_no TEXT, process_name TEXT,
                material_qty REAL, material_unit TEXT
            )
        ''')
        cursor.execute('''
            INSERT INTO material_usage_log (order_no, process_name, material_qty, material_unit)
            VALUES ('ORD001', 'steel', 50, 'meter')
        ''')
        cursor.execute('''
            INSERT INTO material_usage_log (order_no, process_name, material_qty, material_unit)
            VALUES ('ORD001', 'wire', 10, 'kg')
        ''')
        storage._conn.commit()

    def _setup_report_records(self, storage):
        cursor = storage._conn.cursor()
        cursor.execute('DROP TABLE IF EXISTS report_records')
        cursor.execute('''
            CREATE TABLE report_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_no TEXT, process_name TEXT,
                quantity REAL, unit TEXT, status TEXT
            )
        ''')
        cursor.execute('''
            INSERT INTO report_records (order_no, process_name, quantity, unit, status)
            VALUES ('ORD001', 'welding', 30, 'meter', 'approved')
        ''')
        cursor.execute('''
            INSERT INTO report_records (order_no, process_name, quantity, unit, status)
            VALUES ('ORD001', 'weaving', 20, 'meter', 'approved')
        ''')
        storage._conn.commit()

    def test_auto_collect_material_dedup(self, service, storage):
        self._setup_material_log(storage)
        storage.save_material_unit_price('steel', 20, 'meter')
        storage.save_material_unit_price('wire', 8, 'kg')
        storage.save_order_cost({
            'order_no': 'ORD001', 'material_cost': 0, 'labor_cost': 0,
            'overhead_cost': 0, 'outsourcing_cost': 0, 'other_cost': 0,
            'total_cost': 0, 'profit': 0, 'margin_rate': 0, 'revenue': 0
        })
        first_total = service._auto_collect_material('ORD001')
        assert first_total == pytest.approx(50 * 20 + 10 * 8)
        assert len(storage.get_order_cost_details('ORD001')) == 2
        second_total = service._auto_collect_material('ORD001')
        assert second_total == pytest.approx(first_total)
        assert len(storage.get_order_cost_details('ORD001')) == 2

    def test_auto_collect_labor_dedup(self, service, storage):
        self._setup_report_records(storage)
        storage.save_labor_unit_price('welding', 15, 'meter')
        storage.save_labor_unit_price('weaving', 12, 'meter')
        storage.save_order_cost({
            'order_no': 'ORD001', 'material_cost': 0, 'labor_cost': 0,
            'overhead_cost': 0, 'outsourcing_cost': 0, 'other_cost': 0,
            'total_cost': 0, 'profit': 0, 'margin_rate': 0, 'revenue': 0
        })
        first_total = service._auto_collect_labor('ORD001')
        assert first_total == pytest.approx(30 * 15 + 20 * 12)
        assert len(storage.get_order_cost_details('ORD001')) == 2
        second_total = service._auto_collect_labor('ORD001')
        assert second_total == pytest.approx(first_total)
        assert len(storage.get_order_cost_details('ORD001')) == 2

    def test_calculate_order_cost_full(self, service, storage):
        self._setup_material_log(storage)
        self._setup_report_records(storage)
        storage.save_material_unit_price('steel', 20, 'meter')
        storage.save_material_unit_price('wire', 8, 'kg')
        storage.save_labor_unit_price('welding', 15, 'meter')
        storage.save_labor_unit_price('weaving', 12, 'meter')
        cost = service.calculate_order_cost(
            'ORD001', customer_name='CustomerA', quantity=100
        )
        material_expected = 50 * 20 + 10 * 8
        labor_expected = 30 * 15 + 20 * 12
        assert cost['material_cost'] == pytest.approx(material_expected)
        assert cost['labor_cost'] == pytest.approx(labor_expected)
        assert cost['total_cost'] == pytest.approx(material_expected + labor_expected)
        assert cost['status'] == 'calculated'
        assert cost['customer_name'] == 'CustomerA'

    def test_calculate_idempotent(self, service, storage):
        self._setup_material_log(storage)
        self._setup_report_records(storage)
        storage.save_material_unit_price('steel', 20, 'meter')
        storage.save_material_unit_price('wire', 8, 'kg')
        storage.save_labor_unit_price('welding', 15, 'meter')
        storage.save_labor_unit_price('weaving', 12, 'meter')
        first = service.calculate_order_cost('ORD001')['total_cost']
        second = service.calculate_order_cost('ORD001')['total_cost']
        assert first == pytest.approx(second)

    def test_auto_collect_no_data_returns_existing(self, service, storage):
        storage.save_order_cost({
            'order_no': 'ORD001', 'material_cost': 0, 'labor_cost': 0,
            'overhead_cost': 0, 'outsourcing_cost': 0, 'other_cost': 0,
            'total_cost': 0, 'profit': 0, 'margin_rate': 0, 'revenue': 0
        })
        total = service._auto_collect_material('ORD001')
        assert total == 0
        storage.save_order_cost_detail({
            'order_no': 'ORD001', 'cost_type': 'material',
            'source_type': 'auto_material', 'source_id': 'existing',
            'amount': 500
        })
        total = service._auto_collect_material('ORD001')
        assert total == 500


class TestCostAPI:
    """Cost API endpoints"""

    @pytest.fixture(scope='function', autouse=True)
    def _inject_storage(self, storage):
        # [F6 P7 物理清理 2026-06-10] SQLiteStorage 移除, 改用 StorageType.MEMORY
        from storage_layer import StorageFactory, StorageType
        StorageFactory._instances[StorageType.MEMORY] = storage
        yield
        StorageFactory._instances.clear()

    def test_get_order_costs_empty(self, client):
        resp = client.get('/api/cost/orders')
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert body['code'] == 0
        assert body['data']['total'] == 0
        assert body['data']['items'] == []

    def test_calculate_and_query(self, client, storage):
        from services.cost_service import CostService
        svc = CostService(storage)
        svc.save_material_price('steel', 20, 'meter')
        cursor = storage._conn.cursor()
        cursor.execute('DROP TABLE IF EXISTS material_usage_log')
        cursor.execute('''
            CREATE TABLE material_usage_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_no TEXT, process_name TEXT,
                material_qty REAL, material_unit TEXT
            )
        ''')
        cursor.execute('''
            INSERT INTO material_usage_log (order_no, process_name, material_qty, material_unit)
            VALUES ('ORD001', 'steel', 50, 'meter')
        ''')
        storage._conn.commit()
        resp1 = client.post('/api/cost/orders/ORD001/calculate',
                           json={'customer_name': 'CustomerA', 'quantity': 100})
        assert resp1.status_code == 200
        body1 = json.loads(resp1.data)
        assert body1['code'] == 0
        assert body1['data']['order_no'] == 'ORD001'
        resp2 = client.get('/api/cost/orders/ORD001')
        assert resp2.status_code == 200
        body2 = json.loads(resp2.data)
        assert body2['data']['total_cost'] == pytest.approx(50 * 20)

    def test_set_revenue(self, client, storage):
        from services.cost_service import CostService
        svc = CostService(storage)
        svc.save_order_cost({
            'order_no': 'ORD001', 'total_cost': 1000,
            'material_cost': 1000, 'labor_cost': 0,
            'overhead_cost': 0, 'outsourcing_cost': 0, 'other_cost': 0,
            'profit': 0, 'margin_rate': 0, 'revenue': 0
        })
        resp = client.put('/api/cost/orders/ORD001/revenue', json={'revenue': 2000})
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert body['code'] == 0
        resp2 = client.get('/api/cost/orders/ORD001')
        body2 = json.loads(resp2.data)
        assert body2['data']['profit'] == 1000

    def test_add_delete_detail(self, client, storage):
        from services.cost_service import CostService
        svc = CostService(storage)
        svc.save_order_cost({
            'order_no': 'ORD001', 'revenue': 0, 'total_cost': 0,
            'material_cost': 0, 'labor_cost': 0,
            'overhead_cost': 0, 'outsourcing_cost': 0, 'other_cost': 0,
            'profit': 0, 'margin_rate': 0
        })
        resp = client.post('/api/cost/detail',
                          json={'order_no': 'ORD001', 'cost_type': 'material', 'amount': 500})
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert body['code'] == 0
        resp2 = client.get('/api/cost/detail/ORD001')
        assert resp2.status_code == 200
        body2 = json.loads(resp2.data)
        assert len(body2['data']) == 1
        detail_id = body2['data'][0]['id']
        resp3 = client.delete(f'/api/cost/detail/{detail_id}')
        assert resp3.status_code == 200
        body3 = json.loads(resp3.data)
        assert body3['code'] == 0

    def test_material_prices_api(self, client, storage):
        resp = client.get('/api/cost/material-prices')
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert body['data'] == []
        resp2 = client.post('/api/cost/material-prices',
                           json={'material_name': 'steel', 'unit_price': 25.5, 'unit': 'meter'})
        assert resp2.status_code == 200
        resp3 = client.post('/api/cost/material-prices',
                           json={'material_name': 'wire', 'unit_price': 8.0, 'unit': 'kg'})
        assert resp3.status_code == 200
        resp4 = client.get('/api/cost/material-prices')
        assert len(json.loads(resp4.data)['data']) == 2

    def test_material_prices_batch(self, client, storage):
        resp = client.post('/api/cost/material-prices',
                          json=[{'material_name': 'steel', 'unit_price': 25.5, 'unit': 'meter'},
                                {'material_name': 'wire', 'unit_price': 8.0, 'unit': 'kg'}])
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert body['code'] == 0
        assert body['data']['count'] == 2
        resp2 = client.get('/api/cost/material-prices')
        assert len(json.loads(resp2.data)['data']) == 2

    def test_labor_prices_api(self, client, storage):
        resp = client.get('/api/cost/labor-prices')
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert body['data'] == []
        resp2 = client.post('/api/cost/labor-prices',
                           json={'process_name': 'welding', 'unit_price': 15.0, 'unit': 'meter'})
        assert resp2.status_code == 200
        resp3 = client.post('/api/cost/labor-prices',
                           json={'process_name': 'weaving', 'unit_price': 12.0, 'unit': 'meter'})
        assert resp3.status_code == 200
        resp4 = client.get('/api/cost/labor-prices')
        assert len(json.loads(resp4.data)['data']) == 2

    def test_labor_prices_batch(self, client, storage):
        resp = client.post('/api/cost/labor-prices',
                          json=[{'process_name': 'welding', 'unit_price': 15.0, 'unit': 'meter'},
                                {'process_name': 'weaving', 'unit_price': 12.0, 'unit': 'meter'}])
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert body['code'] == 0
        assert body['data']['count'] == 2

    def test_summary_api(self, client, storage):
        resp = client.get('/api/cost/summary')
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert 'total_orders' in body['data']

    def test_get_order_costs_pagination(self, client, storage):
        from services.cost_service import CostService
        svc = CostService(storage)
        for i in range(5):
            svc.save_order_cost({'order_no': f'ORD{i}'})
        resp = client.get('/api/cost/orders?page=1&page_size=3')
        body = json.loads(resp.data)
        assert body['data']['total'] == 5
        assert len(body['data']['items']) == 3

    def test_get_order_costs_search(self, client, storage):
        from services.cost_service import CostService
        svc = CostService(storage)
        svc.save_order_cost({'order_no': 'ORD001', 'customer_name': 'Huawei'})
        svc.save_order_cost({'order_no': 'ORD002', 'customer_name': 'Alibaba'})
        resp = client.get('/api/cost/orders?search=Huawei')
        body = json.loads(resp.data)
        assert body['data']['total'] == 1


class TestContainerCenterCostHandler:
    """Container Center COST Handler"""

    @pytest.fixture(scope='function', autouse=True)
    def _inject_storage(self, storage):
        # [F6 P7 物理清理 2026-06-10] SQLiteStorage 移除, 改用 StorageType.MEMORY
        from storage_layer import StorageFactory, StorageType
        StorageFactory._instances[StorageType.MEMORY] = storage
        yield
        StorageFactory._instances.clear()

    @pytest.fixture(scope='function')
    def handler(self, storage):
        from container_center_v5 import DataCollector
        collector = DataCollector(storage)
        return collector

    def test_handle_calculate_action(self, handler, storage):
        storage.save_material_unit_price('steel', 20, 'meter')
        storage.save_order_cost({'order_no': 'ORD001'})
        cursor = storage._conn.cursor()
        cursor.execute('DROP TABLE IF EXISTS material_usage_log')
        cursor.execute('''
            CREATE TABLE material_usage_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_no TEXT, process_name TEXT,
                material_qty REAL, material_unit TEXT
            )
        ''')
        cursor.execute('''
            INSERT INTO material_usage_log (order_no, process_name, material_qty, material_unit)
            VALUES ('ORD001', 'steel', 50, 'meter')
        ''')
        storage._conn.commit()
        pkg = handler.collect('cost', 'cost calculate',
                              {'action': 'calculate', 'order_no': 'ORD001'})
        assert pkg is not None
        cost = storage.get_order_cost('ORD001')
        assert cost['status'] == 'calculated'

    def test_handle_add_detail_action(self, handler, storage):
        storage.save_order_cost({'order_no': 'ORD001'})
        pkg = handler.collect('cost', 'add detail',
                              {'action': 'add_detail', 'order_no': 'ORD001',
                               'cost_type': 'material', 'amount': 888})
        assert pkg is not None
        details = storage.get_order_cost_details('ORD001')
        assert len(details) >= 1
        cost = storage.get_order_cost('ORD001')
        assert cost['material_cost'] == 888

    def test_handle_set_revenue_action(self, handler, storage):
        storage.save_order_cost({
            'order_no': 'ORD001', 'total_cost': 5000,
            'material_cost': 3000, 'labor_cost': 2000,
            'overhead_cost': 0, 'outsourcing_cost': 0, 'other_cost': 0,
            'profit': 0, 'margin_rate': 0, 'revenue': 0
        })
        pkg = handler.collect('cost', 'set revenue',
                              {'action': 'set_revenue', 'order_no': 'ORD001', 'revenue': 10000})
        assert pkg is not None
        cost = storage.get_order_cost('ORD001')
        assert cost['revenue'] == 10000
        assert cost['profit'] == 5000
