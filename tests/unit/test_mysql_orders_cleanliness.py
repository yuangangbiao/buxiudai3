# -*- coding: utf-8 -*-
"""
K22 桌面端 orders 表脏数据守护测试

防 K22 类问题再次出现：
- BUG 9 修复 (excel_utils.import_orders 加去重) 被回退
- 批量测试订单 (ORD-20260614-*/ORD-20260615-* 等前缀) 再次灌入

包含:
1. 静态扫描: excel_utils.py 含 _check_recent_duplicate 方法
2. 静态扫描: import_orders 调用 _check_recent_duplicate
3. 静态扫描: excel_view.py 调用 import_orders 走 dedup 路径
4. SQL 验证: 当前 MySQL orders 表未删除未归档行数 < 5
5. 功能测试: 同一 Excel 60s 内重复导入被拒绝
"""
import os
import sys
import re
import hashlib
import tempfile

import pytest

PROJECT_DIR = r"d:\yuan\不锈钢网带跟单3.0"
EXCEL_UTILS_PATH = os.path.join(PROJECT_DIR, "utils", "excel_utils.py")
EXCEL_VIEW_PATH = os.path.join(PROJECT_DIR, "desktop", "views", "excel_view.py")


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


class TestBUG9ImportOrdersDedupStatic:
    """静态扫描：B9 修复存在性 (防回退)"""

    @pytest.fixture
    def excel_utils_source(self):
        return _read(EXCEL_UTILS_PATH)

    def test_dedup_method_exists(self, excel_utils_source):
        """_check_recent_duplicate 方法必须存在"""
        assert "def _check_recent_duplicate" in excel_utils_source, \
            "BUG9 修复被回退: _check_recent_duplicate 方法不存在"

    def test_dedup_method_uses_md5(self, excel_utils_source):
        """_check_recent_duplicate 必须用 md5 指纹"""
        match = re.search(
            r'def _check_recent_duplicate\(cls.*?(?=\n    @classmethod|\n    @staticmethod|\n    def \w+|\nclass )',
            excel_utils_source,
            re.DOTALL
        )
        assert match, "找不到 _check_recent_duplicate 方法体"
        body = match.group(0)
        assert "md5" in body or "sha" in body, \
            "BUG9 修复不完整: _check_recent_duplicate 未用 hash 指纹"

    def test_dedup_cooldown_seconds_defined(self, excel_utils_source):
        """_IMPORT_COOLDOWN_SECONDS 必须定义 (冷却期)"""
        assert "_IMPORT_COOLDOWN_SECONDS" in excel_utils_source, \
            "BUG9 修复不完整: 未定义 _IMPORT_COOLDOWN_SECONDS"

    def test_import_orders_calls_dedup(self, excel_utils_source):
        """import_orders 必须调用 _check_recent_duplicate"""
        match = re.search(
            r'def import_orders\(file_path: str\) -> dict:.*?(?=\n    @staticmethod|\n    @classmethod|\n    def \w+|\nclass )',
            excel_utils_source,
            re.DOTALL
        )
        assert match, "找不到 import_orders 方法体"
        body = match.group(0)
        assert "_check_recent_duplicate" in body, \
            "BUG9 修复不完整: import_orders 未调用 _check_recent_duplicate"
        assert "duplicate" in body.lower(), \
            "BUG9 修复不完整: import_orders 未处理 duplicate 返回"

    def test_dedup_returns_error_message(self, excel_utils_source):
        """去重命中时应返回错误信息"""
        match = re.search(
            r'def import_orders\(file_path: str\) -> dict:.*?(?=\n    @staticmethod|\n    @classmethod|\n    def \w+|\nclass )',
            excel_utils_source,
            re.DOTALL
        )
        body = match.group(0)
        assert "errors" in body and "已导入过" in body, \
            "BUG9 修复不完整: import_orders 命中重复时未返回 '已导入过' 错误信息"


class TestExcelViewImportsCorrectly:
    """静态扫描: excel_view.py 是否仍调用 import_orders"""

    def test_excel_view_calls_import(self):
        source = _read(EXCEL_VIEW_PATH)
        match = re.search(
            r'def _import_orders\(self\):.*?(?=\n    def \w+|\nclass )',
            source,
            re.DOTALL
        )
        assert match, "找不到 _import_orders 方法"
        body = match.group(0)
        assert "ExcelImporter.import_orders" in body, \
            "BUG9 修复可能破坏了 _import_orders 调用链"


class TestMySQLOrdersCleanliness:
    """SQL 验证: MySQL orders 表脏数据 < 5 条"""

    @pytest.fixture
    def mysql_available(self):
        """检查 MySQL 是否可用"""
        try:
            import pymysql
            conn = pymysql.connect(
                host='localhost', port=3306,
                user='root', password='88888888',
                database='steel_belt', charset='utf8mb4',
                connect_timeout=2
            )
            yield conn
            conn.close()
        except Exception as e:
            pytest.skip(f"MySQL 不可用: {e}")

    def test_visible_orders_count_small(self, mysql_available):
        """未删除未归档订单数 < 5 (防 230 条测试数据再次出现)"""
        conn = mysql_available
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM orders WHERE is_deleted=0 AND is_archived=0")
        count = cur.fetchone()[0]
        assert count < 5, f"未删除未归档订单数={count} 超过阈值 5, 可能再次出现测试数据污染"

    def test_no_bulk_test_prefix(self, mysql_available):
        """未删除的 ORD-20260614/0615 测试订单应为 0 (防回退)"""
        conn = mysql_available
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM orders "
            "WHERE (order_no LIKE 'ORD-20260614-%' OR order_no LIKE 'ORD-20260615-%') "
            "AND is_deleted=0"
        )
        count = cur.fetchone()[0]
        assert count == 0, f"ORD-20260614/0615 测试订单数={count} 应为 0 (K22 已清理)"


class TestImportOrdersDedupFunctional:
    """功能测试: 同一 Excel 60s 内重复导入被拒"""

    def test_duplicate_import_rejected(self):
        """创建临时 Excel，第一次导入成功（或因缺列失败但不重复），第二次应被拒"""
        try:
            from utils.excel_utils import ExcelImporter
        except ImportError as e:
            pytest.skip(f"无法导入 ExcelImporter: {e}")

        # 准备临时 xlsx
        try:
            import openpyxl
        except ImportError:
            pytest.skip("openpyxl 不可用")

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tf:
            tmp_path = tf.name

        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            # 最小表头 + 1 行数据
            headers = ["订单号", "客户", "电话", "地址", "产品类型", "材质",
                       "网孔尺寸", "丝径", "宽度", "长度", "数量", "单位",
                       "单价", "总金额", "表面处理", "特殊要求", "交期",
                       "状态", "备注", "扩展参数"]
            ws.append(headers)
            ws.append(["", "测试去重客户", "13800000000", "", "测试产品", "",
                       "", "", "", "", 1, "米", 0, 0, "", "", None,
                       "待确认", "", ""])
            wb.save(tmp_path)
            wb.close()

            # 第一次导入 - 因为缺 orders 表真实连接会失败，但不会触发去重
            r1 = ExcelImporter.import_orders(tmp_path)
            # 第二次导入 - 无论第一次结果如何，应触发去重返回 duplicate=True
            r2 = ExcelImporter.import_orders(tmp_path)

            assert r2.get('duplicate') is True, \
                f"BUG9 修复失效: 第二次导入未被拒, 返回 {r2}"
            assert r2.get('imported') == 0, \
                f"BUG9 修复失效: 重复导入应 imported=0, 实际 {r2.get('imported')}"
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
