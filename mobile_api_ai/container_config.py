# -*- coding: utf-8 -*-
"""
容器中心参数配置模块
统一管理所有业务参数配置
"""

import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'))  # 上级目录
from core.config import DB_PATHS
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from core.config import BASE_DIR, COLORS

logger = logging.getLogger(__name__)

REPAIR_CATEGORIES_FILE = DB_PATHS['repair_categories']
OPERATORS_FILE = DB_PATHS['project_operators']
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))


def _parse_remind_days() -> List[int]:
    """从环境变量解析提醒天数"""
    raw = os.getenv('OUTSOURC_REMIND_DAYS', '3,2,1')
    try:
        return [int(x.strip()) for x in raw.split(',') if x.strip().isdigit()]
    except Exception as e:
        logger.warning(f"解析外协提醒天数失败 (raw={raw}): {e}")
        return [3, 2, 1]


def _parse_remind_times() -> List[str]:
    """从环境变量解析提醒时间"""
    raw = os.getenv('OUTSOURC_REMIND_TIMES', '08:00,13:30')
    try:
        times = [x.strip() for x in raw.split(',') if x.strip()]
        return times if times else ['08:00', '13:30']
    except Exception as e:
        logger.warning(f"解析外协提醒时间失败 (raw={raw}): {e}")
        return ['08:00', '13:30']

@dataclass
class OperatorConfig:
    """操作员配置"""
    id: str
    name: str
    role: str
    code: str = ''
    department: str = ''
    enabled: bool = True
    notify_enabled: bool = True
    can_receive_wechat: bool = False
    can_send_wechat: bool = False
    max_tasks: int = 10
    wechat_userid: str = ''
    phone: str = ''
    created_at: str = ''
    updated_at: str = ''

@dataclass
class ProcessConfig:
    """工序配置"""
    id: str
    name: str
    code: str
    sequence: int = 0
    enabled: bool = True
    quality_check_required: bool = False

@dataclass
class DataTypeConfig:
    """数据类型配置"""
    type: str
    name: str
    icon: str
    color: str
    enabled: bool = True
    auto_distribute: bool = False

@dataclass
class NotificationConfig:
    """通知配置"""
    enabled: bool = True
    notify_on_create: bool = True
    notify_on_distribute: bool = True
    notify_on_complete: bool = True
    notify_on_overdue: bool = True

@dataclass
class RepairCategoryConfig:
    """报修种类配置"""
    id: str
    name: str
    icon: str
    assigned_operator_id: str
    description: str = ''

@dataclass
class OutsourcRemindRule:
    """外协催单规则"""
    days_before: int
    enabled: bool = True

@dataclass
class OutsourcConfig:
    """外协模块配置"""
    enabled: bool = True
    default_operator_id: str = field(default_factory=lambda: os.getenv('OUTSOURC_DEFAULT_OPERATOR', ''))
    remind_days: List[int] = field(default_factory=lambda: _parse_remind_days())
    overdue_remind_times: List[str] = field(default_factory=lambda: _parse_remind_times())

class ContainerConfig:
    """容器中心配置类"""

    def __init__(self):
        self._operators: Dict[str, OperatorConfig] = {}
        self._processes: Dict[str, ProcessConfig] = {}
        self._data_types: Dict[str, DataTypeConfig] = {}
        self._repair_categories: Dict[str, RepairCategoryConfig] = {}
        self._outsourc = OutsourcConfig()
        self._notification = NotificationConfig()
        self._load_defaults()

    def _load_defaults(self):
        """加载默认配置"""
        self._load_operators_from_db()
        self._load_default_data_types()
        self._load_default_repair_categories()
        self._load_default_processes()

    def _load_default_operators(self):
        """操作员列表：不再加载硬编码假数据，由 enterprise_structure 提供"""
        pass  # 真实操作员由企业架构（MySQL enterprise_structure 表）动态加载

    def _load_default_processes(self):
        """初始化工序列表（保持最小集，主软件发布任务后调用 refresh_processes 动态更新）"""
        fallback_processes = [
            ProcessConfig('P01', '编织', 'WEAVING', 1, quality_check_required=True),
            ProcessConfig('P02', '质检', 'QUALITY', 2, quality_check_required=True),
            ProcessConfig('P03', '包装', 'PACKING', 3),
        ]
        for proc in fallback_processes:
            self._processes[proc.id] = proc

    def refresh_processes(self):
        """从容器中心数据库动态刷新工序列表"""
        try:
            from wechat_server import container_center
            if not container_center:
                logger.warning('[ContainerConfig] 容器中心未初始化，跳过工序刷新')
                return
            packages = container_center.storage.get_packages(limit=1000)
            seen = {}
            for pkg in packages:
                raw_c = pkg.get('content', {})
                c = json.loads(raw_c) if isinstance(raw_c, str) else (raw_c or {})
                pn = pkg.get('related_process') or c.get('process_name', '')
                if pn and pn not in seen:
                    seen[pn] = pn
            if seen:
                self._processes.clear()
                from core.config import sort_processes_by_display, get_display_seq_map
                seq_map = get_display_seq_map()
                sorted_pns = sort_processes_by_display(list(seen.keys()), seq_map)
                for i, pn in enumerate(sorted_pns, start=1):
                    pid = f'P{i:02d}'
                    real_seq = seq_map.get(pn, i)
                    self._processes[pid] = ProcessConfig(pid, pn, pn.upper(), real_seq, quality_check_required=(pn == '质量检验'))
                    logger.info(f'[ContainerConfig] 刷新工序: {pn} (display_seq={real_seq})')
        except Exception as e:
            logger.warning(f'[ContainerConfig] 刷新工序失败: {e}')

    def _load_default_data_types(self):
        """加载默认数据类型"""
        default_types = [
            DataTypeConfig('report', '报工', '📝', COLORS['DATA_TYPE_REPORT'], auto_distribute=True),
            DataTypeConfig('quality', '质检', '🔍', COLORS['DATA_TYPE_QUALITY']),
            DataTypeConfig('material', '领料', '📦', COLORS['DATA_TYPE_MATERIAL']),
            DataTypeConfig('approval', '审批', '✅', COLORS['DATA_TYPE_APPROVAL']),
            DataTypeConfig('order', '订单', '📋', COLORS['DATA_TYPE_ORDER']),
            DataTypeConfig('process', '工序', '⚙️', COLORS['DATA_TYPE_PROCESS']),
            DataTypeConfig('repair', '报修', '🔧', COLORS['DATA_TYPE_REPAIR']),
        ]
        for dtype in default_types:
            self._data_types[dtype.type] = dtype

    def _load_default_repair_categories(self):
        """加载报修种类配置（文件持久化 + 默认兜底）"""
        default_categories = [
            {'id': 'R01', 'name': '设备故障', 'icon': '🔧', 'assigned_operator_id': '', 'description': '生产设备故障报修'},
            {'id': 'R02', 'name': '电气维修', 'icon': '⚡', 'assigned_operator_id': '', 'description': '电气系统维修'},
            {'id': 'R03', 'name': '安全风险', 'icon': '🚨', 'assigned_operator_id': '', 'description': '安全隐患上报'},
        ]
        for d in default_categories:
            cat = RepairCategoryConfig(**d)
            self._repair_categories[cat.id] = cat
        if os.path.exists(REPAIR_CATEGORIES_FILE):
            try:
                with open(REPAIR_CATEGORIES_FILE, 'r', encoding='utf-8') as f:
                    custom = json.load(f)
                for d in custom:
                    cat = RepairCategoryConfig(
                        d['id'], d['name'], d.get('icon', '📋'),
                        d['assigned_operator_id'], d.get('description', '')
                    )
                    self._repair_categories[cat.id] = cat
                logger.info(f'[_load_default_repair_categories] 从文件加载 {len(custom)} 个自定义报修种类')
            except Exception as e:
                logger.warning(f'[_load_default_repair_categories] 加载报修种类失败: {e}')

    def get_repair_category(self, category_id: str) -> Optional[RepairCategoryConfig]:
        """获取报修种类"""
        return self._repair_categories.get(category_id)

    def get_all_repair_categories(self) -> List[RepairCategoryConfig]:
        """获取所有报修种类"""
        return list(self._repair_categories.values())

    def _save_repair_categories(self):
        """保存报修种类到文件"""
        try:
            with open(REPAIR_CATEGORIES_FILE, 'w', encoding='utf-8') as f:
                json.dump([
                    asdict(c) for c in self._repair_categories.values()
                ], f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f'[_save_repair_categories] 保存失败: {e}')

    def _save_operators(self):
        """保存操作员到 数据库 + JSON 文件 + MySQL workers 表（三重保障）"""
        try:
            data = {k: asdict(v) for k, v in self._operators.items()}
            # 1. 写 enterprise_structure 表（含 operators 列）
            try:
                from container_center_v5 import ContainerCenter
                cc = ContainerCenter()
                es = cc.storage.get_enterprise_structure()
                if es:
                    cc.storage.save_enterprise_structure({'departments': es.get('departments', []), 'users': es.get('users', []), 'operators': data, 'updated_at': datetime.now().isoformat()})
                cc.storage.disconnect()
            except Exception:
                pass
            # 2. 写 operators.json 文件（桌面版/部署包直接读取）
            try:
                with open(OPERATORS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            # 3. 同步到 MySQL workers 表（手机报工登录使用）
            try:
                from storage.mysql_storage import MySQLStorage
                conn = MySQLStorage.get_connection()
                cur = conn.cursor()
                for op_id, op in data.items():
                    cur.execute('''
                        INSERT INTO workers (enterprise_id, name, role, department, status, sync_at, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, NOW(), NOW(), NOW())
                        ON DUPLICATE KEY UPDATE
                            name=VALUES(name), role=VALUES(role), department=VALUES(department),
                            status=VALUES(status), sync_at=NOW(), updated_at=NOW()
                    ''', (op.get('id', op_id), op.get('name', ''), op.get('role', '操作员'),
                          op.get('department', ''), 'active' if op.get('enabled', True) else 'inactive'))
                conn.commit()
                cur.close()
                conn.close()
                logger.info(f'[_save_operators] MySQL workers 同步完成 ({len(data)} 人)')
            except Exception as e:
                logger.warning(f'[_save_operators] MySQL workers 同步失败: {e}')
        except Exception as e:
            logger.warning(f'[_save_operators] 保存失败: {e}')

    def _next_auto_id(self) -> str:
        """生成下一个系统自增 ID"""
        existing_ids = [int(op.id[2:]) for op in self._operators.values()
                        if op.id.startswith('OP') and op.id[2:].isdigit()]
        next_num = max(existing_ids) + 1 if existing_ids else 1
        return f'OP{next_num:03d}'

    def _get_operator_by_wechat(self, wechat_userid: str):
        """通过企业微信 userid 查找已存在的操作员"""
        for op in self._operators.values():
            if op.wechat_userid == wechat_userid:
                return op
        return None

    def _load_operators_from_db(self):
        """从容器中心 MySQL 加载操作员"""
        try:
            from container_center_v5 import ContainerCenter
            cc = ContainerCenter()
            es = cc.storage.get_enterprise_structure()
            if not es:
                cc.storage.disconnect()
                return False

            operators_str = es.get('operators')
            users_str = es.get('users')
            cc.storage.disconnect()

            # 1. 优先加载 operators 列
            ops_raw = operators_str
            if ops_raw and isinstance(ops_raw, str) and ops_raw not in ('', '[]', '{}'):
                ops_data = json.loads(ops_raw)
                if ops_data:
                    for k, v in ops_data.items():
                        self._operators[k] = OperatorConfig(**v)
                    logger.info(f'[_load_operators_from_db] 从 operators 列加载 {len(ops_data)} 个操作员')

            # 2. 始终从 users 列同步（新增/离职检测）
            users_raw = users_str
            if isinstance(users_raw, str):
                users = json.loads(users_raw)
            else:
                users = users_raw or []

            loaded = 0
            skipped = 0
            resigned = 0
            synced_uids = set()
            if users:
                for u in users:
                    uid = u.get('userid', '')
                    if not uid:
                        continue
                    synced_uids.add(uid)
                    existing = self._get_operator_by_wechat(uid)
                    if existing:
                        # 仅更新部门，不覆盖名称和已有权限
                        # 同步只比对 userid，不对名字进行比对
                        dept = u.get('department_name', '') or u.get('main_department', '')
                        if dept:
                            existing.department = dept
                        skipped += 1
                    else:
                        next_id = self._next_auto_id()
                        self._operators[next_id] = OperatorConfig(
                            id=next_id,
                            name=u.get('name', uid),
                            role='操作员',
                            department=u.get('department_name', '') or u.get('main_department', ''),
                            wechat_userid=uid,
                            enabled=False,
                            can_receive_wechat=False,
                            can_send_wechat=False,
                        )
                        loaded += 1

            logger.info(f'[_load_operators_from_db] 从 users 新增 {loaded} 操作员, 更新 {skipped} 已有')

            # 3. 企业微信中已不存在的操作员 → 设为离职
            for op in self._operators.values():
                if op.wechat_userid and op.wechat_userid not in synced_uids:
                    if op.enabled:
                        op.enabled = False
                        op.updated_at = datetime.now().isoformat()
                        resigned += 1
            if resigned > 0:
                logger.info(f'[_load_operators_from_db] 设为离职: {resigned} 人')

            # 首次从 users 创建后立即保存（含离职变更）
            if loaded > 0 or resigned > 0:
                self._save_operators()
            return True
        except Exception as e:
            logger.warning(f'[_load_operators_from_db] 加载失败: {e}')
            return False

    def _load_operators_from_file(self):
        """从文件加载操作员（JSON 备用）"""
        if not os.path.exists(OPERATORS_FILE):
            return
        try:
            with open(OPERATORS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for k, v in data.items():
                self._operators[k] = OperatorConfig(**v)
            logger.info(f'[_load_operators_from_file] 从文件加载 {len(self._operators)} 个操作员')
        except Exception as e:
            logger.warning(f'[_load_operators_from_file] 加载失败: {e}')

    def add_repair_category(self, name: str, assigned_operator_id: str,
                           description: str = '', icon: str = '📋') -> Optional[RepairCategoryConfig]:
        """新增报修种类"""
        existing = [c for c in self._repair_categories.values() if c.name == name]
        if existing:
            return None
        existing_ids = [int(c.id[1:]) for c in self._repair_categories.values() if c.id.startswith('R')]
        next_num = max(existing_ids) + 1 if existing_ids else 1
        new_id = f'R{next_num:02d}'
        cat = RepairCategoryConfig(new_id, name, icon, assigned_operator_id, description)
        self._repair_categories[new_id] = cat
        self._save_repair_categories()
        logger.info(f'[add_repair_category] 新增种类: {new_id} {name}')
        return cat

    def remove_repair_category(self, category_id: str) -> bool:
        """删除报修种类"""
        if category_id not in self._repair_categories:
            return False
        del self._repair_categories[category_id]
        self._save_repair_categories()
        logger.info(f'[remove_repair_category] 删除种类: {category_id}')
        return True

    def get_outsourc_config(self) -> OutsourcConfig:
        """获取外协配置"""
        return self._outsourc

    def update_outsourc_config(self, **kwargs):
        """更新外协配置"""
        for key, value in kwargs.items():
            if hasattr(self._outsourc, key):
                setattr(self._outsourc, key, value)
        logger.info(f'[update_outsourc_config] 更新: {kwargs}')

    # ==================== 操作员管理 ====================

    def get_operator(self, operator_id: str) -> Optional[OperatorConfig]:
        """获取操作员"""
        return self._operators.get(operator_id)

    def get_all_operators(self) -> List[OperatorConfig]:
        """获取所有操作员"""
        return list(self._operators.values())

    def get_enabled_operators(self) -> List[OperatorConfig]:
        """获取已启用的操作员"""
        return [op for op in self._operators.values() if op.enabled]

    def get_operators_by_department(self, department: str) -> List[OperatorConfig]:
        """获取指定部门的所有操作员"""
        return [op for op in self._operators.values()
                if op.enabled and op.department == department]

    def get_all_departments(self) -> List[str]:
        """获取所有部门列表"""
        departments = set(op.department for op in self._operators.values() if op.department)
        return sorted(list(departments))

    def add_operator(self, operator: OperatorConfig) -> bool:
        """添加操作员（防重复：同 wechat_userid 不可重复任命）"""
        if operator.id in self._operators:
            return False
        # 检查是否已有同企业微信 id 的操作员
        if operator.wechat_userid and self._get_operator_by_wechat(operator.wechat_userid):
            return False
        self._operators[operator.id] = operator
        self._save_operators()
        return True

    def update_operator(self, operator_id: str, **kwargs) -> bool:
        """更新操作员"""
        if operator_id not in self._operators:
            return False
        op = self._operators[operator_id]
        for key, value in kwargs.items():
            if hasattr(op, key):
                setattr(op, key, value)
        self._save_operators()
        return True

    def remove_operator(self, operator_id: str) -> bool:
        """移除操作员（同步清理 MySQL + JSON 文件）"""
        if operator_id not in self._operators:
            return False
        op = self._operators[operator_id]
        wechat_uid = op.wechat_userid

        # 1. 从内存移除
        del self._operators[operator_id]
        # 2. 保存（更新 SQLite + JSON 文件）
        self._save_operators()

        # 3. 清理 MySQL steel_belt 库
        if wechat_uid:
            try:
                from db.steelbelt_pool import cursor as sb_cursor
                conn, cur = sb_cursor()
                cur = conn.cursor()
                cur.execute("DELETE FROM operators WHERE wechat_userid = %s", (wechat_uid,))
                op_del = cur.rowcount
                # 标记 enterprise_personnel 为非操作员
                cur.execute("UPDATE enterprise_personnel SET is_operator = 0 WHERE userid = %s", (wechat_uid,))
                ep_upd = cur.rowcount
                conn.commit()
                logger.info(f'[_remove_operator] MySQL 清理: operators删{op_del}行, personnel标记{ep_upd}行')
                conn.close()
            except Exception as e:
                logger.warning(f'[_remove_operator] MySQL 清理失败: {e}')
        return True

    # ==================== 工序管理 ====================

    def get_process(self, process_id: str) -> Optional[ProcessConfig]:
        """获取工序"""
        return self._processes.get(process_id)

    def get_all_processes(self) -> List[ProcessConfig]:
        """获取所有工序"""
        return sorted(self._processes.values(), key=lambda p: p.sequence)

    def get_enabled_processes(self) -> List[ProcessConfig]:
        """获取已启用的工序"""
        return [p for p in self._processes.values() if p.enabled]

    def get_process_by_name(self, name: str) -> Optional[ProcessConfig]:
        """根据名称获取工序"""
        for p in self._processes.values():
            if p.name == name:
                return p
        return None

    def add_process(self, process: ProcessConfig) -> bool:
        """添加工序"""
        if process.id in self._processes:
            return False
        self._processes[process.id] = process
        return True

    def update_process(self, process_id: str, **kwargs) -> bool:
        """更新工序"""
        if process_id not in self._processes:
            return False
        proc = self._processes[process_id]
        for key, value in kwargs.items():
            if hasattr(proc, key):
                setattr(proc, key, value)
        return True

    # ==================== 数据类型管理 ====================

    def get_data_type(self, type_id: str) -> Optional[DataTypeConfig]:
        """获取数据类型"""
        return self._data_types.get(type_id)

    def get_all_data_types(self) -> List[DataTypeConfig]:
        """获取所有数据类型"""
        return list(self._data_types.values())

    def get_enabled_data_types(self) -> List[DataTypeConfig]:
        """获取已启用的数据类型"""
        return [dt for dt in self._data_types.values() if dt.enabled]

    # ==================== 通知配置 ====================

    def get_notification_config(self) -> NotificationConfig:
        """获取通知配置"""
        return self._notification

    def update_notification_config(self, **kwargs) -> bool:
        """更新通知配置"""
        for key, value in kwargs.items():
            if hasattr(self._notification, key):
                setattr(self._notification, key, value)
        return True

    # ==================== 工具方法 ====================

    def to_dict(self) -> Dict:
        """导出配置为字典"""
        return {
            'operators': {
                k: {
                    'id': v.id,
                    'name': v.name,
                    'role': v.role,
                    'department': v.department,
                    'enabled': v.enabled
                }
                for k, v in self._operators.items()
            },
            'processes': {
                k: {
                    'id': v.id,
                    'name': v.name,
                    'code': v.code,
                    'sequence': v.sequence,
                    'enabled': v.enabled
                }
                for k, v in self._processes.items()
            },
            'data_types': {
                k: {
                    'type': v.type,
                    'name': v.name,
                    'icon': v.icon,
                    'color': v.color,
                    'enabled': v.enabled
                }
                for k, v in self._data_types.items()
            }
        }

    def load_from_dict(self, config_dict: Dict):
        """从字典加载配置"""
        if 'operators' in config_dict:
            for k, v in config_dict['operators'].items():
                self._operators[k] = OperatorConfig(**v)

        if 'processes' in config_dict:
            for k, v in config_dict['processes'].items():
                self._processes[k] = ProcessConfig(**v)

        if 'data_types' in config_dict:
            for k, v in config_dict['data_types'].items():
                self._data_types[k] = DataTypeConfig(**v)


# 全局配置实例
container_config = ContainerConfig()
