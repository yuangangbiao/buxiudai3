"""
清理与云端消息通讯无关的路由和函数
保留规则:
  - dispatch_center.py: 保留消息发送链路 + 操作员/部门CRUD
  - wechat_server.py: 保留消息同步(写入类) + 企业微信收发 + 云端发送
  - config_center.py: 全部删除（与消息通讯无关）
"""
import os
import re
import shutil

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEPLOY_DIR = os.path.join(PROJECT_DIR, '云端部署包v1.1.1')

# ============================================================
# dispatch_center.py 要删除的函数名
# (已核对真实函数名，非发送链路/非操作员部门CRUD的均删除)
# ============================================================
DISPATCH_DELETE_FUNCTIONS = {
    # 首页/状态
    'index',
    'get_status',
    # 仓库
    'list_pending_warehousing',
    # 任务操作（非发送链路）
    'report_task_progress',
    'convert_all_tasks_to_public',
    # 物料管理
    'receive_material_requirements',
    'sync_material_prepared',
    'receive_material_outbound',
    'query_material_requirements',
    # 设备管理
    'list_devices',
    'get_device_tasks',
    # 调试
    'debug_process_names',
    'debug_cc_workorders',
    'debug_cache_data',
    # 流程（非发送链路）
    'backfill_processes',
    'repair_process_products',
    # 报修管理
    'list_repair_categories',
    'add_repair_category',
    'delete_repair_category',
    'list_repair_records',
    'complete_repair_record',
    # 外协管理
    'list_outsource_records',
    'create_outsource_record',
    'get_outsource_record',
    'assign_outsource_record',
    'feedback_outsource_record',
    'complete_outsource_record',
    'receive_outsource_record',
    'get_outsource_config',
    'update_outsource_config',
    # 统计和预警
    'get_stats',
    'list_alerts',
    'dismiss_alert',
    'get_dispatch_log',
    # 工单管理（非发送链路）
    'workorder_stats',
    'dispatch_workorder_list',
    'workorder_detail',
    'refresh_workorder_status',
    # 工序子步骤（纯管理）
    'list_process_sub_steps',
    'get_process_sub_step_summary',
    'create_process_sub_step',
    # 云端状态/测试（非发送）
    'cloud_status',
    'cloud_connection_test',
    # 调度管理器（服务管理UI）
    'scheduler_manager_status',
    'scheduler_manager_toggle',
    'scheduler_manager_interval',
    # 服务管理
    'server_list',
    'server_start',
    'server_stop',
    'server_logs',
    'server_python_path',
    # 文档服务
    'list_documents',
    'get_document',
}

# ============================================================
# wechat_server.py 要删除的函数名
# (只保留：同步写入类、企业微信收发、云端发送、验证辅助)
# 删除：只读查询/监控/日志/静态文件/健康检查
# ============================================================
WECHAT_DELETE_FUNCTIONS = {
    # 静态文件服务
    'serve_static',
    # 同步监控（只读，非发送）
    'get_sync_status',
    'get_detailed_health',
    'get_circuit_breaker_status',
    'get_queue_status',
    'get_queue_stats',
    'get_sync_tasks',
    'get_sync_task',
    'get_task_status',
    # 同步报告查询
    'get_report_history',
    'get_pending_requests',
    # 日志审计
    'get_operation_logs',
    'get_log_stats',
    # 企业微信只读查询
    'get_departments',
    'get_users',
    'get_user_info',
    # 状态/健康
    'health',
    'cloud_status',
    'status',
}


def find_function_end(lines, def_line_idx):
    """找到函数定义结束的位置（基于缩进）"""
    if def_line_idx >= len(lines):
        return len(lines)

    def_line = lines[def_line_idx]
    def_indent = len(def_line) - len(def_line.lstrip())

    for i in range(def_line_idx + 1, len(lines)):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if stripped.startswith('@'):
            continue
        indent = len(line) - len(line.lstrip())
        if indent <= def_indent and stripped:
            return i
    return len(lines)


def clean_file(filepath, delete_funcs):
    """从文件中删除指定的函数（包括路由装饰器）"""
    print(f"\n处理文件: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    delete_ranges = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith('@') and 'route' in stripped:
            route_line = i
            for j in range(i + 1, min(i + 3, len(lines))):
                if lines[j].strip().startswith('def '):
                    func_name = lines[j].strip()[4:].split('(')[0].strip()
                    if func_name in delete_funcs:
                        end_idx = find_function_end(lines, j)
                        delete_ranges.append((route_line, end_idx))
                        print(f"  → 删除: {func_name} (L{route_line+1}-L{end_idx})")
                        i = end_idx
                        break
            else:
                i += 1
        else:
            i += 1

    delete_ranges.sort(key=lambda x: x[0], reverse=True)
    for start, end in delete_ranges:
        del lines[start:end]

    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    print(f"  [OK] 共删除 {len(delete_ranges)} 个函数")
    return len(delete_ranges)


def remove_config_center():
    """删除config_center.py文件"""
    config_center_path = os.path.join(DEPLOY_DIR, 'config_center.py')
    if os.path.exists(config_center_path):
        backup_path = config_center_path + '.backup'
        if not os.path.exists(backup_path):
            shutil.copy2(config_center_path, backup_path)
            print(f"  [OK] 已备份: {backup_path}")
        os.remove(config_center_path)
        print(f"  [OK] 已删除: config_center.py")
        return True
    print("  - config_center.py 不存在，跳过")
    return False


def remove_config_center_bp_from_create_app():
    """从create_app()中移除config_center_bp注册"""
    filepath = os.path.join(DEPLOY_DIR, 'dispatch_center.py')
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 删除config_center_bp注册代码块
    pattern = (
        r"    try:\n"
        r"        from config_center import config_center_bp\n"
        r"        app\.register_blueprint\(config_center_bp\)\n"
        r"        logger\.info\('配置中心蓝图已注册: /api/config-center'\)\n"
        r"    except Exception as e:\n"
        r"        logger\.warning\('配置中心蓝图注册失败: %s', e\)\n"
    )
    new_content = re.sub(pattern, '', content)

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("  [OK] 已移除 config_center_bp 注册代码")
    else:
        print("  - 未找到 config_center_bp 注册代码")


def main():
    print("=" * 60)
    print("清理与云端消息通讯无关的功能")
    print("=" * 60)

    # [1/4] 删除 config_center.py
    print("\n[1/4] 删除 config_center.py...")
    remove_config_center()

    # [2/4] 移除 config_center_bp 注册
    print("\n[2/4] 移除 config_center_bp 注册...")
    remove_config_center_bp_from_create_app()

    # [3/4] 清理 dispatch_center.py
    print("\n[3/4] 清理 dispatch_center.py...")
    dc_path = os.path.join(DEPLOY_DIR, 'dispatch_center.py')
    if os.path.exists(dc_path):
        backup_path = dc_path + '.backup'
        if not os.path.exists(backup_path):
            shutil.copy2(dc_path, backup_path)
            print(f"  [OK] 已备份: {backup_path}")
        clean_file(dc_path, DISPATCH_DELETE_FUNCTIONS)
    else:
        print(f"  ✗ dispatch_center.py 不存在")

    # [4/4] 清理 wechat_server.py
    print("\n[4/4] 清理 wechat_server.py...")
    ws_path = os.path.join(DEPLOY_DIR, 'wechat_server.py')
    if os.path.exists(ws_path):
        backup_path = ws_path + '.backup'
        if not os.path.exists(backup_path):
            shutil.copy2(ws_path, backup_path)
            print(f"  [OK] 已备份: {backup_path}")
        clean_file(ws_path, WECHAT_DELETE_FUNCTIONS)
    else:
        print(f"  ✗ wechat_server.py 不存在")

    print("\n" + "=" * 60)
    print("清理完成！请在终端中手动运行：")
    print("  cd mobile_api_ai && python scripts/tools/clean_unrelated_routes.py")
    print("=" * 60)


if __name__ == '__main__':
    main()
