"""[审计 v2] 精确数 str(e)"""
import re

for path, label in [
    (r'desktop_web\server.py', 'desktop_web/server.py'),
    (r'mobile_api_ai\dispatch_center\_core.py', '_core.py'),
]:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    # 精确模式
    str_e = len(re.findall(r'str\(e\)', content))
    str_exc = len(re.findall(r'str\(exc\)', content))
    str_err = len(re.findall(r'str\(err\)', content))
    str_exception = len(re.findall(r'str\(exception\)', content))
    print(f'{label}:')
    print(f'  str(e): {str_e}')
    print(f'  str(exc): {str_exc}')
    print(f'  str(err): {str_err}')
    print(f'  str(exception): {str_exception}')
    print(f'  总和: {str_e + str_exc + str_err + str_exception}')