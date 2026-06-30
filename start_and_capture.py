#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
import sys
import os
import threading
import time

PYTHON = sys.executable
SCRIPT = r"d:\yuan\不锈钢网带跟单3.0\bootstrap.py"

# 使用 Popen 直接启动
proc = subprocess.Popen(
    [PYTHON, SCRIPT],
    cwd=r"d:\yuan\不锈钢网带跟单3.0",
    stdin=subprocess.DEVNULL,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

# 实时输出
try:
    while proc.poll() is None:
        line = proc.stdout.readline()
        if line:
            print(line, end='')
except Exception as e:
    print(f"异常: {e}")
finally:
    proc.wait()

print(f"\n退出码: {proc.returncode}")
