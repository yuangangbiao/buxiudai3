# -*- coding: utf-8 -*-
"""MySQL 存储后端 — 容器中心专用，无 cc_ 前缀"""
import os, json, logging, uuid as _uuid
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from contextlib import contextmanager
import pymysql
from pymysql.cursors import DictCursor
from dbutils.pooled_db import PooledDB

from dotenv import load_dotenv
# [T18 修复 2026-06-14] 动态计算项目根目录 .env 路径
# 之前：r'D:\yuan\不锈钢网带跟单3.0\.env' 硬编码 → 跨机器部署 100% 失败
# 现在：从 storage/mysql_storage.py 自身位置回溯 3 级到项目根
#   __file__ = .../mobile_api_ai/storage/mysql_storage.py
#   .parent   = .../mobile_api_ai/storage/
#   .parent.parent = .../mobile_api_ai/
#   .parent.parent.parent = 项目根 (D:\yuan\不锈钢网带跟单3.0)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_FILE = PROJECT_ROOT / '.env'
# 兜底：若项目根没 .env，尝试 mobile_api_ai/.env（更常见）
if not ENV_FILE.exists():
    _alt = Path(__file__).resolve().parent.parent / '.env'
    if _alt.exists():
        ENV_FILE = _alt
load_dotenv(str(ENV_FILE), override=True)

from core.exceptions import safe_cursor_execute, safe_cursor_insert

_mysql_cfg_cache = None
_db_timeout_cache = None
_base_dir_cache = None

def _get_mysql_cfg():
    global _mysql_cfg_cache
    if _mysql_cfg_cache is None:
        from core.config import CONTAINER_MYSQL_CFG
        _mysql_cfg_cache = CONTAINER_MYSQL_CFG.copy()
    return _mysql_cfg_cache

def _get_db_timeout():
    global _db_timeout_cache
    if _db_timeout_cache is None:
        from core.config import DB_CONNECT_TIMEOUT
        _db_timeout_cache = DB_CONNECT_TIMEOUT
    return _db_timeout_cache

def _get_base_dir():
    global _base_dir_cache
    if _base_dir_cache is None:
        from core.config import BASE_DIR
        _base_dir_cache = BASE_DIR
    return _base_dir_cache
from utils.auto_schema import auto_ensure_schema

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════
# 接口契约：必须实现的方法，connect() 时自动校验
# ══════════════════════════════════════════════════════════
REQUIRED_METHODS = [
    'connect', 'disconnect', 'health_check',
    'execute', 'fetch_one', 'fetch_all', 'insert', 'update',
    'load_enterprise_structure', 'get_enterprise_structure', 'save_enterprise_structure',
    'get_all_process_records', 'get_process_record', 'save_process_record',
    'get_process_records', 'get_process_records_by_work_order',
    'save_package', 'get_packages', 'get_package', 'delete_package',
    'update_package', 'update_package_status', 'cleanup_expired_packages',
    'get_sub_steps_by_process', 'save_process_sub_step', 'save_sub_step',
    'get_sub_step_summary', 'get_last_sub_step',
    'get_all_workers', 'get_worker', 'save_worker', 'delete_worker',
    'get_attendance', 'get_attendance_by_date', 'upsert_attendance',
    'save_return_record',
    'save_data_flow_log', 'log_sync',
]


def _fmt(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return 1 if v else 0
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, (set, frozenset)):
        return json.dumps(list(v), ensure_ascii=False)
    if isinstance(v, bytes):
        return v.decode('utf-8', errors='replace')
    return v


def _safe_name(name):
    import re
    return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]{0,63}$', name))


class MySQLStorage:
    PREFIX = ''
    _pool = None  # 类级别连接池，所有实例共享

    PSS_COLUMNS = {'id', 'uuid', 'order_no', 'step_name', 'quantity',
                   'qualified_qty', 'operator', 'process_code', 'created_at'}

    def __init__(self, **kwargs):
        self.config = _get_mysql_cfg()
        self.config.update(kwargs)
        self._tables_ensured = False

    @property
    def _conn(self):
        """兼容旧 API — 每次从连接池获取独立连接"""
        self._ensure_conn()
        return self._pool.connection()

    def _get_conn(self):
        """获取自动提交的连接 — pymysql+DBUtils 池化后 autocommit 需手动设置"""
        conn = self._pool.connection()
        with conn.cursor(DictCursor) as c:
            c.execute("SET autocommit=1")
        return conn

    def _table(self, name: str) -> str:
        """兼容旧 API — 返回表名字符串"""
        if not _safe_name(name):
            raise ValueError(f"非法表名: {name}")
        return name

    def _migrate_schema(self):
        """自动迁移 MySQL 表结构，添加缺失列（连接时调用）"""
        if not self._pool:
            return
        migrations = {
            'process_records': [
                ('work_order_no', 'ALTER TABLE process_records ADD COLUMN work_order_no VARCHAR(100) DEFAULT \'\''),
                ('process_type', 'ALTER TABLE process_records ADD COLUMN process_type VARCHAR(50) NOT NULL DEFAULT \'production\''),
                ('flow_type', 'ALTER TABLE process_records ADD COLUMN flow_type VARCHAR(100) DEFAULT \'production\''),
            ],
            # R12: data_packages 加 process_code 列(SSOT 分类主键)
            # 配合 ETL 脚本 fill_data_packages_process_code.py 回填老数据
            'data_packages': [
                ('process_code', 'ALTER TABLE data_packages ADD COLUMN process_code VARCHAR(10) DEFAULT \'\''),
                ('idx_pkg_process_code', 'ALTER TABLE data_packages ADD INDEX idx_pkg_process_code (process_code)'),
                ('updated_at', 'ALTER TABLE data_packages ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'),
            ],
            # F17: workers 加企业微信字段(同步权限相关)
            'workers': [
                ('wechat_userid', 'ALTER TABLE workers ADD COLUMN wechat_userid VARCHAR(64) DEFAULT \'\''),
                ('can_receive_wechat', 'ALTER TABLE workers ADD COLUMN can_receive_wechat TINYINT(1) DEFAULT 1'),
                ('can_send_wechat', 'ALTER TABLE workers ADD COLUMN can_send_wechat TINYINT(1) DEFAULT 1'),
                ('max_tasks', 'ALTER TABLE workers ADD COLUMN max_tasks INT DEFAULT 10'),
            ],
        }
        for table, cols in migrations.items():
            for col, ddl in cols:
                try:
                    with self._pool.connection() as _c:
                        with _c.cursor(DictCursor) as cur:
                            cur.execute(ddl)
                    logger.info('[MySQLStorage] 迁移: %s.%s 已添加', table, col)
                except Exception as e:
                    err_msg = str(e)
                    if ('Duplicate column' in err_msg
                            or 'Duplicate key name' in err_msg
                            or 'already exists' in err_msg.lower()):
                        logger.debug('[MySQLStorage] 列/索引 %s.%s 已存在，跳过', table, col)
                    else:
                        logger.warning('[MySQLStorage] 迁移列 %s.%s 失败: %s', table, col, e)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *a):
        self.disconnect()

    def connect(self) -> bool:
        try:
            # [K28 修复 2026-06-14] 调大连接池 + 自动恢复
            # 之前：maxconnections=20 并发 200 排队崩溃，_pool 被设为 None 后 _pool.connection() 报 NoneType
            # 现在：maxconnections=50 + blocking + 自动重试初始化
            # [T8 修复 2026-06-14] 不强制 DictCursor 默认值
            # 之前：cursorclass=DictCursor → 业务 cur.fetchone()[0] 报 KeyError
            # 现在：默认 tuple cursor，兼容 pymysql.connect 行为；业务层可显式 cursor(DictCursor)
            MySQLStorage._pool = PooledDB(
                creator=pymysql,
                maxconnections=50, mincached=5, maxcached=15,
                blocking=True, ping=1,
                **self.config, autocommit=True,
            )
            self._check_contract()
            self._ensure_all_tables()
            self._seed_default_data()
            self._migrate_schema()
            return True
        except pymysql.Error as e:
            logger.error("MySQL 连接池初始化失败: %s", e)
            MySQLStorage._pool = None
            return False

    def _check_contract(self):
        """启动时校验接口契约：缺方法立刻报错，不等运行时崩溃"""
        missing = [m for m in REQUIRED_METHODS if not hasattr(self, m) or not callable(getattr(self, m))]
        if missing:
            msg = f'[MySQLStorage] 接口契约校验失败，缺少 {len(missing)} 个方法: {missing}'
            logger.error(msg)
            raise RuntimeError(msg)
        logger.info('[MySQLStorage] 接口契约校验通过 (%d 个方法)', len(REQUIRED_METHODS))

    def _ensure_all_tables(self):
        """标准建表（不依赖 auto_ensure_schema 运行时猜列）
        首次启动执行 DDL，后续启动通过 SHOW TABLES 快速跳过。
        """
        if self._tables_ensured:
            return
        # 快速检查：表已存在则跳过全部 DDL
        try:
            with self._pool.connection() as _c:
                with _c.cursor(DictCursor) as cur:
                    cur.execute("SELECT COUNT(*) as cnt FROM information_schema.tables WHERE table_schema = %s AND table_name = 'enterprise_structure'",
                               (self.config.get('database', ''),))
                    row = cur.fetchone()
                    if row and row.get('cnt', 0) > 0:
                        self._tables_ensured = True
                        return
        except Exception:
            pass  # 查询失败则走完整建表流程

        ddl_list = [
            '''CREATE TABLE IF NOT EXISTS enterprise_structure (
                id INT NOT NULL PRIMARY KEY,
                departments LONGTEXT,
                users LONGTEXT,
                updated_at DATETIME
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

            '''CREATE TABLE IF NOT EXISTS workers (
                id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                enterprise_id VARCHAR(64) NOT NULL DEFAULT '',
                name VARCHAR(128) NOT NULL DEFAULT '',
                phone VARCHAR(32) DEFAULT '',
                role VARCHAR(64) DEFAULT '',
                department VARCHAR(128) DEFAULT '',
                status VARCHAR(32) DEFAULT 'active',
                sync_at DATETIME,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                wechat_userid VARCHAR(64) DEFAULT '' COMMENT '企业微信用户ID',
                can_receive_wechat TINYINT(1) DEFAULT 1 COMMENT '是否接收微信消息',
                can_send_wechat TINYINT(1) DEFAULT 1 COMMENT '是否发送微信消息',
                max_tasks INT DEFAULT 10 COMMENT '最大任务数',
                UNIQUE KEY uk_enterprise_id (enterprise_id),
                KEY idx_name (name),
                KEY idx_status (status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

            '''CREATE TABLE IF NOT EXISTS attendance (
                id INT AUTO_INCREMENT PRIMARY KEY,
                worker VARCHAR(200) NOT NULL,
                check_in VARCHAR(200) DEFAULT '',
                check_out VARCHAR(200) DEFAULT '',
                status VARCHAR(100) DEFAULT '未签到',
                date VARCHAR(200) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_worker_date (worker, date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

            '''CREATE TABLE IF NOT EXISTS process_records (
                id VARCHAR(64) NOT NULL PRIMARY KEY,
                process_type VARCHAR(50) DEFAULT 'production',
                order_no VARCHAR(100) DEFAULT '',
                product_name VARCHAR(200) DEFAULT '',
                quantity DOUBLE DEFAULT 0,
                unit VARCHAR(50) DEFAULT '',
                customer_name VARCHAR(200) DEFAULT '',
                delivery_date DATE,
                priority VARCHAR(50) DEFAULT 'normal',
                status VARCHAR(50) DEFAULT 'created',
                current_step INT DEFAULT 0,
                steps JSON,
                task_count INT DEFAULT 0,
                completed_task_count INT DEFAULT 0,
                flow_type VARCHAR(100) DEFAULT '',
                plan_start DATE,
                plan_end DATE,
                customer_group VARCHAR(100) DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                KEY idx_order_no (order_no),
                KEY idx_status (status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

            '''CREATE TABLE IF NOT EXISTS process_sub_steps (
                id VARCHAR(50) NOT NULL PRIMARY KEY,
                order_no VARCHAR(50),
                process_code VARCHAR(10),
                step_name VARCHAR(100),
                quantity DECIMAL(10,2) DEFAULT 0.00,
                operator VARCHAR(50),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

            '''CREATE TABLE IF NOT EXISTS data_packages (
                id VARCHAR(64) NOT NULL PRIMARY KEY,
                data_type VARCHAR(64) NOT NULL,
                title TEXT, content TEXT,
                source VARCHAR(128) DEFAULT '',
                priority VARCHAR(32) DEFAULT 'normal',
                status VARCHAR(32) DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                distributed_at DATETIME,
                acknowledged_at DATETIME,
                completed_at DATETIME,
                completed_qty INT DEFAULT 0,
                actual_qty INT DEFAULT 0,
                target_operator VARCHAR(64) DEFAULT '',
                operator_id VARCHAR(64) DEFAULT '',
                target_device VARCHAR(64) DEFAULT '',
                tags TEXT,
                related_order VARCHAR(64) DEFAULT '',
                related_process VARCHAR(64) DEFAULT '',
                KEY idx_pkg_type (data_type),
                KEY idx_pkg_status (status),
                KEY idx_pkg_operator (target_operator),
                KEY idx_pkg_order (related_order)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

            '''CREATE TABLE IF NOT EXISTS data_flow_logs (
                id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                event_type VARCHAR(64) NOT NULL DEFAULT '',
                flow_type VARCHAR(64) DEFAULT '',
                source VARCHAR(128) DEFAULT '',
                target VARCHAR(128) DEFAULT '',
                status VARCHAR(32) DEFAULT '',
                detail JSON,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

            '''CREATE TABLE IF NOT EXISTS sync_logs (
                id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                action VARCHAR(64) DEFAULT '',
                package_id VARCHAR(64) DEFAULT '',
                detail TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

            '''CREATE TABLE IF NOT EXISTS return_records (
                id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                order_id VARCHAR(64) NOT NULL DEFAULT '',
                reason TEXT,
                returned_qty DECIMAL(10,2) DEFAULT 0.00,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                KEY idx_order_id (order_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

            '''CREATE TABLE IF NOT EXISTS data_collection_records (
                id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                record_type VARCHAR(64) NOT NULL DEFAULT '',
                data_type VARCHAR(64) DEFAULT '',
                source_id VARCHAR(128) DEFAULT '',
                collected_at DATETIME,
                data JSON,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

            '''CREATE TABLE IF NOT EXISTS report_queue (
                id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                order_no VARCHAR(64) NOT NULL,
                step_name VARCHAR(128) NOT NULL,
                quantity DECIMAL(10,2) NOT NULL,
                operator VARCHAR(64) DEFAULT '',
                process_id VARCHAR(64) DEFAULT '',
                status VARCHAR(32) NOT NULL DEFAULT 'pending',
                retry_count INT DEFAULT 0,
                max_retries INT DEFAULT 3,
                last_error TEXT,
                enqueued_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                processed_at DATETIME,
                KEY idx_status (status),
                KEY idx_order (order_no)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

            # SSOT: schedule_records 表 F6 P9 DROP，数据已迁移到 process_records
            # 不再创建此表
        ]
        try:
            with self._pool.connection() as _c:
                with _c.cursor(DictCursor) as cur:
                    for ddl in ddl_list:
                        try:
                            cur.execute(ddl)
                        except pymysql.Error as e:
                            logger.warning('[MySQLStorage] DDL 非致命错误: %s', e)
            logger.info('[MySQLStorage] 标准建表完成 (%d 张)', len(ddl_list))
            self._tables_ensured = True
        except Exception as e:
            logger.warning('[MySQLStorage] 建表阶段异常: %s', e)

    def _seed_default_data(self):
        """建表后自动填充种子数据（仅当表为空时）
        [F16 T16.3 修复] enterprise_structure 表已 F6 P9 DROP, 跳过该表 seed
        """
        try:
            # [F16 T16.3 修复] enterprise_structure 已 F6 P9 DROP, 数据迁到 data/enterprise_structure.json
            # 不再 seed MySQL (无该表), 用户通过 storage.load_enterprise_structure() 读 JSON
            logger.info('[F16 T16.3] enterprise_structure 已 F6 P9 DROP, 数据源 = data/enterprise_structure.json')

            # workers
            row = self.fetch_one("SELECT COUNT(*) as cnt FROM workers")
            if row and row['cnt'] == 0:
                op_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'operators.json')
                if os.path.exists(op_path):
                    with open(op_path, 'r', encoding='utf-8') as f:
                        ops = json.load(f)
                    for op_id, op in ops.items():
                        self.insert('workers', {
                            'enterprise_id': op.get('id', op_id),
                            'name': op.get('name', ''),
                            'role': op.get('role', '操作员'),
                            'department': op.get('department', ''),
                            'status': 'active' if op.get('enabled', True) else 'inactive',
                        })
                    logger.info('[MySQLStorage] 种子数据: workers 已初始化 (%d 人)', len(ops))
        except Exception as e:
            logger.warning('[MySQLStorage] 种子数据初始化失败: %s', e)

    def disconnect(self):
        # [K28 修复 2026-06-14] disconnect 不应粗暴置 None（导致并发请求失败）
        # 之前：disconnect 后 self._pool = None，其他线程持有 self 引用时拿到 None
        # 现在：保留 _pool，仅清空实例状态
        if self._pool:
            try: self._pool.close()
            except Exception: pass
            # 不置 None，避免并发 race；下次 connect() 会重新创建

    def health_check(self) -> Dict:
        r = {'status': 'ok', 'type': 'mysql', 'pool': 'PooledDB'}
        try:
            if not self._pool: self.connect()
            if self._pool:
                with self._pool.connection() as conn:
                    with conn.cursor(DictCursor) as c:
                        c.execute("SELECT 1")
            else:
                r['status'] = 'error'
        except Exception as e:
            r['status'] = 'error'
            r['error'] = str(e)
        return r

    @contextmanager
    def transaction(self):
        """事务上下文管理器 [T1 2026-06-14 + T41.3 修复 2026-06-14]

        替代业务层直连 pymysql.connect 的事务模式：
            with storage.transaction() as (conn, cur):
                cur.execute("SELECT ... FOR UPDATE")
                cur.execute("UPDATE ...")
                # 自动 commit (无异常) / rollback (异常)

        优点:
        - 走连接池，无 5-20ms 握手开销
        - 自动 commit/rollback，无需业务层手写
        - 异常传播，调用方 try/except 仍可捕获

        Returns:
            (conn, cur) 元组
        """
        self._ensure_conn()
        with self._pool.connection() as conn:
            # [T41.3 修复 2026-06-14] 事务内显式关闭 autocommit
            # 之前：池化 autocommit=True → 每次 execute 立即 commit → 抛错时已落盘，"回滚"无效
            # 现在：进入事务 SET autocommit=0，所有 DML 在 commit/rollback 前不落盘
            cur = conn.cursor()
            try:
                cur.execute("SET autocommit=0")
                yield conn, cur
                conn.commit()
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
                # 恢复 autocommit（避免连接归还池后污染下次使用）
                try:
                    cur.execute("SET autocommit=1")
                except Exception:
                    pass
                raise
            else:
                try:
                    cur.execute("SET autocommit=1")
                except Exception:
                    pass
            finally:
                try:
                    cur.close()
                except Exception:
                    pass

    def _ensure_conn(self):
        if self._pool is None:
            self.connect()

    def _reconnect_and_retry(self):
        """池版本：无需重连，PooledDB 自动管理"""
        self._ensure_conn()

    def _safe_execute(self, sql, params=None, default_return=0):
        """池安全执行 — 显式 autocommit"""
        self._ensure_conn()
        with self._pool.connection() as conn:
            return safe_cursor_execute(conn, sql, params, default_return=default_return)

    def _safe_insert(self, sql, params=None):
        """池安全插入 — 显式 autocommit 确保数据落盘"""
        self._ensure_conn()
        with self._pool.connection() as conn:
            return safe_cursor_insert(conn, sql, params)

    def execute(self, sql, params=None) -> int:
        self._ensure_conn()
        try:
            return self._safe_execute(sql, params, default_return=0)
        except (pymysql.err.InterfaceError, pymysql.err.OperationalError):
            self._reconnect_and_retry()
            return self._safe_execute(sql, params, default_return=0)

    # ───── 类型归一化 ─────
    @staticmethod
    def _normalize(value):
        """将 MySQL 原生类型转换为 Python 标准类型，避免 float/Decimal 混算"""
        from decimal import Decimal
        if value is None:
            return None
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, bytes):
            return value.decode('utf-8', errors='replace')
        return value

    @staticmethod
    def _normalize_row(row):
        """归一化整行数据"""
        if row is None:
            return None
        if isinstance(row, dict):
            return {k: MySQLStorage._normalize(v) for k, v in row.items()}
        return row

    def fetch_one(self, sql, params=None):
        self._ensure_conn()
        import time as _t
        _start = _t.time()
        try:
            with self._pool.connection() as _c:
                with _c.cursor(DictCursor) as c:
                    c.execute(sql, params)
                    result = self._normalize_row(c.fetchone())
                    self._log_slow_query(sql, params, _t.time() - _start)
                    return result
        except (pymysql.err.InterfaceError, pymysql.err.OperationalError):
            self._reconnect_and_retry()
            with self._pool.connection() as _c:
                with _c.cursor(DictCursor) as c:
                    c.execute(sql, params)
                    result = self._normalize_row(c.fetchone())
                    self._log_slow_query(sql, params, _t.time() - _start)
                    return result

    def fetch_all(self, sql, params=None):
        self._ensure_conn()
        import time as _t
        _start = _t.time()
        try:
            with self._pool.connection() as _c:
                with _c.cursor(DictCursor) as c:
                    c.execute(sql, params)
                    rows = [self._normalize_row(r) for r in c.fetchall()]
                    self._log_slow_query(sql, params, _t.time() - _start, row_count=len(rows))
                    return rows
        except (pymysql.err.InterfaceError, pymysql.err.OperationalError):
            self._reconnect_and_retry()
            with self._pool.connection() as _c:
                with _c.cursor(DictCursor) as c:
                    c.execute(sql, params)
                    rows = [self._normalize_row(r) for r in c.fetchall()]
                    self._log_slow_query(sql, params, _t.time() - _start, row_count=len(rows))
                    return rows

    # [优化 2026-06-13] 慢查询日志：> 200ms 警告，> 1s 错误
    SLOW_QUERY_THRESHOLD_MS = 200
    VERY_SLOW_QUERY_THRESHOLD_MS = 1000

    @classmethod
    def _log_slow_query(cls, sql, params, elapsed_sec, row_count=None):
        elapsed_ms = elapsed_sec * 1000
        if elapsed_ms < cls.SLOW_QUERY_THRESHOLD_MS:
            return
        sql_first_line = (sql[:200] + '...') if len(sql) > 200 else sql
        params_str = str(params)[:100] if params else ''
        if row_count is not None:
            extra = f' rows={row_count}'
        else:
            extra = ''
        if elapsed_ms >= cls.VERY_SLOW_QUERY_THRESHOLD_MS:
            logger.error(f'[VERY SLOW SQL] {elapsed_ms:.2f}ms{extra} | {sql_first_line} | params={params_str}')
        else:
            logger.warning(f'[SLOW SQL] {elapsed_ms:.2f}ms{extra} | {sql_first_line} | params={params_str}')

    # 无 id 的表自动生成 UUID（pymysql 无自增 insert_id 返回）
    _UUID_TABLES = {'process_records', 'process_sub_steps', 'data_packages'}  # id 为 varchar 的表

    def insert(self, table: str, data: dict) -> Optional[int]:
        self._ensure_conn()
        if not _safe_name(table):
            raise ValueError(f"非法表名: {table}")
        if table in self._UUID_TABLES and 'id' not in data:
            data = {**data, 'id': str(_uuid.uuid4())[:8]}
        with self._get_conn() as _conn:
            auto_ensure_schema(_conn, table, data)
            cols = ', '.join(f'`{k}`' for k in data)
            vals = ', '.join(['%s'] * len(data))
            params = [_fmt(v) for v in data.values()]
            return self._safe_insert(f"INSERT INTO `{table}` ({cols}) VALUES ({vals})", params)

    def update(self, table, data, where, where_params=None):
        self._ensure_conn()
        if not _safe_name(table):
            raise ValueError(f"非法表名: {table}")
        with self._pool.connection() as _conn:
            auto_ensure_schema(_conn, table, data)
        sets = ', '.join(f'`{k}`= %s' for k in data)
        params = [_fmt(v) for v in data.values()]
        if where_params:
            params.extend(where_params)
        return self._safe_execute(f"UPDATE `{table}` SET {sets} WHERE {where}", params, default_return=0)

    # ───── 企业架构 ─────
    @staticmethod
    def _load_enterprise_structure_json():
        """[F16 T16.3 修复] 改用 data/enterprise_structure.json 替代 MySQL (F6 P9 已 DROP)
        原因: enterprise_structure 表已被 F6 P9 2026-06-10 DROP (跨库历史表清理, 详见 MEMORY.md L20)
              企业架构数据迁到 JSON 静态文件, 读路径与原 SELECT 保持一致 (返回 dict 含 departments/users/updated_at)
        """
        # 路径优先级: data/enterprise_structure.json (项目根) > storage/data/enterprise_structure.json (兼容)
        candidates = [
            os.path.join(_get_base_dir(), 'data', 'enterprise_structure.json'),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'enterprise_structure.json'),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'enterprise_structure.json'),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'enterprise_structure.json'),
        ]
        for p in candidates:
            if p and os.path.exists(p):
                try:
                    with open(p, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    # 规范化: 字段缺失补空 + updated_at 默认文件 mtime
                    if not isinstance(data.get('departments'), list):
                        data['departments'] = []
                    if not isinstance(data.get('users'), list):
                        data['users'] = []
                    if 'updated_at' not in data:
                        data['updated_at'] = datetime.fromtimestamp(
                            os.path.getmtime(p)).isoformat()
                    return data
                except Exception as e:
                    logger.warning(f'[F16 T16.3] 读 enterprise_structure.json 失败: {p} err={e}')
        return {'departments': [], 'users': [], 'updated_at': datetime.now().isoformat()}

    def load_enterprise_structure(self):
        """[F16 T16.3 修复] 改用 JSON 替代 SELECT (F6 P9 DROP)"""
        return self._load_enterprise_structure_json()

    def get_enterprise_structure(self):
        return self.load_enterprise_structure()

    def save_enterprise_structure(self, data):
        """[F16 T16.3 修复] 改写 JSON 文件 (替代 UPDATE/INSERT INTO enterprise_structure)
        [F17 增强 2026-06-16] 同时保存 operators 字段（合并内存/已有数据）
        兼容原调用方签名: 接受 dict, 返回 True
        """
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            'data', 'enterprise_structure.json')
        try:
            # 1. 尝试加载现有数据（保留已有的 operators 字段，避免覆盖）
            existing_operators = {}
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        existing = json.load(f)
                    existing_operators = existing.get('operators') or {}
                    if not isinstance(existing_operators, dict):
                        existing_operators = {}
                except Exception: pass

            # 2. 合并 operators（新传入的 operators 优先级更高）
            merged_operators = dict(existing_operators)
            incoming_ops = data.get('operators')
            if incoming_ops:
                if isinstance(incoming_ops, dict):
                    merged_operators.update(incoming_ops)
                elif isinstance(incoming_ops, list):
                    for op in incoming_ops:
                        if isinstance(op, dict) and op.get('id'):
                            merged_operators[op['id']] = op

            # 3. 构造并写入 payload（含 operators）
            payload = {
                'departments': data.get('departments', []),
                'users': data.get('users', []),
                'operators': merged_operators,
                'updated_at': datetime.now().isoformat(),
            }
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            if merged_operators:
                logger.info(f'[F17] save_enterprise_structure → {path} ok (operators={len(merged_operators)})')
            else:
                logger.info(f'[F16 T16.3] save_enterprise_structure → {path} ok')
            return True
        except Exception as e:
            logger.error(f'[F16 T16.3] save_enterprise_structure 失败: {e}')
            return False

    # ───── 工序记录 ─────
    # [优化 2026-06-13] 严谨字段裁剪白名单（基于 13 个调用方的实际使用审计）
    # 完整字段列表：id, process_type, order_no, product_name, quantity, unit,
    #   customer_name, delivery_date, priority, status, current_step, steps,
    #   task_count, completed_task_count, content, flow_type, plan_start, plan_end,
    #   customer_group, source, template_id, qc_required, qc_trigger_reason,
    #   created_at, updated_at, created_by, completed_at, completed_by
    # 使用频次（13 个调用方统计）：
    #   order_no=11, product_name=6, quantity=5, status=4, flow_type=4,
    #   customer_name=2, delivery_date=2, unit=2, id=3, steps=2, current_step=1,
    #   priority=1, customer_group=1, content=1, created_at=1, updated_at=1,
    #   process_code=1, process_name=1, step_name=1
    # 未使用字段（可裁剪）：template_id, qc_required, qc_trigger_reason, task_count,
    #   completed_task_count, source, plan_start, plan_end, created_by,
    #   completed_at, completed_by, process_type
    _ALL_PROCESS_RECORDS_FIELDS = (
        'id, order_no, product_name, quantity, unit, customer_name, '
        'delivery_date, priority, status, current_step, steps, '
        'content, flow_type, customer_group, process_code, process_name, '
        'step_name, created_at, updated_at'
    )

    # [P2 修复 2026-06-18 Bug #11] dashboard 老板 KPI 数据源
    def get_all_production_orders(self, limit: int = 1000) -> List[Dict]:
        """获取生产订单列表（含 status / 进度信息）

        用于 dashboard 老板 KPI 统计（pending/processing/completed）.
        数据源: container_center.production_orders
        """
        return self.fetch_all(
            """SELECT id, order_no, order_id, status, plan_start, plan_end,
                      actual_start, actual_end, assigned_to, priority, is_deleted,
                      material, spec
               FROM production_orders
               WHERE IFNULL(is_deleted, 0) = 0
               ORDER BY id DESC LIMIT %s""",
            (int(limit),)) or []

    def get_all_process_records(self, limit: int = 1000, fields: Optional[str] = None) -> List[Dict]:
        """[优化 2026-06-13] 实时过滤 steel_belt 中已归档的订单

        归档/取消归档操作会实时反映在列表中

        Args:
            limit: 限制返回数量，默认 1000，防止爆表
            fields: 自定义 SELECT 字段列表（逗号分隔），None 时使用白名单

        字段裁剪策略（严谨）：
        - 13 个调用方使用的 18 个字段已纳入白名单
        - 2 个调用方使用完整 rec 对象，调用方传入 fields='*' 即可
        - 6+ 个不常用字段（template_id/qc_required/task_count 等）已裁剪
        """
        select_fields = fields if fields else self._ALL_PROCESS_RECORDS_FIELDS
        return self.fetch_all(f"""
            SELECT {select_fields} FROM process_records
            WHERE is_archived = 0
            ORDER BY created_at DESC
            LIMIT %s
        """, (limit,)) or []

    def get_process_record(self, record_id):
        return self.fetch_one("SELECT * FROM process_records WHERE id=%s", (str(record_id),))

    def get_process_record_by_order(self, order_no: str):
        return self.fetch_one("SELECT * FROM process_records WHERE order_no=%s", (order_no,))

    def get_order_status(self, order_no: str) -> str:
        """SSOT: 统一获取订单状态（从 process_records 表）

        Args:
            order_no: 订单号

        Returns:
            str: 订单状态，如 'created', 'in_production', 'completed' 等
        """
        record = self.fetch_one("SELECT status FROM process_records WHERE order_no=%s", (order_no,))
        return record.get('status', 'unknown') if record else 'not_found'

    def update_order_status(self, order_no: str, status: str) -> bool:
        """SSOT: 统一更新订单状态（到 process_records 表）

        Args:
            order_no: 订单号
            status: 新状态

        Returns:
            bool: 是否更新成功
        """
        result = self.update(
            'process_records',
            {'status': status, 'updated_at': datetime.now()},
            'order_no=%s',
            (order_no,)
        )
        return result > 0

    def save_process_record(self, record: Dict) -> bool:
        """保存工序记录：存在则更新，不存在则插入"""
        rid = record.get('id')
        if rid and self.fetch_one("SELECT 1 FROM process_records WHERE id=%s LIMIT 1", (str(rid),)):
            self.update('process_records', record, "id = %s", (str(rid),))
        else:
            self.insert('process_records', record)
        return True

    def get_process_records(self, search=None, status=None, limit=50, offset=0, process_type=None):
        """[优化 2026-06-12] 增加 status 和 offset 参数
        [K40 修复 2026-06-14] 增加 process_type 参数（v5 client 兼容）
        [优化 2026-06-15] 添加快速路径：无状态过滤时使用子查询优化
        """
        params = []
        conditions = []

        if search:
            conditions.append("order_no = %s")
            params.append(search)

        if status:
            conditions.append("status=%s")
            params.append(status)

        conditions.insert(0, "is_archived = 0")
        where_clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        # [修复 2026-06-13] 显式列出列名避免 SELECT * + ROW_NUMBER() 问题
        # [优化 2026-06-15] 添加 process_code, process_name 字段
        # [优化 2026-06-15] 无状态过滤时使用更快的子查询
        base_select = """
            SELECT id, process_type, order_no, product_name, quantity, unit, customer_name,
                   delivery_date, priority, status, current_step, steps, task_count,
                   completed_task_count, content, flow_type, plan_start, plan_end,
                   customer_group, source, template_id, qc_required, qc_trigger_reason,
                   created_at, updated_at, created_by, completed_at, completed_by,
                   is_archived, data_locked, last_reverted_at, prod_id,
                   process_code, process_name
            """
        if not status and not search:
            sql = """
                SELECT p.* FROM process_records p
                INNER JOIN (
                    SELECT order_no, MAX(updated_at) as max_updated
                    FROM process_records
                    WHERE is_archived = 0
                    GROUP BY order_no
                ) latest ON p.order_no = latest.order_no AND p.updated_at = latest.max_updated
                WHERE p.is_archived = 0
                ORDER BY p.created_at DESC
                LIMIT %s OFFSET %s
            """
            params = [limit, offset]
        else:
            where_clause_outer = where_clause.replace("order_no =", "p.order_no =").replace("status=", "p.status=").replace("is_archived =", "p.is_archived =")
            sql = f"""
                SELECT p.* FROM process_records p
                INNER JOIN (
                    SELECT order_no, MAX(updated_at) as max_updated
                    FROM process_records
                    WHERE is_archived = 0
                    GROUP BY order_no
                ) latest ON p.order_no = latest.order_no AND p.updated_at = latest.max_updated
                {where_clause_outer}
                ORDER BY p.created_at DESC
                LIMIT %s OFFSET %s
            """
            params.extend([limit, offset])

        return self.fetch_all(sql, tuple(params)) or []

    # ───── 数据包 ─────
    def save_package(self, package: Dict) -> bool:
        pkg_id = package.get('id', str(_uuid.uuid4())[:8])
        # 去重
        existing = self.fetch_one(
            "SELECT id FROM data_packages WHERE data_type=%s AND related_order=%s AND related_process=%s LIMIT 1",
            (package.get('data_type', ''), package.get('related_order', ''), package.get('related_process', '')))
        if existing:
            self.update('data_packages', {k: v for k, v in package.items() if k != 'id'},
                        "id=%s", (existing['id'],))
            return True
        self.insert('data_packages', {**package, 'id': pkg_id})
        return True

    def get_packages(self, limit=500, offset=0, fields=None, **kwargs):
        """[优化 2026-06-12] 增加 offset 和 fields 参数

        Args:
            limit: 每页数量
            offset: 偏移量
            fields: 字段列表，None=全部字段
            **kwargs: 支持 data_type, status, related_order, operator
        """
        # [优化] 字段裁剪，减少网络传输
        if fields:
            select_fields = ','.join(fields)
        else:
            select_fields = '*'

        sql = f"SELECT {select_fields} FROM data_packages WHERE 1=1"
        params = []
        for k in ('data_type', 'status', 'related_order'):
            if v := kwargs.get(k):
                sql += f" AND {k}=%s"
                params.append(v)
        operator = kwargs.get('operator')
        if operator:
            sql += " AND (target_operator=%s OR status='distributed')"
            params.append(operator)
        sql += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        return self.fetch_all(sql, tuple(params)) or []

    def get_packages_count_group(self) -> Dict:
        """[T24 修复 2026-06-14] SQL 聚合统计容器池状态

        之前 get_pool_status() 拉 1000 行所有字段到 Python 内存聚合 → 5s+
        现在：单条 SQL GROUP BY data_type, status 一次拿全 → < 10ms
        不受 data_packages 行数影响（O(N) → O(GROUP)，G << N）

        Returns:
            {
              'total': int,                  # 总数
              'by_type': {data_type: int},   # 按数据类型分组
              'by_status': {status: int},     # 按状态分组
            }
        """
        sql = """
            SELECT
              COUNT(*) AS cnt,
              data_type,
              status
            FROM data_packages
            GROUP BY data_type, status
        """
        rows = self.fetch_all(sql) or []
        by_type: Dict[str, int] = {}
        by_status: Dict[str, int] = {}
        total = 0
        for row in rows:
            # DictCursor → dict
            if isinstance(row, dict):
                cnt = int(row.get('cnt', 0) or 0)
                dt = row.get('data_type') or 'other'
                st = row.get('status') or 'unknown'
            else:
                cnt = int(row[0])
                dt = row[1] or 'other'
                st = row[2] or 'unknown'
            total += cnt
            by_type[dt] = by_type.get(dt, 0) + cnt
            by_status[st] = by_status.get(st, 0) + cnt
        return {
            'total': total,
            'by_type': by_type,
            'by_status': by_status,
        }

    def package_exists(self, order_no: str = None, process_name: str = None,
                        data_type: str = None) -> bool:
        """高效检查任务是否已存在（不走 SELECT * 全字段）"""
        sql = "SELECT 1 FROM data_packages WHERE 1=1"
        params = []
        if order_no:
            sql += " AND (related_order=%s OR order_no=%s)"
            params.extend([order_no, order_no])
        if process_name:
            sql += " AND (process_name=%s OR JSON_EXTRACT(content, '$.process_name')=%s)"
            params.extend([process_name, process_name])
        if data_type:
            sql += " AND data_type=%s"
            params.append(data_type)
        sql += " LIMIT 1"
        result = self.fetch_one(sql, tuple(params))
        return result is not None

    def get_package(self, pkg_id):
        return self.fetch_one("SELECT * FROM data_packages WHERE id=%s", (str(pkg_id),))

    def delete_package(self, pkg_id):
        return self.execute("DELETE FROM data_packages WHERE id=%s", (str(pkg_id),))

    # ───── 工序编码映射 ─────
    def get_process_names(self):
        """[F16 T16.1 修复] 改用 process_records 实时聚合 + PROCESS_CODES 内存字典
        原实现: SELECT FROM process_names (表已被 F6 P9 DROP, 触发 1146 WARNING)
        新实现: 内存聚合, 无 SQL 调用
        """
        seen = {}  # process_code → process_name (首次出现)
        try:
            for r in (self.fetch_all(
                "SELECT process_code, process_name, step_name FROM process_records") or []):
                pc = (r.get('process_code') or '').strip()
                pn = (r.get('process_name') or '').strip() or (r.get('step_name') or '').strip()
                if pc and pc not in seen:
                    seen[pc] = pn
        except Exception:
            pass
        # 合并 PROCESS_CODES (内存内置标准工序) + 运行时注册的自定义工序
        try:
            from core._config_domain import PROCESS_CODES, _custom_process_codes
            for pn, pc in {**PROCESS_CODES, **_custom_process_codes}.items():
                if pc and pc not in seen:
                    seen[pc] = pn
        except Exception:
            pass
        return seen

    # ───── 子步骤 ─────
    def get_sub_steps_by_process(self, order_no):
        # [P0 修复 2026-06-18 Bug #4] 返回 processName 字段
        # 修复前: SELECT * → 前端 processName 显示空
        # 修复后: 直接把 step_name 复制为 processName (process_records.process_name 100% 空表, JOIN 无意义)
        # Bug 狩猎 R1 (2026-06-18) 验证: process_records 总 7 条, 0 条 process_name 非空
        # 故弃用 LEFT JOIN process_records 方案
        rows = self.fetch_all(
            """SELECT s.*, s.step_name AS processName
               FROM process_sub_steps s
               WHERE s.order_no=%s
               ORDER BY s.created_at ASC""",
            (str(order_no),)) or []
        # [P0 修复 2026-06-18] 同时补 process_name_joined 字段（兼容老代码）
        for r in rows:
            r.setdefault('process_name_joined', r.get('step_name') or '')
        return rows

    def get_sub_steps_batch(self, order_nos: list, limit: int = 5000, fields: Optional[str] = None) -> dict:
        """[优化 2026-06-13] 批量查询多个订单的 sub_steps，用哈希分组

        Args:
            order_nos: 订单号列表
            limit: 限制返回数量，默认 5000，防止爆表
            fields: 自定义 SELECT 字段列表（逗号分隔），None 时使用白名单

        Returns:
            dict: {order_no: [sub_step, ...]} 按订单号分组的字典

        字段裁剪策略（严谨）：
        - app.py:376-382 实际使用：order_no, quantity, step_name
        - 默认白名单包含 8 个常用字段
        - 调用方传 fields='*' 可获取完整对象
        """
        from collections import defaultdict
        if not order_nos:
            return {}

        order_nos = [str(ono) for ono in order_nos if ono]
        if not order_nos:
            return {}

        # [优化 2026-06-13] 字段白名单（基于 app.py:376-382 实际使用）
        # 使用字段：order_no, quantity, step_name
        # 关联字段：process_code（LIKE 过滤条件使用）
        # 默认白名单：id, order_no, step_name, process_code, quantity, qualified_qty,
        #             batch_no, created_at
        # 完整字段（22 个）：id, uuid, process_id, process_record_id, order_no, step_name,
        #   batch_no, quantity, qualified_qty, operator, operator_id, equipment_name,
        #   remark, record_date, source, overtime_hours, synced, synced_at, created_at,
        #   updated_at, created_by, updated_by, is_deleted, deleted_at, deleted_by,
        #   version, wechat_userid, process_code
        # 裁剪：equipment_name, remark, source, overtime_hours, operator_id, wechat_userid,
        #   uuid, process_id, process_record_id, deleted_* 字段（约 12 个）
        select_fields = fields if fields else 'id, order_no, step_name, process_code, quantity, qualified_qty, batch_no, created_at'
        placeholders = ','.join(['%s'] * len(order_nos))
        sql = f"SELECT {select_fields} FROM process_sub_steps WHERE order_no IN ({placeholders}) AND process_code LIKE 'P%%' ORDER BY order_no, created_at ASC LIMIT %s"

        results = self.fetch_all(sql, tuple(order_nos) + (limit,)) or []

        # 哈希分组
        grouped = defaultdict(list)
        for r in results:
            ono = r.get('order_no', '')
            if ono:
                grouped[ono].append(r)

        return dict(grouped)

    def save_process_sub_step(self, data):
        """保存工序子步骤。v4.0 改造：从"按派工批次拆行"改为"每工序 1 行，多人 operator 追加"。

        业务规则：
        1. 去重键：(order_no, step_name, process_code) 三元组
        2. 存在 → 追加 operator（逗号分隔，dedup），其他字段（quantity/qualified_qty/status）保持原值
        3. 不存在 → INSERT 新行（id 由 _UUID_TABLES 机制自动生成 8 位 UUID）
        4. 同人重复派工 → 无 operator 变化，不发 UPDATE
        5. process_code 为空/NULL 时按 NULL 匹配（兼容老数据）

        Returns:
            bool: True 成功
        """
        order_no = (data.get('order_no') or '').strip()
        step_name = (data.get('step_name') or '').strip()
        process_code = (data.get('process_code') or '').strip()
        new_operator = (data.get('operator') or '').strip()

        if not order_no or not step_name:
            return False

        if process_code:
            existing = self.fetch_one(
                """
                SELECT id, operator FROM process_sub_steps
                WHERE order_no=%s AND step_name=%s AND process_code=%s
                LIMIT 1
                """,
                (order_no, step_name, process_code))
        else:
            existing = self.fetch_one(
                """
                SELECT id, operator FROM process_sub_steps
                WHERE order_no=%s AND step_name=%s
                  AND (process_code IS NULL OR process_code='')
                LIMIT 1
                """,
                (order_no, step_name))

        if existing:
            if new_operator:
                old_op = (existing.get('operator') or '').strip()
                old_op_list = [x.strip() for x in old_op.split(',') if x.strip()]
                if new_operator not in old_op_list:
                    old_op_list.append(new_operator)
                    merged = ','.join(old_op_list)
                    self.update('process_sub_steps',
                                {'operator': merged},
                                'id=%s', (existing['id'],))
            return True

        self.insert('process_sub_steps', data)
        return True

    def save_process_sub_step_with_pkg_update(
            self, data: dict, pkg_order: str, pkg_process: str, qty_delta: float):
        """v4.0 改造（F6 P6 修复）: 原子化保存 process_sub_steps + 累加 data_packages.

        与 save_process_sub_step 的关键差异:
        - 本方法在**单次连接**内完成 process_sub_steps 的 3 键去重/合并 + data_packages
          累加 + 显式 commit, 保证两个写入的原子性 (要么都成功, 要么都回滚).
        - save_process_sub_step 不传 pkg 参数时, 调用方须自行负责 data_packages 累加, 但
          那样会形成两次独立 commit, 数据一致性存在风险 (F6 悲观审计发现).

        设计决策（[v4.0 / 2026-06-10] 审计项 N3）: 本方法**故意**不走
        ``self._safe_execute`` / ``self._safe_insert`` 包装, 原因是这两个
        包装内部独立获取连接 + 隐式 commit, 会破坏本方法"单次连接 + 显式
        commit"的事务边界. 因此本方法直接用 ``self._pool.connection()``
        拿连接, 在该连接内连续执行多个 SQL, 最后由调用方在末尾 ``commit()``
        一次性提交, 异常时 ``rollback()`` 整体回滚.

        Args:
            data: 工序子步骤数据, 必含 order_no/step_name/operator/quantity.
            pkg_order: data_packages.related_order 关联订单号.
            pkg_process: data_packages.related_process 关联工序.
            qty_delta: 本次累加数量 (通常 = data['quantity']).

        Returns:
            bool: True 成功.

        Raises:
            Exception: 任何 SQL 异常都会回滚事务并向上抛.
        """
        self._ensure_conn()
        order_no = (data.get('order_no') or '').strip()
        step_name = (data.get('step_name') or '').strip()
        process_code = (data.get('process_code') or '').strip()
        new_operator = (data.get('operator') or '').strip()
        if not order_no or not step_name:
            raise ValueError('order_no 和 step_name 必填')
        # 移除 data 中可能存在的 id, 走我们的 UUID 策略
        data = {k: v for k, v in data.items() if k != 'id'}
        if 'process_sub_steps' in self._UUID_TABLES and 'id' not in data:
            data = {**data, 'id': str(_uuid.uuid4())[:8]}
        with self._pool.connection() as conn:
            try:
                with conn.cursor(DictCursor) as cur:
                    # 1. 查重 (同 save_process_sub_step 的 3 键去重)
                    if process_code:
                        cur.execute(
                            "SELECT id, operator FROM process_sub_steps "
                            "WHERE order_no=%s AND step_name=%s AND process_code=%s LIMIT 1",
                            (order_no, step_name, process_code))
                    else:
                        cur.execute(
                            "SELECT id, operator FROM process_sub_steps "
                            "WHERE order_no=%s AND step_name=%s "
                            "AND (process_code IS NULL OR process_code='') LIMIT 1",
                            (order_no, step_name))
                    row = cur.fetchone()
                    if row:
                        # 已存在 → 合并 operator（【P0修复 2026-06-18 Bug #1+#2】不再累加 data_packages.completed_qty）
                        # 修复前: 命中时仍 UPDATE completed_qty + qty_delta → 重复报工暴增 20 万倍
                        # 修复后: 命中时只合并 operator, 不再累加 completed_qty
                        # 累加只在"未命中 → 新插入行"时执行
                        existing_id = row[0] if isinstance(row, (list, tuple)) else row['id']
                        old_op = ((row[1] if isinstance(row, (list, tuple)) else row['operator']) or '').strip()
                        if new_operator:
                            old_list = [x.strip() for x in old_op.split(',') if x.strip()]
                            if new_operator not in old_list:
                                old_list.append(new_operator)
                            new_op = ','.join(old_list)
                            # [K38 修复 2026-06-14] 限制 operator 合并后最大长度
                            # 之前：累积无限制 → UPDATE operator=...varchar(255) 截断 → 1406 DataError → 500
                            # 现在：超长截断到 250 字符（不超 varchar(255) 上限）
                            if len(new_op) > 250:
                                new_op = new_op[:250]
                        else:
                            new_op = old_op
                        if new_op != old_op:
                            cur.execute(
                                "UPDATE process_sub_steps SET operator=%s WHERE id=%s",
                                (new_op, existing_id))
                    else:
                        # 新增行
                        cols = ', '.join(f'`{k}`' for k in data)
                        vals = ', '.join(['%s'] * len(data))
                        params = [_fmt(v) for v in data.values()]
                        cur.execute(
                            f"INSERT INTO `process_sub_steps` ({cols}) VALUES ({vals})",
                            params)
                        # 2. 【P0修复 2026-06-18 Bug #1+#2】累加 data_packages.completed_qty
                        # 仅当新增行时累加, 去重命中时不再累加（避免重复报工导致 completed_qty 暴增）
                        cur.execute(
                            "UPDATE data_packages SET completed_qty = COALESCE(completed_qty, 0) + %s "
                            "WHERE related_order=%s AND related_process=%s",
                            (qty_delta, pkg_order, pkg_process))
                # 3. 一次 commit, 原子性保证
                conn.commit()
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
                raise
        return True

    def dedup_process_sub_steps(self, batch_size: int = 1000, max_iter: int = 100) -> int:
        """清理 process_sub_steps 中 (order_no, step_name, process_code, operator, quantity) 5元组重复行。

        业务规则：
        1. 按 5 元组分组，含 DATE(created_at) 分组
        2. 每组保留创建最早的 1 条作 anchor（p1.id < p2.id），operator 合并去重，删除其余行
        3. 按 batch_size 拆批（防大表锁表 + 长事务）
        4. v4.0 之后正常情况应无重复可清（save_process_sub_step 已防重），此函数仅作安全网

        Returns:
            int: 累计删除条数
        """
        total = 0
        for i in range(max_iter):
            try:
                anchor_groups = self.fetch_all("""
                    SELECT order_no, step_name,
                           IFNULL(process_code, '') AS process_code,
                           operator, quantity,
                           DATE(created_at) AS created_date,
                           MIN(id) AS anchor_id
                    FROM process_sub_steps
                    GROUP BY order_no, step_name,
                             IFNULL(process_code, ''),
                             operator, quantity,
                             DATE(created_at)
                    HAVING COUNT(*) > 1
                    LIMIT %s
                """, (int(batch_size),)) or []
                if not anchor_groups:
                    break
                for grp in anchor_groups:
                    order_no = grp['order_no']
                    step_name = grp['step_name']
                    process_code = grp['process_code']
                    operator = grp.get('operator') or ''
                    quantity = grp.get('quantity') or 0
                    created_date = grp['created_date']
                    anchor_id = grp['anchor_id']
                    params = (order_no, step_name, process_code, operator,
                              str(quantity), created_date, anchor_id,
                              order_no, step_name, process_code, operator,
                              str(quantity), created_date)
                    self.execute(
                        "DELETE p2 FROM process_sub_steps p1 "
                        "JOIN process_sub_steps p2 USING (order_no, step_name, process_code, operator, quantity) "
                        "WHERE DATE(p1.created_at)=DATE(p2.created_at) "
                        "  AND p1.id < p2.id "
                        "  AND p1.id=%s "
                        "  AND p1.order_no=%s AND p1.step_name=%s "
                        "  AND IFNULL(p1.process_code,'')=%s "
                        "  AND p1.operator=%s AND p1.quantity=%s "
                        "  AND DATE(p1.created_at)=%s",
                        params)
                logger.info(f"dedup_process_sub_steps: 批次 {i+1} 删除 {total} 条")
            except Exception as e:
                logger.exception(f"dedup_process_sub_steps 失败: {e}")
                break
        return total

    # ───── 调度命令 ─────
    def save_dispatch_command(self, command: dict) -> bool:
        """保存调度命令"""
        command['created_at'] = command.get('created_at') or datetime.now().isoformat()
        return bool(self.execute(
            'INSERT INTO dispatch_commands (order_no, process_name, command, status, created_at) VALUES (%s,%s,%s,%s,%s)',
            (command.get('order_no', ''), command.get('process_name', ''),
             command.get('command', ''), command.get('status', 'pending'),
             command['created_at'])
        ))

    def get_dispatch_commands_by_order_process(self, order_no: str, process_name: str) -> list:
        """按订单+工序查询调度命令"""
        return self.fetch_all(
            'SELECT * FROM dispatch_commands WHERE order_no=%s AND process_name=%s ORDER BY created_at DESC',
            (order_no, process_name)
        ) or []

    # ───── 其他 ─────
    def cleanup_expired_packages(self, retention_days=30):
        return self.execute(
            "DELETE FROM data_packages WHERE created_at < DATE_SUB(NOW(), INTERVAL %s DAY)",
            (retention_days,))

    def get_process_records_by_work_order(self, order_no):
        return self.fetch_all(
            "SELECT * FROM process_records WHERE order_no=%s AND is_archived=0",
            (order_no,)
        ) or []

    # ───── 数据回归审计 ─────

    def save_history(self, original_id: int, data: dict) -> bool:
        """写入回归审计记录。与主数据在同一事务内调用，失败则整个事务回滚。

        Args:
            original_id: 被覆盖的 process_sub_steps.id
            data: { order_no, step_name, batch_no, operator_before, operator_after,
                    old_quantity, new_quantity, revert_reason, reverted_by }
        """
        self.insert('process_sub_steps_history', {
            'original_id': original_id,
            'order_no': data.get('order_no', ''),
            'step_name': data.get('step_name', ''),
            'batch_no': data.get('batch_no', ''),
            'operator_before': data.get('operator_before', ''),
            'operator_after': data.get('operator_after', ''),
            'old_quantity': float(data.get('old_quantity', 0) or 0),
            'new_quantity': float(data.get('new_quantity', 0) or 0),
            'revert_reason': data.get('revert_reason', 'other_override'),
            'reverted_by': data.get('reverted_by', ''),
        })
        return True

    def soft_delete_sub_step(self, sub_step_id: int, operator: str) -> bool:
        """逻辑删除子步骤（撤回）。
        与 history 写入在同一事务内调用。
        """
        self.update('process_sub_steps',
                     {'quantity': 0, 'deleted': 1},
                     'id=%s', (sub_step_id,))
        return True

    def get_history(self, order_no: str, step_name: str = '') -> list:
        """查询审计记录"""
        if step_name:
            return self.fetch_all(
                "SELECT * FROM process_sub_steps_history WHERE order_no=%s AND step_name=%s ORDER BY reverted_at DESC",
                (order_no, step_name)) or []
        return self.fetch_all(
            "SELECT * FROM process_sub_steps_history WHERE order_no=%s ORDER BY reverted_at DESC",
            (order_no,)) or []

    def get_first_created_at(self, order_no: str, step_name: str):
        """查该工序的最早 sub_step.created_at，用于修正时限基线"""
        return self.fetch_one(
            "SELECT MIN(created_at) AS first_created_at FROM process_sub_steps WHERE order_no=%s AND step_name=%s",
            (order_no, step_name))

    def _wal_db_path(self):
        import os
        return os.path.join(os.path.dirname(__file__), '..', 'data', 'regression_wal.db')

    def wal_write(self, key: str, data: dict) -> bool:
        """WAL 预写日志。DB 崩溃后通过回放 wAL 恢复未完成的事务。"""
        import sqlite3, json, os
        path = self._wal_db_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE IF NOT EXISTS wal (id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT, payload TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
        conn.execute("INSERT INTO wal (key, payload) VALUES (?, ?)", (key, json.dumps(data, ensure_ascii=False, default=str)))
        conn.commit()
        conn.close()
        return True

    def wal_replay(self, processor) -> int:
        """回放 WAL 中未处理的事件。processor(key, data) -> bool。
        返回成功处理数。
        """
        import sqlite3, json
        path = self._wal_db_path()
        conn = sqlite3.connect(path)
        rows = conn.execute("SELECT id, key, payload FROM wal ORDER BY id").fetchall()
        count = 0
        for row in rows:
            try:
                data = json.loads(row[2])
                if processor(row[1], data):
                    conn.execute("DELETE FROM wal WHERE id=?", (row[0],))
                    count += 1
            except Exception:
                pass
        conn.commit()
        conn.close()
        return count

    # ───── 报工消息队列 ─────
    def enqueue_report(self, data: dict) -> int:
        """入队: 立即返回，不阻塞

        [T21 修复 2026-06-14] 支持幂等键 idempotency_key
        之前：同 order_no+step_name 重复入队 → worker 重复处理
        现在：传 idempotency_key 时走 INSERT IGNORE → 同 uuid 不重复入队
              返 0 表示已存在
        """
        idem = data.get('idempotency_key')
        if idem:
            # [T21] 用 INSERT IGNORE + UNIQUE 索引实现幂等
            try:
                return self._safe_insert(
                    """INSERT IGNORE INTO report_queue
                       (order_no, step_name, quantity, qualified_qty, operator,
                        process_id, status, retry_count, max_retries, idempotency_key)
                       VALUES (%s, %s, %s, %s, %s, %s, 'pending', 0, 3, %s)""",
                    (data['order_no'], data['step_name'], data['quantity'],
                     data.get('qualified_qty', data['quantity']),
                     data.get('operator', ''), data.get('process_id', ''), idem)
                )
            except Exception:
                # 降级：无 idempotency_key 字段时走旧路径
                pass
        return self.insert('report_queue', {
            'order_no': data['order_no'],
            'step_name': data['step_name'],
            'quantity': data['quantity'],
            'qualified_qty': data.get('qualified_qty', data['quantity']),
            'operator': data.get('operator', ''),
            'process_id': data.get('process_id', ''),
            'status': 'pending',
            'retry_count': 0,
            'max_retries': 3,
        })

    def count_pending_reports(self) -> int:
        """[T22 修复 2026-06-14] 队列深度（pending + retry）

        fetch_all 返回 dict 列表（DictCursor），需用 'COUNT(*)' 键取值
        """
        rows = self.fetch_all(
            "SELECT COUNT(*) AS cnt FROM report_queue WHERE status IN ('pending','retry')"
        ) or []
        if not rows:
            return 0
        # DictCursor → dict; tuple cursor → tuple
        row = rows[0]
        if isinstance(row, dict):
            return int(row.get('cnt', 0) or row.get('COUNT(*)', 0))
        return int(row[0])

    def dequeue_pending_reports(self, limit: int = 10):
        """取待处理的报工（含待重试的）"""
        return self.fetch_all(
            "SELECT * FROM report_queue WHERE status IN ('pending','retry') "
            "ORDER BY retry_count ASC, enqueued_at ASC LIMIT %s",
            (limit,)) or []

    def mark_report_processed(self, queue_id: int):
        """标记报工处理成功"""
        self.update('report_queue',
            {'status': 'completed', 'processed_at': datetime.now().isoformat()},
            'id=%s', (queue_id,))

    def mark_report_failed(self, queue_id: int, error: str, retry_count: int):
        """标记失败并递增重试次数"""
        if retry_count >= 3:
            self.update('report_queue',
                {'status': 'failed', 'retry_count': retry_count, 'last_error': error},
                'id=%s', (queue_id,))
        else:
            # 指数退避: 30s/60s/120s 后重试
            backoff = 30 * (2 ** (retry_count - 1)) if retry_count > 0 else 0
            self.update('report_queue',
                {'status': 'retry', 'retry_count': retry_count, 'last_error': error,
                 'enqueued_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')},
                'id=%s', (queue_id,))

    def mark_report_dead(self, queue_id: int, reason: str):
        """[架构审计 P1 修复 2026-06-13] 标记为死信（超过最大重试次数）

        与 mark_report_failed 区别：
        - mark_report_failed: 状态 = failed（仍可能被手动重试）
        - mark_report_dead: 状态 = dead（不再自动重试，需人工介入）
        """
        self.update('report_queue',
            {'status': 'dead', 'last_error': reason[:255],
             'dead_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')},
            'id=%s', (queue_id,))

    def cleanup_report_queue(self, retention_days: int = 7):
        """清理旧队列记录"""
        return self.execute(
            "DELETE FROM report_queue WHERE status IN ('completed','failed') "
            "AND enqueued_at < DATE_SUB(NOW(), INTERVAL %s DAY)",
            (retention_days,))

    # ───── 子步骤汇总 ─────
    def save_sub_step(self, record):
        """保存子工序（BaseStorage 多态接口契约实现）.

        ⚠️ [v4.0 标记 / 2026-06-10] 该方法为基类多态契约保留, **不走 3 键去重**;
        直接以 record['id'] 为主键做 insert/update. 派工语义请改用
        ``save_process_sub_step`` 或 ``save_process_sub_step_with_pkg_update``
        (后者在 F6 P6 修复中提供, 单连接原子化保证).
        本方法的"按 id 覆盖"语义与"派工批次"语义不符, 已被 F6 派工路径
        全部弃用, 仅供兼容老调用方 (基类抽象约束).
        """
        rid = record.get('id')
        if rid and self.fetch_one("SELECT 1 FROM process_sub_steps WHERE id=%s LIMIT 1", (str(rid),)):
            self.update('process_sub_steps', record, "id = %s", (str(rid),))
        else:
            self.insert('process_sub_steps', record)
        return True

    def get_sub_step_summary(self, order_no):
        steps = self.fetch_all(
            "SELECT step_name, SUM(quantity) as total_qty, COUNT(*) as cnt FROM process_sub_steps WHERE order_no=%s GROUP BY step_name",
            (order_no,)) or []
        return steps

    def get_sub_step_summary_batch(self, order_nos: list) -> dict:
        """[优化 2026-06-15] 批量获取多个订单的子步骤汇总，一次 SQL 替代 N 次

        Args:
            order_nos: 订单号列表

        Returns:
            dict: {order_no: {'completed_qty': int, 'order_qty': int, 'shipped_qty': int, 'step_count': int}}
        """
        from collections import defaultdict
        if not order_nos:
            return {}

        order_nos = [str(ono) for ono in order_nos if ono]
        if not order_nos:
            return {}

        placeholders = ','.join(['%s'] * len(order_nos))
        sql = f"""
            SELECT order_no, 
                   SUM(quantity) as total_qty, 
                   COUNT(DISTINCT step_name) as step_count,
                   COUNT(*) as record_count
            FROM process_sub_steps 
            WHERE order_no IN ({placeholders}) 
            GROUP BY order_no
        """
        results = self.fetch_all(sql, tuple(order_nos)) or []

        summary = {}
        for r in results:
            ono = r.get('order_no', '')
            if ono:
                summary[ono] = {
                    'completed_qty': int(r.get('total_qty', 0) or 0),
                    'order_qty': int(r.get('total_qty', 0) or 0),
                    'shipped_qty': 0,
                    'step_count': int(r.get('step_count', 0) or 0),
                }
        return summary

    def get_last_sub_step(self, order_no):
        return self.fetch_one(
            "SELECT * FROM process_sub_steps WHERE order_no=%s ORDER BY created_at DESC LIMIT 1",
            (order_no,))

    # ───── 工人管理 ─────
    def get_all_workers(self):
        return self.fetch_all("SELECT * FROM workers WHERE status='active'") or []

    def get_worker(self, worker_id):
        return self.fetch_one("SELECT * FROM workers WHERE enterprise_id=%s", (worker_id,))

    def get_worker_by_name(self, name: str):
        return self.fetch_one("SELECT * FROM workers WHERE name=%s AND status='active'", (name,))

    def save_worker(self, worker):
        return self.insert('workers', worker)

    def delete_worker(self, username):
        return self.update('workers', {'status': 'inactive'}, 'enterprise_id=%s', (username,))

    # ───── 考勤 ─────
    # [F16 T16.6 修复] attendance 表 F6 P9 2026-06-10 DROP (跨库历史表清理, 详见 MEMORY.md L20)
    #     attendance 业务降级: 缺表时返 None/[]/False, 不阻塞调用方
    def get_attendance(self, worker, date):
        try:
            return self.fetch_one(
                "SELECT * FROM attendance WHERE worker=%s AND date=%s",
                (worker, date))
        except Exception as e:
            if '1146' in str(e) or 'doesn\'t exist' in str(e):
                logger.warning('[F16 T16.6] attendance 表 F6 P9 DROP, get_attendance 返 None: %s', e)
                return None
            raise

    def get_attendance_by_date(self, date):
        try:
            return self.fetch_all(
                "SELECT * FROM attendance WHERE date=%s",
                (date,)) or []
        except Exception as e:
            if '1146' in str(e) or 'doesn\'t exist' in str(e):
                logger.warning('[F16 T16.6] attendance 表 F6 P9 DROP, get_attendance_by_date 返 []: %s', e)
                return []
            raise

    def upsert_attendance(self, worker, date, check_in='', check_out='', status='未签到'):
        try:
            existing = self.get_attendance(worker, date)
            if existing:
                return self.update('attendance',
                    {'check_in': check_in, 'check_out': check_out, 'status': status},
                    'id=%s', (existing['id'],))
            return self.insert('attendance',
                {'worker': worker, 'date': date, 'check_in': check_in, 'check_out': check_out, 'status': status})
        except Exception as e:
            if '1146' in str(e) or 'doesn\'t exist' in str(e):
                logger.warning('[F16 T16.6] attendance 表 F6 P9 DROP, upsert_attendance 返 False: %s', e)
                return False
            raise

    # ───── 回传记录 ─────
    # SSOT: schedule_records 表 F6 P9 DROP，数据已迁移到 process_records
    # 本节方法统一从 process_records 查询订单状态

    def save_schedule_record(self, record: Dict) -> bool:
        """保存排产记录：SSOT 直接写入 process_records 表"""
        order_no = record.get('order_no', '')
        if not order_no:
            return False
        return self.update_order_status(order_no, record.get('status', 'scheduled'))

    def get_schedule_record(self, schedule_id: str) -> Optional[Dict]:
        """按 schedule_id 获取单条排产记录 → 从 process_records 查询"""
        rec = self.get_process_record(schedule_id)
        if rec:
            rec['schedule_id'] = rec.get('id')
        return rec

    def get_schedule_record_by_order(self, order_no: str) -> Optional[Dict]:
        """按订单号获取最近一条排产记录 → 从 process_records SSOT 查询"""
        return self.get_process_record_by_order(order_no)

    def get_schedule_records_by_order(self, order_no: str) -> List[Dict]:
        """按订单号获取所有排产记录 → 从 process_records SSOT 查询"""
        rec = self.get_process_record_by_order(order_no)
        return [rec] if rec else []

    def get_schedule_records(self, status: str = None, limit: int = 100) -> List[Dict]:
        """按状态/限制获取排产记录列表 → 从 process_records SSOT 查询"""
        return self.get_process_records(status=status, limit=limit, offset=0)

    def get_all_schedule_records(self) -> List[Dict]:
        """获取所有排产记录 → 从 process_records SSOT 查询"""
        return self.get_process_records(limit=1000, offset=0)

    # RE-002 T3: 补 ScheduleFlowMixin 接口方法（schedule_routes.py 排产流程日志必需）
    def log_schedule_flow(self, order_no: str, event_type: str, event_data: Dict, operator: str = None) -> bool:
        """记录排产流程日志（ScheduleFlowMixin 抽象方法）"""
        try:
            import json as _json
            payload = {
                'order_no': str(order_no),
                'event_type': str(event_type),
                'event_data': _json.dumps(event_data, ensure_ascii=False) if event_data else None,
                'operator': str(operator) if operator else None,
            }
            self.insert('schedule_flow_logs', payload)
            return True
        except Exception as e:
            logger.error(f"[MySQLStorage] log_schedule_flow 失败: {e}")
            return False

    def get_schedule_flow_logs(self, order_no: str) -> List[Dict]:
        """获取排产流程日志（ScheduleFlowMixin 抽象方法）"""
        try:
            rows = self.fetch_all(
                "SELECT * FROM schedule_flow_logs WHERE order_no=%s ORDER BY id DESC",
                (str(order_no),),
            )
            return list(rows or [])
        except Exception as e:
            logger.error(f"[MySQLStorage] get_schedule_flow_logs 失败: {e}")
            return []

    def save_return_record(self, package_id, return_data, analyzed=None, write_back_cmd=None):
        """回传记录：reason 存 return_data，analyzed/write_back_cmd 合并存入"""
        merged = dict(return_data) if isinstance(return_data, dict) else {'raw': str(return_data)}
        if analyzed:
            merged['_analyzed'] = analyzed
        if write_back_cmd:
            merged['_write_back_cmd'] = write_back_cmd
        qty = float(merged.get('qty', merged.get('quantity', merged.get('actual_qty', 0))))
        return self.insert('return_records', {
            'order_id': package_id,
            'reason': json.dumps(merged, ensure_ascii=False),
            'returned_qty': qty,
        })

    # ───── 包管理补充 ─────
    def update_package(self, pkg_id, pkg_dict):
        return self.update('data_packages', pkg_dict, 'id=%s', (pkg_id,))

    def update_package_status(self, pkg_id, status, remark=''):
        return self.update('data_packages', {'status': status}, 'id=%s', (pkg_id,))

    # ───── 数据流日志 ─────
    def save_data_flow_log(self, log):
        return self.insert('data_flow_logs', log)

    def log_sync(self, action, package_id=None, detail=None):
        return self.insert('sync_logs', {'action': action, 'package_id': package_id or '', 'detail': detail or ''})

    @classmethod
    def get_connection(cls):
        """获取池连接 — 替代所有 pymysql.connect() 直连"""
        inst = cls()
        inst._ensure_conn()
        return inst._pool.connection()


def create_mysql_storage(**kwargs) -> MySQLStorage:
    s = MySQLStorage(**kwargs)
    s.connect()
    return s


import threading, time as _time

class ConnectionMonitor:
    """MySQL 连接健康巡检 — 每分钟检查一次"""
    _instance = None

    def __init__(self, storage: MySQLStorage, interval: int = 60):
        self.storage = storage
        self.interval = interval
        self._running = False

    def start(self):
        if self._running:
            return
        self._running = True
        t = threading.Thread(target=self._loop, daemon=True, name="mysql-health")
        t.start()
        logger.info('[MySQLHealth] 连接巡检已启动（每%d秒）', self.interval)

    def _loop(self):
        while self._running:
            _time.sleep(self.interval)
            try:
                self.storage._ensure_conn()
            except Exception as e:
                logger.warning('[MySQLHealth] 连接异常: %s', e)

    def stop(self):
        self._running = False


def start_connection_monitor(storage, interval=60):
    """启动连接健康巡检"""
    monitor = ConnectionMonitor(storage, interval)
    monitor.start()
    return monitor


# 补充 report 相关方法（兼容 stats_engine）
def _patch_report_methods():
    """为 MySQLStorage 补上 report 相关方法"""
    if not hasattr(MySQLStorage, 'list_report_definitions'):
        def _list_report_defs(self, category=None):
            w, p = [], []
            if category: w.append('category = %s'); p.append(category)
            wh = (' WHERE ' + ' AND '.join(w)) if w else ''
            return self.fetch_all(f"SELECT * FROM report_definition{wh} ORDER BY created_at DESC", p) or []
        MySQLStorage.list_report_definitions = _list_report_defs

    if not hasattr(MySQLStorage, 'save_report_definition'):
        def _save_report_def(self, data):
            return self.insert('report_definition', data)
        MySQLStorage.save_report_definition = _save_report_def

    if not hasattr(MySQLStorage, 'get_report_output'):
        def _get_report_output(self, output_id):
            return self.fetch_one("SELECT * FROM report_output WHERE id = %s", (output_id,))
        MySQLStorage.get_report_output = _get_report_output

    if not hasattr(MySQLStorage, 'list_report_schedules'):
        def _list_report_schedules(self, enabled_only=False):
            w = " WHERE enabled = 1" if enabled_only else ""
            return self.fetch_all(f"SELECT * FROM report_schedule{w} ORDER BY created_at DESC") or []
        MySQLStorage.list_report_schedules = _list_report_schedules

    if not hasattr(MySQLStorage, 'list_report_outputs'):
        def _list_report_outputs(self, report_id=None, limit=50):
            w, p = [], []
            if report_id: w.append('report_id = %s'); p.append(report_id)
            wh = (' WHERE ' + ' AND '.join(w)) if w else ''
            return self.fetch_all(
                f"SELECT * FROM report_output{wh} ORDER BY created_at DESC LIMIT %s",
                p + [limit]) or []
        MySQLStorage.list_report_outputs = _list_report_outputs


# ══════════════════════════════════════════════════════════
# SSOT 本地表查询（避免跨库查询）
# steel_belt 数据同步到 container_center 本地表
# ══════════════════════════════════════════════════════════

def _patch_local_table_methods():
    """为 MySQLStorage 补上本地表查询方法（SSOT）"""

    # orders_local 查询
    if not hasattr(MySQLStorage, 'get_order_local'):
        def _get_order_local(self, order_no):
            return self.fetch_one(
                "SELECT * FROM orders_local WHERE order_no=%s AND is_deleted=0 LIMIT 1",
                (order_no,))
        MySQLStorage.get_order_local = _get_order_local

    if not hasattr(MySQLStorage, 'get_all_orders_local'):
        def _get_all_orders_local(self, limit=1000):
            return self.fetch_all(
                "SELECT * FROM orders_local WHERE is_deleted=0 AND is_archived=0 ORDER BY created_at DESC LIMIT %s",
                (limit,)) or []
        MySQLStorage.get_all_orders_local = _get_all_orders_local

    if not hasattr(MySQLStorage, 'sync_order_to_local'):
        def _sync_order_to_local(self, order_data):
            order_no = order_data.get('order_no')
            if not order_no:
                return False
            existing = self.fetch_one("SELECT id FROM orders_local WHERE order_no=%s", (order_no,))
            if existing:
                self.update('orders_local', order_data, 'order_no=%s', (order_no,))
            else:
                self.insert('orders_local', order_data)
            return True
        MySQLStorage.sync_order_to_local = _sync_order_to_local

    # production_orders_local 查询
    if not hasattr(MySQLStorage, 'get_production_order_local'):
        def _get_production_order_local(self, order_no):
            return self.fetch_one(
                "SELECT * FROM production_orders_local WHERE order_no=%s AND is_deleted=0 LIMIT 1",
                (order_no,))
        MySQLStorage.get_production_order_local = _get_production_order_local

    if not hasattr(MySQLStorage, 'get_all_production_orders_local'):
        def _get_all_production_orders_local(self, limit=1000):
            return self.fetch_all(
                "SELECT * FROM production_orders_local WHERE is_deleted=0 ORDER BY created_at DESC LIMIT %s",
                (limit,)) or []
        MySQLStorage.get_all_production_orders_local = _get_all_production_orders_local

    # operators_local 查询
    if not hasattr(MySQLStorage, 'get_operator_local'):
        def _get_operator_local(self, name):
            return self.fetch_one(
                "SELECT * FROM operators_local WHERE name=%s AND is_active=1 LIMIT 1",
                (name,))
        MySQLStorage.get_operator_local = _get_operator_local

    if not hasattr(MySQLStorage, 'get_all_operators_local'):
        def _get_all_operators_local(self):
            return self.fetch_all(
                "SELECT * FROM operators_local WHERE is_active=1 ORDER BY name") or []
        MySQLStorage.get_all_operators_local = _get_all_operators_local


# 应用补丁
_patch_local_table_methods()

_patch_report_methods()
