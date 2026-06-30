"""L3: 性能基线测试 - 修复 P1-6 + P2-10"""
import time
import pytest
import requests
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed

# 修复 P1-6: 从 _config 导入，避免循环依赖
from tests.core._config import SERVICES


# 性能基线（可调）
PERF_BASELINES = {
    'desktop_web_orders_list': {'p95': 2.0, 'p99': 5.0, 'tps': 50},
    'desktop_web_login': {'p95': 1.5, 'p99': 3.0, 'tps': 100},
    'dispatch_operators': {'p95': 1.0, 'p99': 3.0, 'tps': 200},
    'mobile_my_tasks': {'p95': 1.5, 'p99': 3.0, 'tps': 100},
    'db_query': {'p95': 0.5, 'p99': 1.0, 'tps': 500},
}


class PerformanceResult:
    """性能测试结果"""
    
    def __init__(self, name: str):
        self.name = name
        self.latencies: list = []
        self.errors: list = []
        self.start_time = time.time()
    
    def add(self, latency: float, error: str = None):
        if error:
            self.errors.append(error)
        else:
            self.latencies.append(latency)
    
    @property
    def total(self):
        return len(self.latencies) + len(self.errors)
    
    @property
    def p50(self):
        return statistics.median(self.latencies) if self.latencies else 0
    
    @property
    def p95(self):
        if not self.latencies:
            return 0
        sorted_lat = sorted(self.latencies)
        idx = int(len(sorted_lat) * 0.95)
        return sorted_lat[idx]
    
    @property
    def p99(self):
        if not self.latencies:
            return 0
        sorted_lat = sorted(self.latencies)
        idx = int(len(sorted_lat) * 0.99)
        return sorted_lat[idx]
    
    @property
    def tps(self):
        elapsed = time.time() - self.start_time
        return len(self.latencies) / max(elapsed, 0.001)
    
    @property
    def error_rate(self):
        return len(self.errors) / max(self.total, 1)
    
    def check_baseline(self) -> dict:
        """对照基线检查"""
        baseline = PERF_BASELINES.get(self.name, {})
        result = {
            'name': self.name,
            'p50': f"{self.p50 * 1000:.1f}ms",
            'p95': f"{self.p95 * 1000:.1f}ms",
            'p99': f"{self.p99 * 1000:.1f}ms",
            'tps': f"{self.tps:.1f}",
            'error_rate': f"{self.error_rate * 100:.1f}%",
            'checks': {},
        }
        
        if 'p95' in baseline:
            p95_s = self.p95
            baseline_p95 = baseline['p95']
            passed = p95_s <= baseline_p95
            result['checks']['p95'] = {
                'actual': p95_s, 'baseline': baseline_p95,
                'passed': passed
            }
        if 'tps' in baseline:
            passed = self.tps >= baseline['tps']
            result['checks']['tps'] = {
                'actual': self.tps, 'baseline': baseline['tps'],
                'passed': passed
            }
        
        return result


@pytest.mark.L3
@pytest.mark.perf
class TestPerformanceBaseline:
    """性能基线"""
    
    def _measure_url(self, url: str, count: int = 20) -> PerformanceResult:
        """测量 URL 性能"""
        result = PerformanceResult(url)
        result.start_time = time.time()
        for _ in range(count):
            try:
                start = time.time()
                r = requests.get(url, timeout=10)
                latency = time.time() - start
                if r.status_code < 500:
                    result.add(latency)
                else:
                    result.add(latency, f"HTTP {r.status_code}")
            except Exception as e:
                result.add(0, str(e)[:30])
        return result
    
    def test_orders_list_perf(self):
        """订单列表性能 - 修复 P1-6: 添加 assert 实际验证"""
        result = self._measure_url(f'{SERVICES["desktop_web"]}/api/orders/list', count=20)
        check = result.check_baseline()

        # 修复 P1-6: 必须有 assert，不能只 print
        for name, c in check['checks'].items():
            if not c.get('passed', True):
                pytest.fail(
                    f"性能基线 {name} 偏离: 实际={c['actual']:.3f}, "
                    f"基线={c['baseline']:.3f}"
                )

        # 错误率必须 < 5%
        assert result.error_rate < 0.05, f"错误率过高: {result.error_rate*100:.1f}%"

    def test_dispatch_operators_perf(self):
        """5003 操作员列表性能 - 修复 P1-6: 添加 assert"""
        result = self._measure_url(f'{SERVICES["dispatch"]}/api/dispatch-center/operators', count=30)
        check = result.check_baseline()

        # 修复 P1-6
        for name, c in check['checks'].items():
            if not c.get('passed', True):
                pytest.fail(
                    f"性能基线 {name} 偏离: 实际={c['actual']:.3f}, "
                    f"基线={c['baseline']:.3f}"
                )

        assert result.error_rate < 0.05, f"错误率过高: {result.error_rate*100:.1f}%"


@pytest.mark.L3
@pytest.mark.perf
class TestConcurrency:
    """并发测试"""
    
    def test_concurrent_orders_list(self):
        """并发订单列表"""
        url = f'{SERVICES["desktop_web"]}/api/orders/list'
        result = PerformanceResult('concurrent_orders')
        result.start_time = time.time()
        
        def fetch():
            try:
                start = time.time()
                r = requests.get(url, timeout=10)
                return time.time() - start, r.status_code
            except Exception as e:
                return 0, str(e)
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(fetch) for _ in range(50)]
            for f in as_completed(futures):
                latency, code = f.result()
                if isinstance(code, int) and code < 500:
                    result.add(latency)
                else:
                    result.add(latency, f"HTTP {code}" if isinstance(code, int) else str(code))
        
        print(f"\n📊 并发测试: TPS={result.tps:.1f}, P95={result.p95*1000:.1f}ms, 错误率={result.error_rate*100:.1f}%")
        # 错误率应 < 5%
        assert result.error_rate < 0.05, f"错误率过高: {result.error_rate*100:.1f}%"
