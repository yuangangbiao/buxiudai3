"""最严审计：process_id → process_code 切换"""
# 审计所有 process_records / data_packages / 报工 相关代码路径

target_files = {
    'schedule_routes.py': '排产发布 → data_packages',
    'container_center_v5.py': '容器中心同步 → MySQL',
    'app.py': '报工API → MySQL',
    'sync_bridge.py': '8008同步桥 → MySQL',
    'production.py': '排产 → process_records',
    'api/scan.py': '扫码API',
    'dispatch_center.py': '调度中心核心',
    'storage_layer.py': 'SQLite存储层',
    'container_center_client.py': '容器中心客户端',
}
