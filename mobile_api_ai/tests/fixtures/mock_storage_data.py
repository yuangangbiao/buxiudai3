SAMPLE_PACKAGE = {
    'id': 'PKG001',
    'order_no': 'WO20260526001',
    'data_type': 'report',
    'status': 'pending',
    'data': {'content': '测试数据包'},
}

SAMPLE_DISPATCH_COMMAND = {
    'id': 'CMD001',
    'order_no': 'WO20260526001',
    'target_type': 'operator',
    'target_id': 'OP001',
    'command': 'start_production',
    'status': 'pending',
}

SAMPLE_PROCESS_RECORD = {
    'id': 'PR001',
    'order_no': 'WO20260526001',
    'steps': [
        {'name': '工单发布', 'status_key': 'released'},
        {'name': '生产执行', 'status_key': 'processing'},
    ],
    'current_step': 0,
}

SAMPLE_SUB_STEP = {
    'id': 'SS001',
    'process_id': 'PR001',
    'step_name': '焊接',
    'operator': '张三',
    'quantity': 10,
    'batch_no': 'B20260526001',
}

SAMPLE_COLLECTION_RECORD = {
    'id': 'COL001',
    'data_type': 'quality',
    'status': 'completed',
    'order_no': 'WO20260526001',
    'data': {'pass_rate': 0.98},
}

SAMPLE_SCHEDULE_RECORD = {
    'id': 'SCH001',
    'order_no': 'WO20260526001',
    'status': 'scheduled',
    'scheduled_date': '2026-05-27',
}

SAMPLE_COST = {
    'order_no': 'WO20260526001',
    'material_cost': 1000.0,
    'labor_cost': 500.0,
    'overhead_cost': 200.0,
    'total_cost': 1700.0,
    'revenue': 2500.0,
}
