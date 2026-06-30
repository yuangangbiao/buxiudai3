# -*- coding: utf-8 -*-
"""
register_process DB 持久化测试（T4 边界用例矩阵）

边界矩阵：
| 类别 | 输入 | 期望 |
|------|------|------|
| 正常注册 | 焊接/PWELD/process | DB 有记录 + 内存有映射 |
| 重复注册 | 再调用一次相同 name | 返回已有 code，不插新行 |
| 表不存在 | process_code_registry DROP | 静默降级，仅写内存 |
| 空 name | register_process('') | 抛 ValueError |
| None code 自动分配 | register_process('折弯') | 自动分配 P17 |
| unregister 后重新注册 | unregister → 再 register | 新 code 递增 |
"""
import sys
import os
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.config import (
    register_process, unregister_process,
    get_process_code, is_registered,
    reset_custom_processes,
)


@pytest.fixture(autouse=True)
def clean_custom():
    reset_custom_processes()
    yield
    reset_custom_processes()


MOCK_DB = 'pymysql.connect'


class TestPersistNormal:

    def test_register_with_category_persists_to_db(self):
        with patch(MOCK_DB) as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            mock_conn.return_value.commit.return_value = None
            mock_conn.return_value.close.return_value = None

            code = register_process('焊接', 'PWELD', category='process')

            assert code == 'PWELD'
            assert is_registered('焊接')
            assert get_process_code('焊接') == 'PWELD'
            mock_cursor.execute.assert_called_once()
            call_args = mock_cursor.execute.call_args
            assert 'INSERT INTO process_code_registry' in call_args[0][0]
            assert ('焊接', 'PWELD', 'process') == call_args[0][1]


class TestPersistIdempotent:

    def test_duplicate_register_returns_existing_no_new_insert(self):
        with patch(MOCK_DB) as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.cursor.return_value = mock_cursor

            code1 = register_process('打磨', 'PWELD')
            code2 = register_process('打磨', 'PWELD')

            assert code1 == 'PWELD'
            assert code2 == 'PWELD'
            assert mock_cursor.execute.call_count == 1


class TestPersistSilentDegradation:

    def test_table_not_exists_silent_degradation(self):
        import pymysql
        with patch(MOCK_DB) as mock_conn:
            mock_conn.side_effect = pymysql.err.OperationalError(
                1146, "Table 'process_code_registry' doesn't exist")

            code = register_process('热处理', 'PHEAT')

            assert code == 'PHEAT'
            assert is_registered('热处理')
            assert get_process_code('热处理') == 'PHEAT'

    def test_other_db_error_silent_degradation(self):
        import pymysql
        with patch(MOCK_DB) as mock_conn:
            mock_conn.side_effect = pymysql.err.OperationalError(
                1045, "Access denied")

            code = register_process('喷涂', 'PSPRAY')

            assert code == 'PSPRAY'
            assert is_registered('喷涂')


class TestPersistInputValidation:

    def test_empty_name_raises_valueerror(self):
        with pytest.raises(ValueError, match='process_name 不能为空'):
            register_process('')

    def test_whitespace_only_raises_valueerror(self):
        with pytest.raises(ValueError):
            register_process('   ')

    def test_none_code_auto_allocates_p17(self):
        with patch(MOCK_DB) as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.cursor.return_value = mock_cursor

            code = register_process('折弯')

            assert code == 'P17'
            assert get_process_code('折弯') == 'P17'


class TestPersistUnregisterReRegister:

    def test_unregister_then_reregister_new_code(self):
        with patch(MOCK_DB) as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            mock_conn.return_value.commit.return_value = None

            code1 = register_process('电泳')
            assert code1 == 'P17'

            ok = unregister_process('电泳')
            assert ok is True
            assert not is_registered('电泳')

            code2 = register_process('电泳')
            assert code2 == 'P18'

    def test_unregister_with_category(self):
        with patch(MOCK_DB) as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            mock_conn.return_value.commit.return_value = None

            code = register_process('钝化', category='process')
            assert code == 'P17'

            ok = unregister_process('钝化')
            assert ok is True
            assert not is_registered('钝化')


class TestPersistUnregisterDbDelete:

    def test_unregister_deletes_from_db(self):
        with patch(MOCK_DB) as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            mock_conn.return_value.commit.return_value = None

            register_process('清洗', 'PCLEAN')
            unregister_process('清洗')

            call_args_list = mock_cursor.execute.call_args_list
            delete_calls = [c for c in call_args_list if 'DELETE' in str(c)]
            assert len(delete_calls) == 1
            assert ('清洗',) == delete_calls[0][0][1]

    def test_unregister_table_not_exists_silent_degradation(self):
        import pymysql
        with patch(MOCK_DB) as mock_conn:
            mock_conn.side_effect = pymysql.err.OperationalError(
                1146, "Table 'process_code_registry' doesn't exist")

            register_process('组装')
            ok = unregister_process('组装')

            assert ok is True
            assert not is_registered('组装')
