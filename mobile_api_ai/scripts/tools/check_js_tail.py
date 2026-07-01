# -*- coding: utf-8 -*-
import re, sys

with open(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\face_checkin_static\assets\index-CSvaDeP4.js', 'rb') as f:
    c = f.read()

text = c.decode('utf-8', errors='replace')

# Read context around jcA function (pos 12438726)
start = 12437000
end = min(len(text), 12440000)
chunk = text[start:end]

# Remove emoji and non-printable chars for console output
clean = ''.join(ch if ord(ch) < 128 or ord(ch) > 0x1F000 else '?' for ch in chunk)
print(clean)
