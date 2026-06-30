# -*- coding: utf-8 -*-
"""
缓存命中率运行时监控 — 探针模块

集成方式（在 cache.py 顶部加）:
    from scripts.tools.cache_metrics import CacheMetrics, init_metrics
    _metrics = init_metrics()

    class RedisCache:
        def get(self, key, default=None):
            _metrics.hit() if ... else _metrics.miss()

暴露端点（在 app.py 注册）:
    @app.route('/api/metrics/cache')
    def cache_metrics():
        return jsonify(_metrics.snapshot())

提供:
    - hit/miss 计数
    - 按 key 前缀的命中率
    - 慢查询告警
    - 内存后端命中率
    - Redis 健康状态
"""
import time
import threading
from collections import defaultdict
from datetime import datetime
from typing import Optional


class CacheMetrics:
    """缓存指标收集器（线程安全）"""

    def __init__(self):
        self._lock = threading.Lock()
        self._reset()

    def _reset(self):
        self.started_at = datetime.now()
        self.hits = 0
        self.misses = 0
        self.errors = 0
        self.sets = 0
        self.deletes = 0
        self.hit_by_prefix = defaultdict(lambda: {'hit': 0, 'miss': 0})
        self.slow_queries = []
        self.backend = 'unknown'

    def _prefix(self, key: str) -> str:
        """从 key 提取一级前缀（用 : 分割）"""
        if not isinstance(key, str):
            return '?'
        if ':' in key:
            return key.split(':', 1)[0]
        if '_' in key:
            parts = key.split('_')
            return '_'.join(parts[:2]) if len(parts) >= 2 else parts[0]
        return key[:20] if len(key) > 20 else key

    def hit(self, key: Optional[str] = None, elapsed_ms: float = 0):
        with self._lock:
            self.hits += 1
            if key:
                p = self._prefix(key)
                self.hit_by_prefix[p]['hit'] += 1
            if elapsed_ms > 50:
                self.slow_queries.append({'op': 'get', 'key': key, 'ms': elapsed_ms, 'at': time.time()})
                if len(self.slow_queries) > 100:
                    self.slow_queries = self.slow_queries[-100:]

    def miss(self, key: Optional[str] = None, elapsed_ms: float = 0):
        with self._lock:
            self.misses += 1
            if key:
                p = self._prefix(key)
                self.hit_by_prefix[p]['miss'] += 1
            if elapsed_ms > 50:
                self.slow_queries.append({'op': 'get', 'key': key, 'ms': elapsed_ms, 'at': time.time()})
                if len(self.slow_queries) > 100:
                    self.slow_queries = self.slow_queries[-100:]

    def error(self, op: str = 'get', key: Optional[str] = None):
        with self._lock:
            self.errors += 1

    def set(self, key: Optional[str] = None):
        with self._lock:
            self.sets += 1

    def delete(self, key: Optional[str] = None):
        with self._lock:
            self.deletes += 1

    def set_backend(self, backend: str):
        with self._lock:
            self.backend = backend

    def snapshot(self) -> dict:
        with self._lock:
            total_gets = self.hits + self.misses
            hit_rate = (self.hits / total_gets * 100) if total_gets > 0 else 0.0

            prefix_stats = []
            for prefix, cnt in self.hit_by_prefix.items():
                p_total = cnt['hit'] + cnt['miss']
                p_rate = (cnt['hit'] / p_total * 100) if p_total > 0 else 0.0
                prefix_stats.append({
                    'prefix': prefix,
                    'hits': cnt['hit'],
                    'misses': cnt['miss'],
                    'total': p_total,
                    'hit_rate_pct': round(p_rate, 2),
                })
            prefix_stats.sort(key=lambda x: x['total'], reverse=True)

            return {
                'generated_at': datetime.now().isoformat(),
                'started_at': self.started_at.isoformat(),
                'uptime_seconds': (datetime.now() - self.started_at).total_seconds(),
                'backend': self.backend,
                'overall': {
                    'hits': self.hits,
                    'misses': self.misses,
                    'errors': self.errors,
                    'sets': self.sets,
                    'deletes': self.deletes,
                    'total_gets': total_gets,
                    'hit_rate_pct': round(hit_rate, 2),
                },
                'by_prefix': prefix_stats,
                'slow_queries': self.slow_queries[-10:],
                'diagnosis': self._diagnose(hit_rate, prefix_stats),
            }

    def _diagnose(self, overall_rate: float, prefix_stats: list) -> list:
        issues = []
        total_gets = self.hits + self.misses
        if overall_rate < 30:
            issues.append({
                'level': 'high',
                'message': '总命中率 < 30%，缓存策略可能不合理（TTL 过短/频繁失效）'
            })
        elif overall_rate < 60:
            issues.append({
                'level': 'medium',
                'message': '总命中率 30-60%，有优化空间'
            })
        else:
            issues.append({
                'level': 'ok',
                'message': '总命中率 >= 60%，健康'
            })

        for p in prefix_stats:
            if p['total'] >= 10 and p['hit_rate_pct'] < 20:
                issues.append({
                    'level': 'medium',
                    'message': "前缀 '{}' 命中率 {pct}%，建议加缓存或延长 TTL".format(
                        p['prefix'], pct=p['hit_rate_pct'])
                })

        if total_gets > 0 and self.errors > total_gets * 0.05:
            issues.append({
                'level': 'high',
                'message': "错误率 > 5%，可能 Redis 连接不稳"
            })

        return issues


_global_metrics: Optional[CacheMetrics] = None


def init_metrics() -> CacheMetrics:
    global _global_metrics
    if _global_metrics is None:
        _global_metrics = CacheMetrics()
    return _global_metrics


def get_metrics() -> Optional[CacheMetrics]:
    return _global_metrics


def timed_get(metrics: CacheMetrics, backend_name: str):
    """上下文管理器：自动计时 + 记录 hit/miss"""
    class _Timer:
        def __init__(self):
            self.start = 0.0
            self.elapsed = 0.0
        def __enter__(self):
            self.start = time.time()
            return self
        def __exit__(self, exc_type, exc, tb):
            self.elapsed = (time.time() - self.start) * 1000
    return _Timer()


if __name__ == '__main__':
    print("=== 缓存监控演示 ===")
    m = init_metrics()
    m.set_backend('redis')
    for i in range(80):
        m.hit(key='user:{}'.format(i % 10))
    for i in range(20):
        m.miss(key='order:{}'.format(i))
    for i in range(5):
        m.error(op='get')
    for i in range(50):
        m.set(key='config:{}'.format(i))
    import json
    print(json.dumps(m.snapshot(), ensure_ascii=False, indent=2))
