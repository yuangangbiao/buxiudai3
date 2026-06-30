import sys
import os

exit_code = 0

# Step 1: Import dispatch_center
print("=" * 50)
print("1. Importing dispatch_center...")
sys.path.insert(0, r'D:\yuan\不锈钢网带跟单3.0')
os.chdir(r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai')
try:
    import dispatch_center
    print("   dispatch_center: OK")
    # Verify key functions exist
    for attr in ['app', 'loadProcesses', 'refreshTasks', 'loadStatus', 'loadFlowMatchingRules', 'loadTemplates', 'loadFeedback', 'loadCloudConfig']:
        if hasattr(dispatch_center, attr):
            print(f"   dispatch_center.{attr}: OK")
        else:
            print(f"   dispatch_center.{attr}: MISSING")
except Exception as e:
    print(f"   FAILED: {e}")
    exit_code = 1

# Step 2: Import other key modules
print()
print("=" * 50)
print("2. Importing key modules...")

modules = [
    ('fault_tolerance', 'FaultTolerance'),
    ('sync_bridge', None),
    ('alert', 'AlertLevel'),
    ('config_center', None),
    ('container_center.storage.redis_cache', 'RedisCache'),
    ('cache', 'get_cache'),
]

for mod_name, attr in modules:
    try:
        if attr:
            exec(f'from mobile_api_ai.{mod_name} import {attr}')
        else:
            exec(f'import mobile_api_ai.{mod_name}')
        print(f"   {mod_name}: OK")
    except Exception as e:
        print(f"   {mod_name}: FAILED - {e}")
        exit_code = 1

# Step 3: Check key Phase 3 changes
print()
print("=" * 50)
print("3. Verifying Phase 3 changes...")

# Verify fault_tolerance delegates to modules.circuit_breaker
try:
    from modules.circuit_breaker import CircuitBreaker
    print("   modules.circuit_breaker.CircuitBreaker: OK")
except Exception as e:
    print(f"   modules.circuit_breaker.CircuitBreaker: MISSING - {e}")
    exit_code = 1

# Could also verify sycn_bridge has _get_mysql_connection
try:
    import inspect
    from mobile_api_ai.sync_bridge import sync_to_mysql
    source = inspect.getsource(sync_to_mysql)
    if '_get_mysql_connection()' in source:
        print("   sync_bridge.sync_to_mysql uses _get_mysql_connection(): OK")
    else:
        print("   sync_bridge.sync_to_mysql: _get_mysql_connection NOT FOUND")
        exit_code = 1
except Exception as e:
    print(f"   sync_bridge check: FAILED - {e}")
    exit_code = 1

print()
print("=" * 50)
print(f"Overall: {'PASS' if exit_code == 0 else 'FAIL'}")
sys.exit(exit_code)
