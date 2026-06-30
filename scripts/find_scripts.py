import requests, re
r = requests.get('http://localhost:5008/', timeout=5)
t = r.text
scripts = re.findall(r'<script[^>]*src=["\']([^"\']+)["\']', t)
for s in scripts[:20]:
    print(s)
print()
# 找 inline script function
inline = re.findall(r'(function loadProcessTasks|function loadQualityRecords|function loadMaterialTasks|function loadOutsource)\s*\(', t)
print('inline funcs:', inline)
