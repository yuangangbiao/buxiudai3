# -*- coding: utf-8 -*-
"""
stats_smart_sheet 模块 - 部署引导脚本

一键完成所有部署步骤：
0. 环境检查
1. 依赖检查
2. 创建智能表格
3. 建 sync_log 表
4. 填入 sheet_id
5. 单元测试
6. 端到端验证

用法：
    python setup.py                      # 引导模式
    python setup.py --step 1             # 只执行指定步骤
    python setup.py --skip-create        # 跳过创建表格
    python setup.py --skip-e2e           # 跳过端到端验证
    python setup.py --force-e2e          # 非交互模式强制 e2e（会实际推送）
    python setup.py --step 6 --force-e2e  # 单步 e2e，强制执行
"""
import sys
import os
import json
import argparse
import logging

# 日志规范：所有输出用 logger，不使用 print
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# 常量（消除魔法数字）
_BANNER_WIDTH = 60
_MASK_PREFIX_LEN = 4
_EXPECTED_TABLE_COUNT = 9

# .env 路径基于脚本自身位置，不依赖 cwd
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ENV_PATH = os.path.join(_SCRIPT_DIR, '.env')

from dotenv import load_dotenv
load_dotenv(_ENV_PATH, override=True)

# 添加项目路径
sys.path.insert(0, os.path.dirname(_SCRIPT_DIR))


def _banner(title: str):
    """统一分隔线打印（消除重复代码）"""
    line = "=" * _BANNER_WIDTH
    logger.info(f"\n{line}\n{title}\n{line}")


def _mask(val: str) -> str:
    """脱敏显示环境变量值"""
    if len(val) > _MASK_PREFIX_LEN:
        return val[:_MASK_PREFIX_LEN] + '***'
    return '***'


def _require_interactive() -> bool:
    """检查是否为交互式环境"""
    return sys.stdin.isatty()


def _confirm(prompt: str, default: str = 'n', auto: bool = False) -> bool:
    """安全的确认输入（非交互环境有默认值）
    auto=True: 非交互环境自动返回 True（用于 e2e）
    auto=False: 非交互环境使用 default 参数
    """
    if not _require_interactive():
        if auto:
            logger.warning("  非交互环境，默认执行 e2e（实际推送）")
            return True
        logger.info(f"  非交互环境，使用默认值: {default}")
        return default == 'y'
    try:
        reply = input(prompt).strip().lower()
        return reply == 'y'
    except (EOFError, IOError):
        logger.warning("  输入不可用，使用默认值")
        return default == 'y'


def check_env():
    """步骤0: 环境变量检查"""
    _banner("步骤0: 环境变量检查")

    required = [
        'MYSQL_HOST', 'MYSQL_PORT', 'MYSQL_USER', 'MYSQL_PASSWORD',
        'CONTAINER_MYSQL_USER', 'CONTAINER_MYSQL_PASSWORD',
        'CONTAINER_MYSQL_DATABASE',
        'INVENTORY_MYSQL_USER', 'INVENTORY_MYSQL_PASSWORD',
        'INVENTORY_DB_NAME',
        'CLOUD_5004_HOST', 'CLOUD_5004_API_KEY',
        'WECHAT_SMARTSHEET_KEY',
        'STATS_API_KEY',
    ]
    optional = [
        'INVENTORY_SAFETY_THRESHOLD', 'INVENTORY_SLOW_MOVING_DAYS',
        'STATS_MAX_RETRIES', 'STATS_RETRY_INTERVAL',
    ]

    missing = []
    for key in required:
        val = os.getenv(key, '')
        if not val:
            logger.error(f"  ❌ {key}: 未设置（必需）")
            missing.append(key)
        else:
            logger.info(f"  ✅ {key}: {_mask(val)}")

    for key in optional:
        val = os.getenv(key, '')
        if val:
            logger.info(f"  ⬜ {key}: {val} (可选)")
        else:
            logger.info(f"  ⬜ {key}: 未设置（使用默认值）")

    if missing:
        logger.warning(f"  ⚠️  缺少 {len(missing)} 个必需环境变量")
        logger.info("  💡 请复制 .env.example 为 .env 并填入实际值")
        return False
    return True


def check_dependencies():
    """步骤1: 检查 Python 依赖"""
    _banner("步骤1: 依赖检查")

    # 修复 P2-M-9: 用 importlib 替代 __import__
    import importlib.util
    deps = [
        ('pymysql', 'PyMySQL'),
        ('requests', 'requests'),
        ('dotenv', 'python-dotenv'),
        ('apscheduler', 'APScheduler'),
        ('dbutils', 'DBUtils'),
    ]
    missing = []
    for import_name, display_name in deps:
        spec = importlib.util.find_spec(import_name)
        if spec is not None:
            logger.info(f"  ✅ {display_name}")
        else:
            logger.error(f"  ❌ {display_name} 未安装")
            missing.append(display_name)
    if missing:
        logger.warning(f"  💡 安装: pip install {' '.join(missing)}")
        return False
    return True


def _confirm_smart_sheets(skip: bool = False):
    """包装 create_smart_sheets，支持 --confirm 跳过确认"""
    if skip:
        logger.info("  ⏭️  --confirm，跳过确认（假设已完成）")
        return True
    return create_smart_sheets()


def create_smart_sheets():
    """步骤2: 创建智能表格"""
    _banner("步骤2: 创建智能表格")
    logger.info("  💡 方式A（手动）: 企业微信工作台 → 智能表格 → 创建 9 张")
    logger.info("  💡 方式B（API）: python setup_create_smart_sheets.py --dry-run")
    logger.info(f"  📋 9 张表格清单：")

    tables = [
        ('production_daily_report',    '工单-生产日报'),
        ('production_monthly_report',  '工单-生产月报'),
        ('workshop_capacity',           '工单-车间产能分析'),
        ('workorder_progress',         '工单-工单进度跟踪'),
        ('substep_report',            '工单-工序报工汇总'),
        ('inventory_weekly_report',    '库存-库存周报'),
        ('inventory_monthly_summary',   '库存-物料收发存汇总'),
        ('inventory_alert',           '库存-库存预警'),
        ('inventory_slow_moving',     '库存-呆滞料分析'),
    ]
    for i, (key, name) in enumerate(tables, 1):
        logger.info(f"     {i}. {name} ({key})")

    # 修复 HIGH-5: 交互式 input() 安全化
    reply = _confirm("  是否已完成智能表格创建？(y/n): ")
    return reply


def create_sync_log():
    """步骤3: 创建 sync_log 表"""
    _banner("步骤3: 创建 stats_sync_log 表")

    try:
        from stats_smart_sheet.mysql_config import get_conn
        logger.info("  🔄 连接 container_center 库...")
        conn = get_conn('container_center')
        logger.info("  ✅ 连接成功")

        # 检查是否已存在
        with conn.cursor() as c:
            c.execute("SHOW TABLES LIKE 'stats_sync_log'")
            if c.fetchone():
                logger.info("  ⏭️  stats_sync_log 表已存在，跳过创建")
                conn.close()
                return True

        # 读取建表脚本
        script_path = os.path.join(_SCRIPT_DIR, 'stats_sync_log.sql')
        if os.path.exists(script_path):
            with open(script_path, encoding='utf-8') as f:
                sql = f.read()
            # 去掉注释行，只留 SQL
            lines = [l for l in sql.split('\n')
                     if l.strip() and not l.strip().startswith('--')]
            create_sql = '\n'.join(lines)
            with conn.cursor() as c:
                c.execute(create_sql)
            logger.info("  ✅ stats_sync_log 表创建成功")
        else:
            logger.warning("  ⚠️  stats_sync_log.sql 文件未找到，跳过")

        conn.close()
        return True
    except RuntimeError as e:
        # 修复 P0-2: 分层异常处理
        logger.error(f"  ❌ 配置错误: {e}")
        logger.info("  💡 请检查 MYSQL_* 环境变量是否正确")
        return False
    except Exception:
        # 修复 P0-2: 用 logger.exception 记录 traceback
        logger.exception("  ❌ 发生异常")
        logger.info("  💡 请手动执行: mysql -u root -p container_center < stats_sync_log.sql")
        return False


def fill_sheet_ids():
    """步骤4: 填入 sheet_id"""
    _banner("步骤4: 填入智能表格 docid/sheet_id")
    logger.info("  💡 运行: python setup_smart_sheets.py --fill")
    logger.info("  💡 或手动编辑 TABLE_INDEX.json")

    index_path = os.path.join(_SCRIPT_DIR, 'TABLE_INDEX.json')
    if os.path.exists(index_path):
        with open(index_path, encoding='utf-8') as f:
            index = json.load(f)
        # 修复 HIGH-7: 用常量替代魔法数字 9
        if len(index) >= _EXPECTED_TABLE_COUNT:
            logger.info(f"  ✅ TABLE_INDEX.json 已配置 {len(index)} 张表")
            return True
        else:
            logger.warning(f"  ⚠️  TABLE_INDEX.json 只有 {len(index)} 张表，"
                           f"还需 {_EXPECTED_TABLE_COUNT - len(index)} 张")
            return False
    else:
        logger.warning("  ⚠️  TABLE_INDEX.json 不存在，需填入")
        return False


def run_unit_tests():
    """步骤5: 单元测试"""
    _banner("步骤5: 单元测试（mock 模式）")
    try:
        from stats_smart_sheet.tests import test_stats_smart_sheet as ts
        import unittest
        suite = unittest.TestSuite()
        loader = unittest.TestLoader()
        for cls in [ts.TestProductionLines, ts.TestComputeHash,
                    ts.TestFieldMapping, ts.TestConfigIntegrity,
                    ts.TestConcurrencyControl]:
            suite.addTests(loader.loadTestsFromTestCase(cls))
        runner = unittest.TextTestRunner(verbosity=1)
        result = runner.run(suite)
        return result.wasSuccessful()
    except Exception:
        logger.exception("  ❌ 单元测试异常")
        return False


def run_e2e(table: str = 'substep_report', force: bool = False):
    """步骤6: 端到端验证
    force=True: 非交互模式强制执行（--force-e2e）
    force=False: 非交互模式默认跳过
    """
    _banner("步骤6: 端到端验证")
    logger.info(f"  测试表: {table}")
    logger.info("  💡 DRY-RUN 模式只查 DB，不推送")
    logger.info("  💡 非 DRY-RUN 会实际写入智能表格")

    # N-2 修复: 非交互模式不自动执行，除非 --force-e2e
    reply = _confirm(
        f"  是否运行端到端验证（非 dry-run 会实际推送）？(y/n): ",
        default='n',
        auto=force,  # --force-e2e 时自动执行
    )
    if not reply:
        logger.info("  ⏭️  跳过端到端验证")
        return True

    # 修复 HIGH-4: 实际调用 test_e2e 的 main()
    try:
        from stats_smart_sheet import test_e2e
        # 构造 sys.argv 模拟命令行
        original_argv = sys.argv
        sys.argv = ['test_e2e', '--table', table, '--skip-cloud']
        try:
            success = test_e2e.main()
        finally:
            sys.argv = original_argv
        return success
    except Exception:
        logger.exception("  ❌ 端到端验证异常")
        return False


def main():
    parser = argparse.ArgumentParser(description='stats_smart_sheet 部署引导')
    parser.add_argument('--step', type=int, choices=range(7),
                        help='只执行指定步骤 (0-6)')
    parser.add_argument('--skip-create', action='store_true',
                        help='跳过创建表格')
    parser.add_argument('--skip-e2e', action='store_true',
                        help='跳过端到端验证')
    parser.add_argument('--confirm', action='store_true',
                        help='跳过所有交互确认（CI/CD，自动执行）')
    parser.add_argument('--force-e2e', action='store_true',
                        help='非交互模式下强制运行 e2e（会实际推送）')
    args = parser.parse_args()

    logger.info("=" * _BANNER_WIDTH)
    logger.info("stats_smart_sheet 模块部署引导")
    logger.info("=" * _BANNER_WIDTH)

    steps = []

    if args.step is None or args.step == 0:
        steps.append(('环境检查', check_env))

    if args.step is None or args.step == 1:
        steps.append(('依赖检查', check_dependencies))

    if args.step is None or args.step == 2:
        steps.append(('智能表格创建',
                     lambda: _confirm_smart_sheets(args.confirm)))

    if args.step is None or args.step == 3:
        steps.append(('创建sync_log表', create_sync_log))

    if args.step is None or args.step == 4:
        steps.append(('填入sheet_id', fill_sheet_ids))

    if args.step is None or args.step == 5:
        steps.append(('单元测试', lambda: run_unit_tests()))

    if args.step is None and not args.skip_e2e:
        # N-2 修复: --force-e2e 强制 e2e 执行
        steps.append(('端到端验证', lambda: run_e2e(force=args.force_e2e)))

    passed = 0
    for name, fn in steps:
        try:
            if fn():
                passed += 1
                logger.info(f"\n  ✅ 「{name}」完成")
            else:
                logger.warning(f"\n  ⚠️  「{name}」未完全通过，继续下一步...")
        except Exception:
            logger.exception(f"\n  ❌ 「{name}」异常")

    logger.info(f"\n{'=' * _BANNER_WIDTH}")
    logger.info(f"完成: {passed}/{len(steps)} 步骤")
    logger.info(f"{'=' * _BANNER_WIDTH}")

    if passed == len(steps):
        logger.info("\n✅ 部署完成！")
        logger.info("后续操作：")
        logger.info("  1. python check_services.py --all  # 检查服务状态")
        logger.info("  2. python test_e2e.py --dry-run    # 端到端验证")
        logger.info("  3. 重启 cloud_relay.py（本地5005）")
        logger.info("  4. 重启 cloud_group_bot_service.py（云端5004）")

    return passed == len(steps)


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
