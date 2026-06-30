"""[v3.7.8] publisher.py 端到端集成测试

启动条件（标记为 integration，需要时跑）：
1. 5003 端口容器中心服务运行
2. MySQL 数据库可访问
3. SQLite 文件路径可写

当前实现：所有测试都标记为 skip（依赖未就绪）
等 docker-compose 准备好后移除 skip 标记。
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


# 检查 5003 端口是否运行
def _is_5003_running():
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        result = sock.connect_ex(('127.0.0.1', 5003))
        sock.close()
        return result == 0
    except Exception:
        return False


# 检查 MySQL 是否可达
def _is_mysql_available():
    try:
        from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
        import pymysql
        conn = pymysql.connect(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
        conn.close()
        return True
    except Exception:
        return False


pytestmark_5003 = pytest.mark.skipif(
    not _is_5003_running(),
    reason='[v3.7.8] 5003 端口容器中心未运行（启动方法：cd mobile_api_ai && python standalone_dispatch_server.py）',
)
pytestmark_mysql = pytest.mark.skipif(
    not _is_mysql_available(),
    reason='[v3.7.8] MySQL 不可达（生产环境配置 CONTAINER_MYSQL_CFG）',
)


# =============================================================================
# API 兼容测试（不需要 5003 / MySQL，但有运行时验证）
# =============================================================================

class TestPublisherAPIRuntime:
    """API 兼容层运行时验证（不依赖外部服务）"""

    def test_publish_report_task_uses_real_publisher(self):
        """[v3.7.7.1] 验证 service 调用的方法真存在"""
        from mobile_api_ai.dispatch_center.publisher import get_publisher

        p = get_publisher('report')

        # service 真实调用方式
        result = p.publish_report_task(
            order_no='WO-INT-001',
            process_name='拉丝',
            customer_name='客户',
            product_type='304',
            quantity=10,
            unit='米',
            planned_qty=10,
            operator_id='OP001',
            operator_name='张三',
            priority='normal',
        )

        assert result is not None, 'publish_report_task 返回 None'
        assert result == 'WO-INT-001'
        print('✅ 运行时 API 兼容通过')

    def test_data_actually_stored_in_memory(self):
        """验证数据真存到 _task_store（不是 mock）"""
        from mobile_api_ai.dispatch_center.publisher import get_publisher, get_all_tasks

        before_count = len(get_all_tasks())

        p = get_publisher('report')
        p.publish_report_task(
            order_no='WO-INT-002',
            process_name='拉丝',
            quantity=10,
        )

        after_count = len(get_all_tasks())
        assert after_count == before_count + 1, f'存储未生效: {before_count} -> {after_count}'
        print(f'✅ 存储验证通过 ({before_count} -> {after_count})')


# =============================================================================
# 5003 端口 HTTP 调用测试（依赖服务运行）
# =============================================================================

@pytestmark_5003
class TestPublisherHTTP5003:
    """[v3.7.8 目标] 验证 publisher 调用 5003 端口"""

    def test_publish_call_5003(self):
        """publish 应该 POST 到 5003/api/internal/publish"""
        # 等 v3.7.8 实现 HTTP 调用后启用
        pytest.skip('[v3.7.8] 待实现 HTTP 调用后再启用')

    def test_5003_receives_data(self):
        """5003 接收后应该有 DB 写入"""
        pytest.skip('[v3.7.8] 待 HTTP 调用实现')


# =============================================================================
# MySQL 直连测试（依赖 DB）
# =============================================================================

@pytestmark_mysql
class TestPublisherMySQL:
    """[v3.7.8 目标] 验证 publisher 直写 MySQL"""

    def test_insert_to_dispatch_center_tasks(self):
        """[v3.7.8] 应该 INSERT INTO dispatch_center_tasks"""
        pytest.skip('[v3.7.8] 待 DDL 创建表后启用')

    def test_query_task_count(self):
        """[v3.7.8] 应该能 SELECT COUNT(*) FROM dispatch_center_tasks"""
        pytest.skip('[v3.7.8] 待实现')


# =============================================================================
# 端到端业务流（最高优先级）
# =============================================================================

class TestPublisherBusinessFlow:
    """端到端业务流（不依赖外部服务，但验证业务逻辑）"""

    def test_report_to_material_to_quality_flow(self):
        """完整业务流：报工 → 物料 → 质检"""
        from mobile_api_ai.dispatch_center.publisher import get_publisher

        # Step 1: 报工
        report = get_publisher('report')
        task1 = report.publish_report_task(
            order_no='WO-FLOW-001',
            process_name='拉丝',
            quantity=50,
            unit='米',
            operator_name='张三',
        )
        assert task1 == 'WO-FLOW-001'

        # Step 2: 物料
        material = get_publisher('material')
        task2 = material.publish_material_task(
            order_no='WO-FLOW-001',
            materials=[{'name': '钢丝', 'qty': 50, 'unit': 'kg'}],
        )
        assert task2 == 'WO-FLOW-001'

        # Step 3: 质检
        quality = get_publisher('quality')
        task3 = quality.publish_quality_task(
            order_no='WO-FLOW-001',
            inspection_type='终检',
        )
        assert task3 == 'WO-FLOW-001'

        print('✅ 业务流: 报工→物料→质检 全部通过')


if __name__ == '__main__':
    # 手动跑（不通过 pytest）
    print('=== TestPublisherAPIRuntime ===')
    t = TestPublisherAPIRuntime()
    t.test_publish_report_task_uses_real_publisher()
    t.test_data_actually_stored_in_memory()
    print()
    print('=== TestPublisherBusinessFlow ===')
    f = TestPublisherBusinessFlow()
    f.test_report_to_material_to_quality_flow()
    print('\n=== 全部集成测试通过 ===')