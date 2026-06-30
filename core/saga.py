# -*- coding: utf-8 -*-
"""Saga 编排器 — 跨服务长事务补偿协调"""
import json, logging, threading, time
from datetime import datetime
from dataclasses import dataclass, field
from typing import Callable, Optional
from models.database import get_connection

logger = logging.getLogger(__name__)


@dataclass
class SagaStep:
    name: str
    execute: Callable  # () -> bool
    compensate: Callable  # () -> None


class SagaOrchestrator:
    """补偿型 Saga 协调器。正常路径顺序执行，失败时逆序补偿。"""

    def __init__(self, name: str, steps: list):
        self.name = name
        self.steps = steps
        self._log = []

    def run(self, initial_data: dict = None) -> dict:
        """执行 Saga，返回 {success: bool, log: [], error: str|None}"""
        completed = []
        try:
            for step in self.steps:
                ok = step.execute()
                self._log.append({'step': step.name, 'action': 'execute', 'ok': ok})
                if ok:
                    completed.append(step)
                else:
                    raise RuntimeError(f'Step {step.name} 执行失败')
            return {'success': True, 'log': self._log, 'error': None}

        except Exception as e:
            logger.error(f'[Saga:{self.name}] 失败于 {step.name}: {e}')
            # 逆序补偿
            for step in reversed(completed):
                try:
                    step.compensate()
                    self._log.append({'step': step.name, 'action': 'compensate', 'ok': True})
                except Exception as ce:
                    self._log.append({'step': step.name, 'action': 'compensate', 'ok': False, 'error': str(ce)})
                    self._save_dead_letter(step, str(ce))
            return {'success': False, 'log': self._log, 'error': str(e)}

    def _save_dead_letter(self, step, error):
        """补偿失败写入死信表"""
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute(
                """CREATE TABLE IF NOT EXISTS saga_dead_letter (
                   id INT AUTO_INCREMENT PRIMARY KEY, saga_name VARCHAR(100),
                   step_name VARCHAR(100), error TEXT, created_at DATETIME)""")
            c.execute("INSERT INTO saga_dead_letter (saga_name, step_name, error, created_at) VALUES (%s,%s,%s,%s)",
                      (self.name, step.name, error, datetime.now()))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f'[Saga] dead_letter写入失败: {e}')


# ---- 预定义 Saga：订单履约流程 ----
def create_order_fulfillment_saga(order_no: str):
    """订单→排产→生产→质检→发货"""
    def schedule(): return True   # 排产逻辑（对接 dispatch_center）
    def unschedule(): pass        # 取消排产
    def produce(): return True    # 生产逻辑
    def unproduce(): pass         # 撤销生产
    def qc_pass(): return True    # 质检逻辑
    def qc_reject(): pass         # 质检驳回
    def ship(): return True       # 发货逻辑
    def unship(): pass            # 撤销发货

    return SagaOrchestrator(f'order_fulfillment_{order_no}', [
        SagaStep('schedule', schedule, unschedule),
        SagaStep('produce', produce, unproduce),
        SagaStep('qc', qc_pass, qc_reject),
        SagaStep('ship', ship, unship),
    ])
