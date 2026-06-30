#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MySQL MCP 准备脚本（一键建账号 + 安全加固）

功能：
  1. 建只读账号 trae_ro@localhost（AI 日常查询用）
  2. 建读写账号 trae_rw@localhost（数据迁移/修复用）
  3. 撤销 root@% 远程访问权限
  4. 验证新账号可登录
  5. 失败时自动回滚

用法：
  # 安装（建账号 + 撤销远程 root）
  python setup_mysql_mcp.py install

  # 仅验证（不修改任何东西）
  python setup_mysql_mcp.py verify

  # 卸载（删账号 + 恢复远程 root）
  python setup_mysql_mcp.py uninstall

  # 仅撤销远程 root
  python setup_mysql_mcp.py revoke-remote

作者：TRAE + AI 助手
创建：2026-06-20
"""
import sys
import os
import argparse
import getpass
import pymysql

# ============================================================
# 配置区
# ============================================================
ADMIN_USER = 'root'
ADMIN_HOST = '127.0.0.1'
ADMIN_PORT = 3306

# 目标数据库
TARGET_DBS = ['steel_belt', 'container_center', 'inventory_db', 'steel_belt_test']

# 新账号
RO_USER = 'trae_ro'
RO_HOST = 'localhost'
RO_PASS = 'Trae_RO_2026!ReadOnly'  # 16+ 字符，含大小写数字符号

RW_USER = 'trae_rw'
RW_HOST = 'localhost'
RW_PASS = 'Trae_RW_2026!ReadWrite'  # 16+ 字符，含大小写数字符号

# 远程 root 检测
REMOTE_ROOT_USER = 'root'
REMOTE_ROOT_HOST = '%'


# ============================================================
# 工具函数
# ============================================================
def get_admin_conn(admin_pass: str):
    """用 root 账号连 MySQL"""
    return pymysql.connect(
        host=ADMIN_HOST,
        port=ADMIN_PORT,
        user=ADMIN_USER,
        password=admin_pass,
        charset='utf8mb4',
        autocommit=False,
    )


def user_exists(cur, user: str, host: str) -> bool:
    """检查用户是否已存在"""
    cur.execute("SELECT 1 FROM mysql.user WHERE user = %s AND host = %s", (user, host))
    return cur.fetchone() is not None


def exec_sql(cur, sql: str, params=None):
    """执行 SQL，参数化（无参数时不传，避免 pymysql 把字面量 % 当占位符）"""
    if params:
        cur.execute(sql, params)
    else:
        cur.execute(sql)


def banner(text: str):
    """打印分隔线"""
    print('\n' + '=' * 70)
    print(f'  {text}')
    print('=' * 70)


# ============================================================
# 命令 1: install
# ============================================================
def cmd_install(admin_pass: str):
    """建账号 + 撤销远程 root"""
    banner('步骤 1/5: 连接 MySQL（root 账号）')
    conn = get_admin_conn(admin_pass)
    cur = conn.cursor()
    print(f'✓ 已连接 {ADMIN_HOST}:{ADMIN_PORT}')

    try:
        # ---------- 步骤 2: 建只读账号 ----------
        banner('步骤 2/5: 建只读账号 trae_ro@localhost')
        if user_exists(cur, RO_USER, RO_HOST):
            print(f'⚠ {RO_USER}@{RO_HOST} 已存在，先删除重建')
            exec_sql(cur, f"DROP USER '{RO_USER}'@'{RO_HOST}'")

        exec_sql(cur, f"CREATE USER '{RO_USER}'@'{RO_HOST}' IDENTIFIED BY %s", (RO_PASS,))
        print(f'✓ 创建用户 {RO_USER}@{RO_HOST}')

        # 授权：3 个目标库的 SELECT + SHOW VIEW + EXECUTE
        for db in TARGET_DBS:
            exec_sql(cur, f"GRANT SELECT, SHOW VIEW, EXECUTE ON `{db}`.* TO '{RO_USER}'@'{RO_HOST}'")
            print(f'  ✓ 授权 {RO_USER} -> {db}.*  (SELECT/SHOW VIEW/EXECUTE)')

        # 注意：information_schema 在 MySQL 8 默认对所有用户只读可访问，无需 GRANT
        print(f'  ℹ information_schema 默认对所有用户只读可访问，无需授权')

        # ---------- 步骤 3: 建读写账号 ----------
        banner('步骤 3/5: 建读写账号 trae_rw@localhost')
        if user_exists(cur, RW_USER, RW_HOST):
            print(f'⚠ {RW_USER}@{RW_HOST} 已存在，先删除重建')
            exec_sql(cur, f"DROP USER '{RW_USER}'@'{RW_HOST}'")

        exec_sql(cur, f"CREATE USER '{RW_USER}'@'{RW_HOST}' IDENTIFIED BY %s", (RW_PASS,))
        print(f'✓ 创建用户 {RW_USER}@{RW_HOST}')

        # 授权：所有 DML + DDL
        for db in TARGET_DBS:
            exec_sql(cur, f"""GRANT SELECT, INSERT, UPDATE, DELETE,
                              CREATE, DROP, ALTER, INDEX, REFERENCES,
                              CREATE VIEW, SHOW VIEW, EXECUTE
                              ON `{db}`.* TO '{RW_USER}'@'{RW_HOST}'""")
            print(f'  ✓ 授权 {RW_USER} -> {db}.*  (DML + DDL)')

        conn.commit()
        print('\n✓ 用户授权已提交')

        # ---------- 步骤 4: 撤销远程 root ----------
        banner('步骤 4/5: 撤销 root@% 远程访问（安全加固）')
        if user_exists(cur, REMOTE_ROOT_USER, REMOTE_ROOT_HOST):
            print(f'⚠ 发现远程 root 账号 {REMOTE_ROOT_USER}@{REMOTE_ROOT_HOST}')

            # 通过环境变量控制（避免 input 卡住）
            auto_revoke = os.environ.get('MYSQL_MCP_AUTO_REVOKE', 'no').lower()
            if auto_revoke == 'yes':
                print('  环境变量 MYSQL_MCP_AUTO_REVOKE=yes → 自动撤销')
                exec_sql(cur, f"REVOKE ALL PRIVILEGES, GRANT OPTION FROM '{REMOTE_ROOT_USER}'@'{REMOTE_ROOT_HOST}'")
                exec_sql(cur, f"DROP USER '{REMOTE_ROOT_USER}'@'{REMOTE_ROOT_HOST}'")
                conn.commit()
                print(f'✓ 已删除远程 root 账号')
            else:
                print('  ⊘ 跳过撤销远程 root')
                print('  如需撤销：设环境变量 MYSQL_MCP_AUTO_REVOKE=yes 再跑 install')
        else:
            print('✓ 远程 root 账号不存在，无需处理')

        # 刷新权限
        exec_sql(cur, 'FLUSH PRIVILEGES')
        conn.commit()

        # ---------- 步骤 5: 验证 ----------
        banner('步骤 5/5: 验证新账号可登录')
        verify_new_accounts()

    except Exception as e:
        conn.rollback()
        print(f'\n✗ 安装失败: {e}')
        print('已自动回滚')
        sys.exit(1)
    finally:
        conn.close()

    # 输出 MCP 配置
    banner('✓ 安装完成！请按以下步骤挂载 MySQL MCP')
    print_mcp_config()


# ============================================================
# 命令 2: verify
# ============================================================
def verify_new_accounts():
    """用新账号重连测试"""
    print('  → 测试 trae_ro 只读账号...')
    try:
        ro_conn = pymysql.connect(
            host='127.0.0.1', port=ADMIN_PORT,
            user=RO_USER, password=RO_PASS,
            database='steel_belt', charset='utf8mb4',
        )
        ro_cur = ro_conn.cursor()
        ro_cur.execute('SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s', ('steel_belt',))
        table_count = ro_cur.fetchone()[0]
        print(f'    ✓ 只读连接成功，steel_belt 库有 {table_count} 张表')
        ro_conn.close()
    except Exception as e:
        print(f'    ✗ 只读账号测试失败: {e}')
        return False

    print('  → 测试 trae_rw 读写账号...')
    try:
        rw_conn = pymysql.connect(
            host='127.0.0.1', port=ADMIN_PORT,
            user=RW_USER, password=RW_PASS,
            database='steel_belt', charset='utf8mb4',
        )
        rw_cur = rw_conn.cursor()
        rw_cur.execute('SELECT 1')
        print('    ✓ 读写连接成功')
        rw_conn.close()
    except Exception as e:
        print(f'    ✗ 读写账号测试失败: {e}')
        return False

    return True


def cmd_verify(admin_pass: str):
    """仅验证，不修改"""
    banner('验证模式：不修改任何数据')
    conn = get_admin_conn(admin_pass)
    cur = conn.cursor()

    try:
        print('  → 检查 root@% 远程账号...')
        if user_exists(cur, REMOTE_ROOT_USER, REMOTE_ROOT_HOST):
            print(f'    ⚠ 远程 root 仍存在（{REMOTE_ROOT_USER}@{REMOTE_ROOT_HOST}）')
        else:
            print('    ✓ 远程 root 已撤销')

        print('\n  → 检查 trae_ro 只读账号...')
        if user_exists(cur, RO_USER, RO_HOST):
            print(f'    ✓ {RO_USER}@{RO_HOST} 存在')
        else:
            print(f'    ✗ {RO_USER}@{RO_HOST} 不存在')

        print('\n  → 检查 trae_rw 读写账号...')
        if user_exists(cur, RW_USER, RW_HOST):
            print(f'    ✓ {RW_USER}@{RW_HOST} 存在')
        else:
            print(f'    ✗ {RW_USER}@{RW_HOST} 不存在')

        print('\n  → 实测新账号连接...')
        verify_new_accounts()

    finally:
        conn.close()


# ============================================================
# 命令 3: uninstall
# ============================================================
def cmd_uninstall(admin_pass: str):
    """删账号 + 恢复远程 root"""
    banner('卸载模式：删除 trae_ro / trae_rw')
    conn = get_admin_conn(admin_pass)
    cur = conn.cursor()
    try:
        for user, host in [(RO_USER, RO_HOST), (RW_USER, RW_HOST)]:
            if user_exists(cur, user, host):
                exec_sql(cur, f"REVOKE ALL PRIVILEGES, GRANT OPTION FROM '{user}'@'{host}'")
                exec_sql(cur, f"DROP USER '{user}'@'{host}'")
                print(f'  ✓ 已删除 {user}@{host}')
            else:
                print(f'  - {user}@{host} 不存在，跳过')

        conn.commit()
        print('\n✓ 卸载完成')
    except Exception as e:
        conn.rollback()
        print(f'✗ 卸载失败: {e}')
    finally:
        conn.close()


# ============================================================
# 命令 4: revoke-remote
# ============================================================
def cmd_revoke_remote(admin_pass: str):
    """仅撤销远程 root"""
    banner('撤销远程 root@%')
    conn = get_admin_conn(admin_pass)
    cur = conn.cursor()
    try:
        if user_exists(cur, REMOTE_ROOT_USER, REMOTE_ROOT_HOST):
            exec_sql(cur, f"REVOKE ALL PRIVILEGES, GRANT OPTION FROM '{REMOTE_ROOT_USER}'@'{REMOTE_ROOT_HOST}'")
            exec_sql(cur, f"DROP USER '{REMOTE_ROOT_USER}'@'{REMOTE_ROOT_HOST}'")
            conn.commit()
            print(f'✓ 已撤销远程 root')
        else:
            print('✓ 远程 root 不存在，无需处理')
    except Exception as e:
        conn.rollback()
        print(f'✗ 失败: {e}')
    finally:
        conn.close()


# ============================================================
# 输出 MCP 配置
# ============================================================
def print_mcp_config():
    """打印可粘贴的 MCP 配置 JSON"""
    config = {
        "mcpServers": {
            "codebase-memory-mcp": {
                "command": "d:\\tools\\codebase-memory-mcp.exe",
                "args": ["--stdio"]
            },
            "mysql": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-mysql"],
                "env": {
                    "MYSQL_HOST": "127.0.0.1",
                    "MYSQL_PORT": "3306",
                    "MYSQL_USER": RO_USER,
                    "MYSQL_PASSWORD": RO_PASS
                }
            }
        }
    }

    print('\n' + '-' * 70)
    print('请复制以下 JSON 到 Trae MCP 配置文件：')
    print('文件位置: C:\\Users\\lenovo\\AppData\\Roaming\\TRAE SOLO CN\\User\\mcp.json')
    print('-' * 70)
    import json
    print(json.dumps(config, indent=2, ensure_ascii=False))
    print('-' * 70)
    print('\n下一步：')
    print('  1. 打开 Trae IDE')
    print('  2. 打开 MCP 配置文件，把上述 JSON 替换进去')
    print('  3. 重启 Trae IDE')
    print('  4. 工具列表中应出现 mcp__mysql__* 系列工具')


# ============================================================
# 入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description='MySQL MCP 准备脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest='command', required=True)

    sub.add_parser('install', help='建账号 + 撤销远程 root')
    sub.add_parser('verify', help='验证当前状态')
    sub.add_parser('uninstall', help='删除 trae 账号')
    sub.add_parser('revoke-remote', help='仅撤销远程 root')

    args = parser.parse_args()

    # 密码获取优先级：环境变量 > .env 默认密码
    admin_pass = os.environ.get('MYSQL_ROOT_PASSWORD') or '88888888'
    print(f'[使用 MySQL root 密码: {"<环境变量>" if os.environ.get("MYSQL_ROOT_PASSWORD") else "<项目 .env 默认值>"}]')

    if args.command == 'install':
        cmd_install(admin_pass)
    elif args.command == 'verify':
        cmd_verify(admin_pass)
    elif args.command == 'uninstall':
        cmd_uninstall(admin_pass)
    elif args.command == 'revoke-remote':
        cmd_revoke_remote(admin_pass)


if __name__ == '__main__':
    main()
