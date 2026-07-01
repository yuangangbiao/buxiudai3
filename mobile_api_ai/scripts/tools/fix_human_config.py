# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

js_path = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\face_checkin_static\assets\index-CSvaDeP4.js'

with open(js_path, 'rb') as f:
    raw = f.read()

text = raw.decode('utf-8', errors='replace')

old = 'tensorflow_backend:"webgl"'
new = 'tensorflow_backend:"wasm",tensorflow_wasm_path:kk+"/wasm"'

if old in text:
    count = text.count(old)
    print(f"Found '{old}' {count} time(s)")
    text = text.replace(old, new, 1)
    print(f"Replaced with: {new}")
    
    # Verify
    if 'tensorflow_wasm_path:kk+"/wasm"' in text:
        print("Verification: wasm path added successfully")
    
    with open(js_path, 'wb') as f:
        f.write(text.encode('utf-8'))
    print("File saved")
else:
    print(f"ERROR: '{old}' not found!")
    # Search for similar patterns
    for kw in ['tensorflow_backend', 'webgl']:
        idx = text.find(kw)
        if idx >= 0:
            ctx = text[max(0,idx-20):idx+30]
            clean = ''.join(ch if ord(ch)>=32 and ord(ch)<127 else ' ' for ch in ctx)
            print(f"Found '{kw}' at {idx}: ...{clean}...")
