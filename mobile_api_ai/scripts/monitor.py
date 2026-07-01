# -*- coding: utf-8 -*-
"""
重构监控告警脚本 (v3.7.1)

功能:
- DB连接健康检查
- API成功率采样
- 错误日志关键字监控
- 企微WebHook三级告警推送

依赖:
    pip install pymysql requests python-dotenv

使用:
    # 单次执行
    python scripts/monitor.py

    # 定时执行 (crontab)
    */5 * * * * cd /path/to/mobile_api_ai && python scripts/monitor.py >> logs/monitor.log 2>&1

    # 手动触发不同级别
    python scripts/monitor.py --level P0
    python scripts/monitor.py --level P1
    python scripts/monitor.py --level P2
"""

import os
import sys
import time
import json
import logging
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

import pymysql
import requests

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from bots.group_bot import GroupBot
from core.config import MAX_TEXT_LENGTH

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(BASE_DIR, 'logs', 'monitor.log'), encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
MYSQL_USER = os.getenv('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'steel_belt')
CONTAINER_DB = os.getenv('CONTAINER_MYSQL_DATABASE', 'container_center')

DB_TIMEOUT = 5
API_TIMEOUT = 10
API_SAMPLE_SIZE = 20

WECHAT_WEBHOOK_URL = os.getenv('WECHAT_WORK_BOT_URL', os.getenv('WECHAT_WEBHOOK_URL', ''))

P0_ENDPOINTS = [
    '/api/dispatch/process_records',
    '/api/dispatch/orders',
    '/api/dispatch/workers',
]

P1_ENDPOINTS = [
    '/api/dispatch/packages',
    '/api/dispatch/reports',
    '/api/face/checkin',
]

P2_ENDPOINTS = [
    '/api/dispatch/stats',
    '/api/dispatch/operators',
]

ALL_ENDPOINTS = P0_ENDPOINTS + P1_ENDPOINTS + P2_ENDPOINTS

API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:5003')

ERROR_LOG_PATTERNS = [
    ('ConnectionRefusedError', 1, 'P0'),
    ('pymysql.err.OperationalError', 1, 'P0'),
    ('InternalServerError', 1, 'P1'),
    ('Traceback', 5, 'P1'),
    ('TimeoutError', 3, 'P1'),
    ('DatabaseError', 2, 'P2'),
]


class DBHealthChecker:
    """数据库健康检查"""

    def __init__(self):
        self.cfg = {
            'host': MYSQL_HOST,
            'port': MYSQL_PORT,
            'user': MYSQL_USER,
            'password': MYSQL_PASSWORD,
            'charset': 'utf8mb4',
            'connect_timeout': DB_TIMEOUT,
        }

    def check_connection(self, database: str) -> Dict[str, Any]:
        start = time.time()
        try:
            conn = pymysql.connect(database=database, **self.cfg)
            with conn.cursor() as c:
                c.execute('SELECT 1')
                c.fetchone()
            conn.close()
            elapsed = (time.time() - start) * 1000
            return {'ok': True, 'db': database, 'latency_ms': round(elapsed, 1), 'error': None}
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return {'ok': False, 'db': database, 'latency_ms': round(elapsed, 1), 'error': str(e)}

    def check_main_db(self) -> Dict[str, Any]:
        return self.check_connection(MYSQL_DATABASE)

    def check_container_db(self) -> Dict[str, Any]:
        return self.check_connection(CONTAINER_DB)

    def check_table_counts(self) -> List[Dict[str, Any]]:
        results = []
        for db, tables in [(MYSQL_DATABASE, ['production_orders', 'process_records', 'sync_queue']),
                           (CONTAINER_DB, ['data_packages', 'process_records'])]:
            try:
                conn = pymysql.connect(database=db, **self.cfg)
                with conn.cursor() as c:
                    for tbl in tables:
                        try:
                            c.execute(f'SELECT COUNT(*) FROM {tbl}')
                            cnt = c.fetchone()[0]
                            results.append({'db': db, 'table': tbl, 'count': cnt, 'ok': True})
                        except Exception as e:
                            results.append({'db': db, 'table': tbl, 'count': -1, 'ok': False, 'error': str(e)})
                conn.close()
            except Exception as e:
                for tbl in tables:
                    results.append({'db': db, 'table': tbl, 'count': -1, 'ok': False, 'error': str(e)})
        return results


class APIHealthChecker:
    """API成功率检查"""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')

    def check_endpoint(self, endpoint: str, sample_size: int = 5) -> Dict[str, Any]:
        success = 0
        errors = []
        latencies = []
        for _ in range(sample_size):
            start = time.time()
            try:
                url = f'{self.base_url}{endpoint}'
                resp = requests.get(url, timeout=API_TIMEOUT)
                elapsed = (time.time() - start) * 1000
                latencies.append(round(elapsed, 1))
                if resp.status_code < 500:
                    success += 1
                else:
                    errors.append(f'HTTP {resp.status_code}')
            except Exception as e:
                elapsed = (time.time() - start) * 1000
                latencies.append(round(elapsed, 1))
                errors.append(str(e)[:60])
        rate = success / sample_size * 100
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        p99_latency = sorted(latencies)[int(len(latencies) * 0.99)] if len(latencies) > 1 else (latencies[0] if latencies else 0)
        return {
            'endpoint': endpoint,
            'success_rate': round(rate, 1),
            'avg_latency_ms': round(avg_latency, 1),
            'p99_latency_ms': round(p99_latency, 1),
            'errors': errors[:3],
            'ok': rate >= 95.0
        }

    def check_p0_endpoints(self) -> List[Dict[str, Any]]:
        return [self.check_endpoint(ep, sample_size=3) for ep in P0_ENDPOINTS]

    def check_all_endpoints(self) -> List[Dict[str, Any]]:
        return [self.check_endpoint(ep, sample_size=5) for ep in ALL_ENDPOINTS]


class ErrorLogMonitor:
    """错误日志关键字监控"""

    def __init__(self, log_dir: str):
        self.log_dir = log_dir

    def scan_errors(self, hours: int = 1) -> Dict[str, Any]:
        cutoff = datetime.now() - timedelta(hours=hours)
        findings = {}
        log_files = [
            os.path.join(self.log_dir, 'dispatch_5003.err'),
            os.path.join(self.log_dir, 'app.log'),
            os.path.join(self.log_dir, 'error.log'),
        ]
        for pattern, threshold, level in ERROR_LOG_PATTERNS:
            count = 0
            details = []
            for lfile in log_files:
                if not os.path.exists(lfile):
                    continue
                try:
                    with open(lfile, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            if len(line) > 100:
                                continue
                            try:
                                parts = line.split(']', 1)
                                if len(parts) < 2:
                                    continue
                                ts_str = parts[0].strip('[')
                                msg = parts[1]
                                try:
                                    ts = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
                                except ValueError:
                                    continue
                                if ts < cutoff:
                                    continue
                                if pattern in msg:
                                    count += 1
                                    if len(details) < 3:
                                        details.append(line.strip()[:120])
                            except Exception:
                                continue
                except Exception:
                    continue
            if count > 0:
                findings[pattern] = {
                    'count': count,
                    'level': level,
                    'threshold': threshold,
                    'exceeded': count >= threshold,
                    'sample': details
                }
        return findings


class WeChatNotifier:
    """企微WebHook通知"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.bot = GroupBot(webhook_url) if webhook_url else None

    def send_markdown(self, title: str, content: str, level: str = 'P0') -> bool:
        if not self.bot:
            logger.warning('[通知] 未配置企微WebHook，跳过推送')
            return False
        level_emoji = {'P0': '🔴', 'P1': '🟡', 'P2': '🟢'}.get(level, '⚪')
        full_content = f'{level_emoji} **{title}**\n\n{content}'
        if len(full_content) > MAX_TEXT_LENGTH - 50:
            full_content = full_content[:MAX_TEXT_LENGTH - 50] + '\n\n_(内容截断)_'
        try:
            self.bot.send_text(full_content)
            logger.info(f'[通知] 企微消息已发送: {title}')
            return True
        except Exception as e:
            logger.error(f'[通知] 企微消息发送失败: {e}')
            return False


class MonitorReport:
    """监控报告生成"""

    @staticmethod
    def format_db_report(db_result: Dict, table_counts: List, level: str = 'P0') -> str:
        db_ok = db_result.get('ok', False)
        db_name = db_result.get('db', '')
        latency = db_result.get('latency_ms', 0)
        db_error = db_result.get('error', '')
        lines = [
            f'**DB[{db_name}]**: {"✅" if db_ok else "❌"} 延迟 {latency}ms',
        ]
        if not db_ok:
            lines.append(f'> 错误: `{db_error}`')
        table_lines = []
        for t in table_counts:
            icon = '✅' if t.get('ok') else '❌'
            table_lines.append(f'{icon} `{t["db"]}.{t["table"]}` = {t["count"]}')
        if table_lines:
            lines.append('表行数:')
            lines.extend(table_lines)
        return '\n'.join(lines)

    @staticmethod
    def format_api_report(results: List[Dict], level: str) -> str:
        if not results:
            return '**API**: 无数据'
        lines = []
        for r in results:
            ep = r['endpoint']
            rate = r['success_rate']
            p99 = r['p99_latency_ms']
            icon = '✅' if r['ok'] else '❌'
            line = f'{icon} `{ep}` 成功率 {rate}% P99 {p99}ms'
            if r['errors']:
                line += f' | 错误: `{"; ".join(r["errors"][:1])}`'
            lines.append(line)
        return '\n'.join(lines)

    @staticmethod
    def format_error_report(findings: Dict) -> str:
        if not findings:
            return '**错误日志**: ✅ 近1小时无异常'
        lines = ['**错误日志** (近1小时):']
        for pattern, info in findings.items():
            icon = '🔴' if info['exceeded'] else '🟡'
            lines.append(f'{icon} `{pattern}`: {info["count"]}次 (阈值{info["threshold"]})')
            if info.get('sample'):
                for s in info['sample'][:1]:
                    lines.append(f'> `{s}`')
        return '\n'.join(lines)


def run_health_check(level: str = 'P0') -> Dict[str, Any]:
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_dir = os.path.join(BASE_DIR, 'logs')
    os.makedirs(log_dir, exist_ok=True)

    result = {'timestamp': ts, 'level': level, 'db': {}, 'api': {}, 'errors': {}, 'summary': {}}

    db_checker = DBHealthChecker()
    api_checker = APIHealthChecker(API_BASE_URL)
    error_monitor = ErrorLogMonitor(log_dir)

    if level in ('P0', 'P1', 'P2'):
        db_main = db_checker.check_main_db()
        db_cont = db_checker.check_container_db()
        result['db'] = {'main': db_main, 'container': db_cont}
        logger.info(f'[DB] main={db_main["ok"]} cont={db_cont["ok"]}')

    if level in ('P0',):
        table_counts = db_checker.check_table_counts()
        result['db']['tables'] = table_counts
        api_results = api_checker.check_p0_endpoints()
        result['api'] = {'p0': api_results}
        findings = error_monitor.scan_errors(hours=1)
        result['errors'] = findings
    elif level in ('P1',):
        table_counts = db_checker.check_table_counts()
        result['db']['tables'] = table_counts
        api_results = api_checker.check_all_endpoints()
        result['api'] = {'all': api_results}
        findings = error_monitor.scan_errors(hours=1)
        result['errors'] = findings
    elif level in ('P2',):
        api_results = api_checker.check_all_endpoints()
        result['api'] = {'all': api_results}
        findings = error_monitor.scan_errors(hours=2)
        result['errors'] = findings

    p0_fail = (not result['db'].get('main', {}).get('ok', False) or
               not result['db'].get('container', {}).get('ok', False))
    api_fail = any(not r['ok'] for r in result['api'].get('p0', result['api'].get('all', [])))
    error_fail = any(info['exceeded'] for info in result['errors'].values())
    result['summary'] = {
        'db_fail': p0_fail,
        'api_fail': api_fail,
        'error_fail': error_fail,
        'overall': not (p0_fail or api_fail or error_fail)
    }

    return result


def decide_alert_level(result: Dict[str, Any]) -> Optional[str]:
    if result['summary']['db_fail']:
        return 'P0'
    if result['summary']['api_fail']:
        return 'P1'
    if result['summary']['error_fail']:
        return 'P2'
    return None


def send_alert(result: Dict[str, Any], alert_level: Optional[str] = None):
    if alert_level is None:
        logger.info('[通知] 所有检查通过，无需告警')
        return
    notifier = WeChatNotifier(WECHAT_WEBHOOK_URL)
    ts = result['timestamp']
    level = alert_level or result['level']

    if level == 'P0':
        title = f'🔴 P0告警: 系统异常 [{ts}]'
        content_parts = []
        for db_name, db_result in result['db'].items():
            if db_name == 'tables':
                continue
            table_counts = result['db'].get('tables', [])
            db_tables = [t for t in table_counts if t['db'] == ('steel_belt' if db_name == 'main' else 'container_center')]
            content_parts.append(MonitorReport.format_db_report(db_result, db_tables, level))
        content = '\n\n'.join(content_parts)
    elif level == 'P1':
        api_results = result['api'].get('all', result['api'].get('p0', []))
        failed = [r for r in api_results if not r['ok']]
        title = f'🟡 P1告警: API异常 [{ts}]'
        content = MonitorReport.format_api_report(failed, level)
        content += '\n\n' + MonitorReport.format_error_report(result['errors'])
    else:
        title = f'🟢 P2告警: 错误日志 [{ts}]'
        content = MonitorReport.format_error_report(result['errors'])

    content += f'\n\n> 触发级别: {level} | 详细报告: `logs/monitor.log`'

    notifier.send_markdown(title, content, level)


def main():
    parser = argparse.ArgumentParser(description='重构监控系统')
    parser.add_argument('--level', choices=['P0', 'P1', 'P2', 'full'], default='full',
                        help='检查级别: P0=DB+P0 API, P1=DB+全部API, P2=全部检查')
    parser.add_argument('--no-alert', action='store_true', help='不发送企微通知')
    parser.add_argument('--output-json', action='store_true', help='输出JSON格式报告')
    args = parser.parse_args()

    level = args.level if args.level != 'full' else 'P1'

    logger.info(f'=== 监控开始 [{level}] ===')
    result = run_health_check(level)

    if args.output_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    summary = result['summary']
    overall = summary['overall']
    logger.info(f'DB: {"✅" if not summary["db_fail"] else "❌"} | '
                f'API: {"✅" if not summary["api_fail"] else "❌"} | '
                f'错误: {"✅" if not summary["error_fail"] else "❌"} | '
                f'总体: {"✅" if overall else "❌"}')

    if not args.no_alert:
        alert_level = decide_alert_level(result)
        send_alert(result, alert_level)

    logger.info('=== 监控结束 ===')
    sys.exit(0 if overall else 1)


if __name__ == '__main__':
    main()
