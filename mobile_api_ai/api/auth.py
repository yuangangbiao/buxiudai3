# -*- coding: utf-8 -*-
"""
认证模块 - 员工扫码登录
"""
from flask import Blueprint, request, jsonify
import jwt
import os
import json
from datetime import datetime, timedelta
from mobile_api_ai.api.limiter import limiter
from core.config import DB_PATHS

bp = Blueprint('auth', __name__, url_prefix='/api/auth')

SECRET_KEY = os.getenv('JWT_SECRET_KEY')

def _load_operators():
    """从项目根 operators.json 加载真实操作员列表"""
    path = DB_PATHS['project_operators']
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        return [
            {
                'operator_id': v.get('id', k),
                'name': v.get('name', k),
                'role': v.get('role', '工人'),
                'team_name': v.get('department', ''),
                'status': 'active' if v.get('enabled', True) else 'disabled'
            }
            for k, v in raw.items()
        ]
    return [{'operator_id': 'YuanGangBiao', 'name': '苑岗彪', 'role': '员工', 'team_name': '宁津', 'status': 'active'}]

OPERATORS = _load_operators()

def api_response(code=0, message='success', data=None):
    response = {'code': code, 'message': message}
    if data is not None:
        response['data'] = data
    return jsonify(response)

def success(data=None, message='success'):
    return api_response(code=0, message=message, data=data)

def fail(code=1, message='操作失败'):
    return api_response(code=code, message=message)

@bp.route('/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        data = {}
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

@bp.route('/verify', methods=['GET'])
@limiter.limit("30 per minute")
def verify():
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return fail(code=1002, message='无效的Token')

    token = auth_header[7:]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return success(data={'valid': True, 'operator': payload})
    except jwt.ExpiredSignatureError:
        return fail(code=1003, message='Token已过期')
    except jwt.InvalidTokenError:
        return fail(code=1004, message='无效的Token')

@bp.route('/info', methods=['GET'])
@limiter.limit("30 per minute")
def info():
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return fail(code=1002, message='无效的Token')

    token = auth_header[7:]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return success(data={'operator': payload})
    except jwt.ExpiredSignatureError:
        return fail(code=1003, message='Token已过期')
    except jwt.InvalidTokenError:
        return fail(code=1004, message='无效的Token')
