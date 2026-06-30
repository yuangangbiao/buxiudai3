# -*- coding: utf-8 -*-
"""
健康检查器主系统集成模块

为桌面端提供依赖组件健康检查能力
基于 mobile_api_ai/modules/health_checker.py 封装
"""

import os
import time
import logging
import socket
from typing import Optional, Dict, Any, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class SystemHealthStatus(Enum):
    """系统健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HealthCheckResult:
    """健康检查结果"""

    def __init__(
        self,
        status: SystemHealthStatus,
        message: str,
        latency_ms: float = 0,
        details: Optional[Dict[str, Any]] = None
    ):
        self.status = status
        self.message = message
        self.latency_ms = latency_ms
        self.details = details or {}
        self.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> dict:
        return {
            'status': self.status.value,
            'message': self.message,
            'latency_ms': round(self.latency_ms, 2),
            'details': self.details,
            'timestamp': self.timestamp
        }

    def __bool__(self) -> bool:
        return self.status == SystemHealthStatus.HEALTHY


class MySQLHealthChecker:
    """MySQL数据库健康检查"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """从环境变量或配置加载"""
        return {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'port': int(os.getenv('MYSQL_PORT', '3306')),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'database': os.getenv('MYSQL_DATABASE', 'steel_belt')
        }

    def check(self) -> HealthCheckResult:
        """执行MySQL健康检查"""
        start_time = time.time()

        try:
            from core.db import get_direct_connection

            conn = get_direct_connection(**self.config, connect_timeout=5)
            cursor = conn.cursor()

            cursor.execute("SELECT 1")
            cursor.fetchone()

            cursor.execute("SHOW TABLE STATUS")
            table_count = len(cursor.fetchall())

            cursor.close()
            conn.close()

            latency = (time.time() - start_time) * 1000

            return HealthCheckResult(
                status=SystemHealthStatus.HEALTHY,
                message=f"MySQL运行正常 (延迟{latency:.1f}ms)",
                latency_ms=latency,
                details={
                    'host': self.config['host'],
                    'database': self.config['database'],
                    'table_count': table_count
                }
            )

        except ImportError:
            return HealthCheckResult(
                status=SystemHealthStatus.UNKNOWN,
                message="pymysql模块未安装，跳过MySQL检查",
                latency_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            logger.error(f"MySQL健康检查失败: {e}")
            return HealthCheckResult(
                status=SystemHealthStatus.UNHEALTHY,
                message=f"MySQL连接失败: {str(e)[:50]}",
                latency_ms=latency,
                details={'host': self.config['host'], 'error': str(e)}
            )


class SQLiteHealthChecker:
    """SQLite数据库健康检查"""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or self._get_default_db_path()

    def _get_default_db_path(self) -> str:
        """获取默认数据库路径"""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, 'data', 'steel_belt.db')

    def check(self) -> HealthCheckResult:
        """执行SQLite健康检查"""
        start_time = time.time()

        try:
            import sqlite3

            if not os.path.exists(self.db_path):
                return HealthCheckResult(
                    status=SystemHealthStatus.UNHEALTHY,
                    message=f"数据库文件不存在: {self.db_path}",
                    latency_ms=(time.time() - start_time) * 1000
                )

            conn = sqlite3.connect(self.db_path, timeout=5)
            cursor = conn.cursor()

            cursor.execute("SELECT 1")
            cursor.fetchone()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            table_count = len(cursor.fetchall())

            cursor.execute("PRAGMA integrity_check")
            integrity = cursor.fetchone()[0]

            conn.close()

            latency = (time.time() - start_time) * 1000

            return HealthCheckResult(
                status=SystemHealthStatus.HEALTHY if integrity == 'ok' else SystemHealthStatus.DEGRADED,
                message=f"SQLite运行正常 (延迟{latency:.1f}ms)",
                latency_ms=latency,
                details={
                    'path': self.db_path,
                    'table_count': table_count,
                    'integrity': integrity
                }
            )

        except ImportError:
            return HealthCheckResult(
                status=SystemHealthStatus.UNKNOWN,
                message="sqlite3模块不可用",
                latency_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            logger.error(f"SQLite健康检查失败: {e}")
            return HealthCheckResult(
                status=SystemHealthStatus.UNHEALTHY,
                message=f"SQLite检查失败: {str(e)[:50]}",
                latency_ms=latency,
                details={'path': self.db_path, 'error': str(e)}
            )


class NetworkHealthChecker:
    """网络连通性健康检查"""

    def __init__(self, targets: Optional[Dict[str, str]] = None):
        self.targets = targets or self._get_default_targets()

    def _get_default_targets(self) -> Dict[str, str]:
        """获取默认检查目标"""
        return {
            'gateway': os.getenv('DEFAULT_GATEWAY', '192.168.1.1'),
            'dns': os.getenv('DNS_SERVER', '8.8.8.8')
        }

    def check_host(self, host: str, port: int = 80, timeout: float = 3.0) -> bool:
        """检查主机连通性"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def check(self) -> HealthCheckResult:
        """执行网络健康检查"""
        start_time = time.time()

        results = {}
        all_healthy = True

        for name, host in self.targets.items():
            if name == 'dns':
                reachable = self.check_host(host, 53)
            else:
                reachable = self.check_host(host, 80)

            results[name] = {
                'host': host,
                'reachable': reachable
            }

            if not reachable:
                all_healthy = False

        latency = (time.time() - start_time) * 1000

        if all_healthy:
            return HealthCheckResult(
                status=SystemHealthStatus.HEALTHY,
                message="网络连接正常",
                latency_ms=latency,
                details=results
            )
        else:
            failed = [k for k, v in results.items() if not v['reachable']]
            return HealthCheckResult(
                status=SystemHealthStatus.DEGRADED,
                message=f"部分网络目标不可达: {', '.join(failed)}",
                latency_ms=latency,
                details=results
            )


class SystemResourceHealthChecker:
    """系统资源健康检查"""

    def __init__(
        self,
        cpu_warning_threshold: float = 80.0,
        memory_warning_threshold: float = 85.0,
        disk_warning_threshold: float = 90.0
    ):
        self.cpu_threshold = cpu_warning_threshold
        self.memory_threshold = memory_warning_threshold
        self.disk_threshold = disk_warning_threshold

    def check(self) -> HealthCheckResult:
        """执行系统资源健康检查"""
        start_time = time.time()

        try:
            import psutil

            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            results = {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_mb': round(memory.available / 1024 / 1024, 2),
                'disk_percent': disk.percent,
                'disk_free_gb': round(disk.free / 1024 / 1024 / 1024, 2)
            }

            issues = []
            if cpu_percent > self.cpu_threshold:
                issues.append(f"CPU使用率过高({cpu_percent:.1f}%)")
            if memory.percent > self.memory_threshold:
                issues.append(f"内存使用率过高({memory.percent:.1f}%)")
            if disk.percent > self.disk_threshold:
                issues.append(f"磁盘使用率过高({disk.percent:.1f}%)")

            latency = (time.time() - start_time) * 1000

            if not issues:
                return HealthCheckResult(
                    status=SystemHealthStatus.HEALTHY,
                    message="系统资源正常",
                    latency_ms=latency,
                    details=results
                )
            else:
                return HealthCheckResult(
                    status=SystemHealthStatus.DEGRADED,
                    message=f"资源警告: {', '.join(issues)}",
                    latency_ms=latency,
                    details=results
                )

        except ImportError:
            return HealthCheckResult(
                status=SystemHealthStatus.UNKNOWN,
                message="psutil模块未安装，跳过系统资源检查",
                latency_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            logger.error(f"系统资源检查失败: {e}")
            return HealthCheckResult(
                status=SystemHealthStatus.UNKNOWN,
                message=f"系统资源检查失败: {str(e)[:50]}",
                latency_ms=latency
            )


class HealthCheckerManager:
    """健康检查管理器"""

    def __init__(self):
        self.checkers: Dict[str, Callable[[], HealthCheckResult]] = {}
        self._register_default_checkers()

    def _register_default_checkers(self) -> None:
        """注册默认检查器"""
        self.register_checker('mysql', MySQLHealthChecker())
        self.register_checker('sqlite', SQLiteHealthChecker())
        self.register_checker('network', NetworkHealthChecker())
        self.register_checker('system', SystemResourceHealthChecker())

    def register_checker(self, name: str, checker) -> None:
        """注册检查器"""
        if hasattr(checker, 'check') and callable(checker.check):
            self.checkers[name] = checker.check
            logger.info(f"健康检查器注册: {name}")

    def unregister_checker(self, name: str) -> None:
        """注销检查器"""
        if name in self.checkers:
            del self.checkers[name]
            logger.info(f"健康检查器注销: {name}")

    def check(self, name: str) -> Optional[HealthCheckResult]:
        """执行指定检查"""
        if name not in self.checkers:
            logger.warning(f"未找到健康检查器: {name}")
            return None

        try:
            return self.checkers[name]()
        except Exception as e:
            logger.error(f"健康检查执行失败 [{name}]: {e}")
            return HealthCheckResult(
                status=SystemHealthStatus.UNHEALTHY,
                message=f"检查执行失败: {str(e)[:50]}"
            )

    def check_all(self) -> Dict[str, HealthCheckResult]:
        """执行所有检查"""
        results = {}
        for name in self.checkers:
            result = self.check(name)
            if result:
                results[name] = result
        return results

    def get_overall_status(self) -> SystemHealthStatus:
        """获取整体健康状态"""
        results = self.check_all()
        if not results:
            return SystemHealthStatus.UNKNOWN

        statuses = [r.status for r in results.values()]

        if any(s == SystemHealthStatus.UNHEALTHY for s in statuses):
            return SystemHealthStatus.UNHEALTHY
        elif any(s == SystemHealthStatus.DEGRADED for s in statuses):
            return SystemHealthStatus.DEGRADED
        elif all(s == SystemHealthStatus.HEALTHY for s in statuses):
            return SystemHealthStatus.HEALTHY
        else:
            return SystemHealthStatus.UNKNOWN


_health_manager_instance = None


def get_health_checker_manager() -> HealthCheckerManager:
    """获取健康检查管理器单例"""
    global _health_manager_instance
    if _health_manager_instance is None:
        _health_manager_instance = HealthCheckerManager()
    return _health_manager_instance


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    manager = get_health_checker_manager()

    print("=" * 60)
    print("健康检查器集成模块测试")
    print("=" * 60)

    print("\n--- 单项检查 ---")
    for name in ['sqlite', 'network', 'system']:
        result = manager.check(name)
        if result:
            print(f"{name}: [{result.status.value}] {result.message}")

    print("\n--- 整体状态 ---")
    overall = manager.get_overall_status()
    print(f"整体状态: {overall.value}")

    print("\n--- 所有检查结果 ---")
    for name, result in manager.check_all().items():
        print(f"{name}: {result.to_dict()}")

    print("\n" + "=" * 60)
