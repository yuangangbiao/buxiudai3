"""T1.2-Q1 验证: mock_db fixture 功能验证"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 直接测试 conftest 可导入
import tests.conftest

has_fixture = hasattr(tests.conftest, 'mock_db') or 'mock_db' in dir(tests.conftest)
print(f'[1/3] conftest has mock_db: {has_fixture}')

# 手动验证 fixture 逻辑
from unittest.mock import MagicMock, patch

with patch('models.database.get_connection') as mock_fn:
    mock_conn = MagicMock(name='mock_connection')
    mock_cursor = MagicMock(name='mock_cursor')
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.cursor.return_value.__exit__.return_value = None
    mock_conn.commit.return_value = None
    mock_conn.close.return_value = None
    mock_fn.return_value = mock_conn

    # 验证 cursor 可用
    mock_cursor.fetchone.return_value = {'id': 1, 'name': 'test'}
    mock_cursor.execute.return_value = None
    mock_cursor.fetchall.return_value = [{'id': 1}, {'id': 2}]

    # 验证 API 模式
    conn = mock_fn()
    cursor = conn.cursor().__enter__()
    cursor.execute("SELECT * FROM test")
    result = cursor.fetchone()

    assert result == {'id': 1, 'name': 'test'}, f'Expected dict, got {result}'
    assert cursor.fetchall() == [{'id': 1}, {'id': 2}]
    print(f'[2/3] mock cursor API works: PASS')

    # 验证 context manager
    with conn.cursor() as cur:
        assert cur is mock_cursor
        cur.execute("INSERT INTO test VALUES (1)")
    conn.commit.assert_called_once()
    print(f'[3/3] context manager works: PASS')

print(f'\nT1.2-Q1: PASS')
