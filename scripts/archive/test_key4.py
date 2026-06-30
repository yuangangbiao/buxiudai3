import sys
import importlib.util

spec = importlib.util.spec_from_file_location("lm", "d:/yuan/不锈钢网带跟单3.0/security/license_manager.py")
lm_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lm_module)

LicenseManager = lm_module.LicenseManager

key = 'SB-6C50-32EA-EE67-3857'
LICENSE_KEY_PREFIX = "SB-"

# Step by step debug
print("=== Step by step validation ===")
key_stripped = key.strip()
print(f"1. key.strip(): [{key_stripped}]")

key_upper = key_stripped.upper()
print(f"2. key.upper(): [{key_upper}]")

starts_with = key_upper.startswith(LICENSE_KEY_PREFIX)
print(f"3. startswith('SB-'): {starts_with}")

parts = key_upper.split("-")
print(f"4. split('-'): {parts} (count={len(parts)})")

if len(parts) != 5:
    print("FAIL: parts count != 5")
else:
    for i, part in enumerate(parts):
        print(f"5.{i}. part[{i}]=[{part}] len={len(part)}", end="")
        if i == 0:
            if part != "SB":
                print(" FAIL: first part != SB")
            else:
                print(" OK")
        else:
            if len(part) != 4:
                print(" FAIL: part len != 4")
            else:
                valid_chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                all_valid = all(c in valid_chars for c in part)
                if not all_valid:
                    for c in part:
                        if c not in valid_chars:
                            print(f' FAIL: char "{c}" not in valid_chars')
                else:
                    print(" OK")

print("\n=== Direct function call ===")
result = LicenseManager._validate_license_key_format(key)
print(f"validate_license_key_format('{key}'): {result}")