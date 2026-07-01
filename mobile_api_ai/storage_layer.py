# -*- coding: utf-8 -*-
"""
容器端存储抽象层
支持多种存储后端：MySQL（生产）、Redis（缓存）
SQLite 已废弃 — 全部数据走 MySQL (CONTAINER_MYSQL_CFG)
设计时已考虑未来迁移到Redis的兼容性
"""
import json
import logging
import os
import sqlite3
import threading
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum

from core.config import DB_PATHS

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class StorageType(Enum):
    """存储类型"""
    MEMORY = 'memory'
    SQLITE = 'sqlite'
    REDIS = 'redis'
    MYSQL = 'mysql'


class ConnectionMixin(ABC):
    """连接管理 Mixin - 提供存储连接与断开连接功能"""

    @abstractmethod
    def connect(self) -> bool:
        """连接存储"""
        pass

    @abstractmethod
    def disconnect(self):
        """断开连接"""
        pass


class PackageStorageMixin(ABC):
    """数据包存储 Mixin - 提供数据包的增删改查与回传记录"""

    @abstractmethod
    def save_package(self, package: Dict) -> bool:
        """保存数据包"""
        pass

    @abstractmethod
    def get_package(self, package_id: str) -> Optional[Dict]:
        """获取数据包"""
        pass

    @abstractmethod
    def get_packages(self, status: str = None, data_type: str = None,
                    operator: str = None, limit: int = 100) -> List[Dict]:
        """获取数据包列表"""
        pass

    @abstractmethod
    def update_package_status(self, package_id: str, status: str,
                            completed_at: datetime = None) -> bool:
        """更新数据包状态"""
        pass

    @abstractmethod
    def delete_package(self, package_id: str) -> bool:
        """删除数据包"""
        pass

    @abstractmethod
    def save_return_record(self, package_id: str, return_data: Dict,
                          analyzed_result: Dict, write_back_cmd: Dict) -> bool:
        """保存回传记录"""
        pass


class SyncLogMixin(ABC):
    """同步日志 Mixin - 提供同步日志记录功能"""

    @abstractmethod
    def log_sync(self, action: str, package_id: str = None, detail: str = None):
        """记录同步日志"""
        pass


class HealthMixin(ABC):
    """健康检查 Mixin - 提供存储健康检查功能"""

    @abstractmethod
    def health_check(self) -> Dict:
        """健康检查"""
        pass


class DispatchStorageMixin(ABC):
    """调度指令存储 Mixin - 提供调度指令的增删改查"""

    @abstractmethod
    def save_dispatch_command(self, command: Dict) -> bool:
        """保存调度指令"""
        pass

    @abstractmethod
    def get_dispatch_command(self, command_id: str) -> Optional[Dict]:
        """获取调度指令"""
        pass

    @abstractmethod
    def get_dispatch_commands(self, status: str = None, target_type: str = None,
                            operator: str = None, limit: int = 100) -> List[Dict]:
        """获取调度指令列表"""
        pass

    @abstractmethod
    def update_dispatch_command_status(self, command_id: str, status: str,
                                      result: str = None, error: str = None) -> bool:
        """更新调度指令状态"""
        pass

    @abstractmethod
    def get_all_dispatch_commands(self) -> List[Dict]:
        """获取所有调度指令"""
        pass

    @abstractmethod
    def get_dispatch_commands_by_order_process(self, order_no: str, process_name: str) -> List[Dict]:
        """按订单号和工序名查询调度指令"""
        pass

    @abstractmethod
    def delete_dispatch_command(self, command_id: str) -> bool:
        """删除调度指令"""
        pass

    @abstractmethod
    def dedup_dispatch_commands(self) -> int:
        """清理重复的调度指令，同工单同工序只保留最新一条，返回删除数量"""
        pass


class DataFlowStorageMixin(ABC):
    """数据流转日志 Mixin - 提供数据流转记录的查询与保存"""

    @abstractmethod
    def save_data_flow_log(self, flow_log: Dict) -> bool:
        """保存数据流转记录"""
        pass

    @abstractmethod
    def get_data_flow_logs(self, flow_id: str = None, event_type: str = None,
                          order_no: str = None, limit: int = 100) -> List[Dict]:
        """获取数据流转记录"""
        pass

    @abstractmethod
    def get_all_data_flow_logs(self) -> List[Dict]:
        """获取所有数据流转记录"""
        pass


class CollectionStorageMixin(ABC):
    """数据收集存储 Mixin - 提供数据收集记录的增删改查"""

    @abstractmethod
    def save_collection_record(self, record: Dict) -> bool:
        """保存数据收集记录"""
        pass

    @abstractmethod
    def get_collection_record(self, collect_id: str) -> Optional[Dict]:
        """获取数据收集记录"""
        pass

    @abstractmethod
    def get_collection_records(self, data_type: str = None, status: str = None,
                             order_no: str = None, limit: int = 100) -> List[Dict]:
        """获取数据收集记录列表"""
        pass

    @abstractmethod
    def update_collection_record_status(self, collect_id: str, status: str,
                                       package_id: str = None, error: str = None) -> bool:
        """更新数据收集记录状态"""
        pass

    @abstractmethod
    def get_all_collection_records(self) -> List[Dict]:
        """获取所有数据收集记录"""
        pass


class ScheduleStorageMixin(ABC):
    """排产记录存储 Mixin - 提供排产记录的增删改查"""

    @abstractmethod
    def save_schedule_record(self, record: Dict) -> bool:
        """保存排产记录"""
        pass

    @abstractmethod
    def get_schedule_record(self, schedule_id: str) -> Optional[Dict]:
        """获取排产记录"""
        pass

    @abstractmethod
    def get_schedule_record_by_order(self, order_no: str) -> Optional[Dict]:
        """根据订单号获取排产记录"""
        pass

    @abstractmethod
    def get_schedule_records(self, status: str = None, limit: int = 100) -> List[Dict]:
        """获取排产记录列表"""
        pass

    @abstractmethod
    def get_all_schedule_records(self) -> List[Dict]:
        """获取所有排产记录"""
        pass


class ProcessStorageMixin(ABC):
    """流程记录存储 Mixin - 提供流程记录的增删改查与步骤更新"""

    @abstractmethod
    def save_process_record(self, record: Dict) -> bool:
        """保存流程记录"""
        pass

    @abstractmethod
    def get_process_record(self, record_id: str) -> Optional[Dict]:
        """获取流程记录"""
        pass

    @abstractmethod
    def get_process_record_by_order(self, order_no: str) -> Optional[Dict]:
        """根据订单号获取流程记录"""
        pass

    @abstractmethod
    def get_process_records_by_work_order(self, order_no: str) -> List[Dict]:
        """根据订单号获取流程记录列表"""
        pass

    @abstractmethod
    def get_process_records(self, status: str = None, process_type: str = None,
                           search: str = None, limit: int = 100) -> List[Dict]:
        """获取流程记录列表"""
        pass

    @abstractmethod
    def get_all_process_records(self) -> List[Dict]:
        """获取所有流程记录"""
        pass

    @abstractmethod
    def update_process_record_status(self, record_id: str, status: str,
                                    completed_at: str = None, completed_by: str = None) -> bool:
        """更新流程记录状态"""
        pass

    @abstractmethod
    def update_process_record_step(self, record_id: str, current_step: int, expected_step: Optional[int] = None) -> bool:
        """更新流程记录当前步骤"""
        pass

    @abstractmethod
    def update_process_record_task_count(self, record_id: str, task_count: int,
                                        completed_task_count: int) -> bool:
        """更新流程记录任务计数"""
        pass

    @abstractmethod
    def delete_process_record(self, record_id: str) -> bool:
        """删除流程记录"""
        pass

    @abstractmethod
    def assign_template_to_process(self, record_id: str, template_id: str) -> bool:
        """为流程记录指定消息模板"""
        pass


class ScheduleFlowMixin(ABC):
    """排产流程日志 Mixin - 提供排产流程日志的记录与查询"""

    @abstractmethod
    def log_schedule_flow(self, order_no: str, event_type: str, event_data: Dict, operator: str = None) -> bool:
        """记录排产流程日志"""
        pass

    @abstractmethod
    def get_schedule_flow_logs(self, order_no: str) -> List[Dict]:
        """获取排产流程日志"""
        pass


class SubStepMixin(ABC):
    """子步骤存储 Mixin - 提供分批入库/发货的子步骤管理"""

    @abstractmethod
    def save_sub_step(self, record: Dict) -> bool:
        """保存子步骤记录（分批入库/发货）"""
        pass

    @abstractmethod
    def get_sub_steps_by_process(self, order_no: str) -> List[Dict]:
        """获取流程的所有子步骤"""
        pass

    @abstractmethod
    def get_recent_sub_step(self, order_no: str, step_name: str,
                            operator: str, quantity: float,
                            seconds: int = 30) -> Optional[Dict]:
        """查询最近N秒内是否已有相同工单+工序+操作人+数量的报工记录
        用于创建时防重检查
        """
        pass

    @abstractmethod
    def dedup_process_sub_steps(self) -> int:
        """清理 process_sub_steps 中完全重复的报工记录
        按 process_id + step_name + operator + quantity + 日期 分组，
        每组保留最新一条，返回删除的记录数
        """
        pass

    @abstractmethod
    def get_sub_step_summary(self, order_no: str) -> Dict:
        """获取子步骤汇总（累计入库/发货量等）"""
        pass


class CostStorageMixin(ABC):
    """成本存储 Mixin - 提供订单成本的汇总、明细与统计"""

    @abstractmethod
    def save_order_cost(self, cost: Dict) -> bool:
        """保存订单成本汇总"""
        pass

    @abstractmethod
    def get_order_cost(self, order_no: str) -> Optional[Dict]:
        """获取订单成本汇总"""
        pass

    @abstractmethod
    def get_all_order_costs(self, status: str = None, search: str = None,
                           sort_by: str = 'order_no', sort_order: str = 'asc',
                           limit: int = 100, offset: int = 0) -> List[Dict]:
        """获取订单成本列表，支持筛选和分页"""
        pass

    @abstractmethod
    def count_order_costs(self, status: str = None, search: str = None) -> int:
        """统计订单成本数量"""
        pass

    @abstractmethod
    def delete_order_cost(self, order_no: str) -> bool:
        """删除订单成本汇总"""
        pass

    @abstractmethod
    def save_order_cost_detail(self, detail: Dict) -> bool:
        """保存成本明细条目"""
        pass

    @abstractmethod
    def get_order_cost_details(self, order_no: str) -> List[Dict]:
        """获取订单成本明细列表"""
        pass

    @abstractmethod
    def delete_order_cost_detail(self, detail_id: int) -> bool:
        """删除成本明细条目"""
        pass

    @abstractmethod
    def get_cost_summary(self) -> Dict:
        """获取成本汇总统计（总利润、总成本等）"""
        pass


class PriceStorageMixin(ABC):
    """单价存储 Mixin - 提供物料单价与工序工时单价的维护"""

    @abstractmethod
    def get_material_unit_price(self, material_name: str) -> Optional[float]:
        """获取物料单价"""
        pass

    @abstractmethod
    def save_material_unit_price(self, material_name: str, unit_price: float,
                                 unit: str = '个') -> bool:
        """保存/更新物料单价"""
        pass

    @abstractmethod
    def get_all_material_prices(self) -> List[Dict]:
        """获取所有物料单价"""
        pass

    @abstractmethod
    def get_labor_unit_price(self, process_name: str) -> Optional[float]:
        """获取工序工时单价"""
        pass

    @abstractmethod
    def save_labor_unit_price(self, process_name: str, unit_price: float,
                              unit: str = '米') -> bool:
        """保存/更新工序工时单价"""
        pass

    @abstractmethod
    def get_all_labor_prices(self) -> List[Dict]:
        """获取所有工序单价"""
        pass


class BaseStorage(
    ConnectionMixin, PackageStorageMixin, SyncLogMixin, HealthMixin,
    DispatchStorageMixin, DataFlowStorageMixin, CollectionStorageMixin,
    ScheduleStorageMixin, ProcessStorageMixin, ScheduleFlowMixin,
    SubStepMixin, CostStorageMixin, PriceStorageMixin
):
    """
    存储抽象基类
    定义存储接口，所有后端实现必须实现这些方法
    通过多继承组合各领域 Mixin，实现接口关注点分离
    """
    pass




class RedisStorage(BaseStorage):
    """
    Redis存储后端
    预留接口，未来需要时可以快速实现

    使用说明：
    1. 安装redis: pip install redis
    2. 启动redis服务器
    3. 修改配置中的REDIS_URL
    """

    def __init__(self, host: str = None, port: int = None,
                 db: int = 0, password: str = None):
        self.host = host or os.getenv('REDIS_HOST', 'localhost')
        self.port = port or int(os.getenv('REDIS_PORT', '6379'))
        self.db = db
        self.password = password
        self._client = None
        self._redis_available = False

    def connect(self) -> bool:
        """连接Redis"""
        if redis is None:
            logger.warning("Redis库未安装，请运行: pip install redis")
            return False
        try:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True
            )
            self._client.ping()
            self._redis_available = True
            logger.info(f"Redis连接成功: {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            return False

    def disconnect(self):
        if self._client:
            self._client.close()
            self._client = None
            self._redis_available = False
            logger.info("Redis已断开连接")

    def _check_connection(self):
        """检查连接"""
        if not self._redis_available or not self._client:
            raise Exception("Redis未连接，请先调用connect()")

    def save_package(self, package: Dict) -> bool:
        """保存数据包到Redis"""
        self._check_connection()
        key = f"package:{package.get('id')}"
        self._client.set(key, json.dumps(package, ensure_ascii=False))
        self._client.sadd('packages:all', package.get('id'))
        self._client.sadd(f"packages:status:{package.get('status')}", package.get('id'))
        if package.get('related_order'):
            self._client.sadd(f"packages:order:{package.get('related_order')}", package.get('id'))
        return True

    def get_package(self, package_id: str) -> Optional[Dict]:
        """获取数据包"""
        self._check_connection()
        key = f"package:{package_id}"
        data = self._client.get(key)
        if data:
            return json.loads(data)
        return None

    def get_packages(self, status: str = None, data_type: str = None,
                    operator: str = None, limit: int = 100) -> List[Dict]:
        """获取数据包列表"""
        self._check_connection()

        package_ids = self._client.smembers('packages:all')
        packages = []

        for pid in list(package_ids)[:limit]:
            pkg = self.get_package(pid)
            if pkg:
                if status and pkg.get('status') != status:
                    continue
                if data_type and pkg.get('data_type') != data_type:
                    continue
                if operator and pkg.get('target_operator') != operator:
                    continue
                packages.append(pkg)

        return packages

    def update_package_status(self, package_id: str, status: str,
                            completed_at: datetime = None) -> bool:
        """更新数据包状态"""
        self._check_connection()
        pkg = self.get_package(package_id)
        if pkg:
            pkg['status'] = status
            if completed_at:
                pkg['completed_at'] = completed_at.isoformat()
            self.save_package(pkg)
            return True
        return False

    def delete_package(self, package_id: str) -> bool:
        """删除数据包"""
        self._check_connection()
        pkg = self.get_package(package_id)
        if pkg:
            key = f"package:{package_id}"
            self._client.delete(key)
            self._client.srem('packages:all', package_id)
            if pkg.get('status'):
                self._client.srem(f"packages:status:{pkg.get('status')}", package_id)
            return True
        return False

    def save_return_record(self, package_id: str, return_data: Dict,
                          analyzed_result: Dict, write_back_cmd: Dict) -> bool:
        """保存回传记录"""
        self._check_connection()
        key = f"return:{package_id}"
        record = {
            'package_id': package_id,
            'return_data': return_data,
            'analyzed_result': analyzed_result,
            'write_back_cmd': write_back_cmd,
            'returned_at': datetime.now().isoformat()
        }
        self._client.set(key, json.dumps(record, ensure_ascii=False))
        return True

    def log_sync(self, action: str, package_id: str = None, detail: str = None):
        """记录同步日志"""
        self._check_connection()
        key = f"log:{datetime.now().strftime('%Y%m%d%H%M%S')}"
        log = {'action': action, 'package_id': package_id, 'detail': detail}
        self._client.lpush('logs:sync', json.dumps(log, ensure_ascii=False))

    def health_check(self) -> Dict:
        """健康检查"""
        if not self._redis_available:
            return {
                'status': 'not_connected',
                'storage': 'redis',
                'message': 'Redis未连接或不可用'
            }

        try:
            info = self._client.info()
            return {
                'status': 'healthy',
                'storage': 'redis',
                'redis_version': info.get('redis_version'),
                'connected_clients': info.get('connected_clients')
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'storage': 'redis',
                'error': str(e)
            }

    # ========== 调度指令 ==========

    def save_dispatch_command(self, command: Dict) -> bool:
        """保存调度指令"""
        self._check_connection()
        command_id = command.get('id', '')
        key = f"dispatch_command:{command_id}"
        if 'created_at' not in command:
            command['created_at'] = datetime.now().isoformat()
        command['updated_at'] = datetime.now().isoformat()
        self._client.set(key, json.dumps(command, ensure_ascii=False, default=str))
        self._client.sadd('dispatch_commands:all', command_id)
        if command.get('status'):
            self._client.sadd(f"dispatch_commands:status:{command['status']}", command_id)
        if command.get('target_type'):
            self._client.sadd(f"dispatch_commands:type:{command['target_type']}", command_id)
        return True

    def get_dispatch_command(self, command_id: str) -> Optional[Dict]:
        """获取调度指令"""
        self._check_connection()
        key = f"dispatch_command:{command_id}"
        data = self._client.get(key)
        return json.loads(data) if data else None

    def get_dispatch_commands(self, status: str = None, target_type: str = None,
                              operator: str = None, limit: int = 100) -> List[Dict]:
        """获取调度指令列表"""
        self._check_connection()
        if status:
            command_ids = self._client.smembers(f"dispatch_commands:status:{status}")
        elif target_type:
            command_ids = self._client.smembers(f"dispatch_commands:type:{target_type}")
        else:
            command_ids = self._client.smembers('dispatch_commands:all')
        commands = []
        for cid in list(command_ids)[:limit]:
            cmd = self.get_dispatch_command(cid)
            if cmd:
                if operator and cmd.get('operator') != operator:
                    continue
                if target_type and status and cmd.get('target_type') != target_type:
                    continue
                commands.append(cmd)
        return commands

    def update_dispatch_command_status(self, command_id: str, status: str,
                                       result: str = None, error: str = None) -> bool:
        """更新调度指令状态"""
        cmd = self.get_dispatch_command(command_id)
        if not cmd:
            return False
        old_status = cmd.get('status')
        cmd['status'] = status
        cmd['updated_at'] = datetime.now().isoformat()
        if result is not None:
            cmd['result'] = result
        if error is not None:
            cmd['error'] = error
        self._client.set(
            f"dispatch_command:{command_id}",
            json.dumps(cmd, ensure_ascii=False, default=str)
        )
        if old_status and old_status != status:
            self._client.srem(f"dispatch_commands:status:{old_status}", command_id)
        self._client.sadd(f"dispatch_commands:status:{status}", command_id)
        return True

    def get_all_dispatch_commands(self) -> List[Dict]:
        """获取所有调度指令"""
        self._check_connection()
        command_ids = self._client.smembers('dispatch_commands:all')
        commands = []
        for cid in command_ids:
            cmd = self.get_dispatch_command(cid)
            if cmd:
                commands.append(cmd)
        return commands

    def get_dispatch_commands_by_order_process(self, order_no: str, process_name: str) -> List[Dict]:
        self._check_connection()
        results = []
        command_ids = self._client.smembers('dispatch_commands:all')
        for cid in command_ids:
            cmd = self.get_dispatch_command(cid)
            if cmd and cmd.get('order_no') == order_no and cmd.get('process_name') == process_name:
                results.append(cmd)
        results.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return results

    def delete_dispatch_command(self, command_id: str) -> bool:
        self._check_connection()
        key = f"dispatch_command:{command_id}"
        if not self._client.exists(key):
            return False
        cmd = self.get_dispatch_command(command_id)
        old_status = cmd.get('status') if cmd else None
        old_target_type = cmd.get('target_type') if cmd else None
        self._client.delete(key)
        self._client.srem('dispatch_commands:all', command_id)
        if old_status:
            self._client.srem(f"dispatch_commands:status:{old_status}", command_id)
        if old_target_type:
            self._client.srem(f"dispatch_commands:type:{old_target_type}", command_id)
        return True

    def dedup_dispatch_commands(self) -> int:
        self._check_connection()
        groups = {}
        command_ids = self._client.smembers('dispatch_commands:all')
        for cid in command_ids:
            cmd = self.get_dispatch_command(cid)
            if cmd:
                key = (cmd.get('order_no'), cmd.get('process_name'))
                if key[0] and key[1]:
                    groups.setdefault(key, []).append(cid)
        deleted = 0
        for key, ids in groups.items():
            if len(ids) > 1:
                ids_to_delete = ids[1:]
                for cid in ids_to_delete:
                    self.delete_dispatch_command(cid)
                deleted += len(ids_to_delete)
        return deleted

    # ========== 数据流转记录 ==========

    def save_data_flow_log(self, flow_log: Dict) -> bool:
        """保存数据流转记录"""
        self._check_connection()
        flow_id = flow_log.get('id', '')
        key = f"data_flow_log:{flow_id}"
        if 'created_at' not in flow_log:
            flow_log['created_at'] = datetime.now().isoformat()
        self._client.set(key, json.dumps(flow_log, ensure_ascii=False, default=str))
        self._client.sadd('data_flow_logs:all', flow_id)
        if flow_log.get('order_no'):
            self._client.sadd(f"data_flow_logs:order:{flow_log['order_no']}", flow_id)
        if flow_log.get('event_type'):
            self._client.sadd(f"data_flow_logs:event:{flow_log['event_type']}", flow_id)
        return True

    def get_data_flow_logs(self, flow_id: str = None, event_type: str = None,
                           order_no: str = None, limit: int = 100) -> List[Dict]:
        """获取数据流转记录"""
        self._check_connection()
        if order_no:
            log_ids = self._client.smembers(f"data_flow_logs:order:{order_no}")
        elif event_type:
            log_ids = self._client.smembers(f"data_flow_logs:event:{event_type}")
        else:
            log_ids = self._client.smembers('data_flow_logs:all')
        logs = []
        for lid in list(log_ids)[:limit]:
            data = self._client.get(f"data_flow_log:{lid}")
            if data:
                log = json.loads(data)
                if flow_id and log.get('flow_id') != flow_id:
                    continue
                logs.append(log)
        return logs

    def get_all_data_flow_logs(self) -> List[Dict]:
        """获取所有数据流转记录"""
        self._check_connection()
        log_ids = self._client.smembers('data_flow_logs:all')
        logs = []
        for lid in log_ids:
            data = self._client.get(f"data_flow_log:{lid}")
            if data:
                logs.append(json.loads(data))
        return logs

    # ========== 数据收集记录 ==========

    def save_collection_record(self, record: Dict) -> bool:
        """保存数据收集记录"""
        self._check_connection()
        collect_id = record.get('id', '')
        key = f"collection_record:{collect_id}"
        if 'created_at' not in record:
            record['created_at'] = datetime.now().isoformat()
        record['updated_at'] = datetime.now().isoformat()
        self._client.set(key, json.dumps(record, ensure_ascii=False, default=str))
        self._client.sadd('collection_records:all', collect_id)
        if record.get('status'):
            self._client.sadd(f"collection_records:status:{record['status']}", collect_id)
        if record.get('data_type'):
            self._client.sadd(f"collection_records:type:{record['data_type']}", collect_id)
        if record.get('order_no'):
            self._client.sadd(f"collection_records:order:{record['order_no']}", collect_id)
        return True

    def get_collection_record(self, collect_id: str) -> Optional[Dict]:
        """获取数据收集记录"""
        self._check_connection()
        key = f"collection_record:{collect_id}"
        data = self._client.get(key)
        return json.loads(data) if data else None

    def get_collection_records(self, data_type: str = None, status: str = None,
                               order_no: str = None, limit: int = 100) -> List[Dict]:
        """获取数据收集记录列表"""
        self._check_connection()
        if order_no:
            record_ids = self._client.smembers(f"collection_records:order:{order_no}")
        elif status:
            record_ids = self._client.smembers(f"collection_records:status:{status}")
        elif data_type:
            record_ids = self._client.smembers(f"collection_records:type:{data_type}")
        else:
            record_ids = self._client.smembers('collection_records:all')
        records = []
        for rid in list(record_ids)[:limit]:
            rec = self.get_collection_record(rid)
            if rec:
                if data_type and rec.get('data_type') != data_type:
                    continue
                if status and rec.get('status') != status:
                    continue
                if order_no and rec.get('order_no') != order_no:
                    continue
                records.append(rec)
        return records

    def update_collection_record_status(self, collect_id: str, status: str,
                                        package_id: str = None, error: str = None) -> bool:
        """更新数据收集记录状态"""
        rec = self.get_collection_record(collect_id)
        if not rec:
            return False
        old_status = rec.get('status')
        rec['status'] = status
        rec['updated_at'] = datetime.now().isoformat()
        if package_id is not None:
            rec['package_id'] = package_id
        if error is not None:
            rec['error'] = error
        self._client.set(
            f"collection_record:{collect_id}",
            json.dumps(rec, ensure_ascii=False, default=str)
        )
        if old_status and old_status != status:
            self._client.srem(f"collection_records:status:{old_status}", collect_id)
        self._client.sadd(f"collection_records:status:{status}", collect_id)
        return True

    def get_all_collection_records(self) -> List[Dict]:
        """获取所有数据收集记录"""
        self._check_connection()
        record_ids = self._client.smembers('collection_records:all')
        records = []
        for rid in record_ids:
            rec = self.get_collection_record(rid)
            if rec:
                records.append(rec)
        return records

    # ========== 排产记录 ==========

    def save_schedule_record(self, record: Dict) -> bool:
        """保存排产记录"""
        self._check_connection()
        schedule_id = record.get('id', '')
        key = f"schedule_record:{schedule_id}"
        if 'created_at' not in record:
            record['created_at'] = datetime.now().isoformat()
        record['updated_at'] = datetime.now().isoformat()
        self._client.set(key, json.dumps(record, ensure_ascii=False, default=str))
        self._client.sadd('schedule_records:all', schedule_id)
        if record.get('status'):
            self._client.sadd(f"schedule_records:status:{record['status']}", schedule_id)
        if record.get('order_no'):
            self._client.sadd(f"schedule_records:order:{record['order_no']}", schedule_id)
        return True

    def get_schedule_record(self, schedule_id: str) -> Optional[Dict]:
        """获取排产记录"""
        self._check_connection()
        key = f"schedule_record:{schedule_id}"
        data = self._client.get(key)
        return json.loads(data) if data else None

    def get_schedule_record_by_order(self, order_no: str) -> Optional[Dict]:
        """根据订单号获取排产记录"""
        self._check_connection()
        record_ids = self._client.smembers(f"schedule_records:order:{order_no}")
        for rid in record_ids:
            rec = self.get_schedule_record(rid)
            if rec:
                return rec
        return None

    def get_schedule_records(self, status: str = None, limit: int = 100) -> List[Dict]:
        """获取排产记录列表"""
        self._check_connection()
        if status:
            record_ids = self._client.smembers(f"schedule_records:status:{status}")
        else:
            record_ids = self._client.smembers('schedule_records:all')
        records = []
        for rid in list(record_ids)[:limit]:
            rec = self.get_schedule_record(rid)
            if rec:
                records.append(rec)
        return records

    def get_all_schedule_records(self) -> List[Dict]:
        """获取所有排产记录"""
        self._check_connection()
        record_ids = self._client.smembers('schedule_records:all')
        records = []
        for rid in record_ids:
            rec = self.get_schedule_record(rid)
            if rec:
                records.append(rec)
        return records

    def save_process_record(self, record: Dict) -> bool:
        self._check_connection()
        record_id = record.get('id', '')
        key = f"process:{record_id}"
        self._client.set(key, json.dumps(record, ensure_ascii=False, default=str))
        self._client.sadd('processes:all', record_id)
        return True

    def get_process_record(self, record_id: str) -> Optional[Dict]:
        self._check_connection()
        key = f"process:{record_id}"
        data = self._client.get(key)
        return json.loads(data) if data else None

    def get_process_record_by_order(self, order_no: str) -> Optional[Dict]:
        all_records = self.get_all_process_records()
        for r in all_records:
            if r.get('order_no') == order_no:
                return r
        return None

    def get_process_records(self, status: str = None, process_type: str = None,
                           search: str = None, limit: int = 100) -> List[Dict]:
        all_records = self.get_all_process_records()
        result = []
        for r in all_records:
            if status and r.get('status') != status:
                continue
            if process_type and r.get('process_type') != process_type:
                continue
            if search:
                fields = [r.get('order_no', ''), r.get('order_no', ''),
                         r.get('product_name', ''), r.get('customer_name', '')]
                if not any(search.lower() in f.lower() for f in fields if f):
                    continue
            result.append(r)
            if len(result) >= limit:
                break
        return result

    def get_all_process_records(self) -> List[Dict]:
        self._check_connection()
        record_ids = self._client.smembers('processes:all')
        records = []
        for rid in record_ids:
            record = self.get_process_record(rid)
            if record:
                records.append(record)
        return records

    def update_process_record_status(self, record_id: str, status: str,
                                    completed_at: str = None, completed_by: str = None) -> bool:
        record = self.get_process_record(record_id)
        if not record:
            return False
        record['status'] = status
        record['updated_at'] = datetime.now().isoformat()
        if completed_at:
            record['completed_at'] = completed_at
        if completed_by:
            record['completed_by'] = completed_by
        return self.save_process_record(record)

    def update_process_record_step(self, record_id: str, current_step: int, expected_step: Optional[int] = None) -> bool:
        record = self.get_process_record(record_id)
        if not record:
            return False
        if expected_step is not None and record.get('current_step') != expected_step:
            logger.warning('乐观锁冲突(Redis): process=%s 期望current_step=%s 实际current_step=%s',
                           record_id, expected_step, record.get('current_step'))
            return False
        record['current_step'] = current_step
        record['updated_at'] = datetime.now().isoformat()
        return self.save_process_record(record)

    def update_process_record_task_count(self, record_id: str, task_count: int,
                                        completed_task_count: int) -> bool:
        record = self.get_process_record(record_id)
        if not record:
            return False
        record['task_count'] = task_count
        record['completed_task_count'] = completed_task_count
        record['updated_at'] = datetime.now().isoformat()
        return self.save_process_record(record)

    def delete_process_record(self, record_id: str) -> bool:
        self._check_connection()
        key = f"process:{record_id}"
        self._client.delete(key)
        self._client.srem('processes:all', record_id)
        return True

    def assign_template_to_process(self, record_id: str, template_id: str) -> bool:
        record = self.get_process_record(record_id)
        if not record:
            return False
        record['template_id'] = template_id
        record['updated_at'] = datetime.now().isoformat()
        return self.save_process_record(record)

    # ========== 排产流程日志 ==========

    def log_schedule_flow(self, order_no: str, event_type: str, event_data: Dict, operator: str = None) -> bool:
        """记录排产流程日志"""
        self._check_connection()
        log_id = f"{order_no}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        key = f"schedule_flow_log:{log_id}"
        log_entry = {
            'id': log_id,
            'order_no': order_no,
            'event_type': event_type,
            'event_data': event_data,
            'operator': operator or '',
            'created_at': datetime.now().isoformat()
        }
        self._client.set(key, json.dumps(log_entry, ensure_ascii=False, default=str))
        self._client.sadd(f"schedule_flow_logs:order:{order_no}", log_id)
        self._client.sadd('schedule_flow_logs:all', log_id)
        return True

    def get_schedule_flow_logs(self, order_no: str) -> List[Dict]:
        """获取排产流程日志"""
        self._check_connection()
        log_ids = self._client.smembers(f"schedule_flow_logs:order:{order_no}")
        logs = []
        for lid in log_ids:
            data = self._client.get(f"schedule_flow_log:{lid}")
            if data:
                logs.append(json.loads(data))
        logs.sort(key=lambda x: x.get('created_at', ''))
        return logs

    # ========== 子步骤记录（分批入库/发货） ==========

    def save_sub_step(self, record: Dict) -> bool:
        """保存子步骤记录（分批入库/发货）"""
        self._check_connection()
        step_id = record.get('id', '')
        key = f"sub_step:{step_id}"
        if 'created_at' not in record:
            record['created_at'] = datetime.now().isoformat()
        record['updated_at'] = datetime.now().isoformat()
        self._client.set(key, json.dumps(record, ensure_ascii=False, default=str))
        if record.get('process_id'):
            self._client.sadd(f"sub_steps:order:{record['process_id']}", step_id)
        self._client.sadd('sub_steps:all', step_id)
        return True

    def get_sub_steps_by_process(self, order_no: str) -> List[Dict]:
        """获取流程的所有子步骤"""
        self._check_connection()
        step_ids = self._client.smembers(f"sub_steps:process:{process_id}")
        steps = []
        for sid in step_ids:
            data = self._client.get(f"sub_step:{sid}")
            if data:
                steps.append(json.loads(data))
        steps.sort(key=lambda x: x.get('created_at', ''))
        return steps

    def get_sub_step_summary(self, order_no: str) -> Dict:
        """获取子步骤汇总（累计入库/发货量等）"""
        self._check_connection()
        steps = self.get_sub_steps_by_process(process_id)
        total_quantity = 0
        total_amount = 0
        step_count = len(steps)
        for s in steps:
            total_quantity += s.get('quantity', 0) or 0
            total_amount += s.get('amount', 0) or 0
        return {
            'process_id': process_id,
            'total_steps': step_count,
            'total_quantity': total_quantity,
            'total_amount': total_amount,
            'last_step_at': steps[-1].get('created_at') if steps else None
        }

    def save_order_cost(self, cost: Dict) -> bool:
        self._check_connection()
        key = f"order_cost:{cost['order_no']}"
        self._client.set(key, json.dumps(cost, ensure_ascii=False, default=str))
        self._client.sadd('order_costs:all', cost['order_no'])
        return True

    def get_order_cost(self, order_no: str) -> Optional[Dict]:
        self._check_connection()
        data = self._client.get(f"order_cost:{order_no}")
        return json.loads(data) if data else None

    def get_all_order_costs(self, status: str = None, search: str = None,
                           sort_by: str = 'order_no', sort_order: str = 'asc',
                           limit: int = 100, offset: int = 0) -> List[Dict]:
        self._check_connection()
        order_nos = list(self._client.smembers('order_costs:all'))
        results = []
        for on in order_nos:
            cost = self.get_order_cost(on)
            if cost:
                if status and cost.get('status') != status:
                    continue
                if search and search.lower() not in (cost.get('order_no', '') or '').lower() \
                        and search.lower() not in (cost.get('customer_name', '') or '').lower():
                    continue
                results.append(cost)
        reverse = sort_order.lower() == 'desc'
        results.sort(key=lambda x: x.get(sort_by, ''), reverse=reverse)
        return results[offset:offset + limit]

    def count_order_costs(self, status: str = None, search: str = None) -> int:
        return len(self.get_all_order_costs(status=status, search=search))

    def delete_order_cost(self, order_no: str) -> bool:
        self._check_connection()
        self._client.delete(f"order_cost:{order_no}")
        self._client.srem('order_costs:all', order_no)
        return True

    def save_order_cost_detail(self, detail: Dict) -> bool:
        self._check_connection()
        detail_id = self._client.incr('order_cost_detail_id')
        key = f"order_cost_detail:{detail_id}"
        detail['id'] = detail_id
        self._client.set(key, json.dumps(detail, ensure_ascii=False, default=str))
        self._client.sadd(f"order_cost_details:{detail['order_no']}", detail_id)
        return True

    def get_order_cost_details(self, order_no: str) -> List[Dict]:
        self._check_connection()
        detail_ids = self._client.smembers(f"order_cost_details:{order_no}")
        results = []
        for did in detail_ids:
            data = self._client.get(f"order_cost_detail:{did}")
            if data:
                results.append(json.loads(data))
        results.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return results

    def delete_order_cost_detail(self, detail_id: int) -> bool:
        self._check_connection()
        key = f"order_cost_detail:{detail_id}"
        data = self._client.get(key)
        if data:
            detail = json.loads(data)
            self._client.srem(f"order_cost_details:{detail.get('order_no', '')}", detail_id)
            self._client.delete(key)
            return True
        return False

    def get_cost_summary(self) -> Dict:
        self._check_connection()
        order_nos = list(self._client.smembers('order_costs:all'))
        if not order_nos:
            return {'total_orders': 0, 'total_revenue': 0, 'total_cost': 0, 'total_profit': 0}
        total_revenue = 0
        total_cost = 0
        loss_count = 0
        confirmed_count = 0
        draft_count = 0
        margins = []
        for on in order_nos:
            cost = self.get_order_cost(on)
            if cost:
                total_revenue += cost.get('revenue', 0)
                total_cost += cost.get('total_cost', 0)
                if cost.get('profit', 0) < 0:
                    loss_count += 1
                if cost.get('status') == 'confirmed':
                    confirmed_count += 1
                elif cost.get('status') == 'draft':
                    draft_count += 1
                margins.append(cost.get('margin_rate', 0))
        return {
            'total_orders': len(order_nos),
            'total_revenue': total_revenue,
            'total_cost': total_cost,
            'total_profit': total_revenue - total_cost,
            'avg_margin_rate': round(sum(margins) / len(margins), 2) if margins else 0,
            'loss_count': loss_count,
            'confirmed_count': confirmed_count,
            'draft_count': draft_count,
        }

    def get_material_unit_price(self, material_name: str) -> Optional[float]:
        self._check_connection()
        data = self._client.get(f"material_price:{material_name}")
        if data:
            return json.loads(data).get('unit_price')
        return None

    def save_material_unit_price(self, material_name: str, unit_price: float, unit: str = '个') -> bool:
        self._check_connection()
        self._client.set(f"material_price:{material_name}",
                        json.dumps({'unit_price': unit_price, 'unit': unit}, ensure_ascii=False))
        return True

    def get_all_material_prices(self) -> List[Dict]:
        self._check_connection()
        keys = self._client.keys('material_price:*')
        results = []
        for k in keys:
            name = k.decode().split(':', 1)[1]
            data = self._client.get(k)
            if data:
                results.append({'material_name': name, **json.loads(data)})
        return results

    def get_labor_unit_price(self, process_name: str) -> Optional[float]:
        self._check_connection()
        data = self._client.get(f"labor_price:{process_name}")
        if data:
            return json.loads(data).get('unit_price')
        return None

    def save_labor_unit_price(self, process_name: str, unit_price: float, unit: str = '米') -> bool:
        self._check_connection()
        self._client.set(f"labor_price:{process_name}",
                        json.dumps({'unit_price': unit_price, 'unit': unit}, ensure_ascii=False))
        return True

    def get_all_labor_prices(self) -> List[Dict]:
        self._check_connection()
        keys = self._client.keys('labor_price:*')
        results = []
        for k in keys:
            name = k.decode().split(':', 1)[1]
            data = self._client.get(k)
            if data:
                results.append({'process_name': name, **json.loads(data)})
        return results


class MemoryStorage(BaseStorage):
    """
    内存存储后端
    仅用于开发测试，重启后数据丢失
    """

    def __init__(self):
        self._packages: Dict[str, Dict] = {}
        self._logs: List[Dict] = []
        self._processes: Dict[str, Dict] = {}
        self._dispatch_commands: Dict[str, Dict] = {}
        self._data_flow_logs: List[Dict] = []
        self._collection_records: Dict[str, Dict] = {}
        self._schedule_records: Dict[str, Dict] = {}
        self._schedule_flow_logs: List[Dict] = []
        self._sub_steps: List[Dict] = []
        self._order_costs: Dict[str, Dict] = {}
        self._order_cost_details: List[Dict] = []
        self._material_prices: Dict[str, Dict] = {}
        self._labor_prices: Dict[str, Dict] = {}
        # [F6 P8 2026-06-10] 补 _sync_logs 列表, 兼容 TestSyncLog.hasattr(_sync_logs) 检查
        self._sync_logs: List[Dict] = []
        # [F6 P8 2026-06-10] 补 _conn 占位, 兼容 SQLiteStorage 时代 TestConnection 断言
        # 内存版 connect 后为占位对象, disconnect 后 None
        self._conn = None

    def connect(self) -> bool:
        logger.info("内存存储已创建（开发测试用，重启后数据丢失）")
        self._conn = True  # 内存版无真实连接, 占位
        return True

    def disconnect(self):
        self._packages.clear()
        self._logs.clear()
        self._processes.clear()
        self._dispatch_commands.clear()
        self._data_flow_logs.clear()
        self._collection_records.clear()
        self._schedule_records.clear()
        self._schedule_flow_logs.clear()
        self._sub_steps.clear()
        self._order_costs.clear()
        self._order_cost_details.clear()
        self._material_prices.clear()
        self._labor_prices.clear()
        # [F6 P8 2026-06-10] 同步清空 _sync_logs + _conn
        self._sync_logs.clear()
        self._conn = None
        logger.info("内存存储已清空")

    def save_package(self, package: Dict) -> bool:
        self._packages[package.get('id')] = package
        return True

    def get_package(self, package_id: str) -> Optional[Dict]:
        return self._packages.get(package_id)

    def get_packages(self, status: str = None, data_type: str = None,
                    operator: str = None, limit: int = 100) -> List[Dict]:
        results = list(self._packages.values())

        if status:
            results = [p for p in results if p.get('status') == status]
        if data_type:
            results = [p for p in results if p.get('data_type') == data_type]
        if operator:
            results = [p for p in results if p.get('target_operator') == operator]

        results.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return results[:limit]

    def update_package_status(self, package_id: str, status: str,
                            completed_at: datetime = None) -> bool:
        if package_id in self._packages:
            self._packages[package_id]['status'] = status
            if completed_at:
                self._packages[package_id]['completed_at'] = completed_at.isoformat()
            return True
        return False

    def delete_package(self, package_id: str) -> bool:
        if package_id in self._packages:
            del self._packages[package_id]
            return True
        return False

    def save_return_record(self, package_id: str, return_data: Dict,
                          analyzed_result: Dict, write_back_cmd: Dict) -> bool:
        return True

    def log_sync(self, action: str, package_id: str = None, detail: str = None):
        entry = {
            'action': action,
            'package_id': package_id,
            'detail': detail,
            'created_at': datetime.now().isoformat()
        }
        self._logs.append(entry)
        # [F6 P8 2026-06-10] 同时写 _sync_logs, 兼容 TestSyncLog.hasattr(_sync_logs) 检查
        self._sync_logs.append(entry)

    def get_sync_logs(self, limit: int = 100, package_id: str = None) -> List[Dict]:
        # [F6 P8 2026-06-10] 补 get_sync_logs, TestSyncLog fallback 走此接口
        results = list(self._sync_logs)
        if package_id:
            results = [l for l in results if l.get('package_id') == package_id]
        return results[:limit]

    def health_check(self) -> Dict:
        return {
            'status': 'healthy',
            'storage': 'memory',
            'total_packages': len(self._packages)
        }

    def save_process_record(self, record: Dict) -> bool:
        self._processes[record.get('id', '')] = record
        return True

    def get_process_record(self, record_id: str) -> Optional[Dict]:
        return self._processes.get(record_id)

    def get_process_record_by_order(self, order_no: str) -> Optional[Dict]:
        for r in self._processes.values():
            if r.get('order_no') == order_no:
                return r
        return None

    def get_process_records(self, status: str = None, process_type: str = None,
                           search: str = None, limit: int = 100) -> List[Dict]:
        results = list(self._processes.values())
        if status:
            results = [r for r in results if r.get('status') == status]
        if process_type:
            results = [r for r in results if r.get('process_type') == process_type]
        if search:
            results = [r for r in results if search in (r.get('order_no', '') or '') or
                      search in (r.get('order_no', '') or '') or
                      search in (r.get('product_name', '') or '')]
        results.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return results[:limit]

    def get_all_process_records(self) -> List[Dict]:
        return list(self._processes.values())

    def update_process_record_status(self, record_id: str, status: str,
                                    completed_at: str = None, completed_by: str = None) -> bool:
        if record_id not in self._processes:
            return False
        self._processes[record_id]['status'] = status
        self._processes[record_id]['updated_at'] = datetime.now().isoformat()
        if completed_at:
            self._processes[record_id]['completed_at'] = completed_at
        if completed_by:
            self._processes[record_id]['completed_by'] = completed_by
        return True

    def update_process_record_step(self, record_id: str, current_step: int, expected_step: Optional[int] = None) -> bool:
        if record_id not in self._processes:
            return False
        if expected_step is not None and self._processes[record_id].get('current_step') != expected_step:
            logger.warning('乐观锁冲突(Memory): process=%s 期望current_step=%s 实际current_step=%s',
                           record_id, expected_step, self._processes[record_id].get('current_step'))
            return False
        self._processes[record_id]['current_step'] = current_step
        self._processes[record_id]['updated_at'] = datetime.now().isoformat()
        return True

    def update_process_record_task_count(self, record_id: str, task_count: int,
                                        completed_task_count: int) -> bool:
        if record_id not in self._processes:
            return False
        self._processes[record_id]['task_count'] = task_count
        self._processes[record_id]['completed_task_count'] = completed_task_count
        self._processes[record_id]['updated_at'] = datetime.now().isoformat()
        return True

    def delete_process_record(self, record_id: str) -> bool:
        if record_id in self._processes:
            del self._processes[record_id]
            return True
        return False

    def assign_template_to_process(self, record_id: str, template_id: str) -> bool:
        if record_id not in self._processes:
            return False
        self._processes[record_id]['template_id'] = template_id
        self._processes[record_id]['updated_at'] = datetime.now().isoformat()
        return True

    # ==================== dispatch 组 ====================

    def save_dispatch_command(self, command: Dict) -> bool:
        """保存调度指令"""
        self._dispatch_commands[command['command_id']] = command
        return True

    def get_dispatch_command(self, command_id: str) -> Optional[Dict]:
        """获取调度指令"""
        return self._dispatch_commands.get(command_id)

    def get_dispatch_commands(self, status: str = None, target_type: str = None,
                            operator: str = None, limit: int = 100) -> List[Dict]:
        """获取调度指令列表"""
        results = list(self._dispatch_commands.values())
        if status:
            results = [c for c in results if c.get('status') == status]
        if target_type:
            results = [c for c in results if c.get('target_type') == target_type]
        if operator:
            results = [c for c in results if c.get('operator_id') == operator]
        results.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return results[:limit]

    def update_dispatch_command_status(self, command_id: str, status: str,
                                      result: str = None, error: str = None) -> bool:
        """更新调度指令状态"""
        if command_id not in self._dispatch_commands:
            return False
        self._dispatch_commands[command_id]['status'] = status
        if result:
            self._dispatch_commands[command_id]['result'] = result
        if error:
            self._dispatch_commands[command_id]['error_message'] = error
        return True

    def get_all_dispatch_commands(self) -> List[Dict]:
        """获取所有调度指令"""
        results = list(self._dispatch_commands.values())
        results.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return results

    def get_dispatch_commands_by_order_process(self, order_no: str, process_name: str) -> List[Dict]:
        results = []
        for cmd in self._dispatch_commands.values():
            if cmd.get('order_no') == order_no and cmd.get('process_name') == process_name:
                results.append(cmd)
        results.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return results

    def delete_dispatch_command(self, command_id: str) -> bool:
        if command_id in self._dispatch_commands:
            del self._dispatch_commands[command_id]
            return True
        return False

    def dedup_dispatch_commands(self) -> int:
        groups = {}
        for cid, cmd in self._dispatch_commands.items():
            key = (cmd.get('order_no'), cmd.get('process_name'))
            if key[0] and key[1]:
                groups.setdefault(key, []).append(cid)
        deleted = 0
        for key, ids in groups.items():
            if len(ids) > 1:
                for cid in ids[1:]:
                    del self._dispatch_commands[cid]
                deleted += len(ids) - 1
        return deleted

    # ==================== data_flow 组 ====================

    def save_data_flow_log(self, flow_log: Dict) -> bool:
        """保存数据流转记录"""
        self._data_flow_logs.append(flow_log)
        return True

    def get_data_flow_logs(self, flow_id: str = None, event_type: str = None,
                          order_no: str = None, limit: int = 100) -> List[Dict]:
        """获取数据流转记录"""
        results = list(self._data_flow_logs)
        if flow_id:
            results = [r for r in results if r.get('flow_id') == flow_id]
        if event_type:
            results = [r for r in results if r.get('event_type') == event_type]
        if order_no:
            results = [r for r in results if r.get('order_no') == order_no]
        results.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return results[:limit]

    def get_all_data_flow_logs(self) -> List[Dict]:
        """获取所有数据流转记录"""
        results = list(self._data_flow_logs)
        results.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return results

    # ==================== collection 组 ====================

    def save_collection_record(self, record: Dict) -> bool:
        """保存数据收集记录"""
        self._collection_records[record['collect_id']] = record
        return True

    def get_collection_record(self, collect_id: str) -> Optional[Dict]:
        """获取数据收集记录"""
        return self._collection_records.get(collect_id)

    def get_collection_records(self, data_type: str = None, status: str = None,
                             order_no: str = None, limit: int = 100) -> List[Dict]:
        """获取数据收集记录列表"""
        results = list(self._collection_records.values())
        if data_type:
            results = [r for r in results if r.get('data_type') == data_type]
        if status:
            results = [r for r in results if r.get('status') == status]
        if order_no:
            results = [r for r in results if r.get('order_no') == order_no]
        results.sort(key=lambda x: x.get('collected_at', ''), reverse=True)
        return results[:limit]

    def update_collection_record_status(self, collect_id: str, status: str,
                                       package_id: str = None, error: str = None) -> bool:
        """更新数据收集记录状态"""
        if collect_id not in self._collection_records:
            return False
        self._collection_records[collect_id]['status'] = status
        if package_id:
            self._collection_records[collect_id]['package_id'] = package_id
        if error:
            self._collection_records[collect_id]['error_message'] = error
        return True

    def get_all_collection_records(self) -> List[Dict]:
        """获取所有数据收集记录"""
        results = list(self._collection_records.values())
        results.sort(key=lambda x: x.get('collected_at', ''), reverse=True)
        return results

    # ==================== schedule 组 ====================

    def save_schedule_record(self, record: Dict) -> bool:
        """保存排产记录"""
        self._schedule_records[record['schedule_id']] = record
        return True

    def get_schedule_record(self, schedule_id: str) -> Optional[Dict]:
        """获取排产记录"""
        return self._schedule_records.get(schedule_id)

    def get_schedule_record_by_order(self, order_no: str) -> Optional[Dict]:
        """根据订单号获取排产记录"""
        for r in self._schedule_records.values():
            if r.get('order_no') == order_no:
                return r
        return None

    def get_schedule_records(self, status: str = None, limit: int = 100) -> List[Dict]:
        """获取排产记录列表"""
        results = list(self._schedule_records.values())
        if status:
            results = [r for r in results if r.get('status') == status]
        results.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return results[:limit]

    def get_all_schedule_records(self) -> List[Dict]:
        """获取所有排产记录"""
        results = list(self._schedule_records.values())
        results.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return results

    # ==================== schedule_flow 组 ====================

    def log_schedule_flow(self, order_no: str, event_type: str, event_data: Dict, operator: str = None) -> bool:
        """记录排产流程日志"""
        self._schedule_flow_logs.append({
            'order_no': order_no,
            'event_type': event_type,
            'event_data': event_data,
            'operator': operator,
            'created_at': datetime.now().isoformat()
        })
        return True

    def get_schedule_flow_logs(self, order_no: str) -> List[Dict]:
        """获取排产流程日志"""
        results = [r for r in self._schedule_flow_logs if r.get('order_no') == order_no]
        results.sort(key=lambda x: x.get('created_at', ''))
        return results

    # ==================== sub_step 组 ====================

    def save_sub_step(self, record: Dict) -> bool:
        """保存子步骤记录（分批入库/发货）"""
        self._sub_steps.append(record)
        return True

    def get_sub_steps_by_process(self, order_no: str) -> List[Dict]:
        """获取流程的所有子步骤"""
        # [F6 P7 物理清理 2026-06-10] 修预存在 NameError: 原代码误用 'process_id'(未定义变量), 应为参数 'order_no'
        results = [s for s in self._sub_steps if s.get('order_no') == order_no]
        results.sort(key=lambda x: x.get('created_at', ''))
        return results

    def get_sub_step_summary(self, order_no: str) -> Dict:
        """获取子步骤汇总（累计入库/发货量等）"""
        # [F6 P7 物理清理 2026-06-10] 修预存在 NameError: 原代码 4 处 'process_id' 应为 'order_no'
        steps = [s for s in self._sub_steps if s.get('order_no') == order_no]
        completed_qty = sum(s.get('quantity', 0) for s in steps if s.get('step_name') == '完工入库')
        shipped_qty = sum(s.get('quantity', 0) for s in steps if s.get('step_name') == '发货')
        order_qty = 0
        for p in self._processes.values():
            if p.get('order_no') == order_no:
                order_qty = p.get('quantity', 0)
                break
        return {
            'order_qty': order_qty,
            'completed_qty': completed_qty,
            'shipped_qty': shipped_qty,
            'completed_remaining': max(0, order_qty - completed_qty),
            'shipped_remaining': max(0, order_qty - shipped_qty),
            'is_completed_done': completed_qty >= order_qty if order_qty > 0 else False,
            'is_shipped_done': shipped_qty >= order_qty if order_qty > 0 else False
        }

    # ==================== order_cost 组（移除 hasattr） ====================

    # [F6 P7 物理清理 2026-06-10] 补 3 个 SubStepMixin / ProcessStorageMixin 抽象方法的 stub
    # SQLiteStorage 已物理移除, MemoryStorage 之前漏实现这 3 个方法, 导致继承 BaseStorage 实例化失败

    def get_process_records_by_work_order(self, order_no: str) -> List[Dict]:
        """按工单号获取流程记录列表 (内存版)"""
        return [r for r in self._processes.values() if r.get('order_no') == order_no]

    def get_recent_sub_step(self, order_no: str, step_name: str,
                            operator: str, quantity: float,
                            seconds: int = 30) -> Optional[Dict]:
        """查最近 N 秒内同 (order_no, step_name, operator, quantity) 的子步骤 (内存版)
        用于创建时防重检查, 重启后数据丢失, 退化为返回 None
        """
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(seconds=seconds)
        for s in reversed(self._sub_steps):
            if (s.get('order_no') == order_no and s.get('step_name') == step_name
                    and s.get('operator') == operator
                    and abs(float(s.get('quantity', 0)) - float(quantity)) < 0.01):
                ts_str = s.get('created_at', '')
                try:
                    ts = datetime.fromisoformat(ts_str) if ts_str else None
                except (ValueError, TypeError):
                    ts = None
                if ts is None or ts >= cutoff:
                    return s
        return None

    def dedup_process_sub_steps(self) -> int:
        """清理 sub_steps 中完全重复的报工记录 (内存版, 按 process_id+step_name+operator+quantity 分组)"""
        seen = set()
        deduped = []
        deleted = 0
        for s in self._sub_steps:
            key = (s.get('process_id', ''), s.get('step_name', ''),
                   s.get('operator', ''), s.get('quantity', 0))
            if key in seen:
                deleted += 1
            else:
                seen.add(key)
                deduped.append(s)
        self._sub_steps = deduped
        return deleted

    def save_order_cost(self, cost: Dict) -> bool:
        """保存订单成本汇总"""
        self._order_costs[cost['order_no']] = {**cost, 'updated_at': datetime.now().isoformat()}
        return True

    def get_order_cost(self, order_no: str) -> Optional[Dict]:
        """获取订单成本汇总"""
        return self._order_costs.get(order_no)

    def get_all_order_costs(self, status: str = None, search: str = None,
                           sort_by: str = 'order_no', sort_order: str = 'asc',
                           limit: int = 100, offset: int = 0) -> List[Dict]:
        """获取订单成本列表，支持筛选和分页"""
        results = list(self._order_costs.values())
        if status:
            results = [r for r in results if r.get('status') == status]
        if search:
            results = [r for r in results if search.lower() in (r.get('order_no', '') or '').lower()
                      or search.lower() in (r.get('customer_name', '') or '').lower()]
        reverse = sort_order.lower() == 'desc'
        results.sort(key=lambda x: x.get(sort_by, ''), reverse=reverse)
        return results[offset:offset + limit]

    def count_order_costs(self, status: str = None, search: str = None) -> int:
        """统计订单成本数量"""
        return len(self.get_all_order_costs(status=status, search=search))

    def delete_order_cost(self, order_no: str) -> bool:
        """删除订单成本汇总"""
        if order_no in self._order_costs:
            del self._order_costs[order_no]
        self._order_cost_details = [d for d in self._order_cost_details if d['order_no'] != order_no]
        return True

    def save_order_cost_detail(self, detail: Dict) -> bool:
        """保存成本明细条目"""
        entry = {**detail, 'id': len(self._order_cost_details) + 1,
                 'created_at': detail.get('created_at', datetime.now().isoformat())}
        self._order_cost_details.append(entry)
        return True

    def get_order_cost_details(self, order_no: str) -> List[Dict]:
        """获取订单成本明细列表"""
        return [d for d in self._order_cost_details if d['order_no'] == order_no]

    def delete_order_cost_detail(self, detail_id: int) -> bool:
        """删除成本明细条目"""
        for i, d in enumerate(self._order_cost_details):
            if d['id'] == detail_id:
                self._order_cost_details.pop(i)
                return True
        return False

    def get_cost_summary(self) -> Dict:
        """获取成本汇总统计（总利润、总成本等）"""
        costs = list(self._order_costs.values())
        if not costs:
            return {'total_orders': 0, 'total_revenue': 0, 'total_cost': 0, 'total_profit': 0,
                    'avg_margin_rate': 0, 'loss_count': 0, 'confirmed_count': 0, 'draft_count': 0}
        total_revenue = sum(c.get('revenue', 0) for c in costs)
        total_cost = sum(c.get('total_cost', 0) for c in costs)
        return {
            'total_orders': len(costs),
            'total_revenue': total_revenue,
            'total_cost': total_cost,
            'total_profit': total_revenue - total_cost,
            'avg_margin_rate': round(sum(c.get('margin_rate', 0) for c in costs) / len(costs), 2) if costs else 0,
            'loss_count': sum(1 for c in costs if c.get('profit', 0) < 0),
            'confirmed_count': sum(1 for c in costs if c.get('status') == 'confirmed'),
            'draft_count': sum(1 for c in costs if c.get('status') == 'draft'),
        }

    def get_material_unit_price(self, material_name: str) -> Optional[float]:
        """获取物料单价"""
        entry = self._material_prices.get(material_name)
        return entry.get('unit_price') if entry else None

    def save_material_unit_price(self, material_name: str, unit_price: float,
                                 unit: str = '个') -> bool:
        """保存/更新物料单价"""
        self._material_prices[material_name] = {'unit_price': unit_price, 'unit': unit}
        return True

    def get_all_material_prices(self) -> List[Dict]:
        """获取所有物料单价"""
        return [{'material_name': k, **v} for k, v in self._material_prices.items()]

    def get_labor_unit_price(self, process_name: str) -> Optional[float]:
        """获取工序工时单价"""
        entry = self._labor_prices.get(process_name)
        return entry.get('unit_price') if entry else None

    def save_labor_unit_price(self, process_name: str, unit_price: float,
                              unit: str = '米') -> bool:
        """保存/更新工序工时单价"""
        self._labor_prices[process_name] = {'unit_price': unit_price, 'unit': unit}
        return True

    def get_all_labor_prices(self) -> List[Dict]:
        """获取所有工序单价"""
        return [{'process_name': k, **v} for k, v in self._labor_prices.items()]


def resolve_storage_type() -> 'StorageType':
    """根据环境变量决定默认存储类型。
    - 未设置 / CONTAINER_STORAGE_TYPE=mysql → MySQL（默认生产, v4.0 强制）
    - [F6 P7 物理清理 2026-06-10] SQLiteStorage 已物理移除, SQLite 分支废弃

    [审计项 N2 / 2026-06-10] 本函数 USE_SQLITE 默认 'false'（v4.0 强制 MySQL）,
    与 ``core/_config_infra.DatabaseConfig.USE_SQLITE`` 默认 'true' 不一致 —
    那是 DatabaseConfig 类的 SQLITE_DB_PATH 默认值兜底, 仅影响 .db 路径回退;
    真正决定存储后端的是本函数, 实际生产以本函数为准.
    """
    explicit = os.getenv('CONTAINER_STORAGE_TYPE', '').lower()
    if explicit == 'mysql':
        return StorageType.MYSQL
    # [F6 P7 物理清理 2026-06-10] SQLiteStorage 已物理移除, 显式配置 sqlite 直接报错
    if explicit == 'sqlite':
        raise ValueError('SQLiteStorage 已物理移除 [F6 P7 2026-06-10], 不再支持 CONTAINER_STORAGE_TYPE=sqlite')
    return StorageType.MYSQL  # 默认生产 v4.0 强制 MySQL


class StorageFactory:
    """
    存储工厂
    根据配置创建对应的存储后端
    """

    _instances: Dict[StorageType, BaseStorage] = {}

    @classmethod
    def create(cls, storage_type: StorageType = StorageType.MYSQL, **kwargs) -> BaseStorage:
        # [F6 P7 物理清理 2026-06-10] SQLiteStorage 已物理移除, 直接 raise
        if storage_type == StorageType.SQLITE:
            raise RuntimeError('SQLiteStorage 已物理移除 [F6 P7 2026-06-10], 不再支持 StorageType.SQLITE')

        elif storage_type == StorageType.REDIS:
            storage = RedisStorage(
                host=kwargs.get('redis_host', os.getenv('REDIS_HOST', 'localhost')),
                port=kwargs.get('redis_port', int(os.getenv('REDIS_PORT', '6379'))),
                db=kwargs.get('redis_db', 0),
                password=kwargs.get('redis_password')
            )
            if storage.connect():
                cls._instances[StorageType.REDIS] = storage
            else:
                # [F6 P7 物理清理 2026-06-10] Redis 失败回退改走 MySQL (而非 SQLite)
                logger.warning("Redis连接失败，回退到MySQL")
                return cls.create(StorageType.MYSQL, **kwargs)
            return storage

        elif storage_type == StorageType.MEMORY:
            storage = MemoryStorage()
            cls._instances[StorageType.MEMORY] = storage
            return storage

        elif storage_type == StorageType.MYSQL:
            from storage.mysql_storage import create_mysql_storage
            storage = create_mysql_storage()
            cls._instances[StorageType.MYSQL] = storage
            return storage

        else:
            raise ValueError(f"不支持的存储类型: {storage_type}")

    @classmethod
    def get_instance(cls, storage_type: StorageType) -> Optional[BaseStorage]:
        return cls._instances.get(storage_type)

    @classmethod
    def close_all(cls):
        for storage in cls._instances.values():
            storage.disconnect()
        cls._instances.clear()


def create_storage(config: Dict = None) -> BaseStorage:
    """
    创建存储后端的便捷函数

    配置示例：
    {
        'type': 'sqlite',  # sqlite, redis, memory, mysql
        'db_path': 'container_center.db'  # SQLite数据库路径
    }

    或 Redis配置：
    {
        'type': 'redis',
        'host': 'localhost',
        'port': 6379,
        'db': 0
    }

    注意：不传 config 或 config 未指定 type 时，默认使用 resolve_storage_type()
    根据 USE_SQLITE 环境变量自动选择 MySQL 或 SQLite。
    """
    if config is None:
        default_type = resolve_storage_type()
        return StorageFactory.create(default_type)

    storage_type = config.get('type', '').lower()
    if not storage_type:
        default_type = resolve_storage_type()
        return StorageFactory.create(default_type)

    if storage_type == 'sqlite':
        return StorageFactory.create(
            StorageType.SQLITE,
            db_path=config.get('db_path', os.getenv('CONTAINER_DB_PATH', DB_PATHS['container_center']))
        )
    elif storage_type == 'redis':
        return StorageFactory.create(
            StorageType.REDIS,
            redis_host=config.get('host', os.getenv('REDIS_HOST', 'localhost')),
            redis_port=config.get('port', int(os.getenv('REDIS_PORT', '6379'))),
            redis_db=config.get('db', 0),
            redis_password=config.get('password')
        )
    elif storage_type == 'memory':
        return StorageFactory.create(StorageType.MEMORY)
    elif storage_type == 'mysql':
        from storage.mysql_storage import create_mysql_storage
        return create_mysql_storage()
    else:
        raise ValueError(f"不支持的存储类型: {storage_type}")


if __name__ == '__main__':
    print("=" * 50)
    print("存储后端测试")
    print("=" * 50)

    print("\n[1] 测试SQLite存储...")
    storage = create_storage({'type': 'sqlite', 'db_path': 'test_storage.db'})
    print(f"健康检查: {storage.health_check()}")

    print("\n[2] 保存测试数据包...")
    test_pkg = {
        'id': 'TEST001',
        'data_type': 'report',
        'title': '测试报工',
        'content': {'record_id': 1, 'planned_qty': 100},
        'source': 'test',
        'priority': 'normal',
        'status': 'pending',
        'created_at': datetime.now().isoformat(),
        'target_operator': 'OP001',
        'related_order': 'ORD001'
    }
    storage.save_package(test_pkg)
    print("数据包已保存")

    print("\n[3] 查询数据包...")
    packages = storage.get_packages()
    print(f"查询到 {len(packages)} 个数据包")

    print("\n[4] 健康检查...")
    print(storage.health_check())

    storage.disconnect()

    print("\n" + "=" * 50)
    print("测试完成！")
