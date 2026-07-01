# -*- coding: utf-8 -*-
"""
环境变量验证模块 - 启动时验证必须配置

使用方式：
    from env_validator import validate_environment

    # 在 app.py 启动前调用
    validate_environment()

    # 或导入settings自动验证
    from settings import settings
"""
import os
import sys
import logging

logger = logging.getLogger(__name__)


class EnvironmentError(Exception):
    """环境变量验证错误"""
    pass


REQUIRED_ENV_VARS = {
    'JWT_SECRET_KEY': {
        'required': True,
        'description': 'JWT认证密钥（必须，32字节以上）',
        'min_length': 16,
        'error_msg': 'JWT_SECRET_KEY 环境变量未设置或长度不足'
    },
    'MYSQL_PASSWORD': {
        'required': True,
        'description': 'MySQL数据库密码',
        'min_length': 1,
        'error_msg': 'MYSQL_PASSWORD 环境变量未设置'
    }
}

OPTIONAL_ENV_VARS = {
    'MYSQL_HOST': {'default': 'localhost', 'description': 'MySQL主机'},
    'MYSQL_PORT': {'default': '3306', 'description': 'MySQL端口'},
    'MYSQL_DATABASE': {'default': 'steel_belt', 'description': 'MySQL数据库名'},
    'REDIS_HOST': {'default': 'localhost', 'description': 'Redis主机'},
    'REDIS_PORT': {'default': '6379', 'description': 'Redis端口'},
    'CORS_ALLOWED_ORIGINS': {'default': 'http://localhost:5000', 'description': 'CORS允许的源'},
    'FLASK_DEBUG': {'default': 'false', 'description': '调试模式'},
    'DASHSCOPE_API_KEY': {'default': '', 'description': '阿里云通义千问API密钥'}
}


def validate_value(name: str, config: dict, value: str) -> tuple:
    """验证单个环境变量"""
    if not value and config.get('required'):
        return False, config.get('error_msg', f'{name} 是必填环境变量')

    if value and config.get('min_length'):
        if len(value) < config['min_length']:
            return False, config.get('error_msg', f'{name} 长度不足{config["min_length"]}字符')

    return True, None


def validate_environment(strict: bool = True) -> dict:
    """
    验证环境变量配置

    Args:
        strict: True=严格模式（缺少必填变量时退出）

    Returns:
        dict: 验证结果

    Raises:
        EnvironmentError: 严格模式下，必填变量缺失时抛出
    """
    results = {
        'valid': True,
        'required': {},
        'optional': {},
        'warnings': []
    }

    for name, config in REQUIRED_ENV_VARS.items():
        value = os.getenv(name, '')
        valid, error = validate_value(name, config, value)
        results['required'][name] = {
            'value': value[:4] + '***' if value else '',
            'valid': valid,
            'description': config['description']
        }
        if not valid:
            results['valid'] = False
            results['warnings'].append(error)
            if strict:
                logger.error(f"[ENV] 验证失败: {error}")
                raise EnvironmentError(error)

    for name, config in OPTIONAL_ENV_VARS.items():
        value = os.getenv(name, config.get('default', ''))
        results['optional'][name] = {
            'value': value[:4] + '***' if value else '',
            'description': config['description']
        }
        if not os.getenv(name):
            results['warnings'].append(f'{name} 未设置，使用默认值: {config.get("default")}')

    logger.info(f"[ENV] 环境变量验证完成: {len(results['required'])} 个必填, {len(results['optional'])} 个可选")
    for warning in results['warnings']:
        logger.warning(f"[ENV] {warning}")

    return results


def print_environment_report():
    """打印环境变量报告"""
    print("=" * 60)
    print("环境变量配置报告")
    print("=" * 60)

    print("\n【必填环境变量】")
    for name, config in REQUIRED_ENV_VARS.items():
        value = os.getenv(name, '')
        status = "✓" if value else "✗"
        print(f"  {status} {name}")
        print(f"      说明: {config['description']}")
        if value:
            print(f"      当前值: {value[:4]}***")
        else:
            print(f"      当前值: (未设置)")

    print("\n【可选环境变量】")
    for name, config in OPTIONAL_ENV_VARS.items():
        value = os.getenv(name, '')
        status = "✓" if value else "○"
        print(f"  {status} {name} = {config.get('default', '')}")
        print(f"      说明: {config['description']}")
        if value:
            print(f"      当前值: {value[:4]}***")
        else:
            print(f"      当前值: (使用默认值)")

    print("\n" + "=" * 60)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    print_environment_report()

    try:
        results = validate_environment(strict=False)
        if results['valid']:
            print("\n✓ 所有必填环境变量已配置")
        else:
            print("\n✗ 部分必填环境变量缺失，请检查上述报告")
    except EnvironmentError as e:
        print(f"\n✗ 环境变量验证失败: {e}")
        sys.exit(1)
