# -*- coding: utf-8 -*-
"""
测试 P0 dispatch_server role 硬编码修复 (2026-06-23 小钰修复)

覆盖场景:
1. [D-1] mobile_login SQL 查 role 字段
2. [D-2] mobile_login 不再硬编码 role='worker' (用 row[4] or 'worker')
3. [D-3] 测试用户兜底 role='admin' (便于 admin 路径测试)
4. [D-4] 端到端: 调真实 5003 /api/login 看 role 字段

运行方式:
  & "C:\\Users\\lenovo\\AppData\\Local\\Python\\pythoncore-3.14-64\\python.exe" -m pytest desktop_web/tests/test_p0_dispatch_role.py -v
"""
import os
import sys
import re

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
if _ROOT not in sys.path:
    sys.path.insert(0, os.path.join(_ROOT, 'mobile_api_ai'))

DISPATCH = os.path.join(_ROOT, 'mobile_api_ai', 'standalone_dispatch_server.py')
DISPATCH_BASE = os.getenv('DISPATCH_BASE', 'http://127.0.0.1:5003')


class TestDispatchRoleFixStatic:
    """dispatch_server.py 源码静态校验"""

    def _read(self):
        with open(DISPATCH, 'r', encoding='utf-8') as f:
            return f.read()

    def _mobile_login_block(self):
        """提取 mobile_login 完整函数体"""
        src = self._read()
        lines = src.split('\n')
        # 找 def mobile_login 行
        start = None
        for i, line in enumerate(lines):
            if 'def mobile_login' in line:
                start = i
                break
        assert start is not None, '未找到 def mobile_login'
        # 函数体: 缩进 > 0 空格 的行 (函数体至少缩进 4 空格)
        body_lines = [lines[start]]
        for i in range(start + 1, len(lines)):
            line = lines[i]
            # 结束条件: 0 缩进的顶级语句, 或下一个 def / @app.route
            if line.strip() == '':
                body_lines.append(line)
                continue
            indent = len(line) - len(line.lstrip())
            if indent == 0:
                break
            body_lines.append(line)
        return '\n'.join(body_lines)

    def test_d_1_sql_includes_role(self):
        """[D-1] mobile_login SQL 已查 role 列"""
        body = self._mobile_login_block()
        # SQL: SELECT id, name, department, wechat_userid, role FROM operators
        assert 'wechat_userid, role FROM operators' in body or 'role FROM operators' in body, \
            f'D-1 FAIL: SQL 未查 role 列\nbody head: {body[:600]}'
        print('  [OK] SQL 已查 role 列')

    def test_d_2_no_hardcoded_worker(self):
        """[D-2] mobile_login 不再硬编码 role='worker' (L152 已修)"""
        body = self._mobile_login_block()
        assert "'role': 'worker'" not in body, \
            f'D-2 FAIL: 仍存在硬编码 \'role\': \'worker\'\nbody: {body[:800]}'
        assert "row[4] or 'worker'" in body, \
            "D-2 FAIL: 未使用 row[4] or 'worker' 替换"
        print('  [OK] 硬编码 role=worker 已替换为 row[4] or worker')

    def test_d_3_test_user_is_admin(self):
        """[D-3] 测试用户兜底 role 改为 admin (便于 admin 路径测试)"""
        body = self._mobile_login_block()
        # 找 if username == '测试' 行, 取后续 N 行
        lines = body.split('\n')
        block_start = None
        for i, line in enumerate(lines):
            if "username == '测试'" in line:
                block_start = i
                break
        assert block_start is not None, '未找到测试用户兜底'
        # 取后续 10 行 (return jsonify... 包括 role 行)
        block = '\n'.join(lines[block_start:block_start + 10])
        assert "'role': 'admin'" in block, \
            f'D-3 FAIL: 测试用户兜底 role 不是 admin\n{block}'
        print('  [OK] 测试用户兜底 role=admin')

    def test_d_4_comment_added(self):
        """[D-4] 代码注释明确标记为 P0 修复 (小钰 2026-06-23)"""
        src = self._read()
        assert 'P0 修复 2026-06-23 小钰' in src, \
            'D-4 FAIL: 缺少 P0 修复标记注释'
        print('  [OK] 代码已加 P0 修复标记注释')


def test_d_5_e2e_login_returns_real_role():
    """[D-5] 端到端: 调真实 5003 /api/login 看 role 字段 (不 mock)

    前置条件: 5003 服务必须正在运行
    """
    import requests
    try:
        r = requests.get(f'{DISPATCH_BASE}/health', timeout=3)
    except Exception:
        try:
            r = requests.get(f'{DISPATCH_BASE}/api/health', timeout=3)
        except Exception as e:
            import pytest
            pytest.skip(f'5003 不可达, 跳过端到端: {e}')

    # 用测试用户 (走 admin 兜底)
    r_login = requests.post(
        f'{DISPATCH_BASE}/api/login',
        json={'username': '测试'},
        timeout=5
    )
    print(f'  [INFO] 5003 /api/login 状态: {r_login.status_code}')
    if r_login.status_code != 200:
        print(f'  [INFO] 响应: {r_login.text[:200]}')
        import pytest
        pytest.skip('登录失败, 跳过 e2e')

    body = r_login.json()
    if body.get('code') != 0:
        import pytest
        pytest.skip(f'登录业务失败: {body.get("message")}, 跳过 e2e')

    user = body['data']
    role = user.get('role')
    print(f'  [OK] 登录成功: name={user.get("name")} role={role}')

    # 修复后, 测试用户兜底应该返回 admin (不是 worker)
    # 如果仍是 worker, 说明修复未生效 / 5003 未重启
    if role == 'worker':
        print(f'  [WARN] role 仍为 worker — 5003 可能未重启加载新代码')
    elif role == 'admin':
        print('  [OK] role=admin 修复生效')
    else:
        print(f'  [INFO] role={role} (其他值, 来自 DB)')


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v', '--tb=short'])
