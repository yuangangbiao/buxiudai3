# -*- coding: utf-8 -*-
"""库存 Web 蓝图 — 数据库工具与公共校验函数

TASK-003 / TASK-006 / TASK-011 实施：
- validate_required: 必填+类型校验（返回 (errors, converted) 元组）
- validate_qty: 数量边界 + MAX_STOCK 校验（TASK-014）
- log_operation: 写操作审计日志埋点（TASK-013）
- execute: SQL 执行封装（with context manager）
- PROJECT_ROOT: 统一项目根目录定义（TASK-003）
"""
import os
import json
import logging
import queue
import re
import threading
from contextlib import contextmanager
from functools import lru_cache
from decimal import Decimal, InvalidOperation
from datetime import datetime
from core.db import get_direct_connection

logger = logging.getLogger(__name__)

# ============================================================
# TASK-003: PROJECT_ROOT 统一定义 + 备份目录自动创建
# ============================================================

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP_DIR = os.path.join(PROJECT_ROOT, 'inventory_backups')
CONFIG_PATH = os.path.join(PROJECT_ROOT, 'inventory_config.json')

# 自动创建备份目录（防止 backup_restore 时目录不存在）
try:
    os.makedirs(BACKUP_DIR, exist_ok=True)
    logger.info(f'[TASK-003] 备份目录就绪: {BACKUP_DIR}')
except OSError as e:
    logger.error(f'[TASK-003] 备份目录创建失败: {e}')


# ============================================================
# 共享 MySQL 配置（与 inventory_api_server 保持一致）
# ============================================================

def _mysql_cfg():
    """从环境变量获取 MySQL 配置（不缓存，每次新连接）"""
    return {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'port': int(os.getenv('MYSQL_PORT', '3306')),
        'user': os.getenv('MYSQL_USER'),
        'password': os.getenv('MYSQL_PASSWORD', ''),
        'database': os.getenv('INVENTORY_DB_NAME', 'inventory_db'),
        'charset': 'utf8mb4',
        'connect_timeout': int(os.getenv('DB_CONNECT_TIMEOUT', '3')),
        'autocommit': False,
    }


# ============================================================
# TASK-006: validate_required 校验函数（v2.3：返回 errors + converted）
# ============================================================

# 字段长度限制
FIELD_MAX_LENGTHS = {
    'code': 50,
    'name': 100,
    'spec': 200,
    'unit': 20,
    'category': 50,
}

# 允许的 code 字符（仅字母数字下划线）
CODE_PATTERN = re.compile(r'^[A-Za-z0-9_]+$')

# 允许的 name 字符（中文 + 字母数字下划线 + 空格 + 常用标点）
NAME_PATTERN = re.compile(r'^[\u4e00-\u9fa5A-Za-z0-9_\-\s\(\)（）、,，.。/]+$')


def _convert_value(val, target_type):
    """TASK-006: 转换字符串到目标类型（int / float）"""
    if val is None:
        return None
    if target_type is int:
        try:
            return int(val)
        except (ValueError, TypeError):
            return None
    if target_type is float:
        try:
            return float(val)
        except (ValueError, TypeError):
            return None
    return val


def validate_required(data, fields, types=None):
    """必填字段 + 类型校验

    Args:
        data: dict, 请求数据
        fields: list, 必填字段名
        types: dict, 字段 -> 期望类型 {field: int/float/str}

    Returns:
        (errors: list[str], converted: dict) 元组
        调用方应使用 converted[field] 代替 data[field] 传给 SQL

    v2.3 升级：
    - 字段长度限制（code ≤ 50, name ≤ 100）
    - code 字符限制（仅字母数字下划线）
    - 错误信息聚合
    """
    errors = []
    converted = {}
    types = types or {}

    for field in fields:
        val = data.get(field)

        # 必填检查
        if val is None or val == '':
            errors.append(f'{field} 必填')
            continue

        # 长度检查
        max_len = FIELD_MAX_LENGTHS.get(field)
        if max_len and isinstance(val, str) and len(val) > max_len:
            errors.append(f'{field} 长度超过 {max_len}')
            continue

        # 字符检查
        if field == 'code' and isinstance(val, str) and not CODE_PATTERN.match(val):
            errors.append(f'{field} 只能包含字母、数字、下划线')
            continue
        if field == 'name' and isinstance(val, str) and not NAME_PATTERN.match(val):
            errors.append(f'{field} 包含非法字符')
            continue

        # 类型转换
        expected = types.get(field)
        if expected is not None and expected is not str:
            cv = _convert_value(val, expected)
            if cv is None:
                errors.append(f'{field} 类型错误（期望 {expected.__name__}）')
                continue
            converted[field] = cv
        else:
            converted[field] = val if isinstance(val, str) else str(val)

    return errors, converted


# ============================================================
# TASK-014: 数量边界 + MAX_STOCK 校验
# ============================================================

# CRITICAL Fix M6: 用 @lru_cache 包装（环境变量一般启动后不变）
@lru_cache(maxsize=1)
def _get_max_stock():
    """TASK-014: 读取 INVENTORY_MAX_STOCK，无默认 + 非整数启动失败

    CRITICAL Fix M6: 加 @lru_cache 缓存环境变量读取（每次 validate_qty 都会调用）
    """
    val = os.getenv('INVENTORY_MAX_STOCK')
    if val is None:
        raise RuntimeError("环境变量 INVENTORY_MAX_STOCK 必须设置（无默认值）")
    try:
        v = int(val)
        if v <= 0:
            raise ValueError
        return v
    except ValueError:
        raise RuntimeError(f"INVENTORY_MAX_STOCK 必须是正整数，当前: {val!r}")


def validate_qty(qty, field='qty'):
    """TASK-014: 数量校验（>0, <= MAX_STOCK）"""
    if qty is None:
        return f'{field} 必填'
    try:
        v = float(qty)
    except (ValueError, TypeError):
        return f'{field} 必须是数字'
    if v <= 0:
        return f'{field} 必须大于 0'
    try:
        max_stock = _get_max_stock()
    except RuntimeError as e:
        return f'系统配置错误: {e}'
    if v > max_stock:
        return f'{field} 超过最大允许值 {max_stock}'
    return None


# ============================================================
# TASK-013: 写操作审计日志埋点
# CRITICAL Fix H8: 引入简单连接池，避免每次新连接耗尽
# ============================================================

# CRITICAL Fix H8: 自建简单连接池（避免每次 log_operation 新建连接）
_audit_pool = None
_audit_pool_lock = threading.Lock()
_AUDIT_POOL_SIZE = 4  # 审计专用池大小


def _get_audit_pool():
    """懒加载审计日志连接池"""
    global _audit_pool
    if _audit_pool is not None:
        return _audit_pool
    with _audit_pool_lock:
        if _audit_pool is not None:  # double-check
            return _audit_pool
        try:
            _audit_pool = queue.Queue(maxsize=_AUDIT_POOL_SIZE)
            for _ in range(_AUDIT_POOL_SIZE):
                conn = get_direct_connection(**_mysql_cfg())
                _audit_pool.put(conn)
            logger.info(f'[审计池] 已创建 {_AUDIT_POOL_SIZE} 个连接')
            return _audit_pool
        except Exception as e:
            logger.exception(f'[审计池] 创建失败: {e}')
            return None


def log_operation(op_type, entity, entity_id, operator='system', detail=None):
    """记录写操作审计日志

    Args:
        op_type: 操作类型 (create/update/delete/inbound/outbound/...)
        entity: 实体类型 (product/supplier/...)
        entity_id: 实体 ID
        operator: 操作人（从 session 获取）
        detail: dict 详情（如修改前后快照）

    CRITICAL Fix H8: 使用连接池而非每次新建连接
    """
    pool = _get_audit_pool()
    if pool is None:
        # 池创建失败时降级为单次连接（不阻塞业务）
        _log_operation_single(op_type, entity, entity_id, operator, detail)
        return

    conn = None
    try:
        # 从池中借出（最多等 2 秒）
        conn = pool.get(timeout=2)
        with conn.cursor() as c:
            c.execute(
                """INSERT INTO operation_logs
                   (op_type, entity, entity_id, operator, detail, created_at)
                   VALUES (%s, %s, %s, %s, %s, NOW())""",
                (op_type, entity, str(entity_id), operator,
                 json.dumps(detail, ensure_ascii=False) if detail else None)
            )
        conn.commit()
    except queue.Empty:
        logger.warning('[审计池] 连接池耗尽，降级为单次连接')
        _log_operation_single(op_type, entity, entity_id, operator, detail)
    except Exception as e:
        # CRITICAL Fix H10: 失败时仍要记录（不能让审计被静默吞掉）
        logger.exception(f'[审计日志] 写入失败: {e}')
        # 失败的连接不放回池（已损坏）
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
    else:
        # 成功则归还连接
        try:
            pool.put_nowait(conn)
        except queue.Full:
            try:
                conn.close()
            except Exception:
                pass


def _log_operation_single(op_type, entity, entity_id, operator, detail):
    """降级方案：单次连接写入审计日志（连接池失败时用）"""
    try:
        conn = get_direct_connection(**_mysql_cfg())
        try:
            with conn.cursor() as c:
                c.execute(
                    """INSERT INTO operation_logs
                       (op_type, entity, entity_id, operator, detail, created_at)
                       VALUES (%s, %s, %s, %s, %s, NOW())""",
                    (op_type, entity, str(entity_id), operator,
                     json.dumps(detail, ensure_ascii=False) if detail else None)
                )
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        logger.exception(f'[审计日志] 单次连接写入失败: {e}')


# ============================================================
# SQL 执行封装
# ============================================================

@contextmanager
def get_conn():
    """上下文管理器：自动 close"""
    conn = get_direct_connection(**_mysql_cfg())
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass


# TASK-T2: 别名 - service 层用 _direct_conn 表达"直接连接（不走连接池）"
_direct_conn = get_conn


def execute(sql, params=None, fetch=False, commit=False):
    """执行 SQL 工具函数

    Args:
        sql: SQL 语句（必须用 %s 占位符，禁止 f-string/format 拼接！）
        params: 参数元组/列表
        fetch: True 返回 rows，False 返回 rowcount
        commit: True 自动 commit
    """
    conn = get_direct_connection(**_mysql_cfg())
    try:
        with conn.cursor() as c:
            c.execute(sql, params or ())
            if fetch:
                if fetch == 'all':
                    rows = c.fetchall()
                else:
                    rows = c.fetchone()
                return rows
            rowcount = c.rowcount
        if commit:
            conn.commit()
        return rowcount
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ============================================================
# TASK-018: 文件权限加固（跨平台）
# ============================================================

def _secure_file(path):
    """TASK-018: 设置配置文件权限为 0o600（仅 Linux/macOS）
    Windows 下用 NTFS ACL（PowerShell icacls）"""
    if os.name == 'nt':
        # Windows: 用 icacls 限制为当前用户
        try:
            import subprocess
            username = os.getenv('USERNAME', 'Everyone')
            subprocess.run(
                ['icacls', path, '/inheritance:r',
                 '/grant:r', f'{username}:(R,W)'],
                check=False, capture_output=True
            )
        except Exception as e:
            logger.warning(f'[TASK-018] Windows ACL 设置失败: {e}')
    else:
        # Linux/macOS
        try:
            os.chmod(path, 0o600)
        except OSError as e:
            logger.warning(f'[TASK-018] chmod 0o600 失败: {e}')


def load_config():
    """加载 inventory_config.json（不存在则返回空 dict）"""
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.exception(f'[配置] 加载失败: {e}')
        return {}


def save_config(cfg):
    """保存 inventory_config.json + 自动加固权限"""
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        _secure_file(CONFIG_PATH)
        return True
    except OSError as e:
        logger.exception(f'[配置] 保存失败: {e}')
        return False


# ============================================================
# TASK-T3: 公共 update / pagination / soft_delete
# ============================================================

def parse_pagination(args, default_size: int = 20, max_size: int = 200):
    """从 request.args 解析分页参数

    Args:
        args: Flask request.args
        default_size: 默认每页
        max_size: 最大每页（防 DoS）

    Returns:
        (page, page_size) 元组
    """
    try:
        page = max(1, int(args.get('page', 1)))
    except (ValueError, TypeError):
        page = 1
    try:
        page_size = min(max_size, max(1, int(args.get('page_size', default_size))))
    except (ValueError, TypeError):
        page_size = default_size
    return page, page_size


def _do_update(table, eid, sql_template, params, entity, audit_detail, data_for_len_check=None):
    """TASK-T3: 通用更新 - 长度检查 + 事务 UPDATE + 审计

    Args:
        table: 表名（白名单后传入）
        eid: 主键 ID
        sql_template: UPDATE SQL（含 WHERE id=%s）
        params: SQL 参数元组（不含 eid）
        entity: 审计 entity 名
        audit_detail: 审计 detail dict
        data_for_len_check: 需要长度检查的 dict（None 跳过）

    Returns:
        (jsonify_response, status_code)
    """
    # 白名单表名（防 SQL 注入）
    ALLOWED_TABLES = {'products', 'suppliers', 'categories', 'warehouses', 'bases'}
    if table not in ALLOWED_TABLES:
        return jsonify({'ok': False, 'msg': f'非法表名: {table}'}), 400

    if data_for_len_check is not None:
        len_errs = _check_field_lengths(data_for_len_check)
        if len_errs:
            return jsonify({'ok': False, 'msg': '; '.join(len_errs)}), 400

    try:
        with _direct_conn() as conn:
            with conn.cursor() as c:
                # FOR UPDATE 行级锁
                c.execute(f'SELECT id FROM {table} WHERE id=%s AND deleted_at IS NULL FOR UPDATE', (eid,))
                if not c.fetchone():
                    return jsonify({'ok': False, 'msg': '记录不存在'}), 404
                # 拼接 WHERE
                full_sql = sql_template + ' WHERE id=%s'
                c.execute(full_sql, tuple(params) + (eid,))
            conn.commit()

        try:
            log_operation(
                op_type='update', entity=entity, entity_id=eid,
                operator='admin', detail=audit_detail
            )
        except Exception:
            logger.exception(f'[{entity} 更新] 审计失败')

        return jsonify({'ok': True}), 200
    except Exception:
        logger.exception(f'[{entity} 更新] 失败')
        return jsonify({'ok': False, 'msg': '更新失败'}), 500


def _soft_delete(table, eid, entity, extra_check=None):
    """TASK-T3: 软删除公共函数

    Args:
        table: 表名（白名单）
        eid: 主键 ID
        entity: 审计 entity 名
        extra_check: 可选引用检查函数 (eid) -> error_msg or ''

    Returns:
        (jsonify_response, status_code)
    """
    ALLOWED_TABLES = {'products', 'suppliers', 'categories', 'warehouses', 'bases'}
    if table not in ALLOWED_TABLES:
        return jsonify({'ok': False, 'msg': f'非法表名: {table}'}), 400

    # 引用检查
    if extra_check:
        err = extra_check(eid)
        if err:
            return jsonify({'ok': False, 'msg': err}), 409

    try:
        with _direct_conn() as conn:
            with conn.cursor() as c:
                rows = c.execute(
                    f'UPDATE {table} SET deleted_at=NOW() WHERE id=%s AND deleted_at IS NULL',
                    (eid,)
                )
            conn.commit()

        if not rows:
            return jsonify({'ok': False, 'msg': '记录不存在或已删除'}), 404

        try:
            log_operation(
                op_type='delete', entity=entity, entity_id=eid,
                operator='admin', detail={'soft_delete': True}
            )
        except Exception:
            logger.exception(f'[{entity} 删除] 审计失败')

        return jsonify({'ok': True}), 200
    except Exception:
        logger.exception(f'[{entity} 删除] 失败')
        return jsonify({'ok': False, 'msg': '删除失败'}), 500


def _restore(table, eid, entity):
    """TASK-T3: 恢复软删除的记录"""
    ALLOWED_TABLES = {'products', 'suppliers', 'categories', 'warehouses', 'bases'}
    if table not in ALLOWED_TABLES:
        return jsonify({'ok': False, 'msg': f'非法表名: {table}'}), 400

    try:
        with _direct_conn() as conn:
            with conn.cursor() as c:
                # 查 code 冲突
                if entity in ('product', 'supplier', 'category', 'warehouse', 'base'):
                    code_col = 'code' if entity in ('product', 'warehouse', 'base') else None
                    if code_col:
                        c.execute(
                            f'SELECT {code_col} FROM {table} WHERE id=%s AND deleted_at IS NOT NULL',
                            (eid,)
                        )
                        row = c.fetchone()
                        if not row:
                            return jsonify({'ok': False, 'msg': '记录不存在或未被删除'}), 404
                        if row.get(code_col):
                            c.execute(
                                f'SELECT id FROM {table} WHERE {code_col}=%s AND deleted_at IS NULL AND id!=%s',
                                (row[code_col], eid)
                            )
                            if c.fetchone():
                                return jsonify({'ok': False, 'msg': f'code {row[code_col]!r} 已被占用'}), 409

                rows = c.execute(
                    f'UPDATE {table} SET deleted_at=NULL WHERE id=%s AND deleted_at IS NOT NULL',
                    (eid,)
                )
            conn.commit()

        if not rows:
            return jsonify({'ok': False, 'msg': '记录不存在或未被删除'}), 404

        try:
            log_operation(
                op_type='restore', entity=entity, entity_id=eid,
                operator='admin', detail={}
            )
        except Exception:
            logger.exception(f'[{entity} 恢复] 审计失败')

        return jsonify({'ok': True}), 200
    except Exception:
        logger.exception(f'[{entity} 恢复] 失败')
        return jsonify({'ok': False, 'msg': '恢复失败'}), 500
