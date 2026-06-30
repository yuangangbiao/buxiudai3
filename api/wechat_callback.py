# -*- coding: utf-8 -*-
"""
微信报工回调API服务

提供以下接口：
1. POST /api/wechat/report - 接收微信报工状态更新
2. GET /api/wechat/status/{order_no} - 查询订单报工状态
3. POST /api/wechat/batch - 批量更新报工状态
4. POST /api/wechat/operator - 更新操作员信息
"""

import json
import os
import sys
import threading
import time
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

try:
    from flask import Flask, request, jsonify, Response
    from core.cors_config import init_cors
except ImportError:
    # 如果Flask不可用，使用简单的HTTP服务器
    pass

from services.wechat_report_service import WeChatReportService
from services.schedule_dispatch_service import ScheduleDispatchService
from utils.op_logger import log_ui


class WeChatCallbackAPI:
    """微信报工回调API"""
    
    def __init__(self, host='0.0.0.0', port=5001):
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        init_cors(self.app)
        
        # 注册路由
        self._register_routes()
        
        # 服务器线程
        self.server_thread = None
        self.running = False
    
    def _register_routes(self):
        """注册API路由"""
        
        @self.app.route('/api/wechat/report', methods=['POST'])
        def handle_report():
            """处理微信报工状态更新"""
            try:
                data = request.get_json()
                
                if not data:
                    return jsonify({"success": False, "message": "请求体为空"}), 400
                
                log_ui("微信报工API", "收到回调", f"订单: {data.get('order_no', '未知')}")
                
                result = WeChatReportService.process_callback(data)
                
                if result['success']:
                    return jsonify(result), 200
                else:
                    return jsonify(result), 400
            
            except Exception as e:
                log_ui("微信报工API", "处理失败", str(e))
                return jsonify({"success": False, "message": f"服务器内部错误: {str(e)}"}), 500
        
        @self.app.route('/api/wechat/status/<order_no>', methods=['GET'])
        def get_status(order_no):
            """查询订单报工状态"""
            try:
                result = WeChatReportService.sync_report_status(order_no)
                
                if result['success']:
                    return jsonify(result), 200
                else:
                    return jsonify(result), 404
            
            except Exception as e:
                return jsonify({"success": False, "message": f"服务器内部错误: {str(e)}"}), 500
        
        @self.app.route('/api/wechat/batch', methods=['POST'])
        def batch_update():
            """批量更新报工状态"""
            try:
                data = request.get_json()
                
                if not data or not isinstance(data, list):
                    return jsonify({"success": False, "message": "请求体必须是数组"}), 400
                
                log_ui("微信报工API", "批量更新", f"数量: {len(data)}")
                
                result = WeChatReportService.batch_update_status(data)
                
                return jsonify(result), 200
            
            except Exception as e:
                return jsonify({"success": False, "message": f"服务器内部错误: {str(e)}"}), 500
        
        @self.app.route('/api/wechat/operator', methods=['POST'])
        def update_operator():
            """更新操作员信息"""
            try:
                data = request.get_json()
                
                required_fields = ['order_no', 'process_name', 'operator']
                missing_fields = [f for f in required_fields if f not in data]
                
                if missing_fields:
                    return jsonify({"success": False, "message": f"缺少必需字段: {','.join(missing_fields)}"}), 400
                
                result = WeChatReportService.update_operator(
                    data['order_no'],
                    data['process_name'],
                    data['operator']
                )
                
                if result['success']:
                    return jsonify(result), 200
                else:
                    return jsonify(result), 400
            
            except Exception as e:
                return jsonify({"success": False, "message": f"服务器内部错误: {str(e)}"}), 500
        
        @self.app.route('/api/wechat/schedule/confirm', methods=['POST'])
        def handle_schedule_confirm():
            """处理排产确认回调 - 企业微信操作员确认排产后，经容器中心回调"""
            try:
                data = request.get_json()

                if not data:
                    return jsonify({"success": False, "message": "请求体为空"}), 400

                log_ui("排产回调API", "收到排产确认", f"订单: {data.get('order_no', '未知')}")

                result = ScheduleDispatchService.handle_schedule_callback(data)

                if result['success']:
                    return jsonify(result), 200
                else:
                    return jsonify(result), 400

            except Exception as e:
                log_ui("排产回调API", "处理失败", str(e))
                return jsonify({"success": False, "message": f"服务器内部错误: {str(e)}"}), 500

        @self.app.route('/api/wechat/health', methods=['GET'])
        def health_check():
            """健康检查"""
            return jsonify({
                "success": True,
                "service": "wechat_report_callback",
                "timestamp": datetime.now().isoformat()
            }), 200
    
    def start(self):
        """启动API服务"""
        if self.running:
            log_ui("微信报工API", "服务已运行", f"端口: {self.port}")
            return
        
        log_ui("微信报工API", "启动服务", f"http://{self.host}:{self.port}")
        
        self.running = True
        self.server_thread = threading.Thread(
            target=self.app.run,
            kwargs={
                'host': self.host,
                'port': self.port,
                'debug': False,
                'use_reloader': False
            },
            daemon=True
        )
        self.server_thread.start()
    
    def stop(self):
        """停止API服务"""
        if self.running:
            self.running = False
            log_ui("微信报工API", "停止服务", "")


# 全局API实例
_api_instance = None


def get_api_instance(host='0.0.0.0', port=5001):
    """获取API实例"""
    global _api_instance
    if _api_instance is None:
        _api_instance = WeChatCallbackAPI(host, port)
    return _api_instance


def start_wechat_api(host='0.0.0.0', port=5001):
    """启动微信报工API服务"""
    api = get_api_instance(host, port)
    api.start()
    return api


if __name__ == '__main__':
    # 独立运行时
    api = WeChatCallbackAPI(host='0.0.0.0', port=5001)
    api.start()
    
    # 保持运行
    while True:
        time.sleep(1)