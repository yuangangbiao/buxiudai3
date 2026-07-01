# -*- coding: utf-8 -*-
"""
企业微信 OAuth2 登录模块
通过 code 换取 UserId，匹配操作员，返回 JWT
"""
from flask import Blueprint, request, jsonify
import jwt
import requests
import logging
from datetime import datetime, timedelta, timezone
from core.config import WECHAT_CORP_ID, WECHAT_SECRET, JWT_SECRET_KEY, JWT_EXPIRE_HOURS
from container_config import container_config

logger = logging.getLogger(__name__)

bp = Blueprint('wecom', __name__, url_prefix='/api/wecom')


@bp.route('/login', methods=['POST'])
def wecom_login():
    data = request.get_json(silent=True) or {}
    code = (data.get('code') or '').strip()

    if not code:
        return jsonify({'code': 400, 'message': '缺少参数 code'})

    if not WECHAT_CORP_ID or not WECHAT_SECRET:
        logger.error('企业微信配置缺失: WECHAT_CORP_ID 或 WECHAT_SECRET 未设置')
        return jsonify({'code': 500, 'message': '系统配置缺失'})

    try:
        token_resp = requests.get(
            'https://qyapi.weixin.qq.com/cgi-bin/gettoken',
            params={'corpid': WECHAT_CORP_ID, 'corpsecret': WECHAT_SECRET},
            timeout=10
        )
        token_data = token_resp.json()
    except requests.RequestException as e:
        logger.error(f'获取 access_token 网络异常: {e}')
        return jsonify({'code': 500, 'message': '企业微信服务连接失败'})

    if token_data.get('errcode') != 0:
        logger.error(f'获取 access_token 失败: {token_data}')
        return jsonify({'code': 500, 'message': '企业微信认证失败，请检查配置'})

    access_token = token_data['access_token']

    try:
        user_resp = requests.get(
            'https://qyapi.weixin.qq.com/cgi-bin/auth/getuserinfo3rd',
            params={'access_token': access_token, 'code': code},
            timeout=10
        )
        user_data = user_resp.json()
    except requests.RequestException as e:
        logger.error(f'获取用户信息网络异常: {e}')
        return jsonify({'code': 500, 'message': '企业微信服务连接失败'})

    if user_data.get('errcode') != 0:
        logger.error(f'获取用户信息失败: {user_data}')
        return jsonify({'code': 500, 'message': '获取用户信息失败，请重试'})

    userid = user_data.get('UserId') or user_data.get('OpenId')
    if not userid:
        return jsonify({'code': 500, 'message': '未获取到用户身份'})

    matched_op = None
    for op in container_config.get_all_operators():
        if op.wechat_userid == userid:
            matched_op = op
            break

    if not matched_op:
        return jsonify({'code': 401, 'message': '该企业微信用户未授权，请先在调度中心同步操作员'})

    if not matched_op.enabled:
        return jsonify({'code': 403, 'message': '账号已被禁用'})

    token = jwt.encode({
        'userid': matched_op.wechat_userid,
        'op_id': matched_op.id,
        'name': matched_op.name,
        'role': matched_op.role,
        'permissions': {
            'can_receive_wechat': getattr(matched_op, 'can_receive_wechat', False),
            'can_send_wechat': getattr(matched_op, 'can_send_wechat', False),
        },
        'exp': datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    }, JWT_SECRET_KEY, algorithm='HS256')

    return jsonify({
        'code': 0,
        'message': '登录成功',
        'token': token,
        'operator': {
            'id': matched_op.id,
            'name': matched_op.name,
            'role': matched_op.role,
            'department': matched_op.department,
            'can_receive_wechat': getattr(matched_op, 'can_receive_wechat', False),
            'can_send_wechat': getattr(matched_op, 'can_send_wechat', False),
        }
    })
