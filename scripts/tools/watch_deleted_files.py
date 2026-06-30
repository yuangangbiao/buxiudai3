#!/usr/bin/env python3
"""
实时监控 data/ 目录中文件被删除的事件
用法: python watch_deleted_files.py
"""
import os
import sys
import time
import threading

WATCH_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data'))
LOG_FILE = os.path.join(os.path.dirname(__file__), 'watch_deleted_files.log')

snapshot = {}

def build_snapshot():
    snap = {}
    if not os.path.exists(WATCH_DIR):
        return snap
    for fname in os.listdir(WATCH_DIR):
        fpath = os.path.join(WATCH_DIR, fname)
        try:
            stat = os.stat(fpath)
            snap[fname] = (stat.st_size, stat.st_mtime, stat.st_ctime)
        except (FileNotFoundError, PermissionError, OSError):
            pass
    return snap

def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')

if __name__ == '__main__':
    log(f"监控目录: {WATCH_DIR}")
    log(f"日志文件: {LOG_FILE}")

    if not os.path.exists(WATCH_DIR):
        log(f"错误: 目录不存在: {WATCH_DIR}")
        sys.exit(1)

    log(f"当前文件列表: {os.listdir(WATCH_DIR)}")
    snapshot = build_snapshot()

    log("开始监控 (每3秒扫描一次, 按 Ctrl+C 停止)...")

    try:
        while True:
            time.sleep(3)
            current = build_snapshot()
            deleted = set(snapshot.keys()) - set(current.keys())
            for fname in sorted(deleted):
                old_stat = snapshot[fname]
                log(f"⚠️ 文件被删除: {fname} (大小={old_stat[0]}, 修改时间={old_stat[1]})")
            snapshot = current
    except KeyboardInterrupt:
        log("监控停止")
