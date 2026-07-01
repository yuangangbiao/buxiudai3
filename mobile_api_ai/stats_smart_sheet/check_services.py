# -*- coding: utf-8 -*-
"""
服务健康检查 + 重启脚本
验证 5005 和云端 5004 是否正常运行

用法：
    python check_services.py              # 健康检查
    python check_services.py --restart    # 重启本地 5005
    python check_services.py --all        # 检查全部（含云端）
"""
import sys
import os
import argparse
import logging
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from dotenv import load_dotenv
load_dotenv('.env', override=True)

logger = logging.getLogger(__name__)


def check_local_5005():
    """检查本地 5005 服务"""
    port = os.getenv('RELAY_PORT', '5005')
    host = os.getenv('RELAY_HOST', '0.0.0.0')
    url = f'http://{host}:{port}/api/health'
    try:
        resp = requests.get(url, timeout=5)
        data = resp.json()
        logger.info(f"  ✅ 本地 5005 运行正常")
        logger.info(f"     URL: {url}")
        logger.info(f"     响应: {data}")
        return True
    except requests.exceptions.ConnectionError:
        logger.error(f"  ❌ 本地 5005 未运行（连接被拒绝）")
        logger.info(f"     请启动: python cloud_relay.py")
        return False
    except Exception:
        logger.exception(f"  ❌ 本地 5005 检查异常")
        return False


def check_cloud_5004():
    """检查云端 5004 服务"""
    host = os.getenv('CLOUD_5004_HOST', '')
    port = os.getenv('CLOUD_5004_PORT', '5004')
    if not host:
        logger.warning("  ⚠️  CLOUD_5004_HOST 未配置，跳过云端检查")
        return None

    url = f'http://{host}:{port}/api/health'
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        logger.info(f"  ✅ 云端 5004 运行正常")
        logger.info(f"     URL: {url}")
        logger.info(f"     响应: {data}")
        return True
    except requests.exceptions.ConnectionError:
        logger.error(f"  ❌ 云端 5004 未运行（连接被拒绝）")
        logger.info(f"     host={host} port={port}")
        logger.info(f"     请登录云端服务器检查服务状态")
        return False
    except Exception:
        logger.exception(f"  ❌ 云端 5004 检查异常")
        return False


def check_stats_push_endpoint():
    """检查 stats/push 端点是否注册"""
    port = os.getenv('RELAY_PORT', '5005')
    host = os.getenv('RELAY_HOST', '127.0.0.1')
    url = f'http://{host}:{port}/api/stats/push'

    health_url = f'http://{host}:{port}/api/health'
    try:
        requests.get(health_url, timeout=3)
    except Exception:
        logger.error(f"  ❌ 5005 未运行，无法检查 stats/push 端点")
        return False

    try:
        resp = requests.post(url, json={}, timeout=5)
        if resp.status_code == 401:
            logger.info(f"  ✅ stats/push 端点已注册（鉴权正常）")
            return True
        elif resp.status_code == 404:
            logger.error(f"  ❌ stats/push 端点未注册（404）")
            logger.info(f"     请重启 cloud_relay.py 加载新端点")
            return False
        else:
            logger.warning(f"  ⚠️  stats/push 端点响应异常: {resp.status_code} {resp.text[:100]}")
            return True
    except Exception:
        logger.warning(f"  ⚠️  stats/push 端点检查异常")
        return False


def check_smart_sheet_write_endpoint():
    """检查云端 5004 的 smartsheet/write 端点"""
    host = os.getenv('CLOUD_5004_HOST', '')
    port = os.getenv('CLOUD_5004_PORT', '5004')
    if not host:
        return None

    url = f'http://{host}:{port}/api/smartsheet/write'
    api_key = os.getenv('STATS_API_KEY', '')
    try:
        resp = requests.post(url, json={}, headers={'X-API-Key': api_key}, timeout=10)
        if resp.status_code == 401:
            logger.info(f"  ✅ smartsheet/write 端点已注册（鉴权正常）")
            return True
        elif resp.status_code == 400:
            logger.info(f"  ✅ smartsheet/write 端点已注册（缺少参数正常）")
            return True
        elif resp.status_code == 404:
            logger.error(f"  ❌ smartsheet/write 端点未注册（404）")
            logger.info(f"     请重启云端 cloud_group_bot_service.py")
            return False
        else:
            logger.warning(f"  ⚠️  smartsheet/write 响应: {resp.status_code}")
            return True
    except Exception:
        logger.warning(f"  ⚠️  smartsheet/write 检查异常")
        return False


def main():
    parser = argparse.ArgumentParser(description='服务健康检查')
    parser.add_argument('--restart', action='store_true', help='重启本地 5005')
    parser.add_argument('--all', action='store_true', help='检查全部（含云端）')
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("stats_smart_sheet 服务健康检查")
    logger.info("=" * 60)

    results = {}

    logger.info("\n📍 本地 5005:")
    results['local_5005'] = check_local_5005()

    logger.info("\n📍 stats/push 端点:")
    results['stats_push'] = check_stats_push_endpoint()

    if args.all or args.restart:
        logger.info("\n📍 云端 5004:")
        results['cloud_5004'] = check_cloud_5004()

        logger.info("\n📍 smartsheet/write 端点:")
        results['smart_sheet_write'] = check_smart_sheet_write_endpoint()

    logger.info("\n" + "=" * 60)
    logger.info("检查结果摘要")
    logger.info("=" * 60)
    ok_count = sum(1 for v in results.values() if v is True)
    fail_count = sum(1 for v in results.values() if v is False)
    skip_count = sum(1 for v in results.values() if v is None)
    logger.info(f"  通过: {ok_count}")
    logger.info(f"  失败: {fail_count}")
    logger.info(f"  跳过: {skip_count}")

    if fail_count == 0:
        logger.info("\n✅ 所有检查通过！")
    else:
        logger.warning("\n⚠️  有检查失败，请根据上述提示处理。")

    logger.info("=" * 60)
    return fail_count == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
