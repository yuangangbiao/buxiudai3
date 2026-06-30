# -*- coding: utf-8 -*-
"""
应用程序初始化和配置（优化版）
"""

import sys
import os
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def get_version() -> str:
    """获取版本号"""
    from version import VERSION
    return VERSION


def get_build_info() -> dict:
    """获取构建信息"""
    return {
        'version': get_version(),
        'arch': 'MVC + Service + EventBus',
        'features': [
            '统一配置管理',
            '服务层封装',
            '事件总线',
            '审计日志',
            '数据校验',
            '统一异常处理',
        ]
    }


def initialize_app():
    """
    初始化应用程序（优化版）

    优化策略：
    1. 合并数据库操作 - 使用单个连接完成所有初始化
    2. 移除重复的连接池预热（已在init_db中完成）
    3. 延迟事件总线初始化（按需加载）
    """
    from models.database import init_db, get_connection

    # 1. 初始化数据库（包含表结构创建和连接预热）
    init_db()

    # 2. 确保审计日志表存在（合并到init_db连接中）
    _ensure_audit_table()

    # 3. 注册默认事件处理器（延迟加载）
    _register_default_handlers()

    # 4. 发布应用启动事件
    from core.event_bus import EventBus, Events
    EventBus.publish(Events.APP_STARTED, get_build_info())

    logger.info(f"[{get_version()}] 应用程序初始化完成")


def _ensure_audit_table():
    """确保审计日志表存在（优化版：使用现有连接）"""
    from models.database import get_connection
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                operator TEXT,
                action TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT,
                before_data TEXT,
                after_data TEXT,
                remark TEXT,
                ip_address TEXT,
                extra_info TEXT
            )
        ''')
        conn.commit()
        cursor.close()
    finally:
        conn.close()


def _register_default_handlers():
    """注册默认事件处理器（延迟加载）"""
    from core.event_bus import EventBus, Events

    def on_order_status_changed(event, data):
        logger.info(f"订单状态变更: {data.get('order_no')} - {data.get('from_status')} -> {data.get('to_status')}")

    EventBus.subscribe(Events.ORDER_STATUS_CHANGED, on_order_status_changed)

    def on_inventory_low(event, data):
        logger.warning(f"库存预警: {data.get('material_name')} 低于安全库存")

    EventBus.subscribe(Events.INVENTORY_LOW_STOCK, on_inventory_low)


def create_secure_flask_app(
    import_name: str,
    default_origins: str = 'http://localhost:5000,http://localhost:3000',
    enable_limiter: bool = True,
    template_folder: Optional[str] = None,
    static_folder: Optional[str] = None,
    blueprints: Optional[List] = None,
) -> 'Flask':
    from flask import Flask
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    from core.cors_config import init_cors
    from core.config import JWT_SECRET_KEY

    app = Flask(
        import_name,
        template_folder=template_folder,
        static_folder=static_folder,
    )

    init_cors(app, default_origins=default_origins)

    if enable_limiter:
        Limiter(
            app=app,
            key_func=get_remote_address,
            default_limits=os.getenv('DEFAULT_RATE_LIMITS', '1000 per day, 300 per hour').split(', '),
            storage_uri=os.getenv('LIMITER_STORAGE_URI', 'memory://'),
        )

    app.secret_key = JWT_SECRET_KEY

    @app.errorhandler(Exception)
    def handle_global_exception(e):
        logger.exception('[全局异常] %s', e)
        return {'code': 500, 'message': str(e)}, 500

    @app.route('/favicon.ico')
    def favicon():
        return '', 204

    if blueprints:
        for bp in blueprints:
            app.register_blueprint(bp)

    return app