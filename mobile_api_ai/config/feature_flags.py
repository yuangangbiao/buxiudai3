# -*- coding: utf-8 -*-
"""
[feature_flags.py - 2026-06-14]
降级开关中心 - 实施 FALLBACK.md 中定义的能力
5002 启动时加载，业务层根据 flag 选择数据源

设计原则：
- 默认全部启用（use_local_mirror=True）
- 故障时运维改 MySQL 表切换 flag
- 切换不需重启 5002（每 30s 重新加载）
- 切换全程记录审计日志
"""
import logging
import os
import time
from typing import Dict

from storage.mysql_storage import MySQLStorage

logger = logging.getLogger(__name__)


class FeatureFlag:
    """单个 feature flag"""
    def __init__(self, name: str, default: bool, description: str = ''):
        self.name = name
        self.default = default
        self.description = description
        self.value = default

    def enable(self):
        logger.info(f'[FLAG] {self.name} → ENABLED')
        self.value = True

    def disable(self):
        logger.info(f'[FLAG] {self.name} → DISABLED')
        self.value = False

    def is_enabled(self) -> bool:
        return self.value


class FeatureFlagManager:
    """Feature flag 中心（MySQL 持久化 + 内存缓存）"""

    _instance = None

    def __init__(self):
        self.flags: Dict[str, FeatureFlag] = {}
        # 注册默认 flags
        self._register_default_flags()
        # 启动时从 MySQL 加载
        self.reload()
        self._last_reload = time.time()

    @classmethod
    def get_instance(cls):
        """单例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _register_default_flags(self):
        """注册默认 flags"""
        self.flags['use_local_mirror'] = FeatureFlag(
            'use_local_mirror',
            default=True,
            description='业务层读镜像表（orders_local 等）；False → 读源表（steel_belt.orders）',
        )
        self.flags['use_outbox_fallback'] = FeatureFlag(
            'use_outbox_fallback',
            default=True,
            description='mirror 失败时写入 outbox 兜底；False → 直接失败',
        )
        self.flags['enable_etl_sync'] = FeatureFlag(
            'enable_etl_sync',
            default=True,
            description='5002 启动 ETL worker 同步源表到镜像表；False → 关闭 ETL（紧急止血）',
        )
        self.flags['enable_hard_delete_sync'] = FeatureFlag(
            'enable_hard_delete_sync',
            default=True,
            description='ETL 检测源表硬删除后清理镜像表；False → 关闭硬删除同步',
        )
        self.flags['enable_outbox_worker'] = FeatureFlag(
            'enable_outbox_worker',
            default=True,
            description='5002 启动 outbox worker 处理死信；False → 关闭 outbox（紧急止血）',
        )
        self.flags['enable_auto_cleanup'] = FeatureFlag(
            'enable_auto_cleanup',
            default=True,
            description='ETL 同步后清理过期数据（90天/365天）；False → 关闭清理',
        )

    def reload(self):
        """从 MySQL 重新加载所有 flags"""
        try:
            conn = MySQLStorage.get_connection()
            try:
                with conn.cursor() as c:
                    c.execute("""
                        SELECT COUNT(*) AS cnt FROM information_schema.tables
                        WHERE table_schema = DATABASE() AND table_name = 'feature_flags'
                    """)
                    if c.fetchone()[0] == 0:
                        c.execute("""
                            CREATE TABLE feature_flags (
                                name VARCHAR(64) PRIMARY KEY,
                                enabled TINYINT NOT NULL DEFAULT 1,
                                description VARCHAR(255) DEFAULT '',
                                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                            ) ENGINE=InnoDB
                        """)
                        for f in self.flags.values():
                            c.execute(
                                "INSERT INTO feature_flags (name, enabled, description) VALUES (%s, %s, %s)",
                                (f.name, 1 if f.default else 0, f.description),
                            )
                        conn.commit()
                        logger.info('[FLAG] feature_flags 表已创建')
                    else:
                        c.execute("SELECT name, enabled FROM feature_flags")
                        for row in c.fetchall():
                            name = row[0]
                            enabled = bool(row[1])
                            if name in self.flags:
                                self.flags[name].value = enabled
                        logger.info(f'[FLAG] 重新加载 {len(self.flags)} 个 flag')
            finally:
                conn.close()
        except Exception as e:
            logger.warning(f'[FLAG] 加载失败，使用默认配置: {e}')

    def set_flag(self, name: str, enabled: bool):
        """运行时切换 flag（持久化到 MySQL）"""
        if name not in self.flags:
            raise ValueError(f'未知 flag: {name}')
        try:
            conn = MySQLStorage.get_connection()
            try:
                with conn.cursor() as c:
                    c.execute(
                        "UPDATE feature_flags SET enabled=%s, updated_at=NOW() WHERE name=%s",
                        (1 if enabled else 0, name),
                    )
                    if c.rowcount == 0:
                        c.execute(
                            "INSERT INTO feature_flags (name, enabled) VALUES (%s, %s)",
                            (name, 1 if enabled else 0),
                        )
                conn.commit()
            finally:
                conn.close()
            if enabled:
                self.flags[name].enable()
            else:
                self.flags[name].disable()
        except Exception as e:
            logger.error(f'[FLAG] 切换 {name} 失败: {e}')
            raise

    def is_enabled(self, name: str) -> bool:
        """查询 flag 状态"""
        if name not in self.flags:
            return False
        return self.flags[name].is_enabled()

    def get_all(self) -> Dict[str, bool]:
        """获取所有 flag 状态"""
        return {name: f.is_enabled() for name, f in self.flags.items()}

    def maybe_reload(self, interval_sec: int = 30):
        """定期重新加载（每 30s 调用一次）"""
        now = time.time()
        if now - self._last_reload > interval_sec:
            self.reload()
            self._last_reload = now


# 便捷函数
def is_use_local_mirror() -> bool:
    """业务层读镜像表开关"""
    return FeatureFlagManager.get_instance().is_enabled('use_local_mirror')


def is_use_outbox_fallback() -> bool:
    """outbox 兜底开关"""
    return FeatureFlagManager.get_instance().is_enabled('use_outbox_fallback')


def is_enable_etl_sync() -> bool:
    """ETL 同步开关"""
    return FeatureFlagManager.get_instance().is_enabled('enable_etl_sync')


def is_enable_outbox_worker() -> bool:
    """outbox worker 开关"""
    return FeatureFlagManager.get_instance().is_enabled('enable_outbox_worker')
