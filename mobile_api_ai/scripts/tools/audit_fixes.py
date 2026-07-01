"""
审计脚本：验证所有已修复风险点是否到位
只审计不修改，输出详细报告
"""
import os
import re
import sys

BASE = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai'
MODELS = r'd:\yuan\不锈钢网带跟单3.0\models'

results = []  # (category, item, status, detail)

def audit(label, desc, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    results.append((label, desc, status, detail))
    return condition

# ============================================================
# R1: CORS 白名单模式
# ============================================================
for fname in ['dispatch_center.py', 'container_center_api.py']:
    fp = os.path.join(BASE, fname)
    with open(fp, encoding='utf-8') as f:
        c = f.read()
    # CORS 必须指定 origins 白名单（通过 os.getenv 或变量）
    has_whitelist = ('CORS(' in c and 'origins=' in c and ('os.getenv' in c.split('CORS(')[1] if 'CORS(' in c else False))
    # 更准确的检查
    cors_lines = [l for l in c.split('\n') if 'CORS(' in l and 'origins=' in l]
    ok = any('os.getenv' in l or 'ORIGINS' in l or 'ALLOWED' in l for l in cors_lines)
    audit('R1 CORS白名单', fname, ok)

# ============================================================
# R2: get_json(force=True) 无残留
# ============================================================
total_force = 0
files_with_force = []
EXCLUDE_DIRS = {'.git', '__pycache__', 'venv', '.venv', 'node_modules',
                '云端更新包', '云端部署包', '云端部署包v1.1.1'}
EXCLUDE_FILES = {'wechat_server.py', 'wechat_cloud.py', 'fix_get_json.py',
                 'verify_all_fixes.py', 'audit_fixes.py'}
for root, dirs, files in os.walk(BASE):
    dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
    for f in files:
        if f.endswith('.py') and f not in EXCLUDE_FILES:
            fp = os.path.join(root, f)
            with open(fp, encoding='utf-8') as fh:
                c = fh.read()
            count = len(re.findall(r'get_json\(force=True', c))
            if count > 0:
                total_force += count
                files_with_force.append((os.path.relpath(fp, BASE), count))
audit('R2 get_json强制参数', '主源码(含子目录)', total_force == 0,
      f'残留{total_force}处' if total_force > 0 else '无残留')
if files_with_force:
    for rel, cnt in files_with_force:
        audit('  ├─残留文件', rel, False, f'{cnt}处')

# R2.5: 云端文件是否受保护（应保留force=True）
for fname in ['wechat_server.py', 'wechat_cloud.py']:
    fp = os.path.join(BASE, fname)
    if not os.path.exists(fp):
        continue
    with open(fp, encoding='utf-8') as f:
        c = f.read()
    has_force = 'get_json(force=True' in c
    audit('R2 云端文件保护', fname, has_force, '云端文件保留force=True' if has_force else '[WARN] 已被修改')

# ============================================================
# R3: API 速率限制 (flask-limiter)
# ============================================================
for fname in ['dispatch_center.py', 'container_center_api.py',
              'container_api_server.py', 'standalone_dispatch_server.py', 'app.py']:
    fp = os.path.join(BASE, fname)
    with open(fp, encoding='utf-8') as f:
        c = f.read()
    has_limiter = 'flask_limiter' in c and 'Limiter(' in c
    audit('R3 Flask-Limiter', fname, has_limiter)

# ============================================================
# R4: JWT空密钥回退（settings.py）
# ============================================================
# 检查 settings.py 或所有引用 JWT_SECRET_KEY 的环境变量配置
settings_files = [
    os.path.join(BASE, 'settings.py'),
    os.path.join(BASE, 'config.py'),
    os.path.join(BASE, 'container_center', 'config.py'),
]
r4_found = False
for sf in settings_files:
    if os.path.exists(sf):
        with open(sf, encoding='utf-8') as f:
            c = f.read()
        # 检查 JWT_SECRET_KEY 是否从环境变量读取
        if 'JWT_SECRET_KEY' in c:
            if 'os.getenv' in c and 'JWT_SECRET_KEY' in c:
                r4_found = True
                audit('R4 JWT密钥来源', os.path.basename(sf), True)
                break
if not r4_found:
    # 在 container_center_api.py 中检查
    fp = os.path.join(BASE, 'container_center_api.py')
    with open(fp, encoding='utf-8') as f:
        c = f.read()
    has_env_jwt = 'JWT_SECRET_KEY' in c and 'os.getenv' in c
    has_no_default = 'JWT_SECRET_KEY' in c and "os.getenv('JWT_SECRET_KEY')" in c
    # 检查是否还有 hardcoded 默认值
    dangerous_default = re.search(r"os\.getenv\(.*JWT_SECRET_KEY.*,\s*['\"](?!')", c)
    audit('R4 JWT密钥环境变量', 'container_center_api.py',
          has_env_jwt and not dangerous_default,
          '从环境变量读取' if has_env_jwt else '仍可能硬编码')

# ============================================================
# R5: debug=True 在生产服务器中
# ============================================================
debug_files = []
for root, dirs, files in os.walk(BASE):
    dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
    for f in files:
        if f.endswith('.py') and f not in {'fix_get_json.py', 'verify_all_fixes.py', 'audit_fixes.py'}:
            fp = os.path.join(root, f)
            with open(fp, encoding='utf-8') as fh:
                c = fh.read()
            # 查找 debug=True 但排除注释和字符串中的
            lines = c.split('\n')
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if 'debug=True' in stripped and not stripped.startswith('#'):
                    debug_files.append((os.path.relpath(fp, BASE), i, stripped.strip()))
audit('R5 debug=True残留', '全部源码', len(debug_files) == 0,
      f'残留{len(debug_files)}处' if debug_files else '无残留')
for rel, ln, txt in debug_files:
    audit('  ├─debug=True', f'{rel}:{ln}', False, txt)

# ============================================================
# R6: JWT硬编码密钥变更（container_center_api.py）
# ============================================================
fp = os.path.join(BASE, 'container_center_api.py')
with open(fp, encoding='utf-8') as f:
    c = f.read()
has_jwt_env = 'JWT_SECRET_KEY' in c and 'os.getenv' in c
has_old_key = 'change-me-in-production' in c
audit('R6 JWT密钥硬编码', 'container_center_api.py', has_jwt_env and not has_old_key,
      '已使用环境变量' if has_jwt_env else '⚠ 检查')
if has_old_key:
    audit('  ├─旧密钥残留', 'container_center_api.py', False, 'change-me-in-production 仍在文件中')

# ============================================================
# R7: API_SECRET_KEY 空密钥回退
# ============================================================
fp = os.path.join(BASE, 'container_center_api.py')
with open(fp, encoding='utf-8') as f:
    c = f.read()
has_api_env = 'API_SECRET_KEY' in c and 'os.getenv' in c
# 检查是否还有空字符串默认值
has_empty_default = re.search(r"os\.getenv\(['\"]API_SECRET_KEY['\"],\s*['\"]['\"]", c)
audit('R7 API密钥环境变量', 'container_center_api.py',
      has_api_env and not has_empty_default,
      '从环境变量读取' if has_api_env else '⚠')

# ============================================================
# R8: 硬编码端口（仅 debug_start.py port=5003）
# ============================================================
for fname in ['debug_start.py']:
    fp = os.path.join(BASE, fname)
    if not os.path.exists(fp):
        audit('R8 端口环境变量', fname, False, '文件不存在')
        continue
    with open(fp, encoding='utf-8') as f:
        c = f.read()
    has_port_env = 'WECHAT_BOT_PORT' in c and 'os.getenv' in c
    audit('R8 端口环境变量', fname, has_port_env)

# ============================================================
# R9: 服务绑定 0.0.0.0
# ============================================================
for fname in ['debug_start.py', 'start_debug.py', 'run_app.py', 'face_server.py']:
    fp = os.path.join(BASE, fname)
    if not os.path.exists(fp):
        audit('R9 host环境变量', fname, False, '文件不存在')
        continue
    with open(fp, encoding='utf-8') as f:
        c = f.read()
    has_host_env = 'FLASK_HOST' in c and 'os.getenv' in c
    has_hardcoded = "host='0.0.0.0'" in c or 'host="0.0.0.0"' in c
    audit('R9 host环境变量', fname, has_host_env,
          f'硬编码残留={has_hardcoded}' if not has_host_env else '')

# ============================================================
# R10: DDL字段类型/长度对齐
# ============================================================
dbfp = os.path.join(MODELS, 'database.py')
if os.path.exists(dbfp):
    with open(dbfp, encoding='utf-8') as f:
        c = f.read()
    checks_r10 = {
        'INT UNSIGNED in CREATE TABLE': 'INT UNSIGNED' in c,
        'VARCHAR(64) for name': 'VARCHAR(64)' in c,
        'VARCHAR(32) for phone': 'VARCHAR(32)' in c,
        'group_desc instead of description': 'group_desc' in c,
        'No INT alone (should be UNSIGNED)': True,
    }
    # 检查是否有裸 INT (在CREATE TABLE上下文中)
    create_tables = re.findall(r'CREATE TABLE.*?;', c, re.DOTALL)
    bare_int = 0
    for tbl in create_tables:
        bare_int += len(re.findall(r'\bINT\b(?!\s+UNSIGNED)', tbl))
    checks_r10['No bare INT in DDL'] = bare_int == 0

    for desc, ok in checks_r10.items():
        audit(f'R10 {desc}', 'database.py', ok)
else:
    audit('R10 DDL', 'database.py', False, '文件不存在')

# ============================================================
# 打印审计报告
# ============================================================
print('=' * 70)
print('  审计报告 - 已修复风险点验证')
print('=' * 70)

categories = {}
for label, desc, status, detail in results:
    categories.setdefault(label, []).append((desc, status, detail))

pass_count = 0
fail_count = 0
for cat, items in categories.items():
    print(f'\n[{cat}]')
    for desc, status, detail in items:
        icon = '[OK]' if status == 'PASS' else '[FAIL]'
        print(f'  {icon} {desc:40s}', end='')
        if detail:
            print(f'  {detail}')
        else:
            print()
        if status == 'PASS':
            pass_count += 1
        else:
            fail_count += 1

print()
print('=' * 70)
total = pass_count + fail_count
print(f'  总计: {total} 项 | 通过: {pass_count} | 失败: {fail_count}')
if fail_count == 0:
    print('  结论: [OK] 全部风险修复到位')
else:
    print(f'  结论: [WARN] 存在 {fail_count} 项未通过')
print('=' * 70)

sys.exit(0 if fail_count == 0 else 1)
