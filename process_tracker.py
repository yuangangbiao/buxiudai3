# -*- coding: utf-8 -*-
"""
工序追踪器 - Process Tracker

追踪订单在各工序的生产状态

使用方式：
    from process_tracker import ProcessTracker

    tracker = ProcessTracker()

    # 追踪工序状态
    tracker.track_process(
        order_no='ORD202604001',
        process_name='编织',
        status='in_progress',
        operator_id='OP001',
        operator_name='张三',
        quantity=100,
        completed_qty=50
    )

    # 查询订单所有工序
    processes = tracker.get_order_processes('ORD202604001')

    # 获取当前工序
    current = tracker.get_current_process('ORD202604001')
"""

import sys
import os
import logging
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

MOBILE_API_AI_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'mobile_api_ai')
if MOBILE_API_AI_PATH not in sys.path:
    sys.path.insert(0, MOBILE_API_AI_PATH)


class ProcessTracker:
    """
    工序追踪器

    职责：
        - 记录订单在各工序的生产状态
        - 查询订单工序历史
        - 获取当前进行中的工序
    """

    STATUS_PENDING = 'pending'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'

    VALID_STATUSES = [STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_COMPLETED]

    def __init__(self, db_path: Optional[str] = None):
        """
        初始化工序追踪器

        Args:
            db_path: 数据库路径，默认使用容器数据库
        """
        self._load_config()
        self._init_storage(db_path)
        self._ensure_table()

    def _load_config(self) -> None:
        """
        加载配置
        """
        try:
            from modular_config import ModularConfig
            config = ModularConfig()
            tracker_config = config.get_config('process_tracker', {})
            self._enabled = tracker_config.get('enabled', True)
            self._retention_days = tracker_config.get('retention_days', 90)
        except Exception:
            self._enabled = True
            self._retention_days = 90

    def _init_storage(self, db_path: Optional[str] = None) -> None:
        """
        初始化存储

        Args:
            db_path: 数据库路径
        """
        if db_path:
            self._db_path = db_path
        else:
            env_path = os.getenv('CONTAINER_DB_PATH', '').strip()
            if env_path:
                self._db_path = os.path.abspath(env_path)
            else:
                try:
                    from modular_config import ModularConfig
                    self._db_path = ModularConfig.get_container_db_path()
                except Exception:
                    self._db_path = os.path.join(
                        os.path.dirname(os.path.abspath(__file__)),
                        'mobile_api_ai', 'wechat_container.db'
                    )

        self._table_name = 'process_tracking'
        self._storage_file = os.path.join(
            os.path.dirname(self._db_path),
            'process_tracking.json'
        )
        self._ensure_storage_file()

    def _ensure_storage_file(self) -> None:
        """
        确保存储文件存在
        """
        os.makedirs(os.path.dirname(self._storage_file), exist_ok=True)
        if not os.path.exists(self._storage_file):
            with open(self._storage_file, 'w', encoding='utf-8') as f:
                json.dump([], f)

    def _ensure_table(self) -> None:
        """
        确保存储表存在（JSON模式）
        """
        pass

    def _read_records(self) -> List[Dict[str, Any]]:
        """
        读取所有记录

        Returns:
            记录列表
        """
        try:
            with open(self._storage_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f'[工序追踪] 读取记录失败: {e}')
            return []

    def _write_records(self, records: List[Dict[str, Any]]) -> bool:
        """
        写入记录

        Args:
            records: 记录列表

        Returns:
            是否成功
        """
        try:
            with open(self._storage_file, 'w', encoding='utf-8') as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f'[工序追踪] 写入记录失败: {e}')
            return False

    def _notify_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        发送事件通知

        Args:
            event_type: 事件类型
            data: 事件数据
        """
        try:
            from event_bus import EventBus
            EventBus.publish(event_type, data)
        except ImportError:
            logger.warning('[工序追踪] EventBus不可用')
        except Exception as e:
            logger.warning(f'[工序追踪] 事件通知失败: {e}')

    def track_process(self,
                     order_no: str,
                     process_name: str,
                     status: str,
                     operator_id: str = '',
                     operator_name: str = '',
                     quantity: int = 0,
                     completed_qty: int = 0,
                     remarks: str = '',
                     **kwargs) -> bool:
        """
        追踪工序状态

        Args:
            order_no: 订单号
            process_name: 工序名称
            status: 状态 (pending/in_progress/completed)
            operator_id: 操作员ID
            operator_name: 操作员名称
            quantity: 数量
            completed_qty: 完成数量
            remarks: 备注
            **kwargs: 扩展参数

        Returns:
            是否成功
        """
        if not self._enabled:
            logger.warning('[工序追踪] 功能未启用')
            return False

        if status not in self.VALID_STATUSES:
            logger.error(f'[工序追踪] 无效状态: {status}')
            return False

        records = self._read_records()

        record = {
            'id': f'{order_no}_{process_name}_{datetime.now().strftime("%Y%m%d%H%M%S")}',
            'order_no': order_no,
            'process_name': process_name,
            'status': status,
            'operator_id': operator_id,
            'operator_name': operator_name,
            'quantity': quantity,
            'completed_qty': completed_qty,
            'remarks': remarks,
            'start_time': None,
            'end_time': None,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            **kwargs
        }

        if status == self.STATUS_IN_PROGRESS:
            record['start_time'] = datetime.now().isoformat()
        elif status == self.STATUS_COMPLETED:
            record['end_time'] = datetime.now().isoformat()

            existing = self._find_record(records, order_no, process_name)
            if existing and existing.get('start_time'):
                record['start_time'] = existing['start_time']

        updated_records = [r for r in records
                          if not (r['order_no'] == order_no and r['process_name'] == process_name)]
        updated_records.append(record)

        if self._write_records(updated_records):
            self._notify_event('PROCESS_TRACKED', record)
            logger.info(f'[工序追踪] 记录成功: order={order_no}, process={process_name}, status={status}')
            return True

        return False

    def _find_record(self,
                    records: List[Dict[str, Any]],
                    order_no: str,
                    process_name: str) -> Optional[Dict[str, Any]]:
        """
        查找记录

        Args:
            records: 记录列表
            order_no: 订单号
            process_name: 工序名称

        Returns:
            找到的记录或None
        """
        for record in records:
            if record.get('order_no') == order_no and record.get('process_name') == process_name:
                return record
        return None

    def get_order_processes(self, order_no: str) -> List[Dict[str, Any]]:
        """
        获取订单所有工序列表

        Args:
            order_no: 订单号

        Returns:
            工序列表
        """
        if not self._enabled:
            return []

        records = self._read_records()
        order_records = [r for r in records if r.get('order_no') == order_no]

        order_records.sort(key=lambda x: x.get('created_at', ''), reverse=True)

        return order_records

    def get_current_process(self, order_no: str) -> Optional[Dict[str, Any]]:
        """
        获取订单当前工序（in_progress状态）

        Args:
            order_no: 订单号

        Returns:
            当前工序记录或None
        """
        if not self._enabled:
            return None

        records = self._read_records()

        for record in records:
            if (record.get('order_no') == order_no and
                record.get('status') == self.STATUS_IN_PROGRESS):
                return record

        return None

    def get_process_history(self,
                          order_no: str,
                          process_name: str) -> List[Dict[str, Any]]:
        """
        获取指定工序历史记录

        Args:
            order_no: 订单号
            process_name: 工序名称

        Returns:
            历史记录列表
        """
        if not self._enabled:
            return []

        records = self._read_records()
        history = [r for r in records
                   if r.get('order_no') == order_no and r.get('process_name') == process_name]

        history.sort(key=lambda x: x.get('created_at', ''))

        return history

    def get_pending_processes(self) -> List[Dict[str, Any]]:
        """
        获取所有待处理的工序

        Returns:
            待处理工序列表
        """
        if not self._enabled:
            return []

        records = self._read_records()
        pending = [r for r in records if r.get('status') == self.STATUS_PENDING]

        return pending

    def get_in_progress_processes(self) -> List[Dict[str, Any]]:
        """
        获取所有进行中的工序

        Returns:
            进行中工序列表
        """
        if not self._enabled:
            return []

        records = self._read_records()
        in_progress = [r for r in records if r.get('status') == self.STATUS_IN_PROGRESS]

        return in_progress

    def complete_process(self,
                         order_no: str,
                         process_name: str,
                         completed_qty: int = 0,
                         remarks: str = '',
                         **kwargs) -> bool:
        """
        完成工序

        Args:
            order_no: 订单号
            process_name: 工序名称
            completed_qty: 完成数量
            remarks: 备注
            **kwargs: 扩展参数

        Returns:
            是否成功
        """
        return self.track_process(
            order_no=order_no,
            process_name=process_name,
            status=self.STATUS_COMPLETED,
            completed_qty=completed_qty,
            remarks=remarks,
            **kwargs
        )

    def start_process(self,
                     order_no: str,
                     process_name: str,
                     operator_id: str = '',
                     operator_name: str = '',
                     quantity: int = 0,
                     **kwargs) -> bool:
        """
        开始工序

        Args:
            order_no: 订单号
            process_name: 工序名称
            operator_id: 操作员ID
            operator_name: 操作员名称
            quantity: 数量
            **kwargs: 扩展参数

        Returns:
            是否成功
        """
        return self.track_process(
            order_no=order_no,
            process_name=process_name,
            status=self.STATUS_IN_PROGRESS,
            operator_id=operator_id,
            operator_name=operator_name,
            quantity=quantity,
            **kwargs
        )


_process_tracker_instance: Optional['ProcessTracker'] = None


def get_process_tracker() -> 'ProcessTracker':
    """
    获取全局工序追踪器实例（单例）

    Returns:
        ProcessTracker实例
    """
    global _process_tracker_instance
    if _process_tracker_instance is None:
        _process_tracker_instance = ProcessTracker()
    return _process_tracker_instance


def reset_process_tracker() -> None:
    """
    重置全局工序追踪器实例
    """
    global _process_tracker_instance
    _process_tracker_instance = None


def demo() -> None:
    """
    演示用法
    """
    print('=' * 60)
    print('工序追踪器演示')
    print('=' * 60)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    tracker = ProcessTracker()

    print('\n[1] 开始编织工序...')
    tracker.start_process(
        order_no='ORD202604001',
        process_name='编织',
        operator_id='OP001',
        operator_name='张三',
        quantity=100
    )

    print('\n[2] 查询当前工序...')
    current = tracker.get_current_process('ORD202604001')
    if current:
        print(f"当前工序: {current['process_name']}, 状态: {current['status']}")

    print('\n[3] 完成编织工序...')
    tracker.complete_process(
        order_no='ORD202604001',
        process_name='编织',
        completed_qty=100,
        remarks='全部完成'
    )

    print('\n[4] 查询订单所有工序...')
    processes = tracker.get_order_processes('ORD202604001')
    for p in processes:
        print(f"  - {p['process_name']}: {p['status']}")

    print('\n' + '=' * 60)
    print('演示完成！')
    print('=' * 60)


if __name__ == '__main__':
    demo()
