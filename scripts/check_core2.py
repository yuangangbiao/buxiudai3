"""[调试 v2]"""
import subprocess

# 先获取正确的路径
r = subprocess.run(['git', 'ls-tree', 'HEAD', '-r'], capture_output=True, text=True)
for line in r.stdout.split('\n'):
    if '_core.py' in line and 'dispatch_center' in line:
        # 提取路径
        parts = line.split()
        if len(parts) >= 4:
            path = ' '.join(parts[3:])
            print(f'找到: {path}')
            break

# 用 ls-files 查找
r2 = subprocess.run(['git', 'ls-files', '|', 'findstr', '_core.py'], capture_output=True, text=True, shell=True)
print('ls-files 结果:')
print(r2.stdout)