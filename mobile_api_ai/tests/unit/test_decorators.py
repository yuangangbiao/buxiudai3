# -*- coding: utf-8 -*-
"""
decorators 单元测试

覆盖：
- success / fail 响应格式
- validate_json_params 装饰器
- validate_type 装饰器
- 各种边界情况
"""
import pytest
from unittest.mock import MagicMock, patch


class TestResponseHelpers:
    """success / fail 响应格式测试"""

    @patch('api.decorators.jsonify')
    def test_success_minimal(self, mock_jsonify):
        from api.decorators import success
        success()
        call_args = mock_jsonify.call_args[0][0]
        assert call_args['code'] == 0
        assert call_args['message'] == '操作成功'

    @patch('api.decorators.jsonify')
    def test_success_with_data(self, mock_jsonify):
        from api.decorators import success
        success(data={'x': 1})
        call_args = mock_jsonify.call_args[0][0]
        assert call_args['data'] == {'x': 1}

    @patch('api.decorators.jsonify')
    def test_success_with_extra(self, mock_jsonify):
        from api.decorators import success
        success(data=[1, 2], message='完成', total=10)
        call_args = mock_jsonify.call_args[0][0]
        assert call_args['total'] == 10
        assert call_args['message'] == '完成'

    @patch('api.decorators.jsonify')
    def test_success_none_data_excluded(self, mock_jsonify):
        from api.decorators import success
        success()
        call_args = mock_jsonify.call_args[0][0]
        assert 'data' not in call_args

    @patch('api.decorators.jsonify')
    def test_fail(self, mock_jsonify):
        from api.decorators import fail
        fail(500, '服务器错误')
        call_args = mock_jsonify.call_args[0][0]
        assert call_args['code'] == 500
        assert call_args['message'] == '服务器错误'

    @patch('api.decorators.jsonify')
    def test_fail_with_data(self, mock_jsonify):
        from api.decorators import fail
        fail(400, '参数错误', data={'field': 'x'})
        call_args = mock_jsonify.call_args[0][0]
        assert call_args['data'] == {'field': 'x'}


class TestValidateJsonParams:
    """validate_json_params 装饰器测试"""

    def setup_method(self):
        from flask import Flask
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_valid_request(self):
        from api.decorators import validate_json_params, success
        @self.app.route('/test', methods=['POST'])
        @validate_json_params('name', 'email')
        def view():
            from flask import request
            assert request.validated_data['name'] == 'test'
            return success()
        resp = self.client.post('/test', json={'name': 'test', 'email': 'a@b.com'})
        assert resp.status_code == 200

    def test_missing_field(self):
        from api.decorators import validate_json_params
        @self.app.route('/test', methods=['POST'])
        @validate_json_params('name', 'email')
        def view():
            from flask import jsonify
            return jsonify({'ok': True})
        resp = self.client.post('/test', json={'name': 'test'})
        data = resp.get_json()
        assert data['code'] == 400
        assert 'email' in data['message']

    def test_no_json(self):
        from api.decorators import validate_json_params
        @self.app.route('/test', methods=['POST'])
        @validate_json_params('name')
        def view():
            from flask import jsonify
            return jsonify({'ok': True})
        resp = self.client.post('/test', data='not json', content_type='text/plain')
        data = resp.get_json()
        assert data['code'] == 400
        assert 'JSON' in data['message']

    def test_optional_fields_filled_with_none(self):
        from api.decorators import validate_json_params, success
        @self.app.route('/test', methods=['POST'])
        @validate_json_params('name', optional_fields=['age', 'gender'])
        def view():
            from flask import request
            assert request.validated_data['age'] is None
            assert request.validated_data['gender'] is None
            return success()
        resp = self.client.post('/test', json={'name': 'test'})
        assert resp.status_code == 200

    def test_required_field_none(self):
        from api.decorators import validate_json_params
        @self.app.route('/test', methods=['POST'])
        @validate_json_params('name')
        def view():
            from flask import jsonify
            return jsonify({'ok': True})
        resp = self.client.post('/test', json={'name': None})
        data = resp.get_json()
        assert data['code'] == 400

    def test_zero_value_passes(self):
        from api.decorators import validate_json_params, success
        @self.app.route('/test', methods=['POST'])
        @validate_json_params('count')
        def view():
            return success()
        resp = self.client.post('/test', json={'count': 0})
        assert resp.status_code == 200


class TestValidateType:
    """validate_type 装饰器测试"""

    def setup_method(self):
        from flask import Flask
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_wrong_order(self):
        from api.decorators import validate_type
        @self.app.route('/test', methods=['POST'])
        @validate_type('count', int)
        def view():
            from flask import jsonify
            return jsonify({'ok': True})
        resp = self.client.post('/test', json={'count': 5})
        data = resp.get_json()
        assert data['code'] == 500

    def test_correct_type(self):
        from api.decorators import validate_json_params, validate_type, success
        @self.app.route('/test', methods=['POST'])
        @validate_json_params('count')
        @validate_type('count', int)
        def view():
            return success()
        resp = self.client.post('/test', json={'count': 5})
        assert resp.status_code == 200

    def test_wrong_type(self):
        from api.decorators import validate_json_params, validate_type
        @self.app.route('/test', methods=['POST'])
        @validate_json_params('count')
        @validate_type('count', int, 'count必须是整数')
        def view():
            from flask import jsonify
            return jsonify({'ok': True})
        resp = self.client.post('/test', json={'count': '5'})
        data = resp.get_json()
        assert data['code'] == 400
        assert 'count必须是整数' in data['message']

    def test_bool_is_int(self):
        from api.decorators import validate_json_params, validate_type, success
        @self.app.route('/test', methods=['POST'])
        @validate_json_params('count')
        @validate_type('count', int)
        def view():
            return success()
        resp = self.client.post('/test', json={'count': True})
        assert resp.status_code == 200
