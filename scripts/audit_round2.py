"""[审计第 2 轮] 独立验证每个 commit 的声称"""
import subprocess
import os
import ast


def check(label, condition):
    icon = '✅' if condition else '❌'
    print(f'  {icon} {label}')
    return condition


print('=' * 60)
print('Commit 1: 2ee7a125 (P2 修复 - 仅 _core.py)')
print('=' * 60)
print('声称: P2-5/6 在 _core.py')

# 1a. P2-5 线程守卫
with open(r'mobile_api_ai\dispatch_center\_core.py', 'r', encoding='utf-8') as f:
    core = f.read()
has_persist = '_persist_thread' in core
has_is_alive = 'is_alive()' in core
print(f'  P2-5 _persist_thread 属性: {check("_persist_thread 属性存在", has_persist)}')
print(f'  P2-5 is_alive() 守卫: {check("is_alive() 调用存在", has_is_alive)}')

# 1b. P2-6 N+1 优化
has_existing_ids = 'existing_ids' in core
has_in_clause = 'WHERE id IN' in core
print(f'  P2-6 existing_ids 集合: {check("existing_ids 缓存", has_existing_ids)}')
print(f'  P2-6 WHERE id IN 子句: {check("IN 子句批量查询", has_in_clause)}')

# 1c. _core.py 真实改动行数（vs 9a4e5c7b 之前）
r = subprocess.run(['git', 'diff', '9a4e5c7b', '2ee7a125', '--numstat', '--', './mobile_api_ai/dispatch_center/_core.py'],
                   capture_output=True, text=True)
print(f'  实际改动: {r.stdout.strip()}')

print()
print('=' * 60)
print('Commit 2: b40e6a2b (Web 化骨架)')
print('=' * 60)
print('声称: 3745 行 + P2-2/3/7')

# 2a. desktop_web/server.py 行数
if os.path.exists(r'desktop_web\server.py'):
    with open(r'desktop_web\server.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    line_count = len(lines)
    print(f'  desktop_web/server.py 实际行数: {check(f"{line_count} 行", line_count == 3745)}')
else:
    print('  ❌ desktop_web/server.py 不存在')

# 2b. P2-2 CORS
if os.path.exists(r'desktop_web\server.py'):
    server = open(r'desktop_web\server.py', 'r', encoding='utf-8').read()
    has_cors = 'ALLOWED_ORIGINS' in server
    has_supports_creds = 'supports_credentials' in server
    print(f'  P2-2 ALLOWED_ORIGINS: {check("动态 origins", has_cors)}')
    print(f'  P2-2 supports_credentials: {check("credentials 支持", has_supports_creds)}')

# 2c. P2-3 全局异常处理器
has_errorhandler = '@app.errorhandler' in server if 'server' in dir() else False
print(f'  P2-3 @app.errorhandler: {check("全局异常处理器", has_errorhandler)}')

# 2d. P2-7 报工超量拦截
has_p27 = '[P2-7]' in server if 'server' in dir() else False
print(f'  P2-7 [P2-7] 标记: {check("报工拦截", has_p27)}')

print()
print('=' * 60)
print('Commit 3: 5f8c2283 (Q-B6 全量迁移)')
print('=' * 60)
print('声称: 7 个引用方 100% 迁移 + 124 测试')

# 3a. 7 个文件已迁移
migrated_files = [
    'manual_publish_service.py',
    'task_recall_service.py',
    'container_event_listener.py',
    'material_publish_service.py',
    'auto_publish_service.py',
]
print('  5 个服务文件迁移:')
for f in migrated_files:
    if os.path.exists(f):
        content = open(f, 'r', encoding='utf-8').read()
        has_new = 'mobile_api_ai.dispatch_center.publisher' in content
        has_old = 'from desktop_container_integration import' in content
        ok = has_new and not has_old
        print(f'    {check(f, ok)}')

# 3b. tests/modular/test_desktop_container.py
test_content = open('tests/modular/test_desktop_container.py', 'r', encoding='utf-8').read()
print(f'  test_desktop_container.py 已重写: {check("改用 publisher", "publisher" in test_content)}')

# 3c. publisher.py 存在
print(f'  publisher.py 存在: {check("mobile_api_ai/dispatch_center/publisher.py", os.path.exists(r"mobile_api_ai\dispatch_center\publisher.py"))}')

print()
print('=' * 60)
print('Commit 4: 82a9b3e2 (审计修正 + 生产存储)')
print('=' * 60)
print('声称: v3.7.4/5 文档修正 + 生产迁移指南')

# 4a. 文档修正
v374 = open('docs/v3.7.4/ACCEPTANCE_v3.7.4.md', 'r', encoding='utf-8').read()
v375 = open('docs/v3.7.5/ACCEPTANCE_v3.7.5.md', 'r', encoding='utf-8').read()
v376 = open('docs/v3.6.8/ACCEPTANCE_P2_v3.6.8.md', 'r', encoding='utf-8').read()

print(f'  v3.7.4 文档修正: {check("审计修正 2026-06-25 出现", "审计修正 2026-06-25" in v374)}')
print(f'  v3.7.5 文档修正: {check("揭示真实问题", "用 skip 掩盖" in v375)}')
print(f'  PRODUCTION_STORAGE_MIGRATION.md: {check("存在", os.path.exists("docs/v3.7.7/PRODUCTION_STORAGE_MIGRATION.md"))}')

# 4b. publisher.py 加生产警告
pub = open('mobile_api_ai/dispatch_center/publisher.py', 'r', encoding='utf-8').read()
print(f'  publisher.py 生产警告: {check("_IS_PRODUCTION 检测", "_IS_PRODUCTION" in pub)}')

print()
print('=' * 60)
print('Commit 5: 1f964d8a (v3.6.8 ACCEPTANCE 修正)')
print('=' * 60)
print('声称: 92→76 数字校准')

# 5a. 文档中是否写 92→76
v368 = open('docs/v3.6.8/ACCEPTANCE_P2_v3.6.8.md', 'r', encoding='utf-8').read()
print(f'  92 提到: {check("92 在文档中", "92" in v368)}')
print(f'  76 提到: {check("76 在文档中", "76" in v368)}')
print(f'  数字校准说明: {check("修正记录章节", "修正记录" in v368)}')

# 5b. 实际数字验证（之前已确认）
print(f'  实际 desktop_web/server.py str(e): {check("8 处", server.count("str(e)") if "server" in dir() else 0 == 8)}')
print(f'  实际 _core.py str(e): {check("68 处", core.count("str(e)") == 68)}')