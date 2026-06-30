import os
from flask import Flask
from flask_cors import CORS


def init_cors(app: Flask, default_origins: str = 'http://localhost:3000') -> None:
    origins_str = os.getenv('CORS_ALLOWED_ORIGINS', default_origins)
    if not origins_str or origins_str.strip() == '*':
        raise ValueError(
            'CORS_ALLOWED_ORIGINS 未正确配置。'
            '请设置具体的允许域名，禁止使用 "*"。'
        )
    origins = [o.strip() for o in origins_str.split(',') if o.strip()]
    CORS(app, resources={r"/api/*": {"origins": origins}}, supports_credentials=True)
