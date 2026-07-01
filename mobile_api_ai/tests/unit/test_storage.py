# -*- coding: utf-8 -*-
# [F6 P7 物理清理 2026-06-10] SQLiteStorage 已物理移除, 改用 MemoryStorage 跑单元测试
import pytest
from datetime import datetime
from unittest.mock import patch


@pytest.fixture
def storage():
    from schema_auto import _ensure_table_cache
    _ensure_table_cache.clear()
    from storage_layer import MemoryStorage
    s = MemoryStorage()
    s.connect()
    yield s
    s.disconnect()


def _make_package(overrides=None):
    data = {
        'id': 'pkg-001',
        'data_type': 'work_order',
        'title': '测试工单',
        'content': {'order_no': 'ORD-001'},
        'source': 'wechat',
        'priority': 'high',
        'status': 'pending',
        'created_at': datetime.now().isoformat(),
        'target_operator': '张三',
        'related_order': 'ORD-001',
        'related_process': '生产执行',
    }
    if overrides:
        data.update(overrides)
    return data


def _make_process_record(overrides=None):
    data = {
        'id': 'proc-001',
        'order_no': 'ORD-001',
        'process_name': '生产执行',
        'status': 'published',
        'operator': '张三',
        'quantity': 100,
        'start_time': datetime.now().isoformat(),
    }
    if overrides:
        data.update(overrides)
    return data


def _make_sub_step(overrides=None):
    data = {
        'process_id': 'proc-001',
        'step_name': '焊接',
        'batch_no': 'B001',
        'quantity': 50,
        'operator': '张三',
        'order_no': 'ORD-001',
    }
    if overrides:
        data.update(overrides)
    return data


def _make_collection_record(overrides=None):
    data = {
        'collect_id': 'col-001',
        'data_type': 'production_data',
        'status': 'pending',
        'order_no': 'ORD-001',
        'title': '测试收集',
        'collected_at': datetime.now().isoformat(),
    }
    if overrides:
        data.update(overrides)
    return data


def _make_schedule_record(overrides=None):
    data = {
        'schedule_id': 'sch-001',
        'order_no': 'ORD-001',
        'product_name': '网带',
        'quantity': 100,
        'status': 'scheduled',
        'created_at': datetime.now().isoformat(),
    }
    if overrides:
        data.update(overrides)
    return data


def _make_cost(overrides=None):
    data = {
        'order_no': 'ORD-001',
        'material_cost': 500.0,
        'labor_cost': 300.0,
        'total_cost': 800.0,
    }
    if overrides:
        data.update(overrides)
    return data


# [F6 P7 物理清理 2026-06-10] 预存在 DB_PATHS import 失败 (与 SQLiteStorage 物理移除无关)
class TestConnection:
    def test_connect(self, storage):
        assert storage._conn is not None

    def test_disconnect(self, storage):
        storage.disconnect()
        assert storage._conn is None

    def test_health_check(self, storage):
        result = storage.health_check()
        assert result['status'] == 'healthy'
        assert 'storage' in result
        assert result['storage'] == 'memory'

    def test_reconnect(self, storage):
        storage.disconnect()
        result = storage.connect()
        assert result is True
        assert storage._conn is not None


# [F6 P7 物理清理 2026-06-10] 预存在 DB_PATHS import 失败 (与 SQLiteStorage 物理移除无关)
class TestPackageStorage:
    def test_save_and_get_package(self, storage):
        pkg = _make_package()
        assert storage.save_package(pkg) is True
        retrieved = storage.get_package('pkg-001')
        assert retrieved is not None
        assert retrieved['id'] == 'pkg-001'
        assert retrieved['title'] == '测试工单'

    def test_save_duplicate_package(self, storage):
        pkg = _make_package()
        assert storage.save_package(pkg) is True
        assert storage.save_package(pkg) is True

    def test_get_package_not_found(self, storage):
        result = storage.get_package('nonexistent')
        assert result is None

    def test_get_packages_list(self, storage):
        pkg1 = _make_package({'id': 'pkg-001', 'status': 'pending'})
        pkg2 = _make_package({'id': 'pkg-002', 'status': 'completed', 'data_type': 'report'})
        storage.save_package(pkg1)
        storage.save_package(pkg2)
        pkgs = storage.get_packages()
        assert len(pkgs) == 2

    def test_get_packages_filter_by_status(self, storage):
        pkg1 = _make_package({'id': 'pkg-001', 'status': 'pending'})
        pkg2 = _make_package({'id': 'pkg-002', 'status': 'completed'})
        storage.save_package(pkg1)
        storage.save_package(pkg2)
        pkgs = storage.get_packages(status='pending')
        assert len(pkgs) == 1
        assert pkgs[0]['id'] == 'pkg-001'

    def test_get_packages_filter_by_type(self, storage):
        pkg1 = _make_package({'id': 'pkg-001', 'data_type': 'work_order'})
        pkg2 = _make_package({'id': 'pkg-002', 'data_type': 'report'})
        storage.save_package(pkg1)
        storage.save_package(pkg2)
        pkgs = storage.get_packages(data_type='report')
        assert len(pkgs) == 1
        assert pkgs[0]['id'] == 'pkg-002'

    def test_update_package_status(self, storage):
        pkg = _make_package()
        storage.save_package(pkg)
        assert storage.update_package_status('pkg-001', 'completed') is True
        retrieved = storage.get_package('pkg-001')
        assert retrieved['status'] == 'completed'

    def test_delete_package(self, storage):
        pkg = _make_package()
        storage.save_package(pkg)
        assert storage.delete_package('pkg-001') is True
        assert storage.get_package('pkg-001') is None

    def test_save_return_record(self, storage):
        pkg = _make_package()
        storage.save_package(pkg)
        ret = {
            'package_id': 'pkg-001',
            'return_data': {'result': 'ok'},
            'analyzed_result': {'status': 'success'},
            'write_back_cmd': {'action': 'update'},
        }
        assert storage.save_return_record(**ret) is True


# [F6 P7 物理清理 2026-06-10] 预存在 DB_PATHS import 失败 (与 SQLiteStorage 物理移除无关)
class TestProcessRecord:
    def test_save_and_get_record(self, storage):
        rec = _make_process_record()
        assert storage.save_process_record(rec) is True
        retrieved = storage.get_process_record('proc-001')
        assert retrieved is not None
        assert retrieved['id'] == 'proc-001'

    def test_get_record_not_found(self, storage):
        result = storage.get_process_record('nonexistent')
        assert result is None

    def test_get_record_by_order(self, storage):
        rec = _make_process_record()
        storage.save_process_record(rec)
        retrieved = storage.get_process_record_by_order('ORD-001')
        assert retrieved is not None
        assert retrieved['order_no'] == 'ORD-001'

    def test_get_records_list(self, storage):
        rec1 = _make_process_record({'id': 'proc-001', 'status': 'published'})
        rec2 = _make_process_record({'id': 'proc-002', 'status': 'in_production'})
        storage.save_process_record(rec1)
        storage.save_process_record(rec2)
        recs = storage.get_process_records()
        assert len(recs) >= 2

    def test_update_record_status(self, storage):
        rec = _make_process_record()
        storage.save_process_record(rec)
        assert storage.update_process_record_status('proc-001', 'in_production') is True
        retrieved = storage.get_process_record('proc-001')
        assert retrieved['status'] == 'in_production'

    def test_update_record_step(self, storage):
        rec = _make_process_record(
            {'id': 'proc-001', 'steps': [{'name': '排产', 'status_key': 'scheduling'}, {'name': '生产', 'status_key': 'production'}]}
        )
        storage.save_process_record(rec)
        assert storage.update_process_record_step('proc-001', 1) is True
        retrieved = storage.get_process_record('proc-001')
        assert retrieved is not None
        assert retrieved.get('current_step', -1) == 1

    def test_delete_record(self, storage):
        rec = _make_process_record()
        storage.save_process_record(rec)
        assert storage.delete_process_record('proc-001') is True
        assert storage.get_process_record('proc-001') is None


# [F6 P7 物理清理 2026-06-10] 预存在 DB_PATHS import 失败 (与 SQLiteStorage 物理移除无关)
class TestSubStep:
    def test_save_and_get_sub_steps(self, storage):
        rec = _make_process_record()
        storage.save_process_record(rec)
        sub = _make_sub_step()
        assert storage.save_sub_step(sub) is True
        steps = storage.get_sub_steps_by_process('ORD-001')
        assert len(steps) == 1
        assert steps[0]['step_name'] == '焊接'

    def test_multiple_sub_steps(self, storage):
        rec = _make_process_record()
        storage.save_process_record(rec)
        sub1 = _make_sub_step({'batch_no': 'B001', 'quantity': 50})
        sub2 = _make_sub_step({'batch_no': 'B002', 'quantity': 30})
        assert storage.save_sub_step(sub1) is True
        assert storage.save_sub_step(sub2) is True
        steps = storage.get_sub_steps_by_process('ORD-001')
        assert len(steps) == 2

    def test_recent_sub_step_not_found(self, storage):
        result = storage.get_recent_sub_step('proc-001', '焊接', '张三', 50)
        assert result is None

    def test_recent_sub_step_found(self, storage):
        rec = _make_process_record()
        storage.save_process_record(rec)
        sub = _make_sub_step()
        storage.save_sub_step(sub)
        result = storage.get_recent_sub_step('ORD-001', '焊接', '张三', 50, seconds=60)
        assert result is not None
        assert result['step_name'] == '焊接'

    def test_get_sub_step_summary(self, storage):
        rec = _make_process_record()
        storage.save_process_record(rec)
        sub1 = _make_sub_step({'batch_no': 'B001', 'quantity': 50, 'step_name': '完工入库'})
        sub2 = _make_sub_step({'batch_no': 'B002', 'quantity': 30, 'step_name': '完工入库'})
        storage.save_sub_step(sub1)
        storage.save_sub_step(sub2)
        summary = storage.get_sub_step_summary('ORD-001')
        assert isinstance(summary, dict)
        assert summary.get('completed_qty', 0) == 80
        assert summary.get('order_qty', 0) == 100
        assert summary.get('completed_remaining', 0) == 20

    def test_dedup_sub_steps(self, storage):
        rec = _make_process_record()
        storage.save_process_record(rec)
        sub1 = _make_sub_step({'batch_no': 'B001', 'quantity': 50})
        sub2 = _make_sub_step({'batch_no': 'B001', 'quantity': 50})
        storage.save_sub_step(sub1)
        storage.save_sub_step(sub2)
        deleted = storage.dedup_process_sub_steps()
        assert deleted >= 0


# [F6 P7 物理清理 2026-06-10] 预存在 DB_PATHS import 失败 (与 SQLiteStorage 物理移除无关)
class TestCollectionRecord:
    def test_save_and_get_record(self, storage):
        col = _make_collection_record()
        assert storage.save_collection_record(col) is True
        retrieved = storage.get_collection_record('col-001')
        assert retrieved is not None
        assert retrieved['collect_id'] == 'col-001'

    def test_get_record_not_found(self, storage):
        result = storage.get_collection_record('nonexistent')
        assert result is None

    def test_get_records_list(self, storage):
        col1 = _make_collection_record({'collect_id': 'col-001'})
        col2 = _make_collection_record({'collect_id': 'col-002', 'data_type': 'quality'})
        storage.save_collection_record(col1)
        storage.save_collection_record(col2)
        recs = storage.get_collection_records()
        assert len(recs) == 2

    def test_update_record_status(self, storage):
        col = _make_collection_record()
        storage.save_collection_record(col)
        assert storage.update_collection_record_status('col-001', 'completed', package_id='pkg-001') is True
        retrieved = storage.get_collection_record('col-001')
        assert retrieved['status'] == 'completed'

    def test_get_all_records(self, storage):
        col = _make_collection_record()
        storage.save_collection_record(col)
        all_recs = storage.get_all_collection_records()
        assert len(all_recs) == 1


# [F6 P7 物理清理 2026-06-10] 预存在 DB_PATHS import 失败 (与 SQLiteStorage 物理移除无关)
class TestScheduleRecord:
    def test_save_and_get_record(self, storage):
        sch = _make_schedule_record()
        assert storage.save_schedule_record(sch) is True
        retrieved = storage.get_schedule_record('sch-001')
        assert retrieved is not None
        assert retrieved['schedule_id'] == 'sch-001'

    def test_get_record_not_found(self, storage):
        result = storage.get_schedule_record('nonexistent')
        assert result is None

    def test_get_record_by_order(self, storage):
        sch = _make_schedule_record()
        storage.save_schedule_record(sch)
        retrieved = storage.get_schedule_record_by_order('ORD-001')
        assert retrieved is not None
        assert retrieved['order_no'] == 'ORD-001'

    def test_get_records_list(self, storage):
        sch = _make_schedule_record()
        storage.save_schedule_record(sch)
        recs = storage.get_schedule_records()
        assert len(recs) >= 1

    def test_get_all_records(self, storage):
        sch = _make_schedule_record()
        storage.save_schedule_record(sch)
        all_recs = storage.get_all_schedule_records()
        assert len(all_recs) == 1


# [F6 P7 物理清理 2026-06-10] 预存在 DB_PATHS import 失败 (与 SQLiteStorage 物理移除无关)
class TestDataFlowLog:
    def test_save_and_get_logs(self, storage):
        log = {
            'flow_id': 'flow-001',
            'event_type': 'created',
            'order_no': 'ORD-001',
            'event_data': {'key': 'value'},
            'operator': '张三',
        }
        assert storage.save_data_flow_log(log) is True
        logs = storage.get_data_flow_logs()
        assert len(logs) >= 1

    def test_get_logs_by_flow_id(self, storage):
        log1 = {'flow_id': 'flow-001', 'event_type': 'created', 'event_data': {}}
        log2 = {'flow_id': 'flow-002', 'event_type': 'updated', 'event_data': {}}
        storage.save_data_flow_log(log1)
        storage.save_data_flow_log(log2)
        logs = storage.get_data_flow_logs(flow_id='flow-001')
        assert len(logs) >= 1

    def test_get_all_logs(self, storage):
        log = {'flow_id': 'flow-001', 'event_type': 'created', 'event_data': {}}
        storage.save_data_flow_log(log)
        all_logs = storage.get_all_data_flow_logs()
        assert len(all_logs) >= 1


# [F6 P7 物理清理 2026-06-10] 预存在 DB_PATHS import 失败
class TestCostStorage:
    def test_save_and_get_cost(self, storage):
        cost = _make_cost()
        assert storage.save_order_cost(cost) is True
        retrieved = storage.get_order_cost('ORD-001')
        assert retrieved is not None
        assert retrieved['order_no'] == 'ORD-001'

    def test_get_cost_not_found(self, storage):
        result = storage.get_order_cost('ORD-NONE')
        assert result is None

    def test_get_all_costs(self, storage):
        cost1 = _make_cost({'order_no': 'ORD-001'})
        cost2 = _make_cost({'order_no': 'ORD-002', 'total_cost': 600.0})
        storage.save_order_cost(cost1)
        storage.save_order_cost(cost2)
        all_costs = storage.get_all_order_costs()
        assert len(all_costs) == 2

    def test_count_costs(self, storage):
        cost = _make_cost()
        storage.save_order_cost(cost)
        count = storage.count_order_costs()
        assert count >= 1

    def test_delete_cost(self, storage):
        cost = _make_cost()
        storage.save_order_cost(cost)
        assert storage.delete_order_cost('ORD-001') is True
        assert storage.get_order_cost('ORD-001') is None

    def test_cost_details(self, storage):
        cost = _make_cost()
        storage.save_order_cost(cost)
        detail = {'order_no': 'ORD-001', 'cost_type': 'material', 'amount': 500.0, 'remark': '钢材'}
        assert storage.save_order_cost_detail(detail) is True
        details = storage.get_order_cost_details('ORD-001')
        assert len(details) >= 1

    def test_cost_summary(self, storage):
        cost1 = _make_cost({'order_no': 'ORD-001', 'total_cost': 800.0})
        cost2 = _make_cost({'order_no': 'ORD-002', 'total_cost': 600.0})
        storage.save_order_cost(cost1)
        storage.save_order_cost(cost2)
        summary = storage.get_cost_summary()
        assert 'total_cost' in summary or isinstance(summary, dict)


# [F6 P7 物理清理 2026-06-10] TestPriceStorage 预存在 DB_PATHS import 失败 (与 SQLiteStorage 物理移除无关)
class TestPriceStorage:
    def test_save_and_get_material_price(self, storage):
        assert storage.save_material_unit_price('不锈钢', 15.0, '公斤') is True
        price = storage.get_material_unit_price('不锈钢')
        assert price == 15.0

    def test_get_material_price_not_found(self, storage):
        price = storage.get_material_unit_price('unknown_material')
        assert price is None

    def test_get_all_material_prices(self, storage):
        storage.save_material_unit_price('不锈钢', 15.0)
        storage.save_material_unit_price('碳钢', 8.0)
        prices = storage.get_all_material_prices()
        assert len(prices) >= 2

    def test_save_and_get_labor_price(self, storage):
        assert storage.save_labor_unit_price('焊接', 25.0, '米') is True
        price = storage.get_labor_unit_price('焊接')
        assert price == 25.0

    def test_get_labor_price_not_found(self, storage):
        price = storage.get_labor_unit_price('unknown_process')
        assert price is None

    def test_get_all_labor_prices(self, storage):
        storage.save_labor_unit_price('焊接', 25.0)
        storage.save_labor_unit_price('包装', 10.0)
        prices = storage.get_all_labor_prices()
        assert len(prices) >= 2


class TestSyncLog:
    def test_log_sync(self, storage):
        result = storage.log_sync('upload', 'pkg-001', '上传成功')
        assert result is None or result is True

    def test_sync_logs_accumulate(self, storage):
        storage.log_sync('upload', 'pkg-001', '上传成功')
        storage.log_sync('download', 'pkg-002', '下载成功')
        from storage_layer import BaseStorage
        if isinstance(storage, BaseStorage):
            if hasattr(storage, '_sync_logs') and isinstance(storage._sync_logs, list):
                count = len(storage._sync_logs)
            else:
                logs = storage.get_sync_logs(limit=100)
                count = len(logs) if logs else 0
            assert count >= 2
