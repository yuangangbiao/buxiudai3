# -*- coding: utf-8 -*-
"""
数据收集API模块
提供外部系统推送数据的统一入口
支持多种数据类型：报工、质检、领料、审批等
"""
import logging
from flask import Blueprint, jsonify, request
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)
import uuid
import json

data_collector_bp = Blueprint('data_collector', __name__, url_prefix='/api/collector')

def get_container_center():
    """获取容器中心实例"""
    try:
        from wechat_server import container_center as cc
        return cc
    except ImportError as e:
        logger.error(f"无法导入容器中心实例: {e}")
        return None

def get_container_integration():
    """获取容器集成实例（已废弃，始终返回 None）"""
    return None

def get_storage():
    """获取存储实例"""
    cc = get_container_center()
    if cc:
        return cc.storage
    return None

def validate_required_fields(data: Dict, required_fields: List[str]) -> tuple:
    """验证必填字段"""
    missing = [f for f in required_fields if not data.get(f)]
    if missing:
        return False, f"缺少必填字段: {', '.join(missing)}"
    return True, None

def generate_collect_id(prefix: str = 'COL') -> str:
    """生成收集记录ID"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    unique = str(uuid.uuid4())[:4].upper()
    return f"{prefix}-{timestamp}-{unique}"

def save_collection_record(data: Dict, data_type: str, title: str = None, package_id: str = None, status: str = 'collected', error: str = None):
    """保存收集记录到数据库"""
    try:
        storage = get_storage()
        if not storage:
            return False

        record = {
            'collect_id': data.get('_collect_id'),
            'data_type': data_type,
            'title': title or data.get('title', f'{data_type}数据'),
            'source': data.get('source', 'api'),
            'raw_data': data,
            'order_no': data.get('order_no'),
            'process_name': data.get('process_name'),
            'operator_id': data.get('operator_id'),
            'package_id': package_id,
            'status': status,
            'collected_at': datetime.now().isoformat(),
            'error_message': error
        }

        if data.get('_collect_id'):
            storage.save_collection_record(record)
        return True
    except Exception as e:
        logger.error(f"[Collector] 保存收集记录失败: {e}")
        return False

@data_collector_bp.route('/collect', methods=['POST'])
def api_collect():
    """
    通用数据收集接口
    支持所有数据类型

    请求体:
    {
        "data_type": "report|quality|material|approval|order|custom",
        "title": "标题",
        "content": {...},
        "order_no": "订单号",
        "process_name": "工序名称",
        "operator_id": "操作员ID",
        "source": "数据来源",
        "priority": "normal|high|low",
        "tags": ["标签1", "标签2"],
        "metadata": {...}
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 400, 'message': '请求体不能为空'}), 400

        data_type = data.get('data_type')
        if not data_type:
            return jsonify({'code': 400, 'message': 'data_type不能为空'}), 400

        valid_types = ['report', 'quality', 'material', 'approval', 'order', 'process', 'custom']
        if data_type not in valid_types:
            return jsonify({'code': 400, 'message': f'data_type必须是: {", ".join(valid_types)}'}), 400

        collect_id = generate_collect_id(data_type.upper()[:3].replace('CUSTOM', 'CUS'))
        data['_collect_id'] = collect_id

        container_center = get_container_center()
        if not container_center:
            return jsonify({'code': 500, 'message': '容器中心未初始化'}), 500

        content = data.get('content', {})
        content['_source'] = data.get('source', 'api')
        content['_collected_at'] = datetime.now().isoformat()
        if data.get('metadata'):
            content['_metadata'] = data.get('metadata')

        pkg = None
        if data_type == 'report':
            pkg = container_center.collect_report(
                order_no=data.get('order_no', ''),
                process_name=data.get('process_name', ''),
                record_id=data.get('record_id', int(datetime.now().timestamp())),
                operator_id=data.get('operator_id', 'OP001'),
                planned_qty=content.get('planned_qty', 0),
                source=data.get('source', 'api')
            )
        elif data_type == 'quality':
            pkg = container_center.collect_quality(
                order_no=data.get('order_no', ''),
                order_id=content.get('order_id', 0),
                inspector_id=data.get('operator_id', 'OP001'),
                inspection_type=content.get('inspection_type', '常规'),
                source=data.get('source', 'api')
            )
        elif data_type == 'material':
            pkg = container_center.collect_material(
                order_no=data.get('order_no', ''),
                material_name=content.get('material_name', ''),
                quantity=content.get('quantity', 0),
                operator_id=data.get('operator_id', 'OP001'),
                unit=content.get('unit', '件'),
                source=data.get('source', 'api')
            )
        elif data_type == 'approval':
            pkg = container_center.collect_approval(
                order_no=data.get('order_no', ''),
                approval_id=content.get('approval_id', 0),
                approver_id=data.get('operator_id', 'OP001'),
                reason=content.get('reason', ''),
                source=data.get('source', 'api')
            )
        else:
            from container_center_v5 import DataPackage
            pkg = DataPackage(
                data_type=data_type,
                title=data.get('title', f'{data_type}数据'),
                content=content,
                source=data.get('source', 'api'),
                priority=data.get('priority', 'normal')
            )
            pkg.related_order = data.get('order_no')
            pkg.related_process = data.get('process_name')
            pkg.target_operator = data.get('operator_id')
            pkg.tags = data.get('tags', [])
            container_center.storage.save_package(pkg.to_dict())
            container_center.storage.log_sync('API_COLLECT', pkg.id, f'API收集{data_type}数据')

        if pkg and data.get('auto_distribute', True):
            container_center.distributor.distribute(pkg.id, data.get('operator_id'))

        save_collection_record(data, data_type, package_id=pkg.id if pkg else None, status='processed')

        return jsonify({
            'code': 0,
            'message': '数据收集成功',
            'data': {
                'collect_id': collect_id,
                'package_id': pkg.id if pkg else None,
                'data_type': data_type,
                'order_no': data.get('order_no'),
                'process_name': data.get('process_name'),
                'operator_id': data.get('operator_id'),
                'status': 'distributed' if data.get('auto_distribute', True) else 'pending',
                'collected_at': datetime.now().isoformat()
            }
        })

    except Exception as e:
        save_collection_record(data, data_type, status='failed', error=str(e))
        return jsonify({'code': 500, 'message': str(e)}), 500

@data_collector_bp.route('/collect/report', methods=['POST'])
def api_collect_report():
    """
    报工数据收集接口

    请求体:
    {
        "order_no": "订单号",
        "process_name": "工序名称",
        "operator_id": "操作员ID",
        "planned_qty": 100,
        "actual_qty": 95,
        "qualified_qty": 92,
        "work_hours": 8.5,
        "source": "MES系统",
        "record_id": 12345,
        "auto_distribute": true
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 400, 'message': '请求体不能为空'}), 400

        required = ['order_no', 'process_name']
        valid, msg = validate_required_fields(data, required)
        if not valid:
            return jsonify({'code': 400, 'message': msg}), 400

        collect_id = generate_collect_id('RPT')
        data['_collect_id'] = collect_id

        container_center = get_container_center()
        if not container_center:
            return jsonify({'code': 500, 'message': '容器中心未初始化'}), 500

        content = {
            'record_id': data.get('record_id', int(datetime.now().timestamp())),
            'planned_qty': data.get('planned_qty', 0),
            'actual_qty': data.get('actual_qty', 0),
            'qualified_qty': data.get('qualified_qty', 0),
            'work_hours': data.get('work_hours', 0),
            'order_no': data.get('order_no'),
            'process_name': data.get('process_name'),
            '_source': data.get('source', 'api'),
            '_collected_at': datetime.now().isoformat()
        }

        pkg = container_center.collect_report(
            order_no=data['order_no'],
            process_name=data['process_name'],
            record_id=content['record_id'],
            operator_id=data.get('operator_id', 'OP001'),
            planned_qty=data.get('planned_qty', 0),
            source=data.get('source', 'api')
        )

        pkg.content.update(content)
        container_center.storage.save_package(pkg.to_dict())

        if data.get('auto_distribute', True):
            container_center.distributor.distribute(pkg.id, data.get('operator_id'))

        save_collection_record(data, 'report', package_id=pkg.id, status='processed')

        return jsonify({
            'code': 0,
            'message': '报工数据收集成功',
            'data': {
                'collect_id': collect_id,
                'package_id': pkg.id,
                'order_no': data['order_no'],
                'process_name': data['process_name'],
                'status': 'distributed' if data.get('auto_distribute', True) else 'pending'
            }
        })

    except Exception as e:
        save_collection_record(data, 'report', status='failed', error=str(e))
        return jsonify({'code': 500, 'message': str(e)}), 500

@data_collector_bp.route('/collect/quality', methods=['POST'])
def api_collect_quality():
    """
    质检数据收集接口

    请求体:
    {
        "order_no": "订单号",
        "order_id": 123,
        "inspector_id": "操作员ID",
        "inspection_type": "巡检",
        "inspection_result": "合格",
        "defect_count": 0,
        "source": "QMS系统",
        "auto_distribute": true
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 400, 'message': '请求体不能为空'}), 400

        collect_id = generate_collect_id('QLT')
        data['_collect_id'] = collect_id

        container_center = get_container_center()
        if not container_center:
            return jsonify({'code': 500, 'message': '容器中心未初始化'}), 500

        pkg = container_center.collect_quality(
            order_no=data.get('order_no', ''),
            order_id=data.get('order_id', 0),
            inspector_id=data.get('inspector_id', 'OP001'),
            inspection_type=data.get('inspection_type', '常规'),
            source=data.get('source', 'api')
        )

        if data.get('content'):
            pkg.content.update(data.get('content'))

        container_center.storage.save_package(pkg.to_dict())

        if data.get('auto_distribute', True):
            container_center.distributor.distribute(pkg.id, data.get('inspector_id'))

        save_collection_record(data, 'quality', package_id=pkg.id, status='processed')

        return jsonify({
            'code': 0,
            'message': '质检数据收集成功',
            'data': {
                'collect_id': collect_id,
                'package_id': pkg.id,
                'order_no': data.get('order_no'),
                'inspection_type': data.get('inspection_type')
            }
        })

    except Exception as e:
        save_collection_record(data, 'quality', status='failed', error=str(e))
        return jsonify({'code': 500, 'message': str(e)}), 500

@data_collector_bp.route('/collect/material', methods=['POST'])
def api_collect_material():
    """
    领料数据收集接口

    请求体:
    {
        "order_no": "订单号",
        "material_name": "不锈钢丝",
        "quantity": 100,
        "unit": "kg",
        "operator_id": "操作员ID",
        "source": "WMS系统",
        "auto_distribute": true
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 400, 'message': '请求体不能为空'}), 400

        required = ['order_no', 'material_name', 'quantity']
        valid, msg = validate_required_fields(data, required)
        if not valid:
            return jsonify({'code': 400, 'message': msg}), 400

        collect_id = generate_collect_id('MAT')
        data['_collect_id'] = collect_id

        container_center = get_container_center()
        if not container_center:
            return jsonify({'code': 500, 'message': '容器中心未初始化'}), 500

        pkg = container_center.collect_material(
            order_no=data['order_no'],
            material_name=data['material_name'],
            quantity=data['quantity'],
            operator_id=data.get('operator_id', 'OP001'),
            unit=data.get('unit', '件'),
            source=data.get('source', 'api')
        )

        if data.get('auto_distribute', True):
            container_center.distributor.distribute(pkg.id, data.get('operator_id'))

        save_collection_record(data, 'material', package_id=pkg.id, status='processed')

        return jsonify({
            'code': 0,
            'message': '领料数据收集成功',
            'data': {
                'collect_id': collect_id,
                'package_id': pkg.id,
                'order_no': data['order_no'],
                'material_name': data['material_name']
            }
        })

    except Exception as e:
        save_collection_record(data, 'material', status='failed', error=str(e))
        return jsonify({'code': 500, 'message': str(e)}), 500

@data_collector_bp.route('/collect/approval', methods=['POST'])
def api_collect_approval():
    """
    审批数据收集接口

    请求体:
    {
        "order_no": "订单号",
        "approval_id": 123,
        "approver_id": "操作员ID",
        "reason": "审批原因",
        "source": "OA系统",
        "auto_distribute": true
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 400, 'message': '请求体不能为空'}), 400

        collect_id = generate_collect_id('APR')
        data['_collect_id'] = collect_id

        container_center = get_container_center()
        if not container_center:
            return jsonify({'code': 500, 'message': '容器中心未初始化'}), 500

        pkg = container_center.collect_approval(
            order_no=data.get('order_no', ''),
            approval_id=data.get('approval_id', 0),
            approver_id=data.get('approver_id', 'OP001'),
            reason=data.get('reason', ''),
            source=data.get('source', 'api')
        )

        if data.get('auto_distribute', True):
            container_center.distributor.distribute(pkg.id, data.get('approver_id'))

        save_collection_record(data, 'approval', package_id=pkg.id, status='processed')

        return jsonify({
            'code': 0,
            'message': '审批数据收集成功',
            'data': {
                'collect_id': collect_id,
                'package_id': pkg.id,
                'order_no': data.get('order_no'),
                'approval_id': data.get('approval_id')
            }
        })

    except Exception as e:
        save_collection_record(data, 'approval', status='failed', error=str(e))
        return jsonify({'code': 500, 'message': str(e)}), 500

@data_collector_bp.route('/collect/batch', methods=['POST'])
def api_collect_batch():
    """
    批量数据收集接口

    请求体:
    {
        "items": [
            {"data_type": "report", "order_no": "A001", ...},
            {"data_type": "quality", "order_no": "A001", ...}
        ],
        "auto_distribute": true
    }
    """
    try:
        data = request.get_json()
        if not data or not data.get('items'):
            return jsonify({'code': 400, 'message': 'items不能为空'}), 400

        items = data.get('items')
        if not isinstance(items, list):
            return jsonify({'code': 400, 'message': 'items必须是数组'}), 400

        collect_id = generate_collect_id('BAT')
        data['_collect_id'] = collect_id

        container_center = get_container_center()
        if not container_center:
            return jsonify({'code': 500, 'message': '容器中心未初始化'}), 500

        results = []
        for idx, item in enumerate(items):
            try:
                item['_collect_id'] = generate_collect_id('ITM')
                item['_batch_id'] = collect_id
                item['auto_distribute'] = data.get('auto_distribute', True)
                item['source'] = item.get('source', 'batch_api')
                results.append({'index': idx, 'status': 'pending'})
            except Exception as e:
                results.append({'index': idx, 'status': 'error', 'message': str(e)})

        for idx, item in enumerate(items):
            try:
                pkg = None
                data_type = item.get('data_type')

                if data_type == 'report':
                    pkg = container_center.collect_report(
                        order_no=item.get('order_no', ''),
                        process_name=item.get('process_name', ''),
                        record_id=item.get('record_id', int(datetime.now().timestamp())),
                        operator_id=item.get('operator_id', 'OP001'),
                        planned_qty=item.get('planned_qty', 0),
                        source=item.get('source', 'batch_api')
                    )
                elif data_type == 'quality':
                    pkg = container_center.collect_quality(
                        order_no=item.get('order_no', ''),
                        order_id=item.get('order_id', 0),
                        inspector_id=item.get('inspector_id', 'OP001'),
                        inspection_type=item.get('inspection_type', '常规'),
                        source=item.get('source', 'batch_api')
                    )
                elif data_type == 'material':
                    pkg = container_center.collect_material(
                        order_no=item.get('order_no', ''),
                        material_name=item.get('material_name', ''),
                        quantity=item.get('quantity', 0),
                        operator_id=item.get('operator_id', 'OP001'),
                        unit=item.get('unit', '件'),
                        source=item.get('source', 'batch_api')
                    )
                elif data_type == 'approval':
                    pkg = container_center.collect_approval(
                        order_no=item.get('order_no', ''),
                        approval_id=item.get('approval_id', 0),
                        approver_id=item.get('approver_id', 'OP001'),
                        reason=item.get('reason', ''),
                        source=item.get('source', 'batch_api')
                    )
                else:
                    from container_center_v5 import DataPackage
                    pkg = DataPackage(
                        data_type=data_type or 'custom',
                        title=item.get('title', '批量数据'),
                        content=item.get('content', {}),
                        source=item.get('source', 'batch_api')
                    )
                    container_center.storage.save_package(pkg.to_dict())

                if pkg and item.get('auto_distribute', True):
                    container_center.distributor.distribute(pkg.id, item.get('operator_id'))

                save_collection_record(item, data_type or 'custom', package_id=pkg.id if pkg else None, status='processed')

                results[idx] = {
                    'index': idx,
                    'status': 'success',
                    'collect_id': item.get('_collect_id'),
                    'package_id': pkg.id if pkg else None,
                    'data_type': data_type
                }
            except Exception as e:
                save_collection_record(item, item.get('data_type', 'custom'), status='failed', error=str(e))
                results[idx] = {'index': idx, 'status': 'error', 'message': str(e)}

        success_count = len([r for r in results if r.get('status') == 'success'])

        save_collection_record({
            '_collect_id': collect_id,
            'batch_items': len(items),
            'success_count': success_count
        }, 'batch', title=f'批量收集{len(items)}条', status='processed')

        return jsonify({
            'code': 0,
            'message': f'批量收集完成，成功{success_count}/{len(items)}条',
            'data': {
                'collect_id': collect_id,
                'total': len(items),
                'success': success_count,
                'failed': len(items) - success_count,
                'results': results
            }
        })

    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)}), 500

@data_collector_bp.route('/collect/custom', methods=['POST'])
def api_collect_custom():
    """
    自定义数据收集接口

    请求体:
    {
        "title": "自定义标题",
        "content": {"key1": "value1", "key2": "value2"},
        "data_type": "custom",
        "order_no": "订单号",
        "process_name": "工序",
        "operator_id": "操作员ID",
        "source": "自定义来源",
        "priority": "normal|high|low",
        "tags": ["标签1", "标签2"],
        "auto_distribute": true
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 400, 'message': '请求体不能为空'}), 400

        collect_id = generate_collect_id('CUS')
        data['_collect_id'] = collect_id

        container_center = get_container_center()
        if not container_center:
            return jsonify({'code': 500, 'message': '容器中心未初始化'}), 500

        from container_center_v5 import DataPackage
        pkg = DataPackage(
            data_type='custom',
            title=data.get('title', '自定义数据'),
            content=data.get('content', {}),
            source=data.get('source', 'custom_api'),
            priority=data.get('priority', 'normal')
        )

        pkg.related_order = data.get('order_no')
        pkg.related_process = data.get('process_name')
        pkg.target_operator = data.get('operator_id')
        pkg.tags = data.get('tags', [])

        container_center.storage.save_package(pkg.to_dict())
        container_center.storage.log_sync('CUSTOM_COLLECT', pkg.id, f'自定义数据收集: {data.get("title")}')

        if data.get('auto_distribute', True):
            container_center.distributor.distribute(pkg.id, data.get('operator_id'))

        save_collection_record(data, 'custom', title=data.get('title'), package_id=pkg.id, status='processed')

        return jsonify({
            'code': 0,
            'message': '自定义数据收集成功',
            'data': {
                'collect_id': collect_id,
                'package_id': pkg.id,
                'title': data.get('title'),
                'status': 'distributed' if data.get('auto_distribute', True) else 'pending'
            }
        })

    except Exception as e:
        save_collection_record(data, 'custom', status='failed', error=str(e))
        return jsonify({'code': 500, 'message': str(e)}), 500

@data_collector_bp.route('/records', methods=['GET'])
def api_get_collection_records():
    """
    获取收集记录列表

    查询参数:
    - data_type: 数据类型筛选
    - status: 状态筛选 (collected/processed/failed)
    - order_no: 订单号筛选
    - limit: 返回数量限制 (默认100)
    """
    try:
        data_type = request.args.get('data_type')
        status = request.args.get('status')
        order_no = request.args.get('order_no')
        limit = int(request.args.get('limit', 100))

        storage = get_storage()
        if not storage:
            return jsonify({'code': 500, 'message': '存储未初始化'}), 500

        records = storage.get_collection_records(
            data_type=data_type,
            status=status,
            order_no=order_no,
            limit=limit
        )

        return jsonify({
            'code': 0,
            'data': {
                'total': len(records),
                'records': records
            }
        })

    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)}), 500

@data_collector_bp.route('/records/all', methods=['GET'])
def api_get_all_collection_records():
    """获取所有收集记录"""
    try:
        storage = get_storage()
        if not storage:
            return jsonify({'code': 500, 'message': '存储未初始化'}), 500

        records = storage.get_all_collection_records()

        return jsonify({
            'code': 0,
            'data': {
                'total': len(records),
                'records': records
            }
        })

    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)}), 500

@data_collector_bp.route('/records/<collect_id>', methods=['GET'])
def api_get_collection_record(collect_id):
    """获取指定收集记录"""
    try:
        storage = get_storage()
        if not storage:
            return jsonify({'code': 500, 'message': '存储未初始化'}), 500

        record = storage.get_collection_record(collect_id)
        if not record:
            return jsonify({'code': 404, 'message': f'收集记录不存在: {collect_id}'}), 404

        return jsonify({
            'code': 0,
            'data': record
        })

    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)}), 500

@data_collector_bp.route('/schema/<data_type>', methods=['GET'])
def api_get_schema(data_type):
    """
    获取数据类型的接口schema

    URL参数:
    - data_type: report|quality|material|approval|custom
    """
    schemas = {
        'report': {
            'name': '报工数据',
            'required': ['order_no', 'process_name'],
            'optional': ['operator_id', 'planned_qty', 'actual_qty', 'qualified_qty', 'work_hours', 'record_id', 'source', 'auto_distribute'],
            'example': {
                'order_no': 'ORD-2024-001',
                'process_name': '编织',
                'operator_id': 'OP001',
                'planned_qty': 100,
                'actual_qty': 95,
                'qualified_qty': 92,
                'work_hours': 8.5,
                'source': 'MES系统'
            }
        },
        'quality': {
            'name': '质检数据',
            'required': [],
            'optional': ['order_no', 'order_id', 'inspector_id', 'inspection_type', 'inspection_result', 'defect_count', 'source', 'auto_distribute'],
            'example': {
                'order_no': 'ORD-2024-001',
                'inspector_id': 'OP002',
                'inspection_type': '巡检',
                'inspection_result': '合格',
                'source': 'QMS系统'
            }
        },
        'material': {
            'name': '领料数据',
            'required': ['order_no', 'material_name', 'quantity'],
            'optional': ['operator_id', 'unit', 'source', 'auto_distribute'],
            'example': {
                'order_no': 'ORD-2024-001',
                'material_name': '不锈钢丝',
                'quantity': 100,
                'unit': 'kg',
                'operator_id': 'OP003',
                'source': 'WMS系统'
            }
        },
        'approval': {
            'name': '审批数据',
            'required': [],
            'optional': ['order_no', 'approval_id', 'approver_id', 'reason', 'source', 'auto_distribute'],
            'example': {
                'order_no': 'ORD-2024-001',
                'approval_id': 12345,
                'approver_id': 'OP004',
                'reason': '订单超期申请',
                'source': 'OA系统'
            }
        },
        'custom': {
            'name': '自定义数据',
            'required': ['title', 'content'],
            'optional': ['order_no', 'process_name', 'operator_id', 'source', 'priority', 'tags', 'auto_distribute'],
            'example': {
                'title': '自定义任务',
                'content': {'key1': 'value1', 'key2': 'value2'},
                'order_no': 'ORD-2024-001',
                'operator_id': 'OP001',
                'source': '自定义系统',
                'priority': 'normal',
                'tags': ['标签1', '标签2']
            }
        }
    }

    if data_type not in schemas:
        return jsonify({'code': 404, 'message': f'未知的数据类型: {data_type}'}), 404

    return jsonify({
        'code': 0,
        'data': schemas.get(data_type)
    })

@data_collector_bp.route('/health', methods=['GET'])
def api_collector_health():
    """收集服务健康检查"""
    try:
        container_center = get_container_center()
        if not container_center:
            return jsonify({
                'code': 500,
                'message': '容器中心未初始化',
                'status': 'unhealthy'
            }), 500

        storage_health = container_center.storage.health_check()

        return jsonify({
            'code': 0,
            'status': 'healthy',
            'collector_version': '1.0',
            'container_center': storage_health.get('status', 'unknown'),
            'total_collection_records': storage_health.get('total_collection_records', 0),
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({'code': 500, 'message': str(e), 'status': 'error'}), 500
