import py_compile
import os

BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                     '云端部署包v1.1.1')

files = ['dispatch_center.py', 'wechat_server.py']
all_ok = True
for f in files:
    path = os.path.join(BASE, f)
    try:
        py_compile.compile(path, doraise=True)
        print(f'{f}: OK')
    except py_compile.PyCompileError as e:
        print(f'{f}: FAIL - {e}')
        all_ok = False

# 检查 config_center.py 是否已删除
cc_path = os.path.join(BASE, 'config_center.py')
if not os.path.exists(cc_path):
    print('config_center.py: DELETED')
else:
    print('config_center.py: STILL EXISTS')
    all_ok = False

print()
print('ALL CHECKS PASSED' if all_ok else 'SOME CHECKS FAILED')
exit(0 if all_ok else 1)
