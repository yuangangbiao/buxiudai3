# -*- coding: utf-8 -*-
"""
测试企业微信 OAuth2 登录模块
覆盖：参数缺失、企业微信API异常、操作员不匹配、操作员禁用、正常登录
"""
import sys, os, json, unittest
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ['JWT_SECRET_KEY'] = 'test-secret-key'
os.environ['WECHAT_CORP_ID'] = 'mock_corpid'
os.environ['WECHAT_SECRET'] = 'mock_secret'

from flask import Flask
from container_config import OperatorConfig


class TestWecomAuth(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        from container_config import container_config as real_config
        self._real_ops = real_config._operators
        real_config._operators = {}
        self._setup_operators(real_config)

        from wecom_auth import bp as wecom_bp
        self._app = Flask(__name__)
        self._app.register_blueprint(wecom_bp)
        self.client = self._app.test_client()

    def _setup_operators(self, config):
        ops = [
            OperatorConfig(id='zhangsan', name='张三', role='员工',
                          department='生产部', enabled=True,
                          notify_enabled=False, max_tasks=5,
                          wechat_userid='zhangsan'),
            OperatorConfig(id='lisi', name='李四', role='员工',
                          department='生产部', enabled=False,
                          notify_enabled=False, max_tasks=5,
                          wechat_userid='lisi'),
            OperatorConfig(id='wangwu', name='王五', role='员工',
                          department='质检部', enabled=True,
                          notify_enabled=False, max_tasks=5,
                          wechat_userid=''),
        ]
        for op in ops:
            config._operators[op.id] = op

    def _make_token_response(self, access_token='mock_token', errcode=0):
        return MagicMock(ok=True, status_code=200,
                         json=lambda: {'errcode': errcode, 'access_token': access_token})

    def _make_user_response(self, userid='zhangsan', errcode=0):
        resp = {'errcode': errcode, 'UserId': userid} if errcode == 0 else {'errcode': errcode, 'errmsg': 'invalid code'}
        return MagicMock(ok=True, status_code=200, json=lambda: resp)

    def test_missing_code(self):
        resp = self.client.post('/api/wecom/login', json={})
        data = resp.get_json()
        self.assertEqual(data['code'], 400)
        self.assertIn('code', data['message'])

    @patch('wecom_auth.requests.get')
    def test_wechat_api_token_fail(self, mock_get):
        mock_get.return_value = self._make_token_response(errcode=40014)
        resp = self.client.post('/api/wecom/login', json={'code': 'invalid_code'})
        data = resp.get_json()
        self.assertEqual(data['code'], 500)

    @patch('wecom_auth.requests.get')
    def test_wechat_api_user_not_found(self, mock_get):
        token_resp = self._make_token_response()
        user_resp = self._make_user_response(errcode=40029)
        mock_get.side_effect = [token_resp, user_resp]
        resp = self.client.post('/api/wecom/login', json={'code': 'bad_code'})
        data = resp.get_json()
        self.assertEqual(data['code'], 500)

    @patch('wecom_auth.requests.get')
    def test_operator_not_matched(self, mock_get):
        token_resp = self._make_token_response()
        user_resp = self._make_user_response(userid='not_in_system')
        mock_get.side_effect = [token_resp, user_resp]
        resp = self.client.post('/api/wecom/login', json={'code': 'valid_code'})
        data = resp.get_json()
        self.assertEqual(data['code'], 401)

    @patch('wecom_auth.requests.get')
    def test_operator_disabled(self, mock_get):
        token_resp = self._make_token_response()
        user_resp = self._make_user_response(userid='lisi')
        mock_get.side_effect = [token_resp, user_resp]
        resp = self.client.post('/api/wecom/login', json={'code': 'valid_code'})
        data = resp.get_json()
        self.assertEqual(data['code'], 403)

    @patch('wecom_auth.requests.get')
    def test_login_success(self, mock_get):
        token_resp = self._make_token_response()
        user_resp = self._make_user_response(userid='zhangsan')
        mock_get.side_effect = [token_resp, user_resp]
        resp = self.client.post('/api/wecom/login', json={'code': 'valid_code'})
        data = resp.get_json()
        self.assertEqual(data['code'], 0)
        self.assertEqual(data['operator']['name'], '张三')
        self.assertIn('token', data)
        self.assertIsInstance(data['token'], str)
        self.assertGreater(len(data['token']), 20)

    @patch('wecom_auth.requests.get')
    def test_login_with_empty_wechat_userid(self, mock_get):
        """wechat_userid 为空的王五，看能否正常被排除"""
        token_resp = self._make_token_response()
        user_resp = self._make_user_response(userid='wangwu')
        mock_get.side_effect = [token_resp, user_resp]
        resp = self.client.post('/api/wecom/login', json={'code': 'valid_code'})
        data = resp.get_json()
        self.assertEqual(data['code'], 401)

    def tearDown(self):
        from container_config import container_config
        container_config._operators = {}


if __name__ == '__main__':
    unittest.main(verbosity=2)
