"""增强的报告系统 - 支持历史基线对比 + TestResult 自动注入"""
import json
import os
import sys
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """单个测试结果"""
    name: str
    layer: str  # L1/L2/L3/L4
    module: str
    status: str  # passed/failed/skipped/error
    duration: float
    timestamp: str
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    screenshot: Optional[str] = None
    retry_count: int = 0
    worker_id: str = 'master'


@dataclass
class TestRun:
    """一次完整测试运行"""
    run_id: str
    start_time: str
    end_time: Optional[str] = None
    duration: float = 0
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    error: int = 0
    results: List[TestResult] = field(default_factory=list)
    environment: Dict = field(default_factory=dict)
    git_info: Dict = field(default_factory=dict)


class ReportManager:
    """报告管理器"""
    
    def __init__(self, base_dir: str = 'tests/reports'):
        self.base_dir = Path(base_dir)
        self.history_dir = self.base_dir / 'history'
        self.latest_dir = self.base_dir / 'latest'
        self.baseline_file = self.base_dir / 'baseline.json'
        
        for d in [self.history_dir, self.latest_dir]:
            d.mkdir(parents=True, exist_ok=True)
    
    def save_run(self, run: TestRun):
        """保存一次测试运行 - 修复 P1-5: 接收 run 时计算汇总数据"""
        # 修复 P1-5: 重新计算 total/passed/failed 等汇总（防止外部数据不一致）
        run.total = len(run.results)
        run.passed = sum(1 for r in run.results if r.status == 'passed')
        run.failed = sum(1 for r in run.results if r.status == 'failed')
        run.skipped = sum(1 for r in run.results if r.status == 'skipped')
        run.error = sum(1 for r in run.results if r.status == 'error')

        # 计算 duration
        if run.results:
            try:
                start = datetime.fromisoformat(run.start_time)
                end = datetime.fromisoformat(run.end_time) if run.end_time else datetime.now()
                run.duration = (end - start).total_seconds()
            except Exception as e:
                logger.debug(f"duration 计算失败: {e}")
                run.duration = sum(r.duration for r in run.results)

        # 保存到历史
        history_file = self.history_dir / f"{run.run_id}.json"
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(run), f, ensure_ascii=False, indent=2)

        # 同时复制到 latest
        latest_file = self.latest_dir / 'report.json'
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(run), f, ensure_ascii=False, indent=2)

        # 生成 Markdown 报告
        try:
            md_content = self.generate_markdown_report(run)
            md_file = self.latest_dir / 'report.md'
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(md_content)
        except Exception as e:
            logger.warning(f"生成 Markdown 报告失败: {e}")

        # 清理旧历史（保留最近 30 次）
        self._cleanup_old_history(keep=30)

        logger.info(f"📊 报告已保存: {history_file}")
    
    def get_baseline(self) -> Optional[TestRun]:
        """获取基线"""
        if not self.baseline_file.exists():
            return None
        try:
            with open(self.baseline_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return self._dict_to_run(data)
        except Exception:
            return None
    
    def set_baseline(self, run_id: str):
        """设置基线"""
        history_file = self.history_dir / f"{run_id}.json"
        if history_file.exists():
            shutil.copy2(history_file, self.baseline_file)
    
    def compare_with_baseline(self, current: TestRun) -> Dict:
        """与基线对比"""
        baseline = self.get_baseline()
        if not baseline:
            return {'has_baseline': False}
        
        # 找出新增/修复/仍失败的测试
        baseline_results = {r.name: r for r in baseline.results}
        current_results = {r.name: r for r in current.results}
        
        new_failures = [
            r for name, r in current_results.items()
            if r.status == 'failed' and (
                name not in baseline_results or
                baseline_results[name].status != 'failed'
            )
        ]
        
        fixed_tests = [
            name for name, r in current_results.items()
            if name in baseline_results and
            r.status == 'passed' and
            baseline_results[name].status == 'failed'
        ]
        
        still_failing = [
            name for name, r in current_results.items()
            if name in baseline_results and
            r.status == 'failed' and
            baseline_results[name].status == 'failed'
        ]
        
        return {
            'has_baseline': True,
            'baseline_run_id': baseline.run_id,
            'baseline_pass_rate': f"{baseline.passed / max(baseline.total, 1) * 100:.1f}%",
            'current_pass_rate': f"{current.passed / max(current.total, 1) * 100:.1f}%",
            'new_failures': [asdict(r) for r in new_failures],
            'fixed_tests': fixed_tests,
            'still_failing': still_failing,
            'pass_rate_change': (
                current.passed / max(current.total, 1) -
                baseline.passed / max(baseline.total, 1)
            ) * 100,
        }
    
    def get_trends(self, limit: int = 10) -> List[Dict]:
        """获取历史趋势"""
        history_files = sorted(self.history_dir.glob('*.json'), reverse=True)[:limit]
        trends = []
        for f in reversed(history_files):
            try:
                with open(f, 'r', encoding='utf-8') as fp:
                    data = json.load(fp)
                trends.append({
                    'run_id': data['run_id'],
                    'start_time': data['start_time'],
                    'total': data['total'],
                    'passed': data['passed'],
                    'failed': data['failed'],
                    'pass_rate': f"{data['passed'] / max(data['total'], 1) * 100:.1f}%",
                    'duration': data['duration'],
                })
            except Exception:
                pass
        return trends
    
    def _cleanup_old_history(self, keep: int = 30):
        """清理旧历史"""
        history_files = sorted(self.history_dir.glob('*.json'), reverse=True)
        for f in history_files[keep:]:
            try:
                f.unlink()
            except Exception:
                pass
    
    def _dict_to_run(self, data: dict) -> TestRun:
        results = [TestResult(**r) for r in data.get('results', [])]
        return TestRun(
            run_id=data['run_id'],
            start_time=data['start_time'],
            end_time=data.get('end_time'),
            duration=data.get('duration', 0),
            total=data.get('total', 0),
            passed=data.get('passed', 0),
            failed=data.get('failed', 0),
            skipped=data.get('skipped', 0),
            error=data.get('error', 0),
            results=results,
            environment=data.get('environment', {}),
            git_info=data.get('git_info', {}),
        )
    
    def generate_markdown_report(self, run: TestRun) -> str:
        """生成 Markdown 报告"""
        pass_rate = run.passed / max(run.total, 1) * 100
        comparison = self.compare_with_baseline(run)
        trends = self.get_trends(limit=5)
        
        lines = [
            "# 测试运行报告",
            "",
            f"**运行ID**: `{run.run_id}`  ",
            f"**开始时间**: {run.start_time}  ",
            f"**耗时**: {run.duration:.1f}秒  ",
            "",
            "## 总体结果",
            "",
            f"| 指标 | 数值 |",
            f"|------|------|",
            f"| 总用例 | {run.total} |",
            f"| 通过 | {run.passed} ✅ |",
            f"| 失败 | {run.failed} ❌ |",
            f"| 跳过 | {run.skipped} ⏭️ |",
            f"| 错误 | {run.error} 💥 |",
            f"| **通过率** | **{pass_rate:.1f}%** |",
            "",
        ]
        
        if comparison.get('has_baseline'):
            lines.extend([
                "## 与基线对比",
                "",
                f"- 基线: {comparison['baseline_run_id']} ({comparison['baseline_pass_rate']})",
                f"- 当前: ({comparison['current_pass_rate']})",
                f"- 变化: {comparison['pass_rate_change']:+.1f}%",
                f"- 新增失败: {len(comparison['new_failures'])}",
                f"- 修复: {len(comparison['fixed_tests'])}",
                f"- 仍失败: {len(comparison['still_failing'])}",
                "",
            ])
        
        if trends:
            lines.extend([
                "## 历史趋势",
                "",
                "| 时间 | 通过率 | 失败 | 耗时 |",
                "|------|:------:|:----:|:----:|",
            ])
            for t in trends:
                lines.append(
                    f"| {t['start_time']} | {t['pass_rate']} | {t['failed']} | {t['duration']:.0f}s |"
                )
            lines.append("")
        
        # 失败详情
        failed_results = [r for r in run.results if r.status == 'failed']
        if failed_results:
            lines.extend([
                "## 失败详情",
                "",
            ])
            for r in failed_results[:20]:  # 最多 20 条
                lines.extend([
                    f"### ❌ {r.name}",
                    f"- 模块: {r.module} ({r.layer})",
                    f"- 错误: {r.error_type or 'Unknown'}: {r.error_message or 'N/A'}",
                    f"- 耗时: {r.duration:.2f}秒",
                    "",
                ])
        
        return "\n".join(lines)


# 全局实例
report_manager = ReportManager()


# ==================== CLI Entry Point (修复 A2) ====================

def main():
    """命令行入口 - 修复 A2: 提供 python -m tests.core.report_enhanced generate"""
    import argparse
    parser = argparse.ArgumentParser(description='测试报告生成器')
    subparsers = parser.add_subparsers(dest='command')

    # generate 子命令
    gen_parser = subparsers.add_parser('generate', help='生成最新报告')
    gen_parser.add_argument('--run-id', help='指定 run_id')
    gen_parser.add_argument('--output', help='输出路径')

    # show 子命令
    show_parser = subparsers.add_parser('show', help='显示历史趋势')
    show_parser.add_argument('--limit', type=int, default=10, help='最近 N 次')

    # baseline 子命令
    base_parser = subparsers.add_parser('set-baseline', help='设置基线')
    base_parser.add_argument('run_id', help='run_id')

    args = parser.parse_args()

    if args.command == 'generate':
        # 从 latest 目录读取最新报告重新生成
        latest = report_manager.latest_dir / 'report.json'
        if not latest.exists():
            print(f"❌ 报告不存在: {latest}")
            print("   请先运行测试生成报告")
            sys.exit(1)

        with open(latest, 'r', encoding='utf-8') as f:
            data = json.load(f)
        run = report_manager._dict_to_run(data)
        report_manager.save_run(run)
        print(f"✅ 报告已生成: {report_manager.latest_dir}")

    elif args.command == 'show':
        trends = report_manager.get_trends(args.limit)
        print(f"\n最近 {len(trends)} 次测试:")
        for t in trends:
            print(f"  {t['start_time']}  通过率={t['pass_rate']}  失败={t['failed']}  耗时={t['duration']:.0f}s")

    elif args.command == 'set-baseline':
        report_manager.set_baseline(args.run_id)
        print(f"✅ 已设置基线: {args.run_id}")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
