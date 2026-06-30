"""诊断微信同步问题 - 模拟 sync_operators_from_wechat 的调用"""
import os, sys, json, logging

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger('diagnose')

# 设置环境和路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'mobile_api_ai'))
os.chdir(os.path.dirname(__file__))

# 加载 cloud_config
cfg_file = os.path.join(os.path.dirname(__file__), 'mobile_api_ai', 'cloud_config.json')
if os.path.exists(cfg_file):
    with open(cfg_file, 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    logger.info(f"cloud_config: host={cfg.get('cloud_host')}, api_key={cfg.get('api_key')[:8]}...")
    os.environ['WECHAT_CLOUD_HOST'] = cfg['cloud_host']
    os.environ['WECHAT_CLOUD_API_KEY'] = cfg['api_key']

# 测试1: 云端API是否可达
import requests
try:
    url = f"{cfg['cloud_host']}/api/wechat/users"
    headers = {'X-API-Key': cfg['api_key']}
    logger.info(f"请求云端: {url}")
    resp = requests.get(url, headers=headers, timeout=30)
    logger.info(f"云端响应: HTTP {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        logger.info(f"返回 code={data.get('code')}, users={len(data.get('users', []))}, departments={len(data.get('departments', []))}")
except Exception as e:
    logger.error(f"云端API异常: {e}", exc_info=True)

# 测试2: container_config 加载
try:
    from container_config import container_config, OperatorConfig
    ops = container_config.get_all_operators()
    logger.info(f"container_config 已加载，当前操作员数: {len(ops)}")
    for op in ops[:3]:
        logger.info(f"  操作员: id={op.id}, name={op.name}, wechat_userid={op.wechat_userid}")
except Exception as e:
    logger.error(f"container_config 加载异常: {e}", exc_info=True)

# 测试3: EventBus 和 MySQL 相关
try:
    from event_bus import EventBus
    bus = EventBus.get()
    logger.info("EventBus 初始化成功")
except Exception as e:
    logger.warning(f"EventBus 初始化异常(非致命): {e}")

try:
    from dispatch_center import get_db_cursor
    with get_db_cursor() as (cursor, conn):
        cursor.execute("SELECT 1")
        logger.info("MySQL 连接成功")
except Exception as e:
    logger.warning(f"MySQL 连接失败(非致命): {e}")

logger.info("诊断完成")
