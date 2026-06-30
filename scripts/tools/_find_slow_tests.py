# -*- coding: utf-8 -*-
"""找出 core 目录中哪些测试文件慢"""
import subprocess, sys, os

PY = sys.executable
CWD = r"d:\yuan\不锈钢网带跟单3.0"
TIMEOUT = 30
files = sorted([
    "tests/unit/core/test_config.py",
    "tests/unit/core/test_db_complete.py",
    "tests/unit/core/test_redis_event_bus.py",
    "tests/unit/core/test_error_handler_complete.py",
    "tests/unit/core/test_error_handler.py",
    "tests/unit/core/test_config_domain.py",
    "tests/unit/core/test_config_infra.py",
    "tests/unit/core/test_config_funcs.py",
    "tests/unit/core/test_config_ui.py",
    "tests/unit/core/test_process_code_classifier.py",
    "tests/unit/core/test_config_modules_complete.py",
    "tests/unit/core/test_error_codes_structured_complete.py",
    "tests/unit/core/test_db_compat_complete.py",
    "tests/unit/core/test_cors_config_complete.py",
    "tests/unit/core/test_event_bus_factory.py",
    "tests/unit/core/test_process_code_integration.py",
    "tests/unit/core/test_circuit_breaker_complete.py",
    "tests/unit/core/test_feature_flags_complete.py",
    "tests/unit/core/test_error_codes_complete.py",
    "tests/unit/core/test_common_queries_complete.py",
    "tests/unit/core/test_saga.py",
    "tests/unit/core/test_app.py",
    "tests/unit/core/test_event_store.py",
    "tests/unit/core/test_common_queries.py",
    "tests/unit/core/test_events.py",
    "tests/unit/core/test_logger.py",
    "tests/unit/core/test_event_bus.py",
    "tests/unit/core/test_exceptions.py",
    "tests/unit/core/test_error_codes.py",
    "tests/unit/core/test_json_safe.py",
    "tests/unit/core/test_rule_engine.py",
    "tests/unit/core/test_metrics.py",
    "tests/unit/core/test_circuit_breaker.py",
    "tests/unit/core/test_feature_flags.py",
    "tests/unit/core/test_process_code_custom.py",
    "tests/unit/core/test_register_process_ssot.py",
    "tests/unit/core/test_register_process_persistence.py",
    "tests/unit/core/test_process_code_order.py",
    "tests/unit/core/test_process_code.py",
    "tests/unit/core/test_db.py",
    "tests/unit/core/test_push_to_30.py",
    "tests/unit/core/test_push_50.py",
    "tests/unit/core/test_process_code_mysql.py",
    "tests/unit/core/test_core_modules.py",
    "tests/unit/core/test_constants_and_enums.py",
    "tests/unit/core/test_sprint30.py",
    "tests/unit/core/test_final_gaps.py",
    "tests/unit/core/test_gap_fillers.py",
    "tests/unit/core/test_coverage_fillers.py",
])

slow = []
for f in files:
    basename = os.path.basename(f)
    try:
        r = subprocess.run(
            [PY, "-m", "pytest", f, "--tb=no", "--no-cov", "-q"],
            capture_output=True, text=True, cwd=CWD, timeout=TIMEOUT
        )
        out = r.stdout + r.stderr
        lines = out.strip().split("\n")
        summary = [l for l in lines if "passed" in l or "failed" in l or "error" in l or "timeout" in l.lower() or "TIMEOUT" in l]
        if summary:
            print(f"  OK {basename}: {summary[-1].strip()}")
        else:
            print(f"  OK {basename}: (no summary)")
    except subprocess.TimeoutExpired:
        print(f"  SLOW {basename}: TIMEOUT (>30s)")
        slow.append(f)
    except Exception as e:
        print(f"  ERR {basename}: {e}")

print(f"\n{'='*50}")
if slow:
    print(f"⚠️  SLOW/TIMEOUT files ({len(slow)}):")
    for f in slow:
        print(f"  - {f}")
else:
    print("✅ All files completed within 30s")
