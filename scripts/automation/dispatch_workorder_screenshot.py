# -*- coding: utf-8 -*-
"""
工单详情截图自动化脚本
功能：
1. 从调度中心流程编排进入
2. 点击订单进入工单详情
3. 对工序报工内的所有工序进行拍照（滚动截图）
4. 保存截图到指定目录
"""
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
SCRIPT_DIR = PROJECT_ROOT / "scripts" / "automation"
PLAYWRIGHT_SCRIPT = SCRIPT_DIR / "dispatch_workorder_screenshot.js"

DISPATCH_URL = os.environ.get("DISPATCH_URL", "http://localhost:5008/api/dispatch-center")
OUTPUT_DIR = PROJECT_ROOT / "exports" / "workorder_screenshots"

def get_timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def ensure_dir(path):
    path = Path(path)
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
    return path

def run_playwright():
    ensure_dir(OUTPUT_DIR)

    env = os.environ.copy()
    env["DISPATCH_URL"] = DISPATCH_URL
    env["OUTPUT_DIR"] = str(OUTPUT_DIR)

    print("=" * 70)
    print("🚀 启动工单详情截图自动化")
    print("=" * 70)
    print(f"📍 目标URL: {DISPATCH_URL}")
    print(f"📁 输出目录: {OUTPUT_DIR}")
    print("=" * 70)

    cmd = [
        sys.executable,
        "-m", "playwright", "codegen",
        "--target", "javascript",
        DISPATCH_URL
    ]

    print(f"\n💡 提示: 你可以使用以下命令直接运行Playwright脚本:")
    print(f"   node {PLAYWRIGHT_SCRIPT}")
    print(f"\n📝 或者使用 Python 的 subprocess 运行:")

    node_cmd = [
        "node",
        str(PLAYWRIGHT_SCRIPT)
    ]

    print(f"\n▶️ 执行命令: {' '.join(node_cmd)}")

    try:
        result = subprocess.run(
            node_cmd,
            env=env,
            cwd=str(SCRIPT_DIR),
            capture_output=False,
            text=True
        )
        return result.returncode
    except FileNotFoundError:
        print("❌ 错误: 未找到 node.exe，请确保已安装 Node.js")
        print("💡 替代方案：使用浏览器手动访问以下地址进行操作:")
        print(f"   {DISPATCH_URL}")
        return 1
    except Exception as e:
        print(f"❌ 执行错误: {e}")
        return 1

if __name__ == "__main__":
    exit_code = run_playwright()
    sys.exit(exit_code)
