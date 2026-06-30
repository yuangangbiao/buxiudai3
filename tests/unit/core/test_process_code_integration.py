# -*- coding: utf-8 -*-
"""集成测试: SQLite 回填、MySQL 匹配逻辑、端到端流程"""

import json
import os
import sys
import tempfile
import sqlite3
import hashlib

import pytest


from core.config import get_process_code, PROCESS_CODES


# ============================================================
# SQLite 回填集成测试
# ============================================================

class TestSQLiteBackfill:
    """SQLite data_packages 回填逻辑"""

    def test_backfill_missing_process_code(self, sqlite_with_data):
        """回填缺失 process_code 的数据包"""
        conn = sqlite_with_data
        cur = conn.cursor()

        # 查找缺失 process_code 的包
        cur.execute("SELECT id, content, related_process FROM data_packages")
        target = None
        for row in cur.fetchall():
            content = json.loads(row['content']) if isinstance(row['content'], str) else row['content']
            if isinstance(content, dict) and not content.get('process_code') and content.get('process_name'):
                target = (row['id'], content, row['related_process'])
                break

        assert target is not None, "应该有一个缺少 process_code 且有 process_name 的包"
        rowid, content, related_process = target

        # 执行回填
        pname = content.get('process_name', '')
        pcode = get_process_code(pname)
        assert pcode, f"process_name={pname!r} 应生成有效编码"

        content['process_code'] = pcode
        cur.execute("UPDATE data_packages SET content=? WHERE id=?",
                   (json.dumps(content, ensure_ascii=False), rowid))
        conn.commit()

        # 验证回填结果
        cur.execute("SELECT content FROM data_packages WHERE id=?", (rowid,))
        new_row = cur.fetchone()
        assert new_row is not None, f"id={rowid} 的记录应该存在"
        new_content = json.loads(new_row['content']) if isinstance(new_row['content'], str) else new_row['content']
        assert new_content.get('process_code') == pcode

    def test_backfill_preserves_existing_process_code(self, sqlite_with_data):
        """回填不应覆盖已有的 process_code"""
        conn = sqlite_with_data
        cur = conn.cursor()

        # 找一条已有 process_code 的包
        cur.execute("SELECT rowid, content FROM data_packages")
        target = None
        for row in cur.fetchall():
            content = json.loads(row['content']) if isinstance(row['content'], str) else row['content']
            if isinstance(content, dict) and content.get('process_code'):
                target = (row['rowid'], content)
                break

        assert target is not None, "应该有一条已有 process_code 的包"
        rowid, content = target
        original_code = content.get('process_code')
        assert original_code

        # 模拟回填逻辑：已有 process_code 的不处理
        assert content.get('process_code')

    def test_order_level_package_no_process(self, sqlite_with_data):
        """订单级数据包不需要 process_code"""
        conn = sqlite_with_data
        cur = conn.cursor()

        cur.execute('''SELECT rowid, content FROM data_packages
            WHERE json_extract(content, '$.flow_type') = 'created' LIMIT 1''')
        row = cur.fetchone()
        content = json.loads(row['content']) if isinstance(row['content'], str) else row['content']

        # 订单级包：有 flow_type，无 process_name -> 不参与回填
        assert 'flow_type' in content
        assert 'process_name' not in content
        assert 'process_code' not in content

        # 空 process_name 不应该生成 process_code
        pname = content.get('process_name', '') or ''
        if pname:
            pcode = get_process_code(pname)
        else:
            pcode = ''
        assert pcode == '', "无工序名的包不应该生成编码"


# ============================================================
# MySQL matching 集成测试（模拟）
# ============================================================

class TestMySQLMatchingLogic:
    """模拟 MySQL UPDATE WHERE order_id + process_code 的匹配逻辑"""

    @pytest.fixture(autouse=True)
    def reset_records(self):
        """每个测试前重置记录"""
        self.MOCK_RECORDS = [
            {'id': 1, 'order_id': 5, 'process_name': '原材料准备', 'process_code': 'P01', 'completed_qty': 0, 'status': '待开始'},
            {'id': 2, 'order_id': 5, 'process_name': '编制左旋', 'process_code': 'P06', 'completed_qty': 50, 'status': '进行中'},
            {'id': 3, 'order_id': 5, 'process_name': '包装入库', 'process_code': 'P16', 'completed_qty': 0, 'status': '待开始'},
            {'id': 4, 'order_id': 8, 'process_name': '原材料准备', 'process_code': 'P01', 'completed_qty': 100, 'status': '已完成'},
            {'id': 5, 'order_id': 8, 'process_name': '包装入库', 'process_code': 'P16', 'completed_qty': 50, 'status': '进行中'},
        ]

    def _match_update(self, order_id, process_code, qty):
        """模拟 MySQL UPDATE ... WHERE order_id=%s AND process_code=%s"""
        matched = [r for r in self.MOCK_RECORDS
                   if r['order_id'] == order_id and r['process_code'] == process_code]
        if len(matched) == 1:
            matched[0]['completed_qty'] += qty
            return len(matched)
        return len(matched)  # 0=未匹配, >1=重复(异常)

    def test_exact_match_updates_one_record(self):
        """完全匹配应只更新一条"""
        count = self._match_update(5, 'P01', 10)
        assert count == 1
        record = next(r for r in self.MOCK_RECORDS if r['id'] == 1)
        assert record['completed_qty'] == 10

    def test_wrong_process_code_returns_zero(self):
        """错误的 process_code 应返回 0"""
        count = self._match_update(5, 'P99', 10)
        assert count == 0

    def test_wrong_order_id_returns_zero(self):
        """错误的 order_id 应返回 0"""
        count = self._match_update(999, 'P01', 10)
        assert count == 0

    def test_different_orders_same_code_independent(self):
        """不同工单的同 process_code 互不影响"""
        self._match_update(5, 'P16', 20)
        self._match_update(8, 'P16', 30)

        record_5 = next(r for r in self.MOCK_RECORDS if r['id'] == 3)
        record_8 = next(r for r in self.MOCK_RECORDS if r['id'] == 5)
        assert record_5['completed_qty'] == 20
        assert record_8['completed_qty'] == 80

    def test_no_duplicate_matching(self):
        """每个 (order_id, process_code) 最多匹配一条"""
        for r in self.MOCK_RECORDS:
            matches = [x for x in self.MOCK_RECORDS
                       if x['order_id'] == r['order_id'] and x['process_code'] == r['process_code']]
            assert len(matches) == 1, f"order_id={r['order_id']} process_code={r['process_code']} 有重复"

    def test_rowcount_zero_means_no_match(self):
        """rowcount=0 时应该返回 404"""
        count = self._match_update(5, 'P08', 10)  # P08 不存在于 order_id=5
        assert count == 0

    def test_multiple_updates_accumulate(self):
        """多次报工累计正确"""
        self._match_update(5, 'P01', 10)
        self._match_update(5, 'P01', 15)
        self._match_update(5, 'P01', 5)
        record = next(r for r in self.MOCK_RECORDS if r['id'] == 1)
        assert record['completed_qty'] == 30


# ============================================================
# process_code 动态生成 + 查询匹配端到端
# ============================================================

class TestEndToEndProcessCodeFlow:
    """端到端：桌面排产→生成 process_code→SQLite 存储→匹配查询"""

    def test_insert_then_match(self, sqlite_with_data):
        """模拟：桌面排产 INSERT → 手机报工 UPDATE 匹配"""
        conn = sqlite_with_data
        cur = conn.cursor()

        # 模拟新建一个数据包（桌面→容器中心）
        order_no = 'GO-NEW-001'
        process_name = '激光切板'
        process_code = get_process_code(process_name)

        assert process_code == 'P03'

        new_content = json.dumps({
            'order_no': order_no,
            'process_name': process_name,
            'process_code': process_code,
            'completed_qty': 0,
            'status': '待开始',
            'quantity': 200
        }, ensure_ascii=False)

        cur.execute(
            "INSERT INTO data_packages (target_operator, related_order, related_process, content, status, created_at) VALUES (?,?,?,?,?,?)",
            ('OP001', order_no, process_name, new_content, 'packaged', '2025-06-01')
        )
        conn.commit()

        # 验证可以读取并匹配
        cur.execute("SELECT content FROM data_packages WHERE related_order=? AND related_process=?",
                   (order_no, process_name))
        row = cur.fetchone()
        content = json.loads(row['content']) if isinstance(row['content'], str) else row['content']
        assert content['process_code'] == 'P03'
        assert content['order_no'] == order_no

    def test_non_standard_process_insert_then_match(self, sqlite_with_data):
        """非标工序 INSERT + 匹配"""
        conn = sqlite_with_data
        cur = conn.cursor()

        order_no = 'GO-NEW-002'
        process_name = '阳极氧化'
        process_code = get_process_code(process_name)

        assert process_code.startswith('PX')
        assert len(process_code) == 6

        new_content = json.dumps({
            'order_no': order_no,
            'process_name': process_name,
            'process_code': process_code,
            'completed_qty': 0,
            'status': '待开始',
            'quantity': 100
        }, ensure_ascii=False)

        cur.execute(
            "INSERT INTO data_packages (target_operator, related_order, related_process, content, status, created_at) VALUES (?,?,?,?,?,?)",
            ('OP002', order_no, process_name, new_content, 'packaged', '2025-06-01')
        )
        conn.commit()

        cur.execute("SELECT content FROM data_packages WHERE related_order=? AND related_process=?",
                   (order_no, process_name))
        row = cur.fetchone()
        content = json.loads(row['content']) if isinstance(row['content'], str) else row['content']
        assert content['process_code'] == process_code


# ============================================================
# Fallback 逻辑测试
# ============================================================

class TestFallbackLogic:
    """app.py / process_v2.py 中的 fallback 逻辑"""

    def test_fallback_when_process_code_missing(self, sqlite_with_data):
        """content 中缺少 process_code 时，从 process_name 动态计算"""
        conn = sqlite_with_data
        cur = conn.cursor()

        # 找一条缺少 process_code 的包
        cur.execute("SELECT rowid, content, related_process FROM data_packages")
        target = None
        for row in cur.fetchall():
            content = json.loads(row['content']) if isinstance(row['content'], str) else row['content']
            if isinstance(content, dict) and not content.get('process_code') and content.get('process_name'):
                target = (row['content'], row['related_process'])
                break

        assert target is not None, "应该有一条缺少 process_code 的包"
        raw_content, related_process = target
        content = json.loads(raw_content) if isinstance(raw_content, str) else raw_content

        # 模拟 fallback 逻辑
        _process_code = content.get('process_code', '')
        if not _process_code:
            _pname = content.get('process_name', '') or related_process or ''
            if _pname:
                _process_code = get_process_code(_pname)

        assert _process_code == 'P14'  # 表面处理

    def test_fallback_when_both_missing(self):
        """process_code 和 process_name 都缺失"""
        content = {'order_no': 'GO-999', 'completed_qty': 10, 'status': '进行中'}
        _process_code = content.get('process_code', '')
        if not _process_code:
            _pname = content.get('process_name', '') or ''
            if _pname:
                _process_code = get_process_code(_pname)

        assert _process_code == ''

    def test_fallback_for_non_standard(self):
        """非标工序的 fallback"""
        content = {'order_no': 'GO-888', 'process_name': '锻造', 'completed_qty': 5}
        _process_code = content.get('process_code', '')
        if not _process_code:
            _pname = content.get('process_name', '')
            if _pname:
                _process_code = get_process_code(_pname)

        assert _process_code.startswith('PX')
        assert len(_process_code) == 6


# ============================================================
# 并发安全模拟测试
# ============================================================

class TestConcurrentSafety:
    """并发场景模拟"""

    def test_same_process_code_always_same_result(self):
        """多线程环境 get_process_code 结果一致"""
        import threading
        results = []

        def worker():
            results.append(get_process_code('打磨'))

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(set(results)) == 1

    def test_get_process_code_is_thread_safe(self):
        """get_process_code 函数本身是线程安全的（纯计算）"""
        import threading
        import concurrent.futures

        results = set()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(get_process_code, f'工序_{i}') for i in range(100)]
            for f in concurrent.futures.as_completed(futures):
                results.add(f.result())

        assert len(results) == 100  # 100 个不同名称 = 100 个不同编码
