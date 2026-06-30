# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
data = open('desktop_web/server.py', 'r', encoding='utf-8').read()
for kw in ['upload-attachment', 'operators/import', 'production/orders', 'orders/import', 'orders/create']:
    idx = data.find(kw)
    print(f'--- {kw} (idx={idx}) ---')
    print(repr(data[idx-30:idx+250]))
    print()
