# -*- coding: utf-8 -*-
"""
中文操作日志工具
在终端实时打印软件操作过程、计算方式、调用方式
"""
import datetime

LOG_ENABLED = True


def _timestamp():
    return datetime.datetime.now().strftime("%H:%M:%S")


def log(module, action, detail=""):
    if not LOG_ENABLED:
        return
    ts = _timestamp()
    line = f"[{ts}] 【{module}】{action}"
    if detail:
        line += f" → {detail}"
    print(line)


def log_step(module, step, action, detail=""):
    if not LOG_ENABLED:
        return
    ts = _timestamp()
    line = f"[{ts}] 【{module}】步骤{step}: {action}"
    if detail:
        line += f" → {detail}"
    print(line)


def log_calc(module, formula, params, result):
    if not LOG_ENABLED:
        return
    ts = _timestamp()
    param_str = ", ".join(f"{k}={v}" for k, v in params.items()) if params else ""
    print(f"[{ts}] 【{module}】计算: 公式=\"{formula}\", 参数=[{param_str}] → 结果={result}")


def log_match(module, process_name, product_type, matched, reason=""):
    if not LOG_ENABLED:
        return
    ts = _timestamp()
    symbol = "✅匹配" if matched else "❌不匹配"
    line = f"[{ts}] 【{module}】工序匹配: 工序=\"{process_name}\", 订单类型=\"{product_type}\" → {symbol}"
    if reason:
        line += f" ({reason})"
    print(line)


def log_sql(module, sql_desc, table, detail=""):
    if not LOG_ENABLED:
        return
    ts = _timestamp()
    line = f"[{ts}] 【{module}】数据库: {sql_desc} 表={table}"
    if detail:
        line += f", {detail}"
    print(line)


def log_error(module, action, error):
    if not LOG_ENABLED:
        return
    ts = _timestamp()
    print(f"[{ts}] 【{module}】❌错误: {action} → {error}")


def log_ui(module, action, detail=""):
    if not LOG_ENABLED:
        return
    ts = _timestamp()
    line = f"[{ts}] 【{module}】用户操作: {action}"
    if detail:
        line += f" → {detail}"
    print(line)
