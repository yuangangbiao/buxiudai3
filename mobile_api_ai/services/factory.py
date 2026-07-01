from typing import Optional
from .interfaces import (
    StatsServiceInterface,
    CostServiceInterface,
    SchedulerServiceInterface,
)


_service_instances = {}


def get_stats_service() -> StatsServiceInterface:
    if 'stats' not in _service_instances:
        from .stats_engine import StatsEngine
        from .session import get_storage
        _service_instances['stats'] = StatsEngine(get_storage())
    return _service_instances['stats']


def get_cost_service() -> CostServiceInterface:
    if 'cost' not in _service_instances:
        from .cost_service import CostService
        from .session import get_storage
        _service_instances['cost'] = CostService(get_storage())
    return _service_instances['cost']


def get_scheduler_service() -> SchedulerServiceInterface:
    if 'scheduler' not in _service_instances:
        engine = get_stats_service()
        from .scheduler import ReportScheduler
        _service_instances['scheduler'] = ReportScheduler(engine)
    return _service_instances['scheduler']


def get_scheduler_service_safe() -> Optional[SchedulerServiceInterface]:
    return _service_instances.get('scheduler')
