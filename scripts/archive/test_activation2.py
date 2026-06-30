
import sys
sys.path.insert(0, '.')

from security.license_tool import activate, check_activation
from security.license_manager import LicenseManager
from security.machine_fingerprint import MachineFingerprint
from security.license_generator_gui import generate_license_key

print('=== 步骤1: 检查初始状态 ===')
status1 = check_activation()
print('已激活:', status1['is_activated'])

print('\n=== 步骤2: 生成密钥 ===')
fingerprint = MachineFingerprint.generate()
print('当前指纹:', fingerprint)
license_key = generate_license_key(fingerprint, '测试客户')
print('生成的密钥:', license_key)

print('\n=== 步骤3: 激活 ===')
result = activate(license_key, '测试客户')
print('激活结果:', result)

print('\n=== 步骤4: 验证激活状态 ===')
status2 = check_activation()
print('已激活:', status2['is_activated'])
print('指纹:', status2['fingerprint_short'])

print('\n=== 步骤5: 重新检查 ===')
status3 = check_activation()
print('已激活:', status3['is_activated'])

print('\n=== 步骤6: LicenseManager 检查 ===')
manager = LicenseManager()
status4 = manager.check_activation()
print('已激活:', status4['is_activated'])
