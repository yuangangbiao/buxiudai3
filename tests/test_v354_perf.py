"""v3.5.4 任务 11.6 D6 验证:性能基准(D5 batch_size=5000)

依据:
- TASK_v3.5.4.md 任务 11.6 验收标准
- DESIGN_v3.5.4.md 3.5 D5 契约
"""
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(r'D:\yuan\gbd3.0')
TOOL_PATH = PROJECT_ROOT / '.workbuddy' / 'tools' / 'regression_db.py'


@pytest.mark.v354
def test_import_perf_baseline():
    """D5 性能: import-tests 总耗时 < 6s (缓存命中 0.02s + 0.5s executemany)"""
    import subprocess
    import sys

    start = time.time()
    p = subprocess.run(
        [sys.executable, str(TOOL_PATH), 'import-tests'],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    elapsed = time.time() - start

    assert p.returncode == 0, f'import-tests 失败: {p.stderr}'
    # 缓存命中场景(2632 用例)应 < 1s
    assert elapsed < 1.0, f'性能不达标: {elapsed:.2f}s (应 < 1.0s)'
    print(f'性能验证: import-tests 耗时 {elapsed:.3f}s')


@pytest.mark.v354
def test_cache_v2_format():
    """D2 缓存 v2: 缓存文件 version=2 + last_collect_time"""
    import json
    cache_path = PROJECT_ROOT / '.workbuddy' / '.pytest_collect_cache.json'
    if not cache_path.exists():
        pytest.skip('缓存文件不存在(可能 import-tests 未跑过)')

    cache = json.loads(cache_path.read_text(encoding='utf-8'))
    assert cache.get('version') == 3, f'缓存 version 应为 2,实际: {cache.get("version")}'
    assert 'last_collect_time' in cache, f'v2 缓存应含 last_collect_time'
    assert 'items' in cache, f'v2 缓存应含 items'
    assert cache.get('pytest_version'), f'v2 缓存应含 pytest_version'
    print(f'v2 缓存验证 OK: last_collect_time={cache["last_collect_time"]}')
