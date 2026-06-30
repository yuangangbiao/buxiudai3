"""结构化日志系统"""
import os
import sys
import json
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


class JSONFormatter(logging.Formatter):
    """JSON 格式化器 - 便于日志分析"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'func': record.funcName,
            'line': record.lineno,
        }
        
        # 附加字段
        for key, value in record.__dict__.items():
            if key not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                'thread', 'threadName', 'processName', 'process', 'message',
                'asctime', 'taskName'
            }:
                log_data[key] = value
        
        # 异常信息
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False, default=str)


class TestLogContext:
    """测试日志上下文 - 自动附加测试元数据"""
    
    def __init__(self):
        self._context: Dict[str, Any] = {}
    
    def set(self, **kwargs):
        self._context.update(kwargs)
    
    def clear(self):
        self._context.clear()
    
    def get(self) -> Dict:
        return self._context.copy()


_context = TestLogContext()


def setup_logging(
    log_dir: str = 'tests/reports/logs',
    level: int = logging.INFO,
    console: bool = True,
    logger_name: str = 'tests',
) -> logging.Logger:
    """配置日志系统 - 修复 P2-2: 不再 clear root handlers，避免影响其他 logger

    Args:
        log_dir: 日志目录
        level: 日志级别
        console: 是否输出到控制台
        logger_name: logger 名称（默认 'tests'，避免污染 root）
    """
    from tests.core._config import LOGS_DIR
    log_dir = str(LOGS_DIR)
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    # 修复 P2-2: 使用专门的 logger 名，不动 root
    tests_logger = logging.getLogger(logger_name)
    tests_logger.setLevel(level)

    # 防止日志冒泡到 root（避免重复输出）
    tests_logger.propagate = False

    # 修复 P2-2: 只清除此 logger 的 handlers，不影响其他 logger
    for handler in list(tests_logger.handlers):
        tests_logger.removeHandler(handler)

    # 文件 handler（JSON 格式）
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, f'test_{timestamp}.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8',
    )
    file_handler.setFormatter(JSONFormatter())
    tests_logger.addHandler(file_handler)

    # 控制台 handler（人类可读）
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_fmt = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_fmt)
        tests_logger.addHandler(console_handler)

    return tests_logger


def log_with_context(logger: logging.Logger, level: int, msg: str, **kwargs):
    """带上下文的日志"""
    extra = {**_context.get(), **kwargs}
    logger.log(level, msg, extra=extra)


# 便捷函数
def info(msg: str, **kwargs):
    log_with_context(logging.getLogger('test'), logging.INFO, msg, **kwargs)


def warning(msg: str, **kwargs):
    log_with_context(logging.getLogger('test'), logging.WARNING, msg, **kwargs)


def error(msg: str, **kwargs):
    log_with_context(logging.getLogger('test'), logging.ERROR, msg, **kwargs)


def debug(msg: str, **kwargs):
    log_with_context(logging.getLogger('test'), logging.DEBUG, msg, **kwargs)
