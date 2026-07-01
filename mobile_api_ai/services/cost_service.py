import logging
import threading
from typing import Dict, List, Optional
from datetime import datetime

from core.db import get_direct_connection

from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
from .interfaces import CostServiceInterface

logger = logging.getLogger(__name__)


class CostService(CostServiceInterface):

    COST_TYPES = ['material', 'labor', 'overhead', 'outsourcing', 'other']
    COST_LABELS = {
        'material': '材料成本',
        'labor': '人工成本',
        'overhead': '制造费用',
        'outsourcing': '外协成本',
        'other': '其他成本'
    }

    def __init__(self, storage):
        self.storage = storage
        self._material_price_cache: Dict[str, float] = {}
        self._labor_price_cache: Dict[str, float] = {}
        self._cache_lock = threading.Lock()

    def _get_cached_material_price(self, name: str) -> float:
        with self._cache_lock:
            if name not in self._material_price_cache:
                self._material_price_cache[name] = self.storage.get_material_unit_price(name) or 0
            val = self._material_price_cache[name]
        return val

    def _get_cached_labor_price(self, name: str) -> float:
        with self._cache_lock:
            if name not in self._labor_price_cache:
                self._labor_price_cache[name] = self.storage.get_labor_unit_price(name) or 0
            val = self._labor_price_cache[name]
        return val

    def invalidate_price_cache(self):
        with self._cache_lock:
            self._material_price_cache.clear()
            self._labor_price_cache.clear()

    def get_order_cost(self, order_no: str) -> Optional[Dict]:
        return self.storage.get_order_cost(order_no)

    def get_all_order_costs(self, status: str = None, search: str = None,
                            sort_by: str = 'order_no', sort_order: str = 'asc',
                            page: int = 1, page_size: int = 20) -> Dict:
        limit = page_size
        offset = (page - 1) * page_size
        items = self.storage.get_all_order_costs(
            status=status, search=search,
            sort_by=sort_by, sort_order=sort_order,
            limit=limit, offset=offset
        )
        total = self.storage.count_order_costs(status=status, search=search)
        return {
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size if total else 0
        }

    def save_order_cost(self, cost: Dict) -> bool:
        cost.setdefault('created_at', datetime.now().isoformat())
        return self.storage.save_order_cost(cost)

    def delete_order_cost(self, order_no: str) -> bool:
        return self.storage.delete_order_cost(order_no)

    def get_cost_details(self, order_no: str) -> List[Dict]:
        return self.storage.get_order_cost_details(order_no)

    def add_cost_detail(self, detail: Dict) -> bool:
        detail.setdefault('created_at', datetime.now().isoformat())
        ok = self.storage.save_order_cost_detail(detail)
        if ok:
            self._recalculate_order(detail['order_no'])
        return ok

    def delete_cost_detail(self, detail_id: int) -> bool:
        detail_to_delete = None
        if hasattr(self.storage, 'get_order_cost_details'):
            order_costs = self.storage.get_all_order_costs() or []
            for order_cost in order_costs:
                order_details = self.storage.get_order_cost_details(order_cost.get('order_no', ''))
                for d in order_details:
                    if d.get('id') == detail_id:
                        detail_to_delete = d
                        break

        ok = self.storage.delete_order_cost_detail(detail_id)
        if ok and detail_to_delete:
            self._recalculate_order(detail_to_delete['order_no'])
        return ok

    def set_revenue(self, order_no: str, revenue: float) -> bool:
        cost = self.storage.get_order_cost(order_no) or {'order_no': order_no}
        cost['revenue'] = revenue
        self._compute_summary(cost)
        return self.storage.save_order_cost(cost)

    def calculate_order_cost(self, order_no: str, customer_name: str = '',
                             product_name: str = '', quantity: float = 0,
                             unit: str = '件') -> Dict:
        existing = self.storage.get_order_cost(order_no)
        cost = existing or {
            'order_no': order_no,
            'customer_name': customer_name,
            'product_name': product_name,
            'quantity': quantity,
            'unit': unit,
            'revenue': 0
        }

        cost['material_cost'] = self._auto_collect_material(order_no)
        cost['labor_cost'] = self._auto_collect_labor(order_no)

        details = self.storage.get_order_cost_details(order_no) or []
        buckets = {'material': 0, 'labor': 0, 'overhead': 0, 'outsourcing': 0, 'other': 0}
        for d in details:
            ct = d.get('cost_type', '')
            if ct in buckets:
                buckets[ct] += d.get('amount', 0)
        cost['overhead_cost'] = buckets['overhead']
        cost['outsourcing_cost'] = buckets['outsourcing']
        cost['other_cost'] = buckets['other']

        self._compute_summary(cost)
        cost['status'] = 'calculated'
        cost['calculated_at'] = datetime.now().isoformat()
        self.storage.save_order_cost(cost)
        return cost

    def get_summary(self) -> Dict:
        summary = self.storage.get_cost_summary()
        if not summary:
            summary = {}
        return summary

    def get_material_prices(self) -> List[Dict]:
        return self.storage.get_all_material_prices()

    def save_material_price(self, material_name: str, unit_price: float,
                            unit: str = '个') -> bool:
        ok = self.storage.save_material_unit_price(material_name, unit_price, unit)
        if ok:
            self.invalidate_price_cache()
        return ok

    def get_labor_prices(self) -> List[Dict]:
        return self.storage.get_all_labor_prices()

    def save_labor_price(self, process_name: str, unit_price: float,
                         unit: str = '米') -> bool:
        ok = self.storage.save_labor_unit_price(process_name, unit_price, unit)
        if ok:
            self.invalidate_price_cache()
        return ok

    def batch_save_material_prices(self, prices: List[Dict]) -> int:
        count = 0
        for p in prices:
            if self.storage.save_material_unit_price(
                    p.get('material_name', '').strip(),
                    float(p.get('unit_price', 0)),
                    p.get('unit', '个')):
                count += 1
        if count:
            self.invalidate_price_cache()
        return count

    def batch_save_labor_prices(self, prices: List[Dict]) -> int:
        count = 0
        for p in prices:
            if self.storage.save_labor_unit_price(
                    p.get('process_name', '').strip(),
                    float(p.get('unit_price', 0)),
                    p.get('unit', '米')):
                count += 1
        if count:
            self.invalidate_price_cache()
        return count

    def _auto_collect_material(self, order_no: str) -> float:
        existing = self.storage.get_order_cost_details(order_no) or []
        logged = {}
        for d in existing:
            if d.get('source_type') == 'auto_material':
                logged[d.get('source_id', '')] = d.get('amount', 0)

        conn = None
        try:
            conn = get_direct_connection(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT process_name, material_qty, material_unit
                    FROM material_usage_log
                    WHERE order_no = %s
                ''', (order_no,))
                rows = cursor.fetchall()
        except Exception as e:
            logger.warning(f"[CostService] 自动归集材料用量失败: {e}")
            return sum(logged.values()) if logged else 0
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

        total = sum(logged.values())
        for row in rows:
            qty = row['material_qty']
            name = row['process_name']
            if name in logged:
                continue
            unit_price = self._get_cached_material_price(name)
            amount = qty * unit_price
            total += amount
            self.storage.save_order_cost_detail({
                'order_no': order_no,
                'cost_type': 'material',
                'source_type': 'auto_material',
                'source_id': str(row['process_name']),
                'description': f"领料: {name} x {qty}",
                'quantity': qty,
                'unit': row['material_unit'] or '',
                'unit_price': unit_price,
                'amount': amount,
                'operator_id': 'system'
            })
        return total

    def _auto_collect_labor(self, order_no: str) -> float:
        existing = self.storage.get_order_cost_details(order_no) or []
        logged = {}
        for d in existing:
            if d.get('source_type') == 'auto_labor':
                logged[d.get('source_id', '')] = d.get('amount', 0)

        conn = None
        try:
            conn = get_direct_connection(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT process_name, quantity, unit
                    FROM report_records
                    WHERE order_no = %s AND status = 'approved'
                ''', (order_no,))
                rows = cursor.fetchall()
        except Exception as e:
            logger.warning(f"[CostService] 自动归集人工用量失败: {e}")
            return sum(logged.values()) if logged else 0
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

        total = sum(logged.values())
        for row in rows:
            qty = row['quantity']
            name = row['process_name']
            if name in logged:
                continue
            unit_price = self._get_cached_labor_price(name)
            amount = qty * unit_price
            total += amount
            self.storage.save_order_cost_detail({
                'order_no': order_no,
                'cost_type': 'labor',
                'source_type': 'auto_labor',
                'source_id': str(row['process_name']),
                'description': f"报工: {name} x {qty}",
                'quantity': qty,
                'unit': row['unit'] or '',
                'unit_price': unit_price,
                'amount': amount,
                'operator_id': 'system'
            })
        return total

    def _sum_cost_type(self, order_no: str, cost_type: str) -> float:
        details = self.storage.get_order_cost_details(order_no)
        if not details:
            return 0
        return sum(
            d.get('amount', 0) for d in details
            if d.get('cost_type') == cost_type
        )

    def _recalculate_order(self, order_no: str):
        cost = self.storage.get_order_cost(order_no)
        if not cost:
            return
        details = self.storage.get_order_cost_details(order_no) or []
        buckets = {'material': 0, 'labor': 0, 'overhead': 0, 'outsourcing': 0, 'other': 0}
        for d in details:
            ct = d.get('cost_type', '')
            if ct in buckets:
                buckets[ct] += d.get('amount', 0)
        cost['material_cost'] = buckets['material']
        cost['labor_cost'] = buckets['labor']
        cost['overhead_cost'] = buckets['overhead']
        cost['outsourcing_cost'] = buckets['outsourcing']
        cost['other_cost'] = buckets['other']
        self._compute_summary(cost)
        self.storage.save_order_cost(cost)

    def _compute_summary(self, cost: Dict):
        cost['total_cost'] = (
            cost.get('material_cost', 0) +
            cost.get('labor_cost', 0) +
            cost.get('overhead_cost', 0) +
            cost.get('outsourcing_cost', 0) +
            cost.get('other_cost', 0)
        )
        revenue = cost.get('revenue', 0)
        cost['profit'] = revenue - cost['total_cost']
        cost['margin_rate'] = round(
            (cost['profit'] / revenue * 100), 2
        ) if revenue > 0 else 0


def get_cost_service():
    from storage_layer import StorageFactory, StorageType, resolve_storage_type
    default_st = resolve_storage_type()
    storage = StorageFactory.get_instance(default_st)
    if not storage:
        storage = StorageFactory.create(default_st)
    return CostService(storage)
