# -*- coding: utf-8 -*-
import os
import re
import pathlib

p = pathlib.Path('dispatch_center.py')
t = p.read_text('utf-8')

# Fix 1: steps = process.get('steps', ...) -> steps = process.get('steps') or ...
count1 = t.count("process.get('steps', flow_template['steps'])")
t = t.replace("process.get('steps', flow_template['steps'])", "process.get('steps') or flow_template['steps']")
print(f'Fix1 (steps): {count1} occurrences')

# Fix 2: timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10')) -> timeout=(3.05, 5) in _send_wechat_message and _send_wechat_app_message
def fix_timeout_in_send_wechat(t):
    pattern = r'(def _send_wechat_(?:message|app_message).*?timeout=)10'
    matches = re.findall(pattern, t, re.DOTALL)
    print(f"Fix2 (timeout): found {len(matches)} timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10')) occurrences")
    t = re.sub(pattern, r'\g<1>(3.05, 5)', t, flags=re.DOTALL)
    return t

t = fix_timeout_in_send_wechat(t)

p.write_text(t, 'utf-8')
print('Done')
