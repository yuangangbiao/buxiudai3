"""
验证保留的功能是否被误删
对比 backup 和清理后文件，列出所有消失函数
并与"应保留"清单对照，标记误删
"""
import re
import os

BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                     '云端部署包v1.1.1')

# ============================================================
# 应保留的函数清单（消息发送链路 + 操作员/部门CRUD）
# ============================================================
SHOULD_KEEP_DISPATCH = {
    # 任务分配/通知
    'assign_task', 'reassign_task', 'cancel_task', 'assign_task_to_all',
    'batch_assign', 'task_notify',
    # 流程推进/发送
    'advance_process', 'confirm_process_step', 'reject_process_step',
    'notify_process_step', 'get_process_tasks', 'delete_process_task',
    'send_process_task', 'send_all_pending',
    # 流程模板绑定
    'get_process_template_bindings', 'update_process_template_bindings',
    'reset_process_template_bindings',
    # 流程CRUD
    'list_processes', 'create_process', 'get_process_detail', 'delete_process',
    # 流程匹配规则
    'list_rules', 'save_rules', 'list_flow_matching_rules', 'save_flow_matching_rules',
    # 操作员管理
    'list_operators', 'create_operator', 'update_operator', 'delete_operator',
    'get_operator_tasks', 'sync_operators_from_wechat', 'get_wechat_departments',
    # 消息模板
    'list_templates', 'create_template', 'update_template', 'delete_template',
    'get_default_templates', 'get_template_variables', 'save_template_order',
    'reset_default_templates', 'get_template_preference', 'save_template_preference',
    'get_templates', 'save_template',
    # 消息发送
    'send_message', 'message_history', 'delete_message_history',
    # 工单状态变更（触发同步）
    'dispatch_update_workorder_status', 'delete_workorder', 'change_delivery_date',
    'register_workorder', 'auto_complete_report', 'confirm_by_wechat_reply',
    # 企业微信同步
    'sync_wechat_employees', 'list_wechat_users', 'handle_enterprise_structure_push',
    # 部门管理
    'get_departments', 'get_department_managers', 'save_department_managers',
    'get_process_departments', 'save_process_department', 'delete_process_department',
    # 全局/云端配置
    'get_global_config', 'save_global_config',
    'cloud_config', 'cloud_poll_data',
    # 云端消息处理
    'handle_cloud_message', 'handle_text_command', 'init_cloud_poller_from_config',
    'update_task_count', 'receive_help_request',
    # 质量
    'create_quality_task',
    # 前端页面
    'dispatch_center_page', 'serve_dispatch_center',
    # JS API
    'load_flow_matching_rules',
    # 其他辅助（保留）
    'get_workorder_detail',  # 工单详情（被流程推进使用）
}

SHOULD_KEEP_WECHAT = {
    'sync_task', 'sync_report', 'validate_input', 'check_drift',
    'create_fingerprint', 'reset_circuit_breaker', 'publish_outsource',
    'wechat_hook', 'verify_url', 'verify_signature', 'decrypt_echostr',
    'receive_message', 'wechat_send', 'proxy_send',
    'poll_messages', 'cloud_send',
    'wechat_report', 'confirm_report', '_notify_operator',
    '_get_cloud_api_key', 'require_api_key', 'get_app_dir',
    'init_services', 'init_wechat_services',
    '_extract_sync_request', '_check_confirmation', '_send_notification',
}


def extract_functions(filepath):
    """从文件中提取所有函数名"""
    funcs = set()
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    for m in re.finditer(r'^async\s+def\s+(\w+)\s*\(|^def\s+(\w+)\s*\(', content, re.MULTILINE):
        funcs.add(m.group(1) or m.group(2))
    return funcs


def check_file(label, backup_path, cleaned_path, should_keep):
    print(f"\n{'='*70}")
    print(f"检查: {label}")
    print(f"{'='*70}")

    if not os.path.exists(backup_path):
        print(f"  [SKIP] backup 文件不存在: {backup_path}")
        return
    if not os.path.exists(cleaned_path):
        print(f"  [SKIP] 清理后文件不存在: {cleaned_path}")
        return

    old_funcs = extract_functions(backup_path)
    new_funcs = extract_functions(cleaned_path)

    # 消失函数 = 在 backup 中有，但清理后没有
    disappeared = old_funcs - new_funcs
    # 新增函数 = 清理后有，但 backup 中没有
    added = new_funcs - old_funcs

    print(f"  backup 中函数数: {len(old_funcs)}")
    print(f"  清理后函数数:   {len(new_funcs)}")
    print(f"  消失函数数:     {len(disappeared)}")
    print(f"  新增函数数:     {len(added)}")

    if added:
        print(f"\n  --- 新增函数（已在清理中加入body）---")
        for f in sorted(added):
            print(f"    + {f}")

    if disappeared:
        print(f"\n  --- 消失函数详细分析 ---")
        for f in sorted(disappeared):
            if f in should_keep:
                print(f"    [!!! 误删 !!!] {f} - 应在保留清单中!")
            else:
                print(f"    [正常删除] {f}")
    else:
        print(f"\n  [OK] 无任何消失函数")

    # 检查应保留但事实上不在backup中的函数（可能已被移除或改名）
    not_in_old = should_keep - old_funcs
    not_in_new = should_keep - new_funcs
    if not_in_old:
        print(f"\n  --- 应保留函数在 backup 中不存在（可能清理前就已被改名/移除）---")
        for f in sorted(not_in_old):
            status = "[OK 存在]" if f in new_funcs else "[已丢失]"
            print(f"    {status} {f}")

    return disappeared, added


# ============================================================
print("=" * 70)
print("云端部署包 v1.1.1 - 保留功能完整性校验")
print("=" * 70)

dc_backup = os.path.join(BASE, 'dispatch_center.py.backup')
dc_cleaned = os.path.join(BASE, 'dispatch_center.py')
ws_backup = os.path.join(BASE, 'wechat_server.py.backup')
ws_cleaned = os.path.join(BASE, 'wechat_server.py')

dc_disappeared, _ = check_file('dispatch_center.py', dc_backup, dc_cleaned, SHOULD_KEEP_DISPATCH)
ws_disappeared, _ = check_file('wechat_server.py', ws_backup, ws_cleaned, SHOULD_KEEP_WECHAT)

# ============================================================
# 总结
# ============================================================
print(f"\n{'='*70}")
print("最终结论")
print(f"{'='*70}")

all_disappeared = (dc_disappeared or set()) | (ws_disappeared or set())
misdeleted = {f for f in all_disappeared if f in SHOULD_KEEP_DISPATCH or f in SHOULD_KEEP_WECHAT}

if misdeleted:
    print(f"\n[!!!] 发现 {len(misdeleted)} 个函数被误删:")
    for f in sorted(misdeleted):
        print(f"      !! {f}")
else:
    print(f"\n[OK] 未发现保留函数被误删，完整性校验通过!")

print(f"\n清理统计:")
print(f"  dispatch_center.py: 删除了 {len(dc_disappeared or set())} 个函数")
print(f"  wechat_server.py:   删除了 {len(ws_disappeared or set())} 个函数")
