# -*- coding: utf-8 -*-
"""
[F16 T16.5 修复] product_flow_map 表已于 F6 P9 2026-06-10 DROP
        (跨库历史表清理, 详见 .workbuddy/memory/MEMORY.md L20)
        原表存 product_type_id → flow_type 映射 (13 行), 现统一硬编码 'production'
        调用方必须显式传 flow_type, 不再支持 product_type_id 隐式推断

修复: try/except 1146 → 返 'production' 兼容, 业务零阻塞
"""
import logging
from models.database import get_connection

logger = logging.getLogger(__name__)


def _is_f6p9_dropped_error(exc) -> bool:
    """识别 1146 Table doesn't exist (F6 P9 DROP 标识)"""
    err = str(exc)
    return '1146' in err or 'doesn\'t exist' in err


class ProductFlowMapDAO:
    @staticmethod
    def get_flow_type(product_type_id):
        """[F16 T16.5 修复] F6 P9 兼容: 表 DROP 返 'production', 不崩"""
        try:
            conn = get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT flow_type FROM product_flow_map WHERE product_type_id=%s",
                    (product_type_id,))
                row = cursor.fetchone()
                if not row:
                    return "production"
                if isinstance(row, dict):
                    return row.get('flow_type', 'production')
                return row[0]
            finally:
                conn.close()
        except Exception as e:
            # [F16 T16.5 修复] F6 P9 DROP 业务降级
            if _is_f6p9_dropped_error(e):
                logger.warning(
                    '[F6 P9 DROP] product_flow_map 表不存在 (1146), '
                    'get_flow_type 降级返 "production": product_type_id=%s err=%s',
                    product_type_id, e)
                return "production"
            # 其他 DB 错误 (连接失败等) 同样降级, 保持业务连续
            logger.warning(
                '[F16 T16.5 兼容] get_flow_type 异常, 降级返 "production": %s', e)
            return "production"
