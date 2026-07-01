# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\face_checkin_static\assets\index-CSvaDeP4.js', 'rb') as f:
    c = f.read()
text = c.decode('utf-8', errors='replace')

# Find the exact match for webgl
idx = text.find('tensorflow_backend:"webgl"')
if idx >= 0:
    ctx = text[max(0,idx-5):idx+60]
    clean = ''.join(ch if ord(ch)>=32 and ord(ch)<127 else ' ' for ch in ctx)
    print(f'Found at offset {idx}')
    print(repr(clean))
    
# Also check for wasm_path in the same area
idx2 = text.find('wasm_path', 12438000, 12440000)
if idx2 >= 0:
    ctx = text[max(0,idx2-5):idx2+50]
    clean = ''.join(ch if ord(ch)>=32 and ord(ch)<127 else ' ' for ch in ctx)
    print(f'wasm_path at {idx2}')
    print(repr(clean))
else:
    print('No wasm_path found in config area')
