"""启动 app.py"""
import sys, os

PROJ = os.path.realpath(os.path.dirname(os.path.abspath(__file__)))
PARENT = os.path.dirname(PROJ)
sys.path.insert(0, PARENT)
os.chdir(PROJ)
os.environ['PORT'] = '5008'

app_path = os.path.join(PROJ, 'app.py')
code = compile(open(app_path, encoding='utf-8').read(), app_path, 'exec')
exec(code, {'__file__': app_path, '__name__': '__main__'})
