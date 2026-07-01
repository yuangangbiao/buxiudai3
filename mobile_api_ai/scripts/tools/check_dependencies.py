"""
检查保留函数是否调用了被删除的函数（依赖断裂检查）
只检查实际被删除的函数
"""
import re
import os

BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                     '云端部署包v1.1.1')

# 实际被删除的函数（从clean_unrelated_routes.py 执行输出的实际删除列表）
ACTUALLY_DELETED_DISPATCH = {
    'debug_process_names', 'index', 'list_pending_warehousing',
    'convert_all_tasks_to_public', 'report_task_progress',
    'receive_material_requirements', 'receive_material_outbound',
    'list_devices', 'debug_cc_workorders', 'backfill_processes',
    'list_repair_categories', 'delete_repair_category', 'complete_repair_record',
    'list_outsource_records', 'get_outsource_record', 'feedback_outsource_record',
    'receive_outsource_record', 'update_outsource_config',
    'list_alerts', 'get_dispatch_log',
    'workorder_stats', 'workorder_detail',
    'list_process_sub_steps', 'create_process_sub_step',
    'cloud_status', 'cloud_connection_test',
    'scheduler_manager_toggle',
    'server_list', 'server_stop', 'server_python_path',
    'list_documents',
}

ACTUALLY_DELETED_WECHAT = {
    'serve_static', 'get_sync_status', 'get_circuit_breaker_status',
    'get_queue_status', 'get_sync_tasks', 'get_task_status',
    'get_report_history', 'get_log_stats', 'get_users',
    'health', 'cloud_status', 'status', 'get_pending_requests',
}


def extract_functions_with_body(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    funcs = {}
    i = 0
    while i < len(lines):
        m = re.match(r'^(async\s+)?def\s+(\w+)\s*\(', lines[i].strip())
        if m:
            name = m.group(2)
            def_indent = len(lines[i]) - len(lines[i].lstrip())
            body_end = len(lines)
            for j in range(i + 1, len(lines)):
                stripped = lines[j].strip()
                if not stripped or stripped.startswith('#'):
                    continue
                indent = len(lines[j]) - len(lines[j].lstrip())
                if indent <= def_indent and not stripped.startswith('@'):
                    body_end = j
                    break
            funcs[name] = (i, lines[i + 1:body_end])
            i = body_end
        else:
            i += 1
    return funcs


def check_calls(funcs, deleted_set, file_label):
    issues = []
    for name, (line_no, body_lines) in funcs.items():
        body_text = ''.join(body_lines)
        for deleted in deleted_set:
            if deleted in name:
                continue
            pattern = r'\b' + re.escape(deleted) + r'\s*\('
            if re.search(pattern, body_text):
                issues.append((name, line_no, deleted))
    return issues


print("=" * 70)
print("精确依赖断裂检查（仅针对实际被删除的函数）")
print("=" * 70)

dc_path = os.path.join(BASE, 'dispatch_center.py')
ws_path = os.path.join(BASE, 'wechat_server.py')

dc_funcs = extract_functions_with_body(dc_path)
dc_issues = check_calls(dc_funcs, ACTUALLY_DELETED_DISPATCH, 'dispatch_center.py')

print(f"\n--- dispatch_center.py ({len(dc_funcs)} 个保留函数) ---")
if dc_issues:
    print(f"\n  [!!!] 发现 {len(dc_issues)} 处调用断裂:")
    for caller, line_no, callee in sorted(dc_issues, key=lambda x: (x[0], x[2])):
        print(f"    {caller} (L{line_no+1}) 调用了被删函数 -> {callee}")
else:
    print(f"  [OK] 无调用断裂")

ws_funcs = extract_functions_with_body(ws_path)
ws_issues = check_calls(ws_funcs, ACTUALLY_DELETED_WECHAT, 'wechat_server.py')

print(f"\n--- wechat_server.py ({len(ws_funcs)} 个保留函数) ---")
if ws_issues:
    print(f"\n  [!!!] 发现 {len(ws_issues)} 处调用断裂:")
    for caller, line_no, callee in sorted(ws_issues, key=lambda x: (x[0], x[2])):
        print(f"    {caller} (L{line_no+1}) 调用了被删函数 -> {callee}")
else:
    print(f"  [OK] 无调用断裂")

# ============================================================
print(f"\n{'='*70}")
print("编译检查")
print(f"{'='*70}")
import py_compile
for label, path in [('dispatch_center.py', dc_path), ('wechat_server.py', ws_path)]:
    try:
        py_compile.compile(path, doraise=True)
        print(f"  [OK] {label}")
    except py_compile.PyCompileError as e:
        print(f"  [FAIL] {label}: {e}")

print(f"\n{'='*70}")
all_ok = not dc_issues and not ws_issues
print("最终结论: ", "ALL OK - 无依赖断裂" if all_ok else "存在断裂需修复")
print(f"{'='*70}")
