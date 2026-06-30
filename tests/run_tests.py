# -*- coding: utf-8 -*-
"""
统一测试入口 - 修复 P0-5 + A2

支持层级过滤、并行执行、报告生成。
"""
import os
import sys
import argparse
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


LAYER_DIRS = {
    'L1': 'tests/L1_smoke',
    'L2': 'tests/L2_modules',
    'L3': 'tests/L3_integration',
    'L4': 'tests/L4_scenarios',
    'all': 'tests',
}


def run_pytest(args):
    """执行 pytest"""
    cmd = [sys.executable, '-m', 'pytest'] + args
    print(f"\n{'=' * 70}")
    print(f"🚀 执行: {' '.join(cmd)}")
    print(f"{'=' * 70}\n")

    return subprocess.run(cmd, cwd=PROJECT_ROOT)


def parse_args():
    """解析命令行参数"""
    p = argparse.ArgumentParser(description='统一测试执行入口')

    p.add_argument('--layer', choices=list(LAYER_DIRS.keys()), default='all',
                   help='测试层级: L1 冒烟 / L2 模块 / L3 集成 / L4 场景 / all 全部')
    p.add_argument('--marker', help='按 marker 过滤，如 p0/security/perf')
    p.add_argument('--parallel', type=int, default=1,
                   help='并行 worker 数量 (默认 1 = 不并发)')
    p.add_argument('--headed', action='store_true', help='有头浏览器模式（看 UI）')
    p.add_argument('--no-cov', action='store_true', help='禁用覆盖率')
    p.add_argument('--html', action='store_true', help='生成 HTML 报告')
    p.add_argument('--rerun', type=int, default=0, help='失败重试次数')
    p.add_argument('--timeout', type=int, default=300, help='单测超时（秒）')
    p.add_argument('--keyword', '-k', help='按测试名关键字过滤')
    p.add_argument('--collect-only', action='store_true', help='只收集不执行')

    return p.parse_args()


def build_pytest_args(args) -> list:
    """组装 pytest 参数"""
    pytest_args = []

    # 路径
    if args.layer != 'all':
        pytest_args += [LAYER_DIRS[args.layer]]

    # marker
    if args.marker:
        pytest_args += ['-m', args.marker]

    # 关键字
    if args.keyword:
        pytest_args += ['-k', args.keyword]

    # 并发
    if args.parallel > 1:
        pytest_args += ['-n', str(args.parallel)]

    # 有头模式
    if args.headed:
        os.environ['HEADLESS'] = 'false'
        pytest_args += ['--headed=false']  # 让 pytest-playwright 知道

    # 覆盖率
    if args.no_cov:
        pytest_args += ['--no-cov']

    # 报告
    if args.html:
        report_path = PROJECT_ROOT / 'tests' / 'reports' / 'html' / 'report.html'
        report_path.parent.mkdir(parents=True, exist_ok=True)
        pytest_args += ['--html', str(report_path), '--self-contained-html']

    # 重试
    if args.rerun > 0:
        pytest_args += ['--reruns', str(args.rerun)]

    # 超时
    if args.timeout:
        pytest_args += ['--timeout', str(args.timeout)]

    # 仅收集
    if args.collect_only:
        pytest_args += ['--collect-only']

    return pytest_args


def main():
    args = parse_args()
    pytest_args = build_pytest_args(args)

    # 加载 .env.test
    env_file = PROJECT_ROOT / 'tests' / '.env.test'
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)

    result = run_pytest(pytest_args)
    sys.exit(result.returncode)


if __name__ == '__main__':
    main()
