import os, sys, json, logging
logging.basicConfig(filename='diag.log', level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s', force=True)
logging.info('START')

os.chdir(os.path.join(os.path.dirname(__file__), 'mobile_api_ai'))
sys.path.insert(0, os.getcwd())

import requests, time

logging.info('TEST1: cloud api')
with open('cloud_config.json', encoding='utf-8') as f:
    cfg = json.load(f)
logging.info(f'host={cfg["cloud_host"]}')

t0 = time.time()
try:
    r = requests.get(cfg['cloud_host'] + '/api/wechat/users',
        headers={'X-API-Key': cfg['api_key']}, timeout=30)
    cost = time.time()-t0
    logging.info(f'HTTP {r.status_code} cost={cost:.1f}s')
    if r.status_code == 200:
        d = r.json()
        logging.info(f'users={len(d.get("users",[]))} depts={len(d.get("departments",[]))} code={d.get("code")}')
except Exception as e:
    logging.error(f'cloud exception: {e}', exc_info=True)

logging.info('TEST2: container_config write')
try:
    from container_config import container_config, OperatorConfig
    before = len(container_config.get_all_operators())
    logging.info(f'operators before={before}')
    op = OperatorConfig(id='test_diag', name='test_diag', role='test')
    result = container_config.add_operator(op)
    logging.info(f'add_operator result={result}')
    container_config.remove_operator('test_diag')
    logging.info(f'operators after={len(container_config.get_all_operators())}')
except Exception as e:
    logging.error(f'container_config exception: {e}', exc_info=True)

logging.info('DONE')
