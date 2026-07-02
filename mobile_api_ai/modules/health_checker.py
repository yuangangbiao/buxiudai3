#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""详细健康检查模块 - 含依赖组件检查、性能指标、系统资源监控"""

import os
import time
import psutil
import logging
import subprocess
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import redis
from elasticsearch import Elasticsearch
import socket

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    status: HealthStatus
    message: str
    latency_ms: float = 0
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ComponentHealthChecker:
    """组件健康检查基类"""

    def __init__(self, name: str, timeout: float = 5.0):
        self.name = name
        self.timeout = min(timeout, 1.0)  # 最大超时1秒，避免长时间阻塞

    def check(self) -> HealthCheckResult:
        """执行检查"""
        raise NotImplementedError


class RedisHealthChecker(ComponentHealthChecker):
    """Redis健康检查"""

    def __init__(self, redis_client: Optional[redis.Redis] = None,
                 password: Optional[str] = None,
                 host: str = 'localhost',
                 port: int = 6379):
        super().__init__("redis")
        self.redis_client = redis_client
        self.password = password
        self.host = host
        self.port = port

    def check(self) -> HealthCheckResult:
        start_time = time.time()
        try:
            if self.redis_client is None:
                self.redis_client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    password=self.password,
                    socket_timeout=self.timeout
                )

            start_check = time.time()
            self.redis_client.ping()
            latency = (time.time() - start_check) * 1000

            info = self.redis_client.info()
            info_keys = ['used_memory_human', 'connected_clients', 'uptime_in_days']

            details = {k: info.get(k) for k in info_keys if k in info}

            memory_used_mb = info.get('used_memory', 0) / 1024 / 1024
            maxmemory_mb = info.get('maxmemory', 0) / 1024 / 1024

            if maxmemory_mb > 0:
                details['memory_usage_percent'] = round(memory_used_mb / maxmemory_mb * 100, 2)

            if info.get('role') == 'master':
                details['master'] = True
                slave_info = self.redis_client.info('replication')
                details['connected_slaves'] = slave_info.get('connected_slaves', 0)
            else:
                details['master'] = False

            status = HealthStatus.HEALTHY
            message = f"Redis运行正常 (延迟{latency:.1f}ms)"

            if details.get('memory_usage_percent', 0) > 90:
                status = HealthStatus.DEGRADED
                message = f"Redis内存使用率过高 ({details['memory_usage_percent']:.1f}%)"

        except redis.ConnectionError as e:
            latency = (time.time() - start_time) * 1000
            status = HealthStatus.UNHEALTHY
            message = f"Redis连接失败: {str(e)}"
            details = {'error': str(e)}
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            status = HealthStatus.UNHEALTHY
            message = f"Redis检查失败: {str(e)}"
            details = {'error': str(e)}

        return HealthCheckResult(
            status=status,
            message=message,
            latency_ms=latency,
            details=details
        )


class ElasticsearchHealthChecker(ComponentHealthChecker):
    """Elasticsearch健康检查"""

    def __init__(self, es_hosts: Optional[list] = None):
        super().__init__("elasticsearch")
        self.es_hosts = es_hosts or os.environ.get('ES_HOSTS', 'localhost:9200').split(',')

    def check(self) -> HealthCheckResult:
        start_time = time.time()
        try:
            es = Elasticsearch(self.es_hosts, request_timeout=self.timeout)

            health = es.cluster.health(timeout=self.timeout)

            status_map = {
                'green': HealthStatus.HEALTHY,
                'yellow': HealthStatus.DEGRADED,
                'red': HealthStatus.UNHEALTHY
            }
            status = status_map.get(health['status'], HealthStatus.UNKNOWN)

            details = {
                'cluster_name': health.get('cluster_name'),
                'cluster_status': health.get('status'),
                'number_of_nodes': health.get('number_of_nodes'),
                'number_of_pending_tasks': health.get('number_of_pending_tasks'),
                'active_shards': health.get('active_shards'),
                'relocating_shards': health.get('relocating_shards'),
                'active_primary_shards': health.get('active_primary_shards')
            }

            if health['status'] == 'red':
                message = f"ES集群状态异常 ({health['status']})"
            elif health['status'] == 'yellow':
                message = f"ES集群状态警告 ({health['status']})"
            else:
                message = f"ES集群运行正常"

            latency = (time.time() - start_time) * 1000

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            status = HealthStatus.UNHEALTHY
            message = f"ES检查失败: {str(e)}"
            details = {'error': str(e)}

        return HealthCheckResult(
            status=status,
            message=message,
            latency_ms=latency,
            details=details
        )


class SystemResourceChecker(ComponentHealthChecker):
    """系统资源检查"""

    def __init__(self):
        super().__init__("system")

    def check(self) -> HealthCheckResult:
        start_time = time.time()

        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            details = {
                'cpu_percent': cpu_percent,
                'cpu_count': psutil.cpu_count(),
                'memory_total_gb': round(memory.total / 1024**3, 2),
                'memory_used_gb': round(memory.used / 1024**3, 2),
                'memory_percent': memory.percent,
                'disk_total_gb': round(disk.total / 1024**3, 2),
                'disk_used_gb': round(disk.used / 1024**3, 2),
                'disk_percent': disk.percent
            }

            status = HealthStatus.HEALTHY
            message_parts = []

            if cpu_percent > 90:
                status = HealthStatus.DEGRADED
                message_parts.append(f"CPU使用率过高({cpu_percent:.1f}%)")

            if memory.percent > 90:
                status = HealthStatus.DEGRADED
                message_parts.append(f"内存使用率过高({memory.percent:.1f}%)")

            if disk.percent > 90:
                status = HealthStatus.DEGRADED
                message_parts.append(f"磁盘使用率过高({disk.percent:.1f}%)")

            if status == HealthStatus.HEALTHY:
                message = "系统资源正常"
            else:
                message = ", ".join(message_parts)

            latency = (time.time() - start_time) * 1000

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            status = HealthStatus.UNKNOWN
            message = f"系统资源检查失败: {str(e)}"
            details = {'error': str(e)}

        return HealthCheckResult(
            status=status,
            message=message,
            latency_ms=latency,
            details=details
        )


class NetworkChecker(ComponentHealthChecker):
    """网络连接检查"""

    def __init__(self, check_hosts: Optional[list] = None):
        super().__init__("network")
        self.check_hosts = check_hosts or self._default_check_hosts()

    @staticmethod
    def _default_check_hosts() -> list:
        """从环境变量获取默认检查目标"""
        raw = os.environ.get('HEALTH_CHECK_HOSTS', '')
        if raw:
            hosts = []
            for part in raw.split(','):
                part = part.strip()
                if ':' in part:
                    host, port_str = part.rsplit(':', 1)
                    try:
                        hosts.append((host, int(port_str)))
                    except ValueError:
                        continue
            if hosts:
                return hosts
        return [
            ('localhost', 5003),
            ('localhost', 6379),
            ('localhost', 9200)
        ]

    def check(self) -> HealthCheckResult:
        start_time = time.time()
        details = {'connections': []}
        all_healthy = True

        for host, port in self.check_hosts:
            try:
                sock = None
                for family in [socket.AF_INET, socket.AF_INET6, socket.AF_UNIX]:
                    try:
                        sock = socket.socket(family, socket.SOCK_STREAM)
                        sock.settimeout(2)
                        result = sock.connect_ex((host, port))
                        sock.close()

                        details['connections'].append({
                            'host': host,
                            'port': port,
                            'status': 'ok' if result == 0 else 'error',
                            'error_code': result
                        })

                        if result != 0:
                            all_healthy = False
                        break
                    except Exception as e:
                        logger.debug(f"Redis连接尝试失败 {host}:{port} - {e}")
                        continue

            except Exception as e:
                details['connections'].append({
                    'host': host,
                    'port': port,
                    'status': 'error',
                    'error': str(e)
                })
                all_healthy = False

        status = HealthStatus.HEALTHY if all_healthy else HealthStatus.DEGRADED
        message = f"网络连接正常" if all_healthy else "部分连接异常"
        latency = (time.time() - start_time) * 1000

        return HealthCheckResult(
            status=status,
            message=message,
            latency_ms=latency,
            details=details
        )


class ProcessChecker(ComponentHealthChecker):
    """进程检查"""

    def __init__(self, process_names: Optional[list] = None):
        super().__init__("process")
        self.process_names = process_names or [
            'wechat_bot',
            'redis-server',
            'nginx',
            'prometheus',
            'grafana-server'
        ]

    def check(self) -> HealthCheckResult:
        start_time = time.time()
        details = {'processes': []}
        all_running = True

        for proc_name in self.process_names:
            try:
                for proc in psutil.process_iter(['pid', 'name', 'status']):
                    try:
                        if proc_name.lower() in proc.info['name'].lower():
                            details['processes'].append({
                                'name': proc_name,
                                'pid': proc.info['pid'],
                                'status': 'running',
                                'memory_mb': round(proc.memory_info().rss / 1024 / 1024, 2)
                            })
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                else:
                    details['processes'].append({
                        'name': proc_name,
                        'status': 'not_found'
                    })
                    all_running = False
            except Exception as e:
                details['processes'].append({
                    'name': proc_name,
                    'status': 'error',
                    'error': str(e)
                })
                all_running = False

        status = HealthStatus.HEALTHY if all_running else HealthStatus.DEGRADED
        message = f"进程运行正常" if all_running else "部分进程未运行"
        latency = (time.time() - start_time) * 1000

        return HealthCheckResult(
            status=status,
            message=message,
            latency_ms=latency,
            details=details
        )


class ClockSyncChecker(ComponentHealthChecker):
    """时钟同步检查"""

    def __init__(self, ntp_server: str = 'ntp.aliyun.com', max_offset: float = 5.0):
        super().__init__("clock_sync")
        self.ntp_server = ntp_server
        self.max_offset = max_offset

    def check(self) -> HealthCheckResult:
        start_time = time.time()
        try:
            import ntplib
            client = ntplib.NTPClient()
            response = client.request(self.ntp_server, version=3, timeout=self.timeout)

            offset = abs(response.offset)
            details = {
                'ntp_server': self.ntp_server,
                'offset_seconds': round(response.offset, 3),
                'delay_ms': round(response.delay * 1000, 3),
                'stratum': response.stratum
            }

            if offset > self.max_offset:
                status = HealthStatus.DEGRADED
                message = f"时钟偏移过大 ({offset:.2f}秒)"
            else:
                status = HealthStatus.HEALTHY
                message = f"时钟同步正常 (偏移{offset:.2f}秒)"

            latency = (time.time() - start_time) * 1000

        except ImportError:
            status = HealthStatus.UNKNOWN
            message = "ntplib未安装，跳过检查"
            details = {'error': 'ntplib not installed'}
            latency = (time.time() - start_time) * 1000
        except Exception as e:
            status = HealthStatus.DEGRADED
            message = f"时钟同步检查失败: {str(e)}"
            details = {'error': str(e)}
            latency = (time.time() - start_time) * 1000

        return HealthCheckResult(
            status=status,
            message=message,
            latency_ms=latency,
            details=details
        )


class DetailedHealthChecker:
    """详细健康检查器（统一管理所有检查项）"""

    def __init__(self, redis_client=None, redis_host='localhost', redis_port=None, es_hosts=None):
        self.start_time = time.time()
        self.checkers = {}

        self.register_checker('redis', RedisHealthChecker(
            redis_client=redis_client,
            host=os.environ.get('REDIS_HOST', redis_host),
            port=int(os.environ.get('REDIS_PORT', redis_port or '6379'))
        ))
        self.register_checker('elasticsearch', ElasticsearchHealthChecker(
            es_hosts=es_hosts or os.environ.get('ES_HOSTS', 'localhost:9200').split(',')
        ))
        self.register_checker('system', SystemResourceChecker())
        self.register_checker('network', NetworkChecker())
        self.register_checker('process', ProcessChecker())
        self.register_checker('clock_sync', ClockSyncChecker())

    def register_checker(self, name: str, checker: ComponentHealthChecker):
        """注册检查器"""
        self.checkers[name] = checker
        logger.info(f"Registered health checker: {name}")

    def unregister_checker(self, name: str):
        """注销检查器"""
        if name in self.checkers:
            del self.checkers[name]

    def check_single(self, name: str) -> HealthCheckResult:
        """检查单个组件"""
        if name not in self.checkers:
            return HealthCheckResult(
                status=HealthStatus.UNKNOWN,
                message=f"检查器不存在: {name}"
            )

        try:
            return self.checkers[name].check()
        except Exception as e:
            logger.error(f"健康检查失败 [{name}]: {e}")
            return HealthCheckResult(
                status=HealthStatus.UNKNOWN,
                message=f"检查执行失败: {str(e)}"
            )

    def check_all(self, parallel_timeout: float = 3.0) -> Dict[str, HealthCheckResult]:
        """检查所有组件，并发执行并带超时控制"""
        results = {}
        from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed

        executor = ThreadPoolExecutor(max_workers=len(self.checkers))
        future_map = {
            executor.submit(self.check_single, name): name
            for name in self.checkers
        }
        try:
            for future in as_completed(future_map, timeout=parallel_timeout):
                name = future_map[future]
                try:
                    results[name] = future.result()
                except Exception as e:
                    logger.error(f"健康检查异常 [{name}]: {e}")
                    results[name] = HealthCheckResult(
                        status=HealthStatus.UNKNOWN,
                        message=f"检查异常: {str(e)}"
                    )
        except TimeoutError:
            logger.warning("部分健康检查超时")
            # 为未返回结果的检查器设置超时状态
            for future, name in future_map.items():
                if name not in results:
                    results[name] = HealthCheckResult(
                        status=HealthStatus.UNKNOWN,
                        message="检查超时（服务不可达）",
                        latency_ms=parallel_timeout * 1000
                    )
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        return results

    def get_overall_status(self, results: Optional[Dict[str, HealthCheckResult]] = None) -> HealthStatus:
        """获取整体状态"""
        if results is None:
            results = self.check_all()

        if not results:
            return HealthStatus.UNKNOWN

        statuses = [r.status for r in results.values()]

        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED
        elif any(s == HealthStatus.UNKNOWN for s in statuses):
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY

    def get_health_report(self, detailed: bool = True) -> Dict[str, Any]:
        """
        获取完整健康报告

        Args:
            detailed: 是否包含详细信息

        Returns:
            健康报告字典
        """
        results = self.check_all()
        overall_status = self.get_overall_status(results)

        report = {
            'status': overall_status.value,
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': round(time.time() - self.start_time, 2),
            'total_checks': len(results),
            'checks': {}
        }

        status_counts = {
            'healthy': 0,
            'degraded': 0,
            'unhealthy': 0,
            'unknown': 0
        }

        for name, result in results.items():
            status_counts[result.status.value] += 1

            if detailed:
                report['checks'][name] = {
                    'status': result.status.value,
                    'message': result.message,
                    'latency_ms': round(result.latency_ms, 2),
                    'details': result.details
                }
            else:
                report['checks'][name] = {
                    'status': result.status.value,
                    'message': result.message
                }

        report['summary'] = status_counts

        return report


_global_health_checker = None


def init_health_checker() -> DetailedHealthChecker:
    """初始化全局健康检查器"""
    global _global_health_checker
    _global_health_checker = DetailedHealthChecker()
    return _global_health_checker


def get_health_checker() -> DetailedHealthChecker:
    """获取全局健康检查器"""
    global _global_health_checker
    if _global_health_checker is None:
        _global_health_checker = DetailedHealthChecker()
    return _global_health_checker


def get_simple_health_check() -> Dict[str, Any]:
    """获取简单健康检查结果"""
    checker = get_health_checker()
    return checker.get_health_report(detailed=False)


def get_detailed_health_check() -> Dict[str, Any]:
    """获取详细健康检查结果"""
    checker = get_health_checker()
    return checker.get_health_report(detailed=True)
