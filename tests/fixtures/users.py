# -*- coding: utf-8 -*-
"""
测试用户数据 - 5个角色

修复 P0-2: 提供 conftest.py:133 所需的 TEST_USERS 数据
"""
import os


# ==================== 测试用户（5 个角色）====================
TEST_USERS = {
    'admin': {
        'name': os.getenv('TEST_ADMIN_NAME', 'admin'),
        'password': os.getenv('TEST_ADMIN_PASSWORD', 'admin123'),
        'operator_id': '1',
        'role': '管理员',
        'permissions': ['*'],  # 全部权限
        'services': ['desktop_web', 'dispatch', 'container'],
    },
    'manager': {
        'name': os.getenv('TEST_MANAGER_NAME', 'manager'),
        'password': os.getenv('TEST_MANAGER_PASSWORD', 'manager123'),
        'operator_id': '2',
        'role': '经理',
        'permissions': ['order:read', 'order:write', 'process:read', 'process:write'],
        'services': ['desktop_web', 'dispatch'],
    },
    'operator': {
        'name': os.getenv('TEST_OPERATOR_NAME', 'operator'),
        'password': os.getenv('TEST_OPERATOR_PASSWORD', 'operator123'),
        'operator_id': '3',
        'role': '操作员',
        'permissions': ['order:read', 'process:read', 'process:write'],
        'services': ['desktop_web', 'mobile'],
    },
    'qc': {
        'name': os.getenv('TEST_QC_NAME', 'qc'),
        'password': os.getenv('TEST_QC_PASSWORD', 'qc123'),
        'operator_id': '4',
        'role': '质检员',
        'permissions': ['quality:read', 'quality:write'],
        'services': ['desktop_web', 'mobile'],
    },
    'warehouse': {
        'name': os.getenv('TEST_WAREHOUSE_NAME', 'warehouse'),
        'password': os.getenv('TEST_WAREHOUSE_PASSWORD', 'warehouse123'),
        'operator_id': '5',
        'role': '仓库管理员',
        'permissions': ['material:read', 'material:write', 'inventory:read'],
        'services': ['desktop_web', 'container'],
    },
}


# ==================== 按 service 分组的用户映射 ====================
# 用于 login_as(service='desktop_web', role='admin') 这种调用
USERS_BY_SERVICE = {}
for role, user in TEST_USERS.items():
    for service in user.get('services', []):
        USERS_BY_SERVICE.setdefault(service, {})[role] = user


def get_user(role: str) -> dict:
    """获取指定角色的用户配置"""
    if role not in TEST_USERS:
        raise ValueError(f"未知角色: {role}, 可选: {list(TEST_USERS.keys())}")
    return TEST_USERS[role]


def get_user_for_service(service: str, role: str = 'admin') -> dict:
    """获取指定服务的指定角色用户"""
    if service not in USERS_BY_SERVICE:
        raise ValueError(f"服务 {service} 没有可用测试用户")
    if role not in USERS_BY_SERVICE[service]:
        raise ValueError(f"服务 {service} 无角色 {role}")
    return USERS_BY_SERVICE[service][role]


__all__ = ['TEST_USERS', 'USERS_BY_SERVICE', 'get_user', 'get_user_for_service']
