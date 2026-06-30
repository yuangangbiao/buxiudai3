import sys
sys.path.insert(0, 'mobile_api_ai')
sys.path.insert(0, '.')

results = []

# 1. fault_tolerance 兼容层
try:
    from fault_tolerance import FaultTolerance, fault_tolerance, RetryConfig
    results.append(('OK', 'fault_tolerance 兼容层导入正常', f'state={fault_tolerance.get_state()}'))
except Exception as e:
    results.append(('FAIL', 'fault_tolerance 导入', str(e)))

# 2. CC redis_cache 包装层
try:
    from container_center.storage.redis_cache import RedisCache, cache
    results.append(('OK', 'CC redis_cache 包装层导入正常', ''))
except Exception as e:
    results.append(('FAIL', 'CC redis_cache 导入', str(e)))

# 3. core.config 核心配置
try:
    from core.config import WECHAT_CORP_ID, WECHAT_AGENT_ID, FLASK_HOST, LOG_DIR
    results.append(('OK', 'core.config 配置导入正常', ''))
except Exception as e:
    results.append(('FAIL', 'core.config 导入', str(e)))

# 4. sync_bridge
try:
    from sync_bridge import sync_bp, _get_mysql_connection
    results.append(('OK', 'sync_bridge 导入正常', ''))
except Exception as e:
    results.append(('FAIL', 'sync_bridge 导入', str(e)))

# 5. alert.py 职责注释
try:
    from alert import send_alert, AlertLevel, AlertManager
    results.append(('OK', 'alert.py 导入正常', ''))
except Exception as e:
    results.append(('FAIL', 'alert.py 导入', str(e)))

# 6. config_center.py
try:
    from config_center import config_center_bp
    results.append(('OK', 'config_center 导入正常', ''))
except Exception as e:
    results.append(('FAIL', 'config_center 导入', str(e)))

# 7. modules.circuit_breaker 独立验证
try:
    from modules.circuit_breaker import CircuitBreaker, CircuitState, get_circuit_breaker
    cb = get_circuit_breaker('test', failure_threshold=5)
    results.append(('OK', 'modules.circuit_breaker 导入正常', f'state={cb.state.value}'))
except Exception as e:
    results.append(('FAIL', 'modules.circuit_breaker 导入', str(e)))

# 8. core.config 核心配置
try:
    from core.config import Config
    results.append(('OK', 'core.config Config 正常', ''))
except Exception as e:
    results.append(('FAIL', '旧 config.py 导入', str(e)))

print()
print('=' * 60)
print('   Phase 3 最终验证报告')
print('=' * 60)
for status, name, detail in results:
    icon = 'PASS' if status == 'OK' else 'FAIL'
    print(f'  [{icon}] {name}')
    if detail:
        print(f'         -> {detail}')
print('=' * 60)
total = len(results)
passed = sum(1 for r in results if r[0] == 'OK')
print(f'  总计: {passed}/{total} 通过')
print('=' * 60)
