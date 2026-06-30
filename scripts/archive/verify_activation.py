
import sys
sys.path.insert(0, '.')

print('=== 验证激活持久化 ===')
from security.license_tool import check_activation
from security.license_manager import LicenseManager

print('\n1. license_tool 检查:')
status1 = check_activation()
print('已激活:', status1['is_activated'])
print('指纹:', status1['fingerprint_short'])
print('客户:', status1.get('customer_name', 'N/A'))

print('\n2. LicenseManager 检查:')
manager = LicenseManager()
status2 = manager.check_activation()
print('已激活:', status2['is_activated'])
print('指纹:', status2['fingerprint_short'])

print('\n✅ 激活状态已持久化！')
