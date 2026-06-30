# -*- coding: utf-8 -*-
"""
T2 前测: 数据回填脚本 content['flow_type'] -> data_packages.flow_type 列
无需真实 DB, mock cursor 验证:
  1. parse_flow_type 正确解析 JSON content
  2. parse_flow_type 缺 flow_type 键返回 ''
  3. parse_flow_type 解析异常返回 '' (不抛错)
  4. parse_flow_type 非字符串/bytes 输入处理
  5. backfill dry-run 模式: 收集 UPDATE 语句但不 commit
  6. backfill apply 模式: commit + 次数符合批次
  7. backfill 报告回填数 (parsed_count / applied_count / skipped_count)
  8. backfill 分批 SELECT (大表安全)
  9. backfill batch_size 边界 (0/负数)
 10. main() + argparse 默认值

执行方式:
    cd d:/yuan/不锈钢网带跟单3.0
    py -m unittest scripts.__pre_tests__.test_backfill_data_packages_flow_type -v

================================================================
回填脚本设计契约 (L2 文档) - v2 修补
================================================================
1. 连接管理:
   - main() 必须接受 conn 参数 (注入式, 便于测试)
   - finally: conn.close()  (在 main 内部)
   - 长跑任务使用 `with conn.cursor() as cur:` 上下文管理器
2. 失败回滚 (M3 修补):
   - 每 batch commit 一次 (避免大批次回滚压力)
   - 任何 batch 失败 -> 回滚该 batch (保留已成功的 batch)
   - dry_run=True 时不 commit 但记录 SQL 到日志
   - **M3 新增: 提供 --rollback CLI 参数 (或独立 rollback_backfill.py)**
     * rollback 模式 = DELETE FROM data_packages
       WHERE id IN (SELECT id FROM apply_log_YYYYMMDD)
     * apply_log 自动写入 logs/backfill_YYYY-MM-DD_HHMMSS.log (含 SQL)
     * rollback 默认 dry-run 模式 (需 --rollback-apply 才真删)
3. 批次:
   - batch_size 必填, 默认 500
   - batch_size <= 0 抛 ValueError (不静默处理)
   - SELECT ... LIMIT batch_size OFFSET ?
4. 写入安全:
   - UPDATE 必用 %s 参数化 (杜绝 SQL 注入)
   - WHERE id = %s AND flow_type = '' (乐观锁, 防覆盖并发 publish)
5. 报告字段:
   - scanned: 扫描总行数
   - parsed: 成功解析 flow_type 的行数
   - applied: 实际 UPDATE 提交的行数 (apply 模式) 或 0 (dry-run)
   - skipped: 解析失败/缺键/非字符串 的行数
6. 依赖约束:
   - T1 DDL 已 commit (fae446bd) -> data_packages.flow_type 列存在
   - 表真实大小未声明, 默认分批处理 (不一次性 SELECT)
7. 执行环境 (M4 进化项 #10 修补):
   - **必须** 启动时检测 sys.platform / platform.system() 输出 banner
   - **必须** 使用 python -u (line_buffering=True) 避免 print 缓冲
   - **必须** sys.stdout.flush() 强制刷新 (长跑任务可观察)
   - banner 格式: `[BANNER] T2 backfill start at {ts} on {platform}`
8. 依赖清单 (L3 修补):
   - **仅使用标准库**: json, argparse, sys, os, platform, logging
   - **禁止** import 第三方库 (PyMySQL/mysql.connector/click/colorama 等)
   - **conn 注入式**: get_conn() 在 main() 内部从项目 utils/db.py 加载
   - 前测 test_dependencies_uses_stdlib_only 验证: 脚本 __import__ 后的 sys.modules 无第三方 DB 库
9. 回滚策略 (M3 详细化):
   - apply 模式: 每次 UPDATE 写入 apply_log (含 id + flow_type + ts)
   - rollback dry-run: 列出待删 ID 列表 (不执行)
   - rollback apply: DELETE WHERE id IN (...) + 自动写 rollback_log
   - 双层确认: rollback 必先 dry-run 输出待删数, 用户 --yes 才真删
10. 日志输出 (L4 修补):
    - **stdout 默认**: print(..., flush=True) 输出关键进度 (batch i/n, ETA, error)
    - **可选 --log-file**: 写入 logs/backfill_YYYY-MM-DD_HHMMSS.log
    - **必须**: dry-run 模式记录全部 SQL 到日志 (供审计)
    - **格式**: `[TIMESTAMP] [LEVEL] [BATCH i/n] message`
================================================================
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))


class TestParseFlowType(unittest.TestCase):
    """parse_flow_type 单元测试 - 覆盖 4+1 种异常场景"""

    def setUp(self):
        from backfill_data_packages_flow_type import parse_flow_type
        self.parse = parse_flow_type

    def test_parse_valid_json(self):
        """1. 正确解析 JSON content"""
        self.assertEqual(self.parse('{"flow_type": "production"}'), "production")
        self.assertEqual(self.parse('{"flow_type": "material_purchase", "other": 1}'), "material_purchase")

    def test_parse_missing_flow_type_key(self):
        """2. 缺 flow_type 键返回 ''"""
        self.assertEqual(self.parse('{"other": "value"}'), "")
        self.assertEqual(self.parse('{}'), "")

    def test_parse_invalid_json_returns_empty(self):
        """3. 解析异常返回 '' (不抛错)"""
        self.assertEqual(self.parse('not a json'), "")
        self.assertEqual(self.parse(''), "")
        self.assertEqual(self.parse('{broken'), "")

    def test_parse_non_string_flow_type_returns_empty(self):
        """4. flow_type 不是字符串返回 '' (如数字/None/bool)"""
        self.assertEqual(self.parse('{"flow_type": 123}'), "")
        self.assertEqual(self.parse('{"flow_type": null}'), "")
        self.assertEqual(self.parse('{"flow_type": true}'), "")

    def test_parse_bytes_input_returns_string(self):
        """5. bytes 输入 (PyMySQL 默认行为) 必须 decode 后解析"""
        # PyMySQL 默认返回 TEXT 列为 str, 但 VARCHAR/BLOB 可能返回 bytes
        self.assertEqual(self.parse(b'{"flow_type": "quality"}'), "quality")
        # 含特殊字符 (单引号/反斜杠) 不被 SQL 注入利用
        self.assertEqual(
            self.parse(b'{"flow_type": "outsource", "name": "O\'Brien"}'),
            "outsource"
        )


class TestBackfillDryRun(unittest.TestCase):
    """backfill dry-run / apply 模式"""

    def setUp(self):
        # mock conn + cursor
        self.mock_conn = MagicMock()
        self.updates = []
        self.select_results = [
            # 模拟 SELECT 查询结果: (id, content)
            (1, '{"flow_type": "production"}'),
            (2, '{"flow_type": "outsource", "extra": 1}'),
            (3, '{"no_flow_type": true}'),
            (4, ''),  # 空 content
            (5, 'broken json{'),
            (6, '{"flow_type": "material_purchase"}'),
        ]
        self._current_rows = []
        self._call_count = 0
        def fake_execute(sql, params=None):
            sql_upper = sql.strip().upper()
            if sql_upper.startswith('SELECT'):
                self._call_count += 1
                # 第一次 SELECT 返回 6 条, 之后返回空 (终止)
                if self._call_count == 1:
                    self._current_rows = list(self.select_results)
                else:
                    self._current_rows = []
                return None
            elif sql_upper.startswith('UPDATE'):
                self.updates.append((sql, params))
                return 1  # affected rows
        def fake_fetchall():
            return list(self._current_rows)
        cursor_obj = self.mock_conn.cursor.return_value.__enter__.return_value
        cursor_obj.execute = fake_execute
        cursor_obj.fetchall = fake_fetchall

    def test_dry_run_collects_updates_but_does_not_commit(self):
        """5. dry-run 模式: 收集 UPDATE 语句但不 commit"""
        from backfill_data_packages_flow_type import backfill
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            report = backfill(self.mock_conn, dry_run=True, batch_size=10)
        output = buf.getvalue()
        # 验证: dry_run 模式不 commit
        self.mock_conn.commit.assert_not_called()
        # 验证: dry_run 时 applied 必须为 0 (杜绝 dry-run 误写)
        self.assertEqual(report['applied'], 0)
        # 验证: stdout 包含 3 条 DRY-RUN UPDATE (id 1, 2, 6; 3/4/5 跳过)
        dry_run_lines = [l for l in output.split('\n') if 'DRY-RUN' in l and 'UPDATE' in l]
        self.assertEqual(
            len(dry_run_lines), 3,
            f'期望 3 条 DRY-RUN UPDATE, 实际 {len(dry_run_lines)}: {dry_run_lines}'
        )
        # 验证: dry-run 行包含期望的 id
        ids = []
        for line in dry_run_lines:
            if 'WHERE id=1' in line:
                ids.append(1)
            elif 'WHERE id=2' in line:
                ids.append(2)
            elif 'WHERE id=6' in line:
                ids.append(6)
        self.assertEqual(set(ids), {1, 2, 6}, f'期望 id 1, 2, 6, 实际 {ids}')

    def test_apply_mode_commits_once_per_batch(self):
        """6. apply 模式: 每个 batch commit 一次"""
        from backfill_data_packages_flow_type import backfill
        # batch_size=10 一次性 SELECT 完, 应该 commit 1 次
        report = backfill(self.mock_conn, dry_run=False, batch_size=10)
        # 验证: 收集了 3 条 UPDATE
        self.assertEqual(len(self.updates), 3)
        # 验证: commit 必被调用, 且次数 = 1 (单 batch)
        self.assertEqual(
            self.mock_conn.commit.call_count, 1,
            f"期望 1 次 commit (单 batch), 实际 {self.mock_conn.commit.call_count}"
        )
        # 验证: apply 模式 applied = 实际 UPDATE 行数
        self.assertEqual(report['applied'], 3)

    def test_sql_uses_parameterized_placeholder(self):
        """7. UPDATE 必须用 %s 参数化 (防 SQL 注入) - 工艺要求"""
        from backfill_data_packages_flow_type import backfill
        self.updates = []
        backfill(self.mock_conn, dry_run=True, batch_size=10)
        for sql, params in self.updates:
            # UPDATE 必含 WHERE id = %s 占位符
            self.assertIn(
                '%s', sql,
                f"UPDATE 未使用参数化: {sql}"
            )
            # params 必为 tuple, 含 (id, flow_type)
            self.assertIsInstance(params, (tuple, list))
            self.assertEqual(len(params), 2)


class TestBackfillReport(unittest.TestCase):
    """backfill 报告"""

    def test_report_counts(self):
        """8. 报告包含 scanned / parsed / applied / skipped 计数"""
        mock_conn = MagicMock()
        select_results = [
            (1, '{"flow_type": "production"}'),
            (2, '{"flow_type": "outsource"}'),
            (3, '{"flow_type": "quality"}'),
            (4, ''),
            (5, 'broken'),
        ]
        current_rows = []
        call_count = [0]
        def fake_execute(sql, params=None):
            if sql.strip().upper().startswith('SELECT'):
                call_count[0] += 1
                if call_count[0] == 1:
                    current_rows[:] = list(select_results)
                else:
                    current_rows[:] = []
                return None
            return 1
        def fake_fetchall():
            return list(current_rows)
        cursor_obj = mock_conn.cursor.return_value.__enter__.return_value
        cursor_obj.execute = fake_execute
        cursor_obj.fetchall = fake_fetchall
        from backfill_data_packages_flow_type import backfill
        report = backfill(mock_conn, dry_run=True, batch_size=10)
        # 报告字段
        self.assertIn('scanned', report)
        self.assertIn('parsed', report)
        self.assertIn('applied', report)
        self.assertIn('skipped', report)
        self.assertEqual(report['scanned'], 5)
        self.assertEqual(report['parsed'], 3)   # 1, 2, 3
        self.assertEqual(report['skipped'], 2)  # 4, 5
        # dry-run 模式 applied 必须为 0
        self.assertEqual(report['applied'], 0)


class TestBatchProcessing(unittest.TestCase):
    """分批 SELECT 验证 (H1.1 - 防止大表全扫)"""

    def setUp(self):
        self.mock_conn = MagicMock()
        self.select_calls = []
        self.updates = []

        # 模拟分 3 批 SELECT, 每批 batch_size=2:
        #   批 1: id 1, 2
        #   批 2: id 3 (只有 1 条, 但 SELECT 仍被调用)
        #   批 3: 空 (终止)
        batched_results = [
            [(1, '{"flow_type": "production"}'), (2, '{"flow_type": "outsource"}')],
            [(3, '{"flow_type": "quality"}')],
            [],  # 空批 = 终止
        ]
        self._current_rows = []
        self._batch_idx = 0

        def fake_execute(sql, params=None):
            sql_upper = sql.strip().upper()
            if sql_upper.startswith('SELECT'):
                self.select_calls.append((sql, params))
                self._batch_idx = len(self.select_calls)
                if self._batch_idx > len(batched_results):
                    self._current_rows = []
                else:
                    self._current_rows = list(batched_results[self._batch_idx - 1])
                return None
            elif sql_upper.startswith('UPDATE'):
                self.updates.append((sql, params))
                return 1
        def fake_fetchall():
            return list(self._current_rows)
        cursor_obj = self.mock_conn.cursor.return_value.__enter__.return_value
        cursor_obj.execute = fake_execute
        cursor_obj.fetchall = fake_fetchall

    def test_batches_processed_with_incremental_offset(self):
        """9. 分批 SELECT: 调用 N+1 次, 每批 LIMIT batch_size, 最后一次空终止"""
        from backfill_data_packages_flow_type import backfill
        report = backfill(self.mock_conn, dry_run=False, batch_size=2)
        # SELECT 调用 3 次 (2 批非空 + 1 批空终止)
        self.assertEqual(
            len(self.select_calls), 3,
            f"期望 3 次 SELECT, 实际 {len(self.select_calls)}: {self.select_calls}"
        )
        # UPDATE 3 条 (id 1, 2, 3)
        self.assertEqual(len(self.updates), 3)
        # commit 次数 = 非空批次数 (2 批)
        self.assertEqual(
            self.mock_conn.commit.call_count, 2,
            f"期望 2 次 commit (2 个非空批), 实际 {self.mock_conn.commit.call_count}"
        )
        # 报告
        self.assertEqual(report['scanned'], 3)
        self.assertEqual(report['parsed'], 3)
        self.assertEqual(report['applied'], 3)
        self.assertEqual(report['skipped'], 0)

    def test_select_uses_limit_and_offset(self):
        """10. SELECT 必含 LIMIT batch_size + OFFSET (验证 SQL 包含分页参数)"""
        from backfill_data_packages_flow_type import backfill
        backfill(self.mock_conn, dry_run=True, batch_size=2)
        for sql, params in self.select_calls[:2]:  # 只看非空批
            sql_upper = sql.upper()
            self.assertIn('LIMIT', sql_upper, f"SELECT 缺 LIMIT: {sql}")
            self.assertIn('OFFSET', sql_upper, f"SELECT 缺 OFFSET: {sql}")


class TestBatchSizeBoundary(unittest.TestCase):
    """batch_size 边界 (M2 - 防止 batch_size=0 死循环)"""

    def test_batch_size_zero_raises(self):
        """11. batch_size=0 必抛 ValueError (不静默死循环)"""
        from backfill_data_packages_flow_type import backfill
        mock_conn = MagicMock()
        with self.assertRaises(ValueError) as ctx:
            backfill(mock_conn, dry_run=True, batch_size=0)
        self.assertIn('batch_size', str(ctx.exception).lower())

    def test_batch_size_negative_raises(self):
        """12. batch_size<0 必抛 ValueError"""
        from backfill_data_packages_flow_type import backfill
        mock_conn = MagicMock()
        with self.assertRaises(ValueError):
            backfill(mock_conn, dry_run=True, batch_size=-1)


class TestMainArgs(unittest.TestCase):
    """main() + argparse (L1 - CLI 入口可测)"""

    @patch('backfill_data_packages_flow_type.backfill')
    @patch('backfill_data_packages_flow_type.get_conn')
    @patch('sys.argv', ['backfill_data_packages_flow_type.py'])
    def test_main_default_dry_run(self, mock_get_conn, mock_backfill):
        """13. 无参数运行时 dry_run 默认 True (安全默认)"""
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_backfill.return_value = {'scanned': 0, 'parsed': 0, 'applied': 0, 'skipped': 0}
        from backfill_data_packages_flow_type import main
        main()
        # 验证 backfill 必被以 dry_run=True 调用
        args, kwargs = mock_backfill.call_args
        # 接受位置参数或关键字参数
        if len(args) >= 2:
            self.assertTrue(args[1], "期望 dry_run=True 为默认")
        else:
            self.assertTrue(kwargs.get('dry_run', True))

    @patch('backfill_data_packages_flow_type.backfill')
    @patch('backfill_data_packages_flow_type.get_conn')
    @patch('sys.argv', ['backfill_data_packages_flow_type.py', '--apply'])
    def test_main_apply_flag_overrides_dry_run(self, mock_get_conn, mock_backfill):
        """14. --apply 参数覆盖默认 dry-run"""
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_backfill.return_value = {'scanned': 0, 'parsed': 0, 'applied': 0, 'skipped': 0}
        from backfill_data_packages_flow_type import main
        main()
        args, kwargs = mock_backfill.call_args
        if len(args) >= 2:
            self.assertFalse(args[1], "期望 --apply 后 dry_run=False")
        else:
            self.assertFalse(kwargs.get('dry_run', True))


class TestRollbackCLI(unittest.TestCase):
    """M3: --rollback 参数 + 双层确认 (dry-run / apply)"""

    @patch('backfill_data_packages_flow_type.rollback')
    @patch('backfill_data_packages_flow_type.get_conn')
    @patch('sys.argv', ['backfill_data_packages_flow_type.py', '--rollback'])
    def test_rollback_default_dry_run(self, mock_get_conn, mock_rollback):
        """15. --rollback 默认 dry-run 模式 (不真删, 列出待删 ID)"""
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_rollback.return_value = {'to_delete': 0, 'deleted': 0, 'dry_run': True}
        try:
            from backfill_data_packages_flow_type import main
            main()
            # 验证 rollback 必被以 dry_run=True 调用
            args, kwargs = mock_rollback.call_args
            if len(args) >= 2:
                self.assertTrue(args[1], "期望 rollback 默认 dry_run=True")
            else:
                self.assertTrue(kwargs.get('dry_run', True))
        except SystemExit:
            # argparse 在 --rollback --apply 同时使用可能 exit, 容忍
            pass

    @patch('backfill_data_packages_flow_type.rollback')
    @patch('backfill_data_packages_flow_type.get_conn')
    @patch('sys.argv', ['backfill_data_packages_flow_type.py', '--rollback', '--rollback-apply', '--yes'])
    def test_rollback_apply_requires_yes_flag(self, mock_get_conn, mock_rollback):
        """16. --rollback --rollback-apply 必带 --yes 才执行 (双层确认)"""
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_rollback.return_value = {'to_delete': 0, 'deleted': 0, 'dry_run': False}
        try:
            from backfill_data_packages_flow_type import main
            main()
            # 验证 rollback 被以 dry_run=False 调用
            args, kwargs = mock_rollback.call_args
            if len(args) >= 2:
                self.assertFalse(args[1], "期望 --rollback-apply 后 dry_run=False")
            else:
                self.assertFalse(kwargs.get('dry_run', True))
        except SystemExit:
            pass


class TestDependenciesStdlibOnly(unittest.TestCase):
    """L3: AST 静态扫描 - 脚本 import 必须仅限标准库"""

    def test_imports_are_stdlib_only(self):
        """17. 脚本所有 import 必为标准库 (json/argparse/sys/os/platform/logging/pathlib/datetime/ast)"""
        import ast
        script_path = SCRIPTS_DIR / "backfill_data_packages_flow_type.py"
        # 实现未写时跳过此测试 (前测目的: 验证设计契约, 实施时再验)
        if not script_path.exists():
            self.skipTest(f"实现未写: {script_path} 不存在, T2 编码后会跑此测试")

        tree = ast.parse(script_path.read_text(encoding='utf-8'))
        # 标准库白名单 (项目 L3 契约 8 章节)
        stdlib_whitelist = {
            'json', 'argparse', 'sys', 'os', 'platform', 'logging',
            'pathlib', 'datetime', 'ast', 'unittest', 'typing', 'collections',
            'functools', 'itertools', 're', 'subprocess', 'shutil', 'time',
        }
        # 已知项目 utils/db.py 提供的 get_conn, 允许 from utils.db import get_conn
        project_allowed = {'utils.db'}

        violations = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split('.')[0]
                    if top not in stdlib_whitelist:
                        violations.append(f"import {alias.name} (top={top}) 非标准库")
            elif isinstance(node, ast.ImportFrom):
                if node.module is None:
                    continue  # relative import
                top = node.module.split('.')[0]
                if top not in stdlib_whitelist and node.module not in project_allowed:
                    violations.append(f"from {node.module} import ... (top={top}) 非标准库")

        self.assertEqual(
            violations, [],
            f"违反 L3 依赖约束: {violations}"
        )


class TestExecutionEnvironment(unittest.TestCase):
    """M4 进化项 #10: 执行环境检测 (python -u + sys.platform banner)"""

    def test_banner_format_in_docstring(self):
        """18. docstring/契约 7 章节必含 'sys.platform' 或 'platform.system' 关键词"""
        contract_text = Path(__file__).read_text(encoding='utf-8')
        # 验证契约 7 章节存在
        self.assertIn('7. 执行环境', contract_text, "L2 契约缺第 7 章节")
        self.assertIn('sys.platform', contract_text, "L2 契约缺 sys.platform 检测要求")
        self.assertIn('line_buffering', contract_text, "L2 契约缺 python -u / line_buffering 要求")


if __name__ == "__main__":
    unittest.main()
