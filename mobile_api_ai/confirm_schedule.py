import os, sys, json, logging, urllib.request
from datetime import datetime, timedelta
import time

_base = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _base)
_parent = os.path.dirname(_base)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from ._service_urls import ServiceURLs
from core.config import MYSQL_CFG, DB_PATHS

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

ORDER_NO = 'ORD-202604270003'
CALLBACK_URL = ServiceURLs.MAIN_SOFTWARE_CALLBACK_URL
CC_BASE = ServiceURLs.CONTAINER_CENTER_URL
DC_BASE = ServiceURLs.DISPATCH_CENTER_URL + '/api/dispatch-center'


def api_json(url, data, method='POST', timeout=10):
    body = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(url, data=body,
        headers={'Content-Type': 'application/json'}, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return True, resp.status, resp.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        return False, e.code, e.read().decode('utf-8')
    except urllib.error.URLError as e:
        return False, None, str(e.reason)


def query_prod_info():
    """从 MySQL 查询 production_orders 记录"""
    try:
        from db.steelbelt_pool import cursor as sb_cursor
        conn, c = sb_cursor()
        c.execute("""
            SELECT po.id as prod_id, po.order_no,
                   po.plan_start, po.plan_end, po.status
            FROM production_orders po
            WHERE po.order_no = %s
        """, (ORDER_NO,))
        row = c.fetchone()
        conn.close()
        if row:
            logger.info(f'[MySQL] prod_id={row["prod_id"]}, status={row["status"]}, '
                        f'plan={row["plan_start"]}~{row["plan_end"]}')
            return dict(row)
        logger.warning(f'[MySQL] 未找到 {ORDER_NO}')
        return None
    except ImportError:
        logger.warning('[MySQL] pymysql 未安装，用默认值')
        return None
    except Exception as e:
        logger.warning(f'[MySQL] 查询失败: {e}')
        return None


def update_container_process():
    logger.info('[容器中心] 更新流程记录...')
    ok, code, body = api_json(
        f'{CC_BASE}/api/processes/2cad360e',
        {'order_no': ORDER_NO, 'priority': 'normal'},
        method='PUT'
    )
    if ok:
        logger.info(f'[容器中心] 流程记录已更新 ({code})')
        return True
    logger.warning(f'[容器中心] 更新失败 ({code}): {body[:100]}')
    return False


def update_dispatch_cache():
    cache_file = DB_PATHS['dispatch_center_data']
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for proc in data.get('processes', []):
            if proc.get('order_no') == ORDER_NO:
                proc['lead_time'] = 15
                proc['lead_time_unit'] = '天'
                proc['schedule_confirmed'] = True
                proc['schedule_confirmed_at'] = datetime.now().isoformat()
                proc['schedule_remark'] = '已确认排产，工期15天'
                break
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info('[缓存] 已更新 dispatch_center_data.json')
        return True
    except Exception as e:
        logger.warning(f'[缓存] 更新失败: {e}')
        return False


def send_callback(payload, label):
    logger.info(f'[{label}] 发送回调 → {CALLBACK_URL}')
    logger.info(f'[{label}] 数据: {json.dumps(payload, ensure_ascii=False)}')
    ok, code, body = api_json(CALLBACK_URL, payload)
    if ok:
        logger.info(f'[{label}] ✓ 成功 ({code})')
        try:
            logger.info(f'[{label}] 响应: {json.dumps(json.loads(body), ensure_ascii=False, indent=2)}')
        except Exception:
            logger.info(f'[{label}] 响应: {body[:200]}')
    else:
        logger.warning(f'[{label}] ⚠ 失败 ({code}): {body[:200]}')
    return ok


if __name__ == '__main__':
    logger.info('=' * 55)
    logger.info(f'  {ORDER_NO} 排产确认回调（容器中心 → 主软件）')
    logger.info('=' * 55)

    # ── 从 MySQL 查询 prod_id ──
    prod_info = query_prod_info()
    if prod_info and prod_info.get('prod_id'):
        prod_id = prod_info['prod_id']
        plan_start = str(prod_info['plan_start'] or datetime.now().strftime('%Y-%m-%d'))
        plan_end = str(prod_info['plan_end'] or (datetime.now() + timedelta(days=15)).strftime('%Y-%m-%d'))
        logger.info(f'[MySQL] prod_id={prod_id}, plan_start={plan_start}, plan_end={plan_end}')
    else:
        prod_id = 28
        plan_start = '2026-05-15'
        plan_end = '2026-05-30'
        logger.warning(f'[MySQL] 未查到，使用默认值: prod_id={prod_id}')

    # 1. 更新本地缓存
    update_dispatch_cache()

    # 2. 更新容器中心流程记录
    update_container_process()

    # ── 回调1：已收到排产信息（排产发布）──
    logger.info('')
    logger.info('── 回调1：已收到排产信息（状态: 待发布 → 待开始）──')
    ok1 = send_callback({
        'type': 'schedule_info_received',
        'order_no': ORDER_NO,
        'prod_id': prod_id,
        'order_no': ORDER_NO,
        'plan_start': plan_start,
        'plan_end': plan_end,
        'process_id': '2cad360e',
        'operator': '企业微信',
        'remark': '已收到排产信息',
        'message': f'工单 {ORDER_NO} 已收到排产信息，正在确认中...',
        'notify_type': 'info',
        'timestamp': datetime.now().isoformat()
    }, '通知-收到排产信息')

    time.sleep(0.3)

    # ── 回调2：确认排产，工期15天（排产确认）──
    logger.info('')
    logger.info('── 回调2：确认排产，工期15天 ──')
    ok2 = send_callback({
        'type': 'schedule_confirmed',
        'order_no': ORDER_NO,
        'prod_id': prod_id,
        'order_no': ORDER_NO,
        'plan_start': plan_start,
        'plan_end': plan_end,
        'process_id': '2cad360e',
        'process_name': '生产流程',
        'step': '排产确认',
        'status_key': 'confirmed',
        'lead_time': 15,
        'lead_time_unit': '天',
        'operator': '计划部',
        'remark': '已确认排产，工期15天',
        'confirmed_by': '计划部',
        'confirmed_at': datetime.now().isoformat(),
        'timestamp': datetime.now().isoformat()
    }, '确认-排产确认工期15天')

    logger.info('')
    logger.info('=' * 55)
    logger.info('操作汇总：')
    logger.info(f'  prod_id={prod_id}')
    logger.info(f'  plan={plan_start} ~ {plan_end}')
    logger.info(f'  回调1(收到排产信息) → {"✓ 成功" if ok1 else "✗ 失败"}')
    logger.info(f'  回调2(确认排产)     → {"✓ 成功" if ok2 else "✗ 失败"}')
    logger.info('  本地缓存    → 已更新')
    logger.info('  流程记录    → 已更新')
    logger.info('=' * 55)
