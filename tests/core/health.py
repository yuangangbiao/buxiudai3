"""增强的服务健康检测"""
import time
import socket
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from tests.core._config import SERVICES  # 修复 A1: 从 _config 导入，消除循环依赖


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    service: str
    port: int
    status: HealthStatus
    latency_ms: float = 0
    http_code: int = 0
    error: Optional[str] = None
    details: Dict = None


class HealthChecker:
    """全服务健康检测器"""
    
    # 服务依赖关系
    DEPENDENCIES = {
        'desktop_web': ['container', 'dispatch'],
        'container': [],
        'dispatch': ['container'],
        'mobile': ['dispatch', 'container'],
        'sync_bridge': ['mobile'],
    }
    
    # 健康端点配置
    HEALTH_ENDPOINTS = {
        'desktop_web': ('GET', '/login', 200),
        'container': ('GET', '/api/health', 200),
        'dispatch': ('GET', '/api/dispatch-center/operators', 200),
        'mobile': ('GET', '/api/health', 200),
        'sync_bridge': ('GET', '/api/sync/catchup_alive', 200),
    }
    
    def __init__(self, timeout: float = 5.0, retry: int = 2):
        self.timeout = timeout
        self.retry = retry
    
    def check_port_open(self, port: int) -> bool:
        """检查端口是否开放"""
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=2):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False
    
    def check_service(self, service: str) -> HealthCheckResult:
        """检查单个服务"""
        url = SERVICES[service]
        method, path, expected_code = self.HEALTH_ENDPOINTS.get(
            service, ('GET', '/', 200)
        )
        full_url = f'{url}{path}'
        
        start = time.time()
        last_error = None
        last_code = 0
        
        for attempt in range(self.retry + 1):
            try:
                r = requests.request(
                    method, full_url,
                    timeout=self.timeout,
                    allow_redirects=True
                )
                latency = (time.time() - start) * 1000
                last_code = r.status_code
                
                if r.status_code == expected_code:
                    return HealthCheckResult(
                        service=service,
                        port=self._extract_port(url),
                        status=HealthStatus.HEALTHY,
                        latency_ms=latency,
                        http_code=r.status_code,
                        details={'attempt': attempt + 1, 'url': full_url}
                    )
                elif r.status_code < 500:
                    return HealthCheckResult(
                        service=service,
                        port=self._extract_port(url),
                        status=HealthStatus.DEGRADED,
                        latency_ms=latency,
                        http_code=r.status_code,
                        details={'attempt': attempt + 1, 'url': full_url}
                    )
                last_error = f"HTTP {r.status_code}"
            except requests.Timeout:
                last_error = f"Timeout after {self.timeout}s"
            except requests.ConnectionError as e:
                last_error = f"Connection error: {str(e)[:50]}"
            except Exception as e:
                last_error = str(e)[:50]
            
            if attempt < self.retry:
                time.sleep(0.5 * (attempt + 1))
        
        return HealthCheckResult(
            service=service,
            port=self._extract_port(url),
            status=HealthStatus.UNHEALTHY,
            latency_ms=(time.time() - start) * 1000,
            http_code=last_code,
            error=last_error
        )
    
    def check_all(self) -> Dict[str, HealthCheckResult]:
        """检查所有服务"""
        results = {}
        for service in SERVICES:
            results[service] = self.check_service(service)
        return results
    
    def check_with_dependencies(self) -> Dict[str, HealthCheckResult]:
        """按依赖关系检查"""
        results = {}
        checked = set()
        
        def _check_recursive(service: str):
            if service in checked:
                return
            # 先检查依赖
            for dep in self.DEPENDENCIES.get(service, []):
                _check_recursive(dep)
            # 再检查本服务
            results[service] = self.check_service(service)
            checked.add(service)
        
        for service in SERVICES:
            _check_recursive(service)
        
        return results
    
    def _extract_port(self, url: str) -> int:
        try:
            return int(url.split(':')[-1].split('/')[0])
        except Exception:
            return 0
    
    def format_report(self, results: Dict[str, HealthCheckResult]) -> str:
        """格式化报告"""
        lines = ["\n" + "=" * 70, "服务健康检查报告", "=" * 70]
        healthy = sum(1 for r in results.values() if r.status == HealthStatus.HEALTHY)
        total = len(results)
        lines.append(f"\n📊 总览: {healthy}/{total} 健康")
        lines.append("-" * 70)
        for service, r in results.items():
            icon = {
                HealthStatus.HEALTHY: '✅',
                HealthStatus.DEGRADED: '⚠️',
                HealthStatus.UNHEALTHY: '❌',
                HealthStatus.UNKNOWN: '❓',
            }[r.status]
            lines.append(
                f"{icon} {service:<15} 端口:{r.port:<6} "
                f"状态:{r.status.value:<10} 延迟:{r.latency_ms:>6.1f}ms "
                f"HTTP:{r.http_code}"
            )
            if r.error:
                lines.append(f"    └─ 错误: {r.error}")
        lines.append("=" * 70)
        return "\n".join(lines)


# 全局实例
health_checker = HealthChecker()
