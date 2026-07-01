import pytest

def test_mock_db_fixture_exists(mock_db):
    assert 'conn' in mock_db
    assert 'cursor' in mock_db

def test_mock_db_cursor_context(mock_db):
    with mock_db['conn'].cursor() as cur:
        assert cur is mock_db['cursor']

def test_mock_db_fetchone(mock_db):
    mock_db['cursor'].fetchone.return_value = {'id': 1, 'name': 'test'}
    result = mock_db['cursor'].fetchone()
    assert result == {'id': 1, 'name': 'test'}

def test_mock_db_fetchall(mock_db):
    mock_db['cursor'].fetchall.return_value = [{'id': 1}, {'id': 2}]
    result = mock_db['cursor'].fetchall()
    assert len(result) == 2

def test_mock_db_execute(mock_db):
    mock_db['cursor'].execute.return_value = None
    result = mock_db['cursor'].execute('SELECT 1')
    assert result is None
