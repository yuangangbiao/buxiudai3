# -*- coding: utf-8 -*-
"""
[v3.6 迁移] 统一指令处理中间件

DEPRECATED: 请使用 services.instruction_handler
此文件保留用于向后兼容，2026-12-31 将删除
"""
from services.instruction_handler import (
    InstructionSource,
    InstructionType,
    ParsedInstruction,
    InstructionParser,
    ResponseGenerator,
    UnifiedInstructionHandler,
    instruction_handler,
)

__all__ = [
    'InstructionSource',
    'InstructionType',
    'ParsedInstruction',
    'InstructionParser',
    'ResponseGenerator',
    'UnifiedInstructionHandler',
    'instruction_handler',
]
