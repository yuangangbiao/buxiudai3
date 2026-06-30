# -*- coding: utf-8 -*-
"""
综合清理脚本 - 执行 A/B/C 三个清理方案

A: 8 个死测试文件 (7 移到 scripts/tools/，1 删除)
B: 清理 coverage_html/ 旧覆盖率目录
C: 清理 tests/logs/ 测试累积日志
"""
import os
import shutil
import sys

PROJECT_ROOT = r"d:\yuan\不锈钢网带跟单3.0"
SCRIPTS_TOOLS = os.path.join(PROJECT_ROOT, "scripts", "tools")

# A: 8 个死测试文件
# 7 个 utility 工具脚本 (移动到 scripts/tools/)
UTILITY_SCRIPTS = [
    "tests\\append_quality_rule_tests.py",
    "tests\\conftest_category_hook.py",
    "tests\\run_tests_by_case_type.py",
    "tests\\run_tests_by_module.py",
    "tests\\write_all_test_classes.py",
    "mobile_api_ai\\tests\\run_all_tests.py",
    "mobile_api_ai\\tests\\fixtures\\_test_cc.py",
]
# 1 个临时调试脚本 (直接删除)
TEMP_DEBUG_SCRIPTS = [
    "tests\\test_re002_message_trigger.py",
]

# B: coverage_html/ 整个目录
COVERAGE_HTML_DIR = os.path.join(PROJECT_ROOT, "coverage_html")
COVERAGE_FILES = [
    ".coverage",
    "coverage.xml",
]

# C: tests/logs/ 全部日志
TESTS_LOGS_DIR = os.path.join(PROJECT_ROOT, "tests", "logs")


def human_size(n_bytes):
    """格式化字节数"""
    for unit in ("B", "KB", "MB", "GB"):
        if n_bytes < 1024.0:
            return f"{n_bytes:.2f} {unit}"
        n_bytes /= 1024.0
    return f"{n_bytes:.2f} TB"


def dir_size(path):
    """递归计算目录大小"""
    total = 0
    count = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            try:
                total += os.path.getsize(fp)
                count += 1
            except OSError:
                pass
    return total, count


def get_size(path):
    """获取文件/目录大小"""
    if os.path.isfile(path):
        return os.path.getsize(path), 1
    elif os.path.isdir(path):
        return dir_size(path)
    return 0, 0


def move_utility_scripts():
    """A1: 移动 7 个 utility 脚本到 scripts/tools/"""
    print("\n" + "=" * 70)
    print("【A1】移动 7 个 utility 工具脚本 → scripts/tools/")
    print("=" * 70)
    os.makedirs(SCRIPTS_TOOLS, exist_ok=True)
    moved = []
    skipped = []
    for rel in UTILITY_SCRIPTS:
        src = os.path.join(PROJECT_ROOT, rel)
        if not os.path.exists(src):
            print(f"  ⊘ 跳过 (不存在): {rel}")
            skipped.append(rel)
            continue
        # 目标文件名加 _ 避免冲突
        basename = os.path.basename(rel)
        # 处理 _test_cc.py 已经有下划线前缀
        if basename.startswith("_"):
            dst_name = "moved_" + basename
        else:
            dst_name = "_moved_" + basename
        dst = os.path.join(SCRIPTS_TOOLS, dst_name)
        size, _ = get_size(src)
        try:
            shutil.move(src, dst)
            print(f"  ✓ 移动: {rel} → scripts/tools/{dst_name} ({human_size(size)})")
            moved.append((rel, dst_name, size))
        except Exception as e:
            print(f"  ✗ 失败: {rel} - {e}")
    return moved, skipped


def delete_temp_debug():
    """A2: 删除 1 个临时调试脚本"""
    print("\n" + "=" * 70)
    print("【A2】删除 1 个临时调试脚本")
    print("=" * 70)
    deleted = []
    for rel in TEMP_DEBUG_SCRIPTS:
        path = os.path.join(PROJECT_ROOT, rel)
        if not os.path.exists(path):
            print(f"  ⊘ 跳过 (不存在): {rel}")
            continue
        size, _ = get_size(path)
        try:
            os.remove(path)
            print(f"  ✓ 删除: {rel} ({human_size(size)})")
            deleted.append((rel, size))
        except Exception as e:
            print(f"  ✗ 失败: {rel} - {e}")
    return deleted


def clean_coverage_html():
    """B: 清理 coverage_html/ 旧目录"""
    print("\n" + "=" * 70)
    print("【B】清理 coverage_html/ 旧覆盖率目录 (2026-06-04 数据)")
    print("=" * 70)
    cleaned = []
    if os.path.exists(COVERAGE_HTML_DIR):
        size, count = get_size(COVERAGE_HTML_DIR)
        try:
            shutil.rmtree(COVERAGE_HTML_DIR)
            print(f"  ✓ 删除目录: coverage_html/ ({count} 文件, {human_size(size)})")
            cleaned.append(("coverage_html/", count, size))
        except Exception as e:
            print(f"  ✗ 失败: {e}")
    else:
        print("  ⊘ coverage_html/ 不存在")
    # 顶层 .coverage 和 coverage.xml
    for rel in COVERAGE_FILES:
        path = os.path.join(PROJECT_ROOT, rel)
        if os.path.exists(path):
            size = os.path.getsize(path)
            try:
                os.remove(path)
                print(f"  ✓ 删除文件: {rel} ({human_size(size)})")
                cleaned.append((rel, 1, size))
            except Exception as e:
                print(f"  ✗ 失败: {rel} - {e}")
        else:
            print(f"  ⊘ 跳过 (不存在): {rel}")
    return cleaned


def clean_tests_logs():
    """C: 清理 tests/logs/ 测试累积日志"""
    print("\n" + "=" * 70)
    print("【C】清理 tests/logs/ 测试累积日志")
    print("=" * 70)
    cleaned = []
    if not os.path.exists(TESTS_LOGS_DIR):
        print("  ⊘ tests/logs/ 不存在")
        return cleaned
    # 列出待删文件
    files = []
    for root, dirs, fnames in os.walk(TESTS_LOGS_DIR):
        for f in fnames:
            files.append(os.path.join(root, f))
    total_size = sum(os.path.getsize(f) for f in files if os.path.isfile(f))
    print(f"  待清理: {len(files)} 文件, {human_size(total_size)}")
    # 显示前 10 个
    for f in files[:10]:
        print(f"    - {os.path.relpath(f, PROJECT_ROOT)} ({human_size(os.path.getsize(f))})")
    if len(files) > 10:
        print(f"    ... 还有 {len(files) - 10} 个文件")
    # 删除整个目录后重建空目录
    try:
        shutil.rmtree(TESTS_LOGS_DIR)
        os.makedirs(TESTS_LOGS_DIR, exist_ok=True)
        # 加个 .gitkeep 防止被 .gitignore 吞掉
        with open(os.path.join(TESTS_LOGS_DIR, ".gitkeep"), "w") as fp:
            fp.write("# 目录占位，pytest 日志输出位置\n")
        print(f"  ✓ 清理完成，保留空目录 + .gitkeep")
        cleaned.append(("tests/logs/", len(files), total_size))
    except Exception as e:
        print(f"  ✗ 失败: {e}")
    return cleaned


def main():
    print("=" * 70)
    print("综合清理脚本 - 执行 A/B/C 三个清理方案")
    print("=" * 70)
    print(f"项目根目录: {PROJECT_ROOT}")

    a1_moved, a1_skipped = move_utility_scripts()
    a2_deleted = delete_temp_debug()
    b_cleaned = clean_coverage_html()
    c_cleaned = clean_tests_logs()

    # 汇总
    print("\n" + "=" * 70)
    print("【清理汇总】")
    print("=" * 70)
    a_size = sum(x[2] for x in a1_moved) + sum(x[1] for x in a2_deleted)
    a_files = len(a1_moved) + len(a2_deleted)
    b_size = sum(x[2] for x in b_cleaned)
    b_files = sum(x[1] for x in b_cleaned)
    c_size = sum(x[2] for x in c_cleaned)
    c_files = sum(x[1] for x in c_cleaned)

    print(f"  A: 移动 {len(a1_moved)} + 删除 {len(a2_deleted)} = {a_files} 文件, 释放 {human_size(a_size)}")
    print(f"  B: 清理 coverage 数据, {b_files} 文件, 释放 {human_size(b_size)}")
    print(f"  C: 清理测试日志, {c_files} 文件, 释放 {human_size(c_size)}")
    print(f"  ─────────────────────────────────────")
    print(f"  总计: {a_files + b_files + c_files} 文件, 释放 {human_size(a_size + b_size + c_size)}")
    print()
    print("✅ 清理完成！")


if __name__ == "__main__":
    main()
