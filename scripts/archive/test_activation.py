
import sys
sys.path.insert(0, '.')

from security.license_manager import LicenseManager
from security.license_binding import LicenseBinding
from security.machine_fingerprint import MachineFingerprint

print('=== 步骤1: 检查初始状态 ===')
manager = LicenseManager()
status1 = manager.check_activation()
print('已激活:', status1['is_activated'])

print('\n=== 步骤2: 生成测试密钥 ===')
test_key = manager.generate_trial_key()
print('生成的密钥:', test_key)

print('\n=== 步骤3: 激活 ===')
result = manager.activate_license(test_key, '测试客户')
print('激活结果:', result)

print('\n=== 步骤4: 验证激活状态 ===')
status2 = manager.check_activation()
print('已激活:', status2['is_activated'])
print('指纹:', status2['fingerprint_short'])
print('客户:', status2.get('customer_name', 'N/A'))

print('\n=== 步骤5: 重新实例化，检查是否持久化 ===')
del manager
manager2 = LicenseManager()
status3 = manager2.check_activation()
print('已激活:', status3['is_activated'])  # 这里应该是 True！
print('指纹:', status3['fingerprint_short'])

print('\n=== 步骤6: 检查绑定文件 ===')
binding_path = LicenseBinding._get_binding_path()
import os
print('文件路径:', binding_path)
print('文件存在:', os.path.exists(binding_path))
if os.path.exists(binding_path):
    binding = LicenseBinding.load_binding()
    print('绑定内容:', binding)
