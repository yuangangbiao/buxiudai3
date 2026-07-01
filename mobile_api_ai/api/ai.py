# -*- coding: utf-8 -*-
"""
AI模块 - 语音识别、图像分析、智能对话
"""
from flask import Blueprint, request, jsonify
import re
import random
from .auth import success, fail

bp = Blueprint('ai', __name__, url_prefix='/api/ai')

ORDERS = [
    {'id': 1, 'order_no': 'ORD202604001', 'customer_name': '上海机械厂', 'product_type': '不锈钢编织网', 'quantity': 100, 'unit': '米', 'status': '生产中', 'delivery_date': '2026-05-10'},
    {'id': 2, 'order_no': 'ORD202604002', 'customer_name': '北京设备公司', 'product_type': '不锈钢丝网', 'quantity': 200, 'unit': '米', 'status': '已排产', 'delivery_date': '2026-05-15'},
    {'id': 3, 'order_no': 'ORD202604003', 'customer_name': '广州五金厂', 'product_type': '精密筛网', 'quantity': 50, 'unit': '平方米', 'status': '质检中', 'delivery_date': '2026-05-08'},
]

PROCESS_RECORDS = [
    {'id': 101, 'order_id': 1, 'process_name': '来料检验', 'status': '已完成', 'completed_qty': 100},
    {'id': 102, 'order_id': 1, 'process_name': '裁剪', 'status': '已完成', 'completed_qty': 100},
    {'id': 103, 'order_id': 1, 'process_name': '编织', 'status': '进行中', 'completed_qty': 60},
    {'id': 104, 'order_id': 1, 'process_name': '定型', 'status': '待开始', 'completed_qty': 0},
    {'id': 105, 'order_id': 1, 'process_name': '质检', 'status': '待开始', 'completed_qty': 0},
    {'id': 106, 'order_id': 1, 'process_name': '包装', 'status': '待开始', 'completed_qty': 0},
]

def parse_voice_report(text):
    """
    解析语音报工文本
    支持格式：
    - "裁剪200米完成了"
    - "编织进行了80"
    - "质检合格"
    - "完成了100米编织"
    """
    text = text.strip()

    result = {
        'process_name': None,
        'quantity': None,
        'status': None,
        'unit': '米',
        'confidence': 0.0,
        'raw_text': text
    }

    process_patterns = {
        '来料检验': [r'来料.*检验', r'来料检验'],
        '裁剪': [r'裁剪', r'切割'],
        '编织': [r'编织', r'编织'],
        '定型': [r'定型', r'定形'],
        '质检': [r'质检', r'检验', r'质量检验'],
        '包装': [r'包装', r'打包'],
    }

    for process_name, patterns in process_patterns.items():
        for pattern in patterns:
            if re.search(pattern, text):
                result['process_name'] = process_name
                break

    quantity_patterns = [
        r'(\d+)\s*(?:米|平方米|个|件|套)',
        r'完成了?\s*(\d+)',
        r'(\d+)\s*(?:完成了|进行中)',
        r'进行[了]?\s*(\d+)',
    ]

    for pattern in quantity_patterns:
        match = re.search(pattern, text)
        if match:
            result['quantity'] = int(match.group(1))
            break

    if '完成' in text or '完了' in text or '结束了' in text:
        result['status'] = '已完成'
        result['confidence'] = 0.9
    elif '进行' in text or '中' in text:
        result['status'] = '进行中'
        result['confidence'] = 0.85
    elif '合格' in text or '没问题' in text:
        result['status'] = '合格'
        result['confidence'] = 0.9
    elif '不合格' in text or '有问题' in text:
        result['status'] = '不合格'
        result['confidence'] = 0.9

    if result['quantity'] and result['process_name']:
        result['confidence'] = 0.95

    return result

def analyze_image_mock(image_data):
    """
    模拟图像分析（实际使用阿里云视觉API）
    返回质检建议
    """
    issues = []
    score = random.randint(85, 100)

    if score < 90:
        issues.append({'type': '轻微划痕', 'position': '边缘区域', 'severity': '低'})

    return {
        'score': score,
        'result': '合格' if score >= 90 else '需复检',
        'issues': issues,
        'suggestion': '人工复核' if issues else '无需人工复核',
        'confidence': 0.92
    }

@bp.route('/speech-to-report', methods=['POST'])
def speech_to_report():
    """
    语音转报工：接收语音识别文本，解析为报工数据
    """
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        data = {}

    text = data.get('text', '')
    if not text:
        return fail(code=3001, message='语音文本不能为空')

    parsed = parse_voice_report(text)

    if not parsed['process_name'] or not parsed['quantity']:
        return success(data={
            'parsed': parsed,
            'needs_confirmation': True,
            'message': '请确认报工信息',
            'suggestions': {
                'processes': ['裁剪', '编织', '定型', '质检', '包装'],
                'format_example': '例如："裁剪200米完成了"'
            }
        })

    return success(data={
        'parsed': parsed,
        'needs_confirmation': False,
        'confirm_data': {
            'process_name': parsed['process_name'],
            'quantity': parsed['quantity'],
            'unit': parsed['unit'],
            'status': parsed['status'],
            'confidence': parsed['confidence']
        }
    })

@bp.route('/image-analysis', methods=['POST'])
def image_analysis():
    """
    图像分析：接收图片，分析质量
    """
    if 'image' not in request.files and 'image_url' not in (request.get_json() or {}):
        return fail(code=3002, message='请提供图片')

    image_data = request.files.get('image')
    analysis_result = analyze_image_mock(image_data)

    return success(data={
        'analysis': analysis_result,
        'message': 'AI分析完成，请人工确认',
        'action_required': True
    })

@bp.route('/chat', methods=['POST'])
def ai_chat():
    """
    AI智能对话：查询订单进度、工序状态等
    """
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        data = {}

    query = data.get('query', '')
    user_id = data.get('user_id', 'OP001')

    if not query:
        return fail(code=3003, message='问题内容不能为空')

    query = query.lower().strip()

    if '进度' in query or '到哪' in query or '状态' in query:
        order_no_match = re.search(r'ord\d+', query, re.IGNORECASE)
        if order_no_match:
            order_no = order_no_match.group(0).upper()
            order = next((o for o in ORDERS if o['order_no'] == order_no), None)
            if order:
                processes = [p for p in PROCESS_RECORDS if p['order_id'] == order['id']]
                completed = len([p for p in processes if p['status'] == '已完成'])
                percentage = round(completed / len(processes) * 100, 2) if processes else 0

                process_list = []
                for p in processes:
                    icon = '✅' if p['status'] == '已完成' else ('🔄' if p['status'] == '进行中' else '⏳')
                    process_list.append(f"{icon} {p['process_name']} - {p['status']}")

                reply = f"""订单{order['order_no']}进度：
━━━━━━━━━━━━━━━━━━━━
客户：{order['customer_name']}
产品：{order['product_type']} {order['quantity']}{order['unit']}
━━━━━━━━━━━━━━━━━━━━
{'\\n'.join(process_list)}
━━━━━━━━━━━━━━━━━━━━
预计完工：{order.get('delivery_date', '待确定')}"""

                return success(data={'reply': reply, 'type': 'order_progress'})

    if '任务' in query or '有什么' in query or '待处理' in query:
        return success(data={
            'reply': '您今天有3个任务：\n1. 编织工单WO202604001 - 进行中(60/100米)\n2. 裁剪工单WO202604002 - 待开始(50米)\n3. 质检工单WO202604003 - 待处理\n\n需要我帮您查看详情吗？',
            'type': 'task_list'
        })

    if '帮助' in query or 'help' in query or '怎么用' in query:
        return success(data={
            'reply': '''AI助手支持以下功能：
━━━━━━━━━━━━━━━
1. 查询订单进度
   例如："ORD202604001到哪一步了"

2. 查看我的任务
   例如："今天有哪些任务"

3. 报工（语音模式）
   例如："裁剪200米完成了"

4. 质检辅助
   拍照上传，AI自动分析
━━━━━━━━━━━━━━━''',
            'type': 'help'
        })

    return success(data={
        'reply': '抱歉，我还没理解您的问题。\n可以试试：\n- "ORD202604001到哪一步了"\n- "今天有哪些任务"\n- "帮助"',
        'type': 'unknown'
    })

@bp.route('/chat/history', methods=['GET'])
def chat_history():
    """获取对话历史"""
    user_id = request.args.get('user_id', 'OP001')
    return success(data={
        'history': [
            {'role': 'user', 'content': 'ORD202604001到哪一步了', 'time': '2026-04-29 10:00:00'},
            {'role': 'ai', 'content': '订单ORD202604001当前在编织工序...', 'time': '2026-04-29 10:00:01'},
        ],
        'total': 2
    })
