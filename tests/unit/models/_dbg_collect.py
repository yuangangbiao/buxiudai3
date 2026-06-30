import sys
print('=== COLLECT TIME PATH ===')
for i, p in enumerate(sys.path[:5]):
    print(f'  [{i}] {p}')
try:
    import core
    print(f'core: {getattr(core, "__file__", "?")}')
except Exception as e:
    print(f'core FAIL: {e}')
try:
    from core.db import get_connection
    print('core.db OK')
except Exception as e:
    print(f'core.db FAIL: {e}')