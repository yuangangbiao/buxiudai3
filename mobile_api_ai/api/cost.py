from flask import Blueprint, request
import logging

from .decorators import success, fail
from services.factory import get_cost_service

logger = logging.getLogger(__name__)

bp = Blueprint('cost', __name__, url_prefix='/api/cost')


def _get_service():
    return get_cost_service()


@bp.route('/orders', methods=['GET'])
def list_orders():
    service = _get_service()
    status = request.args.get('status')
    search = request.args.get('search')
    sort_by = request.args.get('sort_by', 'order_no')
    sort_order = request.args.get('sort_order', 'asc')
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))
    result = service.get_all_order_costs(
        status=status, search=search,
        sort_by=sort_by, sort_order=sort_order,
        page=page, page_size=page_size
    )
    return success(data=result)


@bp.route('/orders/<order_no>', methods=['GET'])
def get_order_cost(order_no):
    service = _get_service()
    cost = service.get_order_cost(order_no)
    if not cost:
        return fail(404, '订单成本数据不存在')
    return success(data=cost)


@bp.route('/orders/<order_no>/calculate', methods=['POST'])
def calculate(order_no):
    service = _get_service()
    data = request.get_json(silent=True) or {}
    result = service.calculate_order_cost(
        order_no,
        customer_name=data.get('customer_name', ''),
        product_name=data.get('product_name', ''),
        quantity=float(data.get('quantity', 0)),
        unit=data.get('unit', '件')
    )
    return success(data=result, message='成本核算完成')


@bp.route('/orders/<order_no>/revenue', methods=['PUT'])
def set_revenue(order_no):
    data = request.get_json(silent=True) or {}
    revenue = float(data.get('revenue', 0))
    service = _get_service()
    if service.set_revenue(order_no, revenue):
        return success(message='收入设置成功')
    return fail(500, '收入设置失败')


@bp.route('/detail/<order_no>', methods=['GET'])
def get_details(order_no):
    service = _get_service()
    details = service.get_cost_details(order_no)
    return success(data=details)


@bp.route('/detail', methods=['POST'])
def add_detail():
    data = request.get_json(silent=True)
    if not data or 'order_no' not in data or 'cost_type' not in data:
        return fail(400, '缺少必填参数: order_no, cost_type')

    valid_types = ['material', 'labor', 'overhead', 'outsourcing', 'other']
    if data['cost_type'] not in valid_types:
        return fail(400, f"cost_type 必须是 {valid_types} 之一")

    if 'amount' not in data and ('quantity' not in data or 'unit_price' not in data):
        data['amount'] = float(data.get('quantity', 0)) * float(data.get('unit_price', 0))

    service = _get_service()
    if service.add_cost_detail(data):
        return success(message='成本明细添加成功')
    return fail(500, '成本明细添加失败')


@bp.route('/detail/<int:detail_id>', methods=['DELETE'])
def delete_detail(detail_id):
    service = _get_service()
    if service.delete_cost_detail(detail_id):
        return success(message='成本明细删除成功')
    return fail(404, '成本明细不存在')


@bp.route('/summary', methods=['GET'])
def summary():
    service = _get_service()
    data = service.get_summary()
    return success(data=data)


@bp.route('/material-prices', methods=['GET'])
def list_material_prices():
    service = _get_service()
    prices = service.get_material_prices()
    return success(data=prices)


@bp.route('/material-prices', methods=['POST'])
def save_material_price():
    data = request.get_json(silent=True)
    if not data:
        return fail(400, '请求体不能为空')

    if isinstance(data, list):
        service = _get_service()
        count = service.batch_save_material_prices(data)
        return success(data={'count': count}, message=f'成功保存{count}条物料单价')
    else:
        service = _get_service()
        ok = service.save_material_price(
            data['material_name'],
            float(data['unit_price']),
            data.get('unit', '个')
        )
        if ok:
            return success(message='物料单价保存成功')
        return fail(500, '物料单价保存失败')


@bp.route('/labor-prices', methods=['GET'])
def list_labor_prices():
    service = _get_service()
    prices = service.get_labor_prices()
    return success(data=prices)


@bp.route('/labor-prices', methods=['POST'])
def save_labor_price():
    data = request.get_json(silent=True)
    if not data:
        return fail(400, '请求体不能为空')

    if isinstance(data, list):
        service = _get_service()
        count = service.batch_save_labor_prices(data)
        return success(data={'count': count}, message=f'成功保存{count}条工序单价')
    else:
        if 'process_name' not in data or 'unit_price' not in data:
            return fail(400, '缺少必填参数: process_name, unit_price')
        service = _get_service()
        ok = service.save_labor_price(
            data['process_name'],
            float(data['unit_price']),
            data.get('unit', '米')
        )
        if ok:
            return success(message='工序单价保存成功')
        return fail(500, '工序单价保存失败')
