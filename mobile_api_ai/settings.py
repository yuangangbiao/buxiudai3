# -*- coding: utf-8 -*-
"""
配置管理模块 - 统一配置加载

支持：
- .env 文件自动加载
- 环境变量覆盖
- 配置验证
- 类型转换

使用方式：
    from settings import settings

    # 访问配置
    db_host = settings.database.host
    jwt_secret = settings.jwt.secret_key

    # 检查环境
    if settings.app.debug:
        ...
"""
import os
from pathlib import Path
from typing import Optional, List, Any
from dataclasses import dataclass, field


@dataclass
class DatabaseConfig:
    """数据库配置"""
    host: str = 'localhost'
    port: int = 3306
    user: str = 'root'
    password: str = ''
    database: str = 'steel_belt'
    pool_size: int = 10
    pool_recycle: int = 3600
    pool_pre_ping: bool = True

    @classmethod
    def from_env(cls):
        return cls(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            port=int(os.getenv('MYSQL_PORT', '3306')),
            user=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', ''),
            database=os.getenv('MYSQL_DATABASE', 'steel_belt'),
            pool_size=int(os.getenv('MYSQL_POOL_SIZE', '10')),
            pool_recycle=int(os.getenv('MYSQL_POOL_RECYCLE', '3600')),
            pool_pre_ping=os.getenv('MYSQL_POOL_PRE_PING', 'true').lower() in ('true', '1', 'yes'),
        )


@dataclass
class JWTConfig:
    """JWT配置"""
    secret_key: str = ''
    algorithm: str = 'HS256'
    expire_hours: int = 24

    @classmethod
    def from_env(cls):
        secret = os.getenv('JWT_SECRET_KEY', '')
        if not secret:
            raise ValueError("JWT_SECRET_KEY 环境变量未设置")
        return cls(
            secret_key=secret,
            algorithm=os.getenv('JWT_ALGORITHM', 'HS256'),
            expire_hours=int(os.getenv('JWT_EXPIRE_HOURS', '24')),
        )


@dataclass
class CORSConfig:
    """CORS配置"""
    origins: List[str] = field(default_factory=lambda: ['http://localhost:5000'])

    @classmethod
    def from_env(cls):
        origins_str = os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:5000,http://localhost:3000')
        origins = [o.strip() for o in origins_str.split(',') if o.strip()]
        return cls(origins=origins)


@dataclass
class FlaskConfig:
    """Flask配置"""
    debug: bool = False
    secret_key: str = ''
    host: str = '0.0.0.0'
    port: int = 5000

    @classmethod
    def from_env(cls):
        debug_str = os.getenv('FLASK_DEBUG', 'false').lower()
        _secret_key = os.getenv('FLASK_SECRET_KEY') or os.getenv('JWT_SECRET_KEY')
        if not _secret_key:
            raise ValueError("必须设置 FLASK_SECRET_KEY 或 JWT_SECRET_KEY 环境变量")
        return cls(
            debug=debug_str in ('true', '1', 'yes'),
            secret_key=_secret_key,
            host=os.getenv('FLASK_HOST', '0.0.0.0'),
            port=int(os.getenv('FLASK_PORT', '5000')),
        )


@dataclass
class WeChatConfig:
    """微信配置"""
    corp_id: str = ''
    agent_id: str = ''
    token: str = ''
    aes_key: str = ''

    @classmethod
    def from_env(cls):
        return cls(
            corp_id=os.getenv('WECHAT_WORK_CORP_ID', ''),
            agent_id=os.getenv('WECHAT_WORK_AGENT_ID', ''),
            token=os.getenv('WECHAT_WORK_TOKEN', ''),
            aes_key=os.getenv('WECHAT_WORK_AES_KEY', ''),
        )


@dataclass
class LogConfig:
    """日志配置"""
    level: str = 'INFO'
    format: str = '%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] %(message)s'
    date_format: str = '%Y-%m-%d %H:%M:%S'
    retention_days: int = 30
    max_bytes: int = 100 * 1024 * 1024

    @classmethod
    def from_env(cls):
        return cls(
            level=os.getenv('LOG_LEVEL', 'INFO'),
            format=os.getenv('LOG_FORMAT', '%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] %(message)s'),
            date_format=os.getenv('LOG_DATE_FORMAT', '%Y-%m-%d %H:%M:%S'),
            retention_days=int(os.getenv('LOG_RETENTION_DAYS', '30')),
            max_bytes=int(os.getenv('LOG_MAX_BYTES', str(100 * 1024 * 1024))),
        )


@dataclass
class Settings:
    """应用配置"""
    database: DatabaseConfig = field(default_factory=DatabaseConfig.from_env)
    jwt: JWTConfig = field(default_factory=JWTConfig.from_env)
    cors: CORSConfig = field(default_factory=CORSConfig.from_env)
    flask: FlaskConfig = field(default_factory=FlaskConfig.from_env)
    wechat: WeChatConfig = field(default_factory=WeChatConfig.from_env)
    log: LogConfig = field(default_factory=LogConfig.from_env)

    @classmethod
    def load(cls) -> 'Settings':
        """加载所有配置"""
        return cls(
            database=DatabaseConfig.from_env(),
            jwt=JWTConfig.from_env(),
            cors=CORSConfig.from_env(),
            flask=FlaskConfig.from_env(),
            wechat=WeChatConfig.from_env(),
            log=LogConfig.from_env(),
        )

    def to_dict(self) -> dict:
        """转换为字典（用于调试）"""
        return {
            'database': {
                'host': self.database.host,
                'port': self.database.port,
                'database': self.database.database,
            },
            'flask': {
                'debug': self.flask.debug,
                'host': self.flask.host,
                'port': self.flask.port,
            },
            'jwt': {
                'algorithm': self.jwt.algorithm,
                'expire_hours': self.jwt.expire_hours,
            },
            'cors': {
                'origins': self.cors.origins,
            },
            'log': {
                'level': self.log.level,
                'retention_days': self.log.retention_days,
            }
        }


settings = Settings.load()
