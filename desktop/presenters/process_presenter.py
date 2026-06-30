"""工序报工重构——从 process_view.py 提取 Presenter 逻辑"""
import logging

logger = logging.getLogger(__name__)


class ProcessReportPresenter:
    """工序报工 Presenter——process_view.py 中提取的业务逻辑"""

    def __init__(self, process_service, event_bus=None):
        self.service = process_service
        self.event_bus = event_bus

    def submit_report(self, record_id, qty, qualified=0, hours=0, worker='', remark=''):
        """提交报工：累加完成量 + 自动判断状态 + 事件发布"""
        try:
            update = self.service.report_progress(record_id, qty, qualified, hours, worker, remark)
        except ValueError as e:
            return {'success': False, 'error': str(e)}

        if self.event_bus:
            from core.events import EventType
            self.event_bus.publish(EventType.PROCESS_REPORTED, {
                'record_id': record_id,
                'qty': qty,
                'status': update['status'],
            })

        return {'success': True, 'update': update}


class ProcessReorderPresenter:
    """工序排序 Presenter — 调用 core.config 的 move_process + 持久化到 DB"""

    def move_up(self, process_name: str) -> bool:
        from core.config import move_process, save_display_order_to_db, invalidate_display_seq_cache
        seq = move_process(process_name, 'up')
        if seq < 0:
            return False
        save_display_order_to_db()
        invalidate_display_seq_cache()
        return True

    def move_down(self, process_name: str) -> bool:
        from core.config import move_process, save_display_order_to_db, invalidate_display_seq_cache
        seq = move_process(process_name, 'down')
        if seq < 0:
            return False
        save_display_order_to_db()
        invalidate_display_seq_cache()
        return True

    def move_to_top(self, process_name: str) -> bool:
        from core.config import move_process, save_display_order_to_db, invalidate_display_seq_cache
        seq = move_process(process_name, 'top')
        if seq < 0:
            return False
        save_display_order_to_db()
        invalidate_display_seq_cache()
        return True

    def move_to_bottom(self, process_name: str) -> bool:
        from core.config import move_process, save_display_order_to_db, invalidate_display_seq_cache
        seq = move_process(process_name, 'bottom')
        if seq < 0:
            return False
        save_display_order_to_db()
        invalidate_display_seq_cache()
        return True

    def reorder_all(self, ordered_names: list) -> bool:
        from core.config import reorder_processes, save_display_order_to_db, invalidate_display_seq_cache
        reorder_processes(ordered_names)
        save_display_order_to_db()
        invalidate_display_seq_cache()
        return True

    def get_all_sorted(self) -> list:
        from core.config import get_all_processes, get_display_seq_map
        seq_map = get_display_seq_map()
        return [(name, seq_map.get(name, 99)) for name in get_all_processes(sort=True)]
