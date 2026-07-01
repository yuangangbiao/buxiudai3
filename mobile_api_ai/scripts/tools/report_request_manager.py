import json
import uuid
from datetime import datetime
from typing import Dict, Optional, Any

class ReportRequest:
    """报工请求记录"""
    
    def __init__(self, order_no: str, process: str, quantity: int, operator: str):
        self.id = str(uuid.uuid4())[:8]
        self.order_no = order_no
        self.process = process
        self.quantity = quantity
        self.operator = operator
        self.task_id = None  # 关联的任务ID
        self.current_completed = 0  # 当前已完成数量
        self.planned_qty = 0  # 计划数量
        self.new_completed = 0  # 报工后完成数量
        self.remaining = 0  # 剩余数量
        self.status = 'pending'  # pending, confirmed, rejected
        self.created_at = datetime.now()
        self.confirmed_at = None
        self.message = ''
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'order_no': self.order_no,
            'process': self.process,
            'quantity': self.quantity,
            'operator': self.operator,
            'task_id': self.task_id,
            'current_completed': self.current_completed,
            'planned_qty': self.planned_qty,
            'new_completed': self.new_completed,
            'remaining': self.remaining,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'confirmed_at': self.confirmed_at.strftime('%Y-%m-%d %H:%M:%S') if self.confirmed_at else None,
            'message': self.message
        }

class ReportRequestManager:
    """报工请求管理器"""
    
    def __init__(self):
        self._requests: Dict[str, ReportRequest] = {}
    
    def create_request(self, order_no: str, process: str, quantity: int, operator: str, 
                       task_id: str = None, current_completed: int = 0, 
                       planned_qty: int = 0, new_completed: int = 0, remaining: int = 0) -> ReportRequest:
        """创建报工请求"""
        req = ReportRequest(order_no, process, quantity, operator)
        req.task_id = task_id
        req.current_completed = current_completed
        req.planned_qty = planned_qty
        req.new_completed = new_completed
        req.remaining = remaining
        self._requests[req.id] = req
        return req
    
    def get_request(self, request_id: str) -> Optional[ReportRequest]:
        """获取报工请求"""
        return self._requests.get(request_id)
    
    def confirm_request(self, request_id: str, message: str = '报工成功') -> bool:
        """确认报工请求"""
        req = self._requests.get(request_id)
        if req:
            req.status = 'confirmed'
            req.confirmed_at = datetime.now()
            req.message = message
            return True
        return False
    
    def reject_request(self, request_id: str, message: str = '报工失败') -> bool:
        """拒绝报工请求"""
        req = self._requests.get(request_id)
        if req:
            req.status = 'rejected'
            req.confirmed_at = datetime.now()
            req.message = message
            return True
        return False
    
    def get_pending_requests(self) -> list:
        """获取所有待确认的请求"""
        return [req.to_dict() for req in self._requests.values() if req.status == 'pending']
    
    def remove_request(self, request_id: str):
        """移除报工请求"""
        if request_id in self._requests:
            del self._requests[request_id]

# 全局报工请求管理器
_report_request_manager = ReportRequestManager()

def get_report_request_manager() -> ReportRequestManager:
    return _report_request_manager
