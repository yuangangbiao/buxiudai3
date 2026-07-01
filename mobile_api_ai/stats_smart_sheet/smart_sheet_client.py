# -*- coding: utf-8 -*-
"""
9 张统计表 → 智能表格 推送客户端
- 本地 5005 (cloud_relay.py) 调用
- 含失败重试（H-4 修复）
- 含幂等性 batch_id（H-2 修复）
"""
import logging
import uuid
import hashlib
import json
import time
from typing import List, Dict, Any

import requests

from .config import PUSH_CONFIG, FIELD_MAPPING

logger = logging.getLogger(__name__)


def compute_hash(records: List[Dict]) -> str:
    """计算记录列表的 SHA256 哈希（用于幂等性）"""
    content = json.dumps(records, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:64]


def map_to_field_ids(table_type: str, records: List[Dict]) -> List[Dict]:
    """将中文字段映射到智能表格 field_id"""
    mapping = FIELD_MAPPING.get(table_type, {})
    if not mapping:
        logger.warning(f"[{table_type}] 字段映射未配置")
        return records
    mapped = []
    for r in records:
        new_r = {}
        for k, v in r.items():
            fid = mapping.get(k, k)  # 找不到映射就保留原 key
            new_r[fid] = v
        mapped.append(new_r)
    return mapped


def push_with_retry(table_type: str, records: List[Dict],
                    period_key: str = '') -> Dict[str, Any]:
    """
    推送数据到 5005（含重试）
    返回: {'code': 0/-1, 'message': '...', 'batch_id': '...', 'success_count': N}
    """
    if not records:
        logger.info(f"[{table_type}] 无数据，跳过推送")
        return {'code': 0, 'message': '无数据', 'batch_id': '', 'success_count': 0}

    batch_id = str(uuid.uuid4())
    record_hash = compute_hash(records)
    payload = {
        'table_type': table_type,
        'period_key': period_key or '',
        'batch_id': batch_id,
        'record_hash': record_hash,
        'records': map_to_field_ids(table_type, records),
    }

    url = f"{PUSH_CONFIG['local_5005_url']}{PUSH_CONFIG['push_endpoint']}"
    headers = {
        'Content-Type': 'application/json',
        'X-API-Key': PUSH_CONFIG['stats_api_key'],
    }
    timeout = PUSH_CONFIG['request_timeout']
    max_retries = PUSH_CONFIG['max_retries']

    last_err = None
    for attempt in range(max_retries):
        logger.info(f"[{table_type}] 推送尝试 {attempt + 1}/{max_retries} | "
                    f"records={len(records)} batch_id={batch_id[:8]}")
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
            result = resp.json()
        except (ValueError, Exception) as e:
            last_err = f"响应解析失败: {e}"
            logger.warning(f"[{table_type}] 响应解析失败(尝试{attempt+1}): {e}")
        else:
            if result.get('code') == 0:
                logger.info(f"[{table_type}] 推送成功: {result.get('message')}")
                return {
                    'code': 0,
                    'message': result.get('message', 'OK'),
                    'batch_id': batch_id,
                    'success_count': result.get('success_count', len(records)),
                }
            last_err = result.get('message', '未知错误')
            logger.warning(f"[{table_type}] 推送失败(尝试{attempt+1}): {last_err}")

        if attempt < max_retries - 1:
            wait = PUSH_CONFIG['retry_base_interval'] ** (attempt + 1)
            logger.info(f"[{table_type}] {wait}秒后重试")
            time.sleep(wait)

    logger.error(f"[{table_type}] 推送最终失败: {last_err}")
    return {
        'code': -1,
        'message': f'推送失败: {last_err}',
        'batch_id': batch_id,
        'success_count': 0,
    }
