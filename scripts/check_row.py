import urllib.request
r = urllib.request.urlopen('http://localhost:5001/process-track')
c = r.read().decode('utf-8')
# Find the onclick in the row
import re
m = re.search(r'onclick="selectOrder\([^"]+\)"', c)
if m:
    print('Found onclick:', m.group()[:200])
else:
    print('No onclick found in template (only in client-side JS)')

# Check if selectOrder function is correct
if 'async function selectOrder' in c:
    print('selectOrder function exists in page')
    m2 = re.search(r'async function selectOrder\([^)]+\)\s*\{[^}]*\}', c, re.DOTALL)
    if m2:
        print('selectOrder function:', m2.group()[:500])
