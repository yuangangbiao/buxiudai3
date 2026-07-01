# -*- coding: utf-8 -*-
"""
pytest覆盖率基准测量脚本 (v3.7.1)

功能:
- 采集unit/integration/e2e三层覆盖率
- 生成baseline.json基准文件
- 对比当前覆盖率与基准，输出差异报告

依赖:
    pip install pytest pytest-cov

使用:
    # Step 1: 采集基准 (只在Week 0跑一次)
    python scripts/measure_coverage_baseline.py --collect-baseline

    # Step 2: 日常检查
    python scripts/measure_coverage_baseline.py

    # Step 3: 查看详细差异
    python scripts/measure_coverage_baseline.py --verbose
"""

import os
import sys
import json
import subprocess
import argparse
from datetime import datetime
from typing import Dict, Any, List, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOBILE_API_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, MOBILE_API_DIR)

COVERAGE_JSON = os.path.join(BASE_DIR, 'coverage_baseline.json')
COVERAGE_REPORT_DIR = os.path.join(BASE_DIR, 'htmlcov')

UNIT_TEST_DIR = os.path.join(MOBILE_API_DIR, 'tests', 'unit')
INTEGRATION_TEST_DIR = os.path.join(MOBILE_API_DIR, 'tests', 'integration')
E2E_TEST_DIR = os.path.join(MOBILE_API_DIR, 'tests', 'e2e')
UNIT_TEST_REL = os.path.join('mobile_api_ai', 'tests', 'unit')
INTEGRATION_TEST_REL = os.path.join('mobile_api_ai', 'tests', 'integration')
E2E_TEST_REL = os.path.join('mobile_api_ai', 'tests', 'e2e')

COV_SOURCES = ['dispatch_center', 'storage', 'api', 'services', 'bots', 'core']


def _run_pytest_with_coverage(test_paths: List[str], cov_output_json: str) -> Dict[str, Any]:
    """
    运行pytest并收集覆盖率 (使用 coverage run + coverage json 方式，绕过 pytest-cov 兼容性问题)
    返回: {'ok': bool, 'coverage': {}, 'stdout': str, 'stderr': str, 'exitcode': int}
    """
    import tempfile

    test_path = test_paths[0] if test_paths else ''

    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['PYTHONPATH'] = BASE_DIR

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            cov_data_dir = tmpdir

            run_cmd = [
                sys.executable, '-m', 'coverage', 'run',
                '--source=' + ','.join(COV_SOURCES),
                '--omit=*/tests/*,*/migrations/*,*/scripts/*',
                '-m', 'pytest',
                '--ignore=mobile_api_ai/tests/unit/test_order_status_contract.py',
                '-W', 'ignore::pytest.PytestRemovedIn9Warning',
                '-W', 'ignore::ResourceWarning',
                test_path,
            ]

            r1 = subprocess.run(
                run_cmd,
                cwd=BASE_DIR, capture_output=True, text=True, timeout=300, env=env
            )

            json_cmd = [
                sys.executable, '-m', 'coverage', 'json',
                '-o', cov_output_json, '--quiet',
            ]
            r2 = subprocess.run(
                json_cmd,
                cwd=BASE_DIR, capture_output=True, text=True, timeout=60, env=env
            )

            coverage_data = {}
            if os.path.exists(cov_output_json):
                try:
                    with open(cov_output_json, 'r', encoding='utf-8') as f:
                        coverage_data = json.load(f)
                except Exception:
                    pass

            stdout = r1.stdout[-5000:] if r1.stdout else ''
            lines = stdout.split('\n')
            passed = sum(1 for l in lines if 'PASSED' in l)
            failed = sum(1 for l in lines if 'FAILED' in l)

            return {
                'ok': r1.returncode == 0,
                'coverage': coverage_data,
                'stdout': stdout,
                'stderr': (r1.stderr or '')[:2000],
                'exitcode': r1.returncode,
                'passed': passed,
                'failed': failed,
            }

    except subprocess.TimeoutExpired:
        return {
            'ok': False, 'coverage': {}, 'stdout': '', 'stderr': 'pytest执行超时(300s)',
            'exitcode': -1, 'passed': 0, 'failed': 0,
        }
    except FileNotFoundError:
        return {
            'ok': False, 'coverage': {}, 'stdout': '', 'stderr': 'pytest/coverage未找到，请先: pip install pytest coverage',
            'exitcode': -2, 'passed': 0, 'failed': 0,
        }


def extract_totals(cov_data: Dict) -> Dict[str, Any]:
    """从coverage.json提取总计数据"""
    totals = cov_data.get('totals', {})
    return {
        'lines_covered': totals.get('covered_lines', 0),
        'lines_total': totals.get('missing_lines', 0) + totals.get('covered_lines', 0),
        'line_rate': round(totals.get('percent_covered', 0), 2),
        'branches_covered': totals.get('covered_branches', 0),
        'branches_total': totals.get('missing_branches', 0) + totals.get('covered_branches', 0),
        'branch_rate': round(totals.get('percent_branches_covered', 0), 2),
    }


def collect_baseline() -> bool:
    """采集三层测试覆盖率，生成baseline"""
    import tempfile

    results = {}

    print('=== 采集单元测试覆盖率 ===')
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
        unit_json = f.name
    try:
        r = _run_pytest_with_coverage([UNIT_TEST_REL], unit_json)
        results['unit'] = {
            'totals': extract_totals(r['coverage']),
            'ok': r['ok'],
            'passed': r['passed'],
            'failed': r['failed'],
            'stdout': r['stdout'],
        }
        print(f"  单元测试: {'✅' if r['ok'] else '❌'} {r['passed']} passed, {r['failed']} failed")
        print(f"  行覆盖率: {results['unit']['totals']['line_rate']}%")
    finally:
        if os.path.exists(unit_json):
            os.unlink(unit_json)

    print('=== 采集集成测试覆盖率 ===')
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
        integ_json = f.name
    try:
        r = _run_pytest_with_coverage([INTEGRATION_TEST_REL], integ_json)
        results['integration'] = {
            'totals': extract_totals(r['coverage']),
            'ok': r['ok'],
            'passed': r['passed'],
            'failed': r['failed'],
        }
        print(f"  集成测试: {'✅' if r['ok'] else '❌'} {r['passed']} passed, {r['failed']} failed")
        print(f"  行覆盖率: {results['integration']['totals']['line_rate']}%")
    finally:
        if os.path.exists(integ_json):
            os.unlink(integ_json)

    e2e_exists = os.path.exists(E2E_TEST_DIR)
    if e2e_exists:
        print('=== 采集E2E测试覆盖率 ===')
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            e2e_json = f.name
        try:
            r = _run_pytest_with_coverage([E2E_TEST_REL], e2e_json)
            results['e2e'] = {
                'totals': extract_totals(r['coverage']),
                'ok': r['ok'],
                'passed': r['passed'],
                'failed': r['failed'],
            }
            print(f"  E2E测试: {'✅' if r['ok'] else '❌'} {r['passed']} passed, {r['failed']} failed")
            print(f"  行覆盖率: {results['e2e']['totals']['line_rate']}%")
        finally:
            if os.path.exists(e2e_json):
                os.unlink(e2e_json)
    else:
        print('  (E2E测试目录不存在，跳过)')
        results['e2e'] = None

    baseline = {
        'version': 'v3.7.1',
        'collected_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'pytest_threshold': 80.0,
        'results': results,
    }

    with open(COVERAGE_JSON, 'w', encoding='utf-8') as f:
        json.dump(baseline, f, ensure_ascii=False, indent=2)

    total_line_rate = 0
    total_weight = 0
    for key in ('unit', 'integration', 'e2e'):
        if results.get(key):
            weight = {'unit': 0.4, 'integration': 0.4, 'e2e': 0.2}[key]
            total_line_rate += results[key]['totals']['line_rate'] * weight
            total_weight += weight
    if total_weight > 0:
        total_line_rate /= total_weight

    print(f'\n✅ Baseline已保存至 {COVERAGE_JSON}')
    print(f'综合行覆盖率: {round(total_line_rate, 2)}% (基准阈值: 80%)')
    return True


def load_baseline() -> Optional[Dict]:
    if not os.path.exists(COVERAGE_JSON):
        return None
    try:
        with open(COVERAGE_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def compare_with_baseline(current: Dict, baseline: Dict, verbose: bool = False) -> Dict[str, Any]:
    """对比当前覆盖率与基准，返回差异"""
    diff = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'baseline_collected_at': baseline.get('collected_at', ''),
        'layers': {},
        'overall': {},
        'pass': True,
        'threshold': baseline.get('pytest_threshold', 80.0),
        'issues': [],
    }

    layer_names = {'unit': '单元测试', 'integration': '集成测试', 'e2e': 'E2E测试'}
    layer_weights = {'unit': 0.4, 'integration': 0.4, 'e2e': 0.2}

    weighted_baseline = 0
    weighted_current = 0
    total_weight = 0

    for layer in ('unit', 'integration', 'e2e'):
        b_totals = baseline['results'].get(layer, {})
        c_totals = current['results'].get(layer, {})

        if not b_totals:
            continue

        b_line = b_totals.get('totals', {}).get('line_rate', 0)
        c_line = c_totals.get('totals', {}).get('line_rate', 0) if c_totals else 0

        diff['layers'][layer] = {
            'name': layer_names[layer],
            'baseline_rate': b_line,
            'current_rate': c_line,
            'delta': round(c_line - b_line, 2),
            'baseline_passed': b_totals.get('passed', 0),
            'baseline_failed': b_totals.get('failed', 0),
            'current_passed': c_totals.get('passed', 0) if c_totals else 0,
            'current_failed': c_totals.get('failed', 0) if c_totals else 0,
        }

        weight = layer_weights[layer]
        weighted_baseline += b_line * weight
        weighted_current += c_line * weight
        total_weight += weight

    if total_weight > 0:
        weighted_baseline /= total_weight
        weighted_current /= total_weight

    diff['overall'] = {
        'baseline_rate': round(weighted_baseline, 2),
        'current_rate': round(weighted_current, 2),
        'delta': round(weighted_current - weighted_baseline, 2),
    }

    threshold = diff['threshold']
    if weighted_current < threshold:
        diff['pass'] = False
        diff['issues'].append(f'综合覆盖率 {weighted_current}% < 阈值 {threshold}%')

    if verbose:
        print(f'\n{"="*60}')
        print(f'覆盖率对比报告')
        print(f'{"="*60}')
        print(f'基准采集时间: {baseline.get("collected_at", "未知")}')
        print(f'当前检查时间: {diff["timestamp"]}')
        print(f'阈值: {threshold}%')
        print()
        for layer, info in diff['layers'].items():
            delta_icon = '📈' if info['delta'] >= 0 else '📉'
            print(f"  [{layer}] {info['name']}")
            print(f"    基准: {info['baseline_rate']}% | 当前: {info['current_rate']}% | {delta_icon} {info['delta']}%")
            print(f"    用例: 基准 {info['baseline_passed']}P/{info['baseline_failed']}F → 当前 {info['current_passed']}P/{info['current_failed']}F")
            print()
        print(f"  [综合] 加权覆盖率")
        print(f"    基准: {diff['overall']['baseline_rate']}% | 当前: {diff['overall']['current_rate']}% | {'✅' if diff['pass'] else '❌'}")
        print(f'{"="*60}')

    return diff


def run_current_measurement() -> Optional[Dict]:
    """运行当前覆盖率测量"""
    import tempfile

    results = {}

    for layer, test_dir in [('unit', UNIT_TEST_REL), ('integration', INTEGRATION_TEST_REL), ('e2e', E2E_TEST_REL)]:
        if not os.path.exists(test_dir):
            continue
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            tmp = f.name
        try:
            r = _run_pytest_with_coverage([test_dir], tmp)
            results[layer] = {
                'totals': extract_totals(r['coverage']),
                'ok': r['ok'],
                'passed': r['passed'],
                'failed': r['failed'],
            }
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    return {
        'version': 'v3.7.1-current',
        'measured_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'results': results,
    }


def main():
    parser = argparse.ArgumentParser(description='pytest覆盖率基准测量')
    parser.add_argument('--collect-baseline', action='store_true',
                        help='采集覆盖率基准(仅Week 0执行一次)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='详细输出对比报告')
    parser.add_argument('--json', action='store_true',
                        help='输出JSON格式')
    args = parser.parse_args()

    if args.collect_baseline:
        print('=== 采集pytest覆盖率基准 ===')
        collect_baseline()
        return

    baseline = load_baseline()
    if not baseline:
        print(f'❌ 未找到基准文件: {COVERAGE_JSON}')
        print('请先运行: python scripts/measure_coverage_baseline.py --collect-baseline')
        sys.exit(1)

    print('=== 测量当前覆盖率 ===')
    current = run_current_measurement()

    for layer, info in current['results'].items():
        print(f"  {layer}: {info['totals']['line_rate']}% ({info['passed']}P/{info['failed']}F)")

    diff = compare_with_baseline(current, baseline, verbose=args.verbose)

    if args.json:
        print(json.dumps(diff, ensure_ascii=False, indent=2))
        return

    if diff['pass']:
        print(f'\n✅ 通过: 综合覆盖率 {diff["overall"]["current_rate"]}% >= 阈值 {diff["threshold"]}%')
        sys.exit(0)
    else:
        print(f'\n❌ 未通过: {", ".join(diff["issues"])}')
        sys.exit(1)


if __name__ == '__main__':
    main()
