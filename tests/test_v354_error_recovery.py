"""v3.5.4 任务 11.6 D6 验证:错误恢复(D1 --no-header + D2 缓存 v1→v2 自动失效)

依据:
- TASK_v3.5.4.md 任务 11.6 验收标准
- DESIGN_v3.5.4.md 3.1 D1 + 3.2 D2 契约
"""
import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(r'D:\yuan\gbd3.0')
TOOL_PATH = PROJECT_ROOT / '.workbuddy' / 'tools' / 'regression_db.py'
CACHE_PATH = PROJECT_ROOT / '.workbuddy' / '.pytest_collect_cache.json'


@pytest.mark.v354
def test_v1_cache_auto_invalidated():
    """D2 缓存升级: v1 缓存自动失效 + 重建 v2"""
    import subprocess
    import sys

    if not CACHE_PATH.exists():
        pytest.skip('缓存文件不存在,无法测试升级')

    # 1. 备份当前 v2 缓存
    original = json.loads(CACHE_PATH.read_text(encoding='utf-8'))
    assert original.get('version') == 3, f'起始缓存应为 v2,实际: {original.get("version")}'

    # 2. 人工改写为 v1 模拟"老缓存"
    v1 = {k: v for k, v in original.items() if k != 'last_collect_time'}
    v1['version'] = 1
    CACHE_PATH.write_text(json.dumps(v1, ensure_ascii=False, indent=2), encoding='utf-8')

    # 3. 跑 import-tests: 应自动失效 v1 + 重建 v2
    p = subprocess.run(
        [sys.executable, str(TOOL_PATH), 'import-tests'],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert p.returncode == 0, f'import-tests 失败: {p.stderr}'

    # 4. 验证:缓存已升 v2
    rebuilt = json.loads(CACHE_PATH.read_text(encoding='utf-8'))
    assert rebuilt.get('version') == 3, f'缓存未升级,仍是: {rebuilt.get("version")}'
    assert 'last_collect_time' in rebuilt, f'v2 缓存缺 last_collect_time'
    print(f'D2 升级验证 OK: v1 → v2 自动失效 + 重建')


@pytest.mark.v354
def test_corrupted_cache_auto_deleted():
    """D2 缓存损坏保护: 损坏缓存自动删除 + 重建"""
    import subprocess
    import sys

    if not CACHE_PATH.exists():
        pytest.skip('缓存文件不存在')

    # 写损坏 JSON
    CACHE_PATH.write_text('{not valid json', encoding='utf-8')

    # 跑 import-tests: 损坏缓存应被自动删除
    p = subprocess.run(
        [sys.executable, str(TOOL_PATH), 'import-tests'],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert p.returncode == 0, f'import-tests 失败: {p.stderr}'

    # 验证:新缓存是有效 v2
    new = json.loads(CACHE_PATH.read_text(encoding='utf-8'))
    assert new.get('version') == 3, f'重建缓存不是 v2'
    print(f'D2 损坏保护验证 OK: 损坏缓存被自动删除并重建')


@pytest.mark.v354
def test_pytest_api_subprocess_args():
    """D1 --no-header 防御: 验证子进程参数含 --no-header

    验证方式: 用 _collect_via_pytest_api 跑一次,看是否正常返回 items
    (无法直接验证参数,但若 conftest 提示混入,会因 :: 启发式被过滤掉,
    最终 items 数量应与 collect-only 输出一致)
    """
    import subprocess
    import sys

    # 跑 import-tests: D1 --no-header 已嵌入 subprocess.run
    p = subprocess.run(
        [sys.executable, str(TOOL_PATH), 'import-tests'],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert p.returncode == 0, f'import-tests 失败: {p.stderr}'
    assert '入库' in p.stdout, f'缺入库消息: {p.stdout}'

    # 验证:items 数量 > 2000 (证明未大量被启发式误过滤)
    import re
    m = re.search(r'入库 (\d+) 个', p.stdout)
    assert m, f'未找到入库数字: {p.stdout}'
    count = int(m.group(1))
    assert count > 2000, f'入库数过少({count}),可能 D1 解析失败误过滤'
    print(f'D1 验证 OK: 入库 {count} 个用例,无 conftest 误过滤')
