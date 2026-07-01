import os, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))
os.environ['FLASK_APP'] = 'app.py'
os.environ['FLASK_ENV'] = 'development'
from app import create_app
app = create_app()
debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
app.run(host=os.getenv('RUN_HOST', '0.0.0.0'),
        port=int(os.getenv('RUN_PORT', '5008')),
        debug=debug_mode)
