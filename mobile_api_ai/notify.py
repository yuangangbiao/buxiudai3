# -*- coding: utf-8 -*-
"""企业微信通知模块 — 覆盖他人数据时推送通知"""

import logging
import json
import sqlite3
import os
import time

logger = logging.getLogger(__name__)

_WECOM_ACCESS_TOKEN = None
_WECOM_TOKEN_EXPIRES = 0
_DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'notify_fallback.db')


def _get_fallback_db():
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS notify_fallback ("
                 "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                 "userid TEXT, "
                 "msg TEXT, "
                 "attempt INTEGER DEFAULT 0, "
                 "created_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
    conn.commit()
    conn.row_factory = sqlite3.Row
    return conn


def _get_access_token() -> str:
    """获取企业微信 access_token（缓存 110 分钟）"""
    global _WECOM_ACCESS_TOKEN, _WECOM_TOKEN_EXPIRES
    now = time.time()
    if _WECOM_ACCESS_TOKEN and now < _WECOM_TOKEN_EXPIRES:
        return _WECOM_ACCESS_TOKEN
    try:
        from core.config import WECHAT_CORP_ID, WECHAT_SECRET
        import requests
        resp = requests.get(
            'https://qyapi.weixin.qq.com/cgi-bin/gettoken',
            params={'corpid': WECHAT_CORP_ID, 'corpsecret': WECHAT_SECRET},
            timeout=10)
        data = resp.json()
        if data.get('errcode') == 0:
            _WECOM_ACCESS_TOKEN = data['access_token']
            _WECOM_TOKEN_EXPIRES = now + 6600  # 110min
            return _WECOM_ACCESS_TOKEN
    except Exception as e:
        logger.warning(f'[Notify] 获取 access_token 失败: {e}')
    return ''


def send_notification(userid: str, message: str) -> bool:
    """发送企业微信文本消息。失败则入降级队列。"""
    token = _get_access_token()
    if not token:
        return _fallback(userid, message)

    try:
        import requests
        resp = requests.post(
            'https://qyapi.weixin.qq.com/cgi-bin/message/send',
            params={'access_token': token},
            json={
                'touser': userid,
                'msgtype': 'text',
                'agentid': 0,
                'text': {'content': message},
            },
            timeout=10)
        data = resp.json()
        if data.get('errcode') == 0:
            logger.info(f'[Notify] 发送成功 → {userid}')
            return True
        logger.warning(f'[Notify] 发送失败: {data}')
    except Exception as e:
        logger.warning(f'[Notify] 网络异常: {e}')
    return _fallback(userid, message)


def _fallback(userid: str, message: str) -> bool:
    """降级：存入本地队列，稍后重试"""
    conn = _get_fallback_db()
    conn.execute("INSERT INTO notify_fallback (userid, msg) VALUES (?,?)", (userid, message))
    conn.commit()
    conn.close()
    return False


def process_fallback_queue() -> int:
    """处理降级队列，返回成功数"""
    conn = _get_fallback_db()
    rows = conn.execute("SELECT * FROM notify_fallback ORDER BY id LIMIT 20").fetchall()
    count = 0
    for row in rows:
        try:
            if send_notification(row['userid'], row['msg']):
                conn.execute("DELETE FROM notify_fallback WHERE id=?", (row['id'],))
                count += 1
            else:
                conn.execute("UPDATE notify_fallback SET attempt=attempt+1 WHERE id=?", (row['id'],))
        except Exception:
            pass
    conn.commit()
    conn.close()
    return count


def notify_override(covered_operator: str, order_no: str, step_name: str,
                    old_qty: float, new_qty: float, by_operator: str) -> bool:
    """便捷方法：通知被覆盖的操作员"""
    msg = (f"【报工数据修正】\n"
           f"订单: {order_no}\n"
           f"工序: {step_name}\n"
           f"原数量: {old_qty} → 新数量: {new_qty}\n"
           f"修正人: {by_operator}\n"
           f"如有疑问请联系管理员")
    return send_notification(covered_operator, msg)


def notify_admin_modified(original_operator: str, admin_user: str,
                          order_no: str, step_name: str,
                          old_qty: float, new_qty: float, remark: str = '') -> bool:
    """通知原操作员：你的报工被调度员修改"""
    msg = (f"【报工被调度员修改】\n"
           f"订单: {order_no}\n"
           f"工序: {step_name}\n"
           f"原数量: {old_qty} → 新数量: {new_qty}\n"
           f"操作员: {admin_user}\n"
           f"原因: {remark or '管理员修正'}\n"
           f"如有疑问请联系调度员")
    return send_notification(original_operator, msg)


def notify_admin_withdraw(original_operator: str, admin_user: str,
                          order_no: str, step_name: str, old_qty: float) -> bool:
    """通知原操作员：你的报工被调度员撤回"""
    msg = (f"【报工被调度员撤回】\n"
           f"订单: {order_no}\n"
           f"工序: {step_name}\n"
           f"原数量: {old_qty}\n"
           f"操作员: {admin_user}\n"
           f"如有疑问请联系调度员")
    return send_notification(original_operator, msg)


def notify_quality_modified(inspector: str, admin_user: str,
                            order_no: str, step_name: str,
                            old_result: str, new_result: str, remark: str = '') -> bool:
    """通知原质检员：质检结果被调度员修改"""
    msg = (f"【质检结果被调度员修改】\n"
           f"订单: {order_no}\n"
           f"工序: {step_name}\n"
           f"原结果: {old_result} → 新结果: {new_result}\n"
           f"操作员: {admin_user}\n"
           f"原因: {remark or '管理员修正'}\n"
           f"如有疑问请联系调度员")
    return send_notification(inspector, msg)


def notify_quality_withdraw(inspector: str, admin_user: str,
                            order_no: str, step_name: str, old_result: str) -> bool:
    """通知原质检员：质检记录被调度员撤回"""
    msg = (f"【质检记录被调度员撤回】\n"
           f"订单: {order_no}\n"
           f"工序: {step_name}\n"
           f"原结果: {old_result}\n"
           f"操作员: {admin_user}\n"
           f"如有疑问请联系调度员")
    return send_notification(inspector, msg)
