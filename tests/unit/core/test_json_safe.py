# -*- coding: utf-8 -*-
r"""core/json_safe.py 的集成测试(真 Flask app + 真 HTTP 请求,无 mock)。

真源码行为(已读 d:\yuan\不锈钢网带跟单3.0\core\json_safe.py 验证):
- Content-Type 含 'application/json' 或 'text/plain' → 放行,执行 func
- 其他(POST/PUT/PATCH)→ 返 415 + 错误体 {'code': 415, 'message': '请求必须包含 Content-Type: application/json'}
- GET 请求跳过检查(不验证 Content-Type)

按 F16 §1:不 mock Flask 业务,真业务走 test_client + test_request_context。
"""
import json

import pytest
from flask import Flask, jsonify, request

from core.json_safe import require_json_content_type


@pytest.fixture
def app():
    """最小化真 Flask app,挂载 @require_json_content_type 装饰的端点。"""
    app = Flask(__name__)

    @app.route("/api/echo", methods=["GET", "POST"])
    @require_json_content_type
    def _echo():
        return jsonify({"received": request.get_json(silent=True) or {}})

    @app.route("/api/noop", methods=["POST"])
    @require_json_content_type
    def _noop():
        return jsonify({"status": "ok"})

    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_passes_when_content_type_is_application_json(client):
    """Content-Type=application/json 时,装饰器透传原函数并返 200。"""
    payload = {"order_no": "GO-2026-001", "process": "原材料准备"}
    res = client.post(
        "/api/echo", data=json.dumps(payload), content_type="application/json"
    )
    assert res.status_code == 200
    body = res.get_json()
    assert body == {"received": payload}


def test_passes_when_content_type_is_text_plain(client):
    """Content-Type=text/plain 也在白名单(看真源码第 20 行 'text/plain' not in ct)→ 放行。"""
    res = client.post("/api/echo", data="any text", content_type="text/plain")
    assert res.status_code == 200
    assert res.get_json() == {"received": {}}


def test_returns_415_when_content_type_missing_on_post(client):
    """POST + Content-Type 缺失 → 装饰器返 415 + 标准错误体(真源码第 21 行)。"""
    res = client.post("/api/echo", data="not json")
    assert res.status_code == 415
    body = res.get_json()
    assert body == {"code": 415, "message": "请求必须包含 Content-Type: application/json"}


def test_returns_415_when_content_type_is_form(client):
    """POST + application/x-www-form-urlencoded → 返 415(白名单只有 application/json/text/plain)。"""
    res = client.post(
        "/api/echo",
        data={"order_no": "GO-001"},
        content_type="application/x-www-form-urlencoded",
    )
    assert res.status_code == 415
    assert res.get_json()["code"] == 415


def test_get_request_skips_content_type_check(client):
    """GET 请求不检查 Content-Type(真源码第 18 行),即使缺也返 200。"""
    res = client.get("/api/echo")
    assert res.status_code == 200


def test_decorated_function_preserves_metadata():
    """@functools.wraps 必须保留原函数的 __name__ 和 __doc__(签名契约)。"""
    def _my_endpoint():
        """我的端点说明。"""
        return "ok"

    decorated = require_json_content_type(_my_endpoint)
    assert decorated.__name__ == "_my_endpoint"
    assert decorated.__doc__ == "我的端点说明。"


def test_decorated_function_executes_inner_code_when_json_accepted(client):
    """Content-Type 正确时,装饰器执行 inner 函数体并返 200(走真业务路径)。"""
    res = client.post("/api/noop", data="{}", content_type="application/json")
    assert res.status_code == 200
    assert res.get_json() == {"status": "ok"}
