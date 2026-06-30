key = 'SB-6C50-32EA-EE67-3857'
key = key.strip().upper()
print(f'key: {key}')
print(f'starts with SB-: {key.startswith("SB-")}')

parts = key.split('-')
print(f'parts count: {len(parts)}')
print(f'parts: {parts}')

for i, part in enumerate(parts):
    print(f'  part[{i}] = "{part}" (len={len(part)})')
    if i == 0:
        print(f'    SB check: {part == "SB"}')
    else:
        for c in part:
            if c not in '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                print(f'    INVALID CHAR: {c}')

# Direct check
valid_chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
part = '6C50'
print(f'\nChecking part "{part}":')
print(f'  All chars valid: {all(c in valid_chars for c in part)}')
for c in part:
    print(f'    "{c}" in valid_chars: {c in valid_chars}')