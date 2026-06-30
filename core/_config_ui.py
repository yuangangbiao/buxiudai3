import os
from core._config_infra import APP_NAME

# ========== API密钥配置 ==========
class ApiKeyConfig:
    """API密钥配置（必须从环境变量读取）"""
    INVENTORY_API_KEY = os.getenv('INVENTORY_API_KEY', '')
    WECHAT_API_KEY = os.getenv('WECHAT_API_KEY', '')
    AI_API_KEY = os.getenv('AI_API_KEY', '')

# ========== 样式配置 ==========
class StyleConfig:
    """UI样式配置"""
    FONT_FAMILY = os.getenv('FONT_FAMILY', 'Microsoft YaHei')
    FONT_SIZE_NORMAL = int(os.getenv('FONT_SIZE_NORMAL', '10'))
    FONT_SIZE_TITLE = int(os.getenv('FONT_SIZE_TITLE', '14'))
    PRIMARY_COLOR = os.getenv('PRIMARY_COLOR', '#2196F3')
    SUCCESS_COLOR = os.getenv('SUCCESS_COLOR', '#4CAF50')
    WARNING_COLOR = os.getenv('WARNING_COLOR', '#FF9800')
    ERROR_COLOR = os.getenv('ERROR_COLOR', '#F44336')

# ========== 字体配置字典 ==========
_font_family = StyleConfig.FONT_FAMILY
FONTS = {
    "title": (_font_family, 20, "bold"),
    "large": (_font_family, 14),
    "large_bold": (_font_family, 14, "bold"),
    "subtitle": (_font_family, 12, "bold"),
    "heading": (_font_family, 12, "bold"),
    "body": (_font_family, 10),
    "normal": (_font_family, 10),
    "normal_bold": (_font_family, 10, "bold"),
    "small": (_font_family, 9),
    "small_bold": (_font_family, 9, "bold"),
    "tiny": (_font_family, 8),
    "icon_emoji": ("Segoe UI Emoji", 18),
    "mono": ("Consolas", 10),
    "mono_small": ("Consolas", 8),
}

# ========== 布局配置（详细） ==========
LAYOUT = {
    "padding": {
        "small": 5,
        "medium": 10,
        "large": 15,
    },
    "margin": {
        "small": 2,
        "medium": 5,
        "large": 8,
    },
    "widths": {
        "small": 8,
        "medium": 14,
        "large": 18,
        "extra_large": 22,
    },
    "heights": {
        "small": 2,
        "medium": 12,
        "large": 14,
        "extra_large": 18,
    },
}

# ========== 窗口配置 ==========
WINDOW_SIZES = {
    "production_select": "1000x450",
    "order_detail": "500x400",
    "custom_types": "550x480",
}

WINDOW = {
    "title": APP_NAME,
    "width": 1200,
    "height": 700,
    "min_width": 800,
    "min_height": 500
}

# ========== 颜色配置（完整） ==========
COLORS = {
    "primary": "#1E3A5F",
    "primary_light": "#2E5A8F",
    "accent": "#4A90D9",
    "bg_main": "#F0F2F5",
    "bg_card": "#FFFFFF",
    "bg_sidebar": "#1E3A5F",
    "text_primary": "#1A1A2E",
    "text_secondary": "#666666",
    "text_white": "#FFFFFF",
    "success": "#4CAF50",
    "warning": "#FF9800",
    "danger": "#F44336",
    "info": "#2196F3",
    "table_header": "#F5F5F5",
    "table_row_odd": "#FFFFFF",
    "table_row_even": "#F9F9F9",
    "orange": "#E65100",
    "light_orange": "#FFF3E0",
    "deep_gray": "#333333",
    "green_dark": "#2E7D32",
    "gray_blue": "#37474F",
    "light_gray": "#F5F5F5",
    "ultra_light_gray": "#ECEFF1",
    "very_light_gray": "#F7F7FA",
    "green": "#4CAF50",
    "orange_light": "#FF9800",
    "red": "#F44336",
    "blue": "#2196F3",
    "DATA_TYPE_REPORT": os.getenv('COLOR_REPORT', '#4caf50'),
    "DATA_TYPE_QUALITY": os.getenv('COLOR_QUALITY', '#2196f3'),
    "DATA_TYPE_MATERIAL": os.getenv('COLOR_MATERIAL', '#ff9800'),
    "DATA_TYPE_APPROVAL": os.getenv('COLOR_APPROVAL', '#9c27b0'),
    "DATA_TYPE_ORDER": os.getenv('COLOR_ORDER', '#00bcd4'),
    "DATA_TYPE_PROCESS": os.getenv('COLOR_PROCESS', '#607d8b'),
    "DATA_TYPE_REPAIR": os.getenv('COLOR_REPAIR', '#FF6B6B'),
}

# ========== 库存阈值（直接访问） ==========
STOCK_WARNING_THRESHOLD = int(os.getenv('STOCK_WARNING_THRESHOLD', '50'))

# ========== 从 mobile_api_ai/config.py 迁移的遗留配置 ==========
# 注意：以下配置项来自 module-level config，供兼容层读取。
# 新代码应通过本模块已有的 API 获取配置，勿直接引用的定义。

# --- JWT ---
_jwt_key = os.getenv('JWT_SECRET_KEY')
if not _jwt_key:
    _env_path = BASE_DIR / '.env'
    if _env_path.exists():
        for _line in _env_path.read_text(encoding='utf-8').splitlines():
            if _line.strip().startswith('JWT_SECRET_KEY='):
                _val = _line.split('=', 1)[1].strip().strip('"').strip("'")
                if _val:
                    _jwt_key = _val
                    break
if not _jwt_key:
    import secrets
    _jwt_key = secrets.token_hex(32)
    logger.warning('JWT_SECRET_KEY 未设置，已自动生成（64字符十六进制密钥）')
    _env_path = BASE_DIR / '.env'
    _new_line = f'JWT_SECRET_KEY={_jwt_key}'
    if _env_path.exists():
        _lines = _env_path.read_text(encoding='utf-8').splitlines()
        _found = False
        for _i, _line in enumerate(_lines):
            if _line.strip().startswith('JWT_SECRET_KEY='):
                _lines[_i] = _new_line
                _found = True
                break
        if not _found:
            _lines.append('')
            _lines.append(_new_line)
        _env_path.write_text('\n'.join(_lines) + '\n', encoding='utf-8')
    else:
        _env_path.parent.mkdir(parents=True, exist_ok=True)
        _env_path.write_text(_new_line + '\n', encoding='utf-8')
    logger.warning('已自动写入 %s', _env_path)
JWT_SECRET_KEY = _jwt_key
JWT_EXPIRE_HOURS = int(os.getenv('JWT_EXPIRE_HOURS', '24'))

# --- 企业微信 ---
WECHAT_CORP_ID = os.getenv('WECHAT_CORP_ID', '')
WECHAT_AGENT_ID = os.getenv('WECHAT_AGENT_ID', '')
WECHAT_SECRET = os.getenv('WECHAT_SECRET', '')

# --- 日志 ---
# [v3.8.1 修复] 之前用 os.getenv('LOG_DIR', 'logs') 返回 str, 覆盖了 _config_infra.py 中的 Path 版本,
# 导致 core/logger.py:35 LOG_DIR.mkdir() 报 'str' object has no attribute 'mkdir'
# 改为从 _config_infra 复用 Path 版本, 允许环境变量覆盖
from pathlib import Path as _Path
from core._config_infra import LOG_DIR as _LOG_DIR_INFRA
_LOG_DIR_ENV = os.getenv('LOG_DIR')
if _LOG_DIR_ENV:
    LOG_DIR = _Path(_LOG_DIR_ENV)
else:
    LOG_DIR = _LOG_DIR_INFRA
LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] %(message)s')
LOG_DATE_FORMAT = os.getenv('LOG_DATE_FORMAT', '%Y-%m-%d %H:%M:%S')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_RETENTION_DAYS = int(os.getenv('LOG_RETENTION_DAYS', '30'))
LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', str(10 * 1024 * 1024)))

# --- 阿里云 ---
ALIYUN_API_KEY = os.getenv('ALIYUN_API_KEY', '')
ALIYUN_API_SECRET = os.getenv('ALIYUN_API_SECRET', '')
ALIYUN_SPEECH_APPKEY = os.getenv('ALIYUN_SPEECH_APPKEY', '')
ALIYUN_VISION_APPKEY = os.getenv('ALIYUN_VISION_APPKEY', '')
DASHSCOPE_API_KEY = os.getenv('DASHSCOPE_API_KEY', '')

# --- 上传 ---
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', str(16 * 1024 * 1024)))

# --- 业务端口 ---
WECHAT_BOT_PORT = int(os.getenv('WECHAT_BOT_PORT', '5003'))
WECHAT_BOT_HOST = os.getenv('WECHAT_BOT_HOST', '0.0.0.0')
CONTAINER_CENTER_PORT = int(os.getenv('CONTAINER_CENTER_PORT', '5002'))
HTTP_TEST_PORT = int(os.getenv('HTTP_TEST_PORT', '9999'))
DIAGNOSE_PORT = int(os.getenv('DIAGNOSE_PORT', '5003'))

# --- 业务阈值 ---
MAX_TEXT_LENGTH = int(os.getenv('MAX_TEXT_LENGTH', '2048'))
SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', '300'))
DATA_RETENTION_DAYS = int(os.getenv('DATA_RETENTION_DAYS', '90'))
CB_SUCCESS_THRESHOLD = int(os.getenv('CB_SUCCESS_THRESHOLD', '3'))

# --- Redis ---
REDIS_DUMP_PATH = os.getenv('REDIS_DUMP_PATH', '')
REDIS_DUMP_PATH_DEFAULT = os.getenv('REDIS_DUMP_PATH_DEFAULT', '')

# --- 颜色配置 ---
COLOR_REPORT = os.getenv('COLOR_REPORT', '#4caf50')
COLOR_QUALITY = os.getenv('COLOR_QUALITY', '#2196f3')
COLOR_MATERIAL = os.getenv('COLOR_MATERIAL', '#ff9800')
COLOR_APPROVAL = os.getenv('COLOR_APPROVAL', '#9c27b0')
COLOR_ORDER = os.getenv('COLOR_ORDER', '#00bcd4')
COLOR_PROCESS = os.getenv('COLOR_PROCESS', '#607d8b')
COLOR_REPAIR = os.getenv('COLOR_REPAIR', '#FF6B6B')
