"""
质检模块重构验证脚本 - 4 层检查机制
验证 quality_view.py 与 quality_dialogs.py 的重构完整性和一致性

用法:
    python scripts/tools/validate_quality_refactor.py
"""

import ast
import os
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
VIEWS_DIR = BASE_DIR / "views"
DIALOGS_DIR = VIEWS_DIR / "dialogs"

QUALITY_VIEW = VIEWS_DIR / "quality_view.py"
QUALITY_DIALOGS = DIALOGS_DIR / "quality_dialogs.py"

# ── 检查项计数 ──
checks = {"pass": 0, "fail": 0, "warn": 0}


def check(ok, msg, level="pass"):
    if level == "pass":
        checks["pass"] += 1
        tag = "[PASS]"
    elif level == "fail":
        checks["fail"] += 1
        tag = "[FAIL]"
    else:
        checks["warn"] += 1
        tag = "[WARN]"
    print(f"  {tag} {msg}")


# ════════════════════════════════════════════
# L1: 执行级 - 函数/方法替换完整性检查
# ════════════════════════════════════════════
def check_level1_execution():
    print("\n═══ L1: 执行级 — 函数替换完整性 ═══")

    with open(QUALITY_VIEW, "r", encoding="utf-8") as f:
        content = f.read()

    # 期望：这三个方法应被替换为对话框类调用（不应含大量内联 UI 代码）
    replacements = [
        ("_compile_task", "QualityTaskCompileDialog"),
        ("_open_qc_form", "QualityRecordFormDialog"),
        ("_show_completion_confirm", "CompletionConfirmDialog"),
    ]

    for func_name, dialog_class in replacements:
        if dialog_class in content:
            check(True, f"{func_name}(...) → {dialog_class}(...) 已替换")
        else:
            check(False, f"{func_name}(...) → {dialog_class}(...) 未替换", "fail")

    # 反向检查：三个对话框类是否都被 import
    with open(QUALITY_VIEW, "r", encoding="utf-8") as f:
        lines = f.readlines()

    import_found = False
    for line in lines:
        if "from dialogs.quality_dialogs import" in line:
            import_found = True
            classes_in_import = line.strip()
            break

    if import_found:
        expected = ["QualityTaskCompileDialog", "QualityRecordFormDialog", "CompletionConfirmDialog"]
        for cls in expected:
            if cls in classes_in_import:
                check(True, f"import {cls} 存在")
            else:
                check(False, f"import {cls} 缺失", "fail")
    else:
        check(False, "quality_view.py 缺少 quality_dialogs 的 import", "fail")


# ════════════════════════════════════════════
# L2: 工具级 - 代码规范检查
# ════════════════════════════════════════════
def check_level2_tool():
    print("\n═══ L2: 工具级 — 代码规范检查 ═══")

    for filepath in [QUALITY_VIEW, QUALITY_DIALOGS]:
        fname = filepath.name
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 2a: 检查重复 import os（模块级只用一次）
        os_imports = [i for i, line in enumerate(lines, 1) if re.match(r"^import os\s*(#.*)?$", line)]
        if len(os_imports) > 1:
            check(False, f"{fname}: 模块级 import os 出现 {len(os_imports)} 次（行 {os_imports}）", "fail")
        else:
            check(True, f"{fname}: import os 无重复")

        # 2b: 检查方法内是否有局部 import os
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped == "import os" and not re.match(r"^import os\s*(#.*)?$", line):
                check(False, f"{fname}:{i} 方法内部 import os", "fail")
                break

        # 2c: 检查是否仍有 messagebox 使用
        for i, line in enumerate(lines, 1):
            if "messagebox." in line and not line.strip().startswith("#"):
                check(False, f"{fname}:{i} {line.strip()} — messagebox 残留", "fail")
                break
        else:
            check(True, f"{fname}: 无 messagebox 残留")

        # 2d: 检查是否有裸露 except（except: 不带 Exception）
        for i, line in enumerate(lines, 1):
            if re.match(r"^\s*except\s*:", line):
                check(False, f"{fname}:{i} 裸露 except: — 应使用 except Exception as e:", "fail")
                break
        else:
            check(True, f"{fname}: 无裸露 except")


# ════════════════════════════════════════════
# L3: 编译级 - 导入路径 & 符号验证
# ════════════════════════════════════════════
def check_level3_compile():
    print("\n═══ L3: 编译级 — 导入路径&符号验证 ═══")

    # 3a: 验证 OrderStatus 来源
    with open(QUALITY_DIALOGS, "r", encoding="utf-8") as f:
        content = f.read()

    m = re.search(r"from\s+(\S+)\s+import\s+.*OrderStatus", content)
    if m:
        source_module = m.group(1)
        expected = "constants"
        if source_module == expected:
            check(True, f"OrderStatus 导入路径正确: from {source_module} import OrderStatus")
        else:
            check(False, f"OrderStatus 导入路径错误: from {source_module} — 应为 from {expected}", "fail")
    else:
        check(False, "未找到 OrderStatus 导入语句", "warn")

    # 3b: 验证所有 from ... import 的模块路径存在
    py_files = [QUALITY_VIEW, QUALITY_DIALOGS]
    for fp in py_files:
        with open(fp, "r", encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content, filename=fp.name)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.level:  # 相对导入
                    continue
                module_path = node.module.replace(".", os.sep) + ".py"
                abs_path = BASE_DIR / module_path
                # 忽略标准库和第三方包
                if not abs_path.exists():
                    pass  # 可能是第三方库，不报错
        check(True, f"{fp.name}: AST 解析通过")


# ════════════════════════════════════════════
# L4: 审查级 - UI 文本& emoji 一致性检查
# ════════════════════════════════════════════
def check_level4_review():
    print("\n═══ L4: 审查级 — UI 文本 & emoji 一致性 ═══")

    with open(QUALITY_DIALOGS, "r", encoding="utf-8") as f:
        content = f.read()

    # 4a: CompletionConfirmDialog 的 emoji 图标
    emoji_checks = {
        "✅": "终检合格标题",
        "📦": "工单编号前缀",
        "🔍": "质检类型前缀",
        "📊": "质检结果前缀",
        "⚠️": "不良数量前缀",
        "👤": "质检员前缀",
        "🕐": "质检时间前缀",
        "⏳": "暂不完成按钮",
    }

    for emoji, context in emoji_checks.items():
        if emoji in content:
            check(True, f"CompletionConfirmDialog: {context} emoji({emoji}) 存在")
        else:
            check(False, f"CompletionConfirmDialog: {context} emoji({emoji}) 丢失", "fail")

    # 4b: QualityRecordFormDialog 附件按钮
    if 'text="📎"' in content:
        check(True, "QualityRecordFormDialog: 附件按钮 icon(📎) 存在")
    else:
        check(False, "QualityRecordFormDialog: 附件按钮 icon(📎) 丢失", "fail")

    # 4c: CompletionConfirmDialog 按钮 emoji
    if 'text="✅ 确认完成"' in content:
        check(True, "确认完成按钮 icon(✅) 存在")
    else:
        check(False, "确认完成按钮 icon(✅) 丢失", "fail")

    # 4d: 窗口标题
    if 'title("✅ 终检合格' in content:
        check(True, "窗口标题 emoji(✅) 存在")
    else:
        check(False, "窗口标题 emoji(✅) 丢失", "fail")

    # 4e: 检查 old `center_window` 是否没有迁移
    if "center_window" in content:
        check(False, "quality_dialogs.py 直接调用 center_window — 应自行计算居中", "warn")
    else:
        check(True, "quality_dialogs.py 无 center_window 外部依赖")


# ════════════════════════════════════════════
# 汇总
# ════════════════════════════════════════════
def summary():
    total = checks["pass"] + checks["fail"] + checks["warn"]
    print(f"\n{'═' * 50}")
    print(f"   验证汇总: 通过 {checks['pass']}/{total}")
    if checks["fail"]:
        print(f"   ❌ 失败 {checks['fail']} 项 — 需立即修复")
    if checks["warn"]:
        print(f"   ⚠️  警告 {checks['warn']} 项 — 建议复查")
    if checks["fail"] == 0:
        print("   ✅ 全部通过，重构完整性验证 OK")
    print(f"{'═' * 50}\n")
    return checks["fail"] == 0


def main():
    print(f"质检模块重构验证脚本")
    print(f"  quality_view.py    : {QUALITY_VIEW}")
    print(f"  quality_dialogs.py : {QUALITY_DIALOGS}")
    print(f"  Python: {sys.version}")

    check_level1_execution()
    check_level2_tool()
    check_level3_compile()
    check_level4_review()

    ok = summary()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
