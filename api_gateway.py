# -*- coding: utf-8 -*-
"""API 网关 — 统一认证/限流/路由，端口 8000"""
import os, logging, time, json
from datetime import datetime
from flask import Flask, request, jsonify
import requests

from logging_setup import setup_daily_logger
setup_daily_logger('api_gateway')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ---- 后端路由表 ----
BACKENDS = {
    'dispatch':  'http://127.0.0.1:5003',
    'container': 'http://127.0.0.1:5002',
    'inventory': 'http://127.0.0.1:5010',
}
API_TOKENS = [t.strip() for t in os.getenv('API_GATEWAY_TOKENS', 'steelbelt-gateway-token').split(',') if t.strip()]

# ---- 限流 ----
_rate_limits = {}
RATE_LIMIT = 100  # req/min

# ---- 中间件 ----
@app.before_request
def auth_and_rate_limit():
    # 跳过健康检查
    if request.path == '/api/health' or request.path == '/metrics':
        return None

    # 认证
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if token and token not in API_TOKENS:
        return jsonify({'code': 401, 'message': 'Unauthorized'}), 401

    # 限流
    ip = request.remote_addr or 'unknown'
    now = time.time()
    records = _rate_limits.setdefault(ip, [])
    records[:] = [t for t in records if now - t < 60]
    if len(records) >= RATE_LIMIT:
        return jsonify({'code': 429, 'message': 'Too Many Requests'}), 429
    records.append(now)

# ---- 路由转发 ----
@app.route('/api/v1/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy(path):
    """根据路径前缀转发到对应后端"""
    backend_key = path.split('/')[0] if '/' in path else path
    backend_url = BACKENDS.get(backend_key)
    if not backend_url:
        return jsonify({'code': 404, 'message': f'未知后端: {backend_key}'}), 404

    target = f"{backend_url}/api/v1/{path}"
    try:
        resp = requests.request(
            method=request.method, url=target,
            headers={k: v for k, v in request.headers if k != 'Host'},
            json=request.get_json(silent=True),
            timeout=10
        )
        return resp.content, resp.status_code, resp.headers.items()
    except Exception as e:
        logger.error(f'[Gateway] 转发失败 {target}: {e}')
        return jsonify({'code': 502, 'message': '后端不可达'}), 502

# ---- 健康检查 ----
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'code': 0, 'service': 'api_gateway', 'time': datetime.now().isoformat()})

# ---- Prometheus metrics ----
@app.route('/metrics', methods=['GET'])
def metrics():
    lines = ['# HELP gateway_requests_total Total requests', '# TYPE gateway_requests_total counter']
    for backend, url in BACKENDS.items():
        lines.append(f'gateway_backend_up{{{backend}="{url}"}} 1')
    return '\n'.join(lines), 200, {'Content-Type': 'text/plain'}

if __name__ == '__main__':
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('GATEWAY_PORT', '8000'))
    logger.info(f'API 网关启动: http://{host}:{port}')
    app.run(host=host, port=port, debug=False)
