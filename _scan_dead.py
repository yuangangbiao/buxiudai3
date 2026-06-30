import os, sys

WORK = r'd:\yuan\不锈钢网带跟单3.0'

# === 1. SCRIPTS 扫描 ===
print('=' * 60)
print('1. SCRIPTS 分析')
print('=' * 60)

scripts = [
    'mobile_api_ai/scripts/archive/__verify_step1.py',
    'mobile_api_ai/scripts/archive/__verify_step2.py',
    'mobile_api_ai/scripts/archive/__verify_step3.py',
    'mobile_api_ai/scripts/archive/__verify_step4.py',
    'mobile_api_ai/scripts/build/build_cloud_exe.py',
    'mobile_api_ai/scripts/build/build_wechat_cloud_exe.py',
    'mobile_api_ai/scripts/debug/test_conn.py',
    'mobile_api_ai/scripts/debug/test_dispatch.py',
    'mobile_api_ai/scripts/debug/test_fix.py',
    'mobile_api_ai/scripts/debug/test_fix2.py',
    'mobile_api_ai/scripts/debug/test_sync.py',
    'mobile_api_ai/scripts/debug/test_write.py',
]

# 工具目录中的明显临时文件
tools_temp = []
tools_dir = os.path.join(WORK, 'mobile_api_ai', 'scripts', 'tools')
if os.path.isdir(tools_dir):
    for f in os.listdir(tools_dir):
        fp = os.path.join(tools_dir, f)
        if os.path.isfile(fp):
            # .txt 输出文件
            if f.endswith('.txt') or f.endswith('.result'):
                tools_temp.append(f'  [TXT/LOG] tools/{f}')
            # 下划线开头的 debug 脚本
            elif f.startswith('_'):
                tools_temp.append(f'  [DEBUG] tools/{f}')
            # cleanup_test / clean_* 
            elif 'cleanup' in f.lower() or 'clean_idem' in f.lower() or 'clean_unrelated' in f.lower():
                tools_temp.append(f'  [CLEANUP] tools/{f}')
            # test_* 单独测试文件
            elif f.startswith('test_') and not 'check' in f:
                tools_temp.append(f'  [TEST_SCRIPT] tools/{f}')
            # verify_* 单独验证脚本
            elif f.startswith('verify_') and not f.replace('verify_', '') in ['main_sw', 'f6_t7_dispatch']:
                tools_temp.append(f'  [VERIFY] tools/{f}')
            # publish_* 单独发布脚本
            elif 'publish' in f.lower():
                tools_temp.append(f'  [PUBLISH] tools/{f}')

# check_* 系列但内容重复的
check_dups = {}
for f in tools_temp:
    name = os.path.basename(f).replace('[CHECK] ', '')
    # 统计重复模式
    pass

print(f'\narchive/:')
for s in scripts:
    bn = os.path.basename(s)
    print(f'  archive/{bn}')

print(f'\ntools/ 疑似无用 ({len(tools_temp)} 个):')
for t in sorted(tools_temp):
    print(t)

# === 2. TESTS 扫描 ===
print('\n' + '=' * 60)
print('2. TESTS 分析')
print('=' * 60)

# 找 log 文件
logs = []
reports_dir = os.path.join(WORK, 'tests', 'reports')
if os.path.isdir(reports_dir):
    for root, dirs, files in os.walk(reports_dir):
        for f in files:
            if f.endswith('.log') or f.endswith('.result') or f.endswith('.xml'):
                fp = os.path.join(root, f)
                rel = fp.replace(WORK, '').lstrip('\\')
                logs.append(f'  [LOG] {rel}')

print(f'\ntests/reports/ 日志文件 ({len(logs)} 个):')
for l in logs[:20]:
    print(l)
if len(logs) > 20:
    print(f'  ... 还有 {len(logs)-20} 个')

# .bak 文件
baks = []
for root, dirs, files in os.walk(os.path.join(WORK, 'tests')):
    if '__pycache__' in root: continue
    for f in files:
        if f.endswith('.bak') or f.endswith('.bak_debug') or f.endswith('.bak_orig'):
            fp = os.path.join(root, f)
            rel = fp.replace(WORK, '').lstrip('\\')
            baks.append(f'  [BAK] {rel}')

if baks:
    print(f'\n.bak 备份文件 ({len(baks)} 个):')
    for b in baks:
        print(b)

# === 3. DOCS 扫描 ===
print('\n' + '=' * 60)
print('3. DOCS 分析')
print('=' * 60)

# 过时版本目录
old_versions = []
docs_dir = os.path.join(WORK, 'docs')
if os.path.isdir(docs_dir):
    for d in os.listdir(docs_dir):
        dp = os.path.join(docs_dir, d)
        if os.path.isdir(dp):
            # 当前是 v3.6.9 和 v3.7.1
            if not d.startswith('v3.6.9') and not d.startswith('v3.7.1'):
                old_versions.append(d)

print(f'\n过时机房版本目录:')
for v in sorted(old_versions):
    print(f'  docs/{v}/')

# docs/v3.6.8 里的旧文档
v368 = os.path.join(docs_dir, 'v3.6.8')
if os.path.isdir(v368):
    files = os.listdir(v368)
    print(f'\ndocs/v3.6.8/ ({len(files)} 个文件):')
    for f in files:
        print(f'  v3.6.8/{f}')

# v3.7.0 里除了当前 PLAN 外的文档
v370 = os.path.join(docs_dir, 'v3.7.0')
if os.path.isdir(v370):
    files = os.listdir(v370)
    keep = ['TODO_v3.7.1.md']  # 可能有用的
    old = [f for f in files if f not in keep]
    print(f'\ndocs/v3.7.0/ 旧文档 ({len(old)} 个):')
    for f in old:
        print(f'  v3.7.0/{f}')
