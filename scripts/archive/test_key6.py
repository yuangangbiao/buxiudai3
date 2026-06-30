import sys
import importlib.util

spec = importlib.util.spec_from_file_location("lm", "d:/yuan/不锈钢网带跟单3.0/security/license_manager.py")
lm_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lm_module)

validate_func = lm_module.LicenseManager._validate_license_key_format

# Check string constants in the bytecode
print("=== Code constants ===")
for i, const in enumerate(validate_func.__code__.co_consts):
    print(f"  [{i}] {repr(const)}")

print("\n=== Local variables ===")
print(f"  varnames: {validate_func.__code__.co_varnames}")

print("\n=== Names ===")
print(f"  names: {validate_func.__code__.co_names}")

# Try calling with different keys
test_keys = [
    "SB-6C50-32EA-EE67-3857",
    "SB-0000-0000-0000-0000",
    "SB-ABCD-EFGH-IJKL-MNOP",  # Invalid chars
]

for key in test_keys:
    result = validate_func(key)
    print(f"\nvalidate('{key}'): {result}")