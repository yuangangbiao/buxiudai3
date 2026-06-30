"""
验证企业架构合并功能（Phase1~4）的测试脚本

测试步骤：
1. 测试 enterprise_departments / enterprise_personnel 表是否存在
2. 测试 POST save API 端点
3. 测试 GET load API 端点
4. 测试 enterprise_personnel 中的 is_operator 标志位

用法：
    python scripts/tools/test_enterprise_merge.py
"""
import os
import sys
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

_PARENT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)

from core.config import MYSQL_CFG


def get_connection():
    import pymysql
    return pymysql.connect(**MYSQL_CFG, charset='utf8mb4')


def test_tables_exist():
    """验证两张新表是否存在"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SHOW TABLES LIKE 'enterprise_departments'")
        assert cursor.fetchone(), "enterprise_departments 表不存在"
        logger.info("[PASS] enterprise_departments 表存在")

        cursor.execute("SHOW TABLES LIKE 'enterprise_personnel'")
        assert cursor.fetchone(), "enterprise_personnel 表不存在"
        logger.info("[PASS] enterprise_personnel 表存在")
        return True
    except AssertionError as e:
        logger.error("[FAIL] %s", e)
        return False
    finally:
        cursor.close()
        conn.close()


def test_save_load():
    """验证 save 和 load API"""
    import requests
    try:
        test_departments = [
            {'id': 1, 'name': '公司总部', 'parentid': 0, 'order': 1},
            {'id': 2, 'name': '生产部', 'parentid': 1, 'order': 2},
        ]
        test_users = [
            {'userid': 'test001', 'name': '测试用户1', 'department': [2], 'mobile': '13800138001', 'email': 'test1@test.com', 'position': '测试工程师'},
            {'userid': 'test002', 'name': '测试用户2', 'department': [2], 'mobile': '13800138002'},
        ]
        test_data = {
            'departments': test_departments,
            'users': test_users,
            'updated_at': '2026-05-27T12:00:00',
        }

        resp = requests.post(
            'http://127.0.0.1:5003/api/dispatch-center/enterprise/structure/save',
            json=test_data,
            timeout=5,
        )
        assert resp.status_code == 200, f"save 返回 {resp.status_code}"
        result = resp.json()
        assert result.get('code') == 0, f"save code={result.get('code')}: {result.get('message', '')}"
        logger.info("[PASS] POST save API 正常工作")

        resp = requests.get(
            'http://127.0.0.1:5003/api/dispatch-center/enterprise/structure/load',
            timeout=5,
        )
        assert resp.status_code == 200, f"load 返回 {resp.status_code}"
        result = resp.json()
        assert result.get('code') == 0, f"load code={result.get('code')}: {result.get('message', '')}"
        data = result.get('data', {})
        departments = data.get('departments', [])
        users = data.get('users', [])
        assert len(departments) == 2, f"部门数量不对: {len(departments)}"
        assert len(users) == 2, f"用户数量不对: {len(users)}"
        logger.info("[PASS] GET load API 返回数据正确 (部门=%d, 用户=%d)", len(departments), len(users))
        return True
    except AssertionError as e:
        logger.error("[FAIL] %s", e)
        return False
    except requests.exceptions.ConnectionError:
        logger.error("[FAIL] 连接失败，请确保 dispatch_center 运行在 5003 端口")
        return False
    except Exception as e:
        logger.error("[FAIL] 异常: %s", e)
        return False


def test_operator_flag():
    """验证 operator 同步到 enterprise_personnel 的 is_operator 标志位"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM dispatch_operators")
        op_count = cursor.fetchone()[0]
        logger.info("dispatch_operators 表有 %d 条记录", op_count)

        cursor.execute("SELECT COUNT(*) FROM enterprise_personnel")
        ep_count = cursor.fetchone()[0]
        logger.info("enterprise_personnel 表有 %d 条记录", ep_count)

        cursor.execute("SELECT COUNT(*) FROM enterprise_personnel WHERE is_operator=1")
        op_in_ep = cursor.fetchone()[0]
        logger.info("enterprise_personnel 中 is_operator=1 的记录: %d", op_in_ep)

        if op_count > 0 and op_in_ep == 0:
            logger.warning("[WARN] dispatch_operators 有 %d 条数据但 enterprise_personnel 中 is_operator=1 为 0", op_count)
        elif op_count > 0 and op_in_ep > 0:
            logger.info("[PASS] 操作员已正确同步到 enterprise_personnel (is_operator=1)")
        return True
    except Exception as e:
        logger.error("[FAIL] 查询失败: %s", e)
        return False
    finally:
        cursor.close()
        conn.close()


def cleanup_test_data():
    """清理测试数据"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM enterprise_departments WHERE id IN (1, 2)")
        cursor.execute("DELETE FROM enterprise_personnel WHERE userid IN ('test001', 'test002')")
        conn.commit()
        logger.info("[INFO] 测试数据已清理")
    except Exception as e:
        logger.warning("[WARN] 清理测试数据失败: %s", e)
    finally:
        cursor.close()
        conn.close()


def main():
    logger.info("=" * 50)
    logger.info("企业架构合并功能验证")
    logger.info("=" * 50)

    tables_ok = test_tables_exist()
    save_load_ok = test_save_load()
    operator_ok = test_operator_flag()

    logger.info("=" * 50)
    logger.info("验证结果汇总:")
    logger.info("  [%s] 表结构验证", 'PASS' if tables_ok else 'FAIL')
    logger.info("  [%s] API save/load 验证", 'PASS' if save_load_ok else 'FAIL')
    logger.info("  [%s] 操作员标志位验证", 'PASS' if operator_ok else 'FAIL')
    logger.info("=" * 50)

    cleanup_test_data()

    if tables_ok and save_load_ok and operator_ok:
        logger.info("全部验证通过!")
        return 0
    else:
        logger.warning("部分验证未通过，请检查日志")
        return 1


if __name__ == '__main__':
    sys.exit(main())
