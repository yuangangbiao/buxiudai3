# -*- coding: utf-8 -*-
"""
缓存预热模块 - 应用启动时预加载热点数据

功能说明：
- 应用启动时自动预热Redis缓存
- 加载热点数据减少冷启动延迟
- 支持异步预热避免阻塞主线程

使用方式：
    from cache_warmup import warmup_cache, async_warmup_cache

    # 同步预热（启动时调用）
    warmup_cache()

    # 异步预热（在后台线程执行）
    async_warmup_cache()
"""
import os
import logging
import threading
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)

_warmup_lock = threading.Lock()
_warmup_completed = False


def _get_db_connection():
    """获取数据库连接"""
    try:
        from models.database import get_db_connection
        return get_db_connection()
    except Exception as e:
        logger.warning(f"[CacheWarmup] 获取数据库连接失败: {e}")
        return None


def _get_cache():
    """获取缓存实例"""
    try:
        from cache import get_cache
        cache = get_cache()
        if cache is None:
            from cache import fallback_cache
            return fallback_cache()
        return cache
    except Exception as e:
        logger.warning(f"[CacheWarmup] 获取缓存实例失败: {e}")
        return None


class WarmupTask:
    """预热任务定义"""

    def __init__(
        self,
        name: str,
        query_func: Callable[[], Any],
        cache_key: str,
        ttl: int = 300,
        condition: Optional[Callable[[], bool]] = None
    ):
        self.name = name
        self.query_func = query_func
        self.cache_key = cache_key
        self.ttl = ttl
        self.condition = condition

    def execute(self, cache) -> bool:
        """执行预热任务"""
        try:
            if self.condition and not self.condition():
                logger.debug(f"[CacheWarmup] 跳过任务 {self.name}（条件不满足）")
                return True

            data = self.query_func()
            if data is not None:
                cache.set(self.cache_key, data, ttl=self.ttl)
                logger.info(f"[CacheWarmup] 预热成功: {self.name} (key={self.cache_key})")
                return True
            else:
                logger.warning(f"[CacheWarmup] 预热数据为空: {self.name}")
                return False
        except Exception as e:
            logger.error(f"[CacheWarmup] 预热失败: {self.name}, error={e}")
            return False


def _get_warmup_tasks() -> List[WarmupTask]:
    """获取预热任务列表"""
    tasks = []

    def get_system_config():
        conn = _get_db_connection()
        if not conn:
            return None
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM system_config LIMIT 100")
                return cursor.fetchall()
        except Exception as e:
            logger.warning(f"[CacheWarmup] 查询系统配置失败: {e}")
            return None
        finally:
            conn.close()

    def get_product_types():
        conn = _get_db_connection()
        if not conn:
            return None
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM product_types WHERE is_active = 1 LIMIT 200")
                return cursor.fetchall()
        except Exception as e:
            logger.warning(f"[CacheWarmup] 查询产品类型失败: {e}")
            return None
        finally:
            conn.close()

    def get_process_list():
        conn = _get_db_connection()
        if not conn:
            return None
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM processes WHERE is_active = 1 LIMIT 100")
                return cursor.fetchall()
        except Exception as e:
            logger.warning(f"[CacheWarmup] 查询工序列表失败: {e}")
            return None
        finally:
            conn.close()

    def get_operators():
        conn = _get_db_connection()
        if not conn:
            return None
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM operators WHERE is_active = 1 LIMIT 100")
                return cursor.fetchall()
        except Exception as e:
            logger.warning(f"[CacheWarmup] 查询操作员失败: {e}")
            return None
        finally:
            conn.close()

    def get_active_orders():
        conn = _get_db_connection()
        if not conn:
            return None
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM orders WHERE status IN ('进行中', '待排产') LIMIT 500"
                )
                return cursor.fetchall()
        except Exception as e:
            logger.warning(f"[CacheWarmup] 查询活跃订单失败: {e}")
            return None
        finally:
            conn.close()

    def get_material_rules():
        conn = _get_db_connection()
        if not conn:
            return None
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM material_rules WHERE is_active = 1 LIMIT 100")
                return cursor.fetchall()
        except Exception as e:
            logger.warning(f"[CacheWarmup] 查询物料规则失败: {e}")
            return None
        finally:
            conn.close()

    def get_template_messages():
        conn = _get_db_connection()
        if not conn:
            return None
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM message_templates WHERE is_active = 1 LIMIT 100")
                return cursor.fetchall()
        except Exception as e:
            logger.warning(f"[CacheWarmup] 查询消息模板失败: {e}")
            return None
        finally:
            conn.close()

    tasks.append(WarmupTask(
        name="系统配置",
        query_func=get_system_config,
        cache_key="system:config",
        ttl=600
    ))

    tasks.append(WarmupTask(
        name="产品类型",
        query_func=get_product_types,
        cache_key="product:types",
        ttl=300
    ))

    tasks.append(WarmupTask(
        name="工序列表",
        query_func=get_process_list,
        cache_key="process:list",
        ttl=300
    ))

    tasks.append(WarmupTask(
        name="操作员",
        query_func=get_operators,
        cache_key="operators:list",
        ttl=180
    ))

    tasks.append(WarmupTask(
        name="活跃订单",
        query_func=get_active_orders,
        cache_key="orders:active",
        ttl=60
    ))

    tasks.append(WarmupTask(
        name="物料规则",
        query_func=get_material_rules,
        cache_key="material:rules",
        ttl=300
    ))

    tasks.append(WarmupTask(
        name="消息模板",
        query_func=get_template_messages,
        cache_key="templates:messages",
        ttl=600
    ))

    return tasks


def warmup_cache(force: bool = False) -> Dict[str, Any]:
    """
    执行缓存预热（同步）

    参数说明：
        force (bool): 是否强制预热（忽略已完成状态）

    返回值说明：
        Dict: 包含预热结果的字典
            - success (bool): 预热是否成功
            - total (int): 预热任务总数
            - completed (int): 成功完成的任务数
            - failed (int): 失败的任务数
            - duration (float): 预热耗时（秒）
    """
    global _warmup_completed

    with _warmup_lock:
        if _warmup_completed and not force:
            logger.info("[CacheWarmup] 缓存已预热，跳过")
            return {
                "success": True,
                "skipped": True,
                "message": "预热已完成，跳过"
            }

        cache = _get_cache()
        if cache is None:
            logger.warning("[CacheWarmup] 缓存不可用，跳过预热")
            return {
                "success": False,
                "error": "缓存不可用"
            }

        tasks = _get_warmup_tasks()
        start_time = datetime.now()
        success_count = 0
        failed_count = 0
        failed_tasks = []

        logger.info(f"[CacheWarmup] 开始预热，共 {len(tasks)} 个任务")

        for task in tasks:
            if task.execute(cache):
                success_count += 1
            else:
                failed_count += 1
                failed_tasks.append(task.name)

        duration = (datetime.now() - start_time).total_seconds()
        _warmup_completed = True

        result = {
            "success": failed_count == 0,
            "total": len(tasks),
            "completed": success_count,
            "failed": failed_count,
            "failed_tasks": failed_tasks,
            "duration": duration
        }

        logger.info(
            f"[CacheWarmup] 预热完成: 成功 {success_count}/{len(tasks)}, "
            f"失败 {failed_count}, 耗时 {duration:.2f}秒"
        )

        return result


def async_warmup_cache(force: bool = False) -> None:
    """
    异步执行缓存预热（在后台线程执行）

    参数说明：
        force (bool): 是否强制预热
    """
    thread = threading.Thread(
        target=warmup_cache,
        args=(force,),
        name="CacheWarmup",
        daemon=True
    )
    thread.start()
    logger.info("[CacheWarmup] 异步预热任务已启动")


def is_warmup_completed() -> bool:
    """检查预热是否已完成"""
    return _warmup_completed


def clear_warmup_status():
    """清除预热状态（用于测试或重置）"""
    global _warmup_completed
    _warmup_completed = False
