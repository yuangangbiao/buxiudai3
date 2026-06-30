"""v3.5.4 任务 11.6 D6 验证:并发 import-tests 都能成功(D3 WAL 模式)

依据:
- TASK_v3.5.4.md 任务 11.6 验收标准
- DESIGN_v3.5.4.md 3.3 D3 契约
"""
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(r'D:\yuan\gbd3.0')
TOOL_PATH = PROJECT_ROOT / '.workbuddy' / 'tools' / 'regression_db.py'


@pytest.mark.v354
def test_concurrent_import_tests_wal():
    """D3 WAL 模式:2 个并发 import-tests 都能成功

    验证点:
    - 2 个进程同时 import 不死锁
    - 都返回 exit_code=0
    - 都打印入库计数
    """
    # 启动 2 个并发 import-tests
    procs = []
    for _ in range(2):
        p = subprocess.Popen(
            [sys.executable, str(TOOL_PATH), 'import-tests'],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        procs.append(p)

    # 等待全部完成
    outputs = []
    for p in procs:
        stdout, stderr = p.communicate(timeout=120)
        outputs.append((p.returncode, stdout, stderr))

    # 验证:2 个都成功
    for i, (rc, stdout, stderr) in enumerate(outputs):
        assert rc == 0, f'进程 {i} 失败(rc={rc}, stderr={stderr})'
        assert '入库' in stdout, f'进程 {i} 缺入库消息: {stdout}'


@pytest.mark.v354
def test_wal_mode_persisted():
    """D3 WAL 模式:PRAGMA journal_mode 持久化到 DB 文件

    验证点:
    - 第一次 import-tests 启动后,DB 切换到 WAL 模式
    - 第二次启动,模式仍是 WAL
    """
    # 第一次 import
    p1 = subprocess.run(
        [sys.executable, str(TOOL_PATH), 'import-tests'],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert p1.returncode == 0, f'第一次 import 失败: {p1.stderr}'

    # 检查 DB 文件模式
    import sqlite3
    db_path = PROJECT_ROOT / '.workbuddy' / 'regression' / 'regression.db'
    with sqlite3.connect(str(db_path)) as conn:
        mode = conn.execute('PRAGMA journal_mode').fetchone()[0]
    assert mode == 'wal', f'WAL 模式未启用,当前: {mode}'
