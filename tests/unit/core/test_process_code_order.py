# -*- coding: utf-8 -*-
"""工序自定义排列排序 — 完整测试套件 (标准工序也支持移动)"""

import sys, os

import pytest
from core.config import (
    register_process, unregister_process,
    get_all_processes, get_process_seq,
    reorder_processes, move_process,
    reset_custom_processes,
    PROCESSES
)


@pytest.fixture(autouse=True)
def clean():
    reset_custom_processes()
    yield
    reset_custom_processes()


class TestDisplaySeq:
    def test_default_seq_auto(self):
        register_process('A')
        register_process('B')
        assert get_process_seq('A') == 17
        assert get_process_seq('B') == 18

    def test_explicit_seq(self):
        register_process('C', display_seq=5)
        register_process('D', display_seq=3)
        assert get_process_seq('C') == 5
        assert get_process_seq('D') == 3

    def test_standard_seq_fixed(self):
        assert get_process_seq('原材料准备') == 1
        assert get_process_seq('包装入库') == 16

    def test_unknown_seq(self):
        assert get_process_seq('不存在') == 999


class TestGetAllProcessesSorted:
    def test_default_sort_by_seq(self):
        register_process('后道工序', display_seq=50)
        register_process('前道工序', display_seq=3)
        ordered = get_all_processes(sort=True)
        assert ordered[0] == '原材料准备'
        assert ordered[1] == '焊接眼镜网'

    def test_no_sort_standards_first(self):
        register_process('A')
        unordered = get_all_processes(sort=False)
        assert unordered[:16] == list(PROCESSES)[:-1]  # 前16个标准
        assert unordered[16:] == ['测试', 'A']  # 测试(P_CS)+1自定义

    def test_total_count(self):
        register_process('A')
        register_process('B')
        assert len(get_all_processes()) == 19  # 16标准+测试(P_CS)+2自定义


class TestReorderProcesses:
    def test_reorder_custom_only(self):
        register_process('A')
        register_process('B')
        reorder_processes(['B', 'A'])
        ordered = get_all_processes(sort=True)
        customs = [n for n in ordered if n not in PROCESSES]
        assert customs == ['B', 'A']

    def test_reorder_includes_standards(self):
        """reorder_processes 可以重排所有工序"""
        register_process('X')
        reorder_processes(['X', '包装入库', '原材料准备'])
        ordered = get_all_processes(sort=True)
        assert ordered[0] == 'X'
        assert ordered[1] == '包装入库'
        assert ordered[2] == '原材料准备'

    def test_missing_in_order_goes_last(self):
        register_process('A')
        register_process('B')
        reorder_processes(['A'])
        assert get_process_seq('B') == 999


class TestMoveProcess:
    def test_move_down(self):
        register_process('A')
        register_process('B')
        move_process('A', 'down')
        ordered = get_all_processes(sort=True)
        customs = [n for n in ordered if n not in PROCESSES]
        assert customs[0] == 'B'

    def test_move_up(self):
        register_process('A')
        register_process('B')
        move_process('B', 'up')
        ordered = get_all_processes(sort=True)
        customs = [n for n in ordered if n not in PROCESSES]
        assert customs[0] == 'B'

    def test_move_top(self):
        register_process('A')
        register_process('B')
        move_process('B', 'top')
        ordered = get_all_processes(sort=True)
        customs = [n for n in ordered if n not in PROCESSES]
        assert customs[0] == 'B'

    def test_move_bottom(self):
        register_process('A')
        register_process('B')
        move_process('A', 'bottom')
        ordered = get_all_processes(sort=True)
        customs = [n for n in ordered if n not in PROCESSES]
        assert customs[-1] == 'A'

    def test_move_at_edge_does_not_crash(self):
        register_process('A')
        move_process('A', 'up')
        assert get_process_seq('A') > 0

    def test_move_unknown_returns_minus_one(self):
        assert move_process('不存在', 'up') == -1

    def test_move_standard_works(self):
        """标准工序也可移动"""
        old_seq = get_process_seq('编制左旋')
        move_process('编制左旋', 'down')
        assert get_process_seq('编制左旋') != old_seq

    def test_move_standard_to_top(self):
        """标准工序置顶 — 被置换的原材料准备被推到后面"""
        move_process('包装入库', 'top')
        ordered = get_all_processes(sort=True)
        assert ordered[0] == '包装入库'
        # 原材料准备被交换到seq=16,排在P_CS(seq=999)之后的标准首位
        # 但'测试'(P_CS)也是PROCESSES成员,所以取倒数第2个标准
        last_std = [n for n in ordered if n in PROCESSES]
        assert last_std[-2] == '原材料准备'  # 倒数第2个(最后是'测试')

    def test_standard_can_be_reordered(self):
        """reorder_processes 可重排标准工序"""
        reorder_processes(['包装入库', '质量检验', '表面处理'])
        ordered = get_all_processes(sort=True)
        assert ordered[0] == '包装入库'

    def test_other_standards_keep_default_after_move(self):
        """移动一个标准工序后，其余未被波及的保持默认顺序"""
        move_process('包装入库', 'top')
        ordered = get_all_processes(sort=True)
        assert ordered[0] == '包装入库'
        # 其余未被交换的标准工序仍保持默认顺序
        rest = [n for n in ordered if n != '包装入库' and n in PROCESSES]
        # 原材料准备被交换到后面，其余保持顺序
        assert rest[0] == '焊接眼镜网'  # seq=2


class TestEndToEndOrdering:
    def test_full_ordering_flow(self):
        register_process('超声波清洗', display_seq=17)
        register_process('激光打标', display_seq=18)
        ordered = get_all_processes(sort=True)
        assert ordered[16] == '超声波清洗'
        assert ordered[17] == '激光打标'
        assert len(ordered) == 19  # 16标准+测试(P_CS)+2自定义

    def test_insert_between_standards(self):
        register_process('AAA前置', display_seq=0)
        register_process('ZZZ后置', display_seq=999)
        ordered = get_all_processes(sort=True)
        assert ordered[0] == 'AAA前置'
        assert ordered[-1] == '测试'

    def test_register_without_seq_goes_end(self):
        register_process('A')
        register_process('B')
        ordered = get_all_processes(sort=True)
        assert 'A' in ordered  # 第一个新工序
        assert 'B' in ordered   # 第二个新工序
        assert ordered[-1] == '测试'  # P_CS seq=999排末尾
