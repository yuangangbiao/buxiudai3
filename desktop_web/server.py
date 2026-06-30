# -*- coding: utf-8 -*-
"""
桌面 Web 化 - 服务骨架 (5001 端口)
按小袁"渐进式 Web 化"决策(2026-06-22),只读 core/ + models/ + 复用 5003 API
不重写 27 个 Tkinter 视图,只做 1:1 像素复刻 + 服务端 API
"""
import os
import sys
import json
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, render_template, jsonify, request, redirect, session
from flask_cors import CORS
from functools import wraps
import requests
from datetime import datetime
import random
import uuid  # [P0-H 修复 2026-06-24] 发货单运单号生成：timestamp 改 UUID（高并发不重复）
import time

# [P1-5 修复 2026-06-24] 统一日志架构：desktop_web 也使用 logging_setup.py
import mobile_api_ai.logging_setup as _ls
_ls.setup_daily_logger('desktop_web')
del _ls
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s:%(lineno)d %(message)s')
logger = logging.getLogger('desktop_web')


def require_auth(f):
    """基础权限校验：必须登录"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'dispatch_user' not in session:
            return jsonify({'code': 401, 'message': '未登录'}), 401
        return f(*args, **kwargs)
    return decorated


def require_role(*roles):
    """角色权限校验：必须是指定角色"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'dispatch_user' not in session:
                return jsonify({'code': 401, 'message': '未登录'}), 401
            user = session.get('dispatch_user', {})
            # [P0 修复 2026-06-23 小钰] 默认 role 'worker' -> 'viewer' (最弱权限, 防止 role 字段缺失时越权)
            user_role = user.get('role', 'viewer')
            allowed = set(roles) | {'admin'}
            if user_role not in allowed:
                return jsonify({'code': 403, 'message': '权限不足'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


def verify_csrf_token(f):
    """CSRF Token 校验装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == 'GET':
            return f(*args, **kwargs)
        session_token = session.get('csrf_token')
        if not session_token:
            return jsonify({'code': 403, 'message': 'CSRF Token缺失，请重新登录'}), 403
        token = (
            request.headers.get('X-CSRF-Token') or
            (request.json.get('csrf_token') if request.is_json and request.json else None) or
            request.form.get('csrf_token')
        )
        if not token or token != session_token:
            return jsonify({'code': 403, 'message': 'CSRF校验失败'}), 403
        return f(*args, **kwargs)
    return decorated


def _sync_bridge(data):
    """向SYNC_BRIDGE发送同步通知，失败不阻断主流程"""
    try:
        url = os.getenv('SYNC_BRIDGE_URL')
        if not url:
            return
        data['source'] = 'web5001'
        data['timestamp'] = datetime.now().isoformat()
        requests.post(url, json=data, timeout=5)
    except Exception as e:
        logger.warning(f'[SYNC_BRIDGE] 同步失败: {e}')


# 5003 调度中心地址(本机)
DISPATCH_BASE = os.getenv('DISPATCH_BASE', 'http://127.0.0.1:5003')

import secrets as _secrets
import base64  # [P0 修复 2026-06-23 小圣] 跨服务 token 协议对齐 5003: base64(uid:uname)

app = Flask(
    __name__,
    template_folder=str(PROJECT_ROOT / 'desktop_web' / 'templates'),
    static_folder=str(PROJECT_ROOT / 'desktop_web' / 'static'),
)
_jwt_secret = os.getenv('JWT_SECRET_KEY')
if not _jwt_secret:
    raise RuntimeError("JWT_SECRET_KEY 环境变量必须设置！禁止使用默认值。生产环境请使用: secrets.token_hex(32) 生成强密钥。")
app.secret_key = _jwt_secret
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB upload limit
_allowed_origins = os.getenv('ALLOWED_ORIGINS', '')
if _allowed_origins:
    _origins = [o.strip() for o in _allowed_origins.split(',') if o.strip()]
    CORS(app, origins=_origins, supports_credentials=True)
else:
    CORS(app, supports_credentials=False)

@app.errorhandler(Exception)
def handle_exception(e):
    logger.exception('[全局异常处理器] 未捕获异常')
    return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500

from models.database import generate_order_no, get_connection
from models.order import OrderDAO
from utils.order_templates import (
    get_all_product_types, get_preset_fields,
    get_common_fields, get_remark_fields, DIM_FIELDS, MATERIAL_FIELDS,
    SURFACE_FIELD, MATERIAL_OPTS, SURFACE_OPTS,
    get_template_names, get_template, save_template,
    rename_template, delete_template,
)
from utils.validators import OrderValidator
from utils.material_calculator import MaterialCalculator
from utils.custom_types import (
    add_product_type, remove_product_type, get_product_types,
    get_custom_dim_params, add_custom_dim_param, remove_custom_dim_param,
    get_custom_mat_params, add_custom_mat_param, remove_custom_mat_param,
    get_surface_treatment_options, add_surface_treatment_option, remove_surface_treatment_option,
)
from core.exceptions import ValidationException


def _get_token():
    """从 session / cookie / header 拿调度中心 token"""
    return (
        request.headers.get('X-Dispatch-Token', '')
        or session.get('dispatch_token', '')
        or request.cookies.get('dispatch_token', '')
    )


def _call_dispatch(path, method='GET', **kwargs):
    """代理请求到 5003 调度中心,自动带 token"""
    token = _get_token()
    headers = kwargs.pop('headers', {})
    if token:
        headers['X-Dispatch-Token'] = token
    url = f'{DISPATCH_BASE}{path}'
    try:
        method = method.upper()
        if method == 'GET':
            r_params = kwargs.pop('params', None)
            if r_params is None and '?' in url:
                r_url = url.split('?', 1)[0]
                r_params = url.split('?', 1)[1]
            else:
                r_url = url
            r = requests.get(r_url, headers=headers, params=r_params, timeout=10)
        elif method == 'POST':
            r = requests.post(url, headers=headers, json=kwargs.get('json'), timeout=10)
        elif method == 'PUT':
            r = requests.put(url, headers=headers, json=kwargs.get('json'), timeout=10)
        elif method == 'DELETE':
            r = requests.delete(url, headers=headers, json=kwargs.get('json'), timeout=10)
        else:
            r = requests.post(url, headers=headers, json=kwargs.get('json'), timeout=10)
        try:
            return r.json(), r.status_code
        except Exception:
            return {'code': r.status_code, 'message': r.text[:200]}, r.status_code
    except requests.exceptions.ConnectionError:
        return {'code': -1, 'message': f'调度中心 {DISPATCH_BASE} 不可达'}, 503
    except Exception as e:
        {'code': -1, 'message': '服务器内部错误，请联系管理员'}, 500


# ════════════════════════════════════════════════════════════════
# 路由
# ════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    return redirect('/orders')


# 订单列表 (复刻 Tkinter OrderListView)
@app.route('/orders')
def orders_page():
    return render_template('orders.html')


@app.route('/orders/new')
def order_new_page():
    return render_template('order_new.html')


@app.route('/api/orders/create', methods=['POST'])
@require_auth
@verify_csrf_token
def api_orders_create():
    """新建订单 (直写 steel_belt.orders, 与桌面端共用数据源)"""
    try:
        data = request.get_json(silent=True) or {}
        data['order_no'] = generate_order_no()
        order_id = OrderDAO.create(data)
        logger.info(f"[订单创建] order_no={data['order_no']} id={order_id}")
        return jsonify({'code': 0, 'data': {'id': order_id, 'order_no': data['order_no']}, 'message': '订单创建成功'})
    except ValidationException as e:
        return jsonify({'code': 400, 'message': '服务器内部错误，请联系管理员'}), 400
    except Exception as e:
        logger.exception('[订单创建] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/orders/<int:order_id>')
def api_orders_get(order_id):
    """获取订单详情（编辑模式）- 对标桌面端 L163-241"""
    try:
        order = OrderDAO.get_by_id(order_id)
        if not order:
            return jsonify({'code': 404, 'message': '订单不存在'}), 404
        return jsonify({'code': 0, 'data': order})
    except Exception as e:
        logger.exception('[订单详情] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/orders/<int:order_id>', methods=['PUT'])
@require_auth
@verify_csrf_token
def api_orders_update(order_id):
    """更新订单（编辑模式）- 对标桌面端 L163-241"""
    try:
        data = request.get_json(silent=True) or {}
        data['id'] = order_id
        if 'status' in data and data['status']:
            from constants import validate_order_status_transition
            conn = get_connection()
            cur = None
            try:
                cur = conn.cursor()
                cur.execute("SELECT status FROM orders WHERE id=%s", (order_id,))
                row = cur.fetchone()
                if not row:
                    return jsonify({'code': 404, 'message': '订单不存在'}), 404
                current_status = row['status']
                cur.close()
                is_valid, msg = validate_order_status_transition(current_status, data['status'])
                if not is_valid:
                    return jsonify({'code': 400, 'message': msg}), 400
            finally:
                if cur: cur.close()
                conn.close()
        OrderDAO.update(order_id, data)
        logger.info(f"[订单更新] order_id={order_id}")
        return jsonify({'code': 0, 'message': '订单更新成功'})
    except ValidationException as e:
        return jsonify({'code': 400, 'message': '服务器内部错误，请联系管理员'}), 400
    except Exception as e:
        logger.exception('[订单更新] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/orders/unscheduled')
def api_orders_unscheduled():
    """获取未排产订单（已确认但未关联 production_orders）"""
    try:
        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT o.id, o.order_no, o.customer_name, o.customer_group,
                       o.product_type, o.material, o.quantity, o.unit,
                       COALESCE(o.total_amount, 0) AS total_amount,
                       COALESCE(o.delivery_date, '') AS delivery_date,
                       o.status, o.created_at
                FROM orders o
                LEFT JOIN production_orders po ON o.id = po.order_id
                WHERE po.id IS NULL
                  AND o.status NOT IN ('已取消', '已发货', '报工完成', '订单完成')
                  AND COALESCE(o.is_deleted, 0) = 0
                  AND COALESCE(o.is_archived, 0) = 0
                ORDER BY o.delivery_date ASC, o.created_at DESC
            """)
            rows = cur.fetchall()
            return jsonify({'code': 0, 'data': {'orders': [dict(r) for r in rows], 'total': len(rows)}}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[未排产订单] 查询失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/orders/product-types')
def api_orders_product_types():
    """产品类型列表 (含中文标签)"""
    try:
        product_types = get_all_product_types()
        return jsonify({'code': 0, 'data': product_types})
    except Exception as e:
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/orders/product-types', methods=['POST'])
@require_auth
@verify_csrf_token
def api_orders_add_product_type():
    """添加自定义产品类型 - 对标桌面端 L1774-1853"""
    try:
        data = request.get_json(silent=True) or {}
        name = data.get('name', '').strip()
        flow_type = data.get('flow_type', 'production')
        if not name:
            return jsonify({'code': 400, 'message': '产品类型名称不能为空'}), 400
        success, msg = add_product_type(name, flow_type)
        if success:
            return jsonify({'code': 0, 'message': msg, 'data': {'name': name}})
        return jsonify({'code': 400, 'message': msg}), 400
    except Exception as e:
        logger.exception('[添加产品类型] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/orders/product-types/<name>', methods=['DELETE'])
@require_auth
@verify_csrf_token
def api_orders_remove_product_type(name):
    """删除自定义产品类型 - 对标桌面端 L1860-1889"""
    try:
        from config import PRODUCT_TYPES
        if name in PRODUCT_TYPES:
            return jsonify({'code': 400, 'message': '默认产品类型无法删除'}), 400
        success, msg = remove_product_type(name)
        if success:
            return jsonify({'code': 0, 'message': msg})
        return jsonify({'code': 400, 'message': msg}), 400
    except Exception as e:
        logger.exception('[删除产品类型] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/orders/templates/<product_type>')
def api_orders_templates_list(product_type):
    """获取指定产品类型的模板列表 - 对标桌面端 L2011-2028"""
    try:
        names = get_template_names(product_type)
        return jsonify({'code': 0, 'data': names})
    except Exception as e:
        logger.exception('[模板列表] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/orders/templates/<product_type>/<name>')
def api_orders_template_get(product_type, name):
    """获取模板数据 - 对标桌面端 L2033-2122"""
    try:
        tpl = get_template(product_type, name)
        return jsonify({'code': 0, 'data': tpl})
    except Exception as e:
        logger.exception('[获取模板] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/orders/templates', methods=['POST'])
@require_auth
@verify_csrf_token
def api_orders_template_save():
    """保存模板 - 对标桌面端 L1979-2009"""
    try:
        data = request.get_json(silent=True) or {}
        pt = data.get('product_type', '').strip()
        name = data.get('name', '').strip()
        values = data.get('values', {})
        if not pt:
            return jsonify({'code': 400, 'message': '产品类型不能为空'}), 400
        if not name:
            return jsonify({'code': 400, 'message': '模板名称不能为空'}), 400
        ok, msg = save_template(pt, name, values)
        if ok:
            return jsonify({'code': 0, 'message': msg})
        return jsonify({'code': 400, 'message': msg}), 400
    except Exception as e:
        logger.exception('[保存模板] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/orders/templates/<product_type>/<name>', methods=['PUT'])
@require_auth
@verify_csrf_token
def api_orders_template_rename(product_type, name):
    """重命名模板 - 对标桌面端 L2130-2181"""
    try:
        data = request.get_json(silent=True) or {}
        new_name = data.get('new_name', '').strip()
        if not new_name:
            return jsonify({'code': 400, 'message': '新名称不能为空'}), 400
        ok, msg = rename_template(product_type, name, new_name)
        if ok:
            return jsonify({'code': 0, 'message': msg})
        return jsonify({'code': 400, 'message': msg}), 400
    except Exception as e:
        logger.exception('[重命名模板] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/orders/templates/<product_type>/<name>', methods=['DELETE'])
@require_auth
@verify_csrf_token
def api_orders_template_delete(product_type, name):
    """删除模板 - 对标桌面端 L2130-2181"""
    try:
        ok, msg = delete_template(product_type, name)
        if ok:
            return jsonify({'code': 0, 'message': msg})
        return jsonify({'code': 400, 'message': msg}), 400
    except Exception as e:
        logger.exception('[删除模板] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/orders/custom-params/dim')
def api_custom_dim_params():
    """获取自定义尺寸参数列表"""
    try:
        params = get_custom_dim_params()
        return jsonify({'code': 0, 'data': [{'name': n, 'unit': u} for n, u in params]})
    except Exception as e:
        logger.exception('[自定义尺寸参数] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/orders/custom-params/dim', methods=['POST'])
@require_auth
@verify_csrf_token
def api_add_custom_dim_param():
    """添加自定义尺寸参数"""
    try:
        data = request.get_json(silent=True) or {}
        name = data.get('name', '').strip()
        unit = data.get('unit', 'mm').strip() or 'mm'
        if not name:
            return jsonify({'code': 400, 'message': '参数名称不能为空'}), 400
        ok, msg = add_custom_dim_param(name, unit)
        if ok:
            return jsonify({'code': 0, 'message': msg, 'data': {'name': name, 'unit': unit}})
        return jsonify({'code': 400, 'message': msg}), 400
    except Exception as e:
        logger.exception('[添加尺寸参数] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/orders/custom-params/dim/<name>', methods=['DELETE'])
@require_auth
@verify_csrf_token
def api_remove_custom_dim_param(name):
    """删除自定义尺寸参数"""
    try:
        ok, msg = remove_custom_dim_param(name)
        if ok:
            return jsonify({'code': 0, 'message': msg})
        return jsonify({'code': 400, 'message': msg}), 400
    except Exception as e:
        logger.exception('[删除尺寸参数] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/orders/custom-params/mat')
def api_custom_mat_params():
    """获取自定义材质参数列表"""
    try:
        params = get_custom_mat_params()
        return jsonify({'code': 0, 'data': params})
    except Exception as e:
        logger.exception('[自定义材质参数] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/orders/custom-params/mat', methods=['POST'])
@require_auth
@verify_csrf_token
def api_add_custom_mat_param():
    """添加自定义材质参数"""
    try:
        data = request.get_json(silent=True) or {}
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'code': 400, 'message': '参数名称不能为空'}), 400
        ok, msg = add_custom_mat_param(name)
        if ok:
            return jsonify({'code': 0, 'message': msg, 'data': name})
        return jsonify({'code': 400, 'message': msg}), 400
    except Exception as e:
        logger.exception('[添加材质参数] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/orders/custom-params/mat/<name>', methods=['DELETE'])
@require_auth
@verify_csrf_token
def api_remove_custom_mat_param(name):
    """删除自定义材质参数"""
    try:
        ok, msg = remove_custom_mat_param(name)
        if ok:
            return jsonify({'code': 0, 'message': msg})
        return jsonify({'code': 400, 'message': msg}), 400
    except Exception as e:
        logger.exception('[删除材质参数] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/orders/custom-params/surface')
def api_surface_options():
    """获取表面处理选项（含自定义）"""
    try:
        opts = get_surface_treatment_options()
        return jsonify({'code': 0, 'data': opts})
    except Exception as e:
        logger.exception('[表面处理选项] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/orders/custom-params/surface', methods=['POST'])
@require_auth
@verify_csrf_token
def api_add_surface_option():
    """添加自定义表面处理方式"""
    try:
        data = request.get_json(silent=True) or {}
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'code': 400, 'message': '处理方式名称不能为空'}), 400
        ok, msg = add_surface_treatment_option(name)
        if ok:
            return jsonify({'code': 0, 'message': msg, 'data': name})
        return jsonify({'code': 400, 'message': msg}), 400
    except Exception as e:
        logger.exception('[添加表面处理] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/orders/custom-params/surface/<name>', methods=['DELETE'])
@require_auth
@verify_csrf_token
def api_remove_surface_option(name):
    """删除自定义表面处理方式"""
    try:
        ok, msg = remove_surface_treatment_option(name)
        if ok:
            return jsonify({'code': 0, 'message': msg})
        return jsonify({'code': 400, 'message': msg}), 400
    except Exception as e:
        logger.exception('[删除表面处理] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/orders/standard-fields')
def api_standard_fields():
    """获取全局标准参数字典（用于参数选择器）"""
    try:
        return jsonify({'code': 0, 'data': {
            'dim_fields': DIM_FIELDS,
            'mat_fields': MATERIAL_FIELDS,
        }})
    except Exception as e:
        logger.exception('[标准参数字典] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/orders/product-params/<product_type>')
def api_orders_product_params(product_type):
    """指定产品类型的完整参数字段定义"""
    try:
        product_type_escaped = str(product_type).replace('/', '_').replace('\\', '_')
        dim = get_preset_fields(product_type)
        common = get_common_fields()
        remark = get_remark_fields()
        return jsonify({'code': 0, 'data': {
            'dim_fields': dim.get('dim_fields', []),
            'mat_fields': dim.get('mat_fields', []),
            'common_fields': common,
            'remark_fields': remark,
            'material_opts': MATERIAL_OPTS,
            'surface_opts': SURFACE_OPTS,
        }})
    except Exception as e:
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/orders/preview-materials', methods=['POST'])
@require_auth
@verify_csrf_token
def api_orders_preview_materials():
    """物料计算预览 - 根据当前表单参数实时计算所需物料"""
    try:
        data = request.get_json(silent=True) or {}
        product_type = data.get('product_type', '')
        if not product_type:
            return jsonify({'code': 400, 'message': '产品类型不能为空'}), 400
        result = MaterialCalculator.preview_calculation(product_type, data)
        return jsonify({'code': 0, 'data': result})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/orders/upload-attachment', methods=['POST'])
@require_auth
@verify_csrf_token
def api_orders_upload_attachment():
    """上传订单附件 - 对标桌面端 L1614-1649：选择文件→复制到 data/attachments"""
    try:
        import shutil
        if 'file' not in request.files:
            return jsonify({'code': 400, 'message': '没有上传文件'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'code': 400, 'message': '文件名为空'}), 400

        attach_dir = PROJECT_ROOT / 'data' / 'attachments'
        attach_dir.mkdir(parents=True, exist_ok=True)

        filename = file.filename
        dst_path = attach_dir / filename
        counter = 1
        base, ext = os.path.splitext(filename)
        while dst_path.exists():
            dst_path = attach_dir / f"{base}_{counter}{ext}"
            counter += 1

        file.save(str(dst_path))
        rel_path = str(dst_path.relative_to(PROJECT_ROOT))
        return jsonify({
            'code': 0,
            'data': {
                'name': dst_path.name,
                'path': rel_path,
                'size': os.path.getsize(str(dst_path)),
            },
            'message': '上传成功'
        })
    except Exception as e:
        logger.exception('[附件上传] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


# 登录页(代理到 5003 dispatch_login)
@app.route('/login')
def login_page():
    return render_template('login.html')


# 代理: 登录
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json(silent=True) or {}
    # [P0 修复 2026-06-24] 自动把 name 转为 operator_id (5003的operator_id 字段才是主键)
    if 'name' in data and 'operator_id' not in data:
        try:
            r0 = requests.get(f'{DISPATCH_BASE}/api/dispatch-center/operators', timeout=3)
            if r0.status_code == 200:
                ops = r0.json().get('data') or []
                for op in ops:
                    if op.get('name') == data['name'] or op.get('wechat_userid') == data['name']:
                        # 5003字段: id/enterprise_id/wechat_userid
                        data['operator_id'] = op.get('id') or op.get('enterprise_id') or op.get('wechat_userid')
                        break
        except Exception:
            pass
    try:
        r = requests.post(f'{DISPATCH_BASE}/api/auth/login', json=data, timeout=5)
        body = r.json()
        if r.status_code == 200 and body.get('code') == 0:
            user = body['data']
            # [P0 修复 2026-06-23 小圣] 跨服务 token 协议冲突修复
            # 5003 鉴权协议: X-Dispatch-Token = base64("uid:uname")
            # 原代码: 5001 自己生成 secrets.token_hex(32) → 5003 拒/被绕过
            # 新代码: 5001 直接按 5003 协议生成 base64(uid:uname) 存 session,
            #         与前端 login.html 第53-54行的 base64 编码完全一致
            #         → _get_token() 拿到的 session 值就是 5003 可接受的 token
            uid = str(user.get('id', '') or '')
            uname = str(user.get('name', '') or '')
            dispatch_token = base64.b64encode(f'{uid}:{uname}'.encode('utf-8')).decode('utf-8')
            session['dispatch_token'] = dispatch_token
            session['dispatch_user'] = user
            session['csrf_token'] = _secrets.token_hex(16)
            body['data'] = {**user, 'csrf_token': session['csrf_token']}
        return jsonify(body), r.status_code
    except Exception as e:
        return jsonify({'code': -1, 'message': '服务器内部错误，请联系管理员'}), 500


# 代理: 订单列表
@app.route('/api/orders/list')
def api_orders_list():
    limit = request.args.get('limit', 100)
    status_filter = request.args.get('status_filter', 'all')
    body, status = _call_dispatch(f'/api/dispatch-center/order-status-list?limit={limit}&status_filter={status_filter}')
    return jsonify(body), status


# [P0-C 修复 2026-06-24] 越权访问防护 - 删除订单 (仅管理员)
@app.route('/api/orders/by-no/<path:order_no>', methods=['DELETE'])
@require_role('admin')
@verify_csrf_token
def api_orders_delete_by_no(order_no):
    """软删除订单（通过 order_no）"""
    list_body, _ = _call_dispatch('/api/dispatch-center/order-status-list?limit=200')
    target = None
    if list_body.get('code') == 0:
        for o in (list_body.get('data') or {}).get('orders') or []:
            if o.get('order_no') == order_no:
                target = o
                break
    if not target:
        return jsonify({'code': 404, 'message': '订单不存在'}), 404
    try:
        from models.database import get_connection
        conn = get_connection()
        try:
            cur = conn.cursor()
            try:
                cur.execute("UPDATE orders SET is_deleted=1, deleted_at=NOW() WHERE order_no=%s", (order_no,))
                conn.commit()
                return jsonify({'code': 0, 'data': {'order_no': order_no, 'message': '已软删除'}})
            finally:
                cur.close()
        finally:
            conn.close()
    except Exception as e:
        return jsonify({'code': 500, 'message': f'删除失败: {e}'}), 500


@app.route('/api/orders/by-no/<path:order_no>/detail')
def api_orders_detail_by_no(order_no):
    """订单详情（通过 order_no）"""
    list_body, _ = _call_dispatch('/api/dispatch-center/order-status-list?limit=200')
    order_data = {}
    if list_body.get('code') == 0:
        for o in (list_body.get('data') or {}).get('orders') or []:
            if o.get('order_no') == order_no:
                order_data = o
                break
    return jsonify({
        'code': 0,
        'data': {
            'order': order_data,
            'processes': [],
        }
    })


@app.route('/api/orders/by-no/<path:order_no>/print')
def api_orders_print_by_no(order_no):
    """订单打印（通过 order_no，含敏感字段过滤）"""
    list_body, _ = _call_dispatch('/api/dispatch-center/order-status-list?limit=200')
    order_data = {}
    if list_body.get('code') == 0:
        for o in (list_body.get('data') or {}).get('orders') or []:
            if o.get('order_no') == order_no:
                order_data = o
                break
    if not order_data:
        return jsonify({'code': 404, 'message': '订单不存在'}), 404
    safe_order = {k: v for k, v in order_data.items() if k not in ('cost', 'unit_cost', 'total_cost', 'profit', 'margin')}
    return jsonify({'code': 0, 'data': {'order': safe_order}})


@app.route('/order-query')
def order_query_page():
    return render_template('order_query.html')


@app.route('/api/orders/query')
def api_orders_query():
    """高级订单查询（条件+分页）"""
    qs = request.query_string.decode('utf-8')
    path = '/api/dispatch-center/order-status-list?' + qs if qs else '/api/dispatch-center/order-status-list'
    body, status = _call_dispatch(path)
    if body.get('code') == 0 and isinstance(body.get('data'), dict):
        orders = body['data'].get('orders') or []
        page = int(request.args.get('page', 1))
        size = int(request.args.get('page_size', 20))
        kw = request.args.get('keyword', '').strip().lower()
        st = request.args.get('status', '').strip()
        grp = request.args.get('customer_group', '').strip()
        prod = request.args.get('product_type', '').strip()
        df = request.args.get('date_from', '').strip()
        dt = request.args.get('date_to', '').strip()
        qmin = request.args.get('qty_min', '').strip()
        qmax = request.args.get('qty_max', '').strip()
        def match(o):
            if kw and kw not in (str(o.get('order_no','')) + str(o.get('customer_name','')) + str(o.get('product_name','')) ).lower(): return False
            if st and o.get('order_status') != st: return False
            if grp and o.get('customer_group') != grp: return False
            if prod and o.get('product_type') != prod and o.get('product_name') != prod: return False
            if df and (o.get('delivery_date','') < df): return False
            if dt and (o.get('delivery_date','') > dt): return False
            if qmin and (o.get('quantity',0) < float(qmin)): return False
            if qmax and (o.get('quantity',0) > float(qmax)): return False
            return True
        filtered = [o for o in orders if match(o)]
        total = len(filtered)
        start = (page - 1) * size
        items = filtered[start:start+size]
        pages = (total + size - 1) // size
        body['data'] = {'items': items, 'total': total, 'pages': pages, 'page': page, 'size': size}
    return jsonify(body), status


# 代理: 调度中心概览
@app.route('/api/overview')
def api_overview():
    body, status = _call_dispatch('/api/dispatch-center/status')
    return jsonify(body), status


# 代理: 操作员列表 - 从 5003 企业架构读取
@app.route('/api/operators')
def api_operators():
    """通过 5003 企业架构读取操作员（统一数据源）"""
    body, status = _call_dispatch('/api/enterprise/operators')
    return jsonify(body), status


# 代理: 企业架构（部门+操作员结构）
@app.route('/api/enterprise/structure')
def api_enterprise_structure():
    """从 5003 获取企业架构数据"""
    body, status = _call_dispatch('/api/enterprise/structure')
    return jsonify(body), status


@app.route('/api/enterprise/operators', methods=['GET'])
def api_enterprise_operators_list():
    """从 5003 列出企业架构操作员"""
    body, status = _call_dispatch('/api/enterprise/operators')
    return jsonify(body), status


@app.route('/api/operators/list')
def api_operators_list():
    """分页+筛选的操作员列表（从企业架构读取）"""
    body, status = _call_dispatch('/api/enterprise/operators')
    if body.get('code') == 0:
        items = body.get('data', {}).get('items', [])
        # 筛选
        kw = request.args.get('name', '').strip()
        department = request.args.get('department', '').strip()
        role = request.args.get('role', '').strip()
        is_active = request.args.get('is_active', '').strip()
        if kw:
            items = [op for op in items if kw in op.get('name', '')]
        if department:
            items = [op for op in items if op.get('department') == department]
        if role:
            items = [op for op in items if op.get('role') == role]
        # 角色映射: active ↔ enabled
        if is_active == '1':
            items = [op for op in items if op.get('enabled') is not False]
        elif is_active == '0':
            items = [op for op in items if op.get('enabled') is False]
        body['data']['items'] = items
        body['data']['list'] = items
        body['data']['total'] = len(items)
        # 角色统计
        role_dist = {}
        for op in items:
            r = op.get('role', '员工')
            role_dist[r] = role_dist.get(r, 0) + 1
        body['data']['role_dist'] = [{'role': k, 'count': v} for k, v in role_dist.items()]
        # 部门统计
        dept_dist = {}
        for op in items:
            d = op.get('department', '') or '未分配'
            dept_dist[d] = dept_dist.get(d, 0) + 1
        body['data']['dept_dist'] = [{'department': k, 'count': v} for k, v in dept_dist.items()]
    return jsonify(body), status


# ── 阶段五: 操作员CRUD增强 ────────────────────────────────────────
import hashlib, secrets


def _hash_pwd(password: str, salt: str) -> str:
    h = hashlib.sha256()
    h.update((salt + password).encode('utf-8'))
    return h.hexdigest()


@app.route('/api/operators', methods=['POST'])
@require_role('admin')
@verify_csrf_token
def api_operator_create():
    """通过 5003 企业架构创建操作员（统一数据源）"""
    try:
        data = request.get_json(silent=True) or {}
        if not data.get('name'):
            return jsonify({'code': 400, 'message': '姓名必填'}), 400
        # 转交 5003
        body, status = _call_dispatch('/api/enterprise/operators', method='POST', json=data)
        return jsonify(body), status
    except Exception as e:
        logger.exception('[操作员新增] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/operators/<operator_id>', methods=['PUT'])
@require_auth
@verify_csrf_token
def api_operator_update(operator_id):
    """通过 5003 企业架构更新操作员"""
    try:
        data = request.get_json(silent=True) or {}
        # 转换 is_active → enabled
        if 'is_active' in data:
            data['enabled'] = data.pop('is_active') not in (0, False, '0', 'inactive')
        body, status = _call_dispatch(f'/api/enterprise/operators/{operator_id}', method='PUT', json=data)
        return jsonify(body), status
    except Exception as e:
        logger.exception('[操作员更新] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


# [P0-C 修复 2026-06-24] 越权访问防护 - 停用操作员 (仅管理员)
@app.route('/api/operators/<operator_id>', methods=['DELETE'])
@require_role('admin')
@verify_csrf_token
def api_operator_delete(operator_id):
    """通过 5003 企业架构停用操作员"""
    try:
        body, status = _call_dispatch(f'/api/enterprise/operators/{operator_id}', method='DELETE')
        return jsonify(body), status
    except Exception as e:
        logger.exception('[操作员删除] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/operators/<operator_id>/stats')
def api_operator_stats(operator_id):
    try:
        month = request.args.get('month', datetime.now().strftime('%Y-%m'))
        from models.database import get_connection
        conn = get_connection()
        try:
            cur = conn.cursor()
            try:
                cur.execute("""
                    SELECT COALESCE(SUM(work_hours), 0) AS total_hours,
                           COALESCE(SUM(completed_qty), 0) AS total_qty,
                           COALESCE(SUM(qualified_qty), 0) AS total_qualified,
                           COUNT(*) AS report_count
                    FROM workreport_records
                    WHERE worker_id=%s AND DATE_FORMAT(report_time, '%%Y-%%m')=%s
                """, (operator_id, month))
                row = cur.fetchone()
            finally:
                cur.close()
        finally:
            conn.close()
        stats = dict(row) if row else {'total_hours': 0, 'total_qty': 0, 'total_qualified': 0, 'report_count': 0}
        total_qty = stats.get('total_qty') or 0
        total_q = stats.get('total_qualified') or 0
        stats['qualify_rate'] = round((total_q / total_qty * 100) if total_qty else 0, 1)
        return jsonify({'code': 0, 'data': {'operator_id': operator_id, 'month': month, **stats}})
    except Exception as e:
        logger.exception('[操作员统计] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/operators/template')
def api_operator_template():
    try:
        from flask import send_file
        path = generate_operator_template()
        return send_file(path, as_attachment=True,
                         download_name='操作员导入模板.xlsx',
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        logger.exception('[操作员模板] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/operators/export')
def api_operator_export():
    """从 5003 企业架构读操作员数据并导出 Excel"""
    try:
        from flask import send_file
        body, _ = _call_dispatch('/api/enterprise/operators')
        if body.get('code') != 0:
            return jsonify(body), 500
        operators = body.get('data', {}).get('items', [])
        # 转换字段以适配 build_operator_export 期望的格式
        from datetime import datetime as _dt
        for o in operators:
            o['is_active'] = o.get('enabled', True)
            if not o.get('last_login'):
                o['last_login'] = None
            if o.get('created_at') and isinstance(o['created_at'], str):
                try: o['created_at'] = _dt.fromisoformat(o['created_at'])
                except: o['created_at'] = None

        stats_map = {}
        if operators:
            from models.database import get_connection
            valid_oids = [o.get('operator_id') or o.get('id') for o in operators if o.get('operator_id') or o.get('id')]
            if valid_oids:
                conn = get_connection()
                try:
                    cur = conn.cursor()
                    try:
                        placeholders = ','.join(['%s'] * len(valid_oids))
                        cur.execute(f"""
                            SELECT worker_id,
                                   COALESCE(SUM(work_hours), 0) AS total_hours,
                                   COALESCE(SUM(completed_qty), 0) AS total_qty,
                                   COALESCE(SUM(qualified_qty), 0) AS total_qualified
                            FROM workreport_records
                            WHERE worker_id IN ({placeholders})
                              AND DATE_FORMAT(report_time, '%%Y-%%m')=DATE_FORMAT(NOW(), '%%Y-%%m')
                            GROUP BY worker_id
                        """, tuple(valid_oids))
                        for row in cur.fetchall():
                            s = dict(row)
                            tq = s.get('total_qty') or 0
                            tf = s.get('total_qualified') or 0
                            s['qualify_rate'] = round((tf / tq * 100) if tq else 0, 1)
                            stats_map[row['worker_id']] = s
                    finally:
                        cur.close()
                finally:
                    conn.close()

        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        fname = f'操作员导出_{ts}.xlsx'
        path = build_operator_export(operators, stats_map, fname)
        return send_file(path, as_attachment=True,
                         download_name=fname,
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        logger.exception('[操作员导出] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/operators/import', methods=['POST'])
@require_auth
@verify_csrf_token
def api_operator_import():
    """通过 5003 企业架构批量创建操作员"""
    try:
        if 'file' not in request.files:
            return jsonify({'code': 400, 'message': '请上传 Excel 文件'}), 400
        f = request.files['file']
        if not f.filename.endswith(('.xlsx', '.xls')):
            return jsonify({'code': 400, 'message': '仅支持 .xlsx / .xls 格式'}), 400
        parsed = parse_operator_import(f)
        valid = parsed.get('valid', [])
        errors = parsed.get('errors', [])
        created, skipped, failed = 0, 0, 0
        for idx, item in enumerate(valid):
            try:
                op_id = item.get('operator_id', '').strip()
                if not op_id:
                    op_id = item.get('wechat_userid', '').strip() or f'OP_{idx:04d}'
                # 检查已存在
                check_body, _ = _call_dispatch(f'/api/enterprise/operators')
                if check_body.get('code') == 0:
                    existing = {op.get('operator_id') for op in check_body.get('data', {}).get('items', [])}
                    if op_id in existing:
                        skipped += 1
                        continue
                # 调用 5003 创建
                payload = {
                    'operator_id': op_id,
                    'name': item.get('name', ''),
                    'role': item.get('role', '员工') or '员工',
                    'department': item.get('department', ''),
                    'wechat_userid': op_id,
                    'phone': item.get('phone', ''),
                }
                r_body, r_status = _call_dispatch('/api/enterprise/operators', method='POST', json=payload)
                if r_body.get('code') == 0:
                    created += 1
                elif r_status == 400 and '已存在' in r_body.get('message', ''):
                    skipped += 1
                else:
                    failed += 1
                    errors.append({'row': idx + 2, 'msg': r_body.get('message', '未知错误')[:80]})
            except Exception as e:
                failed += 1
                errors.append({'row': idx + 2, 'msg': str(e)[:80]})
        return jsonify({
            'code': 0,
            'data': {
                'created': created, 'skipped': skipped, 'failed': failed,
                'errors': errors, 'total': len(valid) + len(errors),
            },
            'message': f'导入完成：成功 {created} 条，跳过 {skipped} 条，失败 {failed} 条'
        })
    except Exception as e:
        logger.exception('[操作员导入] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/operators')
def operators_page():
    return render_template('operators.html')


# 看板页面 (复刻 Tkinter KanbanView)
@app.route('/kanban')
def kanban_page():
    return render_template('kanban.html')


# 代理: 看板数据
@app.route('/api/kanban/list')
def api_kanban_list():
    limit = request.args.get('limit', 200)
    body, status = _call_dispatch(f'/api/dispatch-center/kanban/list?limit={limit}')
    return jsonify(body), status


# 生产排单页面 (复刻 Tkinter ProductionView)
@app.route('/production')
def production_page():
    return render_template('production.html')


# 排产页面 (兼容老路由, 重定向到 /production)
@app.route('/scheduling')
def scheduling_page():
    return render_template('production.html')


# 生产排单管理页面（完整 CRUD）
@app.route('/production-admin')
def production_admin_page():
    return render_template('production_admin.html')


# 代理: 生产排单
@app.route('/api/production/list')
def api_production_list():
    qs = request.query_string.decode('utf-8')
    body, status = _call_dispatch(f'/api/dispatch-center/production/list?{qs}' if qs else '/api/dispatch-center/production/list')
    return jsonify(body), status


# 物料备料页面 (复刻 Tkinter MaterialPrepView)
@app.route('/material')
def material_page():
    return render_template('material.html')


# 物料备料管理页面（完整 CRUD）
@app.route('/material-admin')
def material_admin_page():
    return render_template('material_admin.html')


# ── 物料备料 CRUD（直写 order_materials 表，与桌面端一致） ─────────────────

@app.route('/api/material/add', methods=['POST'])
@require_auth
@verify_csrf_token
def api_material_add():
    """新增物料到订单"""
    try:
        body = request.get_json(silent=True) or {}
        order_id = body.get('order_id')
        material_name = (body.get('material_name') or '').strip()
        if not order_id or not material_name:
            return jsonify({'code': 400, 'message': '缺少 order_id 或 material_name'}), 400

        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id FROM order_materials WHERE order_id=%s AND material_name=%s LIMIT 1",
                (order_id, material_name)
            )
            if cur.fetchone():
                return jsonify({'code': 400, 'message': f'物料「{material_name}」已存在，请勿重复添加'}), 400

            required = float(body.get('required_qty') or 0)
            status = '缺料' if required > 0 else '待备料'
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            cur.execute("""
                INSERT INTO order_materials (order_id, material_name, material_type, unit,
                    required_qty, prepared_qty, prep_status, remark, locked, updated_at)
                VALUES (%s,%s,%s,%s,%s,0,%s,%s,0,%s)
            """, (
                order_id, material_name,
                body.get('material_type', ''),
                body.get('unit', '米'),
                required, status,
                body.get('remark', ''), now
            ))
            mat_id = cur.lastrowid
            conn.commit()

            _save_material_history(order_id, '添加物料', material_name,
                {'required': required, 'unit': body.get('unit', '米')})

            return jsonify({'code': 0, 'message': '物料添加成功', 'data': {'id': mat_id}}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[物料新增] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/material/edit/<int:mat_id>', methods=['PUT'])
@require_auth
@verify_csrf_token
def api_material_edit(mat_id):
    """编辑物料"""
    try:
        body = request.get_json(silent=True) or {}
        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            # [P1-4 修复 2026-06-24] FOR UPDATE 行级锁 - 防止 TOCTOU 竞态
            # 场景: SELECT 后 UPDATE 前，其他事务修改 locked=1 → 越权编辑
            cur.execute("SELECT * FROM order_materials WHERE id=%s FOR UPDATE", (mat_id,))
            old = cur.fetchone()
            if not old:
                return jsonify({'code': 404, 'message': '物料不存在'}), 404

            if old['locked']:
                conn.rollback()
                return jsonify({'code': 400, 'message': '该物料已锁定，请先解锁'}), 400

            req = float(body.get('required_qty') or 0)
            prep = float(body.get('prepared_qty') or 0)
            if prep == 0 and req > 0: status = '缺料'
            elif prep < req: status = '部分缺料'
            elif prep >= req: status = '已备齐'
            else: status = '待备料'

            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cur.execute("""
                UPDATE order_materials SET
                    spec=%s, unit=%s, required_qty=%s, prepared_qty=%s,
                    prep_status=%s, remark=%s, updated_at=%s
                WHERE id=%s
            """, (
                body.get('spec', ''), body.get('unit', '米'),
                req, prep, status,
                body.get('remark', ''), now, mat_id
            ))
            conn.commit()

            _save_material_history(old['order_id'], '编辑物料', old['material_name'],
                {'old_prepared': old['prepared_qty'], 'new_prepared': prep})

            return jsonify({'code': 0, 'message': '物料已更新'}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[物料编辑] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/material/unlock/<int:mat_id>', methods=['PUT'])
@require_auth
@verify_csrf_token
def api_material_unlock(mat_id):
    """解锁物料"""
    try:
        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM order_materials WHERE id=%s", (mat_id,))
            m = cur.fetchone()
            if not m:
                return jsonify({'code': 404, 'message': '物料不存在'}), 404
            if not m['locked']:
                return jsonify({'code': 0, 'message': '已是解锁状态'}), 200

            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cur.execute("UPDATE order_materials SET locked=0, updated_at=%s WHERE id=%s", (now, mat_id))
            conn.commit()

            _save_material_history(m['order_id'], '解锁物料', m['material_name'], {})

            return jsonify({'code': 0, 'message': '物料已解锁'}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[物料解锁] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/material/mark-done/<int:mat_id>', methods=['PUT'])
@require_auth
@verify_csrf_token
def api_material_mark_done(mat_id):
    """标记物料已备齐"""
    try:
        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM order_materials WHERE id=%s", (mat_id,))
            m = cur.fetchone()
            if not m:
                return jsonify({'code': 404, 'message': '物料不存在'}), 404

            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cur.execute(
                "UPDATE order_materials SET prepared_qty=required_qty, prep_status='已备齐', updated_at=%s WHERE id=%s",
                (now, mat_id)
            )
            conn.commit()

            _save_material_history(m['order_id'], '标记已备齐', m['material_name'], {})

            return jsonify({'code': 0, 'message': '已标记为已备齐'}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[物料标记已备齐] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/material/add-qty/<int:mat_id>', methods=['PUT'])
@require_auth
@verify_csrf_token
def api_material_add_qty(mat_id):
    """物料添加入库数量（带并发锁保护）"""
    try:
        body = request.get_json(silent=True) or {}
        add_qty = float(body.get('add_qty') or 0)
        if add_qty <= 0:
            return jsonify({'code': 400, 'message': '入库数量必须大于0'}), 400

        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM order_materials WHERE id=%s FOR UPDATE", (mat_id,))
            m = cur.fetchone()
            if not m:
                return jsonify({'code': 404, 'message': '物料不存在'}), 404

            new_prep = (m['prepared_qty'] or 0) + add_qty
            req = m['required_qty'] or 0
            if new_prep >= req: status = '已备齐'
            elif new_prep > 0: status = '部分缺料'
            else: status = '缺料'

            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cur.execute(
                "UPDATE order_materials SET prepared_qty=%s, prep_status=%s, updated_at=%s WHERE id=%s",
                (new_prep, status, now, mat_id)
            )
            conn.commit()

            detail = {'add_qty': add_qty, 'unit': m['unit'] or '', 'total': new_prep}
            batch_no = body.get('batch_no', '').strip()
            if batch_no: detail['batch_no'] = batch_no
            remark = body.get('remark', '').strip()
            if remark: detail['remark'] = remark

            _save_material_history(m['order_id'], '物料入库', m['material_name'], detail)

            return jsonify({'code': 0, 'message': f'入库成功，{m["material_name"]} 现已备 {new_prep}'}), 200
        except Exception as e:
            conn.rollback()
            logger.exception('[物料入库] 失败')
            return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[物料入库] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


# [P0-C 修复 2026-06-24] 越权访问防护 - 删除物料 (管理员/班组长)
@app.route('/api/material/delete/<int:mat_id>', methods=['DELETE'])
@require_role('admin', 'manager')
@verify_csrf_token
def api_material_delete(mat_id):
    """删除物料"""
    try:
        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("SELECT order_id, material_name FROM order_materials WHERE id=%s", (mat_id,))
            m = cur.fetchone()
            if not m:
                return jsonify({'code': 404, 'message': '物料不存在'}), 404

            # [P1-3 修复 2026-06-24] 软删除（符合 R-113 规则）
            try:
                cur.execute("""
                    UPDATE order_materials SET is_deleted=1, updated_at=NOW()
                    WHERE id=%s
                """, (mat_id,))
            except Exception:
                # 字段不存在时回退硬删除
                cur.execute("DELETE FROM order_materials WHERE id=%s", (mat_id,))
            conn.commit()

            _save_material_history(m['order_id'], '删除物料', m['material_name'], {})

            return jsonify({'code': 0, 'message': '物料已删除'}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[物料删除] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/material/mark-all-done', methods=['PUT'])
@require_auth
@verify_csrf_token
def api_material_mark_all_done():
    """全部标记已备齐"""
    try:
        body = request.get_json(silent=True) or {}
        order_id = body.get('order_id')
        if not order_id:
            return jsonify({'code': 400, 'message': '缺少 order_id'}), 400

        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cur.execute(
                "UPDATE order_materials SET prepared_qty=required_qty, prep_status='已备齐', updated_at=%s WHERE order_id=%s",
                (now, order_id)
            )
            conn.commit()

            _save_material_history(order_id, '全部标记已备齐', '全部物料', {})

            return jsonify({'code': 0, 'message': '全部物料已标记为已备齐'}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[全部标记已备齐] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


# [P0-C 修复 2026-06-24] 越权访问防护 - 重置备料 (管理员/班组长)
@app.route('/api/material/reset', methods=['PUT'])
@require_role('admin', 'manager')
@verify_csrf_token
def api_material_reset():
    """重置备料"""
    try:
        body = request.get_json(silent=True) or {}
        order_id = body.get('order_id')
        if not order_id:
            return jsonify({'code': 400, 'message': '缺少 order_id'}), 400

        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cur.execute(
                "UPDATE order_materials SET prepared_qty=0, prep_status='待备料', updated_at=%s WHERE order_id=%s",
                (now, order_id)
            )
            conn.commit()

            _save_material_history(order_id, '重置备料', '全部物料', {})

            return jsonify({'code': 0, 'message': '备料已重置'}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[重置备料] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/material/calculate', methods=['POST'])
@require_auth
@verify_csrf_token
def api_material_calculate():
    """计算物料（调用 MaterialCalculator）"""
    try:
        body = request.get_json(silent=True) or {}
        order_id = body.get('order_id')
        if not order_id:
            return jsonify({'code': 400, 'message': '缺少 order_id'}), 400

        from models.order import OrderDAO
        order = OrderDAO.get_by_id(order_id)
        if not order:
            return jsonify({'code': 404, 'message': '订单不存在'}), 404

        import json
        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) as cnt FROM order_materials WHERE order_id=%s", (order_id,))
            cnt = cur.fetchone()['cnt']

            if cnt > 0:
                cur.execute("DELETE FROM order_materials WHERE order_id=%s", (order_id,))
                conn.commit()

            order_params = {
                'product_type': order.get('product_type', ''),
                'quantity': order.get('quantity', 0),
                'unit': order.get('unit', '米')
            }
            extra = order.get('extra_params') or {}
            if isinstance(extra, str):
                try: extra = json.loads(extra)
                except Exception: extra = {}
            order_params.update(extra)

            calculator = MaterialCalculator(order_params)
            materials = calculator.calculate_material_types()

            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            total = 0
            for m in materials:
                spec_text = ''
                if m.get('spec_value'):
                    spec_text = f"{m['spec_value']}{m.get('spec_unit', '')}"
                required_qty = m.get('qty_value') if m.get('qty_value') is not None else 0
                unit = m.get('qty_unit') or '待定'

                cur.execute("""
                    INSERT INTO order_materials (order_id, material_name, spec, unit,
                        required_qty, prepared_qty, prep_status, locked, created_at)
                    VALUES (%s,%s,%s,%s,%s,0,'待备料',0,%s)
                """, (order_id, m['material_name'], spec_text, unit, required_qty, now))
                total += 1

            conn.commit()
            return jsonify({'code': 0, 'message': f'物料计算完成，已添加 {total} 种物料', 'data': {'count': total}}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[物料计算] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/material/history')
def api_material_history():
    """物料历史记录"""
    try:
        order_id = request.args.get('order_id')
        limit = int(request.args.get('limit', 50))
        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            if order_id:
                cur.execute(
                    "SELECT * FROM material_history WHERE order_id=%s ORDER BY created_at DESC LIMIT %s",
                    (order_id, limit)
                )
            else:
                cur.execute("SELECT * FROM material_history ORDER BY created_at DESC LIMIT %s", (limit,))
            rows = cur.fetchall()
            return jsonify({'code': 0, 'data': [dict(r) for r in rows]}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[物料历史] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/material/template', methods=['POST'])
@require_auth
@verify_csrf_token
def api_material_template_save():
    """保存物料模板"""
    try:
        body = request.get_json(silent=True) or {}
        from utils.material_templates import get_template as _check_tpl, save_template as _save_tpl
        name = (body.get('name') or '').strip()
        if not name:
            return jsonify({'code': 400, 'message': '模板名称不能为空'}), 400
        existing = _check_tpl(name)
        if existing:
            return jsonify({'code': 400, 'message': f'模板「{name}」已存在，请使用其他名称'}), 400
        materials = body.get('materials') or []
        description = body.get('description') or ''
        ok, msg = _save_tpl(name, materials, description)
        if ok:
            return jsonify({'code': 0, 'message': msg}), 200
        return jsonify({'code': 400, 'message': msg}), 400
    except Exception as e:
        logger.exception('[保存物料模板] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/material/template/list')
def api_material_template_list():
    """物料模板列表"""
    try:
        from utils.material_templates import get_all_templates as _get_all
        templates = _get_all()
        return jsonify({'code': 0, 'data': templates}), 200
    except Exception as e:
        logger.exception('[物料模板列表] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/material/template/apply', methods=['POST'])
@require_auth
@verify_csrf_token
def api_material_template_apply():
    """应用物料模板"""
    try:
        body = request.get_json(silent=True) or {}
        order_id = body.get('order_id')
        template_name = (body.get('template_name') or '').strip()
        mode = body.get('mode', 'append')
        if not order_id or not template_name:
            return jsonify({'code': 400, 'message': '缺少参数'}), 400

        from utils.material_templates import get_template as _get_tpl
        template = _get_tpl(template_name)
        if not template:
            return jsonify({'code': 404, 'message': '模板不存在'}), 404

        mats = template.get('materials') or []
        if not mats:
            return jsonify({'code': 400, 'message': '模板为空'}), 400

        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            if mode == 'replace':
                cur.execute("DELETE FROM order_materials WHERE order_id=%s", (order_id,))

            added = 0
            for mat in mats:
                mat_name = mat.get('name', '') or mat.get('material_name', '')
                if not mat_name:
                    continue
                cur.execute(
                    "SELECT id FROM order_materials WHERE order_id=%s AND material_name=%s LIMIT 1",
                    (order_id, mat_name)
                )
                if cur.fetchone():
                    continue
                required = float(mat.get('required_qty') or 0)
                status = '缺料' if required > 0 else '待备料'
                cur.execute("""
                    INSERT INTO order_materials (order_id, material_name, unit, required_qty,
                        prepared_qty, prep_status, remark, updated_at)
                    VALUES (%s,%s,%s,%s,0,%s,%s,%s)
                """, (order_id, mat_name, mat.get('unit', '米'), required, status,
                      mat.get('remark', ''), now))
                added += 1

            conn.commit()

            _save_material_history(order_id, '载入模板', template_name,
                {'mode': mode, 'added_count': added})

            return jsonify({'code': 0, 'message': f'模板「{template_name}」已应用，添加了 {added} 种物料'}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[应用物料模板] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


def _save_material_history(order_id, action, material_name, detail=None):
    """内部方法：保存物料操作历史"""
    try:
        conn = get_connection()
        try:
            cur = conn.cursor()
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            detail_str = str(detail) if detail else ''
            cur.execute("""
                INSERT INTO material_history (order_id, action, material_name, detail, created_at)
                VALUES (%s,%s,%s,%s,%s)
            """, (order_id, action, material_name, detail_str, now))
            conn.commit()
        finally:
            cur.close()
            conn.close()
    except Exception as e:
        logger.warning(f'[_save_material_history] 失败: {e}')


# 代理: 物料备料
@app.route('/api/material/list')
@require_auth
def api_material_list():
    qs = request.query_string.decode('utf-8')
    body, status = _call_dispatch(f'/api/dispatch-center/material/list?{qs}' if qs else '/api/dispatch-center/material/list')
    return jsonify(body), status


# 质检页面 (复刻 Tkinter QualityView)
@app.route('/quality')
def quality_page():
    return render_template('quality.html')


# 代理: 质检记录
@app.route('/api/quality/list')
def api_quality_list():
    qs = request.query_string.decode('utf-8')
    body, status = _call_dispatch(f'/api/dispatch-center/quality/list?{qs}' if qs else '/api/dispatch-center/quality/list')
    return jsonify(body), status


# Dashboard 大屏页面
@app.route('/dashboard')
def dashboard_page():
    return render_template('dashboard.html')


# 代理: Dashboard 汇总
@app.route('/api/dashboard/summary')
def api_dashboard_summary():
    body, status = _call_dispatch('/api/dispatch-center/dashboard/summary')
    return jsonify(body), status


# 健康检查
@app.route('/health')
def health():
    return jsonify({'code': 0, 'data': {'service': 'desktop_web', 'port': 5001, 'dispatch': DISPATCH_BASE}})


# 报工记录页面
@app.route('/work-reports')
def work_reports_page():
    return render_template('work_reports.html')


# 代理: 报工记录列表
@app.route('/api/work-reports/list')
def api_work_reports_list():
    qs = request.query_string.decode('utf-8')
    body, status = _call_dispatch(f'/api/dispatch-center/report-queue/list?{qs}' if qs else '/api/dispatch-center/report-queue/list')
    return jsonify(body), status


@app.route('/api/work-reports/retry', methods=['POST'])
@require_auth
@verify_csrf_token
def api_work_reports_retry():
    data = request.get_json() or {}
    rq_id = data.get('id')
    if not rq_id:
        return jsonify({'code': 400, 'message': '缺少 id 参数'}), 400
    body, status = _call_dispatch(f'/api/dispatch-center/report-queue/{rq_id}/retry', method='POST', json=data)
    return jsonify(body), status


# ── 发货管理 ───────────────────────────────────────────────────
@app.route('/shipment')
def shipment_page():
    return render_template('shipment.html')


@app.route('/api/shipment/list')
def api_shipment_list():
    qs = request.query_string.decode('utf-8')
    path = '/api/dispatch-center/shipping/list?' + qs if qs else '/api/dispatch-center/shipping/list'
    body, status = _call_dispatch(path)
    return jsonify(body), status


@app.route('/api/shipment/pending')
def api_shipment_pending():
    qs = request.query_string.decode('utf-8')
    path = '/api/dispatch-center/shipping/pending?' + qs if qs else '/api/dispatch-center/shipping/pending'
    body, status = _call_dispatch(path)
    return jsonify(body), status


@app.route('/api/shipment/create', methods=['POST'])
@require_auth
@verify_csrf_token
def api_shipment_create():
    data = request.get_json() or {}
    body, status = _call_dispatch('/api/dispatch-center/shipping/create', method='POST', json=data)
    return jsonify(body), status


@app.route('/api/shipment/confirm-ship', methods=['POST'])
@require_auth
@verify_csrf_token
def api_shipment_confirm_ship():
    data = request.get_json() or {}
    body, status = _call_dispatch('/api/dispatch-center/shipping/confirm-ship', method='POST', json=data)
    return jsonify(body), status


@app.route('/api/shipment/confirm-receive', methods=['POST'])
@require_auth
@verify_csrf_token
def api_shipment_confirm_receive():
    data = request.get_json() or {}
    body, status = _call_dispatch('/api/dispatch-center/shipping/confirm-receive', method='POST', json=data)
    return jsonify(body), status


@app.route('/api/shipment/tracking-list')
def api_shipment_tracking_list():
    qs = request.query_string.decode('utf-8')
    path = '/api/dispatch-center/shipping/tracking-list?' + qs if qs else '/api/dispatch-center/shipping/tracking-list'
    body, status = _call_dispatch(path)
    return jsonify(body), status


@app.route('/api/shipment/finished-goods')
def api_shipment_finished_goods():
    qs = request.query_string.decode('utf-8')
    path = '/api/dispatch-center/shipping/finished-goods?' + qs if qs else '/api/dispatch-center/shipping/finished-goods'
    body, status = _call_dispatch(path)
    return jsonify(body), status


# ── 工序追踪 ───────────────────────────────────────────────────
@app.route('/process-track')
def process_track_page():
    return render_template('process_track.html')


@app.route('/api/process/list')
def api_process_list():
    """订单+工序汇总列表（数据源：production）"""
    qs = request.query_string.decode('utf-8')
    path = '/api/dispatch-center/production/list?' + qs if qs else '/api/dispatch-center/production/list'
    body, status = _call_dispatch(path)
    if body.get('code') == 0 and isinstance(body.get('data'), dict):
        items = body['data'].get('orders', [])
        body['data'] = items
    return jsonify(body), status


@app.route('/api/process/status/<order_no>')
def api_process_status(order_no):
    """单订单工序状态"""
    body, status = _call_dispatch(f'/api/schedule/status/{order_no}')
    return jsonify(body), status


@app.route('/api/process/history/<order_no>')
def api_process_history(order_no):
    """单订单排产历史时间线"""
    body, status = _call_dispatch(f'/api/schedule/history/{order_no}')
    return jsonify(body), status


@app.route('/api/process/timeline/<order_no>')
def api_process_timeline(order_no):
    """单订单工序甘特图数据（融合排产+生产数据）"""
    body, status = _call_dispatch(f'/api/schedule/status/{order_no}')
    process_list = []
    plan_start, plan_end = None, None
    if body.get('code') == 0:
        status_data = body.get('data', {}) or {}
        plan = status_data.get('plan') or {}
        plan_start, plan_end = plan.get('start'), plan.get('end')
        for i, step in enumerate(status_data.get('steps') or status_data.get('processes') or []):
            process_list.append({
                'index': i + 1,
                'name': step.get('process_name') or step.get('name') or f'工序{i+1}',
                'start': step.get('plan_start') or step.get('start_time') or plan_start,
                'end': step.get('plan_end') or step.get('end_time') or plan_end,
                'status': step.get('status') or '待开始',
                'completed_qty': step.get('completed_qty', 0),
                'planned_qty': step.get('planned_qty', 0),
                'operator': step.get('operator_name') or step.get('operator') or '-',
            })
    if not process_list:
        try:
            prod_body, _ = _call_dispatch('/api/dispatch-center/production/list')
            if prod_body.get('code') == 0:
                orders = (prod_body.get('data') or {}).get('orders') or []
                for o in orders:
                    if o.get('order_no') == order_no:
                        plan_start = o.get('plan_start') or plan_start
                        plan_end = o.get('plan_end') or plan_end
                        qty = float(o.get('quantity') or 0)
                        actual_start = o.get('actual_start')
                        actual_end = o.get('actual_end')
                        status = o.get('status') or '生产中'
                        default_processes = ['领料', '编织', '焊接', '表面处理', '质检', '入库']
                        n = len(default_processes)
                        try:
                            from datetime import datetime, timedelta
                            ps = datetime.fromisoformat(plan_start) if plan_start else datetime.now()
                            pe = datetime.fromisoformat(plan_end) if plan_end else ps + timedelta(days=7)
                            total_days = max((pe - ps).days, n)
                            per_days = total_days / n
                        except Exception:
                            ps, pe = None, None
                            per_days = 1
                        for i, name in enumerate(default_processes):
                            if ps and pe:
                                s = ps + timedelta(days=i * per_days)
                                e = ps + timedelta(days=(i+1) * per_days)
                                s_str = s.date().isoformat()
                                e_str = e.date().isoformat()
                            else:
                                s_str = e_str = None
                            if i < n - 1:
                                step_status = '已完成' if status == '已完成' else ('生产中' if i == 0 else '待开始')
                            else:
                                step_status = '已完成' if status == '已完成' else '待开始'
                            process_list.append({
                                'index': i + 1,
                                'name': name,
                                'start': s_str,
                                'end': e_str,
                                'status': step_status,
                                'completed_qty': qty if step_status == '已完成' else (qty/2 if step_status == '生产中' else 0),
                                'planned_qty': qty,
                                'operator': o.get('assigned_to') or '待分配',
                            })
                        break
        except Exception as e:
            logger.warning(f"timeline generation from production failed: {e}")
    return jsonify({
        'code': 0,
        'data': {
            'order_no': order_no,
            'plan_start': plan_start,
            'plan_end': plan_end,
            'processes': process_list,
            'total': len(process_list),
        }
    }), 200


# ── 生产排单 CRUD（直写 production_orders 表，与桌面端一致） ───────────────

@app.route('/api/production/orders', methods=['POST'])
@require_auth
@verify_csrf_token
def api_create_work_order():
    try:
        body = request.get_json(silent=True) or {}
        order_id = body.get('order_id')
        if not order_id:
            return jsonify({'code': 400, 'message': '缺少 order_id'}), 400
        from models.production import ProductionDAO
        prod_id = ProductionDAO.create(order_id, {
            'priority': int(body.get('priority', 5)),
            'plan_start': body.get('plan_start') or None,
            'plan_end': body.get('plan_end') or None,
            'assigned_to': body.get('assigned_to', ''),
            'remark': body.get('remark', ''),
        })
        from constants import ProductionStatus
        ProductionDAO.update_status(prod_id, ProductionStatus.PENDING_PUBLISH.value)
        return jsonify({'code': 0, 'message': '工单创建成功', 'data': {'id': prod_id}}), 200
    except Exception as e:
        logger.exception('[创建工单] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/production/orders/<int:prod_id>', methods=['GET'])
def api_get_work_order(prod_id):
    try:
        from models.production import ProductionDAO
        wo = ProductionDAO.get_by_id(prod_id)
        if not wo:
            return jsonify({'code': 404, 'message': '工单不存在'}), 404
        return jsonify({'code': 0, 'data': wo}), 200
    except Exception as e:
        logger.exception('[获取工单] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/production/orders/<int:prod_id>', methods=['PUT'])
@require_auth
@verify_csrf_token
def api_update_work_order(prod_id):
    try:
        body = request.get_json(silent=True) or {}
        from models.production import ProductionDAO
        data = {}
        if 'priority' in body: data['priority'] = int(body['priority'])
        if 'plan_start' in body: data['plan_start'] = body['plan_start'] or None
        if 'plan_end' in body: data['plan_end'] = body['plan_end'] or None
        if 'assigned_to' in body: data['assigned_to'] = body['assigned_to']
        if 'remark' in body: data['remark'] = body['remark']
        if 'status' in body: data['status'] = body['status']
        ProductionDAO.update(prod_id, data)
        return jsonify({'code': 0, 'message': '修改成功'}), 200
    except Exception as e:
        logger.exception('[编辑工单] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/production/orders/<int:prod_id>/status', methods=['PUT'])
@require_auth
@verify_csrf_token
def api_change_work_order_status(prod_id):
    try:
        body = request.get_json(silent=True) or {}
        new_status = body.get('status')
        if not new_status:
            return jsonify({'code': 400, 'message': '缺少 status'}), 400
        from models.production import ProductionDAO
        from constants import validate_production_status_transition
        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("SELECT status FROM production_orders WHERE id=%s", (prod_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({'code': 404, 'message': '工单不存在'}), 404
            current_status = row['status']
            cur.close()
            is_valid, msg = validate_production_status_transition(current_status, new_status)
            if not is_valid:
                return jsonify({'code': 400, 'message': msg}), 400
        finally:
            if cur: cur.close()
            conn.close()
        ProductionDAO.update_status(prod_id, new_status)
        return jsonify({'code': 0, 'message': f'状态已更新为「{new_status}」'}), 200
    except Exception as e:
        logger.exception('[变更状态] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


# ── 死信管理 ─────────────────────────────────────────────────────────────

@app.route('/api/dispatch/dead-letters', methods=['GET'])
def api_dead_letters():
    try:
        from services.schedule_dispatch_service import ScheduleDispatchService
        dead_letters = ScheduleDispatchService.get_dead_letters()
        return jsonify({'code': 0, 'data': {'dead_letters': dead_letters, 'total': len(dead_letters)}}), 200
    except Exception as e:
        logger.exception('[获取死信] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/dispatch/dead-letters/batch-retry', methods=['POST'])
@require_auth
@verify_csrf_token
def api_batch_retry_dead_letters():
    try:
        body = request.get_json(silent=True) or {}
        ids = body.get('ids', [])
        if not ids:
            return jsonify({'code': 400, 'message': '缺少 ids'}), 400
        if len(ids) > 100:
            return jsonify({'code': 400, 'message': '单次操作不超过100条'}), 400
        from services.schedule_dispatch_service import ScheduleDispatchService
        results = {'success': [], 'failed': [], 'skipped': []}
        for dl_id in ids:
            try:
                result = ScheduleDispatchService.retry_dead_letter(dl_id)
                if result.get('skipped'):
                    results['skipped'].append({'id': dl_id, 'reason': result.get('message', '')})
                elif result.get('success'):
                    results['success'].append(dl_id)
                else:
                    results['failed'].append({'id': dl_id, 'reason': result.get('message', '')})
            except Exception as ex:
                results['failed'].append({'id': dl_id, 'reason': str(ex)})
        ok = len(results['success'])
        total = len(ids)
        msg = f'重发完成：成功 {ok}/{total} 条'
        if results['skipped']:
            msg += f'（{len(results["skipped"])} 条已跳过）'
        return jsonify({'code': 0 if ok > 0 else 400, 'message': msg, 'data': results}), 200
    except Exception as e:
        logger.exception('[批量重发死信] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


# ── 工序管理页面 ──────────────────────────────────────────────
@app.route('/process-admin')
def process_admin_page():
    return render_template('process_admin.html')


@app.route('/api/process/admin-list')
def api_process_admin_list():
    """获取工序列表（按 production_id，直接读 MySQL）"""
    try:
        production_id = request.args.get('production_id', type=int)
        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            if production_id:
                cur.execute("""
                    SELECT pr.*, po.order_no, o.customer_name
                    FROM process_records pr
                    LEFT JOIN production_orders po ON pr.production_id = po.id
                    LEFT JOIN orders o ON po.order_id = o.id
                    WHERE pr.production_id = %s AND COALESCE(pr.is_deleted_code, 0) = 0
                    ORDER BY pr.process_seq ASC
                """, (production_id,))
            else:
                cur.execute("""
                    SELECT pr.*, po.order_no, o.customer_name
                    FROM process_records pr
                    LEFT JOIN production_orders po ON pr.production_id = po.id
                    LEFT JOIN orders o ON po.order_id = o.id
                    WHERE COALESCE(pr.is_deleted_code, 0) = 0
                    ORDER BY pr.production_id, pr.process_seq ASC
                    LIMIT 500
                """)
            rows = cur.fetchall()
            return jsonify({'code': 0, 'data': {'processes': [dict(r) for r in rows]}}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[工序列表] 查询失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/process/<int:process_id>')
def api_process_get(process_id):
    """获取单个工序详情"""
    try:
        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT pr.*, po.order_no, o.customer_name
                FROM process_records pr
                LEFT JOIN production_orders po ON pr.production_id = po.id
                LEFT JOIN orders o ON po.order_id = o.id
                WHERE pr.id = %s
            """, (process_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({'code': 404, 'message': '工序不存在'}), 404
            return jsonify({'code': 0, 'data': dict(row)}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[工序详情] 查询失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/process/add', methods=['POST'])
@require_auth
@verify_csrf_token
def api_process_add():
    """添加工序"""
    try:
        data = request.get_json(silent=True) or {}
        production_id = data.get('production_id')
        process_name = (data.get('process_name') or '').strip()
        if not production_id:
            return jsonify({'code': 400, 'message': '缺少 production_id'}), 400
        if not process_name:
            return jsonify({'code': 400, 'message': '缺少工序名称'}), 400

        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            process_seq = int(data.get('process_seq') or 1)
            worker = (data.get('worker') or '').strip()
            planned_qty = float(data.get('planned_qty') or 1)
            unit = (data.get('unit') or '件').strip()
            is_outsource = 1 if data.get('is_outsource') else 0
            remark = (data.get('remark') or '').strip()

            cur.execute("""
                INSERT INTO process_records
                (production_id, process_name, process_seq, worker, planned_qty, unit,
                 completed_qty, qualified_qty, work_hours, status, is_outsource,
                 is_deleted_code, remark, record_type, record_date)
                VALUES (%s, %s, %s, %s, %s, %s, 0, 0, 0, '待开始', %s, 0, %s, 'product', NOW())
            """, (production_id, process_name, process_seq, worker, planned_qty, unit,
                  is_outsource, remark))
            new_id = cur.lastrowid
            conn.commit()
            logger.info(f"[添加工序] id={new_id} name={process_name}")
            return jsonify({'code': 0, 'message': '工序添加成功', 'data': {'id': new_id}}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[添加工序] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/process/insert', methods=['POST'])
@require_auth
@verify_csrf_token
def api_process_insert():
    """插入工序（在指定工序之后）"""
    try:
        data = request.get_json(silent=True) or {}
        production_id = data.get('production_id')
        after_process_id = data.get('after_process_id')
        process_name = (data.get('process_name') or '').strip()
        if not production_id:
            return jsonify({'code': 400, 'message': '缺少 production_id'}), 400
        if not after_process_id:
            return jsonify({'code': 400, 'message': '缺少 after_process_id'}), 400
        if not process_name:
            return jsonify({'code': 400, 'message': '缺少工序名称'}), 400

        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("SELECT process_seq FROM process_records WHERE id=%s", (after_process_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({'code': 404, 'message': '参考工序不存在'}), 404
            target_seq = row['process_seq'] + 1

            cur.execute("""
                UPDATE process_records SET process_seq = process_seq + 1
                WHERE production_id = %s AND process_seq >= %s AND COALESCE(is_deleted_code, 0) = 0
            """, (production_id, target_seq))
            conn.commit()

            worker = (data.get('worker') or '').strip()
            planned_qty = float(data.get('planned_qty') or 1)
            unit = (data.get('unit') or '件').strip()
            remark = (data.get('remark') or '').strip()

            cur.execute("""
                INSERT INTO process_records
                (production_id, process_name, process_seq, worker, planned_qty, unit,
                 completed_qty, qualified_qty, work_hours, status, is_deleted_code, remark, record_type, record_date)
                VALUES (%s, %s, %s, %s, %s, %s, 0, 0, 0, '待开始', 0, %s, 'product', NOW())
            """, (production_id, process_name, target_seq, worker, planned_qty, unit, remark))
            new_id = cur.lastrowid
            conn.commit()
            logger.info(f"[插入工序] id={new_id} after={after_process_id} seq={target_seq}")
            return jsonify({'code': 0, 'message': '工序插入成功', 'data': {'id': new_id}}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[插入工序] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/process/<int:process_id>', methods=['PUT'])
@require_auth
@verify_csrf_token
def api_process_update(process_id):
    """更新工序"""
    try:
        data = request.get_json(silent=True) or {}
        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM process_records WHERE id=%s", (process_id,))
            old = cur.fetchone()
            if not old:
                return jsonify({'code': 404, 'message': '工序不存在'}), 404

            _PROCESS_UPDATE_FIELDS = {'process_name', 'worker', 'planned_qty', 'unit', 'status', 'is_outsource', 'remark'}
            update_fields = []
            update_values = []

            if 'process_name' in data:
                update_fields.append("process_name=%s")
                update_values.append((data['process_name'] or '').strip())
            if 'worker' in data:
                update_fields.append("worker=%s")
                update_values.append((data['worker'] or '').strip())
            if 'planned_qty' in data:
                update_fields.append("planned_qty=%s")
                update_values.append(float(data['planned_qty'] or 1))
            if 'unit' in data:
                update_fields.append("unit=%s")
                update_values.append((data['unit'] or '件').strip())
            if 'status' in data:
                new_status = data['status']
                update_fields.append("status=%s")
                update_values.append(new_status)
                if new_status == '生产中' and not old['start_time']:
                    cur.execute("UPDATE process_records SET start_time=NOW() WHERE id=%s", (process_id,))
                elif new_status == '已完成' and old['status'] != '已完成':
                    cur.execute("UPDATE process_records SET end_time=NOW() WHERE id=%s", (process_id,))
            if 'is_outsource' in data:
                update_fields.append("is_outsource=%s")
                update_values.append(1 if data['is_outsource'] else 0)
            if 'remark' in data:
                update_fields.append("remark=%s")
                update_values.append((data['remark'] or '').strip())

            if update_fields:
                update_fields.append("record_date=NOW()")
                cur.execute(
                    "UPDATE process_records SET {} WHERE id=%s".format(','.join(update_fields)),
                    update_values + [process_id]
                )
                conn.commit()

            logger.info(f"[更新工序] id={process_id}")
            return jsonify({'code': 0, 'message': '工序已更新'}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[更新工序] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/process/<int:process_id>/start', methods=['PUT'])
@require_auth
@verify_csrf_token
def api_process_start(process_id):
    """工序开始"""
    try:
        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM process_records WHERE id=%s", (process_id,))
            old = cur.fetchone()
            if not old:
                return jsonify({'code': 404, 'message': '工序不存在'}), 404

            cur.execute("""
                UPDATE process_records SET status='生产中', start_time=NOW(), record_date=NOW()
                WHERE id=%s AND (status='待开始' OR status IS NULL OR status='')
            """, (process_id,))
            conn.commit()
            if cur.rowcount == 0:
                return jsonify({'code': 400, 'message': '工序状态无法变更为开始'}), 400

            _sync_bridge({
                'type': 'process_start',
                'process_id': process_id,
                'production_id': old['production_id'],
                'status': '生产中'
            })
            logger.info(f"[工序开始] id={process_id}")
            return jsonify({'code': 0, 'message': '工序已开始'}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[工序开始] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/process/<int:process_id>/complete', methods=['PUT'])
@require_auth
@verify_csrf_token
def api_process_complete(process_id):
    """工序完成"""
    try:
        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM process_records WHERE id=%s", (process_id,))
            old = cur.fetchone()
            if not old:
                return jsonify({'code': 404, 'message': '工序不存在'}), 404

            cur.execute("""
                UPDATE process_records SET status='已完成', end_time=NOW(), record_date=NOW()
                WHERE id=%s AND status!='已完成'
            """, (process_id,))
            # [P0-D 修复 2026-06-24] rowcount 检查：工序不存在或已是"已完成"时返回明确错误
            if cur.rowcount == 0:
                cur.execute("SELECT status FROM process_records WHERE id=%s", (process_id,))
                row = cur.fetchone()
                if not row:
                    return jsonify({'code': 404, 'message': '工序不存在'}), 404
                return jsonify({'code': 400, 'message': f'工序状态已是"{row["status"]}"，无法重复完成'}), 400
            conn.commit()

            _sync_bridge({
                'type': 'process_complete',
                'process_id': process_id,
                'production_id': old['production_id'],
                'status': '已完成'
            })
            logger.info(f"[工序完成] id={process_id}")
            return jsonify({'code': 0, 'message': '工序已完成'}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[工序完成] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


# [P0-C 修复 2026-06-24] 越权访问防护 - 重置工序 (管理员/班组长)
@app.route('/api/process/<int:process_id>/reset', methods=['PUT'])
@require_role('admin', 'manager')
@verify_csrf_token
def api_process_reset(process_id):
    """重置工序状态"""
    try:
        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM process_records WHERE id=%s", (process_id,))
            old = cur.fetchone()
            if not old:
                return jsonify({'code': 404, 'message': '工序不存在'}), 404

            cur.execute("""
                UPDATE process_records SET
                    status='待开始',
                    start_time=NULL,
                    end_time=NULL,
                    completed_qty=0,    -- [P1-2 修复 2026-06-24] 清零累计完成数
                    qualified_qty=0,    -- [P1-2 修复 2026-06-24] 清零累计合格数
                    work_hours=0,       -- [P1-2 修复 2026-06-24] 清零累计工时
                    record_date=NOW()
                WHERE id=%s AND status!='待开始'
            """, (process_id,))
            # [P0-D 修复 2026-06-24] rowcount 检查：工序不存在或已是"待开始"时返回明确错误
            if cur.rowcount == 0:
                cur.execute("SELECT status FROM process_records WHERE id=%s", (process_id,))
                row = cur.fetchone()
                if not row:
                    return jsonify({'code': 404, 'message': '工序不存在'}), 404
                return jsonify({'code': 400, 'message': f'工序状态已是"{row["status"]}"，无法重复重置'}), 400
            conn.commit()

            _sync_bridge({
                'type': 'process_reset',
                'process_id': process_id,
                'production_id': old['production_id'],
                'status': '待开始'
            })
            logger.info(f"[工序重置] id={process_id}")
            return jsonify({'code': 0, 'message': '工序已重置'}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[工序重置] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/process/<int:process_id>/report', methods=['PUT'])
@require_auth
@verify_csrf_token
def api_process_report(process_id):
    """工序报工（[P0-F 修复 2026-06-24] 原子 UPDATE：消除 TOCTOU 竞态）"""
    try:
        data = request.get_json(silent=True) or {}
        qty = float(data.get('qty') or 0)
        if qty <= 0:
            return jsonify({'code': 400, 'message': '报工数量必须大于0'}), 400

        qualified = float(data.get('qualified') or 0)
        hours = float(data.get('hours') or 0)
        worker = (data.get('worker') or '').strip()

        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            # [P0-F] 原子 UPDATE：在一句 SQL 中完成数量累加 + 状态判断
            # WHERE 条件：planned_qty=0（无计划时允许）或 累加后不超过计划数
            cur.execute("""
                UPDATE process_records
                SET completed_qty = completed_qty + %s,
                    qualified_qty = qualified_qty + %s,
                    work_hours = work_hours + %s,
                    status = CASE
                        WHEN completed_qty + %s >= planned_qty THEN '已完成'
                        WHEN completed_qty + %s > 0 THEN '生产中'
                        ELSE status
                    END,
                    worker = COALESCE(NULLIF(%s, ''), worker),
                    record_date = NOW(),
                    start_time = CASE
                        WHEN (status IS NULL OR status = '' OR status = '待开始')
                             AND completed_qty + %s > 0 THEN NOW()
                        ELSE start_time
                    END
                WHERE id = %s
                  AND (planned_qty = 0 OR completed_qty + %s <= planned_qty)
                  AND status != '已完成'
            """, (qty, qualified, hours, qty, qty, worker, qty, process_id, qty))

            if cur.rowcount == 0:
                # 可能：工序不存在 / 已完成 / 超计划数
                cur.execute(
                    "SELECT id, status, completed_qty, planned_qty FROM process_records WHERE id=%s",
                    (process_id,))
                row = cur.fetchone()
                if not row:
                    return jsonify({'code': 404, 'message': '工序不存在'}), 404
                if row['status'] == '已完成':
                    return jsonify({'code': 400, 'message': '工序已完成，无法报工'}), 400
                if row['planned_qty']:
                    planned = float(row['planned_qty'] or 0)
                    completed = float(row['completed_qty'] or 0)
                    over_pct = (completed + qty - planned) / planned if planned > 0 else 0
                    if over_pct > 0.20:
                        over = completed + qty - planned
                        return jsonify({
                            'code': 400,
                            'message': f'[P2-7] 报工超出计划 {over_pct:.1%}，超出 {over:.0f} 件，超 20% 拒绝，请先完成本工序'
                        }), 400
                    if over_pct > 0.05:
                        over = completed + qty - planned
                        return jsonify({
                            'code': 200,
                            'message': f'[P2-7] 提示：报工后累计 {completed + qty:.0f}/{planned:.0f}，超出计划 {over_pct:.1%}，超出 {over:.0f} 件',
                            'warning': True,
                            'data': {
                                'completed_qty': completed,
                                'planned_qty': planned,
                                'over_pct': round(over_pct * 100, 1)
                            }
                        }), 200
                return jsonify({'code': 500, 'message': '报工失败'}), 500

            conn.commit()

            # 查询最新值用于返回
            cur.execute(
                "SELECT completed_qty, qualified_qty, status, production_id "
                "FROM process_records WHERE id=%s",
                (process_id,))
            updated = cur.fetchone()

            _sync_bridge({
                'type': 'process_report',
                'process_id': process_id,
                'production_id': updated['production_id'],
                'completed_qty': updated['completed_qty'],
                'qualified_qty': updated['qualified_qty'],
                'status': updated['status'],
                'worker': worker
            })
            logger.info(f"[工序报工] id={process_id} qty={qty} total={updated['completed_qty']}")
            return jsonify({
                'code': 0,
                'message': f'累计：{updated["completed_qty"]}/{updated["planned_qty"] or 1}',
                'data': {
                    'completed_qty': updated['completed_qty'],
                    'qualified_qty': updated['qualified_qty'],
                    'status': updated['status']
                }
            }), 200
        except Exception as e:
            conn.rollback()
            logger.exception('[工序报工] 失败')
            return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[工序报工] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/process/swap-seq', methods=['PUT'])
@require_auth
@verify_csrf_token
def api_process_swap_seq():
    """交换两道工序的序号"""
    try:
        data = request.get_json(silent=True) or {}
        id1 = data.get('id1')
        id2 = data.get('id2')
        if not id1 or not id2:
            return jsonify({'code': 400, 'message': '缺少参数'}), 400

        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("SELECT process_seq FROM process_records WHERE id=%s", (id1,))
            row1 = cur.fetchone()
            cur.execute("SELECT process_seq FROM process_records WHERE id=%s", (id2,))
            row2 = cur.fetchone()
            if not row1 or not row2:
                return jsonify({'code': 404, 'message': '工序不存在'}), 404

            seq1, seq2 = row1['process_seq'], row2['process_seq']
            cur.execute("UPDATE process_records SET process_seq=%s WHERE id=%s", (seq2, id1))
            cur.execute("UPDATE process_records SET process_seq=%s WHERE id=%s", (seq1, id2))
            conn.commit()

            logger.info(f"[交换序号] id1={id1}({seq1}) <-> id2={id2}({seq2})")
            return jsonify({'code': 0, 'message': '顺序已调整'}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[交换序号] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


# [P0-C 修复 2026-06-24] 越权访问防护 - 删除工序 (仅管理员)
@app.route('/api/process/<int:process_id>', methods=['DELETE'])
@require_role('admin')
@verify_csrf_token
def api_process_delete(process_id):
    """删除工序（软删除）"""
    try:
        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM process_records WHERE id=%s", (process_id,))
            old = cur.fetchone()
            if not old:
                return jsonify({'code': 404, 'message': '工序不存在'}), 404

            cur.execute("""
                UPDATE process_records SET is_deleted_code=1, record_date=NOW()
                WHERE id=%s
            """, (process_id,))
            conn.commit()

            logger.info(f"[删除工序] id={process_id} name={old['process_name']}")
            return jsonify({'code': 0, 'message': '工序已删除'}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[删除工序] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


# ── Excel 导入导出 ─────────────────────────────────────────────
from utils.excel_service import (
    build_order_export, parse_order_import, generate_template,
    build_shipment_export, build_workreport_export,
    build_operator_export, generate_operator_template, parse_operator_import,
)


@app.route('/order-import')
def order_import_page():
    return render_template('order_import.html')


@app.route('/api/orders/template')
def api_orders_template():
    try:
        from flask import send_file
        path = generate_template()
        return send_file(path, as_attachment=True,
                         download_name='订单导入模板.xlsx',
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        logger.exception('[订单模板] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/orders/export')
def api_orders_export():
    try:
        from flask import send_file
        kw = request.args.get('keyword', '').strip()
        st = request.args.get('status', '').strip()
        grp = request.args.get('customer_group', '').strip()
        df = request.args.get('date_from', '').strip()
        dt = request.args.get('date_to', '').strip()
        qmin = request.args.get('qty_min', '').strip()
        qmax = request.args.get('qty_max', '').strip()
        page_size = 5000
        qs = f'page=1&page_size={page_size}'
        if kw: qs += f'&keyword={kw}'
        if st: qs += f'&status={st}'
        if grp: qs += f'&customer_group={grp}'
        if df: qs += f'&date_from={df}'
        if dt: qs += f'&date_to={dt}'
        if qmin: qs += f'&qty_min={qmin}'
        if qmax: qs += f'&qty_max={qmax}'
        body, status = _call_dispatch(f'/api/orders/query?{qs}')
        orders = []
        if body.get('code') == 0:
            items = (body.get('data') or {}).get('items') or []
            total = (body.get('data') or {}).get('total', 0)
            orders = items
            if total > page_size:
                pages = (total + page_size - 1) // page_size
                for p in range(2, pages + 1):
                    qs2 = qs.replace('page=1', f'page={p}')
                    b2, _ = _call_dispatch(f'/api/orders/query?{qs2}')
                    if b2.get('code') == 0:
                        orders.extend((b2.get('data') or {}).get('items') or [])
        from datetime import datetime
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        fname = f'订单导出_{ts}.xlsx'
        path = build_order_export(orders, fname)
        return send_file(path, as_attachment=True,
                         download_name=fname,
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        logger.exception('[订单导出] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/orders/import', methods=['POST'])
@require_auth
@verify_csrf_token
def api_orders_import():
    from werkzeug.datastructures import FileStorage
    # 先检查 Content-Length，避免触发 413 后无法返回 JSON
    cl = request.content_length or 0
    if cl > app.config['MAX_CONTENT_LENGTH']:
        return jsonify({
            'code': 413,
            'message': f'上传文件过大（{cl/1024/1024:.1f}MB），超过限制 {app.config["MAX_CONTENT_LENGTH"]/1024/1024:.0f}MB'
        }), 413
    try:
        if 'file' not in request.files:
            return jsonify({'code': 400, 'message': '请上传 Excel 文件'}), 400
        f = request.files['file']
        if not f.filename.endswith(('.xlsx', '.xls')):
            return jsonify({'code': 400, 'message': '仅支持 .xlsx / .xls 格式'}), 400
        parsed = parse_order_import(f)
        valid = parsed.get('valid', [])
        errors = parsed.get('errors', [])
        created, skipped = 0, 0
        if valid:
            from models.database import get_connection
            import pymysql
            conn = get_connection()
            try:
                cur = conn.cursor()
                for idx, item in enumerate(valid):
                    try:
                        order_no_input = (item.get('order_no') or '').strip()
                        is_exist = False
                        if order_no_input:
                            cur.execute("SELECT 1 FROM orders WHERE order_no=%s LIMIT 1", (order_no_input,))
                            if cur.fetchone():
                                is_exist = True
                        if is_exist:
                            skipped += 1
                            continue
                        auto_no = generate_order_no()
                        def _to_decimal(v, default=None):
                            if v in (None, '', ' ', None): return default
                            try:
                                return float(str(v).replace('mm','').replace('m','').replace('×','x').replace('x','*').strip())
                            except Exception:
                                return default
                        def _to_int(v, default=0):
                            if v in (None, '', ' ', None): return default
                            try: return int(float(v))
                            except Exception: return default
                        extra_dict = {}
                        for k_text, k_num in [('mesh_size','mesh_size'), ('wire_diameter','wire_diameter'),
                                              ('width','width'),('length','length')]:
                            if item.get(k_num) and not _to_decimal(item.get(k_num)):
                                extra_dict[k_num] = item[k_num]
                        cur.execute("""
                            INSERT INTO orders (
                                order_no, customer_name, customer_phone, customer_address, customer_group,
                                product_type, material, mesh_size, wire_diameter, width, length,
                                quantity, unit, unit_price, total_amount, surface_treatment,
                                special_requirements, delivery_date, status, remark, extra_params
                            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """, (
                            auto_no,
                            item.get('customer_name', ''),
                            item.get('customer_phone', ''),
                            item.get('customer_address', ''),
                            item.get('customer_group', ''),
                            item.get('product_type', ''),
                            item.get('material', ''),
                            _to_decimal(item.get('mesh_size')),
                            _to_decimal(item.get('wire_diameter')),
                            _to_decimal(item.get('width')),
                            _to_decimal(item.get('length')),
                            _to_int(item.get('quantity')),
                            item.get('unit', '米'),
                            _to_decimal(item.get('unit_price'), 0) or 0,
                            _to_int(item.get('quantity')) * (_to_decimal(item.get('unit_price'), 0) or 0),
                            item.get('surface_treatment', ''),
                            item.get('special_requirements', ''),
                            item.get('delivery_date', '') or None,
                            '待确认',
                            item.get('remark', ''),
                            json.dumps(extra_dict, ensure_ascii=False) if extra_dict else '',
                        ))
                        conn.commit()
                        created += 1
                    except pymysql.IntegrityError as e:
                        try: conn.rollback()
                        except Exception: pass
                        if e.args and e.args[0] == 1062:
                            skipped += 1
                            errors.append({'row': idx + 2, 'msg': f'订单号已存在，自动跳过'})
                        else:
                            errors.append({'row': idx + 2, 'msg': f'数据库错误: {e}'})
                    except Exception as e:
                        try: conn.rollback()
                        except Exception: pass
                        errors.append({'row': idx + 2, 'msg': f'单行处理失败: {str(e)[:100]}'})
                cur.close()
            finally:
                try: conn.close()
                except Exception: pass
        return jsonify({
            'code': 0,
            'data': {
                'created': created,
                'skipped': skipped,
                'errors': errors,
                'total': len(valid) + len(errors),
            },
            'message': f'导入完成：成功 {created} 条，跳过 {skipped} 条（已存在）'
        })
    except Exception as e:
        logger.exception('[订单导入] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/shipment/export')
def api_shipment_export():
    try:
        from flask import send_file
        qs = request.query_string.decode('utf-8')
        path_str = '/api/dispatch-center/shipping/list?' + qs if qs else '/api/dispatch-center/shipping/list'
        body, _ = _call_dispatch(path_str)
        records = []
        if body.get('code') == 0:
            records = (body.get('data') or {}).get('shipments') or []
            if not records and isinstance(body.get('data'), list):
                records = body.get('data') or []
        from datetime import datetime
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        fname = f'发货记录导出_{ts}.xlsx'
        path = build_shipment_export(records, fname)
        return send_file(path, as_attachment=True,
                         download_name=fname,
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        logger.exception('[发货导出] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/work-reports/export')
def api_workreports_export():
    try:
        from flask import send_file
        qs = request.query_string.decode('utf-8')
        path_str = '/api/dispatch-center/report-queue/list?' + qs if qs else '/api/dispatch-center/report-queue/list'
        body, _ = _call_dispatch(path_str)
        records = []
        if body.get('code') == 0:
            records = (body.get('data') or {}).get('records') or []
            if not records and isinstance(body.get('data'), list):
                records = body.get('data') or []
        from datetime import datetime
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        fname = f'报工记录导出_{ts}.xlsx'
        path = build_workreport_export(records, fname)
        return send_file(path, as_attachment=True,
                         download_name=fname,
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        logger.exception('[报工导出] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


# ── 质检管理页面 ────────────────────────────────────────────────────
@app.route('/quality-admin')
def quality_admin_page():
    return render_template('quality_admin.html')


@app.route('/api/orders/quality-orders')
def api_quality_orders():
    """获取可质检的订单（状态为：待排产/已排产/生产中/质检中）"""
    try:
        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, order_no, customer_name, customer_group, product_type,
                       quantity, unit, status, delivery_date
                FROM orders
                WHERE status IN ('待排产', '已排产', '生产中', '质检中', '待确认')
                  AND COALESCE(is_deleted, 0) = 0
                  AND COALESCE(is_archived, 0) = 0
                ORDER BY delivery_date ASC, created_at DESC
            """)
            rows = cur.fetchall()
            return jsonify({'code': 0, 'data': {'orders': [dict(r) for r in rows], 'total': len(rows)}}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[可质检订单] 查询失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/quality/add', methods=['POST'])
@require_auth
@verify_csrf_token
def api_quality_add():
    """创建质检记录"""
    try:
        data = request.get_json(silent=True) or {}
        order_id = data.get('order_id')
        if not order_id:
            return jsonify({'code': 400, 'message': '缺少 order_id'}), 400

        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("SELECT order_no, customer_name FROM orders WHERE id=%s LIMIT 1", (order_id,))
            order = cur.fetchone()
            if not order:
                return jsonify({'code': 404, 'message': '订单不存在'}), 404
            order_no = order['order_no']
            customer_name = order['customer_name']

            cur.execute("SHOW COLUMNS FROM quality_records LIKE 'inspection_seq'")
            if not cur.fetchone():
                cur.execute("ALTER TABLE quality_records ADD COLUMN inspection_seq INT DEFAULT 0")
            cur.execute("SHOW COLUMNS FROM quality_records LIKE 'inspection_no'")
            if not cur.fetchone():
                cur.execute("ALTER TABLE quality_records ADD COLUMN inspection_no VARCHAR(50) DEFAULT ''")

            inspection_type = data.get('inspection_type', '终检')
            cur.execute("""
                SELECT COALESCE(MAX(inspection_seq), 0) + 1 AS next_seq
                FROM quality_records
                WHERE order_id=%s AND inspection_type=%s
            """, (order_id, inspection_type))
            seq_row = cur.fetchone()
            seq = seq_row['next_seq'] if seq_row else 1
            inspection_no = f"{inspection_type}-{seq}"

            defect_qty = data.get('defect_qty', 0)
            try:
                defect_qty = max(0, int(defect_qty))
            except (ValueError, TypeError):
                defect_qty = 0

            cur.execute("""
                INSERT INTO quality_records (
                    order_id, order_no, inspection_type, inspection_seq, inspection_no,
                    inspection_items, result, defect_description, defect_qty, handling_method,
                    inspector, remark, process_name, record_date
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """, (
                order_id, order_no, inspection_type, seq, inspection_no,
                data.get('inspection_items', ''),
                data.get('result', '待检'),
                data.get('defect_description', ''),
                defect_qty,
                data.get('handling_method', ''),
                data.get('inspector', ''),
                data.get('remark', ''),
                data.get('process_name', '')
            ))
            new_id = cur.lastrowid if hasattr(cur, 'lastrowid') else None
            if not new_id:
                cur.execute("SELECT LAST_INSERT_ID() AS id")
                new_id = cur.fetchone()['id']
            conn.commit()
            logger.info(f"[质检创建] id={new_id} order_no={order_no} type={inspection_type}")
            return jsonify({'code': 0, 'message': '质检记录创建成功', 'data': {'id': new_id}}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[质检创建] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/quality/admin-list')
def api_quality_admin_list():
    """质检记录列表（支持按类型、结果、关键词筛选）"""
    try:
        inspection_type = request.args.get('type', '').strip()
        result = request.args.get('result', '').strip()
        keyword = request.args.get('keyword', '').strip()
        limit = int(request.args.get('limit', 200))
        days_limit = int(request.args.get('days', 60))

        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            sql = """
                SELECT qr.*, o.order_no AS orders_order_no, o.customer_name,
                       GROUP_CONCAT(DISTINCT po.order_no SEPARATOR ', ') AS production_order_no
                FROM quality_records qr
                LEFT JOIN orders o ON qr.order_id = o.id
                LEFT JOIN production_orders po ON qr.order_id = po.order_id
                WHERE 1=1
            """
            params = []
            if inspection_type and inspection_type != '全部':
                sql += " AND qr.inspection_type=%s"
                params.append(inspection_type)
            if result and result != '全部':
                sql += " AND qr.result=%s"
                params.append(result)
            if keyword:
                kw = f"%{keyword}%"
                sql += " AND (qr.order_no LIKE %s OR o.customer_name LIKE %s OR qr.inspector LIKE %s)"
                params.extend([kw, kw, kw])
            sql += " AND qr.record_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)"
            params.append(days_limit)
            sql += " GROUP BY qr.id ORDER BY qr.record_date DESC LIMIT %s"
            params.append(limit)

            cur.execute(sql, params)
            rows = cur.fetchall()
            return jsonify({'code': 0, 'data': {'records': [dict(r) for r in rows], 'total': len(rows)}}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[质检列表] 查询失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/quality/<int:record_id>')
def api_quality_get(record_id):
    """获取单条质检记录"""
    try:
        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT qr.*, o.order_no AS orders_order_no, o.customer_name
                FROM quality_records qr
                LEFT JOIN orders o ON qr.order_id = o.id
                WHERE qr.id=%s
            """, (record_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({'code': 404, 'message': '记录不存在'}), 404
            return jsonify({'code': 0, 'data': dict(row)}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[质检详情] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/quality/<int:record_id>', methods=['PUT'])
@require_auth
@verify_csrf_token
def api_quality_update(record_id):
    """编辑质检记录"""
    try:
        data = request.get_json(silent=True) or {}
        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("SELECT id FROM quality_records WHERE id=%s", (record_id,))
            if not cur.fetchone():
                return jsonify({'code': 404, 'message': '记录不存在'}), 404

            _QUALITY_UPDATE_FIELDS = {'result', 'defect_description', 'defect_qty', 'handling_method', 'inspector', 'remark', 'inspection_items'}
            fields = []
            params = []
            for key in _QUALITY_UPDATE_FIELDS:
                if key in data:
                    fields.append(f"{key}=%s")
                    params.append(data[key])
            if not fields:
                return jsonify({'code': 400, 'message': '没有要更新的字段'}), 400
            params.append(record_id)
            sql = "UPDATE quality_records SET {} WHERE id=%s".format(', '.join(fields))
            cur.execute(sql, params)
            conn.commit()
            logger.info(f"[质检更新] id={record_id}")
            return jsonify({'code': 0, 'message': '更新成功'}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[质检更新] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/quality/<int:record_id>/result', methods=['PUT'])
@require_auth
@verify_csrf_token
def api_quality_result(record_id):
    """变更判定结果"""
    try:
        data = request.get_json(silent=True) or {}
        new_result = data.get('result')
        if not new_result:
            return jsonify({'code': 400, 'message': '缺少 result 参数'}), 400

        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM quality_records WHERE id=%s", (record_id,))
            record = cur.fetchone()
            if not record:
                return jsonify({'code': 404, 'message': '记录不存在'}), 404

            defect_qty = data.get('defect_qty')
            if defect_qty is not None:
                try:
                    defect_qty = max(0, int(defect_qty))
                except (ValueError, TypeError):
                    defect_qty = 0
            else:
                defect_qty = record['defect_qty']

            cur.execute("""
                UPDATE quality_records SET
                    result=%s, defect_qty=%s, handling_method=%s, remark=%s
                WHERE id=%s
            """, (
                new_result, defect_qty,
                data.get('handling_method', record['handling_method'] or ''),
                data.get('remark', record['remark'] or ''),
                record_id
            ))

            if new_result == '合格':
                from constants import OrderStatus
                cur.execute("UPDATE orders SET status=%s, updated_at=NOW() WHERE id=%s",
                           (OrderStatus.FINISHED.value, record['order_id']))
            elif new_result == '不合格':
                from constants import OrderStatus
                cur.execute("UPDATE orders SET status=%s, updated_at=NOW() WHERE id=%s",
                           (OrderStatus.QC.value, record['order_id']))

            conn.commit()
            logger.info(f"[质检判定] id={record_id} result={new_result}")
            return jsonify({'code': 0, 'message': f'判定结果已更新为「{new_result}」'}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[质检判定] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


# [P0-C 修复 2026-06-24] 越权访问防护 - 删除质检记录 (管理员/质检主管)
@app.route('/api/quality/<int:record_id>', methods=['DELETE'])
@require_role('admin', 'inspector')
@verify_csrf_token
def api_quality_delete(record_id):
    """删除质检记录"""
    try:
        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("SELECT id FROM quality_records WHERE id=%s", (record_id,))
            if not cur.fetchone():
                return jsonify({'code': 404, 'message': '记录不存在'}), 404
            # [P1-3 修复 2026-06-24] 软删除（符合 R-113 规则）
            try:
                cur.execute("""
                    UPDATE quality_records SET is_deleted=1, updated_at=NOW()
                    WHERE id=%s
                """, (record_id,))
            except Exception:
                cur.execute("DELETE FROM quality_records WHERE id=%s", (record_id,))
            conn.commit()
            logger.info(f"[质检删除] id={record_id}")
            return jsonify({'code': 0, 'message': '删除成功'}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[质检删除] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/quality/stats')
def api_quality_stats():
    """质检统计"""
    try:
        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN result='合格' THEN 1 ELSE 0 END) as passed,
                    SUM(CASE WHEN result='不合格' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN result IN ('待检', '待复检') THEN 1 ELSE 0 END) as pending
                FROM quality_records
            """)
            row = cur.fetchone()
            total = row['total'] if row else 0
            passed = row['passed'] if row else 0
            failed = row['failed'] if row else 0
            pending = row['pending'] if row else 0
            pass_rate = f"{passed / total * 100:.1f}%" if total > 0 else "0%"
            return jsonify({
                'code': 0,
                'data': {
                    'total': total, 'passed': passed, 'failed': failed,
                    'pending': pending, 'pass_rate': pass_rate
                }
            }), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[质检统计] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


# ── 发货管理增强 ───────────────────────────────────────────────────
@app.route('/shipment-admin')
def shipment_admin_page():
    return render_template('shipment_admin.html')


@app.route('/api/shipment/admin-list')
def api_shipment_admin_list():
    try:
        status_filter = request.args.get('status', '').strip()
        logistics_filter = request.args.get('logistics', '').strip()
        keyword = request.args.get('keyword', '').strip()
        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            sql = """
                SELECT s.*, o.product_type, o.quantity, o.unit, o.customer_name
                FROM shipments s
                LEFT JOIN orders o ON s.order_id = o.id
                WHERE 1=1
            """
            params = []
            if status_filter:
                sql += " AND s.status=%s"
                params.append(status_filter)
            if logistics_filter:
                sql += " AND s.logistics_company=%s"
                params.append(logistics_filter)
            if keyword:
                kw = f"%{keyword}%"
                sql += " AND (s.shipment_no LIKE %s OR s.order_no LIKE %s OR s.receiver_name LIKE %s OR s.tracking_no LIKE %s)"
                params.extend([kw, kw, kw, kw])
            sql += " ORDER BY s.created_at DESC LIMIT 500"
            cur.execute(sql, params)
            rows = cur.fetchall()
            return jsonify({'code': 0, 'data': [dict(r) for r in rows]}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[发货列表] 查询失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/shipment/add', methods=['POST'])
@require_auth
@verify_csrf_token
def api_shipment_add():
    try:
        data = request.get_json(silent=True) or {}
        order_id = data.get('order_id') or data.get('order_id')
        order_no = data.get('order_no')

        if not order_id and not order_no:
            return jsonify({'code': 400, 'message': '缺少 order_id 或 order_no'}), 400

        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("SHOW TABLES LIKE 'shipments'")
            if not cur.fetchone():
                cur.execute("""
                    CREATE TABLE shipments (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        shipment_no VARCHAR(50) NOT NULL UNIQUE,
                        order_id INT,
                        order_no VARCHAR(50),
                        receiver_name VARCHAR(100),
                        receiver_phone VARCHAR(20),
                        receiver_address VARCHAR(255),
                        logistics_company VARCHAR(50),
                        tracking_no VARCHAR(50),
                        status VARCHAR(20) DEFAULT '待发货',
                        shipped_at DATETIME,
                        warehouse VARCHAR(100) DEFAULT '',
                        freight DECIMAL(10,2) DEFAULT 0.00,
                        ship_remark TEXT,
                        receiver_remark TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                """)
            else:
                for col_def in [
                    ("warehouse", "VARCHAR(100) DEFAULT ''"),
                    ("freight", "DECIMAL(10,2) DEFAULT 0.00"),
                    ("ship_remark", "TEXT"),
                    ("receiver_remark", "TEXT"),
                ]:
                    cur.execute(f"SHOW COLUMNS FROM shipments LIKE '{col_def[0]}'")
                    if not cur.fetchone():
                        cur.execute(f"ALTER TABLE shipments ADD COLUMN {col_def[0]} {col_def[1]}")

            if order_id:
                cur.execute("SELECT order_no FROM orders WHERE id=%s LIMIT 1", (order_id,))
                row = cur.fetchone()
                if row:
                    order_no = row['order_no']

            # [P0-L 修复 2026-06-24] 运单号改用 UUID（高并发下 timestamp+random 有碰撞风险）
            shipment_no = f"SH{uuid.uuid4().hex[:16].upper()}"
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            tracking_no = data.get('tracking_no', '').strip()
            if not tracking_no:
                tracking_no = f"WB{uuid.uuid4().hex[:12].upper()}"

            cur.execute("""
                INSERT INTO shipments (
                    shipment_no, order_id, order_no, receiver_name, receiver_phone,
                    receiver_address, logistics_company, tracking_no, status,
                    warehouse, freight, ship_remark, receiver_remark, created_at
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                shipment_no,
                order_id or None,
                order_no or '',
                data.get('receiver_name', ''),
                data.get('receiver_phone', ''),
                data.get('receiver_address', ''),
                data.get('logistics_company', ''),
                tracking_no,
                data.get('status', '待发货'),
                data.get('warehouse', ''),
                data.get('freight', 0),
                data.get('ship_remark', ''),
                data.get('receiver_remark', ''),
                now
            ))
            new_id = cur.lastrowid if hasattr(cur, 'lastrowid') else None
            if not new_id:
                cur.execute("SELECT LAST_INSERT_ID() AS id")
                new_id = cur.fetchone()['id']
            conn.commit()
            logger.info(f"[发货创建] id={new_id} shipment_no={shipment_no}")
            return jsonify({'code': 0, 'message': '发货单创建成功', 'data': {'id': new_id, 'shipment_no': shipment_no}}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[发货创建] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/shipment/<int:shipment_id>')
def api_shipment_get(shipment_id):
    try:
        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT s.*, o.product_type, o.quantity, o.unit, o.customer_name
                FROM shipments s
                LEFT JOIN orders o ON s.order_id = o.id
                WHERE s.id=%s
            """, (shipment_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({'code': 404, 'message': '发货单不存在'}), 404
            return jsonify({'code': 0, 'data': dict(row)}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[发货详情] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/shipment/<int:shipment_id>', methods=['PUT'])
@require_auth
@verify_csrf_token
def api_shipment_update(shipment_id):
    try:
        data = request.get_json(silent=True) or {}
        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("SELECT id FROM shipments WHERE id=%s", (shipment_id,))
            if not cur.fetchone():
                return jsonify({'code': 404, 'message': '发货单不存在'}), 404

            _SHIPMENT_UPDATE_FIELDS = {'receiver_name', 'receiver_phone', 'receiver_address', 'logistics_company', 'tracking_no', 'warehouse', 'freight', 'ship_remark', 'receiver_remark', 'status'}
            fields = []
            params = []
            for key in _SHIPMENT_UPDATE_FIELDS:
                if key in data:
                    if key == 'status':
                        fields.append("status=%s")
                        params.append(data['status'])
                        if data['status'] in ('已发货', '已签收'):
                            fields.append("shipped_at=%s")
                            params.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    else:
                        fields.append(f"{key}=%s")
                        params.append(data[key])

            if not fields:
                return jsonify({'code': 400, 'message': '没有要更新的字段'}), 400

            params.append(shipment_id)
            sql = "UPDATE shipments SET {} WHERE id=%s".format(', '.join(fields))
            cur.execute(sql, params)
            conn.commit()
            logger.info(f"[发货更新] id={shipment_id}")
            return jsonify({'code': 0, 'message': '更新成功'}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[发货更新] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/shipment/<int:shipment_id>/status', methods=['PUT'])
@require_auth
@verify_csrf_token
def api_shipment_status(shipment_id):
    try:
        data = request.get_json(silent=True) or {}
        new_status = data.get('status')
        if not new_status:
            return jsonify({'code': 400, 'message': '缺少 status 参数'}), 400

        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, status FROM shipments WHERE id=%s", (shipment_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({'code': 404, 'message': '发货单不存在'}), 404

            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if new_status in ('已发货', '已签收'):
                cur.execute(
                    "UPDATE shipments SET status=%s, shipped_at=%s, updated_at=%s WHERE id=%s",
                    (new_status, now, now, shipment_id)
                )
            else:
                cur.execute(
                    "UPDATE shipments SET status=%s, updated_at=%s WHERE id=%s",
                    (new_status, now, shipment_id)
                )
            conn.commit()
            logger.info(f"[发货状态更新] id={shipment_id} status={new_status}")
            return jsonify({'code': 0, 'message': f'状态已更新为「{new_status}」'}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[发货状态更新] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


# [P0-C 修复 2026-06-24] 越权访问防护 - 删除发货记录 (仅管理员)
@app.route('/api/shipment/<int:shipment_id>', methods=['DELETE'])
@require_role('admin')
@verify_csrf_token
def api_shipment_delete(shipment_id):
    try:
        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("SELECT shipment_no FROM shipments WHERE id=%s", (shipment_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({'code': 404, 'message': '发货单不存在'}), 404

            # [P1-3 修复 2026-06-24] 软删除（符合 R-113 规则）
            try:
                cur.execute("""
                    UPDATE shipments SET is_deleted=1, updated_at=NOW()
                    WHERE id=%s
                """, (shipment_id,))
            except Exception:
                cur.execute("DELETE FROM shipments WHERE id=%s", (shipment_id,))
            conn.commit()
            logger.info(f"[发货删除] id={shipment_id} no={row['shipment_no']}")
            return jsonify({'code': 0, 'message': '删除成功'}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[发货删除] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/shipment/track/<int:shipment_id>')
def api_shipment_track(shipment_id):
    try:
        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM shipments WHERE id=%s", (shipment_id,))
            shipment = cur.fetchone()
            if not shipment:
                return jsonify({'code': 404, 'message': '发货单不存在'}), 404

            cur.execute("""
                SELECT * FROM shipment_tracking
                WHERE shipment_id=%s
                ORDER BY created_at DESC
            """, (shipment_id,))
            tracking = cur.fetchall()
            if not tracking:
                return jsonify({'code': 0, 'data': [{
                    'time': shipment.get('shipped_at') or shipment.get('created_at'),
                    'status': f"已发货，等待物流更新" if shipment.get('tracking_no') else "暂无物流信息",
                    'location': shipment.get('logistics_company') or ''
                }]}), 200
            return jsonify({'code': 0, 'data': [dict(t) for t in tracking]}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[物流轨迹] 查询失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/shipment/company/list')
@require_auth
def api_shipment_company_list():
    try:
        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("SHOW TABLES LIKE 'logistics_companies'")
            if not cur.fetchone():
                cur.execute("""
                    CREATE TABLE logistics_companies (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(50) NOT NULL,
                        code VARCHAR(20) UNIQUE,
                        phone VARCHAR(20),
                        remark VARCHAR(255),
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                default_companies = [
                    ('顺丰速运', 'SF', '95338'),
                    ('中通快递', 'ZTO', '95311'),
                    ('圆通速递', 'YTO', '95554'),
                    ('韵达快递', 'YUNDA', '95546'),
                    ('申通快递', 'STO', '95543'),
                    ('德邦快递', 'DEPPON', '95353'),
                    ('京东物流', 'JD', '950616'),
                ]
                for name, code, phone in default_companies:
                    try:
                        cur.execute(
                            "INSERT INTO logistics_companies (name, code, phone) VALUES (%s,%s,%s)",
                            (name, code, phone)
                        )
                    except Exception:
                        pass
                conn.commit()

            cur.execute("SELECT * FROM logistics_companies ORDER BY id ASC")
            rows = cur.fetchall()
            return jsonify({'code': 0, 'data': [dict(r) for r in rows]}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[物流公司列表] 查询失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/shipment/company', methods=['POST'])
@require_auth
@verify_csrf_token
def api_shipment_company_add():
    try:
        data = request.get_json(silent=True) or {}
        name = (data.get('name') or '').strip()
        code = (data.get('code') or '').strip()
        if not name or not code:
            return jsonify({'code': 400, 'message': '公司名称和代码不能为空'}), 400

        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("SELECT id FROM logistics_companies WHERE code=%s", (code,))
            if cur.fetchone():
                return jsonify({'code': 400, 'message': f'公司代码「{code}」已存在'}), 400

            cur.execute("""
                INSERT INTO logistics_companies (name, code, phone, remark)
                VALUES (%s,%s,%s,%s)
            """, (name, code, data.get('phone', ''), data.get('remark', '')))
            new_id = cur.lastrowid
            conn.commit()
            logger.info(f"[物流公司添加] id={new_id} name={name}")
            return jsonify({'code': 0, 'message': '添加成功', 'data': {'id': new_id}}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[物流公司添加] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/shipment/company/<int:company_id>', methods=['PUT'])
@require_auth
@verify_csrf_token
def api_shipment_company_update(company_id):
    try:
        data = request.get_json(silent=True) or {}
        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("SELECT id FROM logistics_companies WHERE id=%s", (company_id,))
            if not cur.fetchone():
                return jsonify({'code': 404, 'message': '物流公司不存在'}), 404

            new_code = (data.get('code') or '').strip()
            if new_code:
                cur.execute("SELECT id FROM logistics_companies WHERE code=%s AND id!=%s", (new_code, company_id))
                if cur.fetchone():
                    return jsonify({'code': 400, 'message': f'公司代码「{new_code}」已存在'}), 400

            _LOGISTICS_UPDATE_FIELDS = {'name', 'code', 'phone', 'remark'}
            fields = []
            params = []
            for key in _LOGISTICS_UPDATE_FIELDS:
                if key in data:
                    fields.append(f"{key}=%s")
                    params.append(data[key])
            if not fields:
                return jsonify({'code': 400, 'message': '没有要更新的字段'}), 400

            params.append(company_id)
            sql = "UPDATE logistics_companies SET {} WHERE id=%s".format(', '.join(fields))
            cur.execute(sql, params)
            conn.commit()
            logger.info(f"[物流公司更新] id={company_id}")
            return jsonify({'code': 0, 'message': '更新成功'}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[物流公司更新] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


@app.route('/api/shipment/company/<int:company_id>', methods=['DELETE'])
@require_auth
@verify_csrf_token
def api_shipment_company_delete(company_id):
    try:
        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("SELECT id FROM logistics_companies WHERE id=%s", (company_id,))
            if not cur.fetchone():
                return jsonify({'code': 404, 'message': '物流公司不存在'}), 404

            cur.execute("DELETE FROM logistics_companies WHERE id=%s", (company_id,))
            conn.commit()
            logger.info(f"[物流公司删除] id={company_id}")
            return jsonify({'code': 0, 'message': '删除成功'}), 200
        finally:
            if cur: cur.close()
            conn.close()
    except Exception as e:
        logger.exception('[物流公司删除] 失败')
        return jsonify({'code': 500, 'message': '服务器内部错误，请联系管理员'}), 500


if __name__ == '__main__':
    port = int(os.getenv('DESKTOP_WEB_PORT', 5001))
    logger.info(f'桌面 Web 启动: http://0.0.0.0:{port} (代理 {DISPATCH_BASE})')
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
