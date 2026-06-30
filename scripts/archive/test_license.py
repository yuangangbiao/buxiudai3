
import sys
sys.path.insert(0, '.')
from security.license_manager import LicenseManager
from security.license_binding import LicenseBinding
from security.machine_fingerprint import MachineFingerprint

print('=== 当前状态 ===')
manager = LicenseManager()
status = manager.check_activation()
print('已激活:', status['is_activated'])
print('指纹:', status['fingerprint_short'])

print('\n=== 检查绑定文件 ===')
binding_path = LicenseBinding._get_binding_path()
print('文件路径:', binding_path)
import os
print('文件存在:', os.path.exists(binding_path))
if os.path.exists(binding_path):
    binding = LicenseBinding.load_binding()
    print('绑定内容:', binding)

print('\n=== 检查license_tool.py状态 ===')
from security import license_tool
status2 = license_tool.check_activation()
print('license_tool.py - 已激活:', status2['is_activated'])
print('license_tool.py - 指纹:', status2['fingerprint_short'])
