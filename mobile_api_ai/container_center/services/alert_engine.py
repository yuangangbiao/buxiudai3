# -*- coding: utf-8 -*-
"""
告警触发引擎 - container_center 子系统 v2

检查项（11 类，与 ARCHITECTURE_v3.6.md 第九章 9.2 节对齐）：
  1. 任务超时       — pending/dispatched/distributed 超 threshold (check_overdue_tasks)
  2. 任务停滞       — in_progress 停滞超 threshold (check_stalled_tasks)
  3. 积压告警       — pending 队列超阈值 (check_queue_depth)
  4. 操作员过载     — 单人任务数超限 (check_operator_overload)
  5. 完成率异常     — 完成率低于阈值 (check_completion_rate)
  6. 排产超时       — 计划截止日期已过期 (check_schedule_overdue)
  7. 任务超时告警   — 任务等待超过阈值 (合并实现于 check_order_timeout_alerts，意图拆分名 check_overdue_task_alerts)
  8. 订单逾期告警   — 订单超过 plan_end 未完成 (合并实现于 check_order_timeout_alerts，意图拆分名 check_order_overdue_alerts)
  9. 物料到货通知   — 物料到货提醒 (check_material_arrival)
  10. 外协到期/逾期提醒 — 外协任务在到期日前和逾期后发送提醒 (check_outsource_reminders)
  11. 告警自动升级  — 长期未解除的告警自动升级 (check_escalations)

严重度：CRITICAL > WARNING > INFO
"""
import json
import logging
import threading
import time
import uuid
from datetime import datetime
from typing import Callable, Dict, List, Optional

from template_engine import _render_template

logger = logging.getLogger(__name__)


class AlertEngine:
    def __init__(
        self,
        document_store,
        alert_store,
        config_store,
        send_message: Callable[[str, str], None],
        get_operators: Callable[[], Dict[str, dict]],
    ):
        self.doc_store = document_store
        self.alert_store = alert_store
        self.config_store = config_store
        self.send_message = send_message
        self.get_operators = get_operators
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._stats: Dict[str, int] = {'total_fired': 0, 'today_fired': 0, 'last_check': 0}

    @staticmethod
    def _flatten(pkg: dict) -> dict:
        flat = dict(pkg)
        if isinstance(flat.get('doc_data'), dict):
            flat.update(flat.pop('doc_data'))
        return flat

    # ── 分批迭代 ──────────────────────────────────────────
    BATCH_SIZE = 200

    def _iter_all_packages(self):
        """分批遍历所有数据包，避免一次性加载 5000 条"""
        packages = self.doc_store.get_packages(limit=5000)
        if not packages:
            return
        for i in range(0, len(packages), self.BATCH_SIZE):
            yield packages[i:i + self.BATCH_SIZE]

    # ── 配置读取 ───────────────────────────────────────────
    def _get_rules(self) -> dict:
        try:
            data = self.config_store.get('alert_rules')
            if isinstance(data, dict):
                return data
            if isinstance(data, str):
                import json
                return json.loads(data)
        except Exception:
            pass
        return {}

    # ── 去重 ───────────────────────────────────────────────
    def _is_duplicate(self, doc_id: str, alert_type: str, minutes: int = 30) -> bool:
        results = self.alert_store.query(alert_type=alert_type)
        for alert in results.get('data', []):
            if alert.get('doc_id') != doc_id:
                continue
            try:
                created = datetime.fromisoformat(alert['created_at'])
                if (datetime.now() - created).total_seconds() < minutes * 60:
                    return True
            except (ValueError, TypeError):
                continue
        return False

    # ── 消息发送包装 ─────────────────────────────────────
    LEVEL_PREFIX = {
        'CRITICAL': '🔴',
        'WARNING': '⚠️',
        'INFO': '📊',
    }

    def _send_alert(self, content: str, level: str = 'WARNING',
                   target_operator: str = '', send_to_group: bool = True) -> bool:
        """安全发送告警消息

        Args:
            content: 消息内容
            level: 消息级别
            target_operator: 目标操作员ID（发送个人消息用）
            send_to_group: 是否发送到群

        Returns:
            bool: 发送是否成功
        """
        try:
            prefix = self.LEVEL_PREFIX.get(level, '⚠️')
            msg = f'{prefix} [评级:{level}] {content}'
            success = True

            # 发送到群
            if send_to_group:
                result = self.send_message(msg, msg_type='markdown')
                if isinstance(result, tuple):
                    success = success and bool(result[0])
                elif isinstance(result, dict):
                    success = success and result.get('code', -1) == 0
                else:
                    success = success and bool(result)

            # 发送到个人（任务负责人）
            if target_operator:
                app_result = self.send_message(msg, msg_type='markdown', to_user=target_operator)
                if isinstance(app_result, tuple):
                    success = success and bool(app_result[0])
                elif isinstance(app_result, dict):
                    success = success and app_result.get('code', -1) == 0
                else:
                    success = success and bool(app_result)
                logger.info(f'[_send_alert] 已发送给个人: {target_operator}')

            return success
        except Exception as e:
            logger.error(f'[_send_alert] 发送失败: {e}')
            return False

    def _fire(self, alert_type: str, title: str, content: str, doc_id: str = '',
              level: str = 'WARNING', send: bool = True,
              target_operator: str = '', send_to_group: bool = True) -> bool:
        """统一告警创建入口，返回 True 表示新告警已创建

        Args:
            target_operator: 目标操作员ID（发送个人消息用）
            send_to_group: 是否发送到群
        """
        cooldown = self._get_rules().get('alert_cooldown_minutes', 30)
        if doc_id and self._is_duplicate(doc_id, alert_type, minutes=cooldown):
            return False
        self.alert_store.create(
            alert_type=alert_type, title=title, content=content,
            doc_id=doc_id, level=level,
        )
        self._stats['total_fired'] += 1
        self._stats['today_fired'] += 1
        if send:
            # CRITICAL 立即发送，WARNING/INFO 进入聚合缓冲区
            if level == 'CRITICAL':
                self._send_alert(content, level=level,
                               target_operator=target_operator,
                               send_to_group=send_to_group)
            else:
                self._alert_buffer.append({
                    'type': alert_type, 'level': level,
                    'operator': target_operator, 'title': title, 'time': datetime.now().isoformat(),
                })
        return True

    # ── 1. 任务超时检测 ───────────────────────────────────
    def check_overdue_tasks(self):
        try:
            packages = self.doc_store.get_packages(limit=5000)
            now = datetime.now()
            rules = self._get_rules()
            overdue_minutes = rules.get('auto_reassign_timeout', 60)
            max_alerts = rules.get('max_alerts_per_batch', 10)
            alert_count = 0

            for pkg in packages:
                if alert_count >= max_alerts:
                    break
                flat = self._flatten(pkg)
                status = flat.get('status')
                if status not in ('pending', 'dispatched', 'distributed'):
                    continue
                created_at = flat.get('created_at', '')
                if not created_at:
                    continue
                try:
                    ct = datetime.fromisoformat(created_at) if isinstance(created_at, str) else created_at
                    elapsed = (now - ct).total_seconds() / 60
                except (ValueError, TypeError):
                    continue
                if elapsed <= overdue_minutes:
                    continue

                pkg_id = flat.get('id')
                pkg_type = flat.get('data_type', 'work_order')
                self.doc_store.update_status(pkg_id, 'overdue', pkg_type)
                target_op_id = flat.get('target_operator', '')
                op = self.get_operators().get(target_op_id, {}).get('name', '未知')

                # 提醒次数: 从告警历史统计
                past_alerts = self.alert_store.query(alert_type='task_overdue')
                past_list = past_alerts.get('data', past_alerts) if isinstance(past_alerts, dict) else past_alerts
                reminder_count = len([
                    a for a in past_list
                    if a.get('doc_id') == pkg_id
                ]) + 1

                content = _render_template('tmpl_task_reminder', {
                    '提醒次数': reminder_count,
                    '任务标题': flat.get('title', ''),
                    '订单号': flat.get('related_order', ''),
                    '已用分钟': int(elapsed),
                    '负责人': op,
                })

                # 任务超时：发群 + 发个人（任务负责人）
                if self._fire('task_overdue', '任务超时', content,
                    pkg_id, level='WARNING',
                    target_operator=target_op_id,
                    send_to_group=True):
                    alert_count += 1

            if alert_count > 0:
                logger.info(f'[AlertEngine] 超时检查: {len(packages)}条, 触发{alert_count}告警')
        except Exception as e:
            logger.error(f'[AlertEngine] 超时检查失败: {e}')

    # ── 2. 任务停滞检测 ───────────────────────────────────
    def check_stalled_tasks(self):
        """检测 in_progress 状态停滞超过阈值的任务"""
        try:
            packages = self.doc_store.get_packages(limit=5000)
            now = datetime.now()
            rules = self._get_rules()
            stall_minutes = rules.get('task_stall_timeout', 120)
            cooldown = rules.get('alert_cooldown_minutes', 30)
            alert_count = 0
            max_alerts = rules.get('max_alerts_per_batch', 10)

            for pkg in packages:
                if alert_count >= max_alerts:
                    break
                flat = self._flatten(pkg)
                if flat.get('status') != 'in_progress':
                    continue
                updated_at = flat.get('updated_at', '')
                if not updated_at:
                    created_at = flat.get('created_at', '')
                    if not created_at:
                        continue
                    try:
                        ct = datetime.fromisoformat(created_at) if isinstance(created_at, str) else created_at
                        elapsed = (now - ct).total_seconds() / 60
                    except (ValueError, TypeError):
                        continue
                else:
                    try:
                        ut = datetime.fromisoformat(updated_at) if isinstance(updated_at, str) else updated_at
                        elapsed = (now - ut).total_seconds() / 60
                    except (ValueError, TypeError):
                        continue
                if elapsed <= stall_minutes:
                    continue

                pkg_id = flat.get('id')
                op = self.get_operators().get(flat.get('target_operator', ''), {}).get('name', '未知')
                if self._fire('task_stalled', '任务停滞',
                    f'🟡 **任务停滞告警**\n━━━━━━━━\n'
                    f'任务: {flat.get("title","")}\n订单: {flat.get("related_order","")}\n'
                    f'操作员: {op}\n停滞: {int(elapsed)} 分钟\n━━━━━━━━\n'
                    f'任务已被领取但长时间未推进，请关注',
                    pkg_id, level='INFO', send=False):
                    alert_count += 1

            if alert_count > 0:
                logger.info(f'[AlertEngine] 停滞检查: 触发{alert_count}告警')
        except Exception as e:
            logger.error(f'[AlertEngine] 停滞检查失败: {e}')

    # ── 3. 积压告警 ───────────────────────────────────────
    def check_queue_depth(self):
        """检测 pending 队列是否深度超标"""
        try:
            packages = self.doc_store.get_packages(limit=5000)
            now = datetime.now()
            rules = self._get_rules()
            threshold = rules.get('queue_depth_threshold', 50)

            pending_count = sum(1 for p in packages
                                if isinstance(p, dict) and self._flatten(p).get('status') == 'pending')
            if pending_count < threshold:
                return

            if self._fire('queue_depth', '任务积压',
                f'🔴 **任务积压告警**\n━━━━━━━━\n'
                f'当前待处理任务: {pending_count} 个\n阈值: {threshold} 个\n'
                f'━━━━━━━━\n建议: 增加排班或重新分配任务',
                doc_id='', level='CRITICAL'):
                logger.info(f'[AlertEngine] 积压告警: {pending_count}个 > {threshold}阈值')
        except Exception as e:
            logger.error(f'[AlertEngine] 积压检查失败: {e}')

    # ── 4. 操作员过载检测 ─────────────────────────────────
    def check_operator_overload(self):
        """检测单个操作员任务数是否超标"""
        try:
            packages = self.doc_store.get_packages(limit=5000)
            rules = self._get_rules()
            max_per_op = rules.get('max_tasks_per_operator', 20)

            op_counts: Dict[str, int] = {}
            for pkg in packages:
                if not isinstance(pkg, dict):
                    continue
                flat = self._flatten(pkg)
                if flat.get('status') not in ('distributed', 'in_progress', 'pending'):
                    continue
                op = (flat.get('target_operator') or '').strip()
                if op:
                    op_counts[op] = op_counts.get(op, 0) + 1

            operators = self.get_operators()
            for op_id, count in op_counts.items():
                if count <= max_per_op:
                    continue
                op_name = operators.get(op_id, {}).get('name', op_id)
                if self._fire('operator_overload', '操作员过载',
                    f'⚡ **操作员过载告警**\n━━━━━━━━\n'
                    f'操作员: {op_name}\n任务数: {count} 个\n上限: {max_per_op} 个\n'
                    f'━━━━━━━━\n建议: 转派部分任务',
                    doc_id=op_id, level='WARNING', send=False):
                    logger.info(f'[AlertEngine] 过载告警: {op_name} {count}个任务')
        except Exception as e:
            logger.error(f'[AlertEngine] 过载检查失败: {e}')

    # ── 5. 完成率异常检测 ─────────────────────────────────
    def check_completion_rate(self):
        """检测完成率是否低于阈值"""
        try:
            packages = self.doc_store.get_packages(limit=5000)
            rules = self._get_rules()
            min_rate = rules.get('min_completion_rate', 5)

            total = 0; completed = 0
            for pkg in packages:
                if not isinstance(pkg, dict):
                    continue
                st = self._flatten(pkg).get('status', '')
                if st in ('pending', 'dispatched', 'distributed', 'in_progress', 'completed', 'overdue'):
                    total += 1
                    if st == 'completed':
                        completed += 1

            if total < 10:  # 样本不足
                return
            rate = round(completed / total * 100, 1) if total > 0 else 0
            if rate >= min_rate:
                return

            if self._fire('low_completion', '完成率偏低',
                f'📊 **完成率异常告警**\n━━━━━━━━\n'
                f'当前完成率: {rate}%\n最低阈值: {min_rate}%\n'
                f'已完成: {completed} / 总任务: {total}\n'
                f'━━━━━━━━\n请关注整体生产进度',
                doc_id='', level='INFO', send=False):
                logger.info(f'[AlertEngine] 完成率告警: {rate}% < {min_rate}%')
        except Exception as e:
            logger.error(f'[AlertEngine] 完成率检查失败: {e}')

    # ── 5.5. 排产超时检测 ─────────────────────────────────
    def check_schedule_overdue(self):
        """检测排产计划是否已超期未完成"""
        try:
            packages = self.doc_store.get_packages(limit=5000)
            now = datetime.now()
            rules = self._get_rules()
            cooldown = rules.get('alert_cooldown_minutes', 30)
            count = 0
            for pkg in packages:
                content = pkg.get('content', {})
                if isinstance(content, str):
                    try: content = json.loads(content)
                    except json.JSONDecodeError: continue
                plan_end = content.get('plan_end', '')
                if not plan_end:
                    continue
                try:
                    end_date = datetime.strptime(plan_end, '%Y-%m-%d')
                except (ValueError, TypeError):
                    continue
                if end_date >= now:
                    continue
                status = pkg.get('status', '')
                if status in ('completed', 'confirmed'):
                    continue
                pkg_id = pkg.get('id') or content.get('order_no', '')
                if self._is_duplicate(str(pkg_id), 'schedule_overdue', minutes=cooldown):
                    continue
                overdue_days = (now - end_date).days
                order_no = content.get('order_no', pkg.get('related_order', ''))
                product = content.get('product_name', content.get('product_type', content.get('product', '')))
                quantity = content.get('quantity', 0)
                unit = content.get('unit', '件')
                content_msg = _render_template('tmpl_schedule_reminder', {
                    '订单号': order_no,
                    '产品': product,
                    '数量': quantity,
                    '单位': unit,
                    '截止时间': plan_end,
                    '超时天数': overdue_days,
                })
                if self._fire('schedule_overdue', '排产超时', content_msg, str(pkg_id), level='WARNING'):
                    count += 1
            if count:
                logger.info(f'[AlertEngine] 排产超时检查: 触发{count}条告警')
        except Exception as e:
            logger.error(f'[AlertEngine] 排产超时检查失败: {e}')

    # ── 5.6. 任务超时 + 订单逾期告警 ─────────────────────
    def check_order_timeout_alerts(self):
        """[向后兼容入口] 同时扫描任务超时 + 订单逾期告警

        拆分后由 check_overdue_task_alerts + check_order_overdue_alerts 分别承担，
        保留本方法作为合并入口，供旧调用方继续使用。
        """
        count_task = self.check_overdue_task_alerts()
        count_order = self.check_order_overdue_alerts()
        total = count_task + count_order
        if total:
            logger.info(f'[AlertEngine] 超时/逾期检查: {total}条告警 (任务超时 {count_task} + 订单逾期 {count_order})')
        return total

    def check_overdue_task_alerts(self):
        """任务超时告警 — 状态为 pending/dispatched 且超过阈值 (WARNING)"""
        try:
            packages = self.doc_store.get_packages(limit=5000)
            now = datetime.now()
            rules = self._get_rules()
            cooldown = rules.get('alert_cooldown_minutes', 60)
            timeout_minutes = rules.get('task_timeout_minutes', 30)
            alert_count = 0

            for pkg in packages:
                content = pkg.get('content', {})
                if isinstance(content, str):
                    try:
                        content = json.loads(content)
                    except json.JSONDecodeError:
                        continue
                status = pkg.get('status', '')
                pkg_id = pkg.get('id', '')

                if status not in ('pending', 'dispatched'):
                    continue
                created = pkg.get('created_at', '')
                try:
                    ct = datetime.fromisoformat(created) if isinstance(created, str) else created
                    elapsed = (now - ct).total_seconds() / 60
                except (ValueError, TypeError):
                    continue
                if elapsed <= timeout_minutes:
                    continue
                if self._is_duplicate(pkg_id, 'task_timeout', minutes=cooldown):
                    continue
                op = self.get_operators().get(pkg.get('target_operator', ''), {}).get('name', '未知')
                msg = _render_template('tmpl_alert_timeout', {
                    '标题': pkg.get('title', ''),
                    '订单号': pkg.get('related_order', ''),
                    '操作员': op,
                })
                if self._fire('task_timeout', '任务超时告警', msg, pkg_id, level='WARNING'):
                    alert_count += 1

            if alert_count:
                logger.info(f'[AlertEngine] 任务超时检查: {alert_count}条告警')
            return alert_count
        except Exception as e:
            logger.error(f'[AlertEngine] 任务超时检查失败: {e}')
            return 0

    def check_order_overdue_alerts(self):
        """订单逾期告警 — 订单已超过 plan_end 未完成 (CRITICAL)"""
        try:
            packages = self.doc_store.get_packages(limit=5000)
            now = datetime.now()
            rules = self._get_rules()
            cooldown = rules.get('alert_cooldown_minutes', 60)
            alert_count = 0

            for pkg in packages:
                content = pkg.get('content', {})
                if isinstance(content, str):
                    try:
                        content = json.loads(content)
                    except json.JSONDecodeError:
                        continue
                status = pkg.get('status', '')
                pkg_id = pkg.get('id', '')

                if status in ('completed', 'confirmed', 'cancelled'):
                    continue
                plan_end = content.get('plan_end', pkg.get('plan_end', ''))
                if not plan_end:
                    continue
                try:
                    end_date = datetime.strptime(plan_end, '%Y-%m-%d')
                except (ValueError, TypeError):
                    continue
                if end_date >= now:
                    continue
                if self._is_duplicate(pkg_id, 'order_overdue', minutes=cooldown):
                    continue
                overdue_days = (now - end_date).days
                order_no = pkg.get('related_order', content.get('order_no', ''))
                product = content.get('product_name', content.get('product', ''))
                client = content.get('customer', content.get('client', ''))
                msg = _render_template('tmpl_alert_overdue', {
                    '订单号': order_no,
                    '产品': product,
                    '客户': client,
                    '逾期天数': overdue_days,
                })
                if self._fire('order_overdue', '订单逾期告警', msg, pkg_id, level='CRITICAL'):
                    alert_count += 1

            if alert_count:
                logger.info(f'[AlertEngine] 订单逾期检查: {alert_count}条告警')
            return alert_count
        except Exception as e:
            logger.error(f'[AlertEngine] 订单逾期检查失败: {e}')
            return 0

    # ── 5.7. 物料到货通知 ─────────────────────────────
    def check_material_arrival(self):
        """扫描采购任务完成→发送物料到货通知"""
        try:
            packages = self.doc_store.get_packages(limit=5000)
            rules = self._get_rules()
            cooldown = rules.get('alert_cooldown_minutes', 60)
            count = 0
            for pkg in packages:
                if pkg.get('status') != 'completed':
                    continue
                content = pkg.get('content', {})
                if isinstance(content, str):
                    try: content = json.loads(content)
                    except json.JSONDecodeError: continue
                data_type = pkg.get('data_type', '')
                if data_type not in ('purchase', 'procurement'):
                    continue
                pkg_id = pkg.get('id', '')
                if self._is_duplicate(pkg_id, 'material_arrival', minutes=cooldown):
                    continue
                material = content.get('material_name', pkg.get('title', ''))
                qty = content.get('required_qty', content.get('quantity', 0))
                unit = content.get('unit', '个')
                supplier = content.get('supplier', content.get('vendor', '供应商'))
                msg = _render_template('tmpl_material_arrival', {
                    '物料名称': material,
                    '数量': qty,
                    '单位': unit,
                    '供应商': supplier,
                })
                if self._fire('material_arrival', '物料到货', msg, pkg_id, level='INFO'):
                    count += 1
            if count:
                logger.info(f'[AlertEngine] 物料到货通知: {count}条')
        except Exception as e:
            logger.error(f'[AlertEngine] 物料到货检查失败: {e}')

    # ── 6. 外协提醒 ───────────────────────────────────────
    def check_outsource_reminders(self):
        try:
            cfg = self.config_store.get('outsource_config') or {}
            if not cfg.get('enabled', False):
                return

            now = datetime.now()
            now_str = now.strftime('%Y-%m-%d %H:%M:%S')
            current_time_str = now.strftime('%H:%M')
            overdue_times = cfg.get('overdue_remind_times', [])
            remind_days = cfg.get('remind_days', [])

            # 检查所有类型的包，不限于 work_order
            packages = self.doc_store.get_packages(limit=5000) or []
            for pkg in packages:
                flat = self._flatten(pkg)
                if flat.get('data_type') != 'outsource':
                    continue
                status = flat.get('status', '')
                if status in ('completed', 'received'):
                    continue

                promised_date_str = flat.get('promised_date')
                if not promised_date_str:
                    continue

                try:
                    promised_date = datetime.fromisoformat(promised_date_str)
                    days_left = (promised_date - now).total_seconds() / 86400
                except (ValueError, TypeError):
                    continue

                target_op = flat.get('target_operator', '未知')
                op_name = self.get_operators().get(target_op, {}).get('name', target_op)
                title = flat.get('title', '')
                pkg_id = flat.get('id', '')

                if days_left <= 0:
                    if current_time_str in overdue_times:
                        last_remind = flat.get('last_remind_at', '')
                        if not last_remind or (now - datetime.fromisoformat(last_remind)).total_seconds() > 3600:
                            self.doc_store.update(pkg_id, {
                                'last_remind_at': now_str, 'overdue_remind_sent': True
                            }, flat.get('data_type', 'work_order'))
                            self.doc_store.update_status(pkg_id, 'overdue', flat.get('data_type', 'work_order'))
                            self._send_alert(
                                f'🚨 **外协逾期催单**\n━━━━━━━━\n'
                                f'任务: {title}\n操作员: {op_name}\n'
                                f'逾期: {int(-days_left)} 天\n━━━━━━━━\n请尽快完成！',
                                level='WARNING')
                elif round(days_left) in remind_days:
                    if not flat.get('reminder_sent', ''):
                        self.doc_store.update(pkg_id, {
                            'reminder_sent': f'{round(days_left)}days'
                        }, flat.get('data_type', 'work_order'))
                        self._send_alert(
                            f'⏰ **外协到期提醒**\n━━━━━━━━\n'
                            f'任务: {title}\n操作员: {op_name}\n'
                            f'剩余: {int(days_left)} 天\n━━━━━━━━\n请关注进度！',
                            level='INFO')
        except Exception as e:
            logger.error(f'[AlertEngine] 外协检查失败: {e}')

    # ── Auto-Resolution ────────────────────────────────────
    def auto_resolve_alerts(self):
        """自动解除已完成的/已提升的任务告警"""
        try:
            alerts = self.alert_store.query(dismissed=0, size=500)
            for alert in alerts.get('data', []):
                doc_id = alert.get('doc_id', '')
                if not doc_id:
                    continue
                try:
                    pkg = self.doc_store.get_package(doc_id)
                    if not pkg:
                        continue
                    st = self._flatten(pkg).get('status', '')
                    # 已完成/overdue/已转派 → 自动解除
                    if st in ('completed', 'overdue'):
                        self.alert_store.dismiss(alert['id'])
                        logger.debug(f'[AlertEngine] 自动解除告警 {alert["id"][:8]}: {st}')
                except Exception:
                    continue
        except Exception as e:
            logger.error(f'[AlertEngine] auto_resolve 失败: {e}')

    # ── Escalation: 未确认告警升级 ─────────────────────────
    def check_escalations(self):
        """WARNING 2h 未确认 → CRITICAL; CRITICAL 4h → 紧急通知"""
        try:
            now = datetime.now()
            thresholds = {
                'WARNING': 120,    # 2小时
                'CRITICAL': 240,   # 4小时
            }
            alerts = self.alert_store.query(dismissed=0, size=200)
            for alert in alerts.get('data', []):
                level = alert.get('level', 'INFO')
                if level not in thresholds:
                    continue
                # 已升级过的不再升级
                if alert.get('escalated_to'):
                    continue
                # 已确认的不升级
                if alert.get('acknowledged_at'):
                    continue
                # 被静默的不升级
                snoozed = alert.get('snoozed_until')
                if snoozed:
                    try:
                        if datetime.fromisoformat(snoozed) > now:
                            continue
                    except ValueError: pass

                try:
                    created = datetime.fromisoformat(alert['created_at'])
                    elapsed = (now - created).total_seconds() / 60
                except (ValueError, TypeError):
                    continue

                if elapsed > thresholds[level]:
                    new_level = 'CRITICAL' if level == 'WARNING' else 'CRITICAL'
                    self.alert_store.update(alert['id'], {
                        'escalated_to': new_level,
                        'escalated_at': now.isoformat(),
                    })
                    self._send_alert(
                        f'⬆️ **告警升级**\n━━━━━━━━\n{level} → {new_level}\n'
                        f'{alert["title"]}\n{elapsed:.0f}分钟未确认',
                        level='CRITICAL')
                    logger.info(f'[AlertEngine] 升级告警 {alert["id"][:8]}: {level}→{new_level}')
        except Exception as e:
            logger.error(f'[AlertEngine] 升级检查失败: {e}')

    # ── Correlation: 同订单告警归并 ─────────────────────────
    _alert_buffer: list = []  # 聚合缓冲区

    def _aggregate_and_send(self):
        """将缓冲区中的告警按类型+订单归并，发送摘要"""
        if not self._alert_buffer:
            return
        now = datetime.now()
        # 安静时段(22:00-07:00) 不发送
        hour = now.hour
        if 22 <= hour or hour < 7:
            return  # 保留在缓冲区，等下次检查

        rules = self._get_rules()
        max_agg = rules.get('max_alerts_per_batch', 10)
        alerts_to_send = self._alert_buffer[:max_agg]
        self._alert_buffer = self._alert_buffer[max_agg:]

        by_type = {}
        by_operator = {}
        for a in alerts_to_send:
            t = a.get('type', 'unknown')
            op = a.get('operator', '未知')
            by_type[t] = by_type.get(t, 0) + 1
            by_operator[op] = by_operator.get(op, 0) + 1

        type_lines = '\n'.join(f'  {t}: {c}条' for t, c in by_type.items())
        op_lines = '\n'.join(f'  {op}: {c}条' for op, c in list(by_operator.items())[:5])

        self._send_alert(
            f'📋 **告警摘要 ({now.strftime("%H:%M")})**\n'
            f'━━━━━━━━\n按类型:\n{type_lines}\n'
            f'按操作员:\n{op_lines}\n'
            f'━━━━━━━━\n共 {len(alerts_to_send)} 条待处理',
            level='INFO')
        logger.info(f'[AlertEngine] 聚合摘要发送: {len(alerts_to_send)}条')

    # ── 调度 ───────────────────────────────────────────────
    def start(self, interval_seconds: int = 60):
        if self._thread and self._thread.is_alive():
            logger.warning('[AlertEngine] 已在运行')
            return

        self._stop_event.clear()
        # 重置今日统计
        self._stats['today_fired'] = 0

        def _run():
            cycle = 0
            while not self._stop_event.is_set():
                try:
                    self.check_overdue_tasks()
                    self.check_stalled_tasks()
                    self.check_outsource_reminders()
                    # 每周期检查升级
                    self.check_escalations()
                    # 每周期发送聚合摘要
                    self._aggregate_and_send()
                    # 低频检查（每 5 周期一次）
                    if cycle % 5 == 0:
                        self.check_queue_depth()
                        self.check_operator_overload()
                        self.check_completion_rate()
                        self.check_schedule_overdue()
                        self.check_overdue_task_alerts()
                        self.check_order_overdue_alerts()
                        self.check_material_arrival()
                        self.auto_resolve_alerts()
                    self._stats['last_check'] = int(time.time())
                    cycle += 1
                except Exception as e:
                    logger.error(f'[AlertEngine] 周期异常: {e}')
                self._stop_event.wait(interval_seconds)

        self._thread = threading.Thread(target=_run, daemon=True, name='alert-engine')
        self._thread.start()
        logger.info(f'[AlertEngine] 已启动, 间隔{interval_seconds}s, 低频检查间隔{interval_seconds*5}s')

    def stop(self):
        self._stop_event.set()
        logger.info('[AlertEngine] 已停止')

    def health_check(self) -> Dict:
        """自检：引擎健康状态"""
        now = time.time()
        last = self._stats.get('last_check', 0)
        lag = int(now - last) if last else -1

        # 判断状态
        is_running = self._thread is not None and self._thread.is_alive()
        if not is_running:
            status = 'STOPPED'
        elif lag > 300:
            status = 'STALE'  # 上次检查超过5分钟
        elif lag > 120:
            status = 'DEGRADED'
        else:
            status = 'HEALTHY'

        return {
            'status': status,
            'running': is_running,
            'last_check': last,
            'lag_seconds': lag,
            'alerts_today': self._stats.get('today_fired', 0),
            'alerts_total': self._stats.get('total_fired', 0),
            'check_types': 6,  # overdue, stalled, outsourced, queue, overload, completion
            'low_freq_enabled': True,
        }

    def get_stats(self) -> Dict:
        return dict(self._stats)
