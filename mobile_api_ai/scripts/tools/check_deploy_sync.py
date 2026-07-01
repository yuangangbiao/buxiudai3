"""
检查本次修复的文件是否同步到云端部署包v1.1.1

直接对比：获取本次修复的核心源码文件列表，逐一检查部署包中对应文件是否内容一致
"""
import os
import hashlib

BASE = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai'
DEPLOY = os.path.join(BASE, '云端部署包v1.1.1')

def md5(fp):
    h = hashlib.md5()
    with open(fp, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

# 本次修复的核心源码文件 (相对 mobile_api_ai 的路径)
# Group A + Group B 中所有被修改的文件
CORE_FILES = [
    'dispatch_center.py',
    'container_center_api.py',
    'container_api_server.py',
    'standalone_dispatch_server.py',
    'app.py',
    'debug_start.py',
    'start_debug.py',
    'run_app.py',
    'face_server.py',
    'cloud_poller.py',
    'api/ai.py',
    'api/approval.py',
    'api/auth.py',
    'api/cost.py',
    'api/decorators.py',
    'api/legacy_routes.py',
    'api/quality.py',
    'api/reports.py',
    'container_center/api/alerts.py',
    'container_center/api/configs.py',
    'container_center/api/documents.py',
    'container_center/api/messages.py',
    'face_checkin/__init__.py',
    'schedule_flow.py',
    'sync_bridge.py',
    'wecom_auth.py',
]

# 额外检查：代码审查后的新脚本
NEW_SCRIPTS = [
    'scripts/tools/fix_get_json.py',
]

print('=' * 75)
print('  云端部署包同步检查 (云端部署包v1.1.1)')
print('=' * 75)

# 构建部署包文件索引
deploy_index = {}  # basename -> (filepath, md5)
for root, dirs, files in os.walk(DEPLOY):
    for f in files:
        if f.endswith('.py'):
            fp = os.path.join(root, f)
            deploy_index[f] = (fp, md5(fp))

# DAT 子目录索引
dat_index = {}
dat_dir = os.path.join(DEPLOY, 'DAT')
if os.path.exists(dat_dir):
    for root, dirs, files in os.walk(dat_dir):
        for f in files:
            if f.endswith('.py'):
                fp = os.path.join(root, f)
                dat_index[f] = (fp, md5(fp))

synced = 0
unsynced = []
not_found = []
new_only = []
deploy_extra = []

print(f'\n{"源码文件":45s} {"状态":12s} {"说明":25s}')
print('-' * 75)

for rel_path in CORE_FILES:
    src_file = os.path.join(BASE, rel_path)
    if not os.path.exists(src_file):
        not_found.append(rel_path)
        print(f'  [??] {rel_path:42s} {"源不存在":12s}')
        continue

    basename = os.path.basename(rel_path)
    src_md5 = md5(src_file)

    # 检查部署包根目录
    if basename in deploy_index:
        deploy_fp, deploy_md5 = deploy_index[basename]
        if src_md5 == deploy_md5:
            synced += 1
            print(f'  [OK] {rel_path:42s} {"已同步":12s}')
        else:
            unsynced.append((rel_path, '根目录'))
            print(f'  [!!] {rel_path:42s} {"内容不一致":12s} {"根目录MD5不同":20s}')
    # 检查 DAT 目录
    elif basename in dat_index:
        dat_fp, dat_md5 = dat_index[basename]
        if src_md5 == dat_md5:
            synced += 1
            print(f'  [OK] {rel_path:42s} {"已同步(DAT)":14s}')
        else:
            unsynced.append((rel_path, 'DAT'))
            print(f'  [!!] {rel_path:42s} {"内容不一致":12s} {"DAT目录MD5不同":20s}')
    else:
        not_found.append(rel_path)
        print(f'  [--] {rel_path:42s} {"未在部署包中":14s}')

# 检查新脚本
print()
print('  新创建脚本（不在部署包中属正常）:')
for rel_path in NEW_SCRIPTS:
    src_file = os.path.join(BASE, rel_path)
    if os.path.exists(src_file):
        print(f'  [..] {rel_path:42s} {"仅本地存在":14s}')

# 统计部署包中有但不在核心列表中的文件（冗余检查）
print()
print('=' * 75)
print(f'\n  统计:')
print(f'    已同步:     {synced}')
print(f'    内容不一致: {len(unsynced)}')
print(f'    未在部署包: {len(not_found)}')
print()

if unsynced:
    print('  [WARN] 以下文件内容不一致，需要重新同步:')
    for f, loc in unsynced:
        print(f'    - {f} ({loc})')

if not_found:
    print('  [INFO] 以下文件不在部署包中（可能是本地开发文件，无需同步）:')
    for f in not_found:
        print(f'    - {f}')

if not unsynced and not_found == []:
    print('  [OK] 所有需同步的核心文件均已正确部署!')
elif not unsynced:
    print('  [OK] 所有存在于部署包中的文件均已同步，未同步的文件均为本地开发文件。')

print('=' * 75)
