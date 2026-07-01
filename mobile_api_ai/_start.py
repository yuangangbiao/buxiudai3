import sys, os, logging
sys.path.insert(0, r"d:\yuan\不锈钢网带跟单3.0\mobile_api_ai")
sys.path.insert(0, r"d:\yuan\不锈钢网带跟单3.0")
os.chdir(r"d:\yuan\不锈钢网带跟单3.0\mobile_api_ai")

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', handlers=[
    logging.StreamHandler(sys.stdout)
])
logger = logging.getLogger(__name__)

logger.info("[START] 导入 wechat_server...")
from mobile_api_ai import wechat_server

logger.info("[START] 调用 init_services()...")
wechat_server.init_services()

logger.info("[START] 调用 init_wechat_services()...")
wechat_server.init_wechat_services()

logger.info("[START] 预热 V5CompatibleClient...")
try:
    _client = wechat_server._get_client()
    logger.info(f"[START] V5CompatibleClient 预热完成: {type(_client).__name__}")
except Exception as e:
    logger.warning(f"[START] V5CompatibleClient 预热失败: {e}")

logger.info("[START] 预热 OperationLogDB 连接池...")
try:
    from mobile_api_ai.operation_log import get_operation_log_db
    log_db = get_operation_log_db()
    _conn = log_db._pool.connection()
    _cur = _conn.cursor()
    _cur.execute("SELECT 1")
    _cur.fetchone()
    _cur.close()
    _conn.close()
    logger.info("[START] OperationLogDB 连接池预热完成")
except Exception as e:
    logger.warning(f"[START] OperationLogDB 连接池预热失败: {e}")

logger.info("[START] 启动 Flask 服务 on 0.0.0.0:15003...")
wechat_server.app.run(host="0.0.0.0", port=15003, debug=False, threaded=True, use_reloader=False)
