# -*- coding: utf-8 -*-
"""Check all schedule_dispatch_service entries in sys.modules"""
import sys
import os

def pytest_runtest_call(item):
    if 'test_publish_schedule_success_fresh' not in item.nodeid:
        return
    schedule_entries = [(name, id(mod)) for name, mod in sys.modules.items() if 'schedule_dispatch' in name]
    print(f'\n>>> [CALL HOOK] schedule_dispatch modules:')
    for name, mid in schedule_entries:
        mod = sys.modules.get(name)
        print(f'  - {name} id={mid} file={getattr(mod, "__file__", None)}')
        if hasattr(mod, 'requests'):
            req = mod.requests
            print(f'    .requests={req} id={id(req)} type={type(req).__name__}')

    # Also list modules with name services.schedule_dispatch_service
    print('\n>>> All sys.modules keys with services:')
    for name in sorted(sys.modules.keys()):
        if 'services' in name:
            print(f'  - {name}')
