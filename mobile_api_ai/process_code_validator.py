# -*- coding: utf-8 -*-
"""
R13 任务9: process_code SSOT 校验工具

18个端点共享的 process_code 校验逻辑 + 违规写入。
使用方式:
    from mobile_api_ai.process_code_validator import validate_and_log
    ok, code, msg = validate_and_log(scenario, process_code, process_name, order_no)
    if not ok:
        return fail(code=1002, message=msg)
    # 继续业务逻辑...
"""
import logging
from typing import Optional, Tuple

from core._config_domain import get_process_code

_logger = logging.getLogger(__name__)


def validate_process_code(
    scenario: str,
    process_code: Optional[str],
    process_name: Optional[str],
    order_no: Optional[str] = None,
) -> Tuple[bool, str, str]:
    """
    校验 process_code 是否合法，非法时写入 violation_log。

    Args:
        scenario: 端点/场景标识（如 'dispatch_task'）
        process_code: 传入的工序编码（可为 None/空字符串）
        process_name: 传入的工序名称（用于自动推导）
        order_no: 关联工单号（可选）

    Returns:
        (is_valid, resolved_code, message)
        - is_valid=True / resolved_code=有效编码 / message='' → 合法
        - is_valid=False / resolved_code='' / message=错误原因 → 非法（已写violation_log）
    """
    code = (process_code or '').strip() if process_code else ''
    name = (process_name or '').strip() if process_name else ''

    # 无编码也无名称 → 严重违规
    if not code and not name:
        _write_violation(
            scenario=scenario,
            violation_type='missing_process_code',
            severity='ERROR',
            order_no=order_no,
            detail='process_code 和 process_name 均未提供'
        )
        return False, '', '缺少 process_code 和 process_name'

    # 有名称但无编码 → 尝试从内存映射推导
    if not code and name:
        mapped = get_process_code(name)
        if mapped:
            _logger.debug(f'[{scenario}] 自动推导 process_code: {name} → {mapped}')
            return True, mapped, ''
        else:
            _write_violation(
                scenario=scenario,
                violation_type='no_process_code_mapping',
                severity='WARN',
                order_no=order_no,
                detail=f'process_name="{name}" 无对应编码映射'
            )
            return False, '', f'工序 "{name}" 未注册，请先调用 register_process()'

    # 有编码但无名称 → 尝试补全
    if code and not name:
        name = _find_name_by_code(code)
        if name:
            _logger.debug(f'[{scenario}] 自动推导 process_name: {code} → {name}')

    # 验证编码格式
    import re
    if not re.match(r'^[PMQXpmqx][0-9A-Za-z]{1,8}$', code):
        _write_violation(
            scenario=scenario,
            violation_type='invalid_process_code_format',
            severity='WARN',
            order_no=order_no,
            detail=f'process_code="{code}" 格式不合法，期望 P/M/Q/X 开头'
        )
        return False, '', f'process_code 格式不合法: {code}'

    return True, code.upper(), ''


def _find_name_by_code(code: str) -> Optional[str]:
    """根据 process_code 反查 name（标准工序优先）。"""
    from core._config_domain import PROCESS_CODES
    code_upper = code.upper()
    for name, c in PROCESS_CODES.items():
        if c == code_upper:
            return name
    return None


def _write_violation(
    scenario: str,
    violation_type: str,
    severity: str = 'WARN',
    order_no: Optional[str] = None,
    detail: Optional[str] = None,
) -> None:
    """
    将违规写入 violation_log 表（静默降级）。
    """
    import os
    try:
        # [T11 2026-06-14] 走 shim 连接池
        from core.db_compat import get_conn
        conn = get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO violation_log
                    (scenario, violation_type, severity, order_no, detail)
                VALUES (%s, %s, %s, %s, %s)
            """, (scenario, violation_type, severity, order_no, detail))
            conn.commit()
            cursor.close()
        except Exception as ie:
            conn.close()
            raise ie
    except Exception as e:
        _logger.debug('[violation_log] 记录降级: %s', e)
