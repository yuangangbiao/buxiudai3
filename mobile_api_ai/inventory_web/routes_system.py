# -*- coding: utf-8 -*-
"""库存管理 — 系统路由：备份/恢复/路径/日志清理

TASK-003 实施：
- 路径越权修复（realpath + 双重保护）
- 中文文件名支持（不用 secure_filename）
- 命令注入修复（subprocess shell=False + 列表参数）
- 备份目录自动创建（依赖 db_utils.BACKUP_DIR）

TASK-018 实施：
- save_settings admin_required + 拒绝写 password 字段
- 跨平台文件权限（依赖 db_utils._secure_file）
"""
import os
import re
import sys
import subprocess
import logging
from datetime import datetime
from flask import request, jsonify, redirect, url_for, render_template, session

from .db_utils import (
    execute, get_conn, PROJECT_ROOT, BACKUP_DIR, CONFIG_PATH,
    load_config, save_config, _secure_file
)
from .admin_auth import admin_required, require_csrf  # CRITICAL Fix A3

logger = logging.getLogger(__name__)

# 备份文件名白名单（仅允许中英文、数字、下划线、横线、点）
BACKUP_FILENAME_PATTERN = re.compile(r'^[\u4e00-\u9fa5A-Za-z0-9_\-\.]+$')


def register_routes_system(bp):
    """注册系统管理路由"""

    # ============================================================
    # TASK-003: 备份列表
    # ============================================================
    @bp.route('/inventory/backup', methods=['GET'])
    @admin_required
    def backup_list():
        """列出所有备份文件"""
        try:
            if not os.path.isdir(BACKUP_DIR):
                return render_template('inventory/backup.html', files=[], error='备份目录不存在')

            files = []
            for fname in sorted(os.listdir(BACKUP_DIR), reverse=True):
                fpath = os.path.join(BACKUP_DIR, fname)
                if os.path.isfile(fpath):
                    files.append({
                        'name': fname,
                        'size': os.path.getsize(fpath),
                        'mtime': datetime.fromtimestamp(os.path.getmtime(fpath)).isoformat()
                    })
            return render_template('inventory/backup.html', files=files, error=None)
        except Exception:
            logger.exception('[备份列表] 失败')
            return render_template('inventory/backup.html', files=[], error='读取备份失败')

    # ============================================================
    # TASK-003: 创建备份（修复命令注入）
    # ============================================================
    @bp.route('/inventory/api/backup/create', methods=['POST'])
    @admin_required
    @require_csrf  # CRITICAL Fix A3
    def backup_create():
        """创建新备份（mysqldump）"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'backup_{timestamp}.sql'
            fpath = os.path.join(BACKUP_DIR, filename)

            # 路径校验：必须落在 BACKUP_DIR 内
            real_path = os.path.realpath(fpath)
            real_backup = os.path.realpath(BACKUP_DIR)
            if not real_path.startswith(real_backup + os.sep):
                return jsonify({'ok': False, 'msg': '备份路径越界'}), 400

            # 命令注入修复：列表参数 + shell=False
            user = os.getenv('MYSQL_USER')
            password = os.getenv('MYSQL_PASSWORD', '')
            db_name = os.getenv('INVENTORY_DB_NAME')

            cmd = [
                'mysqldump',
                '-h', os.getenv('MYSQL_HOST', 'localhost'),
                '-P', os.getenv('MYSQL_PORT', '3306'),
                '-u', user,
                f'-p{password}',
                '--single-transaction',
                '--routines',
                db_name
            ]

            with open(real_path, 'w', encoding='utf-8') as f:
                result = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    shell=False,  # 关键：禁用 shell 解析
                    timeout=300
                )
                if result.returncode != 0:
                    err_msg = result.stderr.decode('utf-8', errors='replace')
                    # 脱敏：删除密码信息
                    err_msg = re.sub(r'-p\S+', '-p***', err_msg)
                    logger.error(f'[备份] mysqldump 失败: {err_msg}')
                    return jsonify({'ok': False, 'msg': '备份失败'}), 500

            # 加固文件权限
            _secure_file(real_path)
            logger.info(f'[备份] 成功: {filename}')
            return jsonify({'ok': True, 'filename': filename})
        except subprocess.TimeoutExpired:
            return jsonify({'ok': False, 'msg': '备份超时（5分钟）'}), 500
        except Exception:
            logger.exception('[备份] 异常')
            return jsonify({'ok': False, 'msg': '备份异常'}), 500

    # ============================================================
    # TASK-003: 下载备份
    # ============================================================
    @bp.route('/inventory/api/backup/download/<filename>', methods=['GET'])
    @admin_required
    def backup_download(filename):
        """下载备份文件（中文名支持 + 路径越权防护）"""
        try:
            # 文件名白名单校验
            if not BACKUP_FILENAME_PATTERN.match(filename):
                return jsonify({'ok': False, 'msg': '非法文件名'}), 400

            # 路径越权防护（不用 secure_filename，因为会破坏中文）
            if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
                return jsonify({'ok': False, 'msg': '非法文件名'}), 400

            fpath = os.path.join(BACKUP_DIR, filename)
            real_path = os.path.realpath(fpath)
            real_backup = os.path.realpath(BACKUP_DIR)
            if not real_path.startswith(real_backup + os.sep):
                return jsonify({'ok': False, 'msg': '文件路径越界'}), 400

            if not os.path.isfile(real_path):
                return jsonify({'ok': False, 'msg': '文件不存在'}), 404

            from flask import send_file
            # 中文文件名需要 URL 编码
            from urllib.parse import quote
            return send_file(
                real_path,
                as_attachment=True,
                download_name=quote(filename)
            )
        except Exception:
            logger.exception('[备份下载] 异常')
            return jsonify({'ok': False, 'msg': '下载失败'}), 500

    # ============================================================
    # TASK-003: 删除备份
    # ============================================================
    @bp.route('/inventory/api/backup/delete', methods=['POST'])
    @admin_required
    @require_csrf  # CRITICAL Fix A3
    def backup_delete():
        """删除备份文件"""
        data = request.get_json() or {}
        filename = data.get('filename', '')

        if not BACKUP_FILENAME_PATTERN.match(filename):
            return jsonify({'ok': False, 'msg': '非法文件名'}), 400
        if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
            return jsonify({'ok': False, 'msg': '非法文件名'}), 400

        fpath = os.path.join(BACKUP_DIR, filename)
        real_path = os.path.realpath(fpath)
        real_backup = os.path.realpath(BACKUP_DIR)
        if not real_path.startswith(real_backup + os.sep):
            return jsonify({'ok': False, 'msg': '文件路径越界'}), 400

        try:
            if os.path.isfile(real_path):
                os.remove(real_path)
                logger.info(f'[备份删除] {filename}')
                return jsonify({'ok': True})
            return jsonify({'ok': False, 'msg': '文件不存在'}), 404
        except OSError:
            logger.exception('[备份删除] 失败')
            return jsonify({'ok': False, 'msg': '删除失败'}), 500

    # ============================================================
    # TASK-003: 恢复备份
    # ============================================================
    @bp.route('/inventory/api/backup/restore', methods=['POST'])
    @admin_required
    @require_csrf  # CRITICAL Fix A3
    def backup_restore():
        """恢复备份（mysql 命令）"""
        data = request.get_json() or {}
        filename = data.get('filename', '')

        if not BACKUP_FILENAME_PATTERN.match(filename):
            return jsonify({'ok': False, 'msg': '非法文件名'}), 400
        if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
            return jsonify({'ok': False, 'msg': '非法文件名'}), 400

        fpath = os.path.join(BACKUP_DIR, filename)
        real_path = os.path.realpath(fpath)
        real_backup = os.path.realpath(BACKUP_DIR)
        if not real_path.startswith(real_backup + os.sep):
            return jsonify({'ok': False, 'msg': '文件路径越界'}), 400
        if not os.path.isfile(real_path):
            return jsonify({'ok': False, 'msg': '文件不存在'}), 404

        try:
            user = os.getenv('MYSQL_USER')
            password = os.getenv('MYSQL_PASSWORD', '')
            db_name = os.getenv('INVENTORY_DB_NAME')

            cmd = [
                'mysql',
                '-h', os.getenv('MYSQL_HOST', 'localhost'),
                '-P', os.getenv('MYSQL_PORT', '3306'),
                '-u', user,
                f'-p{password}',
                db_name
            ]

            with open(real_path, 'r', encoding='utf-8') as f:
                result = subprocess.run(
                    cmd,
                    stdin=f,
                    stderr=subprocess.PIPE,
                    shell=False,
                    timeout=300
                )
                if result.returncode != 0:
                    err_msg = result.stderr.decode('utf-8', errors='replace')
                    err_msg = re.sub(r'-p\S+', '-p***', err_msg)
                    logger.error(f'[恢复] mysql 失败: {err_msg}')
                    return jsonify({'ok': False, 'msg': '恢复失败'}), 500

            logger.warning(f'[恢复] 成功: {filename}, operator=admin')
            return jsonify({'ok': True, 'msg': '恢复成功'})
        except Exception:
            logger.exception('[恢复] 异常')
            return jsonify({'ok': False, 'msg': '恢复异常'}), 500

    # ============================================================
    # TASK-011 + TASK-018: 系统设置保存（admin_required + 拒绝写 password）
    # ============================================================
    @bp.route('/inventory/api/settings', methods=['GET'])
    @admin_required
    def get_settings():
        """获取系统设置（不返回 password 字段）"""
        cfg = load_config()
        # 脱敏：剥离 password
        db_cfg = cfg.get('database', {})
        return jsonify({
            'ok': True,
            'database': {
                'host': db_cfg.get('host', 'localhost'),
                'port': db_cfg.get('port', 3306),
                'user': db_cfg.get('user', ''),
                'database': db_cfg.get('database', '')
                # CRITICAL Fix M3: 删除 password_set 字段（攻击者可通过该字段
                # 间接探测密码是否设置，再结合其他信息可能推导出密码长度等）
            }
        })

    @bp.route('/inventory/api/settings', methods=['POST'])
    @admin_required
    @require_csrf  # CRITICAL Fix A3
    def save_settings():
        """保存系统设置（拒绝写 password 字段）"""
        data = request.get_json() or {}

        # TASK-018: 拒绝写 password 字段（必须用环境变量）
        if 'password' in data or 'database' in data and isinstance(data.get('database'), dict) and 'password' in data['database']:
            return jsonify({
                'ok': False,
                'msg': '请使用环境变量 INVENTORY_DB_NAME / MYSQL_USER / MYSQL_PASSWORD 配置数据库凭证，不要通过 API 写入'
            }), 400

        cfg = load_config()
        # 只允许写入 host/port/user/database（非凭证字段）
        db_cfg = cfg.setdefault('database', {})
        for key in ('host', 'port', 'user', 'database'):
            if key in data:
                if key == 'port':
                    try:
                        port_val = int(data[key])
                    except (ValueError, TypeError):
                        return jsonify({'ok': False, 'msg': 'port 必须是整数'}), 400
                    # CRITICAL Fix M4: port 必须在合法范围内
                    if not (1 <= port_val <= 65535):
                        return jsonify({
                            'ok': False,
                            'msg': f'port 必须在 1-65535 之间（当前: {port_val}）'
                        }), 400
                    db_cfg[key] = port_val
                else:
                    db_cfg[key] = str(data[key])

        if save_config(cfg):
            logger.info(f'[设置] 更新: keys={list(data.keys())}')
            return jsonify({'ok': True})
        return jsonify({'ok': False, 'msg': '保存失败'}), 500

    # ============================================================
    # 日志清理（TASK-011：admin 限制）
    # ============================================================
    @bp.route('/inventory/api/cleanup', methods=['POST'])
    @admin_required
    @require_csrf  # CRITICAL Fix A3
    def cleanup_logs():
        """清理 30 天前的日志和已解决预警"""
        try:
            with get_conn() as conn:
                with conn.cursor() as c:
                    c.execute("DELETE FROM operation_logs WHERE created_at < DATE_SUB(NOW(), INTERVAL 30 DAY)")
                    log_count = c.rowcount
                    c.execute("DELETE FROM inventory_alerts WHERE is_resolved=1 AND resolved_at < DATE_SUB(NOW(), INTERVAL 30 DAY)")
                    alert_count = c.rowcount
                conn.commit()

            # CRITICAL Fix M5: 清理操作本身需要审计（防止有人恶意清理证据）
            operator = session.get('username') or 'admin'
            try:
                log_operation(
                    op_type='cleanup',
                    entity='system',
                    entity_id=0,
                    operator=operator,
                    detail={
                        'logs_deleted': log_count,
                        'alerts_deleted': alert_count,
                        'reason': '30 天自动清理'
                    }
                )
            except Exception:
                # 审计失败不应阻塞主操作
                logger.exception('[清理] 审计日志写入失败')

            logger.info(f'[清理] 删除 {log_count} 条日志, {alert_count} 条预警, 操作人={operator}')
            return jsonify({'ok': True, 'logs_deleted': log_count, 'alerts_deleted': alert_count})
        except Exception:
            logger.exception('[清理] 失败')
            return jsonify({'ok': False, 'msg': '清理失败'}), 500

    # ============================================================
    # 系统信息（admin 可见）
    # ============================================================
    @bp.route('/inventory/api/system/info', methods=['GET'])
    @admin_required
    def system_info():
        """系统信息（仅 admin）"""
        return jsonify({
            'ok': True,
            'data': {
                'python_version': sys.version.split()[0],
                'project_root': PROJECT_ROOT,
                'backup_dir': BACKUP_DIR,
                'config_path': CONFIG_PATH,
                'is_admin': session.get('is_admin', False)
            }
        })
