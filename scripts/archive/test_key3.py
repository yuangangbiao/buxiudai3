import sys
import importlib.util

spec = importlib.util.spec_from_file_location("lm", "d:/yuan/不锈钢网带跟单3.0/security/license_manager.py")
lm_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lm_module)

LicenseManager = lm_module.LicenseManager

key = 'SB-6C50-32EA-EE67-3857'
result = LicenseManager._validate_license_key_format(key)
print(f'密钥: {key}')
print(f'验证结果: {result}')

print("\n--- Debug: inspecting the module ---")
print(f'Module file: {lm_module.__file__}')