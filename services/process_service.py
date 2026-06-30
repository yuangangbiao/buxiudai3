# -*- coding: utf-8 -*-
"""
工序服务层 (ProcessService)

继承 BaseService，封装工序记录的业务逻辑，包括：
- 工序记录的增删改查
- 按生产工单查询工序列表
- 工序报工（累加完成量、自动判断状态）
"""

import logging
from typing import Optional, Any

from services.base_service import BaseService
from models.process import ProcessDAO

logger = logging.getLogger(__name__)


class ProcessService(BaseService):
    """工序业务服务

    继承 BaseService 获得事务管理能力，通过 ProcessDAO 操作工序记录表。
    """

    def __init__(self):
        """初始化，注入 ProcessDAO 实例。"""
        super().__init__(dao=ProcessDAO())

    def get_records_by_production(self, prod_id: int) -> list:
        """获取指定生产工单的所有工序记录。

        Args:
            prod_id: 生产工单 ID

        Returns:
            工序记录列表，按 process_seq 升序排列
        """
        return self.dao.get_by_production(prod_id)

    def get_record_by_id(self, record_id: int) -> Optional[dict]:
        """根据 ID 获取单条工序记录。

        Args:
            record_id: 工序记录 ID

        Returns:
            工序记录字典，不存在则返回 None
        """
        return self.dao.get_by_id(record_id)

    def update_record(self, record_id: int, data: dict) -> bool:
        """更新工序记录。

        Args:
            record_id: 工序记录 ID
            data: 要更新的字段字典

        Returns:
            操作是否成功
        """
        return self.dao.update_record(record_id, data)

    def insert_record(self, data: dict) -> int:
        """创建新工序记录。

        Args:
            data: 工序记录字段字典

        Returns:
            新记录 ID
        """
        return self.dao.create(data)

    def delete_record(self, record_id: int) -> bool:
        """删除工序记录。

        Args:
            record_id: 工序记录 ID

        Returns:
            操作是否成功（记录存在且被删除返回 True）
        """
        return self.dao.delete(record_id)

    def report_progress(
        self,
        record_id: int,
        qty: int,
        qualified: int = 0,
        hours: float = 0,
        worker: str = '',
        remark: str = ''
    ) -> dict:
        """工序报工 —— 累加完成量，自动判断状态。

        将本次报工数量累加到已有完成量上，并根据累计完成量
        与计划量的对比自动设置工序状态。

        Args:
            record_id: 工序记录 ID
            qty: 本次完成数量（合格 + 不合格）
            qualified: 本次合格数量，默认 0
            hours: 本次工时（小时），默认 0
            worker: 操作工人，默认空字符串（不覆盖原值）
            remark: 备注，默认空字符串（不覆盖原值）

        Returns:
            更新后的数据字典

        Raises:
            ValueError: 工序记录不存在时抛出
        """
        record = self.dao.get_by_id(record_id)
        if not record:
            raise ValueError(f"工序记录不存在: {record_id}")

        new_qty = record.get('completed_qty', 0) + qty
        planned = record.get('planned_qty', 1)
        status = '已完成' if new_qty >= planned else '进行中'

        update = {
            'completed_qty': new_qty,
            'qualified_qty': record.get('qualified_qty', 0) + qualified,
            'work_hours': record.get('work_hours', 0) + hours,
            'status': status,
        }
        if worker:
            update['worker'] = worker
        if remark:
            update['remark'] = remark

        self.dao.update_record(record_id, update)
        logger.info(
            "工序报工 record_id=%s qty=%d → completed=%d/%d status=%s",
            record_id, qty, new_qty, planned, status
        )
        return update

    def _get_record(self, record_id: int) -> dict:
        """内部：获取记录或抛异常。

        Args:
            record_id: 工序记录 ID

        Returns:
            工序记录字典

        Raises:
            ValueError: 工序记录不存在时抛出
        """
        record = self.dao.get_by_id(record_id)
        if not record:
            raise ValueError(f"工序记录不存在: {record_id}")
        return record

    def reorder_processes(self, production_id: int, ordered_ids: list) -> None:
        """工序排序。

        按 ordered_ids 的顺序为工序记录设置 seq 字段。

        Args:
            production_id: 生产工单 ID
            ordered_ids: 按新顺序排列的记录 ID 列表
        """
        for i, rid in enumerate(ordered_ids):
            self.dao.update_record(rid, {'seq': i + 1})

    def apply_template(self, production_id: int, template_name: str) -> list:
        """从模板批量生成工序。

        Args:
            production_id: 生产工单 ID
            template_name: 模板名称

        Returns:
            新创建的工序记录列表
        """
        from utils.process_templates import get_all_process_templates
        templates = get_all_process_templates()
        template = templates.get(template_name, [])
        records: list = []
        for item in template:
            item['production_id'] = production_id
            rid = self.dao.create(item)
            records.append({'id': rid, **item})
        return records

    def update_planned_qty(self, record_id: int, planned_qty: int) -> Any:
        """更新工序计划数量。

        Args:
            record_id: 工序记录 ID
            planned_qty: 新的计划数量

        Returns:
            DAO 更新操作返回值
        """
        return self.dao.update_record(record_id, {'planned_qty': planned_qty})

    def update_remark(self, record_id: int, remark: str) -> Any:
        """更新工序备注。

        Args:
            record_id: 工序记录 ID
            remark: 备注内容

        Returns:
            DAO 更新操作返回值
        """
        return self.dao.update_record(record_id, {'remark': remark})

    def batch_delete_by_production(self, production_id: int) -> None:
        """批量删除指定生产工单下所有工序记录。

        Args:
            production_id: 生产工单 ID
        """
        records = self.dao.get_by_production(production_id)
        for r in records:
            self.dao.delete(r['id'])

    def get_production_summary(self, production_id: int) -> dict:
        """获取生产工单的工序进度摘要。

        Args:
            production_id: 生产工单 ID

        Returns:
            包含 total、completed、progress 的摘要字典
        """
        records = self.dao.get_by_production(production_id)
        total = len(records)
        completed = sum(1 for r in records if r.get('status') == '已完成')
        return {
            'total': total,
            'completed': completed,
            'progress': completed / max(total, 1) * 100,
        }

    def get_process_defaults(self, process_name: str) -> dict | None:
        """从规则引擎获取工序默认配置。

        Args:
            process_name: 工序名称

        Returns:
            包含 default_qty, unit, requires_material 的字典，未命中返回 None
        """
        try:
            from core.rule_engine import get_rule_engine
            rules = get_rule_engine()
            rule = rules.get_process(process_name)
            if rule:
                return {
                    'default_qty': rule.get('default_qty', 0),
                    'unit': rule.get('unit', ''),
                    'requires_material': rule.get('requires_material', False),
                }
        except Exception as e:
            logger.debug(f"规则引擎查询失败: {e}")
        return None

    def shift_seq_up(self, production_id: int, from_seq: int) -> None:
        """批量工序序号移位：>= from_seq 的序号全部 +1。

        Args:
            production_id: 生产工单 ID
            from_seq: 起始序号（包含），所有 process_seq >= from_seq 的 +1
        """
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE process_records SET process_seq = process_seq + 1 "
                "WHERE production_id=%s AND process_seq >= %s",
                (production_id, from_seq)
            )
