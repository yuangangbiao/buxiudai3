#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import socket

host = os.getenv('CHECK_HOST', '124.223.57.82')
ports = [22, 2222, 5003, 5005, 80, 443, 8080, 9090]

for port in ports:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    result = s.connect_ex((host, port))
    if result == 0:
        print(f'  ✅ 端口 {port} 开放')
    else:
        print(f'  ❌ 端口 {port} 关闭')
    s.close()
