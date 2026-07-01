from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class StatsServiceInterface(ABC):

    @abstractmethod
    def get_dashboard(self) -> dict:
        ...

    @abstractmethod
    def get_production_stats(self) -> dict:
        ...

    @abstractmethod
    def get_cost_stats(self) -> dict:
        ...

    @abstractmethod
    def get_worker_stats(self) -> dict:
        ...

    @abstractmethod
    def list_reports(self, category: Optional[str] = None) -> List[dict]:
        ...

    @abstractmethod
    def get_report(self, report_id: str) -> Optional[dict]:
        ...

    @abstractmethod
    def save_report(self, data: dict) -> bool:
        ...

    @abstractmethod
    def delete_report(self, report_id: str) -> bool:
        ...

    @abstractmethod
    def execute_report(self, report_id: str, params: Optional[dict] = None) -> dict:
        ...

    @abstractmethod
    def export_report(self, report_id: str, format: str = 'xlsx',
                      profile_id: Optional[str] = None,
                      params: Optional[dict] = None) -> dict:
        ...

    @abstractmethod
    def list_export_profiles(self) -> List[dict]:
        ...

    @abstractmethod
    def get_export_profile(self, profile_id: str) -> Optional[dict]:
        ...

    @abstractmethod
    def save_export_profile(self, data: dict) -> bool:
        ...

    @abstractmethod
    def delete_export_profile(self, profile_id: str) -> bool:
        ...

    @abstractmethod
    def list_schedules(self, enabled_only: bool = False) -> List[dict]:
        ...

    @abstractmethod
    def get_schedule(self, schedule_id: str) -> Optional[dict]:
        ...

    @abstractmethod
    def save_schedule(self, data: dict) -> bool:
        ...

    @abstractmethod
    def delete_schedule(self, schedule_id: str) -> bool:
        ...

    @abstractmethod
    def list_outputs(self, report_id: Optional[str] = None, limit: int = 50) -> List[dict]:
        ...


class CostServiceInterface(ABC):

    @abstractmethod
    def get_all_order_costs(self, status: Optional[str] = None,
                            search: Optional[str] = None,
                            sort_by: str = 'order_no',
                            sort_order: str = 'asc',
                            page: int = 1, page_size: int = 20) -> dict:
        ...

    @abstractmethod
    def get_order_cost(self, order_no: str) -> Optional[dict]:
        ...

    @abstractmethod
    def calculate_order_cost(self, order_no: str, customer_name: str = '',
                             product_name: str = '', quantity: float = 0,
                             unit: str = '件') -> dict:
        ...

    @abstractmethod
    def set_revenue(self, order_no: str, revenue: float) -> bool:
        ...

    @abstractmethod
    def get_cost_details(self, order_no: str) -> List[dict]:
        ...

    @abstractmethod
    def add_cost_detail(self, data: dict) -> bool:
        ...

    @abstractmethod
    def delete_cost_detail(self, detail_id: int) -> bool:
        ...

    @abstractmethod
    def get_summary(self) -> dict:
        ...

    @abstractmethod
    def get_material_prices(self) -> List[dict]:
        ...

    @abstractmethod
    def batch_save_material_prices(self, items: List[dict]) -> int:
        ...

    @abstractmethod
    def save_material_price(self, material_name: str, unit_price: float,
                            unit: str = '个') -> bool:
        ...

    @abstractmethod
    def get_labor_prices(self) -> List[dict]:
        ...

    @abstractmethod
    def batch_save_labor_prices(self, items: List[dict]) -> int:
        ...

    @abstractmethod
    def save_labor_price(self, process_name: str, unit_price: float,
                         unit: str = '米') -> bool:
        ...


class SchedulerServiceInterface(ABC):

    @abstractmethod
    def is_running(self) -> bool:
        ...

    @abstractmethod
    def start(self):
        ...

    @abstractmethod
    def stop(self):
        ...

    @property
    @abstractmethod
    def check_interval(self) -> int:
        ...
