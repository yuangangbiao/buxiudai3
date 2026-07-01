# -*- coding: utf-8 -*-
"""
测试文件收集脚本 - 自动扫描并迁移散落的测试文件到统一目录
执行方式: python scripts/tools/collect_test_files.py

Author: AI Assistant
Date: 2026-06-14
"""
import os
import sys
import shutil
import json
import re
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TESTS_DIR = PROJECT_ROOT / "tests"
ARCHIVE_DIR = TESTS_DIR / "scripts_archive"

LOG_FILE = PROJECT_ROOT / "test_collect.log"

TEST_PATTERNS = [
    r"^test_.*\.py$",
    r"^.*_test\.py$",
    r"^__test_.*\.py$",
]

EXCLUDE_DIRS = [
    "__pycache__",
    ".pytest_cache",
    "build",
    "dist",
    ".sandbox",
    ".git",
    "node_modules",
    "venv",
    ".venv",
]

EXCLUDE_PATHS = [
    str(TESTS_DIR),
]

TEST_DIR_NAMES = ["tests", "test", "__test__"]

TEST_CONTENT_MARKERS = [
    r"import\s+unittest",
    r"import\s+pytest",
    r"from\s+unittest",
    r"from\s+pytest",
    r"\bclass\s+Test\w+",
    r"\bclass\s+\w+Test",
    r"\bclass\s+\w+Tests",
    r"\bdef\s+test_\w+",
    r"@pytest\.fixture",
    r"@pytest\.mark\.",
    r"@unittest\.skip",
    r"unittest\.TestCase",
    r"setUp|tearDown",
    r"assertEqual|assertTrue|assertFalse|assertIs|assertIn|assertRaises",
    r"self\.assert",
    r"TestCase",
]

TEST_FILE_MARKERS = [
    "test_*.py",
    "*_test.py",
    "__test_*.py",
]


def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def should_exclude(path_str):
    for exclude in EXCLUDE_PATHS:
        if exclude in path_str:
            return True
    for part in Path(path_str).parts:
        if part in EXCLUDE_DIRS or part.startswith("."):
            if part not in TEST_DIR_NAMES:
                return True
    return False


def is_likely_test_filename(filename):
    if not filename.endswith(".py"):
        return False
    
    if filename in ("conftest.py", "collect_test_files.py"):
        return False
    
    name_lower = filename.lower()
    
    for pattern in TEST_FILE_MARKERS:
        pattern_star = pattern.replace("*", ".*").replace("?", ".")
        if re.match(pattern_star, name_lower):
            return True
    
    return False


def is_test_content(file_path):
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(4096)
        
        match_count = 0
        for marker in TEST_CONTENT_MARKERS:
            if re.search(marker, content, re.IGNORECASE):
                match_count += 1
        
        return match_count >= 2
    except Exception:
        return False


def is_real_test_file(file_path):
    filename = os.path.basename(file_path)
    
    if is_likely_test_filename(filename):
        return is_test_content(file_path)
    
    return False


def find_scattered_test_files():
    scattered = []
    candidates = []
    
    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".")]

        if should_exclude(root):
            continue

        for file in files:
            if file.endswith(".py") and file not in ("conftest.py", "collect_test_files.py"):
                full_path = Path(root) / file
                if str(full_path).startswith(str(TESTS_DIR)):
                    continue
                
                if is_likely_test_filename(file):
                    candidates.append({
                        "file": str(full_path),
                        "name": file,
                        "size": full_path.stat().st_size,
                    })
    
    log(f"🔍 发现 {len(candidates)} 个候选测试文件，开始验证...")
    
    for candidate in candidates:
        if is_test_content(candidate["file"]):
            rel_path = Path(candidate["file"]).relative_to(PROJECT_ROOT)
            candidate["rel"] = str(rel_path)
            scattered.append(candidate)
        else:
            log(f"  ⏭️  {candidate['name']} - 内容验证不通过，跳过")
    
    return scattered


def migrate_test_file(file_info):
    src = Path(file_info["file"])
    filename = src.name
    dst = ARCHIVE_DIR / filename

    counter = 1
    while dst.exists():
        stem = src.stem
        suffix = src.suffix
        dst = ARCHIVE_DIR / f"{stem}_{counter}{suffix}"
        counter += 1

    try:
        shutil.copy2(src, dst)
        src.unlink()
        return True, str(dst.relative_to(PROJECT_ROOT))
    except Exception as e:
        return False, str(e)


def collect_and_migrate():
    log("=" * 60)
    log("🧪 测试文件收集任务开始")
    log(f"📂 项目根目录: {PROJECT_ROOT}")

    scattered = find_scattered_test_files()

    if not scattered:
        log("✅ 未发现需要迁移的测试文件")
        return {"status": "success", "scattered": 0, "migrated": 0}

    log(f"📁 发现 {len(scattered)} 个散落的测试文件:")

    migrated = 0
    failed = 0
    migration_log = []

    for info in scattered:
        log(f"  - {info.get('rel', info['name'])} ({info['size']} bytes)")

        success, result = migrate_test_file(info)
        if success:
            migrated += 1
            migration_log.append(f"  ✅ {info.get('rel', info['name'])} → {result}")
            log(f"    → 已迁移到 {result}")
        else:
            failed += 1
            migration_log.append(f"  ❌ {info.get('rel', info['name'])} 失败: {result}")
            log(f"    → 迁移失败: {result}")

    summary = {
        "status": "success" if failed == 0 else "partial",
        "scattered": len(scattered),
        "migrated": migrated,
        "failed": failed,
        "details": migration_log,
        "timestamp": datetime.now().isoformat(),
    }

    log("")
    log("=" * 60)
    log(f"📊 任务完成: 发现 {len(scattered)} 个, 迁移 {migrated} 个, 失败 {failed} 个")
    log("=" * 60)

    summary_file = PROJECT_ROOT / "test_collect_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return summary


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--dry-run":
        log("🔍 干运行模式 - 仅扫描不迁移")
        scattered = find_scattered_test_files()
        if scattered:
            log(f"发现 {len(scattered)} 个需要迁移的测试文件:")
            for info in scattered:
                log(f"  - {info.get('rel', info['name'])}")
        else:
            log("✅ 未发现需要迁移的测试文件")
        return

    collect_and_migrate()


if __name__ == "__main__":
    main()
