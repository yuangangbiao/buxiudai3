# -*- coding: utf-8 -*-
"""人脸签到系统 - Flask Blueprint 集成模块"""
import json
import time
import socket
import pymysql
import os
import re
import threading
import csv
import calendar as _cal
import hashlib
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from contextlib import contextmanager
from functools import wraps
import requests
from flask import Blueprint, request, jsonify, Response, send_from_directory, redirect
import logging
from core.config import FLASK_PORT as FACE_PORT, DB_PATHS, CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
from core.db import get_direct_connection

# 二维码功能已移除

logger = logging.getLogger(__name__)

bp = Blueprint('face_checkin', __name__, url_prefix='/face')

BASE_DIR = Path(__file__).parent.parent
DB_PATH = Path(DB_PATHS['face_checkin_db'])
CONFIG_PATH = Path(DB_PATHS['face_checkin_config'])
STATIC_DIR = BASE_DIR / 'face_checkin_static'
ADMIN_DIR = BASE_DIR / 'face_checkin' / 'admin'
_config_lock = threading.Lock()

_admin_tokens = {}
_token_lock = threading.Lock()
_TOKEN_EXPIRE_HOURS = 24
_ADMIN_USERNAME = 'admin'  # 当前登录用户名（由 login 设置）

os.makedirs(BASE_DIR / 'data', exist_ok=True)


def _hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def _get_admin_users():
    cfg = load_config()
    users = cfg.get('admin_users', [])
    if not users and cfg.get('admin_password_hash'):
        users = [{'username': 'admin', 'password_hash': cfg['admin_password_hash']}]
        cfg['admin_users'] = users
        save_config(cfg)
    return users


def _save_admin_users(users):
    cfg = load_config()
    cfg['admin_users'] = users
    save_config(cfg)


def _find_admin_user(username):
    users = _get_admin_users()
    for u in users:
        if u['username'] == username:
            return u
    return None


def load_config():
    with _config_lock:
        if CONFIG_PATH.exists():
            try:
                return json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
            except (json.JSONDecodeError, OSError):
                logger.warning('config.json 损坏，使用默认配置')
                return {}
        return {}


def save_config(cfg):
    with _config_lock:
        CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding='utf-8')


def _clean_expired_tokens():
    now = datetime.now()
    with _token_lock:
        expired = [k for k, v in _admin_tokens.items() if v['expires'] < now]
        for k in expired:
            del _admin_tokens[k]


def _generate_token():
    return secrets.token_hex(32)


def _get_current_admin():
    token = request.headers.get('X-Admin-Token', '')
    if not token:
        return None
    _clean_expired_tokens()
    with _token_lock:
        data = _admin_tokens.get(token)
        if data and data['expires'] > datetime.now():
            return data.get('username', 'admin')
        if data:
            del _admin_tokens[token]
        return None


def _verify_admin_token():
    return _get_current_admin() is not None


def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not _verify_admin_token():
            return jsonify({'code': 401, 'message': '未登录或登录已过期，请重新登录'}), 401
        return f(*args, **kwargs)
    return decorated


def get_storage_dir():
    cfg = load_config()
    path = cfg.get('storage_path', 'attendance')
    d = BASE_DIR / path
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_export_dir():
    cfg = load_config()
    path = cfg.get('export_path', 'exports')
    d = BASE_DIR / path
    d.mkdir(parents=True, exist_ok=True)
    return d


def sanitize_filename(name):
    return re.sub(r'[^\w\u4e00-\u9fff-]', '_', name)


@contextmanager
def get_db():
    conn = get_direct_connection(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
    try:
        cursor = conn.cursor()
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def init_db():
    with get_db() as db:
        db.execute('''
            CREATE TABLE IF NOT EXISTS enrollments (
                name VARCHAR(255) PRIMARY KEY,
                descriptor TEXT NOT NULL,
                created_at DOUBLE NOT NULL
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS checkins (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                name TEXT NOT NULL,
                similarity DOUBLE,
                photo_path TEXT,
                created_at DOUBLE NOT NULL
            )
        ''')
        try:
            db.execute('CREATE INDEX idx_checkins_created ON checkins(created_at)')
        except Exception:
            pass
    migrate_db()


def migrate_db():
    with get_db() as db:
        try:
            db.execute('SELECT photo_path FROM checkins LIMIT 1')
        except pymysql.err.OperationalError:
            db.execute('ALTER TABLE checkins ADD COLUMN photo_path TEXT')


init_db()


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.254.254.254', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


@bp.route('/api/ip')
def api_ip():
    return jsonify({'ip': get_local_ip(), 'port': FACE_PORT})


@bp.route('/api/config', methods=['GET', 'PUT'])
def api_config():
    if request.method == 'GET':
        cfg = load_config()
        public = {k: v for k, v in cfg.items() if k != 'admin_password_hash'}
        return jsonify(public)
    if not _verify_admin_token():
        return jsonify({'code': 401, 'message': '未登录或登录已过期，请重新登录'}), 401
    data = request.get_json(silent=True) or {}
    current = load_config()
    allowed_keys = {'storage_path', 'export_path', 'export_schedule_day', 'export_schedule_time',
                    'cloud_url', 'cloud_attendance_enabled'}
    for k, v in data.items():
        if k in allowed_keys and v is not None:
            current[k] = v
    save_config(current)
    return jsonify({'success': True})


@bp.route('/api/admin/login', methods=['POST'])
def api_admin_login():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    if not username:
        username = 'admin'
    if not password:
        return jsonify({'code': 400, 'message': '密码不能为空'}), 400
    users = _get_admin_users()
    if not users:
        users.append({'username': username, 'password_hash': _hash_password(password)})
        _save_admin_users(users)
        logger.info('[admin] 管理员账号 "%s" 首次设置完成', username)
    else:
        user = _find_admin_user(username)
        if not user:
            return jsonify({'code': 401, 'message': '用户名或密码错误'}), 401
        if _hash_password(password) != user['password_hash']:
            return jsonify({'code': 401, 'message': '用户名或密码错误'}), 401
    token = _generate_token()
    with _token_lock:
        _admin_tokens[token] = {'username': username, 'expires': datetime.now() + timedelta(hours=_TOKEN_EXPIRE_HOURS)}
    return jsonify({'success': True, 'token': token, 'username': username})


@bp.route('/api/admin/check', methods=['GET'])
def api_admin_check():
    valid = _verify_admin_token()
    has_admin = bool(_get_admin_users())
    return jsonify({'valid': valid, 'hasAdmin': has_admin})


@bp.route('/api/admin/password', methods=['PUT'])
@require_admin
def api_admin_change_password():
    data = request.get_json(silent=True) or {}
    old = (data.get('oldPassword') or '').strip()
    new = (data.get('newPassword') or '').strip()
    username = _get_current_admin()
    if not username:
        return jsonify({'code': 401, 'message': '未登录'}), 401
    if not old or not new:
        return jsonify({'code': 400, 'message': '旧密码和新密码不能为空'}), 400
    if len(new) < 4:
        return jsonify({'code': 400, 'message': '新密码长度至少4位'}), 400
    user = _find_admin_user(username)
    if not user:
        return jsonify({'code': 400, 'message': '账号不存在'}), 400
    if user['password_hash'] and _hash_password(old) != user['password_hash']:
        return jsonify({'code': 401, 'message': '旧密码错误'}), 401
    users = _get_admin_users()
    for u in users:
        if u['username'] == username:
            u['password_hash'] = _hash_password(new)
            break
    _save_admin_users(users)
    return jsonify({'success': True, 'message': '密码已更新'})


@bp.route('/api/admin/users', methods=['GET'])
@require_admin
def api_admin_list_users():
    users = _get_admin_users()
    safe = [{'username': u['username']} for u in users]
    current = _get_current_admin()
    return jsonify({'users': safe, 'current': current})


@bp.route('/api/admin/users', methods=['POST'])
@require_admin
def api_admin_create_user():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    if not username or not password:
        return jsonify({'code': 400, 'message': '用户名和密码不能为空'}), 400
    if not re.match(r'^[a-zA-Z0-9_\u4e00-\u9fa5]{2,32}$', username):
        return jsonify({'code': 400, 'message': '用户名仅支持字母数字中文下划线，2-32位'}), 400
    if len(password) < 4:
        return jsonify({'code': 400, 'message': '密码长度至少4位'}), 400
    users = _get_admin_users()
    if _find_admin_user(username):
        return jsonify({'code': 400, 'message': '用户名已存在'}), 400
    users.append({'username': username, 'password_hash': _hash_password(password)})
    _save_admin_users(users)
    logger.info('[admin] 新增管理员账号 "%s"', username)
    return jsonify({'success': True, 'message': '管理员账号已创建'})


@bp.route('/api/admin/users', methods=['DELETE'])
@require_admin
def api_admin_delete_user():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    current = _get_current_admin()
    if not username:
        return jsonify({'code': 400, 'message': '用户名不能为空'}), 400
    if username == current:
        return jsonify({'code': 400, 'message': '不能删除自己'}), 400
    users = _get_admin_users()
    found = False
    for u in users[:]:
        if u['username'] == username:
            users.remove(u)
            found = True
            break
    if not found:
        return jsonify({'code': 400, 'message': '用户不存在'}), 400
    _save_admin_users(users)
    logger.info('[admin] 删除管理员账号 "%s"', username)
    return jsonify({'success': True, 'message': '管理员已删除'})


@bp.route('/api/drives')
@require_admin
def api_drives():
    drives = []
    for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        path = letter + ':\\'
        if os.path.isdir(path):
            drives.append({'name': letter, 'path': path})
    return jsonify(drives)


@bp.route('/api/list-dirs', methods=['POST'])
@require_admin
def api_list_dirs():
    data = request.get_json(silent=True) or {}
    parent = data.get('path', '')
    if not parent:
        return jsonify({'path': parent, 'dirs': []})
    try:
        entries = sorted([
            {'name': e.name, 'path': str(e.path)}
            for e in os.scandir(parent)
            if e.is_dir() and not e.name.startswith('.')
        ], key=lambda x: x['name'].lower())
        return jsonify({'path': parent, 'dirs': entries})
    except PermissionError:
        return jsonify({'path': parent, 'dirs': [], 'error': '无权限访问'})
    except Exception as e:
        return jsonify({'path': parent, 'dirs': [], 'error': str(e)})


@bp.route('/api/create-dir', methods=['POST'])
@require_admin
def api_create_dir():
    data = request.get_json(silent=True) or {}
    parent = data.get('parent', '').strip()
    name = data.get('name', '').strip()
    if not parent or not name:
        return jsonify({'code': 400, 'message': 'parent 和 name 不能为空'}), 400
    safe = re.sub(r'[<>:"/\\|?*]', '_', name)
    if not safe:
        return jsonify({'code': 400, 'message': '目录名不合法'}), 400
    new_dir = Path(parent) / safe
    try:
        new_dir.mkdir(parents=True, exist_ok=False)
        return jsonify({'success': True, 'path': str(new_dir), 'name': safe})
    except FileExistsError:
        return jsonify({'code': 409, 'message': f'目录已存在: {safe}'}), 409
    except PermissionError:
        return jsonify({'code': 403, 'message': '无权限创建目录'}), 403
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)}), 500


@bp.route('/api/upload-photo', methods=['POST'])
def api_upload_photo():
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    photo_b64 = data.get('photo', '')
    if not name or not photo_b64:
        return jsonify({'code': 400, 'message': 'name 和 photo 不能为空'}), 400
    safe_name = sanitize_filename(name)
    ts = int(time.time() * 1000)
    filename = f'{safe_name}_{ts}.jpg'
    storage_dir = get_storage_dir()
    person_dir = storage_dir / safe_name
    person_dir.mkdir(parents=True, exist_ok=True)
    if ',' in photo_b64:
        photo_b64 = photo_b64.split(',', 1)[1]
    try:
        import base64
        img_data = base64.b64decode(photo_b64)
    except Exception:
        return jsonify({'code': 400, 'message': 'photo base64 解码失败'}), 400
    file_path = person_dir / filename
    file_path.write_bytes(img_data)
    cfg = load_config()
    return jsonify({'path': f'{cfg.get("storage_path", "attendance")}/{safe_name}/{filename}'})


@bp.route('/api/enroll', methods=['POST'])
def api_enroll():
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    descriptor = data.get('descriptor')
    if not name:
        return jsonify({'code': 400, 'message': '姓名不能为空'}), 400
    with get_db() as db:
        db.execute(
            'REPLACE INTO enrollments (name, descriptor, created_at) VALUES (%s, %s, %s)',
            (name, json.dumps(descriptor), time.time())
        )
    return jsonify({'success': True})


@bp.route('/api/enrollments', methods=['GET', 'DELETE'])
def api_enrollments():
    if request.method == 'DELETE':
        if not _verify_admin_token():
            return jsonify({'code': 401, 'message': '未登录或登录已过期，请重新登录'}), 401
        name = request.args.get('name', '')
        if not name:
            return jsonify({'code': 400, 'message': 'name 参数不能为空'}), 400
        with get_db() as db:
            db.execute('DELETE FROM enrollments WHERE name = %s', (name,))
        return jsonify({'success': True})
    with get_db() as db:
        rows = db.execute('SELECT name, descriptor, created_at FROM enrollments ORDER BY created_at').fetchall()
    return jsonify([
        {'name': r['name'], 'descriptor': json.loads(r['descriptor']), 'createdAt': r['created_at']}
        for r in rows
    ])


@bp.route('/api/enrollments/<name>', methods=['DELETE'])
@require_admin
def api_delete_enrollment(name):
    with get_db() as db:
        db.execute('DELETE FROM enrollments WHERE name = %s', (name,))
    return jsonify({'success': True})


@bp.route('/api/enrollments/photo')
def api_enrollment_photo():
    name = request.args.get('name', '').strip()
    if not name:
        return jsonify({'photoUrl': None})
    safe_name = sanitize_filename(name)
    storage_dir = get_storage_dir()
    person_dir = storage_dir / safe_name
    if not person_dir.is_dir():
        return jsonify({'photoUrl': None})
    files = sorted(person_dir.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
    for f in files:
        if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp'):
            return jsonify({'photoUrl': f'/face/api/photos/{safe_name}/{f.name}'})
    return jsonify({'photoUrl': None})


def _send_to_cloud(name, similarity, checkin_time):
    """发送考勤记录到云端5006服务（企业微信应用渠道）"""
    cfg = load_config()
    cloud_url = cfg.get('cloud_url', '').strip()
    if not cloud_url:
        logger.warning('[云端推送] 未配置cloud_url，跳过云端推送')
        return
    enabled = cfg.get('cloud_attendance_enabled', False)
    if not enabled:
        logger.info('[云端推送] 云端考勤推送未启用，跳过')
        return
    sim_text = f'{float(similarity)*100:.1f}%' if similarity else 'N/A'
    now_str = datetime.fromtimestamp(checkin_time).strftime('%Y-%m-%d %H:%M:%S')
    content = (
        f'\u2705 \u4eba\u8138\u8003\u52e4\u6210\u529f\u901a\u77e5\n'
        f'\u59d3\u540d: {name}\n'
        f'\u65f6\u95f4: {now_str}\n'
        f'\u5339\u914d\u5ea6: {sim_text}'
    )
    try:
        resp = requests.post(
            f'{cloud_url}/api/send',
            json={
                'bot_type': 'app',
                'content': content,
                'msg_type': 'attendance_checkin',
                'source': 'face_checkin',
                'metadata': {
                    'name': name,
                    'similarity': round(float(similarity), 4) if similarity else 0,
                    'checkin_time': now_str
                }
            },
            timeout=10
        )
        if resp.status_code == 200:
            ret = resp.json()
            logger.info(f'[云端推送] 已发送 {name} 考勤到云端: {ret}')
        else:
            logger.warning(f'[云端推送] 云端返回HTTP {resp.status_code}')
    except Exception as e:
        logger.warning(f'[云端推送] 请求失败: {e}')


def _notify_checkin_success(name, similarity, photo_path=''):
    try:
        now_ts = time.time()
        now_str = datetime.fromtimestamp(now_ts).strftime('%Y-%m-%d %H:%M:%S')
        dispatch_url = os.environ.get('DISPATCH_CENTER_URL', 'http://127.0.0.1:5003')

        operator_id = None
        try:
            resp = requests.get(
                f'{dispatch_url}/api/dispatch-center/operators',
                timeout=5,
            )
            if resp.status_code == 200:
                ret = resp.json()
                if ret.get('code') == 0:
                    for op in ret.get('data', []):
                        if op.get('name', '').strip() == name.strip():
                            operator_id = op.get('id')
                            break
            if operator_id:
                logger.info(f'[考勤通知] 从调度中心匹配到 {name} -> {operator_id}')
            else:
                logger.warning(f'[考勤通知] 调度中心未找到操作员 {name}')
                return
        except Exception as e:
            logger.warning(f'[考勤通知] 从调度中心获取操作员列表失败: {e}')
            return
        center_url = os.environ.get('CONTAINER_CENTER_URL', 'http://localhost:5002')
        try:
            requests.post(
                f'{center_url}/api/processes',
                json={
                    'order_no': f'ATTEND_{int(now_ts)}',
                    'process_type': 'attendance',
                    'product_name': f'{name} 人脸考勤',
                    'quantity': 1,
                    'status': 'completed',
                    'source': 'face_checkin',
                    'current_step': 1,
                    'steps': [{'name': '人脸识别考勤', 'status': 'completed', 'completed_at': now_str}],
                    'metadata': {
                        'name': name,
                        'similarity': round(float(similarity), 4) if similarity else 0,
                        'photo_path': photo_path or '',
                        'checkin_time': now_str
                    }
                },
                headers={'X-API-Key': os.environ.get('CONTAINER_CENTER_API_KEY', '')},
                timeout=5
            )
            logger.info(f'[考勤通知] 已推送考勤记录到容器中心')
        except Exception as e:
            logger.warning(f'[考勤通知] 推送到容器中心失败: {e}')

        sim_text = f'{float(similarity)*100:.1f}%' if similarity else 'N/A'
        content = (
            f'\u2705 \u4eba\u8138\u8003\u52e4\u6210\u529f\u901a\u77e5\n'
            f'\u59d3\u540d: {name}\n'
            f'\u65f6\u95f4: {now_str}\n'
            f'\u5339\u914d\u5ea6: {sim_text}'
        )
        try:
            resp = requests.post(
                f'{dispatch_url}/api/dispatch-center/messages/send',
                json={
                    'content': content,
                    'channels': ['wechat_app'],
                    'operator_id': operator_id,
                },
                timeout=10,
            )
            if resp.status_code == 200:
                ret = resp.json()
                if ret.get('code') == 0:
                    logger.info(f'[考勤通知] 已通过调度中心推送给 {name}({operator_id})')
                else:
                    logger.warning(f'[考勤通知] 调度中心返回错误: {ret}')
            else:
                logger.warning(f'[考勤通知] 调度中心HTTP {resp.status_code}')
        except Exception as e:
            logger.warning(f'[考勤通知] 调度中心请求失败: {e}')

        _send_to_cloud(name, similarity, now_ts)

    except Exception as e:
        logger.error(f'[考勤通知] 推送失败: {e}')


def _add_watermark(photo_rel_path, name, timestamp):
    """在照片底部叠加姓名和签到时间水印"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        logger.warning('[水印] Pillow 未安装，跳过水印')
        return
    storage_dir = get_storage_dir()
    rel_parts = photo_rel_path.replace('\\', '/').split('/')
    rel = '/'.join(rel_parts[1:])
    file_path = storage_dir / rel
    if not file_path.exists() or not file_path.is_file():
        logger.warning(f'[水印] 照片不存在: {file_path}')
        return
    img = Image.open(file_path).convert('RGB')
    width, height = img.size
    time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
    text = f'{name}  {time_str}'
    font_size = max(12, width // 28)
    try:
        font = ImageFont.truetype('C:/Windows/Fonts/simhei.ttf', font_size)
    except Exception:
        font = ImageFont.load_default()
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    bbox = overlay_draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    padding = 10
    bar_height = text_h + padding * 2
    overlay_draw.rectangle([(0, height - bar_height), (width, height)], fill=(0, 0, 0, 160))
    text_x = (width - text_w) // 2
    text_y = height - bar_height + padding
    overlay_draw.text((text_x, text_y), text, fill=(255, 255, 255, 255), font=font)
    img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
    img.save(file_path, quality=92)
    logger.info(f'[水印] 已添加水印: {file_path.name}')


@bp.route('/api/checkin', methods=['POST'])
def api_checkin():
    if os.getenv('FACE_ATTENDANCE_ENABLED', 'true').lower() not in ('true', '1', 'yes'):
        return jsonify({'code': 403, 'message': '人脸考勤功能仅在本地端可用，当前为云端模式'}), 403

    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    similarity = data.get('similarity')
    photo_path = data.get('photo_path')
    if not name:
        return jsonify({'code': 400, 'message': 'name 不能为空'}), 400

    now = time.time()
    with get_db() as db:
        row = db.execute(
            'SELECT created_at FROM checkins WHERE name = %s ORDER BY created_at DESC LIMIT 1',
            (name,)
        ).fetchone()
        if row and (now - row['created_at']) < 3600:
            return jsonify({'code': 429, 'message': f'{name} 已在1小时内签到，请稍后再试'}), 429

        db.execute(
            'INSERT INTO checkins (name, similarity, photo_path, created_at) VALUES (%s, %s, %s, %s)',
            (name, similarity, photo_path, now)
        )
    if photo_path:
        try:
            _add_watermark(photo_path, name, now)
        except Exception as e:
            logger.warning(f'[水印] 添加水印失败: {e}')
    _notify_checkin_success(name, similarity, photo_path)
    return jsonify({'success': True})


@bp.route('/api/checkins', methods=['GET'])
def api_checkins():
    date = request.args.get('date')
    limit = request.args.get('limit', 100, type=int)
    with get_db() as db:
        if date:
            start = _date_ts(date)
            end = start + 86400
            rows = db.execute(
                'SELECT name, similarity, photo_path, created_at FROM checkins WHERE created_at >= %s AND created_at < %s ORDER BY created_at DESC LIMIT %s',
                (start, end, limit)
            ).fetchall()
        else:
            rows = db.execute(
                'SELECT name, similarity, photo_path, created_at FROM checkins ORDER BY created_at DESC LIMIT %s',
                (limit,)
            ).fetchall()
    return jsonify([
        {
            'name': r['name'],
            'similarity': r['similarity'],
            'photoPath': r['photo_path'],
            'time': r['created_at'],
            'dateStr': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(r['created_at']))
        }
        for r in rows
    ])


@bp.route('/api/photos/<path:filename>')
def api_photo(filename):
    storage_dir = get_storage_dir()
    file_path = (storage_dir / filename).resolve()
    if not str(file_path).startswith(str(storage_dir.resolve())):
        return jsonify({'code': 403, 'message': '禁止访问'}), 403
    if not file_path.exists() or not file_path.is_file():
        return jsonify({'code': 404, 'message': '照片不存在'}), 404
    return Response(file_path.read_bytes(), mimetype='image/jpeg')


def _date_ts(date_str):
    return time.mktime(time.strptime(date_str, '%Y-%m-%d'))


_scheduler_thread = None
_scheduler_stop = threading.Event()
_scheduler_lock = threading.Lock()
_scheduler_last_export = None
_scheduler_last_export_date = ''
_scheduler_last_error = None


@bp.route('/api/export-checkins', methods=['POST'])
def api_export_checkins():
    if not _verify_admin_token():
        return jsonify({'code': 401, 'message': '未登录或登录已过期，请重新登录'}), 401
    result = _do_export_checkins()
    return jsonify(result)


def _do_export_checkins():
    export_dir = get_export_dir()
    ts = time.strftime('%Y%m%d_%H%M%S')
    filename = f'签到记录_{ts}.csv'
    filepath = export_dir / filename
    with get_db() as db:
        rows = db.execute(
            'SELECT name, similarity, created_at FROM checkins ORDER BY created_at'
        ).fetchall()
    bom = '\ufeff'
    with open(str(filepath), 'w', encoding='utf-8-sig', newline='') as f:
        f.write(bom)
        writer = csv.writer(f)
        writer.writerow(['姓名', '相似度', '签到时间'])
        for r in rows:
            sim = f'{r["similarity"] * 100:.1f}%' if r['similarity'] else '--'
            dt = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(r['created_at']))
            writer.writerow([r['name'], sim, dt])
    global _scheduler_last_export, _scheduler_last_error
    with _scheduler_lock:
        _scheduler_last_export = time.time()
        _scheduler_last_error = None
    return {
        'success': True,
        'file': filename,
        'path': str(filepath),
        'count': len(rows),
        'time': _scheduler_last_export
    }


def _do_scheduled_export():
    try:
        return _do_export_checkins()
    except Exception as e:
        global _scheduler_last_error
        with _scheduler_lock:
            _scheduler_last_error = str(e)
        return None


def _schedule_today_match(cfg):
    day = int(cfg.get('export_schedule_day', 1))
    now = time.localtime()
    max_day = _cal.monthrange(now.tm_year, now.tm_mon)[1]
    target = min(day, max_day)
    return now.tm_mday == target


def _schedule_time_passed(cfg):
    t = cfg.get('export_schedule_time', '09:00')
    parts = t.split(':')
    h, m = int(parts[0]), int(parts[1])
    now = time.localtime()
    return now.tm_hour > h or (now.tm_hour == h and now.tm_min >= m)


def _calc_next_export(cfg):
    now = time.localtime()
    day = int(cfg.get('export_schedule_day', 1))
    t = cfg.get('export_schedule_time', '09:00')
    parts = t.split(':')
    h, m = int(parts[0]), int(parts[1])
    max_day = _cal.monthrange(now.tm_year, now.tm_mon)[1]
    target_day = min(day, max_day)
    cand = time.mktime((now.tm_year, now.tm_mon, target_day, h, m, 0, 0, 0, -1))
    if cand > time.time():
        return cand
    if now.tm_mon == 12:
        ny, nm = now.tm_year + 1, 1
    else:
        ny, nm = now.tm_year, now.tm_mon + 1
    max_day = _cal.monthrange(ny, nm)[1]
    target_day = min(day, max_day)
    return time.mktime((ny, nm, target_day, h, m, 0, 0, 0, -1))


def _scheduler_loop():
    while not _scheduler_stop.is_set():
        _scheduler_stop.wait(60)
        if _scheduler_stop.is_set():
            break
        try:
            cfg = load_config()
            today = time.strftime('%Y-%m-%d')
            global _scheduler_last_export_date
            should_export = False
            with _scheduler_lock:
                if _schedule_today_match(cfg) and _schedule_time_passed(cfg) and _scheduler_last_export_date != today:
                    should_export = True
            if should_export:
                _do_scheduled_export()
                with _scheduler_lock:
                    _scheduler_last_export_date = today
        except Exception as e:
            logger.warning('调度器异常: %s', e)


@bp.route('/api/scheduler', methods=['GET', 'POST'])
def api_scheduler():
    global _scheduler_thread, _scheduler_stop
    if request.method == 'POST' and not _verify_admin_token():
        return jsonify({'code': 401, 'message': '未登录或登录已过期，请重新登录'}), 401
    if request.method == 'GET':
        running = _scheduler_thread is not None and _scheduler_thread.is_alive()
        cfg = load_config()
        next_export = _calc_next_export(cfg) if running else None
        with _scheduler_lock:
            last_export = _scheduler_last_export
            last_error = _scheduler_last_error
        return jsonify({
            'running': running,
            'lastExport': last_export,
            'nextExport': next_export,
            'nextExportDate': time.strftime('%Y-%m-%d %H:%M', time.localtime(next_export)) if next_export else None,
            'lastError': last_error
        })
    data = request.get_json(silent=True) or {}
    action = data.get('action', '') or request.args.get('action', '')
    if action == 'start':
        if _scheduler_thread and _scheduler_thread.is_alive():
            return jsonify({'success': True, 'running': True, 'message': '调度器已在运行'})
        _scheduler_stop.clear()
        _scheduler_thread = threading.Thread(target=_scheduler_loop, daemon=True)
        _scheduler_thread.start()
        return jsonify({'success': True, 'running': True})
    elif action == 'stop':
        _scheduler_stop.set()
        return jsonify({'success': True, 'running': False})
    elif action == 'export':
        return api_export_checkins()
    return jsonify({'success': False, 'message': f'未知操作: {action}'})


@bp.route('/api/send-attendance-to-cloud', methods=['POST'])
@require_admin
def api_send_attendance_to_cloud():
    """手动向云端5006发送考勤记录（管理后台触发）"""
    data = request.get_json(silent=True) or {}
    limit = int(data.get('limit', 50))
    with get_db() as db:
        rows = db.execute(
            'SELECT name, similarity, photo_path, created_at FROM checkins ORDER BY created_at DESC LIMIT %s',
            (limit,)
        ).fetchall()
    if not rows:
        return jsonify({'success': True, 'count': 0, 'message': '无考勤记录可发送'})
    cfg = load_config()
    cloud_url = cfg.get('cloud_url', '').strip()
    if not cloud_url:
        return jsonify({'success': False, 'message': '未配置云端地址(cloud_url)，请在设置中填写'})
    success_count = 0
    fail_count = 0
    for r in rows:
        try:
            name = r['name']
            similarity = r['similarity']
            checkin_time = r['created_at']
            now_str = datetime.fromtimestamp(checkin_time).strftime('%Y-%m-%d %H:%M:%S')
            sim_text = f'{float(similarity)*100:.1f}%' if similarity else 'N/A'
            content = (
                f'\u2705 \u4eba\u8138\u8003\u52e4\u6210\u529f\u901a\u77e5\n'
                f'\u59d3\u540d: {name}\n'
                f'\u65f6\u95f4: {now_str}\n'
                f'\u5339\u914d\u5ea6: {sim_text}'
            )
            resp = requests.post(
                f'{cloud_url}/api/send',
                json={
                    'bot_type': 'app',
                    'content': content,
                    'msg_type': 'attendance_checkin',
                    'source': 'face_checkin',
                    'metadata': {
                        'name': name,
                        'similarity': round(float(similarity), 4) if similarity else 0,
                        'checkin_time': now_str
                    }
                },
                timeout=10
            )
            if resp.status_code == 200:
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            logger.warning(f'[手动推送] 发送 {r["name"]} 到云端失败: {e}')
            fail_count += 1
    return jsonify({
        'success': True,
        'count': success_count,
        'fail': fail_count,
        'total': len(rows),
        'message': f'成功发送 {success_count} 条，失败 {fail_count} 条'
    })


@bp.route('/')
def index():
    return redirect('/face/app/')


@bp.route('/admin/')
def admin():
    return send_from_directory(ADMIN_DIR, 'index.html')

@bp.route('/admin/<path:filename>')
def admin_static(filename):
    return send_from_directory(ADMIN_DIR, filename)


def _serve_spa(path='index.html'):
    spa_file = STATIC_DIR / 'index.html'
    if not spa_file.exists():
        return jsonify({'code': 404, 'message': '前端页面未部署'}), 404
    return Response(spa_file.read_bytes(), mimetype='text/html')


@bp.route('/app/')
def app_index():
    return _serve_spa()


@bp.route('/app/<path:rest>')
def app_spa(rest):
    return _serve_spa()


@bp.route('/assets/<path:filename>')
def static_assets(filename):
    return send_from_directory(STATIC_DIR / 'assets', filename)


@bp.route('/models/<path:filename>')
def static_models(filename):
    return send_from_directory(STATIC_DIR / 'models', filename)


@bp.route('/wasm/<path:filename>')
def static_wasm(filename):
    return send_from_directory(STATIC_DIR / 'wasm', filename)
