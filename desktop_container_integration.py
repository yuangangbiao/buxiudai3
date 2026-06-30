# -*- coding: utf-8 -*-
"""
桌面端容器池集成模块

[v3.8.0] SQLite 已完全移除 (F6 P7 物理清理 2026-06-10 + D3 收敛)
- 唯一数据后端: MySQL (CONTAINER_MYSQL_CFG)
- 可选代理: HTTP API 客户端 (CONTAINER_CENTER_API_URL, 推荐生产)
- 无 SQLite 代码路径 (container_center_v5 raise RuntimeError)

[迁移提示] 推荐新代码使用 mobile_api_ai.dispatch_center.publisher:
    from mobile_api_ai.dispatch_center.publisher import get_publisher
    publisher = get_publisher('report')

使用方法（兼容老代码）:
    from desktop_container_integration import DesktopContainerIntegration

    integration = DesktopContainerIntegration()
    integration.publish_report_task(
        order_no='WO202604001',
        process_name='编织',
        customer_name='上海机械厂',
        product_type='不锈钢编织网',
        quantity=100,
        unit='米',
        planned_qty=100,
        operator_id='OP001',
        operator_name='张三'
    )

    integration.publish_material_task(
        order_no='WO202604001',
        materials=[
            {'material_name': '不锈钢丝', 'required_qty': 500, 'unit': 'kg'},
            {'material_name': '编织网', 'required_qty': 200, 'unit': 'm'}
        ]
    )
"""
import sys
import os
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

MOBILE_API_AI_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'mobile_api_ai')
if MOBILE_API_AI_PATH not in sys.path:
    sys.path.insert(0, MOBILE_API_AI_PATH)


class DesktopContainerIntegration:
    """
    桌面端容器池集成

    [v3.8.0] 后端统一为 MySQL, 无 SQLite 代码路径
    - HTTP API 客户端 (推荐, 通过 CONTAINER_CENTER_API_URL 启用)
    - MySQL ContainerCenter 本地直连 (兜底)
    """

    def __init__(self, **_kwargs_unused):
        """
        初始化集成

        [v3.8.0] 移除 db_path 参数 (SQLite 已废弃)
        - _kwargs_unused 保留参数位置, 仅用于日志警告老调用方
        """
        if _kwargs_unused:
            logger.warning(
                f'[v3.8.0] DesktopContainerIntegration 已移除 SQLite 支持, '
                f'忽略参数: {list(_kwargs_unused.keys())}'
            )
        self._container_center = None
        self._center_client = None
        self._initialized = False
        self._circuit_breaker = None
        self._init_container_center()
        self._init_circuit_breaker()

    def _init_container_center(self) -> None:
        """
        初始化容器中心

        [v3.8.0] 优先级:
          1. HTTP API 客户端 (CONTAINER_CENTER_API_URL / CONTAINER_URL) - 推荐
          2. MySQL ContainerCenter 本地直连 (兜底)
          3. SQLite 代码路径已删除 (container_center_v5 raise RuntimeError)
        """
        api_url = os.getenv('CONTAINER_CENTER_API_URL', '').strip()
        if not api_url:
            api_url = os.getenv('CONTAINER_URL', '').strip()
        if api_url:
            try:
                from container_center_client import ContainerCenterClient
                self._center_client = ContainerCenterClient(base_url=api_url)
                self._initialized = True
                logger.info(f'[容器集成] 初始化 HTTP API 客户端: {api_url}')
                return
            except Exception as e:
                logger.warning(
                    f'[容器集成] HTTP API 客户端初始化失败，回退到 MySQL 直连: {e}'
                )

        try:
            from container_center_v5 import ContainerCenter
            # [v3.8.0] 不传 type='sqlite', 走 container_center_v5 默认 MySQL
            self._container_center = ContainerCenter()
            self._initialized = True
            logger.info('[容器集成] 初始化 MySQL ContainerCenter (CONTAINER_MYSQL_CFG)')
        except Exception as e:
            logger.error(f'[容器集成] 初始化失败: {e}')
            self._initialized = False

    def _init_circuit_breaker(self) -> None:
        """
        初始化熔断器
        """
        try:
            from modular_config import ModularConfig
            cb_config = ModularConfig.get_circuit_breaker_config()

            if cb_config.get('enabled', True):
                from modules.circuit_breaker import CircuitBreaker
                self._circuit_breaker = CircuitBreaker(
                    name='desktop_container_integration',
                    failure_threshold=cb_config.get('failure_threshold', 50),
                    success_threshold=cb_config.get('success_threshold', 3),
                    failure_rate_threshold=cb_config.get('failure_rate_threshold', 0.01),
                    open_timeout=cb_config.get('open_timeout', 30.0),
                    recovery_timeout=cb_config.get('recovery_timeout', 60.0)
                )
                logger.info('[容器集成] 熔断器初始化成功')
        except ImportError:
            logger.warning('[容器集成] 熔断器模块不可用')
        except Exception as e:
            logger.warning(f'[容器集成] 熔断器初始化失败: {e}')

    @property
    def is_available(self) -> bool:
        """
        检查集成是否可用

        Returns:
            集成是否可用（HTTP API 或本地 SQLite 任一模式可用即可）
        """
        if not self._initialized:
            return False

        if self._center_client is not None:
            return True

        if self._container_center is None:
            return False

        if self._circuit_breaker:
            from modules.circuit_breaker import CircuitState
            if self._circuit_breaker.state == CircuitState.OPEN:
                logger.warning('[容器集成] 熔断器处于开启状态')
                return False

        return True

    def _record_success(self) -> None:
        """
        记录成功调用
        """
        if self._circuit_breaker:
            try:
                self._circuit_breaker.record_success()
            except Exception as e:
                logger.warning(f'[容器集成] 记录成功失败: {e}')

    def _record_failure(self) -> None:
        """
        记录失败调用
        """
        if self._circuit_breaker:
            try:
                self._circuit_breaker.record_failure()
            except Exception as e:
                logger.warning(f'[容器集成] 记录失败失败: {e}')

    def _execute_with_circuit_breaker(self, func, *args, **kwargs) -> Any:
        """
        使用熔断器执行函数

        Args:
            func: 要执行的函数
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            函数返回值
        """
        if not self._circuit_breaker:
            return func(*args, **kwargs)

        from modules.circuit_breaker import CircuitState

        if self._circuit_breaker.state == CircuitState.OPEN:
            logger.warning('[容器集成] 熔断器开启，拒绝调用')
            raise Exception('熔断器开启，拒绝调用')

        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure()
            raise

    def publish_report_task(self,
                           order_no: str,
                           process_name: str,
                           customer_name: str = '',
                           product_type: str = '',
                           quantity: int = 0,
                           unit: str = '',
                           planned_qty: int = 0,
                           process_status: str = '待开始',
                           operator_id: str = 'OP001',
                           operator_name: str = '',
                           priority: str = 'normal',
                           is_outsource: bool = False) -> Optional[str]:
        """
        发布报工任务到容器池

        Args:
            order_no: 订单号
            order_no: 订单号
            process_name: 工序名称
            customer_name: 客户名称
            product_type: 产品类型
            quantity: 订单数量
            unit: 单位
            planned_qty: 计划数量
            process_status: 工序状态
            operator_id: 操作员ID
            operator_name: 操作员名称
            priority: 优先级

        Returns:
            任务ID，失败返回 None
        """
        if not self.is_available:
            logger.warning('[容器集成] 不可用，跳过任务发布')
            return None

        try:
            logger.info(f'[容器集成] 发布报工任务: order_no={order_no}, process={process_name}, is_outsource={is_outsource}')

            if self._center_client is not None:
                result = self._center_client.publish_task(
                    task_type='outsource' if is_outsource else 'report',
                    title=f'报工：{process_name} - {order_no}',
                    content={
                        'order_no': order_no,
                        'process_name': process_name,
                        'customer_name': customer_name,
                        'product_type': product_type,
                        'quantity': quantity,
                        'unit': unit,
                        'planned_qty': planned_qty,
                        'process_status': process_status,
                        'operator_name': operator_name,
                        'priority': priority,
                        'is_outsource': is_outsource,
                        'voice_text': f'订单{order_no}，工序{process_name}，数量{planned_qty}{unit}，请确认任务！'
                    },
                    operator_id=operator_id,
                    priority=priority,
                    related_order=order_no,
                    related_process=process_name
                )
                if result:
                    task_id = result.get('task_id', '')
                    logger.info(f'[容器集成] HTTP API 报工任务发布成功: {task_id}')
                    return task_id
                logger.warning('[容器集成] HTTP API 返回为空')
                return None

            if is_outsource:
                pkg = self._container_center.collect_outsource(
                    order_no=order_no,
                    process_name=process_name,
                    process_seq=0,
                    planned_qty=planned_qty,
                    outsource_remark='',
                    operator_id=operator_id
                )
                pkg.content.update({
                    'order_no': order_no,
                    'customer_name': customer_name,
                    'product_type': product_type,
                    'quantity': quantity,
                    'unit': unit,
                    'process_status': process_status,
                    'operator_name': operator_name,
                })
                self._container_center.storage.save_package(pkg.to_dict())
                if operator_id and operator_id != 'OP001':
                    try:
                        self._container_center.distributor.distribute(pkg.id, operator_id)
                    except Exception as e:
                        logger.warning(f'[容器集成] 外协任务分配时警告: {e}')
                logger.info(f'[容器集成] 外协任务发布成功: {pkg.id}')
                return pkg.id

            pkg = self._container_center.collect_report(
                order_no=order_no,
                process_name=process_name,
                record_id=0,
                operator_id=operator_id,
                planned_qty=planned_qty
            )

            pkg.content.update({
                'order_no': order_no,
                'customer_name': customer_name,
                'product_type': product_type,
                'quantity': quantity,
                'unit': unit,
                'process_status': process_status,
                'operator_name': operator_name,
                'priority': priority,
                'voice_text': f'订单{order_no}，工序{process_name}，数量{planned_qty}{unit}，请确认任务！'
            })

            self._container_center.storage.save_package(pkg.to_dict())

            if operator_id and operator_id != 'OP001':
                try:
                    self._container_center.distributor.distribute(pkg.id, operator_id)
                    logger.info(f'[容器集成] 已分配任务给操作员: {operator_id}')
                except Exception as e:
                    logger.warning(f'[容器集成] 分配任务时警告: {e}')

            logger.info(f'[容器集成] 报工任务发布成功: {pkg.id}')
            return pkg.id

        except Exception as e:
            logger.error(f'[容器集成] 发布报工任务失败: {e}')
            self._record_failure()
            return None

    def publish_material_task(self,
                              order_no: str,
                              materials: List[Dict[str, Any]],
                              process_name: str = '',
                              customer_name: str = '',
                              order_id: int = 0,
                              process_id: int = 0,
                              priority: str = 'normal',
                              **kwargs) -> Optional[str]:
        """
        发布用料需求任务到容器池

        Args:
            order_no: 订单号
            order_no: 订单号
            materials: 物料列表，每项包含:
                - material_name: 物料名称
                - required_qty: 需求量
                - prepared_qty: 已备量
                - unit: 单位
            process_name: 工序名称
            customer_name: 客户名称
            order_id: 订单ID
            process_id: 工序ID
            priority: 优先级
            **kwargs: 其他扩展数据

        Returns:
            任务ID，失败返回 None
        """
        if not self.is_available:
            logger.warning('[容器集成] 不可用，跳过用料需求发布')
            return None

        try:
            logger.info(f'[容器集成] 发布用料需求任务: order_no={order_no}, materials_count={len(materials)}')

            if self._center_client is not None:
                result = self._center_client.publish_task(
                    task_type='material',
                    title=f'用料需求 - {order_no}',
                    content={
                        'order_no': order_no,
                        'process_name': process_name,
                        'customer_name': customer_name,
                        'order_id': order_id,
                        'process_id': process_id,
                        'materials': materials,
                        'priority': priority,
                        'voice_text': f'订单{order_no}有用料需求，请及时处理！',
                        **kwargs
                    },
                    operator_id='OP005',
                    priority=priority
                )
                if result:
                    task_id = result.get('task_id', '')
                    logger.info(f'[容器集成] HTTP API 用料需求发布成功: {task_id}')
                    return task_id
                logger.warning('[容器集成] HTTP API 返回为空')
                return None

            if not hasattr(self._container_center, 'create_package'):
                logger.error('[容器集成] 容器中心不支持 create_package 方法')
                return self._publish_material_task_fallback(
                    order_no, order_no, materials,
                    process_name, customer_name, priority, **kwargs
                )

            pkg = self._container_center.create_package(
                data_type='material',
                title=f'用料需求 - {order_no}',
                content={
                    'order_no': order_no,
                    'order_no': order_no,
                    'process_name': process_name,
                    'customer_name': customer_name,
                    'order_id': order_id,
                    'process_id': process_id,
                    'materials': materials,
                    'priority': priority,
                    'voice_text': f'订单{order_no}有用料需求，请及时处理！',
                    **kwargs
                }
            )

            self._container_center.storage.save_package(pkg.to_dict())

            logger.info(f'[容器集成] 用料需求任务发布成功: {pkg.id}')
            return pkg.id

        except Exception as e:
            logger.error(f'[容器集成] 发布用料需求任务失败: {e}')
            self._record_failure()
            return None

    def _publish_material_task_fallback(self,
                                        order_no: str,
                                        materials: List[Dict[str, Any]],
                                        process_name: str,
                                        customer_name: str,
                                        priority: str,
                                        **kwargs) -> Optional[str]:
        """
        备用的用料需求发布方法（当 create_package 不可用时）

        使用 collect_report 模式模拟发布
        """
        try:
            logger.info('[容器集成] 使用备用方法发布用料需求')

            first_material = materials[0] if materials else {}
            material_name = first_material.get('material_name', '用料需求')

            pkg = self._container_center.collect_report(
                order_no=order_no,
                process_name=f'备料-{material_name}',
                record_id=0,
                operator_id='OP005',
                planned_qty=first_material.get('required_qty', 0)
            )

            pkg.content.update({
                'order_no': order_no,
                'customer_name': customer_name,
                'process_name': process_name,
                'data_type': 'material',
                'materials': materials,
                'priority': priority,
                'voice_text': f'订单{order_no}有用料需求，请及时处理！',
                **kwargs
            })

            self._container_center.storage.save_package(pkg.to_dict())

            logger.info(f'[容器集成] 用料需求任务发布成功(备用): {pkg.id}')
            return pkg.id

        except Exception as e:
            logger.error(f'[容器集成] 备用发布方法也失败: {e}')
            return None

    def publish_quality_task(self,
                           order_no: str,
                           customer_name: str = '',
                           product_type: str = '',
                           inspection_type: str = '终检',
                           operator_id: str = 'OP004',
                           operator_name: str = '',
                           priority: str = 'high') -> Optional[str]:
        """
        发布质检任务

        Args:
            order_no: 订单号
            order_no: 订单号
            customer_name: 客户名称
            product_type: 产品类型
            inspection_type: 质检类型（终检/首检）
            operator_id: 操作员ID
            operator_name: 操作员名称
            priority: 优先级

        Returns:
            任务ID，失败返回 None
        """
        if not self.is_available:
            logger.warning('[容器集成] 不可用，跳过质检任务发布')
            return None

        try:
            logger.info(f'[容器集成] 发布质检任务: order_no={order_no}, type={inspection_type}')

            if self._center_client is not None:
                result = self._center_client.publish_task(
                    task_type='quality',
                    title=f'质检：{inspection_type} - {order_no}',
                    content={
                        'order_no': order_no,
                        'customer_name': customer_name,
                        'product_type': product_type,
                        'inspection_type': inspection_type,
                        'operator_name': operator_name,
                        'priority': priority,
                        'voice_text': f'订单{order_no}，需要{inspection_type}，请确认！'
                    },
                    operator_id=operator_id,
                    priority=priority
                )
                if result:
                    task_id = result.get('task_id', '')
                    logger.info(f'[容器集成] HTTP API 质检任务发布成功: {task_id}')
                    return task_id
                logger.warning('[容器集成] HTTP API 返回为空')
                return None

            pkg = self._container_center.collect_quality(
                order_no=order_no,
                order_id=0,
                inspector_id=operator_id,
                inspection_type=inspection_type,
                planned_qty=0
            )

            pkg.content.update({
                'order_no': order_no,
                'customer_name': customer_name,
                'product_type': product_type,
                'operator_name': operator_name,
                'priority': priority,
                'voice_text': f'订单{order_no}，需要{inspection_type}，请确认！'
            })

            self._container_center.storage.save_package(pkg.to_dict())

            logger.info(f'[容器集成] 质检任务发布成功: {pkg.id}')
            return pkg.id

        except Exception as e:
            logger.error(f'[容器集成] 发布质检任务失败: {e}')
            self._record_failure()
            return None

    def get_all_tasks(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取所有任务

        Args:
            limit: 返回数量限制

        Returns:
            任务列表
        """
        if not self.is_available:
            return []

        try:
            if self._center_client is not None:
                return self._center_client.get_all_tasks(limit=limit) or []
            return self._container_center.get_all_tasks(limit=limit)
        except Exception as e:
            logger.error(f'[容器集成] 获取任务失败: {e}')
            return []

    def get_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        根据ID获取任务

        Args:
            task_id: 任务ID

        Returns:
            任务数据
        """
        if not self.is_available:
            return None

        try:
            if self._center_client is not None:
                tasks = self._center_client.get_all_tasks(limit=1000) or []
                for t in tasks:
                    if t.get('id') == task_id or t.get('task_id') == task_id:
                        return t
                return None
            return self._container_center.storage.get_package(task_id)
        except Exception as e:
            logger.error(f'[容器集成] 获取任务失败: {e}')
            return None

    def get_task_count(self) -> Dict[str, Any]:
        """
        获取任务统计

        Returns:
            统计信息字典
        """
        if not self.is_available:
            return {'total': 0}

        try:
            tasks = self.get_all_tasks(limit=1000)
            status_count = {}
            for task in tasks:
                status = task.get('status', 'unknown')
                status_count[status] = status_count.get(status, 0) + 1
            return {
                'total': len(tasks),
                'by_status': status_count
            }
        except Exception as e:
            logger.error(f'[容器集成] 获取统计失败: {e}')
            return {'total': 0}

    def get_circuit_breaker_status(self) -> Optional[Dict[str, Any]]:
        """
        获取熔断器状态

        Returns:
            熔断器状态信息
        """
        if not self._circuit_breaker:
            return None

        try:
            from modules.circuit_breaker import CircuitState
            state = self._circuit_breaker.state
            return {
                'name': self._circuit_breaker.name,
                'state': state.value if isinstance(state, CircuitState) else str(state),
                'metrics': {
                    'total_calls': self._circuit_breaker._metrics.total_calls,
                    'failed_calls': self._circuit_breaker._metrics.failed_calls,
                    'success_rate': self._circuit_breaker._metrics.success_rate
                }
            }
        except Exception as e:
            logger.warning(f'[容器集成] 获取熔断器状态失败: {e}')
            return None

    def show_status(self) -> None:
        """
        打印容器池状态
        """
        stats = self.get_task_count()
        cb_status = self.get_circuit_breaker_status()

        print('\n[STATUS] 容器池状态')
        print('=' * 50)
        print(f"总任务数: {stats.get('total', 0)}")

        status_names = {
            'pending': '[PENDING] 待分配',
            'distributed': '[DISTRIBUTED] 已分配待确认',
            'acknowledged': '[ACK] 已确认',
            'completed': '[DONE] 已完成'
        }

        for status, count in stats.get('by_status', {}).items():
            print(f"  {status_names.get(status, status)}: {count}")

        if cb_status:
            print('-' * 50)
            print(f"熔断器状态: {cb_status['state']}")
            print(f"总调用数: {cb_status['metrics']['total_calls']}")
            print(f"失败调用: {cb_status['metrics']['failed_calls']}")
            print(f"成功率: {cb_status['metrics']['success_rate']:.2%}")

        print('=' * 50)


_integration_instance: Optional['DesktopContainerIntegration'] = None


def get_integration() -> 'DesktopContainerIntegration':
    """
    获取全局集成实例（单例）

    Returns:
        DesktopContainerIntegration 实例
    """
    global _integration_instance
    if _integration_instance is None:
        _integration_instance = DesktopContainerIntegration()
    return _integration_instance


def reset_integration() -> None:
    """
    重置全局集成实例（用于测试或重新初始化）
    """
    global _integration_instance
    _integration_instance = None
    logger.info('[容器集成] 全局实例已重置')


def demo() -> None:
    """
    演示用法
    """
    print('=' * 60)
    print('桌面端容器池集成演示')
    print('=' * 60)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    integration = DesktopContainerIntegration()

    if not integration.is_available:
        print('\n[ERROR] 容器集成不可用，请检查！')
        return

    print('\n[1] 发布报工任务...')
    task_id1 = integration.publish_report_task(
        order_no='WO202604001',
        process_name='编织',
        customer_name='上海机械厂',
        product_type='不锈钢编织网',
        quantity=100,
        unit='米',
        planned_qty=100,
        operator_id='OP001',
        operator_name='张三',
        priority='high'
    )

    print('\n[2] 发布质检任务...')
    task_id2 = integration.publish_quality_task(
        order_no='WO202604002',
        customer_name='北京钢材厂',
        product_type='钢板',
        inspection_type='终检',
        operator_id='OP004',
        operator_name='李四',
        priority='high'
    )

    print('\n[3] 发布用料需求任务...')
    task_id3 = integration.publish_material_task(
        order_no='WO202604003',
        process_name='编织',
        customer_name='广州机械厂',
        materials=[
            {'material_name': '不锈钢丝', 'required_qty': 500, 'prepared_qty': 300, 'unit': 'kg'},
            {'material_name': '编织网', 'required_qty': 200, 'prepared_qty': 200, 'unit': 'm'}
        ],
        priority='normal'
    )

    print('\n[4] 容器池状态')
    integration.show_status()

    print('\n' + '=' * 60)
    print('演示完成！')
    print('=' * 60)


if __name__ == '__main__':
    demo()
