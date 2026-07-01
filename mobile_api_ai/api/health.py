# -*- coding: utf-8 -*-
import logging
from datetime import datetime
from flask import Blueprint, jsonify

logger = logging.getLogger(__name__)
bp = Blueprint('health', __name__, url_prefix='/api')


@bp.route('/health', methods=['GET'])
def health_check():
    components = {}
    all_ok = True

    try:
        from core.db import get_db_cursor
        with get_db_cursor() as (cursor, conn):
            cursor.execute('SELECT 1')
            cursor.fetchone()
        components['db'] = 'ok'
    except Exception as e:
        logger.warning(f'[Health] 数据库检查失败: {e}')
        components['db'] = 'error'
        all_ok = False

    try:
        from bots.base import GroupBot
        bot = GroupBot()
        if bot.is_connected():
            components['bot'] = 'ok'
        else:
            components['bot'] = 'disconnected'
            all_ok = False
    except Exception as e:
        logger.warning(f'[Health] 机器人检查失败: {e}')
        components['bot'] = 'error'
        all_ok = False

    status = 'ok' if all_ok else 'degraded'
    code = 0 if all_ok else 1
    return jsonify({
        'code': code,
        'message': status,
        'data': {
            'status': status,
            'service': 'mobile-api',
            'version': '3.0',
            'timestamp': datetime.now().isoformat(),
            'components': components,
        },
    }), 200
