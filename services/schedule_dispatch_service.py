# -*- coding: utf-8 -*-
"""
排产调度服务 - 事件触发模式，发布时直接发送到容器中心

流程：
1. 主软件点击"确认发布" → 直接发往容器中心
2. 容器中心 → 调度中心 → 云端 → 企业微信
3. 企业微信操作员确认 → 云端 → 调度中心 → 容器中心
4. 容器中心回调主软件API → 标记已排产
"""

import os
import json
import logging
import threading
import time
from datetime import date, datetime
from typing import Dict, Any

import requests

from models.database import get_connection, log_status_change
from constants import ProductionStatus, OrderStatus
from utils.op_logger import log_ui
from config import CONTAINER_CENTER_URL

logger = logging.getLogger(__name__)

_QUEUE_RECOVERY_STARTED = False
_QUEUE_RECOVERY_LOCK = threading.Lock()


class ScheduleDispatchService:
    """排产调度服务"""

    @classmethod
    def _get_container_center_url(cls) -> str:
        return CONTAINER_CENTER_URL

    @classmethod
    def _get_container_api_key(cls) -> str:
        return os.getenv('CONTAINER_API_KEY', '')

    @staticmethod
    def _safe(val: Any) -> Any:
        if isinstance(val, (datetime, date)):
            return val.strftime('%Y-%m-%d %H:%M:%S') if isinstance(val, datetime) else val.strftime('%Y-%m-%d')
        return val

    @classmethod
    def publish_schedule(cls, order_no: str, order: Dict[str, Any],
                         prod_id: int, plan_start: str, plan_end: str) -> Dict[str, Any]:
        """
        事件触发：直接发送排产任务到容器中心（无队列）

        Args:
            order_no: 订单号
            order: 订单完整信息
            prod_id: 生产工单ID
            plan_start: 计划开始日期
            plan_end: 计划结束日期

        Returns:
            dict: {"success": bool, "message": str}
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()

            # 防重复校验 - 双重验证：同时检查本地队列和容器中心
            cursor.execute(
                "SELECT id, status FROM schedule_queue WHERE order_no=%s AND status='success'",
                (order_no,)
            )
            existing = cursor.fetchone()
            if existing:
                verify_url = f"{cls._get_container_center_url()}/api/processes/by-order/{order_no}"
                try:
                    verify_resp = requests.get(verify_url, timeout=5)
                    if verify_resp.status_code == 200:
                        verify_data = verify_resp.json()
                        if verify_data.get('code') == 0 and verify_data.get('data'):
                            log_ui("排产调度", "重复提交", f"工单={order_no} 已成功发布")
                            return {'success': True, 'message': f'工单 {order_no} 已发布，无需重复提交'}
                except Exception as e:
                    logger.warning(
                        f"[排产调度] 验证容器中心工单状态失败: {e}",
                        extra={"order_no": order_no, "endpoint": verify_url}
                    )

                cursor.execute("DELETE FROM schedule_queue WHERE id=%s", (existing['id'],))
                conn.commit()
                log_ui("排产调度", "重新发布", f"工单={order_no} 容器中心无记录，重新发送")

            payload = cls._build_payload(order_no, order, prod_id, plan_start, plan_end)

            # 记录到队列（初始状态 sending）
            payload_json = json.dumps(payload, ensure_ascii=False, default=str)
            cursor.execute(
                "SELECT id FROM schedule_queue WHERE order_no=%s AND status='failed' ORDER BY id DESC LIMIT 1",
                (order_no,)
            )
            failed = cursor.fetchone()
            if failed:
                cursor.execute(
                    "UPDATE schedule_queue SET payload=%s, status='sending', retry_count=0, last_error=NULL, updated_at=NOW() WHERE id=%s",
                    (payload_json, failed['id'])
                )
                queue_id = failed['id']
            else:
                cursor.execute(
                    "INSERT INTO schedule_queue (order_no, prod_id, payload, status) VALUES (%s, %s, %s, 'sending')",
                    (order_no, prod_id, payload_json)
                )
                queue_id = cursor.lastrowid
            conn.commit()

            # 直接发送到容器中心
            result = cls._actually_send(queue_id, payload)
            if result['success']:
                cursor.execute(
                    "UPDATE schedule_queue SET status='success', updated_at=NOW() WHERE id=%s",
                    (queue_id,)
                )
                order_no = payload.get('order_no', '')
                if order_no:
                    cursor.execute(
                        "UPDATE orders SET status=%s, updated_at=NOW() WHERE order_no=%s",
                        (OrderStatus.CONFIRMED.value, order_no)
                    )
                conn.commit()
                log_ui("排产调度", "发布成功", f"工单={order_no}")
                return {'success': True, 'message': '排产发布成功，等待企业微信操作员确认'}
            else:
                cursor.execute(
                    "UPDATE schedule_queue SET status='failed', retry_count=retry_count+1, last_error=%s, updated_at=NOW() WHERE id=%s",
                    (result['message'][:500], queue_id)
                )
                conn.commit()
                log_ui("排产调度", "发布失败", f"工单={order_no}, {result['message']}")
                return {'success': False, 'message': f'发布失败：{result["message"]}'}

        except Exception as e:
            logger.error(
                f"[排产调度] 发布异常: {e}",
                exc_info=True,
                extra={"order_no": order_no}
            )
            try:
                cursor.execute(
                    "UPDATE schedule_queue SET status='failed', last_error=%s, updated_at=NOW() WHERE order_no=%s AND status='sending'",
                    (str(e)[:500], order_no)
                )
                conn.commit()
            except Exception:
                logger.debug("[排产调度] 失败状态更新异常", exc_info=True)
            return {'success': False, 'message': f'发布异常: {str(e)}'}
        finally:
            conn.close()

    @classmethod
    def _build_payload(cls, order_no: str, order: Dict[str, Any],
                       prod_id: int, plan_start: str, plan_end: str) -> dict:
        extra_params = order.get("extra_params", {})
        if isinstance(extra_params, str):
            try:
                extra_params = json.loads(extra_params)
            except Exception as e:
                logger.error("[排产调度] JSON解析extra_params失败: %s", e, exc_info=True, extra={"order_no": order_no})
                extra_params = {}
        if isinstance(extra_params, dict):
            extra_params = {k: cls._safe(v) for k, v in extra_params.items()}

        return {
            'order_no': order_no,
            'prod_id': prod_id,
            'plan_start': plan_start,
            'plan_end': plan_end,
            'product_type_id': order.get('product_type_id', 0),
            'customer_group': cls._safe(order.get('customer_group', '') or order.get('customer_name', '')),
            'product_type': cls._safe(order.get('product_type', '')),
            'material': cls._safe(order.get('material', '')),
            'mesh_size': cls._safe(order.get('mesh_size', '')),
            'wire_diameter': cls._safe(order.get('wire_diameter', '')),
            'width': cls._safe(order.get('width', '')),
            'length': cls._safe(order.get('length', '')),
            'quantity': order.get('quantity', 0),
            'unit': cls._safe(order.get('unit', '米')),
            'surface_treatment': cls._safe(order.get('surface_treatment', '')),
            'special_requirements': cls._safe(order.get('special_requirements', '')),
            'delivery_date': cls._safe(order.get('delivery_date', '')),
            'remark': cls._safe(order.get('remark', '')),
            'extra_params': extra_params,
            'source': 'desktop_schedule',
            'product_type_id': order.get('product_type_id', 0),
        }

    @classmethod
    def _actually_send(cls, queue_id: int, payload: dict) -> Dict[str, Any]:
        """
        实际发送排产数据到容器中心
        被后台队列线程调用
        """
        try:
            url = f"{cls._get_container_center_url()}/api/schedule/publish"
            headers = {'Content-Type': 'application/json'}
            api_key = cls._get_container_api_key()
            if api_key:
                headers['X-API-Key'] = api_key

            log_ui("排产调度", "后台发送", f"队列ID={queue_id}, 工单={payload['order_no']}")

            response = requests.post(url, json=payload, headers=headers, timeout=15)

            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0 or result.get('success'):
                    # 检查是否重复
                    data = result.get('data', {})
                    if data.get('duplicate'):
                        msg = f"队列ID={queue_id}, {data.get('message', '工单已存在')}"
                        log_ui("排产调度", "重复跳过", msg)
                        return {'success': True, 'message': data.get('message', '工单已存在，跳过'), 'duplicate': True}
                    log_ui("排产调度", "发送成功", f"队列ID={queue_id}")
                    return {'success': True, 'message': '发送成功'}
                error_msg = result.get('message', '容器中心返回失败')
                log_ui("排产调度", "发送失败", f"队列ID={queue_id}, {error_msg}")
                return {'success': False, 'message': error_msg}

            log_ui("排产调度", "请求异常", f"队列ID={queue_id}, HTTP {response.status_code}")
            return {'success': False, 'message': f'HTTP {response.status_code}'}

        except requests.ConnectionError:
            error_msg = f"无法连接容器中心 ({cls._get_container_center_url()})"
            logger.error(
                f"[排产调度] {error_msg}",
                extra={"order_no": payload.get("order_no", ""),
                       "endpoint": f"{cls._get_container_center_url()}/api/schedule/publish"}
            )
            return {'success': False, 'message': error_msg}
        except requests.Timeout:
            error_msg = "容器中心请求超时"
            logger.error(
                f"[排产调度] {error_msg}",
                extra={"order_no": payload.get("order_no", ""),
                       "endpoint": f"{cls._get_container_center_url()}/api/schedule/publish"}
            )
            return {'success': False, 'message': error_msg}
        except Exception as e:
            error_msg = f"发送异常: {str(e)}"
            logger.error(
                f"[排产调度] {error_msg}",
                exc_info=True,
                extra={"order_no": payload.get("order_no", ""),
                       "endpoint": f"{cls._get_container_center_url()}/api/schedule/publish"}
            )
            return {'success': False, 'message': error_msg}

    @classmethod
    def _is_container_center_available(cls, timeout=3) -> bool:
        """检测容器中心是否可达"""
        try:
            url = f"{cls._get_container_center_url()}/api/health"
            r = requests.get(url, timeout=timeout)
            return r.status_code == 200
        except Exception:
            logger.debug("[排产调度] 容器中心健康检查失败", exc_info=True)
            return False

    @classmethod
    def _retry_single_queue_item(cls, queue_id: int, order_no: str, payload: dict) -> bool:
        """重试单个队列条目"""
        try:
            url = f"{cls._get_container_center_url()}/api/schedule/publish"
            headers = {'Content-Type': 'application/json'}
            api_key = cls._get_container_api_key()
            if api_key:
                headers['X-API-Key'] = api_key

            response = requests.post(url, json=payload, headers=headers, timeout=15)
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0 or result.get('success'):
                    return True
                logger.warning(
                    f"[排产恢复] API返回失败: {result.get('message', '未知错误')}",
                    extra={"order_no": order_no,
                           "endpoint": f"{cls._get_container_center_url()}/api/schedule/publish"}
                )
            else:
                logger.warning(
                    f"[排产恢复] HTTP {response.status_code}",
                    extra={"order_no": order_no, "http_status": response.status_code}
                )
            return False
        except Exception as e:
            logger.warning(
                f"[排产恢复] 请求异常: {e}",
                extra={"order_no": order_no}
            )
            return False

    @classmethod
    def _process_failed_queue(cls):
        """后台线程：处理失败的队列条目，自动重试"""
        while True:
            try:
                if not cls._is_container_center_available():
                    time.sleep(15)
                    continue

                conn = get_connection()
                cursor = conn.cursor()
                try:
                    cursor.execute("""
                        SELECT id, order_no, payload, retry_count
                        FROM schedule_queue
                        WHERE status IN ('failed', 'sending')
                          AND retry_count < 5
                        ORDER BY id ASC
                        LIMIT 10
                    """)
                    items = cursor.fetchall()

                    if items:
                        logger.info(f"[排产恢复] 发现 {len(items)} 条待重试记录")
                        log_ui("排产恢复", "开始处理", f"发现 {len(items)} 条待重试")

                    for item in items:
                        queue_id = item['id']
                        order_no = item['order_no']
                        payload = json.loads(item['payload']) if item['payload'] else {}
                        retry_count = item['retry_count']

                        if cls._retry_single_queue_item(queue_id, order_no, payload):
                            cursor.execute(
                                "UPDATE schedule_queue SET status='success', retry_count=retry_count+1, updated_at=NOW() WHERE id=%s",
                                (queue_id,)
                            )
                            log_ui("排产恢复", "重试成功", f"工单={order_no}")
                            logger.info(f"[排产恢复] 成功: {order_no} (重试{retry_count + 1}次)")
                        else:
                            cursor.execute(
                                "UPDATE schedule_queue SET status='failed', retry_count=retry_count+1, updated_at=NOW() WHERE id=%s",
                                (queue_id,)
                            )
                            logger.warning(
                                f"[排产恢复] 重试失败: {order_no} (第{retry_count + 1}次)",
                                extra={"order_no": order_no, "retry_count": retry_count + 1}
                            )

                    conn.commit()
                finally:
                    cursor.close()
                    conn.close()
            except Exception as e:
                logger.error(f"[排产恢复] 队列处理异常: {e}")

            time.sleep(15)

    @classmethod
    def get_dead_letters(cls) -> list:
        """获取死信列表（retry_count >= 5 且 status='failed'）"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, order_no, prod_id, payload, retry_count, last_error, created_at, updated_at
                FROM schedule_queue
                WHERE status = 'failed'
                  AND retry_count >= 5
                  AND payload IS NOT NULL
                  AND payload != ''
                ORDER BY id DESC
                LIMIT 50
            """)
            rows = cursor.fetchall()
            cursor.close()
            result = [dict(r) for r in rows]
            if len(result) >= 10:
                logger.warning('[死信告警] schedule_queue 死信已达 %d 条，请及时处理', len(result))
            return result
        finally:
            conn.close()

    @classmethod
    def retry_dead_letter(cls, queue_id: int) -> Dict[str, Any]:
        """重发死信条目 — 原子重置并发送

        Returns: {"success": bool, "message": str, "skipped": bool}
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()

            # 原子抢占：仅当条目仍是死信状态时才重置
            cursor.execute(
                "UPDATE schedule_queue SET retry_count=0, status='sending', last_error=NULL, "
                "updated_at=NOW() WHERE id=%s AND status='failed' AND retry_count >= 5",
                (queue_id,)
            )
            if cursor.rowcount == 0:
                conn.commit()
                cursor.close()
                return {'success': True, 'message': '已被其他进程处理，跳过', 'skipped': True}

            # 读取 payload
            cursor.execute("SELECT payload FROM schedule_queue WHERE id=%s", (queue_id,))
            row = cursor.fetchone()
            if not row or not row['payload']:
                conn.rollback()
                cursor.close()
                return {'success': False, 'message': '死信条目数据缺失'}

            try:
                payload = json.loads(row['payload'])
            except json.JSONDecodeError:
                conn.rollback()
                cursor.close()
                return {'success': False, 'message': '死信条目JSON解析失败'}

            conn.commit()
            cursor.close()

            # 发送到容器中心
            result = cls._actually_send(queue_id, payload)
            order_no = payload.get('order_no', '')

            # 更新最终状态
            conn2 = get_connection()
            try:
                c2 = conn2.cursor()
                if result['success']:
                    c2.execute(
                        "UPDATE schedule_queue SET status='success', updated_at=NOW() WHERE id=%s",
                        (queue_id,)
                    )
                    msg = result.get('message', '')
                    if result.get('duplicate'):
                        log_ui("死信重发", "重复跳过", f"工单={order_no}, {msg}")
                    else:
                        log_ui("死信重发", "发送成功", f"工单={order_no}")
                else:
                    c2.execute(
                        "UPDATE schedule_queue SET status='failed', "
                        "retry_count=retry_count+1, last_error=%s, updated_at=NOW() WHERE id=%s",
                        (result['message'][:500], queue_id)
                    )
                    log_ui("死信重发", "发送失败", f"工单={order_no}, {result['message']}")
                conn2.commit()
                c2.close()
            finally:
                conn2.close()

            return result

        except requests.ConnectionError:
            return {'success': False, 'message': f'容器中心连接失败 ({cls._get_container_center_url()})'}
        except Exception as e:
            logger.error(f"[死信重发] 异常: {e}", exc_info=True)
            return {'success': False, 'message': f'重发异常: {str(e)}'}
        finally:
            conn.close()

    @classmethod
    def start_queue_recovery(cls):
        """启动后台队列恢复线程（全局只启动一次）"""
        global _QUEUE_RECOVERY_STARTED
        with _QUEUE_RECOVERY_LOCK:
            if _QUEUE_RECOVERY_STARTED:
                return
            _QUEUE_RECOVERY_STARTED = True

        t = threading.Thread(target=cls._process_failed_queue, daemon=True,
                             name="schedule-queue-recovery")
        t.start()
        logger.info("[排产调度] 队列恢复线程已启动（每15秒检查失败工单）")

    @classmethod
    def handle_schedule_callback(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理排产回调 - 企业微信操作员确认排产后

        调用方：WeChatCallbackAPI（由容器中心回调）
        """
        required_fields = ['order_no', 'prod_id', 'plan_start', 'plan_end']
        missing = [f for f in required_fields if f not in data]
        if missing:
            return {"success": False, "message": f"缺少必需字段: {','.join(missing)}"}

        order_no = data['order_no']
        prod_id = data['prod_id']
        plan_start = data['plan_start']
        plan_end = data['plan_end']
        operator = data.get('operator', '企业微信')
        remark = data.get('remark', '')

        log_ui("排产调度", "收到回调", f"工单={order_no}, 操作员={operator}")

        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT status, order_id FROM production_orders WHERE id=%s", (prod_id,))
            old = cursor.fetchone()
            old_status = old['status'] if old else None
            order_id = old['order_id'] if old else None

            if old_status == ProductionStatus.PENDING.value:
                log_ui("排产调度", "已排产", f"工单={order_no}, 状态已是待开始，仅更新日期")
                cursor.execute("UPDATE production_orders SET plan_start=%s, plan_end=%s, updated_at=NOW() WHERE id=%s",
                              (plan_start, plan_end, prod_id))
            else:
                new_status = ProductionStatus.PENDING.value
                cursor.execute("""
                    UPDATE production_orders
                    SET status=%s, plan_start=%s, plan_end=%s,
                        updated_at=NOW()
                    WHERE id=%s
                """, (new_status, plan_start, plan_end, prod_id))

                if order_id:
                    cursor.execute("UPDATE orders SET status=%s, updated_at=NOW() WHERE id=%s",
                                   (OrderStatus.SCHEDULED.value, order_id))

            if remark:
                cursor.execute("""
                    UPDATE production_orders SET remark = CONCAT_WS('; ', remark, %s)
                    WHERE id=%s
                """, (f"[排产回调] {remark}", prod_id))

            conn.commit()

            if old_status and old_status != ProductionStatus.PENDING.value:
                log_status_change("production_orders", prod_id, old_status,
                                  ProductionStatus.PENDING.value,
                                  operator=operator, remark=f"排产回调确认:{remark}")

            log_ui("排产调度", "回调处理完成", f"工单={order_no}, 状态→待开始")

            from core.event_bus import EventBus, Events
            EventBus.publish(Events.ORDER_UPDATED, {
                'order_no': order_no,
                'prod_id': prod_id,
                'status': ProductionStatus.PENDING.value,
                'plan_start': plan_start,
                'plan_end': plan_end,
            })

            return {"success": True, "message": "排产回调处理成功"}

        except Exception as e:
            logger.error(
                f"处理排产回调失败: {e}",
                exc_info=True,
                extra={"order_no": order_no, "operator": operator}
            )
            conn.rollback()
            return {"success": False, "message": f"排产回调处理失败: {str(e)}"}
        finally:
            conn.close()
