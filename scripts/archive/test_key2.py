key = 'SB-6C50-32EA-EE67-3857'
LICENSE_KEY_PREFIX = "SB-"

key = key.strip().upper()
print(f'key: [{key}]')
print(f'startswith SB-: {key.startswith(LICENSE_KEY_PREFIX)}')

parts = key.split('-')
print(f'parts count: {len(parts)} (expected 5)')

for i, part in enumerate(parts):
    print(f'  [{i}] part="{part}" len={len(part)}', end='')
    if i == 0:
        print(f' (should be "SB": {part == "SB"})')
    else:
        if len(part) != 4:
            print(' FAIL: len != 4')
        else:
            valid_chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            all_valid = all(c in valid_chars for c in part)
            if not all_valid:
                for c in part:
                    if c not in valid_chars:
                        print(f' FAIL: invalid char "{c}"')
            else:
                print(' OK')