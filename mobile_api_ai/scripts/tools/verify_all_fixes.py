"""
回归验证脚本：检查所有已修复风险点是否到位
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
checks = []
errors = []

def check(label, fname, condition, detail=""):
    if condition:
        checks.append(("PASS", label, fname))
    else:
        msg = f"FAIL [{label}] {fname}" + (f" - {detail}" if detail else "")
        checks.append(("FAIL", label, fname))
        errors.append(msg)

# ===== R1: CORS 白名单模式 =====
for f in [
    "dispatch_center.py",
    "container_center_api.py",
    "standalone_dispatch_server.py",
    "container_api_server.py",
    "app.py",
    "face_server.py",
]:
    fp = os.path.join(BASE, f)
    with open(fp, encoding="utf-8") as fh:
        c = fh.read()
    # 两种合法模式：init_cors(app, ...) 集中化模式 或 CORS(app, origins=os.getenv(...)) 直接模式
    has_init_cors = "init_cors(app" in c
    has_cors_specific = ("CORS(" in c and "origins=" in c and ("os.getenv" in c or "ALLOWED" in c or "ORIGINS" in c))
    check("R1 CORS白名单", f, has_init_cors or has_cors_specific)

# ===== R2: get_json(force=True) 无残留 =====
total_force = 0
exclude_dirs = {".git", "__pycache__", "venv", ".venv", "node_modules", "云端更新包", "云端部署包", "云端部署包v1.1.1"}
exclude_files = {"wechat_server.py", "fix_get_json.py", "verify_all_fixes.py", "audit_fixes.py"}
for root, dirs, files in os.walk(BASE):
    dirs[:] = [d for d in dirs if d not in exclude_dirs]
    for f in files:
        if f.endswith(".py") and f not in exclude_files:
            fp = os.path.join(root, f)
            with open(fp, encoding="utf-8") as fh:
                c = fh.read()
            total_force += len(re.findall(r"get_json\(force=True", c))
check("R2 get_json残留", "主源码", total_force == 0, f"残留{total_force}处")

# ===== R3: Limiter =====
for f in ["dispatch_center.py", "container_center_api.py", "container_api_server.py",
          "standalone_dispatch_server.py", "app.py"]:
    fp = os.path.join(BASE, f)
    with open(fp, encoding="utf-8") as fh:
        c = fh.read()
    has_limiter = "flask_limiter" in c and "Limiter(" in c
    check("R3 Limiter", f, has_limiter)

# ===== R6/R7: 环境变量 =====
for f in ["container_center_api.py"]:
    fp = os.path.join(BASE, f)
    with open(fp, encoding="utf-8") as fh:
        c = fh.read()
    check("R6 JWT环境变量", f, "JWT_SECRET_KEY" in c and "os.getenv" in c)
    check("R7 API密钥环境变量", f, "API_SECRET_KEY" in c and "os.getenv" in c)

# ===== R8/R9: host/port 环境变量 =====
for f in ["start_debug.py"]:
    fp = os.path.join(BASE, f)
    with open(fp, encoding="utf-8") as fh:
        c = fh.read()
    check("R8 端口环境变量", f, "FLASK_PORT" in c)
    check("R9 host环境变量", f, "FLASK_HOST" in c)

# ===== R10: DDL 约束 =====
dbfp = os.path.join(os.path.dirname(BASE), "models", "database.py")
if os.path.exists(dbfp):
    with open(dbfp, encoding="utf-8") as fh:
        c = fh.read()
    check("R10 INT UNSIGNED", "database.py", "INT UNSIGNED" in c)
    check("R10 VARCHAR(64)", "database.py", "VARCHAR(64)" in c)
else:
    check("R10 database.py", "models/database.py", False, "文件不存在")

# ===== 打印报告 =====
print("=" * 65)
print("  回归验证报告 - 全部风险修复检查")
print("=" * 65)
for status, label, fname in checks:
    print(f"  {status}  {label:25s} | {fname}")
print("=" * 65)
if errors:
    print(f"  失败项: {len(errors)}")
    for e in errors:
        print(f"    - {e}")
    sys.exit(1)
else:
    print(f"  全部通过! ({len(checks)}项)")
    sys.exit(0)
