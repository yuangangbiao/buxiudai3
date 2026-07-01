# -*- coding: utf-8 -*-
"""
人脸考勤独立服务器 (端口 5009)
- 仅用于本地端人脸签到考勤，不上云端
- 独立部署，不影响 5003(调度中心) / 5002(容器中心) / 5008(报工系统)
"""
import os
import sys
import logging

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.dirname(BASE_DIR))

logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s [%(levelname)s] %(name)s:%(lineno)d %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger('face_server')

os.environ['FACE_ATTENDANCE_ENABLED'] = 'true'

from flask import Flask, redirect, send_from_directory
from core.cors_config import init_cors

app = Flask(__name__)
init_cors(app)

_FACE_STATIC_DIR = os.path.join(BASE_DIR, 'face_checkin_static')

@app.route('/')
def face_root():
    return redirect('/face/')

@app.route('/models/<path:filename>')
def face_models(filename):
    return send_from_directory(os.path.join(_FACE_STATIC_DIR, 'models'), filename)

@app.route('/wasm/<path:filename>')
def face_wasm(filename):
    return send_from_directory(os.path.join(_FACE_STATIC_DIR, 'wasm'), filename)

from face_checkin import bp as face_checkin_bp
app.register_blueprint(face_checkin_bp)

try:
    from face_checkin import _scheduler_loop, _scheduler_stop, _scheduler_thread
    import threading
    if not (_scheduler_thread and _scheduler_thread.is_alive()):
        _scheduler_stop.clear()
        t = threading.Thread(target=_scheduler_loop, daemon=True)
        t.start()
        logger.info("[FaceServer] 人脸签到调度器已启动")
except Exception as e:
    logger.warning(f"[FaceServer] 人脸签到调度器启动失败: {e}")

if __name__ == '__main__':
    port = int(os.getenv('FACE_SERVER_PORT', '5009'))
    logger.info(f"[FaceServer] 人脸考勤服务器启动: http://0.0.0.0:{port}")
    app.run(host=os.getenv('FLASK_HOST', '0.0.0.0'), port=port, threaded=True, debug=False)
