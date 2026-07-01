# -*- coding: utf-8 -*-
"""
容器池架构API服务器
移动端通过此API与容器池交互，不直接访问数据库
"""
from core.config import REQUEST_TIMEOUT_FAST, DB_PATHS, SERVICE_URLS, FLASK_HOST, CONTAINER_CENTER_PORT

import json
import logging
from flask import Flask, request, jsonify, render_template, redirect
from core.cors_config import init_cors
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import jwt
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

from container import task_pool, Dispatcher, TaskPublisher
from container.task_pool import PAGE_TO_TYPES
from container_dashboard import container_dashboard_bp

app = Flask(__name__)
init_cors(app, default_origins='http://localhost:5000,http://localhost:3000')
Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=os.getenv('DEFAULT_RATE_LIMITS', '1000 per day, 300 per hour').split(', '),
    storage_uri=os.getenv('LIMITER_STORAGE_URI', 'memory://'),
)

app.register_blueprint(container_dashboard_bp, url_prefix='/container')

container_center = None
try:
    from container_center_v5 import ContainerCenter
    container_center = ContainerCenter()
    logger.info("[API Server] 容器中心初始化成功")
except Exception as e:
    logger.warning(f"[API Server] 容器中心初始化失败: {e}")

SECRET_KEY = os.getenv('JWT_SECRET_KEY')

dispatcher = Dispatcher(task_pool)
publisher = TaskPublisher(task_pool)

def _load_operators():
    """从 container_center_api 同步加载操作员，避免硬编码假数据"""
    try:
        from container_center_api import _load_operators_from_enterprise
        ops = _load_operators_from_enterprise()
        if ops:
            return ops
    except Exception:
        pass
    return []

OPERATORS = _load_operators()

def success(data=None, message='success'):
    result = {'code': 0, 'message': message}
    if data is not None:
        result['data'] = data
    return jsonify(result)

def fail(code=1, message='操作失败'):
    return jsonify({'code': code, 'message': message})

def get_current_operator():
    """从Token获取当前操作员"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    token = auth_header[7:]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.InvalidTokenError as e:
        logger.warning(f"JWT Token验证失败: {e}")
        return None

@app.route('/health')
def health():
    return success({'service': 'container-api', 'version': '3.0'})

@app.route('/api/health')
def api_health():
    """API健康检查（供3.0版本测试连接使用）"""
    return jsonify({
        'status': 'running',
        'service': 'container-api',
        'version': '3.0',
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/api/status')
def api_status():
    """获取容器状态（供3.0版本刷新状态使用）"""
    return jsonify({
        'status': 'running',
        'version': '3.0',
        'service': 'container-api',
        'containers': 0,
        'active_tasks': 0,
        'pool_status': {},
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/api/version')
def api_version():
    """获取API版本信息（供主软件连接测试使用）"""
    return success(data={
        'version': '3.0',
        'service': '容器中心API',
        'status': 'running',
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/')
def index():
    accept = request.headers.get('Accept', '')
    if 'text/html' in accept:
        return redirect('/container/')
    pool_status = task_pool.get_pool_status()
    return success({'service': '容器池架构API', 'version': '3.0', 'pool_status': pool_status})

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    operator_id = data.get('operator_id')

    operator = next((op for op in OPERATORS if op['operator_id'] == operator_id), None)
    if not operator:
        return fail(code=1002, message='操作员不存在')

    token_payload = {
        'operator_id': operator_id,
        'name': operator['name'],
        'role': operator['role'],
        'team_name': operator['team_name'],
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    token = jwt.encode(token_payload, SECRET_KEY, algorithm='HS256')

    return success(data={
        'token': token,
        'operator': {
            'id': operator['operator_id'],
            'name': operator['name'],
            'role': operator['role'],
            'team_name': operator['team_name']
        }
    })

@app.route('/api/auth/verify', methods=['GET'])
def verify():
    operator = get_current_operator()
    if not operator:
        return fail(code=1002, message='无效的Token')
    return success(data={'valid': True, 'operator': operator})

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """获取当前员工的任务列表"""
    operator = get_current_operator()
    if not operator:
        return fail(code=1002, message='请先登录')

    page_route = request.args.get('page_route', None)
    types_param = request.args.get('types', None)

    # page_route 与 types 互斥
    if page_route and types_param:
        return fail(code=1003, message='page_route 与 types 互斥，请二选一')

    if page_route:
        task_types = PAGE_TO_TYPES.get(page_route)
        if not task_types:
            return fail(code=1004, message=f'未知的 page_route: {page_route}')
    else:
        task_types = (types_param or 'report,quality,material,approval').split(',')

    # 修补 T10 (F10.3): 接受 flow_types query 参数 (D-T10.4: getlist 支持多值)
    flow_types_param = request.args.getlist('flow_types')
    flow_types = flow_types_param if flow_types_param else None

    status = request.args.get('status', None)

    if flow_types is not None:
        # 修补 T10 (F10.3): flow_types 显式优先, 走 flow_type 路由
        tasks = []
        for ft in flow_types or ['production', 'quality', 'material_purchase', 'outsource', 'repair']:
            tasks.extend(task_pool.get_tasks_by_flow_type(
                ft, status=status or 'pending', operator_id=operator['operator_id']
            ))
    elif status:
        tasks = task_pool.get_tasks_by_types(task_types, status=status, operator_id=operator['operator_id'])
    else:
        tasks = task_pool.get_pending_tasks(operator['operator_id'], task_types)

    return success(data={
        'tasks': [t.to_dict() for t in tasks],
        'total': len(tasks)
    })

@app.route('/api/tasks/dispatch', methods=['POST'])
def dispatch_tasks():
    """批量获取并锁定任务（登录后自动调用）"""
    operator = get_current_operator()
    if not operator:
        return fail(code=1002, message='请先登录')

    data = request.get_json(silent=True) or {}
    task_types = data.get('task_types', ['report', 'quality', 'material', 'approval'])
    max_count = data.get('max_count', 10)
    # 修补 T10 (F10.3): 接受 body flow_types (列表) 透传到 dispatcher
    flow_types = data.get('flow_types', None)  # None 走原路径

    result = dispatcher.dispatch(operator['operator_id'], task_types,
                                  flow_types=flow_types, max_count=max_count)
    return jsonify(result.to_dict())

@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task_detail(task_id):
    """获取任务详情"""
    operator = get_current_operator()
    if not operator:
        return fail(code=1002, message='请先登录')

    result = dispatcher.get_task_detail(task_id, operator['operator_id'])
    return jsonify(result.to_dict())

@app.route('/api/tasks/<task_id>/start', methods=['POST'])
def start_task(task_id):
    """开始执行任务"""
    operator = get_current_operator()
    if not operator:
        return fail(code=1002, message='请先登录')

    if task_pool.start_task(task_id):
        task = task_pool.get_task(task_id)
        return success(message='任务已开始', data=task.to_dict())
    return fail(message='任务启动失败')

@app.route('/api/tasks/<task_id>/complete', methods=['POST'])
def complete_task(task_id):
    """提交任务结果"""
    operator = get_current_operator()
    if not operator:
        return fail(code=1002, message='请先登录')

    data = request.get_json(silent=True) or {}

    result = dispatcher.receive_result(task_id, data)
    return jsonify(result.to_dict())

@app.route('/api/ai/speech-to-report', methods=['POST'])
def speech_to_report():
    """语音转报工 - 解析语音文本，生成报工数据"""
    operator = get_current_operator()
    if not operator:
        return fail(code=1002, message='请先登录')

    data = request.get_json(silent=True) or {}
    text = data.get('text', '')

    import re

    process_patterns = {
        '来料检验': ['来料'], '裁剪': ['裁剪'], '编织': ['编织'],
        '定型': ['定型'], '质检': ['质检', '检验'], '包装': ['包装']
    }

    process_name = None
    for name, patterns in process_patterns.items():
        if any(p in text for p in patterns):
            process_name = name
            break

    quantity_match = re.search(r'(\d+)', text)
    quantity = int(quantity_match.group(1)) if quantity_match else None

    if '完成' in text or '完了' in text:
        status = '已完成'
        confidence = 0.95
    elif '进行' in text:
        status = '进行中'
        confidence = 0.9
    else:
        status = '进行中'
        confidence = 0.8

    needs_confirm = not process_name or not quantity

    return success(data={
        'parsed': {
            'raw_text': text,
            'process_name': process_name,
            'quantity': quantity,
            'unit': '米',
            'status': status,
            'confidence': confidence
        },
        'needs_confirmation': needs_confirm,
        'confirm_data': None if needs_confirm else {
            'process_name': process_name,
            'quantity': quantity,
            'unit': '米',
            'status': status,
            'confidence': confidence
        }
    })

@app.route('/api/ai/chat', methods=['POST'])
def ai_chat():
    """AI对话"""
    operator = get_current_operator()
    if not operator:
        return fail(code=1002, message='请先登录')

    data = request.get_json(silent=True) or {}
    query = data.get('query', '')

    pending_tasks = task_pool.get_pending_tasks(operator['operator_id'])

    if '任务' in query or '待处理' in query:
        if not pending_tasks:
            reply = '您目前没有待处理的任务 👍'
        else:
            task_lines = []
            for i, t in enumerate(pending_tasks[:5], 1):
                task_lines.append(f"{i}. {t.title}")
            reply = f"您有 {len(pending_tasks)} 个待处理任务：\n" + "\n".join(task_lines)
        return success(data={'reply': reply, 'type': 'task_list'})

    if '进度' in query or '到哪' in query:
        order_no_match = re.search(r'ORD\d+', query, re.IGNORECASE)
        if order_no_match:
            order_no = order_no_match.group(0).upper()
            tasks = [t for t in pending_tasks if t.related_order == order_no]
            if tasks:
                reply = f"订单 {order_no} 有 {len(tasks)} 个待处理任务"
            else:
                reply = f"订单 {order_no} 没有待处理任务"
            return success(data={'reply': reply, 'type': 'order_status'})

    if '帮助' in query:
        reply = """AI助手支持：
📋 查看任务 - "今天有什么任务"
📦 订单进度 - "ORD202604001到哪一步了"
"""
        return success(data={'reply': reply, 'type': 'help'})

    return success(data={'reply': '抱歉，我还没理解。请试试："今天有什么任务"', 'type': 'unknown'})

@app.route('/api/pool/status', methods=['GET'])
def pool_status():
    """获取容器池状态（仅管理员）"""
    operator = get_current_operator()
    if not operator:
        return fail(code=1002, message='请先登录')

    if operator.get('role') not in ['主管', '班组长']:
        return fail(code=1003, message='需要管理员权限')

    return success(data=task_pool.get_pool_status())

@app.route('/api/operators', methods=['GET'])
def get_operators():
    """获取操作员列表（供3.0版本调用）"""
    return success(data={
        'operators': OPERATORS
    })

@app.route('/api/dispatch', methods=['POST'])
def dispatch_task():
    """发布任务到指定操作员（供3.0版本调用）"""
    data = request.get_json(silent=True) or {}

    operator_id = data.get('operator_id')
    order_no = data.get('order_no')
    process = data.get('process', data.get('process_name', ''))
    quantity = data.get('quantity', 0)
    priority = data.get('priority', 'normal')
    source = data.get('source', 'main_software')

    if not operator_id:
        return fail(code=1001, message='缺少operator_id参数')

    operator = next((op for op in OPERATORS if op['operator_id'] == operator_id), None)
    if not operator:
        return fail(code=1002, message=f'操作员 {operator_id} 不存在')

    from container import Task, TaskType
    task = Task(
        task_type='report',
        title=f'{process}报工',
        content={
            'order_no': order_no,
            'process_name': process,
            'quantity': quantity
        },
        operator_id=operator_id,
        priority=priority,
        related_order=order_no,
        tags=[source]
    )

    task_id = task_pool.add_task(task)

    logger.info(f"[3.0对接] 派工成功: 订单{order_no}, 工序{process}, 操作员{operator['name']}")

    return success(data={
        'task_id': task_id,
        'operator_id': operator_id,
        'operator_name': operator['name'],
        'order_no': order_no,
        'process': process
    })

@app.route('/api/internal/publish', methods=['POST'])
def internal_publish():
    """内部发布任务接口（供桌面端调用）"""
    data = request.get_json(silent=True) or {}

    task_type = data.get('task_type')
    title = data.get('title')
    content = data.get('content', {})
    operator_id = data.get('operator_id')
    priority = data.get('priority', 'normal')
    related_order = data.get('related_order')
    tags = data.get('tags', [])

    from container import Task, TaskType

    type_map = {
        'report': 'report',
        'quality': 'quality',
        'material': 'material',
        'approval': 'approval'
    }

    task = Task(
        task_type=type_map.get(task_type, 'other'),
        title=title or f'任务',
        content=content,
        operator_id=operator_id,
        priority=priority,
        related_order=related_order,
        tags=tags
    )

    task_id = task_pool.add_task(task)

    return jsonify({
        'success': True,
        'task_id': task_id,
        'message': f'任务已发布: {title}'
    })

@app.route('/publish-tasks', methods=['POST'])
def publish_tasks():
    """发布示例任务到容器池（模拟桌面端发布）"""
    global task_pool, dispatcher, publisher

    task_pool.tasks.clear()
    task_pool.task_index = {k: [] for k in task_pool.task_index.keys()}

    publisher = TaskPublisher(task_pool)
    dispatcher = Dispatcher(task_pool)

    t1 = publisher.publish_report_task('ORD202604001', '编织', 103, 'OP001', 100, 'high')
    t2 = publisher.publish_report_task('ORD202604001', '定型', 104, 'OP002', 100, 'normal')
    t3 = publisher.publish_report_task('ORD202604002', '编织', 201, 'OP001', 200, 'normal')
    t4 = publisher.publish_quality_task('ORD202604001', 1, 'OP004', '终检', 'high')
    t5 = publisher.publish_quality_task('ORD202604002', 2, 'OP004', '首检', 'normal')
    t6 = publisher.publish_material_task('ORD202604001', '不锈钢丝', 50, 'OP003', 'normal')
    t7 = publisher.publish_approval_task('ORD202604001', 1, 'MG001', '原材料质量问题需要经理审批', 'high')

    return jsonify({
        'success': True,
        'message': '已发布7个示例任务',
        'task_ids': [t1, t2, t3, t4, t5, t6, t7],
        'pool_status': task_pool.get_pool_status()
    })

@app.route('/api/schedule/publish', methods=['POST'])
def schedule_publish():
    """
    排产发布接口（供3.0主软件调用）
    
    接收主软件发布的排产数据，存入容器池供调度中心→云端→企业微信流转。
    不需要 operator_id，因为排产任务由调度中心分配，非直接指定操作员。
    """
    data = request.get_json(silent=True) or {}

    order_no = data.get('order_no', '')
    prod_id = data.get('prod_id', 0)
    order_no = data.get('order_no', '')

    if not order_no:
        return jsonify({'code': 1001, 'message': '缺少order_no参数', 'success': False})

    # 构建排产任务存入容器池
    from container import Task

    task = Task(
        task_type='other',
        title=f'排产任务-{order_no}',
        content={
            'order_no': order_no,
            'prod_id': prod_id,
            'order_no': order_no,
            'customer_group': data.get('customer_group', ''),
            'product_type': data.get('product_type', ''),
            'material': data.get('material', ''),
            'mesh_size': data.get('mesh_size', ''),
            'wire_diameter': data.get('wire_diameter', ''),
            'width': data.get('width', ''),
            'length': data.get('length', ''),
            'quantity': data.get('quantity', 0),
            'unit': data.get('unit', '米'),
            'surface_treatment': data.get('surface_treatment', ''),
            'special_requirements': data.get('special_requirements', ''),
            'delivery_date': data.get('delivery_date', ''),
            'remark': data.get('remark', ''),
            'plan_start': data.get('plan_start', ''),
            'plan_end': data.get('plan_end', ''),
            'extra_params': data.get('extra_params', {}),
            'source': data.get('source', 'main_software'),
            'status': 'pending'
        },
        operator_id=None,
        priority='high',
        related_order=order_no,
        tags=['schedule', 'main_software']
    )

    task_id = task_pool.add_task(task)

    logger.info(f"[排产发布] 成功: 工单={order_no}, 订单={order_no}, task_id={task_id}")

    # 同步写入容器中心数据库（如果已初始化）
    if container_center is not None:
        try:
            from container_center_v5 import DataType, DataStatus, DataPackage
            pkg = DataPackage(
                data_type='other',
                title=f'排产-{order_no}',
                content={
                    'order_no': order_no,
                    'prod_id': prod_id,
                    'order_no': order_no,
                    'task_id': task_id
                },
                source='main_software',
                priority='high'
            )
            container_center.storage.add_package(pkg.to_dict())
        except Exception as e:
            logger.warning(f"[排产发布] 容器中心存储写入失败: {e}")

    # === 写入调度中心流程编排数据（发布成功的唯一判定标准）===
    dispatch_written = False
    try:
        import uuid as _uuid
        from datetime import datetime as _dt
        dispatch_data_file = DB_PATHS['dispatch_center_data']
        dispatch_data_dir = os.path.dirname(dispatch_data_file)
        if not os.path.exists(dispatch_data_dir):
            os.makedirs(dispatch_data_dir, exist_ok=True)

        existing_data = {'processes': []}
        if os.path.exists(dispatch_data_file):
            try:
                with open(dispatch_data_file, 'r', encoding='utf-8') as _f:
                    existing_data = json.load(_f)
            except (json.JSONDecodeError, IOError):
                existing_data = {'processes': []}

        if 'processes' not in existing_data:
            existing_data['processes'] = []

        already_exists = any(p.get('order_no') == order_no for p in existing_data['processes'])
        if not already_exists:
            production_steps = [
                {'name': '工单发布', 'role': '计划部', 'status_key': 'published'},
                {'name': '排产制定', 'role': '生产部', 'status_key': 'scheduled'},
                {'name': '排产确认', 'role': '计划部', 'status_key': 'confirmed'},
                {'name': '生产执行', 'role': '生产部', 'status_key': 'in_production'},
                {'name': '质检审核', 'role': '质检部', 'status_key': 'qc_passed', 'parallel': True},
                {'name': '报工完成', 'role': '生产部', 'status_key': 'reported'},
                {'name': '完工入库', 'role': '仓库', 'status_key': 'completed'},
                {'name': '发货', 'role': '仓库', 'status_key': 'shipped'},
            ]
            new_process = {
                'id': str(_uuid.uuid4())[:8],
                'order_no': order_no,
                'product_name': data.get('product_type', '') or data.get('material', ''),
                'quantity': data.get('quantity', 0),
                'status': 'created',
                'flow_type': 'production',
                'current_step': 0,
                'steps': production_steps,
                'created_at': _dt.now().isoformat(),
                'updated_at': _dt.now().isoformat(),
            }
            existing_data['processes'].append(new_process)
            with open(dispatch_data_file, 'w', encoding='utf-8') as _f:
                json.dump(existing_data, _f, ensure_ascii=False, indent=2, default=str)
            logger.info(f"[排产发布] 调度中心流程已写入文件: {order_no}")
            dispatch_written = True
        else:
            logger.info(f"[排产发布] 工单 {order_no} 流程已存在，跳过写入")
            dispatch_written = True
    except Exception as e:
        logger.error(f"[排产发布] 调度中心数据文件写入失败: {e}")
        dispatch_written = False

    if not dispatch_written:
        return jsonify({
            'code': 5001,
            'success': False,
            'message': f'排产任务已存入容器池，但调度中心流程编排写入失败：无法同步到调度中心',
            'data': {
                'task_id': task_id,
                'order_no': order_no,
                'prod_id': prod_id
            }
        })

    # 同时通过HTTP通知调度中心（端口5000），确保实时同步
    try:
        import requests as _req
        dispatch_base_url = SERVICE_URLS['dispatch_center']
        dispatch_url = f'{dispatch_base_url}/api/dispatch-center/processes'
        dispatch_payload = {
            'flow_type': 'production',
            'order_no': order_no,
            'product_name': data.get('product_type', '') or data.get('material', ''),
            'quantity': data.get('quantity', 0),
            'source': 'container_center'
        }
        _resp = _req.post(dispatch_url, json=dispatch_payload, timeout=REQUEST_TIMEOUT_FAST)
        if _resp.status_code in (200, 400):
            logger.info(f"[排产发布] 调度中心HTTP通知完成: {order_no}")
    except Exception as e:
        logger.info(f"[排产发布] 调度中心HTTP通知（可忽略）: {e}")

    return jsonify({
        'code': 0,
        'success': True,
        'message': f'排产任务已发布（调度中心已接收）: {order_no}',
        'data': {
            'task_id': task_id,
            'order_no': order_no,
            'prod_id': prod_id
        }
    })

if __name__ == '__main__':
    from logging_setup import setup_daily_logger
    setup_daily_logger('container_api')
    logger = logging.getLogger(__name__)

    logger.info('=' * 60)
    logger.info('容器池架构API服务器 v3.0')
    logger.info('=' * 60)
    logger.info('架构：移动端 → API → 容器池 → 桌面端数据库')
    logger.info('安全：数据库完全不暴露在外网')
    logger.info('=' * 60)
    logger.info('[Server] 容器API服务启动')
    app.run(host=FLASK_HOST, port=CONTAINER_CENTER_PORT, debug=False)
