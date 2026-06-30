import sys
import importlib.util

spec = importlib.util.spec_from_file_location("lm", "d:/yuan/不锈钢网带跟单3.0/security/license_manager.py")
lm_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lm_module)

validate_func = lm_module.LicenseManager._validate_license_key_format

# Get the actual bytecode and look for string constants
bytecode = validate_func.__code__.co_code
constants = validate_func.__code__.co_consts

print("Constants in function:")
for i, c in enumerate(constants):
    if isinstance(c, str) and len(c) > 10:
        print(f"  [{i}] STRING: {repr(c)}")
        print(f"       bytes: {c.encode()}")

# Also let's look at the actual instructions
import dis
print("\n=== Disassembly ===")
dis.dis(validate_func)

# Most importantly - let's trace exactly where it fails
print("\n=== Step by step with exact logic ===")
key = 'SB-6C50-32EA-EE67-3857'

# Copy the exact logic from the function
if not key:
    print("FAIL at: if not key")
elif not key.strip().upper().startswith("SB-"):
    print("FAIL at: startswith check")
else:
    key_processed = key.strip().upper()
    parts = key_processed.split("-")
    if len(parts) != 5:
        print("FAIL at: parts != 5")
    else:
        all_ok = True
        for part in parts:
            if len(part) != 4:
                print(f"FAIL at: len({part}) != 4")
                all_ok = False
                break
            # This is the critical check
            valid_chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            for c in part:
                if c not in valid_chars:
                    print(f"FAIL at: char '{c}' not in valid_chars")
                    all_ok = False
                    break
            if not all_ok:
                break
        if all_ok:
            print(f"OK: All checks passed!")
            print(f"Result should be: True")