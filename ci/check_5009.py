# -*- coding: utf-8 -*-
"""
ci/check_5009.py - 5009人脸扫描健康检查
"""
import requests, sys

def check(port, name):
    try:
        r = requests.get(f'http://127.0.0.1:{port}/', timeout=10)
        if r.status_code < 500:
            print(f'✅ {name} 健康检查通过 (HTTP {r.status_code})')
            return 0
        else:
            print(f'❌ {name} 返回 {r.status_code}')
            return 1
    except Exception as e:
        print(f'❌ {name} 连接失败: {e}')
        return 1

if __name__ == '__main__':
    sys.exit(check(5009, '5009 人脸扫描'))
