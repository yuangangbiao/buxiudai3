
import os
import sys
sys.path.insert(0, '.')

from security.license_binding import LicenseBinding

print('正在删除旧的激活文件...')

files_to_delete = [
    LicenseBinding._get_binding_path(),
    LicenseBinding._get_salt_path(),
]

for f in files_to_delete:
    try:
        if os.path.exists(f):
            os.remove(f)
            print(f'已删除: {f}')
        else:
            print(f'不存在: {f}')
    except Exception as e:
        print(f'删除 {f} 失败: {e}')

print('\n检查 APPDATA 和 LOCALAPPDATA:')
dirs = [
    os.path.join(os.environ.get("APPDATA", ""), "SteelBeltLicense"),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "SteelBeltLicense"),
]

for d in dirs:
    if os.path.exists(d):
        for f in ['.license_binding', '.license_salt', '.license_activation']:
            path = os.path.join(d, f)
            try:
                if os.path.exists(path):
                    os.remove(path)
                    print(f'已删除: {path}')
            except Exception as e:
                print(f'删除 {path} 失败: {e}')

print('\n清理完成！')
