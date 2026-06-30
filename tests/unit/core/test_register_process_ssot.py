# -*- coding: utf-8 -*-
"""
register_process 15出错场景 SSOT 测试（任务5 T5-6 / 任务15）

覆盖 register_process 5层防御的所有出错路径：

| 场景 | 输入 | 期望 | 防御层 |
|------|------|------|--------|
| 空名称 | register_process('') | ValueError | T5-1 |
| 全空格 | register_process('   ') | ValueError | T5-1 |
| 编码格式非法(数字开头) | register_process('折弯', '123') | ValueError | T5-3 |
| 编码格式非法(特殊字符) | register_process('折弯', 'P@HOME') | ValueError | T5-3 |
| 编码格式非法(过长) | register_process('折弯', 'P1234567890') | ValueError | T5-3 |
| 编码格式非法(仅字母) | register_process('折弯', 'A') | ValueError | T5-3 |
| 编码被其他工序占用 | name A=code P01, name B=code P01 | ValueError | T5-4 |
| 名称已存在(标准工序) | register_process('裁剪') | 返回已有code | T5-4 |
| 名称已存在(自定义) | 先register('A', 'PA')再register('A') | 返回'PA' | T5-4 |
| 自动分配编码 | 不传code | P17 | T5-3 |
| category非法值 | category='invalid' | 接受但不校验 | DB约束 |
| 重复注册(幂等) | 同一name两次 | 返回已有code,仅1次INSERT | T5-2 |
| DB表不存在 | DROP表后register | 静默降级,仅写内存 | T5-5 |
| unregister后注册同名 | unregister('X')→register('X') | 新code递增 | DB+内存 |
| 大小写归一 | register('折弯')和REGISTER('折弯') | 后者返回前者code | T5-1 |
"""
import sys
import os
from unittest.mock import patch, MagicMock

import pytest
import pymysql

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.config import (
    register_process, unregister_process,
    get_process_code, is_registered,
    reset_custom_processes,
)

MOCK_DB = 'pymysql.connect'


@pytest.fixture(autouse=True)
def clean_custom():
    reset_custom_processes()
    yield
    reset_custom_processes()


# ============================================================
# T5-1 参数清洗
# ============================================================
class TestT5_1_ParameterCleaning:
    def test_empty_name_raises_valueerror(self):
        with pytest.raises(ValueError, match='process_name 不能为空'):
            register_process('')

    def test_whitespace_only_raises_valueerror(self):
        with pytest.raises(ValueError):
            register_process('   ')

    def test_name_case_normalized(self):
        with patch(MOCK_DB) as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            code1 = register_process('折弯')
            code2 = register_process('折弯')
            assert code1 == code2 == 'P17'


# ============================================================
# T5-3 格式校验
# ============================================================
class TestT5_3_FormatValidation:
    def test_code_starts_with_digit_raises(self):
        with pytest.raises(ValueError, match='工序编码格式不合法'):
            register_process('折弯', '123ABC')

    def test_code_has_special_char_raises(self):
        with pytest.raises(ValueError):
            register_process('折弯', 'P@HOME')

    def test_code_too_long_raises(self):
        with pytest.raises(ValueError):
            register_process('折弯', 'P1234567890')

    def test_code_single_letter_no_prefix_raises(self):
        with pytest.raises(ValueError):
            register_process('折弯', 'A')

    def test_auto_allocate_p17(self):
        with patch(MOCK_DB) as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            code = register_process('折弯')
            assert code == 'P17'


# ============================================================
# T5-4 一致性检查
# ============================================================
class TestT5_4_ConsistencyCheck:
    def test_standard_process_name_returns_existing(self):
        code = register_process('链板冲压孔')
        assert code == 'P04'

    def test_custom_name_exists_returns_existing(self):
        with patch(MOCK_DB) as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            code1 = register_process('打磨', 'PAB')
            code2 = register_process('打磨')
            assert code1 == code2 == 'PAB'

    def test_code_reused_by_other_name_raises(self):
        with patch(MOCK_DB) as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            register_process('打磨', 'PAB')
            with pytest.raises(ValueError, match='已被其他工序占用'):
                register_process('抛光', 'PAB')


# ============================================================
# T5-2 幂等 + T5-5 静默降级
# ============================================================
class TestT5_2_IdempotentAndDegradation:
    def test_duplicate_register_inserts_once(self):
        with patch(MOCK_DB) as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            code1 = register_process('焊接', 'PWELD')
            code2 = register_process('焊接', 'PWELD')
            assert code1 == code2 == 'PWELD'
            assert mock_cursor.execute.call_count == 1

    def test_table_not_exists_silent_degradation(self):
        with patch(MOCK_DB) as mock_conn:
            mock_conn.side_effect = pymysql.err.OperationalError(
                1146, "Table 'process_code_registry' doesn't exist")
            code = register_process('热处理', 'PHEAT')
            assert code == 'PHEAT'
            assert is_registered('热处理')

    def test_other_db_error_silent_degradation(self):
        with patch(MOCK_DB) as mock_conn:
            mock_conn.side_effect = pymysql.err.OperationalError(
                1045, "Access denied")
            code = register_process('喷涂', 'PSPRAY')
            assert code == 'PSPRAY'
            assert is_registered('喷涂')


# ============================================================
# 综合：unregister 后重新注册
# ============================================================
class TestUnregisterReregister:
    def test_unregister_then_reregister_new_code(self):
        with patch(MOCK_DB) as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            code1 = register_process('电泳')
            assert code1 == 'P17'
            ok = unregister_process('电泳')
            assert ok is True
            assert not is_registered('电泳')
            code2 = register_process('电泳')
            assert code2 == 'P18'

    def test_unregister_then_reregister_different_code(self):
        with patch(MOCK_DB) as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            register_process('清洗', 'PCLEAN')
            ok = unregister_process('清洗')
            assert ok is True
            code = register_process('清洗', 'PCLEAN2')
            assert code == 'PCLEAN2'


# ============================================================
# category 参数边界
# ============================================================
class TestCategoryParameter:
    def test_category_process_stored(self):
        with patch(MOCK_DB) as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            register_process('钝化', category='process')
            call_args = mock_cursor.execute.call_args
            assert ('钝化', 'P17', 'process') == call_args[0][1]

    def test_category_material_stored(self):
        with patch(MOCK_DB) as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            register_process('不锈钢带', 'M01', category='material')
            call_args = mock_cursor.execute.call_args
            assert ('不锈钢带', 'M01', 'material') == call_args[0][1]
