"""S3 安全闸门：验证 center_window 导入正确"""
import sys
import os
import py_compile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE)
sys.path.insert(0, BASE)

errors = []

# 1. 语法检查
for f in ["views/dialogs/__init__.py", "views/dialogs/base.py", "views/quality_view.py"]:
    try:
        py_compile.compile(os.path.join(BASE, f), doraise=True)
        print(f"  ✅ 语法通过: {f}")
    except py_compile.PyCompileError as e:
        errors.append(f"语法错误 {f}: {e}")
        print(f"  ❌ 语法错误: {f}")

# 2. 导入验证
try:
    from desktop.views.dialogs import center_window
    print(f"  ✅ center_window 导入成功: {center_window}")
except ImportError as e:
    errors.append(f"导入失败: {e}")
    print(f"  ❌ center_window 导入失败: {e}")

# 3. quality_view.py 残留检测
with open(os.path.join(BASE, "views/quality_view.py"), encoding="utf-8") as f:
    content = f.read()
    if "winfo_screenwidth()" in content or "winfo_screenheight()" in content:
        errors.append("quality_view.py 仍有 winfo_screenwidth/height 残留")
        print("  ❌ quality_view.py 存在居中代码残留，请检查")
    else:
        print("  ✅ quality_view.py 无 winfo_screenwidth/height 残留")

# 汇总
print()
if errors:
    print(f"S3 安全闸门: ❌ 失败 - {len(errors)} 个问题")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("S3 安全闸门: ✅ 全部通过")
