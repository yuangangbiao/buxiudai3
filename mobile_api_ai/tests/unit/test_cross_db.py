# -*- coding: utf-8 -*-
"""跨库查表 + 去重防护 测试套件

覆盖：
1. 表所属数据库验证（防止查错库）
2. 入口检查（orders 存在性）
3. 去重逻辑（id + order_no+product_name）
4. quantity 兜底（content.quantity 不为 0）
"""
import os, sys, re, pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(sys.path[0]))

MOCK_PATH = os.path.join(os.path.dirname(__file__))

# ════════════════════════════════════════════════════
# 表所属数据库定义
# ════════════════════════════════════════════════════

TABLES_IN_CONTAINER_CENTER = {
    'report_queue', 'process_records', 'process_sub_steps',
    'enterprise_structure', 'workers', 'attendance',
    'data_packages', 'data_flow_logs', 'sync_logs',
    'return_records', 'product_flow_map', 'data_collection_records',
}

TABLES_IN_STEEL_BELT = {
    'orders', 'production_orders',
    'process_records', 'process_sub_steps',
    'schedule_records', 'schedule_queue',
    'operators', 'product_types',
    'sync_queue',
    'customer_contacts', 'customer_groups',
    'process_calc_rules', 'process_names',
    'wechat_tasks',
}

SHARED_TABLES = {'process_sub_steps', 'process_records'}


# ════════════════════════════════════════════════════
# Part 1: Table Ownership
# ════════════════════════════════════════════════════

class TestTableOwnership:
    """验证每张表在正确的数据库中"""

    @pytest.fixture
    def container_tables(self):
        import pymysql
        from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
        cfg = {k: v for k, v in CONTAINER_MYSQL_CFG.items() if k != 'cursorclass'}
        conn = pymysql.connect(**cfg, connect_timeout=DB_CONNECT_TIMEOUT)
        cur = conn.cursor()
        cur.execute("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA='container_center'")
        tables = {r[0] for r in cur.fetchall()}
        cur.close(); conn.close()
        return tables

    @pytest.fixture
    def steel_belt_tables(self):
        import pymysql
        from core.config import MYSQL_CFG, DB_CONNECT_TIMEOUT
        cfg = {k: v for k, v in MYSQL_CFG.items() if k != 'cursorclass'}
        conn = pymysql.connect(**cfg, connect_timeout=DB_CONNECT_TIMEOUT)
        cur = conn.cursor()
        cur.execute("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA='steel_belt'")
        tables = {r[0] for r in cur.fetchall()}
        cur.close(); conn.close()
        return tables

    @pytest.mark.parametrize('table_name', sorted(TABLES_IN_CONTAINER_CENTER - SHARED_TABLES))
    def test_container_tables_exist(self, table_name, container_tables):
        assert table_name in container_tables, \
            f"{table_name} 应在 container_center 但不存在"

    @pytest.mark.parametrize('table_name', sorted(TABLES_IN_STEEL_BELT - SHARED_TABLES))
    def test_steel_belt_tables_exist(self, table_name, steel_belt_tables):
        assert table_name in steel_belt_tables, \
            f"{table_name} 应在 steel_belt 但不存在"

    def test_no_container_tables_in_steel_belt(self, steel_belt_tables):
        leaked = (TABLES_IN_CONTAINER_CENTER - SHARED_TABLES) & steel_belt_tables
        assert not leaked, f"这些表属于 container_center 但出现在 steel_belt: {leaked}"

    def test_no_steel_belt_tables_in_container(self, container_tables):
        leaked = (TABLES_IN_STEEL_BELT - SHARED_TABLES) & container_tables
        assert not leaked, f"这些表属于 steel_belt 但出现在 container_center: {leaked}"


# ════════════════════════════════════════════════════
# Part 2: Code-Level Cross-DB Checks
# ════════════════════════════════════════════════════

class TestCodeCrossDB:
    """验证源代码不会查错库"""

    @pytest.fixture
    def source_files(self):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        files = []
        for root, dirs, filenames in os.walk(base):
            # [F6 P9 2026-06-10] 排除 tests 目录防自指 + 历史排除项
            dirs[:] = [d for d in dirs if d not in ('__pycache__','logs','docs','_migration_backups','scripts','tests')]
            for fn in filenames:
                if fn.endswith('.py'):
                    files.append(os.path.join(root, fn))
        return files

    def test_dispatch_center_no_mysqlstorage_for_orders(self, source_files):
        """dispatch_center.py 查 orders 必须用 steel_belt 连接"""
        for f in source_files:
            if 'dispatch_center.py' not in f:
                continue
            with open(f, 'r', encoding='utf-8', errors='replace') as fh:
                content = fh.read()
            for table in ['orders', 'production_orders']:
                pattern = re.compile(rf'(?:FROM|JOIN)\s+{table}\b', re.IGNORECASE)
                for match in pattern.finditer(content):
                    start = max(0, match.start() - 500)
                    before = content[start:match.start()]
                    if 'MySQLStorage' in before:
                        lineno = content[:match.start()].count('\n') + 1
                        pytest.fail(f"{os.path.basename(f)}:{lineno} MySQLStorage -> {table}（在 steel_belt）")

    def test_get_customer_group_uses_steel_belt(self, source_files):
        """_get_customer_group_for_order 用 steel_belt"""
        for f in source_files:
            if 'dispatch_center.py' not in f:
                continue
            with open(f, 'r', encoding='utf-8', errors='replace') as fh:
                content = fh.read()
            if '_get_customer_group_for_order' not in content:
                continue
            fs = content.index('_get_customer_group_for_order')
            fe = content.find('\ndef ', fs)
            if fe == -1: fe = len(content)
            body = content[fs:fe]
            assert 'MySQLStorage' not in body, \
                "_get_customer_group_for_order 不应使用 MySQLStorage"
            assert 'MYSQL_CFG' in body, \
                "_get_customer_group_for_order 应使用 MYSQL_CFG"

    def test_all_mysqlstorage_queries_only_container_tables(self, source_files):
        """MySQLStorage 只能查 container_center 表"""
        steel_exclusive = TABLES_IN_STEEL_BELT - SHARED_TABLES
        for f in source_files:
            if 'storage/mysql_storage.py' in f:
                continue
            with open(f, 'r', encoding='utf-8', errors='replace') as fh:
                content = fh.read()
            if 'MySQLStorage' not in content:
                continue
            for table in steel_exclusive:
                for match in re.finditer(rf'(?:FROM|JOIN)\s+{table}\b', content, re.IGNORECASE):
                    if 'MySQLStorage' in content[max(0,match.start()-500):match.start()]:
                        pytest.fail(f"{os.path.basename(f)}:{content[:match.start()].count(chr(10))+1} MySQLStorage -> {table}")


# ════════════════════════════════════════════════════
# Part 3: Entry-Point Protections
# ════════════════════════════════════════════════════

class TestEntryProtections:
    """验证发布入口有 orders 存在性检查"""

    def test_register_workorder_checks_orders(self):
        """register_workorder 必须先查 orders 表"""
        # [F6 P9 2026-06-10] dispatch_center.py 已拆分为 dispatch_center/ 目录, 改读 _core.py
        with open('D:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center/_core.py', 'r', encoding='utf-8') as f:
            content = f.read()
        # 函数体内有 SELECT 1 FROM orders
        idx = content.index('def register_workorder')
        end = content.find('\ndef ', idx)
        if end == -1: end = len(content)
        body = content[idx:end]
        assert "SELECT 1 FROM orders" in body or "SELECT id FROM orders" in body, \
            "register_workorder 缺少 orders 存在性检查"

    def test_confirm_schedule_checks_orders(self):
        """confirm_schedule 必须先查 orders 表"""
        with open('D:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center/schedule_routes.py', 'r', encoding='utf-8') as f:
            content = f.read()
        idx = content.index('def api_workorder_confirm_schedule')
        end = content.find('\ndef ', idx)
        if end == -1: end = len(content)
        body = content[idx:end]
        assert "SELECT 1 FROM orders" in body or "SELECT id FROM orders" in body, \
            "confirm_schedule 缺少 orders 存在性检查"


# ════════════════════════════════════════════════════
# Part 4: Dedup Protections
# ════════════════════════════════════════════════════

class TestDedupProtections:
    """验证去重逻辑"""

    def test_mysql_sync_has_product_name_dedup(self):
        """MySQL 同步函数有 id + order_no+product_name 双重去重"""
        # [F6 P9 2026-06-10] dispatch_center.py 已拆分为 dispatch_center/ 目录, 改读 _core.py
        with open('D:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center/_core.py', 'r', encoding='utf-8') as f:
            content = f.read()
        # 找 sync to MySQL 的同步函数
        assert "save_process_record" in content, "缺少 MySQL 同步函数"
        # 必须有二级去重
        assert "product_name" in content, "去重逻辑缺少 product_name 检查"

    def test_register_workorder_rejects_deleted_orders(self):
        """已删除的订单不应能被重新发布"""
        # [F6 P9 2026-06-10] dispatch_center.py 已拆分为 dispatch_center/ 目录, 改读 _core.py
        with open('D:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center/_core.py', 'r', encoding='utf-8') as f:
            content = f.read()
        idx = content.index('def register_workorder')
        end = content.find('\ndef ', idx)
        if end == -1: end = len(content)
        body = content[idx:end]
        assert '404' in body, "register_workorder 对不存在订单应返回 404"

    def test_publish_quantity_fallback(self):
        """publish_task 有 quantity 兜底逻辑"""
        with open('D:/yuan/不锈钢网带跟单3.0/mobile_api_ai/container_center_api.py', 'r', encoding='utf-8') as f:
            content = f.read()
        idx = content.index('def publish_task()')
        end = content.find('\ndef ', idx)
        if end == -1: end = len(content)
        body = content[idx:end]
        assert "quantity" in body, "publish_task 缺少 quantity 处理"
        assert "content['quantity']" in body or 'content.get' in body, "缺少 content.quantity 赋值"


# ════════════════════════════════════════════════════
# Part 5: Public Dispatch (全员派发)
# ════════════════════════════════════════════════════

class TestPublicDispatch:
    """验证全员派发不会按操作员拆分任务"""

    def test_dispatch_is_single_public_task(self):
        """_dispatch 函数不应循环操作员创建多条任务"""
        # [F6 P9 2026-06-10] dispatch_center.py 已拆分为 dispatch_center/ 目录, 改读 _core.py
        # _dispatch 是嵌套函数 (缩进 12 空格), 不像顶层 def _dispatch 用 \ndef 找边界
        with open('D:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center/_core.py', 'r', encoding='utf-8') as f:
            content = f.read()
        # 嵌套 def 形如 "            def _dispatch(targets"
        idx = content.index("            def _dispatch(targets")
        # 嵌套函数结束: 下一个同缩进的语句或 \n            # 注释
        end = content.find("\n            # ", idx + 30)
        if end == -1: end = content.find("\n            except", idx + 30)
        if end == -1: end = idx + 2000  # 兜底截 2000 字符
        body = content[idx:end]
        assert "for op in (targets" not in body, \
            "_dispatch 不应循环操作员（应创建单条公共任务）"
        assert "operator_id: ''" in body or "operator_id': ''" in body, \
            "_dispatch 应传空 operator_id（公共任务）"
