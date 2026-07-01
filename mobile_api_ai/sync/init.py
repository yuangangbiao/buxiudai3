# -*- coding: utf-8 -*-
import logging

from sync.event_bus import EventBus
from sync.handlers.sub_step_handler import handle_sub_step_created
from sync.handlers.attendance_handler import handle_attendance_created, handle_attendance_updated
from sync.handlers.order_handler import handle_process_created, handle_process_updated
from sync.handlers.worker_handler import handle_operator_created, handle_operator_updated, handle_operator_deleted
from sync.handlers.quality_handler import handle_quality_updated
from sync.sync_log import SyncLog

logger = logging.getLogger(__name__)


def init_sync_engine():
    SyncLog.ensure_table()
    EventBus.get().subscribe('sub_step.created', handle_sub_step_created)
    EventBus.get().subscribe('attendance.created', handle_attendance_created)
    EventBus.get().subscribe('attendance.updated', handle_attendance_updated)
    EventBus.get().subscribe('process.created', handle_process_created)
    EventBus.get().subscribe('process.updated', handle_process_updated)
    EventBus.get().subscribe('operator.created', handle_operator_created)
    EventBus.get().subscribe('operator.updated', handle_operator_updated)
    EventBus.get().subscribe('operator.deleted', handle_operator_deleted)
    EventBus.get().subscribe('quality.updated', handle_quality_updated)
    logger.info("Sync engine initialized")
