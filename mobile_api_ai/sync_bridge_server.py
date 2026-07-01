# -*- coding: utf-8 -*-
"""
Sync Bridge 服务启动脚本
功能：同步容器中心状态到 MySQL 数据库
端口：8008
"""

import os
import sys
import logging

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJ_ROOT = os.path.dirname(APP_DIR)
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)
if PROJ_ROOT not in sys.path:
    sys.path.append(PROJ_ROOT)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

from flask import Flask, jsonify, request
from sync_bridge import sync_bp

# 加载 .env 配置
try:
    from dotenv import load_dotenv
    # 指定 .env 文件的绝对路径
    env_path = os.path.join(APP_DIR, '.env')
    load_dotenv(env_path)
    logger.info('[SyncBridge Server] 加载环境变量: %s', env_path)
except ImportError:
    logger.warning('[SyncBridge Server] dotenv 未安装，环境变量可能未加载')

from datetime import datetime
import time

# 创建 Flask 应用
app = Flask(__name__)

# [C4 修复 2026-06-13] 注册 trace_id 中间件
try:
    from utils.trace import init_trace_middleware
    init_trace_middleware(app)
    logger.info('[TRACE] 8008 同步桥 trace_id 中间件已注册')
except Exception as e:
    logger.warning(f'[TRACE] 8008 注册中间件失败: {e}')

@app.errorhandler(400)
def handle_bad_request(e):
    return {'code': 1200, 'message': f'请求格式错误: {str(e.description)}'}, 400

@app.errorhandler(404)
def handle_not_found(e):
    return {'code': 1404, 'message': '接口不存在'}, 404

@app.errorhandler(500)
def handle_server_error(e):
    import logging, traceback
    logging.getLogger(__name__).exception('sync_bridge_server 内部错误')
    original = getattr(e, 'original_exception', e)
    err_msg = f'{type(original).__name__}: {original}'
    tb = ''.join(traceback.format_exception(type(original), original, original.__traceback__))
    logging.getLogger(__name__).error('sync_bridge_server 详细错误:\n%s', tb)
    return {'code': 1500, 'message': err_msg}, 500

@app.before_request
def log_request():
    if request.method == 'POST' and request.path.startswith('/api/sync/'):
        raw_data = request.get_data()
        logger.info('[IN] %s %s | Content-Type: %s | Data(%d): %s',
                   request.method, request.path,
                   request.content_type or 'none',
                   len(raw_data),
                   raw_data[:500].decode('utf-8', errors='replace') if raw_data else 'empty')

# 注册 sync_bridge 蓝图
app.register_blueprint(sync_bp)

# 健康检查端点
@app.route('/health')
def health():
    try:
        from sync_bridge import _get_mysql_connection
        conn = _get_mysql_connection()
        conn.ping()
        conn.close()
        db_ok = True
    except Exception:
        db_ok = False
    return {
        'status': 'ok' if db_ok else 'degraded',
        'service': 'sync_bridge',
        'db': 'connected' if db_ok else 'disconnected',
        'catchup_heartbeat': getattr(app, '_catchup_heartbeat', 0),
        'catchup_alive': (time.time() - getattr(app, '_catchup_heartbeat', 0)) < 120,
    }

@app.route('/api/health')
def api_health():
    """API健康检查（统一格式）"""
    return jsonify({
        'status': 'ok',
        'service': 'sync-bridge',
        'version': '3.0',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    import threading
    from sync_bridge import _sync_queue_worker, _get_container_conn, _get_mysql_connection, _sync_quality_to_mysql
    import json, time

    def _catchup_sync():
        """补洞守护：游标分页 + 失败不跳 + 死信重放 + 异常自恢复"""
        last_id = 0
        time.sleep(15)
        while True:
            app._catchup_heartbeat = time.time()
            try:
                # === 死信重放 ===
                mysql = _get_mysql_connection()
                cur = mysql.cursor()
                cur.execute(
                    "SELECT * FROM notification_dlq WHERE retry_count < max_retries LIMIT 10")
                dlq_rows = cur.fetchall()
                for dlq in dlq_rows:
                    try:
                        body = json.loads(dlq['payload'])
                        _sync_quality_to_mysql(body)
                        cur.execute("DELETE FROM notification_dlq WHERE id=%s", (dlq['id'],))
                    except Exception as e:
                        cur.execute(
                            "UPDATE notification_dlq SET retry_count=retry_count+1, error_msg=%s WHERE id=%s",
                            (str(e)[:500], dlq['id']))
                mysql.commit()
                mysql.close()

                # === 补洞扫描 ===
                cc = _get_container_conn()
                from pymysql.cursors import DictCursor
                cur = cc.cursor(DictCursor)
                cur.execute(
                    "SELECT * FROM quality_records WHERE id > %s "
                    "AND (review_status='' OR review_status IS NULL) "
                    "ORDER BY id ASC LIMIT 50",
                    (last_id,))
                rows = cur.fetchall()
                cc.close()

                if rows:
                    for r in rows:
                        items = json.loads(r.get('inspection_items', '[]'))
                        data = {
                            'action': 'submit', 'order_no': r.get('order_no', ''),
                            'inspection_type': r.get('inspection_type', ''),
                            'process_name': r.get('process_name', ''),
                            'inspector': r.get('inspector', ''),
                            'items': items, 'overall_result': r.get('result', ''),
                            'defect_description': r.get('defect_description', ''),
                        }
                        try:
                            _sync_quality_to_mysql(data)
                            last_id = max(last_id, r.get('id', 0))
                        except Exception as e:
                            logger.error('[Catchup] 同步失败 id=%s: %s', r.get('id'), e)

                time.sleep(30)

            except SyntaxError as e:
                logger.error('[Catchup] 语法错误: %s (%s, line %s)', e, e.filename, e.lineno)
            except Exception as e:
                import traceback
                logger.error('[Catchup] 异常: %s\n%s', e, traceback.format_exc())
                time.sleep(30)

    threading.Thread(target=_catchup_sync, daemon=True, name='catchup-sync').start()

    _stop_event = threading.Event()
    _worker = threading.Thread(target=_sync_queue_worker, args=(_stop_event,), daemon=True, name='sync-queue-worker')
    _worker.start()
    logger.info('[SyncBridge Server] 同步队列 Worker 已启动')

    port = int(os.getenv('PORT', 8008))
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    logger.info('[SyncBridge Server] 启动服务，端口: %s', port)
    logger.info('[SyncBridge Server] 健康检查: http://%s:%s/health', host, port)
    app.run(host=host, port=port, debug=False, use_reloader=False)
