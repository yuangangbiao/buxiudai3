# -*- coding: utf-8 -*-
"""进程 stdout 监控工具 — 统一 start_all.py 和 dispatch_center/_core.py 的监控函数"""
import threading
import logging


def monitor_process_stdout(proc, name, on_line=None):
    """通用进程 stdout 行迭代器（基础版本，供 start_all.py 使用）

    Args:
        proc: subprocess.Popen 对象
        name: 进程名称（用于日志输出）
        on_line: 行处理回调，签名为 on_line(line: str) -> None
                 若为 None，则打印到 stdout

    使用 iter(readline, '') 而非直接迭代 proc.stdout，
    原因：readline() 在进程结束后返回 ''，iter 会自动停止；
    而 for line in proc.stdout 依赖缓冲，可能漏读最后一帧。
    """
    if on_line is None:
        def default_print(line):
            print(f'[{name}] {line}')
        on_line = default_print

    try:
        for raw in iter(proc.stdout.readline, ''):
            if not raw:
                break
            line = raw.strip()
            if line:
                try:
                    on_line(line)
                except Exception:
                    pass
    except Exception as e:
        try:
            on_line(f'[监控] 进程 {name} 输出读取异常: {e}')
        except Exception:
            pass


def start_monitor_thread(proc, name, logger=None, cleanup_callback=None):
    """启动守护线程监控进程 stdout（完整版本，供 _core.py 使用）

    Args:
        proc: subprocess.Popen 对象
        name: 进程名称
        logger: 日志实例（logging.Logger），若为 None 则用 print
        cleanup_callback: 进程退出时的回调，签名为 callback() -> None

    Returns:
        threading.Thread: 已启动的守护线程
    """
    def _on_line(line):
        if logger:
            logger.info('[%s] %s', name, line)
        else:
            print(f'[{name}] {line}')

    def _target():
        try:
            for raw in iter(proc.stdout.readline, ''):
                if not raw:
                    break
                line = raw.strip()
                if line:
                    _on_line(line)
        except Exception:
            pass
        finally:
            if cleanup_callback:
                try:
                    cleanup_callback()
                except Exception:
                    pass

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    return t
