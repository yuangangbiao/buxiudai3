# -*- coding: utf-8 -*-
"""
统一配置管理模块
所有配置必须通过此模块访问，严禁硬编码
"""

import os
import sys
import warnings
from pathlib import Path
from typing import Any, Optional
from dotenv import load_dotenv

_env_loaded = False

def load_env() -> bool:
    """加载 .env 环境变量文件（仅执行一次）"""
    global _env_loaded
    if _env_loaded:
        return True

    env_file = BASE_DIR / '.env'
    if env_file.exists():
        load_dotenv(env_file)
        _env_loaded = True
        return True
    return False

# ========== 路径配置 ==========
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CONFIG_DIR = BASE_DIR / "config"
LOG_DIR = BASE_DIR / "logs"

# 加载 .env（必须在 MYSQL_CFG 等配置之前）
load_env()

def get_data_path(filename: str) -> str:
    """获取数据文件路径"""
    return str(DATA_DIR / filename)

def get_config_path(filename: str) -> str:
    """获取配置文件路径"""
    return str(CONFIG_DIR / filename)

def ensure_dir(path: str) -> None:
    """确保目录存在"""
    Path(path).mkdir(parents=True, exist_ok=True)

# ========== 环境变量加载 ==========
ENV_FILE = BASE_DIR / '.env'
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    warnings.warn(f'.env file not found at {ENV_FILE}')

# ========== 数据库配置 ==========
class DatabaseConfig:
    """数据库配置"""

    @classmethod
    def get(cls, key: str, default: str = '') -> str:
        """获取环境变量"""
        return os.getenv(key, default)

    @property
    def HOST(self) -> str:
        return os.getenv('MYSQL_HOST', 'localhost')

    @property
    def PORT(self) -> int:
        return int(os.getenv('MYSQL_PORT', '3306'))

    @property
    def USER(self) -> str:
        return os.getenv('MYSQL_USER', 'root')

    @property
    def PASSWORD(self) -> str:
        return os.getenv('MYSQL_PASSWORD', '')

    @property
    def DATABASE(self) -> str:
        return os.getenv('MYSQL_DATABASE', 'steel_belt')

    @property
    def CHARSET(self) -> str:
        return os.getenv('MYSQL_CHARSET', 'utf8mb4')

    @property
    def MAX_CONNECTIONS(self) -> int:
        return int(os.getenv('MAX_CONNECTIONS', '10'))

    @property
    def MIN_CONNECTIONS(self) -> int:
        return int(os.getenv('MIN_CONNECTIONS', '2'))

    @property
    def CONNECTION_TIMEOUT(self) -> int:
        return int(os.getenv('CONNECTION_TIMEOUT', '30'))

    @property
    def USE_SQLITE(self) -> bool:
        # [审计项 N2 / 2026-06-10] 此处默认 'true' 仅用于 DatabaseConfig 类的 SQLITE_DB_PATH
        # 默认值兜底; 实际生产路径的存储类型由 ``storage_layer.resolve_storage_type()`` 决定,
        # 那里默认走 MySQL (USE_SQLITE 默认 'false'). 两处分层职责不同, 不要混用.
        return os.getenv('USE_SQLITE', 'true').lower() == 'true'

    @property
    def SQLITE_DB_PATH(self) -> str:
        return os.getenv('SQLITE_DB_PATH', str(DATA_DIR / 'steel_belt.db'))

# 立即加载环境变量（已在文件顶部通过 load_dotenv 完成）

# ========== MySQL 连接配置（模块级变量，供兼容存根使用） ==========
MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
MYSQL_USER = os.getenv('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'steel_belt')

# ========== 统一路径/URL/超时配置字典 ==========
DB_PATHS = {
    # === JSON 配置（保留）===
    'dispatch_center_data': os.getenv('DISPATCH_CENTER_DATA_PATH') or str(BASE_DIR / 'mobile_api_ai' / 'dispatch_center_data.json'),
    'enterprise_structure': os.getenv('ENTERPRISE_STRUCTURE_PATH') or str(BASE_DIR / 'mobile_api_ai' / 'data' / 'enterprise_structure.json'),
    'cloud_config': os.getenv('CLOUD_CONFIG_PATH') or str(BASE_DIR / 'mobile_api_ai' / 'cloud_config.json'),
    'project_operators': os.getenv('PROJECT_OPERATORS_PATH') or str(BASE_DIR / 'operators.json'),
    # === SQLite 已废弃（保留引用以防其他模块崩溃，但运行时会被拦截）===
    'sqlite_data': os.getenv('SQLITE_DATA_PATH') or str(DATA_DIR / 'data.db'),  # DEPRECATED: 全部数据已迁移到 MySQL
    'wechat_container': os.getenv('WECHAT_CONTAINER_DB_PATH') or str(BASE_DIR / 'mobile_api_ai' / 'wechat_container.db'),  # DEPRECATED: → container_center MySQL
    'container_center': os.getenv('CONTAINER_CENTER_DB_PATH') or str(BASE_DIR / 'mobile_api_ai' / 'container_center.db'),  # DEPRECATED: → container_center MySQL
    'chengsheng': os.getenv('CHENGSHENG_DB_PATH') or str(BASE_DIR / 'chengsheng.db'),  # DEPRECATED: → MySQL
    'operation_logs': os.getenv('OPERATION_LOGS_DB_PATH') or str(BASE_DIR / 'mobile_api_ai' / 'operation_logs.db'),  # DEPRECATED: → MySQL
    # === 本地配置（保留）===
    'scheduler_configs': os.getenv('SCHEDULER_CONFIGS_PATH') or str(BASE_DIR / 'mobile_api_ai' / 'data' / 'scheduler_configs.db'),
    'repair_categories': os.getenv('REPAIR_CATEGORIES_PATH') or str(BASE_DIR / 'repair_categories.json'),
    'operators_history': os.getenv('OPERATORS_HISTORY_PATH') or str(BASE_DIR / 'operators_history.json'),
    'window_config': os.getenv('WINDOW_CONFIG_PATH') or str(DATA_DIR / 'window_config.json'),
    'task_pool': os.getenv('TASK_POOL_DB_PATH') or str(BASE_DIR / 'mobile_api_ai' / 'container' / 'task_pool.db'),
    'ssl_cert': os.getenv('SSL_CERT_PATH') or str(BASE_DIR / 'ssl' / 'cert.pem'),
    'ssl_key': os.getenv('SSL_KEY_PATH') or str(BASE_DIR / 'ssl' / 'key.pem'),
    'face_checkin_db': os.getenv('FACE_CHECKIN_DB_PATH') or str(BASE_DIR / 'mobile_api_ai' / 'data' / 'face_checkin.db'),
    'face_checkin_config': os.getenv('FACE_CHECKIN_CONFIG_PATH') or str(BASE_DIR / 'mobile_api_ai' / 'data' / 'config.json'),
    'DEPRECATED_wechat_container': os.getenv('WECHAT_CONTAINER_DB_PATH') or str(BASE_DIR / 'mobile_api_ai' / 'wechat_container.db'),  # 已迁移到 MySQL
    'DEPRECATED_chengsheng': os.getenv('CHENGSHENG_DB_PATH') or str(BASE_DIR / 'mobile_api_ai' / 'chengsheng.db'),
    'DEPRECATED_scheduler_configs': os.getenv('SCHEDULER_CONFIGS_PATH') or '',
    'DEPRECATED_dispatch_data': os.getenv('DISPATCH_DATA_PATH') or str(BASE_DIR / 'mobile_api_ai' / 'dispatch_center_data.json'),
    'DEPRECATED_enterprise_structure': os.getenv('ENTERPRISE_STRUCTURE_PATH') or str(BASE_DIR / 'mobile_api_ai' / 'data' / 'enterprise_structure.json'),
}

# 重新导出 DISPATCH_DATA_FILE（兼容旧导入路径）
DISPATCH_DATA_FILE = DB_PATHS['DEPRECATED_dispatch_data']

DIR_PATHS = {
    'data': str(DATA_DIR),
    'config': str(CONFIG_DIR),
    'logs': str(LOG_DIR),
    'templates': str(BASE_DIR / 'mobile_api_ai' / 'templates'),
    'static': str(BASE_DIR / 'mobile_api_ai' / 'static'),
    'scripts': str(BASE_DIR / 'scripts'),
    'tools': str(BASE_DIR / 'scripts' / 'tools'),
}

SERVICE_URLS = {
    'container_center': os.getenv('CONTAINER_CENTER_URL', 'http://127.0.0.1:5002'),
    'dispatch_center': os.getenv('DISPATCH_CENTER_URL', 'http://127.0.0.1:5003'),
    'sync_bridge': os.getenv('SYNC_BRIDGE_URL', 'http://127.0.0.1:5005'),
    'wechat_cloud': os.getenv('WECHAT_CLOUD_HOST', ''),
    'cloud_relay': os.getenv('CLOUD_RELAY_URL', ''),
    'mobile_api': os.getenv('MOBILE_SERVER_URL', 'http://127.0.0.1:5003'),
    'inventory_api': os.getenv('INVENTORY_API_URL', 'http://127.0.0.1:5004'),
}

# 向后兼容：独立 URL 变量
CONTAINER_CENTER_URL = SERVICE_URLS['container_center']
DISPATCH_CENTER_URL = SERVICE_URLS['dispatch_center']
SYNC_BRIDGE_URL = SERVICE_URLS['sync_bridge']
WECHAT_CLOUD_HOST = SERVICE_URLS['wechat_cloud']
CLOUD_RELAY_URL = SERVICE_URLS['cloud_relay']
MOBILE_SERVER_URL = SERVICE_URLS['mobile_api']
INVENTORY_API_URL = SERVICE_URLS['inventory_api']

EXTERNAL_URLS = {
    'ai_api': os.getenv('AI_API_URL', ''),
    'cdndomain': os.getenv('CDN_DOMAIN', ''),
}

SERVICE_TIMEOUTS = {
    'default': int(os.getenv('DEFAULT_TIMEOUT', '30')),
    'short': int(os.getenv('SHORT_TIMEOUT', '5')),
    'medium': int(os.getenv('MEDIUM_TIMEOUT', '10')),
    'long': int(os.getenv('LONG_TIMEOUT', '60')),
}

# 动态获取配置的函数
def get_db_config(key: str, default: str = '') -> str:
    """获取数据库配置"""
    return os.getenv(key, default)

def is_sqlite() -> bool:
    """是否使用SQLite"""
    return os.getenv('USE_SQLITE', 'true').lower() == 'true'

def get_sqlite_path() -> str:
    """获取SQLite数据库路径"""
    return os.getenv('SQLITE_DB_PATH', str(DATA_DIR / 'steel_belt.db'))

# ========== 应用信息 ==========
APP_NAME = "不锈钢网带跟单系统"
APP_VERSION = "3.0"

# ========== 资源目录 ==========
RESOURCE_DIR = BASE_DIR / "resources"

# ========== 数据库路径 ==========
DB_PATH = str(DATA_DIR / 'steel_belt.db')

# ========== MySQL配置 ==========
MYSQL_CONFIG = {
    "host": os.getenv('MYSQL_HOST', 'localhost'),
    "port": int(os.getenv('MYSQL_PORT', 3306)),
    "database": os.getenv('MYSQL_DATABASE', 'steel_belt'),
    "user": os.getenv('MYSQL_USER', ''),
    "password": os.getenv('MYSQL_PASSWORD', ''),
    "charset": "utf8mb4",
    "cursorclass": "dict"
}

# dispatch_center.py 等使用的 MYSQL_CFG 格式（兼容层）
MYSQL_CFG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', ''),
    'database': os.getenv('MYSQL_DATABASE', 'steel_belt'),
    'charset': 'utf8mb4',
}

# 容器中心专用配置 — 与 MYSQL_CFG 同实例不同库
CONTAINER_MYSQL_CFG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', ''),
    'database': os.getenv('CONTAINER_MYSQL_DATABASE', 'container_center'),
    'charset': 'utf8mb4',
}

# ========== 网络请求超时配置 ==========
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))
SHORT_TIMEOUT = int(os.getenv('SHORT_TIMEOUT', '5'))
REQUEST_TIMEOUT_FAST = int(os.getenv('REQUEST_TIMEOUT_FAST', '5'))
REQUEST_TIMEOUT_NORMAL = int(os.getenv('REQUEST_TIMEOUT_NORMAL', '10'))
REQUEST_TIMEOUT_LONG = int(os.getenv('REQUEST_TIMEOUT_LONG', '30'))
REQUEST_TIMEOUT_QUICK = int(os.getenv('REQUEST_TIMEOUT_QUICK', '3'))
REQUEST_TIMEOUT_EXTRA = int(os.getenv('REQUEST_TIMEOUT_EXTRA', '30'))
DB_CONNECT_TIMEOUT = int(os.getenv('DB_CONNECT_TIMEOUT', '5'))
SQLITE_TIMEOUT = int(os.getenv('SQLITE_TIMEOUT', '10'))
FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
FLASK_PORT = int(os.getenv('FLASK_PORT', '5008'))

# ========== 连接/超时细化配置 ==========
SOCKET_CONNECT_TIMEOUT = int(os.getenv('SOCKET_CONNECT_TIMEOUT', '5'))
QUEUE_POLL_TIMEOUT = int(os.getenv('QUEUE_POLL_TIMEOUT', '1'))
SNAPSHOT_TIMEOUT = int(os.getenv('SNAPSHOT_TIMEOUT', '300'))
CB_OPEN_TIMEOUT = int(os.getenv('CB_OPEN_TIMEOUT', '30'))
CB_RECOVERY_TIMEOUT = int(os.getenv('CB_RECOVERY_TIMEOUT', '60'))
CB_FAILURE_THRESHOLD = int(os.getenv('CB_FAILURE_THRESHOLD', '50'))
CB_FAILURE_RATE_THRESHOLD = float(os.getenv('CB_FAILURE_RATE_THRESHOLD', '0.5'))
CB_HALF_OPEN_REQUESTS = int(os.getenv('CB_HALF_OPEN_REQUESTS', '3'))

# ========== 定时任务/重试/调度配置 ==========
EXPIRY_TIMEOUT = int(os.getenv('EXPIRY_TIMEOUT', '180'))
RETRY_MIN_INTERVAL = int(os.getenv('RETRY_MIN_INTERVAL', '60'))
RETRY_SCHEDULER_INTERVAL = int(os.getenv('RETRY_SCHEDULER_INTERVAL', '60'))
EXPIRY_BATCH_LIMIT = int(os.getenv('EXPIRY_BATCH_LIMIT', '20'))
EXPIRY_CHECK_INTERVAL = int(os.getenv('EXPIRY_CHECK_INTERVAL', '30'))
SCHEDULER_SHUTDOWN_TIMEOUT = int(os.getenv('SCHEDULER_SHUTDOWN_TIMEOUT', '5'))
WECHAT_CLOUD_MAX_RETRIES = int(os.getenv('WECHAT_CLOUD_MAX_RETRIES', '3'))

# ============================================================
# [v3.8.2] P0-S7 密钥校验 (test_p0_s7_secrets.py 验证)
# ============================================================
# 5 套密钥规格 (hex 字符串, len // 2 = 字节数):
#   - JWT_SECRET_KEY:         >=32 字节 (256-bit, JWT 签名)
#   - DISPATCH_TOKEN:         >=16 字节 (调度中心鉴权)
#   - STATS_API_KEY:          >=16 字节 (统计 API)
#   - WECHAT_CLOUD_API_KEY:   >=16 字节 (微信云服务)
#   - SESSION_SECRET:         >=32 字节 (会话加密)
#
# 失败时:
#   - strict=True: 抛 RuntimeError
#   - strict=False: 返回 (False, err_code, err_msg)

from typing import Tuple, Dict as _Dict

_SECRET_SPECS = [
    ('JWT_SECRET_KEY',       32, 'JWT 签名密钥'),
    ('DISPATCH_TOKEN',       16, '调度中心鉴权 token'),
    ('STATS_API_KEY',        16, '统计 API key'),
    ('WECHAT_CLOUD_API_KEY', 16, '微信云服务 API key'),
    ('SESSION_SECRET',       32, '会话加密密钥'),
]


def validate_secrets(strict: bool = True) -> Tuple[bool, int, str]:
    """
    校验 5 套密钥是否符合强度标准

    :param strict: True=失败抛 RuntimeError; False=返回 warning 而不抛错
    :return: (passed, err_code, err_msg)
        err_code:
            0 = 全部通过
            1 = 必填缺失
            2 = 长度不足
            3 = 混用违规
    """
    # 1. 缺失检查
    for name, _, _ in _SECRET_SPECS:
        if not os.getenv(name):
            msg = f'密钥缺失: {name}'
            if strict:
                raise RuntimeError(msg)
            return False, 1, msg

    # 2. 长度检查 (按 hex 字符串, len // 2 = 字节数)
    for name, min_bytes, _ in _SECRET_SPECS:
        val = os.getenv(name, '')
        actual_bytes = len(val) // 2
        if actual_bytes < min_bytes:
            msg = f'密钥过短: {name} ({actual_bytes} 字节 < {min_bytes} 字节要求)'
            if strict:
                raise RuntimeError(msg)
            return False, 2, msg

    # 3. 混用检查 (两把密钥值相同)
    seen = {}
    for name, _, _ in _SECRET_SPECS:
        val = os.getenv(name)
        if val in seen:
            msg = f'密钥混用违规: {name} 与 {seen[val]} 值相同'
            if strict:
                raise RuntimeError(msg)
            return False, 3, msg
        seen[val] = name

    return True, 0, '所有密钥校验通过'


def get_secret_status() -> _Dict[str, _Dict[str, Any]]:
    """
    查询 5 套密钥的状态

    :return: {name: {meets_min, length_bytes, min_bytes, purpose}}
    """
    status = {}
    for name, min_bytes, purpose in _SECRET_SPECS:
        val = os.getenv(name, '')
        length_bytes = len(val) // 2
        status[name] = {
            'meets_min': length_bytes >= min_bytes,
            'length_bytes': length_bytes,
            'min_bytes': min_bytes,
            'purpose': purpose,
        }
    return status
