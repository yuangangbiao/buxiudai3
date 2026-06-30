"""S1 同步: 6 个代码文件主仓 → 部署副本
代码文件: .py / .html / .txt (共 6 个)
部署独有: .env / start.bat / config.py / update_cloud.sh / .exe / mobile_scanner.html / task_redirect.html (保留)
"""
import os
import shutil

BASE = r'd:\yuan\不锈钢网带跟单3.0'
MAIN = os.path.join(BASE, 'mobile_api_ai')
DEPLOY = os.path.join(BASE, 'mobile_api_ai', 'deploy_output')

# 6 个代码文件
S1_CODE_FILES = [
    'wechat_app_bot.py',
    'cloud_backup.py',
    'logging_setup.py',
    'wechat_cloud.py',
    'requirements.txt',
    'templates/config_center.html',
    'templates/container_dashboard.html',
]

# 部署独有 - 列出但不动
DEPLOY_ONLY = [
    '.env (部署环境变量, 4620 B)',
    'config.py (部署运行时配置, 3657 B)',
    'start.bat / update_cloud.sh (部署启动/更新脚本)',
    'wechat_cloud_server.exe (编译产物, 18 MB)',
    'templates/mobile_scanner.html / task_redirect.html (部署端模板)',
]

print(f'[S1] 待同步 {len(S1_CODE_FILES)} 个代码文件\n')

synced = []
for f in S1_CODE_FILES:
    src = os.path.join(MAIN, f)
    dst = os.path.join(DEPLOY, f)

    if not os.path.exists(src):
        print(f'  [SKIP] {f} 主仓不存在')
        continue

    main_size = os.path.getsize(src)
    if os.path.exists(dst):
        deploy_size = os.path.getsize(dst)
        if main_size == deploy_size:
            print(f'  [SKIP] {f} 大小一致 ({main_size} B)')
            continue
        # 备份部署副本
        bak = dst + '.bak_pre_s1_sync'
        shutil.copy2(dst, bak)
        print(f'  [BACKUP] {f} {deploy_size} B → {bak}')

    # cp 主仓 → 部署
    shutil.copy2(src, dst)
    new_size = os.path.getsize(dst)
    synced.append(f)
    print(f'  [SYNC] {f}: {main_size} B → 部署 {new_size} B ✓')

print(f'\n[S1] 同步完成: {len(synced)}/{len(S1_CODE_FILES)} 个文件')
print()
print('=== 部署独有 (保留不动) ===')
for f in DEPLOY_ONLY:
    print(f'  - {f}')

print()
print('=== 端到端冒烟 (defer — 启动 wechat_cloud_server.exe 风险大, 改用语法检查) ===')
import py_compile
for f in S1_CODE_FILES:
    if f.endswith('.py'):
        src = os.path.join(DEPLOY, f)
        try:
            py_compile.compile(src, doraise=True)
            print(f'  [OK] {f} 语法正确')
        except py_compile.PyCompileError as e:
            print(f'  [FAIL] {f}: {e}')
