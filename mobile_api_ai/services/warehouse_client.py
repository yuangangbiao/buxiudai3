# -*- coding: utf-8 -*-
"""
仓库管理系统客户端

对接仓库管理软件（WMS）查询库存
支持库存检查、物料需求提交等操作
"""
import os
import logging
import requests
from typing import Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class WarehouseClient:
    """
    仓库管理系统客户端

    通过HTTP接口对接仓库管理软件
    环境变量配置：
    - WAREHOUSE_API_URL: 仓库API地址，如 http://192.168.1.100:8080/api
    - WAREHOUSE_API_KEY: API密钥（可选）
    - WAREHOUSE_TIMEOUT: 请求超时时间，默认10秒
    """

    def __init__(self):
        self._api_url = os.getenv('WAREHOUSE_API_URL', '').rstrip('/')
        self._api_key = os.getenv('WAREHOUSE_API_KEY', '')
        self._timeout = float(os.getenv('WAREHOUSE_TIMEOUT', '10'))
        self._enabled = bool(self._api_url)

    def is_enabled(self) -> bool:
        """检查仓库接口是否已配置"""
        return self._enabled

    def _get_headers(self) -> Dict:
        """构建请求头"""
        headers = {'Content-Type': 'application/json'}
        if self._api_key:
            headers['Authorization'] = f'Bearer {self._api_key}'
        return headers

    def check_stock(self, material_name: str, required_qty: float,
                    unit: str = '件') -> Dict:
        """
        检查物料库存是否充足

        Args:
            material_name: 物料名称
            required_qty: 需求数量
            unit: 单位

        Returns:
            {
                'sufficient': True/False,
                'current_stock': 当前库存,
                'required': 需求数量,
                'shortage': 缺少数量（库存不足时）,
                'message': 说明信息
            }
        """
        if not self._enabled:
            logger.warning('[WarehouseClient] 仓库接口未配置，物料默认为0，需人工填写')
            return {
                'sufficient': False,
                'current_stock': 0,
                'required': required_qty,
                'shortage': required_qty,
                'message': '仓库接口未配置，物料默认为0，需人工填写',
                'warehouse_available': False
            }

        try:
            response = requests.post(
                f'{self._api_url}/stock/check',
                json={
                    'material_name': material_name,
                    'required_qty': required_qty,
                    'unit': unit
                },
                headers=self._get_headers(),
                timeout=self._timeout
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(f"[WarehouseClient] 库存检查: {material_name} 需求{required_qty} {unit}, 库存{result.get('current_stock', 0)}, 充足={result.get('sufficient', False)}")
                return {
                    'sufficient': result.get('sufficient', False),
                    'current_stock': result.get('current_stock', 0),
                    'required': required_qty,
                    'shortage': result.get('shortage', 0) if not result.get('sufficient') else 0,
                    'message': result.get('message', ''),
                    'warehouse_available': True
                }
            else:
                logger.error(f'[WarehouseClient] 库存检查失败: HTTP {response.status_code}')
                return {
                    'sufficient': False,
                    'current_stock': 0,
                    'required': required_qty,
                    'shortage': required_qty,
                    'message': f'仓库查询失败(HTTP {response.status_code})，物料默认为0，需人工填写',
                    'warehouse_available': False
                }

        except requests.exceptions.Timeout:
            logger.error('[WarehouseClient] 库存检查超时')
            return {
                'sufficient': False,
                'current_stock': 0,
                'required': required_qty,
                'shortage': required_qty,
                'message': '仓库查询超时，物料默认为0，需人工填写',
                'warehouse_available': False
            }
        except requests.exceptions.ConnectionError:
            logger.error(f'[WarehouseClient] 无法连接仓库服务: {self._api_url}')
            return {
                'sufficient': False,
                'current_stock': 0,
                'required': required_qty,
                'shortage': required_qty,
                'message': f'无法连接仓库服务，物料默认为0，需人工填写',
                'warehouse_available': False
            }
        except Exception as e:
            logger.error(f'[WarehouseClient] 库存检查异常: {e}')
            return {
                'sufficient': False,
                'current_stock': 0,
                'required': required_qty,
                'shortage': required_qty,
                'message': f'仓库查询异常: {e}，物料默认为0，需人工填写',
                'warehouse_available': False
            }

    def submit_material_request(self, order_no: str, material_name: str,
                               quantity: float, unit: str = '件',
                               purpose: str = '') -> Dict:
        """
        向仓库提交物料领用请求

        Args:
            order_no: 订单号
            material_name: 物料名称
            quantity: 数量
            unit: 单位
            purpose: 用途说明

        Returns:
            {
                'success': True/False,
                'request_id': 请求ID,
                'message': 说明信息
            }
        """
        if not self._enabled:
            return {
                'success': False,
                'request_id': None,
                'message': '仓库接口未配置，无法提交物料请求'
            }

        try:
            response = requests.post(
                f'{self._api_url}/material/request',
                json={
                    'order_no': order_no,
                    'material_name': material_name,
                    'quantity': quantity,
                    'unit': unit,
                    'purpose': purpose
                },
                headers=self._get_headers(),
                timeout=self._timeout
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(f"[WarehouseClient] 物料请求提交成功: {material_name} x{quantity} -> {order_no}")
                return {
                    'success': True,
                    'request_id': result.get('request_id'),
                    'message': '物料请求已提交'
                }
            else:
                logger.error(f'[WarehouseClient] 物料请求提交失败: HTTP {response.status_code}')
                return {
                    'success': False,
                    'request_id': None,
                    'message': f'物料请求提交失败(HTTP {response.status_code})'
                }

        except Exception as e:
            logger.error(f'[WarehouseClient] 物料请求提交异常: {e}')
            return {
                'success': False,
                'request_id': None,
                'message': f'物料请求提交异常: {e}'
            }


_warehouse_client_instance: Optional[WarehouseClient] = None


def get_warehouse_client() -> WarehouseClient:
    """获取仓库客户端单例"""
    global _warehouse_client_instance
    if _warehouse_client_instance is None:
        _warehouse_client_instance = WarehouseClient()
    return _warehouse_client_instance
