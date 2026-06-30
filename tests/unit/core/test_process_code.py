# -*- coding: utf-8 -*-
"""核心 unit tests: get_process_code + PROCESS_CODES 完整性和正确性"""

import hashlib
import pytest
from core.config import get_process_code, PROCESS_CODES


class TestProcessCodesIntegrity:
    """PROCESS_CODES 字典完整性"""

    def test_count_exactly_19(self):
        """必须恰好 19 个编码（P01-P16 + M01 + Q01 + X01）"""
        assert len(PROCESS_CODES) == 19

    def test_all_keys_are_strings(self):
        for k in PROCESS_CODES:
            assert isinstance(k, str)

    def test_all_values_valid_format(self):
        """所有编码必须是 P01-P16 / M01 / Q01 / X01 格式"""
        valid_prefixes = {'P', 'M', 'Q', 'X'}
        for v in PROCESS_CODES.values():
            assert v[:1] in valid_prefixes, f'{v} 前缀不在合法范围'
            num = int(v[1:])
            assert 1 <= num <= 16

    def test_no_duplicate_values(self):
        """编码不能重复"""
        codes = list(PROCESS_CODES.values())
        assert len(codes) == len(set(codes))

    def test_full_range_all_codes(self):
        codes = set(PROCESS_CODES.values())
        expected = ({f'P{i:02d}' for i in range(1, 17)} |
                    {'M01', 'Q01', 'X01'})
        assert codes == expected

    def test_all_standard_names_present(self, sample_process_codes):
        expected_p = [
            '原材料准备', '焊接眼镜网', '激光切板', '链板冲压孔',
            '链板冲压成型', '编制左旋', '编制右旋', '穿曲轴',
            '输送带组装穿杆', '安装链条', '安装裙边', '整形校直',
            '焊接输送带', '表面处理', '质量检验', '包装入库'
        ]
        # P01-P16 全部存在
        for name in expected_p:
            assert name in sample_process_codes, f'{name} missing'

        # M01/Q01/X01 存在
        assert '备料' in sample_process_codes
        assert '质检' in sample_process_codes
        assert '外协' in sample_process_codes


class TestGetProcessCodeStandard:
    """get_process_code 标准工序"""

    @pytest.mark.parametrize("name,expected", [
        ('原材料准备', 'P01'),
        ('焊接眼镜网', 'P02'),
        ('激光切板', 'P03'),
        ('链板冲压孔', 'P04'),
        ('链板冲压成型', 'P05'),
        ('编制左旋', 'P06'),
        ('编制右旋', 'P07'),
        ('穿曲轴', 'P08'),
        ('输送带组装穿杆', 'P09'),
        ('安装链条', 'P10'),
        ('安装裙边', 'P11'),
        ('整形校直', 'P12'),
        ('焊接输送带', 'P13'),
        ('表面处理', 'P14'),
        ('质量检验', 'P15'),
        ('包装入库', 'P16'),
    ])
    def test_standard_process_returns_correct_code(self, name, expected):
        assert get_process_code(name) == expected


class TestGetProcessCodeEdgeCases:
    """get_process_code 边界条件"""

    def test_empty_string_returns_empty(self):
        assert get_process_code('') == ''

    def test_none_returns_empty(self):
        assert get_process_code(None) == ''

    def test_whitespace_generates_hash(self):
        """纯空格也是一个有效字符串，会生成 PX 编码"""
        result = get_process_code(' ')
        assert result.startswith('PX')
        assert len(result) == 6

    def test_non_standard_returns_px_format(self):
        result = get_process_code('打磨')
        assert result.startswith('PX')
        assert len(result) == 6

    def test_non_standard_is_deterministic(self):
        """同一个非标名称多次调用返回相同值"""
        result1 = get_process_code('抛光处理')
        result2 = get_process_code('抛光处理')
        assert result1 == result2

    def test_non_standard_different_names_different_codes(self):
        code1 = get_process_code('打磨')
        code2 = get_process_code('抛光处理')
        assert code1 != code2

    def test_long_process_name_does_not_crash(self):
        """长名称不应崩溃"""
        long_name = '这是一个非常长的工序名称' * 10
        result = get_process_code(long_name)
        assert result.startswith('PX')
        assert len(result) == 6

    def test_unicode_process_name(self):
        """Unicode 工序名称"""
        result = get_process_code('热处理🔥')
        assert result.startswith('PX')
        assert len(result) == 6

    def test_garbage_data(self):
        """乱码数据"""
        result = get_process_code('工单发布, role: 计划部, status_key: published')
        assert result.startswith('PX')
        assert len(result) == 6

    def test_pure_english_name(self):
        result = get_process_code('Welding')
        assert result.startswith('PX')
        assert len(result) == 6


class TestGetProcessCodeDeterminism:
    """PX 编码确定性测试"""

    def test_same_name_same_result_no_matter_process(self):
        """并发场景检验：多次调用结果相同"""
        results = [get_process_code('打磨') for _ in range(100)]
        assert len(set(results)) == 1

    def test_px_format_is_always_uppercase(self):
        result = get_process_code('打磨')
        assert result == result.upper()

    def test_px_code_is_unique_for_each_standard(self):
        """每个标准工序的编码唯一"""
        codes = [get_process_code(name) for name in PROCESS_CODES]
        assert len(codes) == len(set(codes)) == 19


class TestProcessCodeCompatibility:
    """与 MySQL / SQLite 兼容性"""

    def test_code_fits_in_varchar_10(self):
        """所有可能编码不超过 VARCHAR(10)"""
        codes = list(PROCESS_CODES.values())
        codes.append(get_process_code('打磨'))
        for c in codes:
            assert len(c) <= 10

    def test_code_is_ascii(self):
        """所有编码只包含 ASCII 字符"""
        codes = list(PROCESS_CODES.values())
        codes.append(get_process_code('打磨'))
        for c in codes:
            assert c.isascii()

    def test_no_special_sql_chars(self):
        """不包含 SQL 特殊字符"""
        codes = list(PROCESS_CODES.values())
        codes.append(get_process_code('打磨'))
        for c in codes:
            assert "'" not in c
            assert '"' not in c
            assert ';' not in c
            assert '--' not in c


class TestHashCorrectness:
    """验证 PX 编码的 hash 计算正确性"""

    def test_known_hash(self):
        """已知 hash 值验证：mxhash('打磨') hexdigest[:4].upper()"""
        expected = 'PX' + hashlib.md5('打磨'.encode()).hexdigest()[:4].upper()
        assert get_process_code('打磨') == expected

    def test_hash_consistent_with_md5_spec(self):
        """确保使用的是 MD5 而不是其他算法"""
        import hashlib
        for i, name in enumerate(list(PROCESS_CODES.keys())[:5]):
            # 标准工序不用 hash，用 P01-P16，所以不验证
            pass
        # 非标用 MD5
        name = '编织'
        expected_md5_prefix = hashlib.md5(name.encode()).hexdigest()[:4].upper()
        assert get_process_code(name) == f'PX{expected_md5_prefix}'
