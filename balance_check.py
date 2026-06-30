#!/usr/bin/env python3
with open(r'd:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center/_core.py', 'rb') as f:
    data = f.read()

# Track triple-quote state character by character
i = 0
lineno = 1
col = 1
in_string = False
string_start = None
last_newline = 0

while i < len(data):
    b = data[i]
    if b == ord('\n'):
        lineno += 1
        col = 1
        last_newline = i
        i += 1
        continue
    if b == ord('\r'):
        i += 1
        continue

    # Check for triple quote
    if data[i:i+3] == b'\x22\x22\x22':
        if not in_string:
            # Opening triple-quote
            in_string = True
            string_start = (lineno, col)
            print(f'L{lineno}: OPEN docstring at col {col}: {repr(data[last_newline:i+50])}')
        else:
            # Closing triple-quote
            in_string = False
            print(f'L{lineno}: CLOSE docstring at col {col}, started at {string_start}')
            string_start = None
        i += 3
        col += 3
        continue

    i += 1
    col += 1

print(f'\nFinal: in_string={in_string}, string_start={string_start}')
