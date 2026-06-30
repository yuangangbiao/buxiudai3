"""编译验证 + AST 检查 — 在主进程中直接执行"""
import ast
import sys
import os
import json

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
errors = []
results = []

def check_file(rel_path):
    full_path = os.path.join(BASE, rel_path)
    with open(full_path, encoding="utf-8") as f:
        source = f.read()
    try:
        tree = ast.parse(source)
        results.append({"file": rel_path, "status": "PASS", "detail": ""})
    except SyntaxError as e:
        errors.append(f"语法错误 {rel_path}: {e}")
        results.append({"file": rel_path, "status": "FAIL", "detail": str(e)})

check_file("models/quality.py")
check_file("views/quality_view.py")
check_file("views/dialogs/__init__.py")
check_file("views/dialogs/base.py")

# 残留检测
quality_source = open(os.path.join(BASE, "views/quality_view.py"), encoding="utf-8").read()

get_conn_lines = [i+1 for i, l in enumerate(quality_source.split("\n")) if "get_connection(" in l]
has_screen_center = "winfo_screenwidth()" in quality_source or "winfo_screenheight()" in quality_source
has_center_import = "from desktop.views.dialogs import" in quality_source and "center_window" in quality_source

# JSON 格式输出供工具解析
output = {
    "errors": errors,
    "results": results,
    "residuals": {
        "get_connection_lines": get_conn_lines,
        "has_screen_center": has_screen_center,
        "has_center_import": has_center_import
    },
    "passed": len(errors) == 0 and not has_screen_center and has_center_import
}
print(json.dumps(output, ensure_ascii=False, indent=2))
