# -*- coding: utf-8 -*-
"""
API Swagger/OpenAPI 文档

访问地址：/api/docs
"""
from flask import Blueprint, jsonify, render_template

bp = Blueprint('docs', __name__, url_prefix='/api/docs')


API_DOCS = {
    "openapi": "3.0.0",
    "info": {
        "title": "不锈钢网带跟单系统 API",
        "description": "AI增强版移动报工系统API文档",
        "version": "2.0.0",
        "contact": {
            "name": "Steel Belt Team"
        }
    },
    "servers": [
        {"url": "/api", "description": "当前服务器"}
    ],
    "paths": {
        "/auth/login": {
            "post": {
                "tags": ["认证"],
                "summary": "用户登录",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["username", "password"],
                                "properties": {
                                    "username": {"type": "string", "example": "admin"},
                                    "password": {"type": "string", "example": "{your_password}"}
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "登录成功",
                        "content": {
                            "application/json": {
                                "example": {"code": 0, "message": "登录成功", "data": {"token": "eyJ..."}}
                            }
                        }
                    }
                }
            }
        },
        "/process/my-tasks": {
            "get": {
                "tags": ["报工"],
                "summary": "获取我的任务",
                "parameters": [
                    {"name": "worker_id", "in": "query", "schema": {"type": "string"}, "example": "OP001"}
                ],
                "responses": {
                    "200": {
                        "description": "任务列表",
                        "content": {
                            "application/json": {
                                "example": {"code": 0, "data": {"tasks": [], "total": 0}}
                            }
                        }
                    }
                }
            }
        },
        "/process/<int:record_id>/report": {
            "post": {
                "tags": ["报工"],
                "summary": "提交报工",
                "parameters": [
                    {"name": "record_id", "in": "path", "required": True, "schema": {"type": "integer"}}
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["completed_qty"],
                                "properties": {
                                    "completed_qty": {"type": "number", "example": 100},
                                    "status": {"type": "string", "example": "已完成"},
                                    "qualified_qty": {"type": "number", "example": 98},
                                    "remark": {"type": "string", "example": "质量合格"}
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "报工成功",
                        "content": {
                            "application/json": {
                                "example": {"code": 0, "message": "报工成功"}
                            }
                        }
                    }
                }
            }
        },
        "/process/history": {
            "get": {
                "tags": ["报工"],
                "summary": "报工历史记录",
                "parameters": [
                    {"name": "worker_id", "in": "query", "schema": {"type": "string"}, "example": "OP001"}
                ],
                "responses": {
                    "200": {
                        "description": "历史记录列表",
                        "content": {
                            "application/json": {
                                "example": {"code": 0, "data": {"records": [], "total": 0}}
                            }
                        }
                    }
                }
            }
        },
        "/quality/list": {
            "get": {
                "tags": ["质检"],
                "summary": "质检记录列表",
                "parameters": [
                    {"name": "page", "in": "query", "schema": {"type": "integer"}, "example": 1},
                    {"name": "page_size", "in": "query", "schema": {"type": "integer"}, "example": 20}
                ],
                "responses": {
                    "200": {
                        "description": "质检记录列表",
                        "content": {
                            "application/json": {
                                "example": {"code": 0, "data": {"records": [], "total": 0}}
                            }
                        }
                    }
                }
            }
        },
        "/quality/create": {
            "post": {
                "tags": ["质检"],
                "summary": "创建质检记录",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "order_id": {"type": "integer", "example": 1},
                                    "inspection_type": {"type": "string", "example": "来料检验"},
                                    "result": {"type": "string", "example": "合格"},
                                    "inspector": {"type": "string", "example": "QC001"}
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "创建成功"
                    }
                }
            }
        },
        "/approval/pending": {
            "get": {
                "tags": ["审批"],
                "summary": "待审批列表",
                "parameters": [
                    {"name": "page", "in": "query", "schema": {"type": "integer"}, "example": 1}
                ],
                "responses": {
                    "200": {
                        "description": "待审批列表",
                        "content": {
                            "application/json": {
                                "example": {"code": 0, "data": {"items": [], "total": 0}}
                            }
                        }
                    }
                }
            }
        },
        "/approval/approve": {
            "post": {
                "tags": ["审批"],
                "summary": "审批通过",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["order_id"],
                                "properties": {
                                    "order_id": {"type": "integer", "example": 1},
                                    "comment": {"type": "string", "example": "同意"}
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "审批成功"
                    }
                }
            }
        },
        "/approval/reject": {
            "post": {
                "tags": ["审批"],
                "summary": "审批拒绝",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["order_id"],
                                "properties": {
                                    "order_id": {"type": "integer", "example": 1},
                                    "reason": {"type": "string", "example": "不符合要求"}
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "拒绝成功"
                    }
                }
            }
        },
        "/message/list": {
            "get": {
                "tags": ["消息"],
                "summary": "消息列表",
                "parameters": [
                    {"name": "page", "in": "query", "schema": {"type": "integer"}, "example": 1},
                    {"name": "page_size", "in": "query", "schema": {"type": "integer"}, "example": 20}
                ],
                "responses": {
                    "200": {
                        "description": "消息列表",
                        "content": {
                            "application/json": {
                                "example": {"code": 0, "data": {"messages": [], "total": 0}}
                            }
                        }
                    }
                }
            }
        },
        "/ai/speech-report": {
            "post": {
                "tags": ["AI"],
                "summary": "语音转报工",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "audio_data": {"type": "string", "description": "Base64编码的音频数据"},
                                    "worker_id": {"type": "string", "example": "OP001"}
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "语音识别成功",
                        "content": {
                            "application/json": {
                                "example": {"code": 0, "data": {"text": "裁剪100个", "report_data": {}}}
                            }
                        }
                    }
                }
            }
        },
        "/ai/analyze-image": {
            "post": {
                "tags": ["AI"],
                "summary": "图像分析",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "image_data": {"type": "string", "description": "Base64编码的图片数据"}
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "分析成功"
                    }
                }
            }
        },
        "/ai/chat": {
            "post": {
                "tags": ["AI"],
                "summary": "AI对话",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "message": {"type": "string", "example": "如何提高编织效率？"},
                                    "user_id": {"type": "string", "example": "OP001"}
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "对话成功",
                        "content": {
                            "application/json": {
                                "example": {"code": 0, "data": {"reply": "建议..."}}
                            }
                        }
                    }
                }
            }
        },
        "/metrics/stats": {
            "get": {
                "tags": ["监控"],
                "summary": "获取监控指标",
                "parameters": [
                    {"name": "minutes", "in": "query", "schema": {"type": "integer"}, "example": 60, "description": "统计时间范围（分钟）"}
                ],
                "responses": {
                    "200": {
                        "description": "监控指标",
                        "content": {
                            "application/json": {
                                "example": {"code": 0, "data": {"api": {}, "reports": {}, "errors": {}}}
                            }
                        }
                    }
                }
            }
        },
        "/metrics/health": {
            "get": {
                "tags": ["监控"],
                "summary": "健康检查",
                "responses": {
                    "200": {
                        "description": "服务健康",
                        "content": {
                            "application/json": {
                                "example": {"code": 0, "data": {"status": "healthy"}}
                            }
                        }
                    },
                    "503": {
                        "description": "服务降级",
                        "content": {
                            "application/json": {
                                "example": {"code": 503, "message": "Service degraded"}
                            }
                        }
                    }
                }
            }
        }
    },
    "tags": [
        {"name": "认证", "description": "用户认证相关"},
        {"name": "报工", "description": "报工记录相关"},
        {"name": "质检", "description": "质检记录相关"},
        {"name": "审批", "description": "审批流程相关"},
        {"name": "消息", "description": "消息通知相关"},
        {"name": "AI", "description": "AI增强功能"},
        {"name": "监控", "description": "系统监控相关"}
    ]
}


@bp.route('/')
def swagger_ui():
    """Swagger UI页面"""
    return render_template('swagger.html', spec=API_DOCS)


@bp.route('/openapi.json')
def openapi_json():
    """OpenAPI JSON规范"""
    return jsonify(API_DOCS)


@bp.route('/summary')
def api_summary():
    """API汇总信息"""
    endpoints = []
    for path, methods in API_DOCS['paths'].items():
        for method, details in methods.items():
            if method in ['get', 'post', 'put', 'delete', 'patch']:
                endpoints.append({
                    'method': method.upper(),
                    'path': path,
                    'summary': details.get('summary', ''),
                    'tag': details.get('tags', [''])[0]
                })

    return jsonify({
        'code': 0,
        'message': 'success',
        'data': {
            'title': API_DOCS['info']['title'],
            'version': API_DOCS['info']['version'],
            'total_endpoints': len(endpoints),
            'endpoints': endpoints
        }
    })
