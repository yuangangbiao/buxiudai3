# -*- coding: utf-8 -*-
"""后期工序注册机制 — 完整测试套件"""

import sys, os

import pytest
from core.config import (
    register_process, unregister_process,
    get_all_processes, get_all_process_codes,
    get_process_code, is_registered,
    reset_custom_processes, load_custom_processes_from_db,
    PROCESS_CODES, PROCESSES
)


@pytest.fixture(autouse=True)
def clean_custom():
    reset_custom_processes()
    yield
    reset_custom_processes()


# ============================================================
class TestRegisterProcess:

    def test_register_auto_code(self):
        assert register_process('阳极氧化') == 'P17'
        assert is_registered('阳极氧化')

    def test_register_with_explicit_code(self):
        assert register_process('电镀', 'PXELEC') == 'PXELEC'
        assert get_process_code('电镀') == 'PXELEC'

    def test_register_multiple_auto_increment(self):
        assert register_process('A') == 'P17'
        assert register_process('B') == 'P18'
        assert register_process('C') == 'P19'

    def test_register_duplicate_returns_existing(self):
        register_process('打磨')
        assert register_process('打磨') == 'P17'

    def test_register_standard_returns_pcode(self):
        assert register_process('原材料准备') == 'P01'

    def test_register_strips_whitespace(self):
        assert register_process('  喷砂  ') == 'P17'
        assert get_process_code('喷砂') == 'P17'

    def test_register_empty_raises(self):
        with pytest.raises(ValueError):
            register_process('')

    def test_register_none_raises(self):
        with pytest.raises(ValueError):
            register_process(None)

    def test_register_whitespace_only_raises(self):
        with pytest.raises(ValueError):
            register_process('   ')


# ============================================================
class TestUnregisterProcess:

    def test_unregister_custom_succeeds(self):
        register_process('测试工序')
        assert unregister_process('测试工序') is True

    def test_unregister_standard_fails(self):
        assert unregister_process('原材料准备') is False

    def test_unregister_nonexistent_fails(self):
        assert unregister_process('不存在的工序') is False

    def test_unregister_then_re_register_new_code(self):
        register_process('X')  # P17
        unregister_process('X')
        assert register_process('X') == 'P18'

    def test_unregistered_not_in_lists(self):
        register_process('待删除')
        unregister_process('待删除')
        assert '待删除' not in get_all_processes()


# ============================================================
class TestGetAllProcesses:

    def test_initial_16_standard(self):
        assert len(get_all_processes()) == 17  # 16标准+P_CS

    def test_after_register_increases(self):
        register_process('新工序')
        assert len(get_all_processes()) == 18  # 16标准+P_CS+1新工序

    def test_get_all_codes_includes_custom(self):
        register_process('电镀', 'PXELEC')
        codes = get_all_process_codes()
        assert codes['电镀'] == 'PXELEC'
        assert codes['原材料准备'] == 'P01'


# ============================================================
class TestIsRegistered:

    def test_standard(self):
        assert is_registered('原材料准备')

    def test_custom(self):
        register_process('阳极氧化')
        assert is_registered('阳极氧化')

    def test_unknown(self):
        assert not is_registered('不存在')
        assert not is_registered('')
        assert not is_registered(None)


# ============================================================
class TestProcessCodeAfterRegister:

    def test_registered_uses_registered_code(self):
        # B0 v4: P/M/Q/X 前缀符合 R12 计划 T5-3
        register_process('定制', 'P01CUSTOM')
        assert get_process_code('定制') == 'P01CUSTOM'

    def test_unregistered_still_px_hash(self):
        code = get_process_code('未注册')
        assert code.startswith('PX')

    def test_register_then_unregister_back_to_px(self):
        # B0 v4: P01 前缀符合 R12 计划 T5-3
        register_process('临时', 'P01TEMP')
        assert get_process_code('临时') == 'P01TEMP'
        unregister_process('临时')
        assert get_process_code('临时').startswith('PX')


# ============================================================
class TestCustomProcessEdgeCases:

    def test_max_auto_code_no_overflow(self):
        for i in range(100):
            register_process(f'工序_{i}')
        assert len(get_all_processes()) >= 116  # 16标准+100自定义

    def test_special_chars_in_name(self):
        assert register_process('热处理(高温)') == 'P17'

    def test_very_long_name(self):
        # B0 v4: P01LONG 前缀符合 R12 计划 T5-3, 长度 7 <= 10
        assert len(register_process('A' * 200, 'P01LONG')) <= 10

    def test_reset_clears_all(self):
        register_process('A')
        register_process('B')
        reset_custom_processes()
        assert len(get_all_processes()) == 17  # 16标准+P_CS
        assert not is_registered('A')

    def test_register_preserves_standards(self):
        register_process('自定义')
        for name in PROCESSES:
            assert is_registered(name)


# ============================================================
class TestCustomProcessEndToEnd:

    def test_register_in_all_processes(self):
        register_process('喷砂处理')
        assert '喷砂处理' in get_all_processes()
        assert '原材料准备' in get_all_processes()
        assert len(get_all_processes()) == 18  # 16标准+P_CS+1自定义

    def test_full_flow(self):
        code = register_process('激光刻字')
        assert code == 'P17'
        assert get_process_code('激光刻字') == 'P17'

        content = {
            'order_no': 'GO-001',
            'process_name': '激光刻字',
            'process_code': get_process_code('激光刻字'),
            'completed_qty': 10,
            'status': '进行中',
            'quantity': 100
        }
        assert content['process_code'] == 'P17'
        assert content['order_no'] == 'GO-001'
