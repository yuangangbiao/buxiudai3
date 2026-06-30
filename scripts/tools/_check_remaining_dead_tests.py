# -*- coding: utf-8 -*-
"""检查剩余死测试文件的存在状态，并读取内容判断处理方式"""
import os

PROJECT_ROOT = r"d:\yuan\不锈钢网带跟单3.0"

CATEGORIES = {
    "真正死测试（无 def test_*，应删除）": [
        "tests/_analyze_imports.py",
        "tests/generate_report.py",
    ],
    "工具/调试脚本（应移到 scripts/tools/）": [
        "tests/unit/models/_run_native_coverage.py",
        "tests/unit/models/_run_operator_full_cov.py",
        "tests/unit/utils/_debug_fixture.py",
        "mobile_api_ai/tests/unit/_syspath_runner.py",
        "mobile_api_ai/tests/unit/e2e_get_packages_process_report.py",
        "mobile_api_ai/tests/unit/http_client.py",
    ],
}

def check_has_test_function(filepath):
    """检查文件是否有 def test_* 函数"""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        lines = content.split("\n")
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("def test_") or stripped.startswith("async def test_"):
                return True
        return False
    except Exception:
        return False

def main():
    print("=" * 80)
    print("剩余死测试文件状态检查")
    print("=" * 80)

    total_gone = 0
    total_exists = 0

    for category, files in CATEGORIES.items():
        print(f"\n【{category}】")
        exists = []
        gone = []
        for rel in files:
            full = os.path.join(PROJECT_ROOT, rel)
            if os.path.exists(full):
                size = os.path.getsize(full)
                has_test = check_has_test_function(full)
                print(f"  EXISTS {size:>8} B  has_test={has_test}  {rel}")
                exists.append((rel, size, has_test))
                total_exists += 1
            else:
                print(f"  GONE   {'':>8}    {rel}")
                gone.append(rel)
                total_gone += 1

        print(f"  小计: 存在 {len(exists)} 个, 已消失 {len(gone)} 个")

    # 扫描 tests/ 目录下的其他潜在死测试（不在上面列表中的）
    print("\n【扫描 tests/ 下其他潜在死测试（无 def test_*，不在上面列表）】")
    potential_dead = []
    skip_patterns = ["__pycache__", ".pytest_cache", "conftest", "__init__", ".pyc",
                     "_moved_", "_complete", "_depth", "_gaps", "_basic",
                     "test_quality_rule.py", "test_app.py", "test_circuit",
                     "test_final_batch2", "test_startup_integration", "test_business",
                     "test_smoke_basic", "test_re002"]
    for root, dirs, fnames in os.walk(os.path.join(PROJECT_ROOT, "tests")):
        dirs[:] = [d for d in dirs if not any(p in d for p in skip_patterns)]
        for fname in fnames:
            if not fname.endswith(".py"):
                continue
            if any(p in fname for p in skip_patterns):
                continue
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, PROJECT_ROOT).replace("\\", "/")
            if check_has_test_function(fpath):
                continue
            size = os.path.getsize(fpath)
            print(f"  EXISTS {size:>8} B  {rel}")
            potential_dead.append((rel, size))
            total_exists += 1

    # 扫描 scripts/test_*.py
    print("\n【扫描 scripts/test_*.py（验收脚本，应移到 scripts/manual_acceptance/）】")
    scripts_manual = []
    scripts_dir = os.path.join(PROJECT_ROOT, "scripts")
    if os.path.exists(scripts_dir):
        for fname in sorted(os.listdir(scripts_dir)):
            if not fname.startswith("test_") or not fname.endswith(".py"):
                continue
            fpath = os.path.join(scripts_dir, fname)
            if os.path.isfile(fpath):
                rel = f"scripts/{fname}"
                size = os.path.getsize(fpath)
                has_test = check_has_test_function(fpath)
                print(f"  EXISTS {size:>8} B  has_test={has_test}  {rel}")
                scripts_manual.append((rel, size, has_test))
                total_exists += 1

    print("\n" + "=" * 80)
    print(f"汇总: 存在 {total_exists} 个, 已消失 {total_gone} 个")
    print(f"需要处理（存在）: {total_exists} 个")
    print("=" * 80)

if __name__ == "__main__":
    main()
