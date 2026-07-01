# ========== 工具函数 ==========
import os
import sys
from datetime import datetime, timezone
from core._config_infra import *
from core._config_ui import *


def now():
    """返回当前时间（datetime 对象），支持 .isoformat() / .strftime() / timedelta 运算"""
    try:
        return datetime.now(timezone.utc)
    except Exception:
        return datetime.now()


def get_default_backup_dir():
    """获取默认备份目录路径"""
    if hasattr(sys, 'frozen') and getattr(sys, 'frozen'):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = str(BASE_DIR)
    return os.path.join(base_dir, 'DAT', 'backup')


def get_app_dir():
    """获取应用程序目录路径"""
    if hasattr(sys, 'frozen') and getattr(sys, 'frozen'):
        return os.path.dirname(sys.executable)
    return str(BASE_DIR)


def get_default_redis_dump():
    """获取默认Redis dump文件路径"""
    redis_dump = os.environ.get('REDIS_DUMP_PATH')
    if redis_dump:
        return redis_dump
    if sys.platform == 'win32':
        return None
    redis_dump_default = os.environ.get('REDIS_DUMP_PATH_DEFAULT')
    if redis_dump_default:
        return redis_dump_default
    return None

# ========== Redis 事件总线配置 ==========
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))


class Config:
    """兼容存根类 — 将所有模块级变量暴露为类属性，方便旧代码通过 Config.X 方式访问"""
    JWT_SECRET_KEY = JWT_SECRET_KEY
    JWT_EXPIRE_HOURS = JWT_EXPIRE_HOURS
    WECHAT_CORP_ID = WECHAT_CORP_ID
    WECHAT_SECRET = WECHAT_SECRET
    LOG_DIR = LOG_DIR
    LOG_LEVEL = LOG_LEVEL
    LOG_RETENTION_DAYS = LOG_RETENTION_DAYS
    LOG_FORMAT = LOG_FORMAT
    LOG_DATE_FORMAT = LOG_DATE_FORMAT
    LOG_MAX_BYTES = LOG_MAX_BYTES
    ALIYUN_API_KEY = ALIYUN_API_KEY
    ALIYUN_API_SECRET = ALIYUN_API_SECRET
    ALIYUN_SPEECH_APPKEY = ALIYUN_SPEECH_APPKEY
    ALIYUN_VISION_APPKEY = ALIYUN_VISION_APPKEY
    DASHSCOPE_API_KEY = DASHSCOPE_API_KEY
    MYSQL_HOST = MYSQL_HOST
    MYSQL_PORT = MYSQL_PORT
    MYSQL_USER = MYSQL_USER
    MYSQL_PASSWORD = MYSQL_PASSWORD
    MYSQL_DATABASE = MYSQL_DATABASE
    UPLOAD_FOLDER = UPLOAD_FOLDER
    MAX_CONTENT_LENGTH = MAX_CONTENT_LENGTH
    WECHAT_BOT_HOST = WECHAT_BOT_HOST
    WECHAT_BOT_PORT = WECHAT_BOT_PORT
    CONTAINER_CENTER_PORT = CONTAINER_CENTER_PORT
    HTTP_TEST_PORT = HTTP_TEST_PORT
    DIAGNOSE_PORT = DIAGNOSE_PORT
    FLASK_HOST = FLASK_HOST
    FLASK_PORT = FLASK_PORT
    MAX_TEXT_LENGTH = MAX_TEXT_LENGTH
    SESSION_TIMEOUT = SESSION_TIMEOUT
    DATA_RETENTION_DAYS = DATA_RETENTION_DAYS
    REQUEST_TIMEOUT_FAST = REQUEST_TIMEOUT_FAST
    REQUEST_TIMEOUT_NORMAL = REQUEST_TIMEOUT_NORMAL
    REQUEST_TIMEOUT_LONG = REQUEST_TIMEOUT_LONG
    REQUEST_TIMEOUT_QUICK = REQUEST_TIMEOUT_QUICK
    REQUEST_TIMEOUT_EXTRA = REQUEST_TIMEOUT_EXTRA
    DB_CONNECT_TIMEOUT = DB_CONNECT_TIMEOUT
    SQLITE_TIMEOUT = SQLITE_TIMEOUT
    REDIS_PORT = REDIS_PORT
    CB_FAILURE_THRESHOLD = CB_FAILURE_THRESHOLD
    CB_SUCCESS_THRESHOLD = CB_SUCCESS_THRESHOLD
    CB_FAILURE_RATE_THRESHOLD = CB_FAILURE_RATE_THRESHOLD
