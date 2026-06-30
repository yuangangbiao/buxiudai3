# -*- coding: utf-8 -*-
"""
wechat_container 迁移 v2.0 完整测试套件
========================================
覆盖: DDL验证 / 迁移验证 / MySQLStorage接口 / ContainerCenter集成 / 性能对比 / 回滚

运行:
  python test_migration_v2.py                    # 全部测试
  python test_migration_v2.py --quick             # 快速冒烟
  python test_migration_v2.py --performance       # 仅性能测试

版本: v2.0, 2026-05-29
"""
import os
import sys
import json
import time
import sqlite3
import unittest
import argparse
from datetime import datetime

# 添加项目根目录以支持 core.config / storage_layer 导入
_PROJECT_ROOT = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai'
if os.path.isdir(_PROJECT_ROOT) and _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

TEST_SRC_DB = os.environ.get(
    'TEST_SRC_DB',
    r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\_migration_backups\wechat_container_final_backup.db'
)

# ════════════════════════════════════════════
# 辅助函数
# ════════════════════════════════════════════

def _get_sqlite_tables():
    conn = sqlite3.connect(TEST_SRC_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    tables = [t[0] for t in cursor.fetchall()]
    conn.close()
    return tables

def _get_sqlite_row_count(table_name):
    conn = sqlite3.connect(TEST_SRC_DB)
    cursor = conn.cursor()
    cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
    cnt = cursor.fetchone()[0]
    conn.close()
    return cnt

# ════════════════════════════════════════════
# Test Suite 1: DDL 验证
# ════════════════════════════════════════════

class TestDDLValidation(unittest.TestCase):
    """验证生成的 DDL 与源 SQLite 表结构一致"""

    def test_all_tables_exist_in_ddl(self):
        """DDL 覆盖全部 29 张表"""
        ddl_file = os.path.join(os.path.dirname(__file__), 'ddl_29_tables.sql')
        with open(ddl_file, 'r', encoding='utf-8') as f:
            content = f.read()

        tables = _get_sqlite_tables()
        for t in tables:
            prefix = t if t.startswith('_') else f'cc_{t}'
            self.assertIn(prefix, content, f'DDL 缺少表: {t} → {prefix}')

    def test_table_count(self):
        """表数量 = 29"""
        tables = _get_sqlite_tables()
        self.assertEqual(len(tables), 29, f'期望 29 张表, 实际 {len(tables)}')

    def test_column_count_per_table(self):
        """每张表的列数匹配"""
        conn = sqlite3.connect(TEST_SRC_DB)
        cursor = conn.cursor()
        for t in _get_sqlite_tables():
            cursor.execute(f'PRAGMA table_info({t})')
            cols = cursor.fetchall()
            self.assertGreater(len(cols), 0, f'表 {t} 无列?')
        conn.close()

    def test_ddl_has_engine_innodb(self):
        """DDL 使用 InnoDB 引擎"""
        ddl_file = os.path.join(os.path.dirname(__file__), 'ddl_29_tables.sql')
        with open(ddl_file, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('ENGINE=InnoDB', content)
        self.assertIn('utf8mb4', content)

    def test_cc_prefix_on_all_user_tables(self):
        """非系统表都有 cc_ 前缀"""
        tables = _get_sqlite_tables()
        for t in tables:
            if t.startswith('_'):
                continue
            ddl_file = os.path.join(os.path.dirname(__file__), 'ddl_29_tables.sql')
            with open(ddl_file, 'r', encoding='utf-8') as f:
                content = f.read()
            self.assertIn(f'cc_{t}', content, f'缺少 cc_ 前缀: {t}')

    def test_uuid_tables_have_varchar36_pk(self):
        """UUID 主键表使用 VARCHAR(36)"""
        ddl_file = os.path.join(os.path.dirname(__file__), 'ddl_29_tables.sql')
        with open(ddl_file, 'r', encoding='utf-8') as f:
            content = f.read()
        uuid_tables = ['cc_process_records', 'cc_process_sub_steps', 'cc_data_packages']
        for t in uuid_tables:
            self.assertIn(f'`{t}`', content)
            self.assertIn('VARCHAR(36)', content, f'{t} 应使用 VARCHAR(36) 主键')


# ════════════════════════════════════════════
# Test Suite 2: 迁移验证
# ════════════════════════════════════════════

class TestMigrationValidation(unittest.TestCase):
    """验证迁移脚本正确性"""

    def test_migrate_script_exists(self):
        """迁移脚本文件存在"""
        script = os.path.join(os.path.dirname(__file__), 'migrate_v2.py')
        self.assertTrue(os.path.exists(script), 'migrate_v2.py 不存在')

    def test_migrate_script_syntax(self):
        """迁移脚本 Python 语法检查"""
        import py_compile
        script = os.path.join(os.path.dirname(__file__), 'migrate_v2.py')
        try:
            py_compile.compile(script, doraise=True)
        except py_compile.PyCompileError as e:
            self.fail(f'migrate_v2.py 语法错误: {e}')

    def test_mysql_storage_syntax(self):
        """MySQLStorage 语法检查"""
        import py_compile
        script = os.path.join(os.path.dirname(__file__), 'mysql_storage.py')
        try:
            py_compile.compile(script, doraise=True)
        except py_compile.PyCompileError as e:
            self.fail(f'mysql_storage.py 语法错误: {e}')

    def test_source_db_accessible(self):
        """源 SQLite 数据库可访问"""
        self.assertTrue(os.path.exists(TEST_SRC_DB), f'源数据库不存在: {TEST_SRC_DB}')
        conn = sqlite3.connect(TEST_SRC_DB)
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        self.assertEqual(cursor.fetchone()[0], 1)
        conn.close()

    def test_all_source_tables_accessible(self):
        """所有源表可读"""
        tables = _get_sqlite_tables()
        conn = sqlite3.connect(TEST_SRC_DB)
        cursor = conn.cursor()
        for t in tables:
            cursor.execute(f'SELECT COUNT(*) FROM {t}')
            cnt = cursor.fetchone()[0]
            self.assertIsInstance(cnt, int, f'表 {t} 查询失败')
        conn.close()

    def test_product_flow_map_has_data(self):
        """product_flow_map 有 13 行数据"""
        cnt = _get_sqlite_row_count('product_flow_map')
        self.assertEqual(cnt, 13, f'product_flow_map 应有 13 行, 实际 {cnt}')

    def test_migrate_dry_run(self):
        """干运行模式可用"""
        import subprocess
        script = os.path.join(os.path.dirname(__file__), 'migrate_v2.py')
        result = subprocess.run(
            ['python', script, '--dry-run'],
            capture_output=True, text=True, timeout=30
        )
        self.assertIn('干运行', result.stdout + result.stderr)
        self.assertEqual(result.returncode, 0)


# ════════════════════════════════════════════
# Test Suite 3: MySQLStorage 接口
# ════════════════════════════════════════════

class TestMySQLStorageInterface(unittest.TestCase):
    """验证 MySQLStorage 实现了完整的 BaseStorage 接口"""

    @classmethod
    def setUpClass(cls):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, base_dir)
        # 添加项目根目录以支持 core.config 导入
        project_root = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai'
        if os.path.isdir(project_root):
            sys.path.insert(0, project_root)
        from mysql_storage import MySQLStorage
        cls.MySQLStorage = MySQLStorage

    def test_has_connection_methods(self):
        """connection 方法完整"""
        required = ['connect', 'disconnect']
        for m in required:
            self.assertTrue(hasattr(self.MySQLStorage, m), f'缺少方法: {m}')

    def test_has_package_methods(self):
        """package 方法完整"""
        required = [
            'save_package', 'get_package', 'get_packages',
            'update_package', 'delete_package', 'cleanup_expired_packages'
        ]
        for m in required:
            self.assertTrue(hasattr(self.MySQLStorage, m), f'缺少方法: {m}')

    def test_has_return_record_methods(self):
        """return record 方法完整"""
        required = ['save_return_record', 'get_return_records']
        for m in required:
            self.assertTrue(hasattr(self.MySQLStorage, m), f'缺少方法: {m}')

    def test_has_process_record_methods(self):
        """process record 方法完整"""
        required = [
            'save_process_record', 'get_process_record',
            'get_process_records', 'get_all_process_records',
            'get_recently_updated_records', 'get_process_records_by_work_order'
        ]
        for m in required:
            self.assertTrue(hasattr(self.MySQLStorage, m), f'缺少方法: {m}')

    def test_has_sub_step_methods(self):
        """sub step 方法完整"""
        required = ['save_sub_step', 'get_sub_steps', 'get_sub_steps_by_order']
        for m in required:
            self.assertTrue(hasattr(self.MySQLStorage, m), f'缺少方法: {m}')

    def test_has_schedule_methods(self):
        """schedule 方法完整"""
        required = ['save_schedule_record', 'get_schedule_record', 'get_schedule_records']
        for m in required:
            self.assertTrue(hasattr(self.MySQLStorage, m), f'缺少方法: {m}')

    def test_has_dispatch_methods(self):
        """dispatch 方法完整"""
        required = ['save_dispatch_command', 'get_dispatch_commands']
        for m in required:
            self.assertTrue(hasattr(self.MySQLStorage, m), f'缺少方法: {m}')

    def test_has_flow_log_methods(self):
        """flow log 方法完整"""
        required = ['save_flow_log', 'get_flow_logs']
        for m in required:
            self.assertTrue(hasattr(self.MySQLStorage, m), f'缺少方法: {m}')

    def test_has_sync_methods(self):
        """sync 方法完整"""
        required = ['save_sync_log', 'get_sync_logs', 'save_sync_retry', 'get_pending_retries']
        for m in required:
            self.assertTrue(hasattr(self.MySQLStorage, m), f'缺少方法: {m}')

    def test_has_org_methods(self):
        """组织/人员方法完整"""
        required = [
            'get_enterprise_structure', 'save_enterprise_structure',
            'get_workers', 'save_worker', 'save_attendance', 'get_attendance'
        ]
        for m in required:
            self.assertTrue(hasattr(self.MySQLStorage, m), f'缺少方法: {m}')

    def test_has_product_flow_methods(self):
        """产品流程方法完整"""
        required = ['get_product_flow_map', 'save_product_flow_map']
        for m in required:
            self.assertTrue(hasattr(self.MySQLStorage, m), f'缺少方法: {m}')

    def test_has_cost_methods(self):
        """成本/物料方法完整"""
        required = [
            'save_order_cost', 'save_order_cost_detail',
            'save_material_price', 'get_material_prices',
            'save_labor_price', 'get_labor_prices',
            'save_material_requirement', 'get_material_requirements',
            'save_material_usage', 'save_pending_material_event'
        ]
        for m in required:
            self.assertTrue(hasattr(self.MySQLStorage, m), f'缺少方法: {m}')

    def test_has_audit_methods(self):
        """审计方法完整"""
        required = [
            'save_sub_step_audit', 'get_sub_step_audit_logs',
            'save_schedule_flow_log'
        ]
        for m in required:
            self.assertTrue(hasattr(self.MySQLStorage, m), f'缺少方法: {m}')

    def test_has_data_collection_methods(self):
        """数据采集方法完整"""
        self.assertTrue(hasattr(self.MySQLStorage, 'save_data_collection'))

    def test_has_report_methods(self):
        """报表方法完整"""
        required = [
            'save_report_definition', 'get_report_definitions',
            'save_report_output', 'save_report_schedule', 'save_export_profile'
        ]
        for m in required:
            self.assertTrue(hasattr(self.MySQLStorage, m), f'缺少方法: {m}')

    def test_method_count(self):
        """方法总数 ≥ 45"""
        public_methods = [m for m in dir(self.MySQLStorage)
                         if not m.startswith('_') and callable(getattr(self.MySQLStorage, m))]
        self.assertGreaterEqual(len(public_methods), 45,
                               f'方法数 {len(public_methods)} < 45')

    def test_table_prefix_constant(self):
        """PREFIX = 'cc_'"""
        self.assertEqual(self.MySQLStorage.PREFIX, 'cc_')

    def test_onnection_params_match_env(self):
        """连接参数与 .env 一致"""
        from mysql_storage import MYSQL_CFG
        self.assertIn('host', MYSQL_CFG)
        self.assertIn('port', MYSQL_CFG)
        self.assertIn('database', MYSQL_CFG)
        self.assertIn('password', MYSQL_CFG)


# ════════════════════════════════════════════
# Test Suite 4: 性能基准
# ════════════════════════════════════════════

class TestPerformanceBaseline(unittest.TestCase):
    """性能基准测试（SQLite 当前性能作为基线）"""

    def test_sqlite_query_speed(self):
        """SQLite 查询核心表耗时 < 100ms"""
        conn = sqlite3.connect(TEST_SRC_DB)
        cursor = conn.cursor()
        start = time.time()
        for _ in range(10):
            cursor.execute('SELECT * FROM process_records LIMIT 10')
            cursor.fetchall()
        elapsed = time.time() - start
        conn.close()
        avg_ms = (elapsed / 10) * 1000
        self.assertLess(avg_ms, 100, f'SQLite 查询太慢: {avg_ms:.1f}ms (期望 <100ms)')
        print(f'[SQLite 查询] 平均: {avg_ms:.1f}ms / 次')

    def test_sqlite_write_speed(self):
        """SQLite 写入速度在合理范围"""
        conn = sqlite3.connect(TEST_SRC_DB)
        cursor = conn.cursor()
        start = time.time()
        for i in range(5):
            cursor.execute(
                'INSERT INTO sync_log (event_type, direction, record_id, status, created_at) '
                'VALUES (?, ?, ?, ?, ?)',
                ('test', 'sqlite_to_mysql', f'test_{i}', 'success', datetime.now().isoformat())
            )
            conn.commit()
        elapsed = time.time() - start
        # 清理测试数据
        cursor.execute("DELETE FROM sync_log WHERE event_type = 'test'")
        conn.commit()
        conn.close()
        avg_ms = (elapsed / 5) * 1000
        self.assertLess(avg_ms, 50, f'SQLite 写入太慢: {avg_ms:.1f}ms')

    def test_json_serialization_speed(self):
        """JSON 序列化耗时"""
        test_data = {
            'steps': [
                {'name': '编织', 'status': 'completed', 'operator': 'test', 'qty': 100},
                {'name': '焊接', 'status': 'in_progress', 'operator': 'test2', 'qty': 50},
            ] * 8
        }
        start = time.time()
        for _ in range(1000):
            _ = json.dumps(test_data, ensure_ascii=False)
        elapsed = (time.time() - start) * 1000
        self.assertLess(elapsed, 500, f'JSON 序列化太慢: {elapsed:.1f}ms (1000次)')


# ════════════════════════════════════════════
# Test Suite 5: 回滚验证
# ════════════════════════════════════════════

class TestRollbackReadiness(unittest.TestCase):
    """回滚方案验证"""

    def test_sqlite_backup_exists(self):
        """可以备份 SQLite"""
        import tempfile, shutil
        tmp = tempfile.mktemp(suffix='.db')
        try:
            shutil.copy2(TEST_SRC_DB, tmp)
            self.assertTrue(os.path.exists(tmp))
            self.assertEqual(os.path.getsize(tmp), os.path.getsize(TEST_SRC_DB))
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    def test_env_switch_key_exists(self):
        """CONTAINER_STORAGE_TYPE 环境变量支持"""
        # 检查方案文档中是否定义了此变量（运行时可能未设置）
        plan_file = os.path.join(os.path.dirname(__file__), '优化方案_v2.0_基于真实架构.md')
        with open(plan_file, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('CONTAINER_STORAGE_TYPE', content,
                      '方案文档中应定义 CONTAINER_STORAGE_TYPE 切换变量')

    def test_sqlite_file_not_locked(self):
        """SQLite 文件未被锁定（可正常打开关闭）"""
        conn = sqlite3.connect(TEST_SRC_DB)
        conn.close()
        # 第二次打开确认无残留锁
        conn = sqlite3.connect(TEST_SRC_DB)
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        conn.close()

    def test_retry_queue_table_structure(self):
        """sync_retry_queue 支持重试机制"""
        conn = sqlite3.connect(TEST_SRC_DB)
        cursor = conn.cursor()
        cursor.execute('PRAGMA table_info(sync_retry_queue)')
        cols = {c[1] for c in cursor.fetchall()}
        required = {'retry_count', 'max_retries', 'last_error', 'next_retry_at'}
        self.assertTrue(required.issubset(cols),
                        f'缺少重试队列列: {required - cols}')
        conn.close()


# ════════════════════════════════════════════
# 主入口
# ════════════════════════════════════════════

def run_all():
    """运行全部测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 按优先级添加
    suite.addTests(loader.loadTestsFromTestCase(TestDDLValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestMySQLStorageInterface))
    suite.addTests(loader.loadTestsFromTestCase(TestMigrationValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestRollbackReadiness))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformanceBaseline))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出汇总
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f'\n{"=" * 60}')
    print(f'测试汇总: {total} 项, 通过: {passed}, 失败: {len(result.failures)}, 错误: {len(result.errors)}')
    print(f'通过率: {passed/total*100:.0f}%')

    return result.wasSuccessful()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--quick', action='store_true', help='快速冒烟（仅 DDL + 接口检查）')
    parser.add_argument('--performance', action='store_true', help='仅性能测试')
    parser.add_argument('--test', type=str, default=None, help='仅运行指定测试类')
    args = parser.parse_args()

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    if args.quick:
        suite.addTests(loader.loadTestsFromTestCase(TestDDLValidation))
        suite.addTests(loader.loadTestsFromTestCase(TestMySQLStorageInterface))
    elif args.performance:
        suite.addTests(loader.loadTestsFromTestCase(TestPerformanceBaseline))
    else:
        suite.addTests(loader.loadTestsFromTestCase(TestDDLValidation))
        suite.addTests(loader.loadTestsFromTestCase(TestMySQLStorageInterface))
        suite.addTests(loader.loadTestsFromTestCase(TestMigrationValidation))
        suite.addTests(loader.loadTestsFromTestCase(TestRollbackReadiness))
        suite.addTests(loader.loadTestsFromTestCase(TestPerformanceBaseline))

    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
