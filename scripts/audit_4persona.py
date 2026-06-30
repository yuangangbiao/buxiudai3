"""[审计] 4 人独立审计"""
import os

print('=== A. desktop_container_integration.py 怎么存 ===')
with open('desktop_container_integration.py', 'r', encoding='utf-8') as f:
    content = f.read()
print(f'_center_client 出现: {content.count("_center_client")} 次')
print(f'_container_center 出现: {content.count("_container_center")} 次')
print(f'sqlite 出现: {content.count("sqlite")} 次')
print(f'/api/internal/ 出现: {content.count("/api/internal/")} 次')
print(f'pymysql.connect 出现: {content.count("pymysql.connect")} 次')

print()
print('=== B. 5 个 service 文件调用方式 ===')
for svc in ['manual_publish_service.py', 'auto_publish_service.py',
            'container_event_listener.py', 'material_publish_service.py']:
    if os.path.exists(svc):
        with open(svc, 'r', encoding='utf-8') as f:
            c = f.read()
        ip_count = c.count('_integration.publish_')
        pub_count = c.count('publisher')
        dci_count = c.count('desktop_container_integration')
        print(f'{svc}:')
        print(f'  调 _integration.publish_*: {ip_count} 处')
        print(f'  import publisher: {pub_count} 处')
        print(f'  调 desktop_container_integration: {dci_count} 处')

print()
print('=== C. container_api_server.py (5003 端口接收端) ===')
if os.path.exists('mobile_api_ai/container_api_server.py'):
    with open('mobile_api_ai/container_api_server.py', 'r', encoding='utf-8') as f:
        cas = f.read()
    print(f'pymysql.connect: {cas.count("pymysql.connect")}')
    print(f'save_package: {cas.count("save_package")}')
    print(f'save_process_record: {cas.count("save_process_record")}')
    print(f'@app.route: {cas.count("@app.route")}')

print()
print('=== D. container_center_v5 是什么 ===')
for path in ['container_center_v5.py', 'mobile_api_ai/container_center_v5.py',
            'mobile_api_ai/container_center/__init__.py']:
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            c = f.read()
        print(f'{path}:')
        print(f'  pymysql.connect: {c.count("pymysql.connect")}')
        print(f'  sqlite: {c.count("sqlite")}')
        print(f'  save_package: {c.count("save_package")}')

print()
print('=== E. 实际看 desktop_container_integration.py 关键代码 ===')
# 找 publish_report_task 调用分支
with open('desktop_container_integration.py', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('def publish_report_task')
if idx > 0:
    # 看 1500 字符
    snippet = content[idx:idx+1500]
    # 找分支
    if '_center_client is not None' in snippet:
        print('✅ 有 _center_client 分支（HTTP 调 5003）')
    if '_container_center.collect_report' in snippet:
        print('✅ 有 _container_center 分支（本地 SQLite）')
    if 'pymysql.connect' in snippet:
        print('✅ 有直连 MySQL')
    else:
        print('❌ 没有直连 MySQL')

print()
print('=== F. publisher.py 当前真实行为 ===')
with open('mobile_api_ai/dispatch_center/publisher.py', 'r', encoding='utf-8') as f:
    pub = f.read()
print(f'pymysql.connect: {pub.count("pymysql.connect")}')
print(f'_task_store: {pub.count("_task_store")}')
print(f'_store_task: {pub.count("_store_task")}')
print(f'_center_client: {pub.count("_center_client")}')
print(f'curl /api: {pub.count("/api/internal/")}')