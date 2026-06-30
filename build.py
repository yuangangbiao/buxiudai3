# -*- coding: utf-8 -*-
"""
统一构建脚本 — 一键编译全部 7 个目标

用法:
  python build.py                    # 构建全部
  python build.py --list             # 列出目标
  python build.py main               # 只构建主系统
  python build.py --clean            # 清理 build/dist
"""
import os
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ARCHIVE_DIR = ROOT / "_archive" / "specs"  # 废弃 .spec 归档处

# ── 构建目标定义 ──
BUILD_TARGETS = {
    "main": {
        "spec": "不锈钢网带跟单系统v3.0.spec",
        "desc": "主系统（桌面端）",
    },
    "main_full": {
        "spec": "build_full_spec_3.0.1.spec",
        "desc": "主系统 v3.0.1 完整版",
    },
    "server": {
        "spec": "server.spec",
        "desc": "库存管理服务器",
    },
    "client": {
        "spec": "client.spec",
        "desc": "库存管理客户端",
    },
    "db_init": {
        "spec": "db_init.spec",
        "desc": "数据库初始化工具",
    },
    "wechat_bot": {
        "spec": str(ROOT / "mobile_api_ai" / "wechat_bot.spec"),
        "desc": "企业微信机器人",
    },
    "dashboard": {
        "spec": str(ROOT / "visualization_app" / "dashboard_launcher.spec"),
        "desc": "可视化大屏启动器",
    },
}


def build_one(name: str) -> bool:
    target = BUILD_TARGETS[name]
    spec_path = target["spec"]
    if not os.path.isabs(spec_path):
        spec_path = str(ROOT / spec_path)
    print(f"\n{'='*60}")
    print(f"  Building: {target['desc']} ({name})")
    print(f"  Spec:     {spec_path}")
    print(f"{'='*60}")
    cmd = [sys.executable, "-m", "PyInstaller", spec_path, "--noconfirm"]
    result = subprocess.run(cmd, cwd=str(ROOT))
    ok = result.returncode == 0
    status = "✅" if ok else "❌"
    print(f"  {status} {name} {'OK' if ok else 'FAILED (exit %d)' % result.returncode}")
    return ok


def build_all():
    results = {}
    for name in BUILD_TARGETS:
        results[name] = build_one(name)
    print(f"\n{'='*60}")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"  结果: {passed}/{total} 通过")
    if passed == total:
        print("  ✅ 全部构建成功")
    else:
        failed = [k for k, v in results.items() if not v]
        print(f"  ❌ 失败: {', '.join(failed)}")
    return passed == total


def clean():
    import shutil
    for d in ["build", "dist"]:
        path = ROOT / d
        if path.exists():
            shutil.rmtree(path)
            print(f"  清理: {d}/")


def main():
    if len(sys.argv) < 2:
        return 0 if build_all() else 1

    arg = sys.argv[1]
    if arg == "--list":
        print("构建目标:")
        for name, t in BUILD_TARGETS.items():
            print(f"  {name:15s} — {t['desc']}")
    elif arg == "--clean":
        clean()
    elif arg == "--help":
        print(__doc__)
    elif arg in BUILD_TARGETS:
        return 0 if build_one(arg) else 1
    else:
        print(f"未知目标: {arg}")
        print("可用: " + ", ".join(BUILD_TARGETS.keys()))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
