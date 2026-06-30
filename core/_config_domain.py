import os

# R12 register_process bug fix (R13 任务 18):
# 工序注册时同步刷新跨模块 SSOT _PROCESS_CODE_TO_TYPE
#
# [v3.8.1] 锁定 mobile_api_ai.utils.data_type_contract 路径:
#   - 项目根 utils/data_type_contract.py (10956 bytes, 2026-06-20 新版) 缺失 _PROCESS_CODE_TO_TYPE
#   - mobile_api_ai/utils/data_type_contract.py (14983 bytes) 才是含该符号的版本
#   - 项目根 utils/__init__.py 没有反向 __path__ 扩展, 裸导入 "from utils.X import"
#     永远找到项目根版本,导致 14 个测试文件 ImportError
#   - 详见 docs/v3.8.1/TEST_ERRORS_ANALYSIS.md
from mobile_api_ai.utils.data_type_contract import _PROCESS_CODE_TO_TYPE

# ========== 材质配置 ==========
MATERIALS = [
    "304不锈钢",
    "316不锈钢",
    "316L不锈钢",
    "310S不锈钢",
    "201不锈钢",
    "碳钢镀锌",
    "铝合金",
    "铜合金",
    "钛合金"
]

MATERIAL_DENSITIES = {
    "304不锈钢": 7930,
    "316不锈钢": 7980,
    "316L不锈钢": 7980,
    "310S不锈钢": 7980,
    "201不锈钢": 7930,
    "碳钢镀锌": 7850,
    "铝合金": 2700,
    "铜合金": 8500,
    "钛合金": 4510,
}

# ========== 材质参数预设 ==========
PRESET_MAT_PARAMS = [
    {"key": "曲轴材质", "label": "曲轴材质"},
    {"key": "网丝材质", "label": "网丝材质"},
    {"key": "穿杆材质", "label": "穿杆材质"},
    {"key": "链条材质", "label": "链条材质"},
    {"key": "主齿轮材质", "label": "主齿轮材质"},
    {"key": "挡板材质", "label": "挡板材质"},
    {"key": "辅助轮材质", "label": "辅助轮材质"},
    {"key": "加强筋材质", "label": "加强筋材质"},
    {"key": "链板材质", "label": "链板材质"},
]

# ========== 尺寸参数预设 ==========
PRESET_DIM_PARAMS = [
    {"key": "总宽", "label": "总宽", "unit": "mm"},
    {"key": "净宽", "label": "净宽", "unit": "mm"},
    {"key": "网带宽度", "label": "网带宽度", "unit": "mm"},
    {"key": "钢丝直径", "label": "钢丝直径", "unit": "mm"},
    {"key": "加强链片厚度", "label": "加强链片厚度", "unit": "mm"},
    {"key": "链条厚度", "label": "链条厚度", "unit": "mm"},
    {"key": "链板板厚", "label": "链板板厚", "unit": "mm"},
    {"key": "链板网孔直径", "label": "链板网孔直径", "unit": "mm"},
    {"key": "螺距", "label": "螺距", "unit": "mm"},
    {"key": "曲轴直径", "label": "曲轴直径", "unit": "mm"},
    {"key": "穿杆直径", "label": "穿杆直径", "unit": "mm"},
    {"key": "主轴直径", "label": "主轴直径", "unit": "mm"},
    {"key": "主齿轮直径", "label": "主齿轮直径", "unit": "mm"},
    {"key": "辅助轮直径", "label": "辅助轮直径", "unit": "mm"},
    {"key": "加强筋直径", "label": "加强筋直径", "unit": "mm"},
    {"key": "网带节距", "label": "网带节距", "unit": "mm"},
    {"key": "加强筋间距", "label": "加强筋间距", "unit": "mm"},
    {"key": "链条距", "label": "链条距", "unit": "mm"},
    {"key": "穿杆距", "label": "穿杆距", "unit": "mm"},
    {"key": "中心距", "label": "中心距", "unit": "mm"},
    {"key": "加强垫片布置", "label": "加强垫片布置", "unit": "mm"},
    {"key": "扣间隙", "label": "扣间隙", "unit": "mm"},
    {"key": "网带排数", "label": "网带排数", "unit": "条"},
    {"key": "加强筋数量", "label": "加强筋数量", "unit": "条"},
    {"key": "主齿轮齿数", "label": "主齿轮齿数", "unit": "齿"},
    {"key": "主齿轮数量", "label": "主齿轮数量", "unit": "套"},
    {"key": "辅助齿轮齿数", "label": "辅助齿轮齿数", "unit": "齿"},
    {"key": "辅助轮数量", "label": "辅助轮数量", "unit": "个"},
    {"key": "单段长度", "label": "单段长度", "unit": "m"},
    {"key": "网带段数", "label": "网带段数", "unit": "段"},
    {"key": "挡板高度", "label": "挡板高度", "unit": "mm"},
    {"key": "挡板厚度", "label": "挡板厚度", "unit": "mm"},
    {"key": "链板网孔规格", "label": "链板网孔规格", "unit": "mm"},
]

# ========== 产品类型 ==========
PRODUCT_TYPES = [
    "乙字形网带",
    "人字形网带",
    "平板型网带",
    "勾子链网带",
    "弹簧网",
    "眼镜网带",
    "螺旋网带",
    "链板式网带",
    "链网",
    "马蹄形网带",
    "冷冻网带",
    "冷冻螺旋网",
    "其他"
]

# ========== 表面处理选项 ==========
SURFACE_TREATMENTS = [
    "光亮退火",
    "抛光",
    "钝化",
    "喷砂",
    "无处理"
]

# ========== 订单状态（带颜色） ==========
ORDER_STATUS = {
    "待确认": "#9E9E9E",
    "待排产": "#2196F3",
    "待发布": "#00BCD4",
    "已发布": "#0097A7",
    "已排产": "#03A9F4",
    "生产中": "#FF9800",
    "质检中": "#FF5722",
    "已完成": "#4CAF50",
    "待发货": "#9C27B0",
    "已发货": "#9C27B0",
    "已取消": "#F44336"
}

# ========== 生产工序（17个工序） ==========
PROCESSES = [
    "原材料准备",
    "焊接眼镜网",
    "激光切板",
    "链板冲压孔",
    "链板冲压成型",
    "编制左旋",
    "编制右旋",
    "穿曲轴",
    "输送带组装穿杆",
    "安装链条",
    "安装裙边",
    "整形校直",
    "焊接输送带",
    "表面处理",
    "质量检验",
    "包装入库",
    "测试",  # R11 新增: P_CS 测试工序(特殊编码,不占 P01~P16 位)
]

PROCESS_CODES = {
    "原材料准备": "P01",
    "焊接眼镜网": "P02",
    "激光切板": "P03",
    "链板冲压孔": "P04",
    "链板冲压成型": "P05",
    "编制左旋": "P06",
    "编制右旋": "P07",
    "穿曲轴": "P08",
    "输送带组装穿杆": "P09",
    "安装链条": "P10",
    "安装裙边": "P11",
    "整形校直": "P12",
    "焊接输送带": "P13",
    "表面处理": "P14",
    "质量检验": "P15",
    "包装入库": "P16",
    "备料": "M01",
    "质检": "Q01",
    "外协": "X01",
    "测试": "P_CS",  # R11: 特殊编码,用于测试工序(不参与 P17+ 自增序列)
}


def get_process_code(process_name: str) -> str:
    """获取工序编码。预定义工序用P01-P16，自定义工序用注册编码，其他用PX-hash4动态生成"""
    if not process_name:
        return ''
    import hashlib
    name = process_name.strip()
    code = PROCESS_CODES.get(name) or _custom_process_codes.get(name)
    if code:
        return code
    return 'PX' + hashlib.md5(name.encode()).hexdigest()[:4].upper()


# ========== 后期工序注册系统 ==========

# 自定义工序存储（运行时动态扩展）
_custom_processes: list = []
_custom_process_codes: dict = {}
_custom_process_seqs: dict = {}  # name → display_order
_next_custom_seq = 17  # P01-P16 已占用
_next_display_seq = 17  # 显示序号从 17 开始

# display_seq 缓存（避免频繁查 MySQL）
_display_seq_cache: dict = {}
_display_seq_cache_loaded = False


def register_process(
    process_name: str,
    process_code: str = '',
    display_seq: int = None,
    category: str = 'process'
) -> str:
    """
    注册一个新的工序（含5层防御 + 持久化）。
    - process_code: 编码，不提供则自动分配 P17/P18/...
    - display_seq:  显示排序，不提供则自动递增（排在标准工序后面）
    - category:     类型，默认 'process'，可选 'material'/'quality'/'outsource'/'auxiliary'
    - 如果名称已存在（标准或自定义），返回已有编码
    返回：最终使用的 process_code

    5层防御：
    1. T5-1 参数清洗：strip() + 小写归一化
    2. T5-2 幂等保证：DB INSERT 用 try/except DuplicateKeyError
    3. T5-3 格式校验：编码格式正则 ^[PMQXpmqx][0-9A-Za-z]{1,8}$
    4. T5-4 一致性检查：name 已存在返回已有 code；code 被占用抛异常
    5. T5-5 持久化降级：DB 失败静默降级
    """
    global _next_custom_seq, _next_display_seq

    if not process_name or not process_name.strip():
        raise ValueError('process_name 不能为空')

    # T5-1 参数清洗：仅 strip (B0 修: 去掉 .lower() 归一化, 与下游查询不匹配)
    name = process_name.strip()

    # T5-4 第一层：检查 name 是否已存在（标准工序优先，保留大小写精确匹配）
    existing = PROCESS_CODES.get(name) or _custom_process_codes.get(name)
    if existing:
        return existing

    # 分配编码
    if process_code and process_code.strip():
        code = process_code.strip()
    else:
        code = f'P{_next_custom_seq:02d}'
        _next_custom_seq += 1

    # T5-3 格式校验：编码格式正则 ^[PMQXpmqx][0-9A-Za-z]{1,8}$
    import re
    if not re.match(r'^[PMQXpmqx][0-9A-Za-z]{1,8}$', code):
        raise ValueError('工序编码格式不合法，需符合 P/M/Q/X 开头 + 字母数字，长度 2-9 位')

    # T5-4 第二层：检查 code 是否已被其他 name 占用
    reverse_map = {v: k for k, v in _custom_process_codes.items()}
    if code in reverse_map and reverse_map[code] != name:
        raise ValueError(f'该编码 {code} 已被其他工序占用')

    # 分配显示序号
    if display_seq is not None:
        seq = display_seq
    else:
        seq = _next_display_seq
        _next_display_seq += 1

    # B0 修: 写主 SSOT PROCESS_CODES (R12 原始 bug #1, register_process 不更新主 dict)
    PROCESS_CODES[name] = code

    # 写 _custom_* 内存副本 (始终执行)
    _custom_processes.append(name)
    _custom_process_codes[name] = code
    _custom_process_seqs[name] = seq

    # B0 修: 刷新跨模块 SSOT _PROCESS_CODE_TO_TYPE (R12 原始 bug #2)
    # 工序类型映射: 编码首字母决定 → process_report (P) / material_request (M)
    # / quality_task (Q) / outsource_task (X)
    type_map = {'P': 'process_report', 'M': 'material_request',
                'Q': 'quality_task', 'X': 'outsource_task'}
    _PROCESS_CODE_TO_TYPE[code] = type_map.get(code[0], category)

    # T5-2 + T5-5: DB 持久化（幂等 + 静默降级）
    _persist_process_to_db(name, code, category)

    return code


def _persist_process_to_db(name: str, code: str, category: str) -> None:
    """
    将自定义工序持久化到 process_code_registry 表。
    表不存在时静默降级，不抛异常。
    幂等：DuplicateKeyError → 忽略
    """
    import logging as _log
    import pymysql
    _logger = _log.getLogger(__name__)
    try:
        conn = pymysql.connect(
            host='localhost', user='root',
            password=__import__('os').getenv('MYSQL_PASSWORD', ''),
            database='steel_belt', charset='utf8mb4',
            connect_timeout=5)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO process_code_registry (name, process_code, category) "
                "VALUES (%s, %s, %s)",
                (name, code, category))
            conn.commit()
            cursor.close()
        except Exception as ie:
            conn.close()
            raise ie
    except Exception as e:
        _logger.debug('[register_process] DB持久化降级（仅写内存）: %s', e)


def unregister_process(process_name: str) -> bool:
    """
    注销一个自定义工序（同步删内存+DB）。
    标准工序（P01-P16）不允许注销。
    """
    if not process_name:
        return False
    name = process_name.strip()

    # B0 v2 修: 不能只看 PROCESS_CODES 判"标准", 还要看 _custom_process_codes
    # (register_process B0 修后, 自定义工序也在 PROCESS_CODES 里)
    if name in _custom_process_codes:
        is_custom = True
        code_to_remove = _custom_process_codes[name]
    elif name in PROCESS_CODES:
        # 是标准工序 (登记在 PROCESS_CODES 但不在 _custom_process_codes 里)
        return False
    else:
        return False

    _custom_processes.remove(name)
    del _custom_process_codes[name]
    _custom_process_seqs.pop(name, None)

    # B0 v2 修: 同步删主 SSOT PROCESS_CODES + 跨模块 _PROCESS_CODE_TO_TYPE
    PROCESS_CODES.pop(name, None)
    _PROCESS_CODE_TO_TYPE.pop(code_to_remove, None)

    # 同步删除 DB（静默降级）
    _unpersist_process_from_db(name)

    return True


def _unpersist_process_from_db(name: str) -> None:
    """
    从 process_code_registry 表删除记录。
    表不存在时静默降级，不抛异常。
    """
    import logging as _log
    import pymysql
    _logger = _log.getLogger(__name__)
    try:
        conn = pymysql.connect(
            host='localhost', user='root',
            password=__import__('os').getenv('MYSQL_PASSWORD', ''),
            database='steel_belt', charset='utf8mb4',
            connect_timeout=5)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM process_code_registry WHERE name=%s",
                (name,))
            conn.commit()
            cursor.close()
        except Exception as ie:
            conn.close()
            raise ie
    except Exception as e:
        _logger.debug('[unregister_process] DB删除降级: %s', e)


def _get_standard_seq(name: str) -> int:
    """获取标准工序的默认序号 (1-16)"""
    # R11: "测试" 是特殊工序(P_CS),非标准报工工序,排到最后
    if name == "测试":
        return 999
    idx = PROCESSES.index(name) + 1 if name in PROCESSES else 999
    return idx


def get_process_seq(name: str) -> int:
    """获取单个工序的显示序号。优先用显式指定值，否则用标准工序的默认位置"""
    n = name.strip() if name else ''
    # 显式指定的序号（自定义工序 or 被移动过的标准工序）
    if n in _custom_process_seqs:
        return _custom_process_seqs[n]
    if n in PROCESSES:
        return _get_standard_seq(n)
    return 999


def get_all_processes(sort: bool = True) -> list:
    """
    获取所有已注册的工序列表。
    sort=True: 按显示序号排列
    sort=False: 标准在前，自定义在后
    """
    if not sort:
        return list(PROCESSES) + list(_custom_processes)

    all_names = set(PROCESSES) | set(_custom_processes)
    return sorted(all_names, key=lambda n: (get_process_seq(n), n))


def get_all_process_codes() -> dict:
    """获取所有工序编码（标准 + 自定义）"""
    result = dict(PROCESS_CODES)
    result.update(_custom_process_codes)
    return result


def is_registered(process_name: str) -> bool:
    """检查工序是否已注册"""
    name = process_name.strip() if process_name else ''
    return name in PROCESS_CODES or name in _custom_process_codes


def _ensure_seq(name: str):
    """确保工序在 _custom_process_seqs 中有条目（用于首次移动）"""
    if name not in _custom_process_seqs:
        _custom_process_seqs[name] = get_process_seq(name)


def reorder_processes(order: list) -> bool:
    """
    按传入的名称列表重新排序所有工序。
    order 是 get_all_processes() 的子集排列。
    不在 order 中的工序排在末尾。
    """
    seq = 1
    for name in order:
        n = name.strip()
        if is_registered(n):
            _custom_process_seqs[n] = seq
            seq += 1

    # 未在 order 中的工序排到最后
    for name in get_all_processes(sort=False):
        if name.strip() not in [x.strip() for x in order]:
            _custom_process_seqs[name] = 999

    return True


def move_process(process_name: str, direction: str = 'up') -> int:
    """
    移动工序在显示列表中的位置（标准工序也支持）。
    direction: 'up'/'down'/'top'/'bottom'
    返回新的序号。
    """
    name = process_name.strip()

    if not is_registered(name):
        return -1

    # 确保有显式序号
    _ensure_seq(name)

    ordered = get_all_processes(sort=True)

    if name not in ordered or len(ordered) < 2:
        return get_process_seq(name)

    old_idx = ordered.index(name)
    new_idx = old_idx

    if direction == 'up' and old_idx > 0:
        new_idx = old_idx - 1
    elif direction == 'down' and old_idx < len(ordered) - 1:
        new_idx = old_idx + 1
    elif direction == 'top':
        new_idx = 0
    elif direction == 'bottom':
        new_idx = len(ordered) - 1

    if new_idx == old_idx:
        return get_process_seq(name)

    # 交换序号：双方都获得显式序号
    swap_name = ordered[new_idx]
    _ensure_seq(name)
    if swap_name not in _custom_process_seqs:
        # 标准工序首次被移动波及 → 也创建显式序号
        if swap_name in PROCESSES:
            _custom_process_seqs[swap_name] = _get_standard_seq(swap_name)
        else:
            _custom_process_seqs[swap_name] = get_process_seq(swap_name)

    old_seq = _custom_process_seqs[name]
    _custom_process_seqs[name] = _custom_process_seqs[swap_name]
    _custom_process_seqs[swap_name] = old_seq


def load_custom_processes_from_db(mysql_conn=None):
    """
    [F16 T16.6 修复] process_names 表已 F6 P9 2026-06-10 DROP
        (跨库历史表清理, 详见 .workbuddy/memory/MEMORY.md L20)
        原功能: 从 MySQL process_names 加载自定义工序到内存
        修复: 表 DROP 后返 0 + WARNING, 内存数据由 _custom_process_codes 维护
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.warning('[F16 T16.6] process_names 表已 F6 P9 DROP, load_custom_processes_from_db 返 0 '
                   '(内存 PROCESS_CODES 仍可用, 自定义工序走 register_process() 运行时注册)')
    return 0

    # 保留原逻辑 (F6 P9 之前可达) — 已不可达, 仅留作历史参考
    if mysql_conn is None:
        try:
            from core.db import get_direct_connection
            import os as _os
            mysql_conn = get_direct_connection(
                host=_os.getenv('MYSQL_HOST', 'localhost'),
                port=int(_os.getenv('MYSQL_PORT', '3306')),
                user=_os.getenv('MYSQL_USER', 'root'),
                password=_os.getenv('MYSQL_PASSWORD', ''),
                database=_os.getenv('MYSQL_DATABASE', 'steel_belt'),
                charset='utf8mb4'
            )
        except Exception:
            return 0

    try:
        cur = mysql_conn.cursor()
        cur.execute("SELECT process_name, process_code, display_seq, is_active FROM process_names WHERE is_active=1 ORDER BY display_seq")
        loaded = 0
        for row in cur.fetchall():
            name = row['process_name']
            code = row['process_code']
            seq = row.get('display_seq')
            if name not in PROCESS_CODES and name not in _custom_process_codes:
                register_process(name, code)
            if seq is not None:
                _custom_process_seqs[name] = seq
                loaded += 1
        return loaded
    finally:
        if mysql_conn:
            mysql_conn.close()


def save_display_order_to_db(mysql_conn=None) -> int:
    """
    [F16 T16.6 修复] process_names 表已 F6 P9 2026-06-10 DROP
        (跨库历史表清理, 详见 .workbuddy/memory/MEMORY.md L20)
        原功能: 将内存 display_seq 写回 MySQL process_names
        修复: 表 DROP 后返 0 + WARNING, 内存数据 (_custom_process_seqs) 仍可用
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.warning('[F16 T16.6] process_names 表已 F6 P9 DROP, save_display_order_to_db 返 0 '
                   '(内存 _custom_process_seqs 仍可用, display_seq 重启不持久化)')
    return 0

    # 保留原逻辑 (F6 P9 之前可达) — 已不可达, 仅留作历史参考
    if mysql_conn is None:
        try:
            import pymysql
            import os as _os
            mysql_conn = pymysql.connect(
                host=_os.getenv('MYSQL_HOST', 'localhost'),
                port=int(_os.getenv('MYSQL_PORT', '3306')),
                user=_os.getenv('MYSQL_USER', 'root'),
                password=_os.getenv('MYSQL_PASSWORD', ''),
                database=_os.getenv('MYSQL_DATABASE', 'steel_belt'),
                charset='utf8mb4',
                autocommit=True
            )
        except Exception:
            return 0

    try:
        cur = mysql_conn.cursor()
        updated = 0
        for name in get_all_processes(sort=False):
            seq = get_process_seq(name)
            cur.execute(
                "UPDATE process_names SET display_seq=%s WHERE process_name=%s",
                (seq, name)
            )
            if cur.rowcount == 0:
                # 自定义工序可能不在 process_names 表中 → 插入
                code = get_process_code(name)
                cur.execute(
                    "INSERT INTO process_names (process_name, process_code, process_seq, display_seq)"
                    " VALUES (%s,%s,%s,%s) ON DUPLICATE KEY UPDATE display_seq=%s",
                    (name, code, seq, seq, seq)
                )
            updated += max(cur.rowcount, 1)
        return updated
    finally:
        if mysql_conn:
            mysql_conn.close()


def reset_custom_processes():
    """重置所有自定义工序（主要用于测试）。
    B0 v3 修: 同步清理 SSOT PROCESS_CODES 和跨模块 _PROCESS_CODE_TO_TYPE
    中由 register_process 注入的自定义 key, 避免测试间状态污染。
    """
    global _next_custom_seq, _next_display_seq, _display_seq_cache, _display_seq_cache_loaded
    _custom_processes.clear()
    # 同步清理 SSOT (迭代时拷贝, 避免 RuntimeError)
    for name, code in list(_custom_process_codes.items()):
        PROCESS_CODES.pop(name, None)
        _PROCESS_CODE_TO_TYPE.pop(code, None)
    _custom_process_codes.clear()
    _custom_process_seqs.clear()
    _next_custom_seq = 17
    _next_display_seq = 17
    _display_seq_cache = {}
    _display_seq_cache_loaded = False


def get_display_seq_map(mysql_conn=None, force_refresh: bool = False) -> dict:
    """
    [F16 T16.6 修复] process_names 表已 F6 P9 2026-06-10 DROP
        (跨库历史表清理, 详见 .workbuddy/memory/MEMORY.md L20)
        原功能: 从 MySQL process_names 读取所有工序的 display_seq 映射
        修复: 表 DROP 后返 {} + WARNING, 内存 _custom_process_seqs 兜底
    """
    global _display_seq_cache, _display_seq_cache_loaded

    # 缓存命中 (force_refresh=False) → 直接返
    if _display_seq_cache_loaded and not force_refresh:
        return _display_seq_cache

    # [F16 T16.6 修复] F6 P9 DROP 后, MySQL 持久化已废弃, 返空 dict + WARNING
    # 内存 _custom_process_seqs 保留作 fallback (get_process_seq() 仍可查)
    import logging
    logger = logging.getLogger(__name__)
    logger.warning('[F16 T16.6] process_names 表已 F6 P9 DROP, get_display_seq_map 返空 dict '
                   '(内存 _custom_process_seqs 兜底, display_seq 重启不持久化)')
    _display_seq_cache = {}
    _display_seq_cache_loaded = True  # 标记已加载 (避免反复重试)
    return _display_seq_cache

    # 保留原逻辑 (F6 P9 之前可达) — 已不可达, 仅留作历史参考
    if mysql_conn is None:
        try:
            import pymysql
            import os as _os
            mysql_conn = pymysql.connect(
                host=_os.getenv('MYSQL_HOST', 'localhost'),
                port=int(_os.getenv('MYSQL_PORT', '3306')),
                user=_os.getenv('MYSQL_USER', 'root'),
                password=_os.getenv('MYSQL_PASSWORD', ''),
                database=_os.getenv('MYSQL_DATABASE', 'steel_belt'),
                charset='utf8mb4'
            )
        except Exception:
            return {}

    try:
        cur = mysql_conn.cursor()
        cur.execute("SELECT process_name, COALESCE(display_seq, 99) FROM process_names WHERE is_active=1")
        _display_seq_cache = {row[0]: row[1] for row in cur.fetchall()}
        _display_seq_cache_loaded = True
        return _display_seq_cache
    except Exception:
        return _display_seq_cache if _display_seq_cache else {}
    finally:
        if mysql_conn:
            mysql_conn.close()


def invalidate_display_seq_cache():
    """使 display_seq 缓存失效（工序变更后调用）"""
    global _display_seq_cache, _display_seq_cache_loaded
    _display_seq_cache = {}
    _display_seq_cache_loaded = False


def sort_processes_by_display(process_names: list, seq_map: dict = None) -> list:
    """
    按 display_seq 对工序名列表排序。
    seq_map 可从 get_display_seq_map() 获取（有缓存），传 None 自动获取。
    """
    if seq_map is None:
        seq_map = get_display_seq_map()
    if not seq_map:
        return sorted(process_names)
    return sorted(process_names, key=lambda n: seq_map.get(n, 99))
INSPECTION_TYPES = ["首检", "巡检", "终检"]
INSPECTION_RESULTS = ["合格", "不合格", "待复检"]

INSPECTION_ITEMS_BY_CATEGORY = {
    "原材料准备": {
        "材质核对": ["材质报告核查", "规格核对", "数量核对"],
        "外观检查": ["表面质量", "锈蚀检查", "变形检查"]
    },
    "焊接眼镜网": {
        "焊点检查": ["焊点质量", "焊接强度"],
        "外观检查": ["网面平整度", "形状核对"]
    },
    "激光切板": {
        "尺寸检查": ["切割尺寸", "切口质量"],
        "外观检查": ["毛刺检查", "平面度"]
    },
    "链板冲压孔": {
        "尺寸检查": ["孔径测量", "孔距测量"],
        "外观检查": ["冲压质量", "毛刺检查"]
    },
    "链板冲压成型": {
        "尺寸检查": ["成型尺寸", "弧度检查"],
        "外观检查": ["表面质量", "裂纹检查"]
    },
    "编制左旋": {
        "编织检查": ["编织密度", "纬线张力", "经线张力"],
        "外观检查": ["网孔尺寸", "平整度"]
    },
    "编制右旋": {
        "编织检查": ["编织密度", "纬线张力", "经线张力"],
        "外观检查": ["网孔尺寸", "平整度"]
    },
    "穿曲轴": {
        "装配检查": ["配合度", "间隙测量"],
        "外观检查": ["位置核对", "牢固度"]
    },
    "输送带组装穿杆": {
        "装配检查": ["穿杆位置", "间距测量"],
        "外观检查": ["整齐度", "牢固度"]
    },
    "安装链条": {
        "装配检查": ["链条张紧度", "平行度"],
        "外观检查": ["运行检查", "噪音检查"]
    },
    "安装裙边": {
        "装配检查": ["裙边位置", "固定检查"],
        "外观检查": ["贴合度", "平整度"]
    },
    "整形校直": {
        "尺寸检查": ["校直度", "直线度"],
        "外观检查": ["表面质量", "变形检查"]
    },
    "焊接输送带": {
        "焊点检查": ["焊接质量", "牢固度"],
        "外观检查": ["接头平整", "网面变形"]
    },
    "表面处理": {
        "处理检查": ["镀层厚度", "涂层均匀"],
        "外观检查": ["表面光洁度", "颜色一致性"]
    },
    "质量检验": {
        "全面检查": ["尺寸核对", "外观检查", "性能测试"],
        "报告输出": ["检验记录", "合格判定"]
    },
    "包装入库": {
        "包装检查": ["包装完整性", "标识清晰"],
        "入库核对": ["数量核对", "存放位置"]
    }
}

# ========== 单位选项 ==========
UNITS = ["米", "平方米", "卷", "条", "个", "套", "批"]

# ========== 业务阈值配置 ==========
class BusinessConfig:
    """业务阈值配置（从环境变量读取）"""
    STOCK_WARNING_THRESHOLD = int(os.getenv('STOCK_WARNING_THRESHOLD', '50'))
    STOCK_CRITICAL_THRESHOLD = int(os.getenv('STOCK_CRITICAL_THRESHOLD', '10'))
    ORDER_EXPIRY_DAYS = int(os.getenv('ORDER_EXPIRY_DAYS', '30'))
    ORDER_ARCHIVE_DAYS = int(os.getenv('ORDER_ARCHIVE_DAYS', '365'))
    DEFAULT_PAGE_SIZE = int(os.getenv('DEFAULT_PAGE_SIZE', '50'))
    MAX_PAGE_SIZE = int(os.getenv('MAX_PAGE_SIZE', '200'))
    QUERY_TIMEOUT = int(os.getenv('QUERY_TIMEOUT', '60'))
    COMMAND_TIMEOUT = int(os.getenv('COMMAND_TIMEOUT', '300'))
    MOBILE_API_URL = os.getenv('MOBILE_API_URL', '')
