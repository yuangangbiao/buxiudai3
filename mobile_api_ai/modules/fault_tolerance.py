#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FaultTolerance 模块重导出包装器

本模块从根目录 fault_tolerance.py 重导出所有公共接口，
确保 modules.fault_tolerance 导入路径可用。
"""

from fault_tolerance import (
    CircuitState,
    RetryConfig,
    FaultToleranceMetrics,
    FaultTolerance,
    fault_tolerance,
)

__all__ = [
    'CircuitState',
    'RetryConfig',
    'FaultToleranceMetrics',
    'FaultTolerance',
    'fault_tolerance',
]
