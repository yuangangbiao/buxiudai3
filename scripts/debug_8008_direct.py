import os, sys
sys.path.insert(0, r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai')

try:
    from sync_bridge import _enqueue_sync, _check_substep_rate_limit, sync_bp
    print('Imports OK')

    rl = _check_substep_rate_limit()
    print(f'Rate limit check: {rl}')

    data = {
        'order_no': 'ORD-202604210002',
        'step_name': '编制右旋',
        'process_code': 'P07',
        'quantity': 10,
        'operator': '苑岗彪'
    }
    qid = _enqueue_sync(data)
    print(f'Enqueue success, qid={qid}')
except Exception as e:
    import traceback
    print(f'Error: {type(e).__name__}: {e}')
    traceback.print_exc()
