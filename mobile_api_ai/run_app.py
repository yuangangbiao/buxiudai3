import os, sys
base = os.path.dirname(os.path.abspath(__file__))
os.chdir(base)
sys.path.insert(0, base)
_parent = os.path.dirname(base)
if _parent not in sys.path:
    sys.path.insert(0, _parent)
os.environ['FLASK_APP'] = 'app.py'
os.environ['FLASK_ENV'] = 'development'
from core.config import FLASK_PORT, FLASK_HOST
from app import create_app
app = create_app()
print(f'Starting server on http://{FLASK_HOST}:{FLASK_PORT}')
app.run(host=FLASK_HOST, port=FLASK_PORT, debug=False)
