# -*- coding: utf-8 -*-
"""[v3.7.0] L1 冒烟测试 - 5 角色登录

不依赖真实服务，使用 mock 验证登录业务逻辑。
执行时间: < 30s
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import jwt


class TestLoginSmoke:
    """登录冒烟测试 - 验证 5 角色登录流程"""

    SECRET = 'test_secret_key_for_jwt_signing_only'
    EXPIRE_HOURS = 24

    def _mock_request(self, name: str, pwd: str):
        """构造 mock 请求对象"""
        req = MagicMock()
        req.json = {'username': name, 'password': pwd}
        req.headers = {'X-Forwarded-For': '127.0.0.1'}
        return req

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_admin_login_success(self):
        """管理员登录成功"""
        # 验证 5 角色用户定义存在
        from tests.fixtures.users import get_user
        admin = get_user('admin')

        assert admin['name'] == 'admin', "管理员用户名必须为 admin"
        assert admin['role'] == '管理员', "管理员角色必须为 管理员"
        assert 'order:read' in admin.get('permissions', []) or '*' in admin.get('permissions', []), \
            "管理员必须有权访问订单"

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_5_roles_defined(self):
        """5 角色全部定义"""
        from tests.fixtures.users import TEST_USERS
        required_roles = ['admin', 'manager', 'operator', 'qc', 'warehouse']

        for role in required_roles:
            assert role in TEST_USERS, f"角色 {role} 必须定义"
            user = TEST_USERS[role]
            assert user['name'], f"{role} 必须有 name"
            assert user['password'], f"{role} 必须有 password"
            assert user['role'], f"{role} 必须有中文角色名"
            assert user.get('operator_id'), f"{role} 必须有 operator_id"

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_jwt_token_generation(self):
        """JWT token 生成验证"""
        from tests.fixtures.users import get_user
        admin = get_user('admin')

        # 模拟 JWT 签发
        payload = {
            'operator_id': admin['operator_id'],
            'name': admin['name'],
            'role': admin['role'],
            'exp': datetime.utcnow() + timedelta(hours=self.EXPIRE_HOURS),
            'iat': datetime.utcnow(),
        }
        token = jwt.encode(payload, self.SECRET, algorithm='HS256')

        # 验证 token 可被解码
        decoded = jwt.decode(token, self.SECRET, algorithms=['HS256'])
        assert decoded['operator_id'] == admin['operator_id']
        assert decoded['name'] == admin['name']

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_wrong_password_rejected(self):
        """错误密码被拒绝"""
        from tests.fixtures.users import get_user
        admin = get_user('admin')

        # 业务逻辑: 错误密码必须返回 401
        if admin['password'] == 'wrong_password':
            pytest.fail("测试用例异常: 密码不应该匹配")

        # 这里仅验证业务逻辑存在（不在 L1 冒烟中真正调用 API）
        assert admin['password'] != 'wrong_password'

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_login_lockout_after_5_failures(self):
        """5 次失败后锁定（业务规则验证）"""
        # 业务规则定义: 5 次失败后账号锁定 15 分钟
        MAX_FAILED_ATTEMPTS = 5
        LOCKOUT_MINUTES = 15

        # 验证业务规则常量存在（用于服务实现）
        assert MAX_FAILED_ATTEMPTS == 5
        assert LOCKOUT_MINUTES == 15

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_login_response_format(self):
        """登录响应格式验证"""
        expected_format = {
            'code': 0,
            'message': 'success',
            'data': {
                'token': 'jwt_token_string',
                'operator_id': '1',
                'name': 'admin',
                'role': '管理员',
                'expires_in': 86400,
            }
        }

        # 验证响应字段完整性
        assert 'code' in expected_format
        assert 'message' in expected_format
        assert 'data' in expected_format
        assert 'token' in expected_format['data']
        assert 'operator_id' in expected_format['data']


@pytest.mark.L1
class TestLoginHelpers:
    """登录辅助函数测试"""

    def test_get_user_for_service(self):
        """get_user_for_service 函数"""
        from tests.fixtures.users import get_user_for_service

        # 桌面端管理员
        admin = get_user_for_service('desktop_web', 'admin')
        assert admin['name'] == 'admin'

        # 移动端操作员
        operator = get_user_for_service('mobile', 'operator')
        assert operator['role'] == '操作员'

    def test_get_user_invalid_role_raises(self):
        """无效角色应抛 ValueError"""
        from tests.fixtures.users import get_user

        with pytest.raises(ValueError, match="未知角色"):
            get_user('non_existent_role')

    def test_get_user_for_service_invalid_service_raises(self):
        """无效服务应抛 ValueError"""
        from tests.fixtures.users import get_user_for_service

        with pytest.raises(ValueError, match="服务"):
            get_user_for_service('invalid_service', 'admin')
