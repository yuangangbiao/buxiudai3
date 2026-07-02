# -*- coding: utf-8 -*-
"""
ci/wait_5009.py - 等待人脸扫描服务启动
"""
import sys, time, requests

def wait_service(port, name, timeout=120):
    url = f'http://127.0.0.1:{port}/'
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=3)
            if r.status_code < 500:
                print(f'✅ {name} 已就绪 ({port}) in {time.time()-start:.1f}s')
                return 0
        except requests.exceptions.ConnectionError:
            pass
        except Exception:
            pass
        time.sleep(2)
    print(f'❌ {name} 启动超时 ({timeout}s)')
    return 1

if __name__ == '__main__':
    sys.exit(wait_service(5009, '人脸扫描'))
