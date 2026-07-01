import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app
app = create_app()
for r in sorted(app.url_map.iter_rules(), key=lambda x: x.rule):
    if 'face' in r.rule.lower():
        methods = sorted(r.methods - {'OPTIONS', 'HEAD'})
        print(f'{methods} {r.rule}')
print('--- all routes loaded ---')