import os, shutil

WORK = r'd:\yuan\不锈钢网带跟单3.0'
deleted = []

def rm(path):
    path = os.path.join(WORK, path)
    if os.path.exists(path):
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        deleted.append(path)
        return True
    return False

# === 1. SCRIPTS ===
print('=== 删除 scripts ===')

# archive/
for f in ['__verify_step1.py','__verify_step2.py','__verify_step3.py','__verify_step4.py']:
    rm(f'mobile_api_ai/scripts/archive/{f}')
rm('mobile_api_ai/scripts/archive')
print(f'  archive/ 删除了')

# build/
rm('mobile_api_ai/scripts/build/build_cloud_exe.py')
rm('mobile_api_ai/scripts/build/build_wechat_cloud_exe.py')
rm('mobile_api_ai/scripts/build')
print(f'  build/ 删除了')

# debug/
for f in ['test_conn.py','test_dispatch.py','test_fix.py','test_fix2.py','test_sync.py','test_write.py']:
    rm(f'mobile_api_ai/scripts/debug/{f}')
rm('mobile_api_ai/scripts/debug')
print(f'  debug/ 删除了')

# tools/ 临时文件
tools_dir = os.path.join(WORK, 'mobile_api_ai', 'scripts', 'tools')
if os.path.isdir(tools_dir):
    removed_tools = 0
    for f in os.listdir(tools_dir):
        fp = os.path.join(tools_dir, f)
        if f.endswith('.txt') or f.endswith('.result'):
            os.remove(fp); deleted.append(fp); removed_tools += 1
        elif f.startswith('_'):
            os.remove(fp); deleted.append(fp); removed_tools += 1
        elif 'cleanup' in f.lower() or 'clean_idem' in f.lower():
            os.remove(fp); deleted.append(fp); removed_tools += 1
        elif (f.startswith('test_') or f.startswith('verify_') or f.startswith('publish_') or f.startswith('diag_')) and not any(x in f for x in ['check_mysql', 'check_desktop', 'check_all_dbs', 'check_dependencies', 'check_config', 'check_dispatch', 'check_order', 'check_port', 'check_schedule', 'check_warehousing', 'check_wechat', 'check_chengsheng', 'check_schema', 'check_data2', 'check_db', 'check_008', 'check_op', 'check_process', 'check_result', 'check_write', 'check_root', 'check_network', 'check_hardcode', 'check_brackets', 'check_page', 'check_js', 'check_human', 'check_deep', 'check_deploy', 'check_wh', 'check_wno', 'check_wo', 'check_cs', 'add_index', 'diagnose']):
            os.remove(fp); deleted.append(fp); removed_tools += 1
    print(f'  tools/ 删除了 {removed_tools} 个临时文件')

# === 2. TESTS ===
print('\n=== 删除 tests ===')

# .bak files
baks = []
for root, dirs, files in os.walk(os.path.join(WORK, 'tests')):
    for f in files:
        if f.endswith('.bak') or '.bak_' in f:
            fp = os.path.join(root, f)
            os.remove(fp); deleted.append(fp); baks.append(f)
print(f'  .bak 文件: {len(baks)} 个')

# tests/reports/logs/
logs_dir = os.path.join(WORK, 'tests', 'reports', 'logs')
if os.path.isdir(logs_dir):
    log_count = len([f for f in os.listdir(logs_dir) if f.endswith('.log')])
    for f in os.listdir(logs_dir):
        os.remove(os.path.join(logs_dir, f))
    print(f'  tests/reports/logs/*.log: {log_count} 个')

# old pytest xml
old_xml = os.path.join(WORK, 'tests', 'reports', 'pytest-local-baseline.xml')
if os.path.exists(old_xml):
    os.remove(old_xml); deleted.append(old_xml)
    print(f'  pytest-local-baseline.xml 删除')

# === 3. DOCS ===
print('\n=== 删除 docs ===')

# v3.6.8
v368 = os.path.join(WORK, 'docs', 'v3.6.8')
if os.path.isdir(v368):
    shutil.rmtree(v368); deleted.append(v368)
    print(f'  docs/v3.6.8/ 全删 (20 个文件)')

# v3.7.0 (除了 TODO_v3.7.1.md)
v370 = os.path.join(WORK, 'docs', 'v3.7.0')
if os.path.isdir(v370):
    v370_keep = ['TODO_v3.7.1.md']
    for f in os.listdir(v370):
        if f not in v370_keep:
            os.remove(os.path.join(v370, f)); deleted.append(f)
    print(f'  docs/v3.7.0/ 旧文档删除 (保留 TODO_v3.7.1.md)')

# 过时机房目录
old_dirs = [
    'docs/5008鉴权修复', 'docs/EventBus集成', 'docs/K22_业务表脏数据诊断',
    'docs/P0_TECH_DEBT_CLEANUP', 'docs/P0修复_2026_06_18', 'docs/P1P2修复_2026_06_18',
    'docs/P1_cost_reports_404', 'docs/R14_项目基础设施优化', 'docs/R2_Bug狩猎_2026_06_18',
    'docs/RE-001_history事务包裹', 'docs/RE-002_消息触发链路修复',
    'docs/RE-004_9事件消息全链路覆盖', 'docs/RE-005_工序流程分类严格化',
    'docs/RE-006_写入端data_type严格化', 'docs/acceptance', 'docs/debug',
    'docs/demo_videos', 'docs/dispatch_center', 'docs/learning',
    'docs/p0_auth_fix', 'docs/playwright', 'docs/quality_view修复',
    'docs/superpowers', 'docs/ux_screenshots',
]
removed_dirs = 0
for d in old_dirs:
    dp = os.path.join(WORK, d)
    if os.path.isdir(dp):
        shutil.rmtree(dp); deleted.append(dp); removed_dirs += 1
print(f'  过时机房目录: {removed_dirs} 个')

print(f'\n=== 共删除 {len(deleted)} 个文件/目录 ===')
for d in deleted[:10]:
    print(f'  {d}')
if len(deleted) > 10:
    print(f'  ... 还有 {len(deleted)-10} 个')
