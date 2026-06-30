# -*- coding: utf-8 -*-
"""
微信报工回调API测试脚本
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import threading
import time
import requests


def test_api():
    """测试微信报工回调API"""
    base_url = "http://localhost:5001"
    
    print("=" * 60)
    print("微信报工回调API测试")
    print("=" * 60)
    
    # 测试健康检查
    print("\n1. 测试健康检查接口...")
    try:
        response = requests.get(f"{base_url}/api/wechat/health")
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.text}")
        if response.status_code == 200:
            print("   ✓ 健康检查通过")
        else:
            print("   ✗ 健康检查失败")
    except Exception as e:
        print(f"   ✗ 连接失败: {e}")
    
    # 测试状态查询接口
    print("\n2. 测试状态查询接口...")
    try:
        response = requests.get(f"{base_url}/api/wechat/status/TEST001")
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.text}")
    except Exception as e:
        print(f"   ✗ 连接失败: {e}")
    
    # 测试报工回调接口
    print("\n3. 测试报工回调接口...")
    test_data = {
        "order_no": "TEST001",
        "work_order_no": "WO2024001",
        "process_name": "编织",
        "status": "completed",
        "operator": "张三",
        "remarks": "测试报工"
    }
    try:
        response = requests.post(
            f"{base_url}/api/wechat/report",
            json=test_data
        )
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.text}")
    except Exception as e:
        print(f"   ✗ 连接失败: {e}")
    
    # 测试批量更新接口
    print("\n4. 测试批量更新接口...")
    batch_data = [
        {
            "order_no": "TEST002",
            "work_order_no": "WO2024002",
            "process_name": "焊接",
            "status": "completed",
            "operator": "李四"
        }
    ]
    try:
        response = requests.post(
            f"{base_url}/api/wechat/batch",
            json=batch_data
        )
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.text}")
    except Exception as e:
        print(f"   ✗ 连接失败: {e}")
    
    # 测试操作员更新接口
    print("\n5. 测试操作员更新接口...")
    operator_data = {
        "order_no": "TEST001",
        "process_name": "编织",
        "operator": "王五"
    }
    try:
        response = requests.post(
            f"{base_url}/api/wechat/operator",
            json=operator_data
        )
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.text}")
    except Exception as e:
        print(f"   ✗ 连接失败: {e}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    # 启动API服务
    print("启动微信报工API服务...")
    from api.wechat_callback import start_wechat_api
    api = start_wechat_api()
    
    # 等待服务启动
    time.sleep(2)
    
    # 执行测试
    test_api()