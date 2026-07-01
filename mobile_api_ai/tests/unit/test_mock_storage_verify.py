def test_mock_storage_get_instance(mock_storage):
    from storage_layer import StorageFactory
    instance = StorageFactory.get_instance()
    assert instance is mock_storage


def test_mock_storage_save_package(mock_storage):
    result = mock_storage.save_package('order_no', 'data_type', 'status', 'data')
    assert result is True


def test_mock_storage_get_package(mock_storage):
    result = mock_storage.get_package('PKG001')
    assert result['id'] == 'PKG001'



def test_mock_storage_process_record(mock_storage):
    result = mock_storage.save_process_record('order_no', [])
    assert result is True


def test_mock_storage_sub_step(mock_storage):
    result = mock_storage.save_sub_step('PR001', '焊接', '张三', 10, 'B001')
    assert result is True
    summary = mock_storage.get_sub_step_summary('PR001')
    assert summary['total_quantity'] == 10


def test_mock_storage_schedule(mock_storage):
    result = mock_storage.save_schedule_record('WO001', '2026-05-27', 'scheduled')
    assert result is True
    record = mock_storage.get_schedule_record_by_order('WO001')
    assert record['status'] == 'scheduled'


def test_mock_storage_cost(mock_storage):
    cost = mock_storage.get_order_cost('WO001')
    assert cost['total_cost'] == 1700.0


def test_mock_storage_health(mock_storage):
    health = mock_storage.health_check()
    assert health['status'] == 'healthy'
