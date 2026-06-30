import sys
import importlib.util

spec = importlib.util.spec_from_file_location("lm", "d:/yuan/不锈钢网带跟单3.0/security/license_manager.py")
lm_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lm_module)

# Get the actual function object
validate_func = lm_module.LicenseManager._validate_license_key_format

key = 'SB-6C50-32EA-EE67-3857'

# Inspect the function
import inspect
print("=== Function source ===")
print(inspect.getsource(validate_func))

print("\n=== Bytecode ===")
print(validate_func.__code__.co_code.hex())