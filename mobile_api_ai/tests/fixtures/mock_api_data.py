SAMPLE_WORK_ORDER = {
    'id': 'WO001',
    'order_no': 'WO20260526001',
    'customer_name': '测试客户',
    'product_type': '不锈钢网带',
    'quantity': 100,
    'status': 'pending',
    'created_at': '2026-05-26T10:00:00',
}

SAMPLE_WORK_ORDERS = [
    SAMPLE_WORK_ORDER,
    {
        'id': 'WO002',
        'order_no': 'WO20260526002',
        'customer_name': '测试客户B',
        'product_type': '链条',
        'quantity': 50,
        'status': 'processing',
        'created_at': '2026-05-26T11:00:00',
    },
]

SAMPLE_OPERATORS = [
    {'id': 'OP001', 'name': '张三', 'department': '编织组', 'status': 'online'},
    {'id': 'OP002', 'name': '李四', 'department': '焊接组', 'status': 'offline'},
    {'id': 'OP003', 'name': '王五', 'department': '编织组', 'status': 'idle'},
]

SAMPLE_MESSAGE_RESPONSE = {
    'message_id': 'MSG001',
    'status': 'sent',
}

SAMPLE_DISTRIBUTE_RESPONSE = {
    'task_id': 'WO001',
    'operator_id': 'OP001',
    'status': 'distributed',
}

SAMPLE_QUERY_RESPONSE = {
    'items': SAMPLE_WORK_ORDERS,
    'total': 2,
    'page': 1,
    'size': 50,
}

SAMPLE_EMPTY_RESPONSE = {
    'items': [],
    'total': 0,
    'page': 1,
    'size': 50,
}
