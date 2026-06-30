import sys
import importlib.util

spec = importlib.util.spec_from_file_location("lm", "d:/yuan/不锈钢网带跟单3.0/security/license_manager.py")
lm_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lm_module)

validate_func = lm_module.LicenseManager._validate_license_key_format

# Manually trace through what the function does
key = 'SB-6C50-32EA-EE67-3857'
LICENSE_KEY_PREFIX = "SB-"

print(f"Testing key: {key}")
print()

# Step 1
if not key:
    print("1. FAIL: key is empty/falsy")
else:
    print("1. OK: key is truthy")

# Step 2
key = key.strip().upper()
print(f"2. After strip().upper(): [{key}]")

# Step 3
if not key.startswith(LICENSE_KEY_PREFIX):
    print("3. FAIL: doesn't start with SB-")
else:
    print("3. OK: starts with SB-")

# Step 4
parts = key.split("-")
print(f"4. After split('-'): {parts} (count={len(parts)})")
if len(parts) != 5:
    print("   FAIL: parts count != 5")
else:
    print("   OK: parts count == 5")

# Step 5
for i, part in enumerate(parts):
    print(f"5.{i}. Checking part '{part}' (len={len(part)})")
    if i == 0:
        if part != "SB":
            print(f"    FAIL: first part should be 'SB', got '{part}'")
        else:
            print("    OK: first part is SB")
    else:
        if len(part) != 4:
            print(f"    FAIL: len != 4")
        else:
            print("    OK: len == 4")

        # The actual check
        valid_chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        print(f"    valid_chars = '{valid_chars}'")

        for c in part:
            is_valid = c in valid_chars
            print(f"      char '{c}' in valid_chars: {is_valid}")

        all_valid = all(c in valid_chars for c in part)
        print(f"    all(c in valid_chars for c in '{part}'): {all_valid}")

        if not all_valid:
            print(f"    FAIL: some chars not in valid_chars!")

print()
print(f"Final result of _validate_license_key_format('{key}'): {validate_func('SB-6C50-32EA-EE67-3857')}")