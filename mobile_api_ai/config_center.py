# -*- coding: utf-8 -*-
"""
可视化配置中心 - 根级业务配置管理

职责：管理所有外部接口、系统参数、业务配置，提供 RESTful API + 前端页面
存储方式：JSON 文件 + .env 文件
路由前缀：/api/config-center
与 container_center 配置模块的关系：
  - 本模块 = 根级配置管理（JSON + .env 存储，含前端 UI）
  - container_center 配置模块 = 子系统配置管理（SQLite 存储，纯 API）
  - 两者互补，覆盖不同存储场景
"""
import os
import json
import logging
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime
from flask import Blueprint, jsonify, request, render_template
from core.config import REQUEST_TIMEOUT_FAST, REQUEST_TIMEOUT_NORMAL
from dotenv import set_key

logger = logging.getLogger(__name__)

config_center_bp = Blueprint('config_center', __name__, url_prefix='/api/config-center')

_DEFAULT_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config_center_data.json')
CONFIG_FILE = os.getenv('CONFIG_CENTER_DATA_PATH', _DEFAULT_CONFIG_FILE)
ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')

def _load_json_config() -> Dict:
    """从JSON文件加载配置"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
    return {}

def _save_json_config(config: Dict):
    """保存配置到JSON文件"""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def _read_env_file() -> Dict[str, str]:
    """读取.env文件全部内容"""
    env_vars = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    env_vars[key.strip()] = value.strip()
    return env_vars

def _update_env_var(key: str, value: str):
    """更新.env文件中的单个变量"""
    try:
        set_key(ENV_FILE, key, value)
        os.environ[key] = value
        logger.info(f"[配置中心] 更新环境变量: {key}={value[:20]}...")
        return True
    except Exception as e:
        logger.error(f"[配置中心] 更新环境变量失败: {key} - {e}")
        return False

def _update_env_file(vars_dict: Dict[str, str]):
    """批量更新.env文件"""
    success_count = 0
    for key, value in vars_dict.items():
        if _update_env_var(key, value):
            success_count += 1
    return success_count

CONFIG_SCHEMA = {
    'wechat': {
        'label': '微信配置',
        'icon': '💬',
        'fields': [
            {'key': 'WECHAT_WORK_BOT_URL', 'label': '群机器人Webhook', 'type': 'text', 'placeholder': 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=...', 'sensitive': False},
            {'key': 'WECHAT_CORP_ID', 'label': '企业ID', 'type': 'text', 'placeholder': 'ww...', 'sensitive': False},
            {'key': 'WECHAT_AGENT_ID', 'label': '应用AgentID', 'type': 'text', 'placeholder': '1000001', 'sensitive': False},
            {'key': 'WECHAT_SECRET', 'label': '应用Secret', 'type': 'password', 'placeholder': '', 'sensitive': True},
            {'key': 'WECHAT_TOKEN', 'label': '回调Token', 'type': 'password', 'placeholder': '', 'sensitive': True},
            {'key': 'WECHAT_AES_KEY', 'label': '回调AES密钥', 'type': 'password', 'placeholder': '', 'sensitive': True},
        ]
    },
    'notification': {
        'label': '通知开关',
        'icon': '🔔',
        'fields': [
            {'key': 'ENABLE_WECHAT_NOTIFY', 'label': '启用微信通知', 'type': 'boolean', 'default': 'true'},
            {'key': 'NOTIFY_ON_TASK_ASSIGNED', 'label': '任务分配通知', 'type': 'boolean', 'default': 'true'},
            {'key': 'NOTIFY_ON_TASK_COMPLETED', 'label': '任务完成通知', 'type': 'boolean', 'default': 'true'},
            {'key': 'NOTIFY_ON_LOW_STOCK', 'label': '库存预警通知', 'type': 'boolean', 'default': 'false'},
        ]
    },
    'server': {
        'label': '服务器配置',
        'icon': '🖥️',
        'fields': [
            {'key': 'FLASK_HOST', 'label': '监听地址', 'type': 'text', 'default': '0.0.0.0'},
            {'key': 'FLASK_PORT', 'label': '主服务端口', 'type': 'number', 'default': '5003'},
            {'key': 'WECHAT_BOT_PORT', 'label': '机器人端口', 'type': 'number', 'default': '5003'},
            {'key': 'CONTAINER_CENTER_PORT', 'label': '容器中心端口', 'type': 'number', 'default': '5002'},
            {'key': 'FLASK_DEBUG', 'label': '调试模式', 'type': 'boolean', 'default': 'false'},
        ]
    },
    'database': {
        'label': '数据库配置',
        'icon': '🗄️',
        'fields': [
            {'key': 'MYSQL_HOST', 'label': '数据库地址', 'type': 'text', 'placeholder': 'localhost'},
            {'key': 'MYSQL_PORT', 'label': '端口', 'type': 'number', 'default': '3306'},
            {'key': 'MYSQL_USER', 'label': '用户名', 'type': 'text', 'default': 'root'},
            {'key': 'MYSQL_PASSWORD', 'label': '密码', 'type': 'password', 'placeholder': '', 'sensitive': True},
            {'key': 'MYSQL_DATABASE', 'label': '数据库名', 'type': 'text', 'default': 'production_tracking'},
        ],
        'test': {
            'label': '测试数据库连接',
            'action': 'test_mysql'
        }
    },
    'external_api': {
        'label': '外部接口配置',
        'icon': '🔌',
        'fields': [
            {'key': 'ALIYUN_API_KEY', 'label': '阿里云API Key', 'type': 'password', 'sensitive': True},
            {'key': 'ALIYUN_API_SECRET', 'label': '阿里云API Secret', 'type': 'password', 'sensitive': True},
            {'key': 'ALIYUN_SPEECH_APPKEY', 'label': '阿里云语音AppKey', 'type': 'password', 'sensitive': True},
            {'key': 'ALIYUN_VISION_APPKEY', 'label': '阿里云视觉AppKey', 'type': 'password', 'sensitive': True},
            {'key': 'DASHSCOPE_API_KEY', 'label': '通义千问API Key', 'type': 'password', 'sensitive': True},
        ]
    },
    'warehouse': {
        'label': '仓库接口配置',
        'icon': '📦',
        'fields': [
            {'key': 'WAREHOUSE_API_URL', 'label': '仓库API地址', 'type': 'text', 'placeholder': 'http://192.168.1.100:8080/api'},
            {'key': 'WAREHOUSE_API_KEY', 'label': 'API密钥', 'type': 'password', 'sensitive': True},
            {'key': 'WAREHOUSE_TIMEOUT', 'label': '请求超时(秒)', 'type': 'number', 'default': '10'},
        ],
        'test': {
            'label': '测试仓库连接',
            'action': 'test_warehouse'
        }
    },
    'business': {
        'label': '业务参数',
        'icon': '⚙️',
        'fields': [
            {'key': 'MAX_TEXT_LENGTH', 'label': '最大文本长度', 'type': 'number', 'default': '2048'},
            {'key': 'SESSION_TIMEOUT', 'label': '会话超时(秒)', 'type': 'number', 'default': '300'},
            {'key': 'JWT_EXPIRE_HOURS', 'label': 'JWT过期时间(小时)', 'type': 'number', 'default': '24'},
            {'key': 'PURCHASE_OPERATORS', 'label': '采购人员ID(逗号分隔)', 'type': 'text', 'default': 'PU001,PU002'},
        ]
    },
    'container': {
        'label': '容器中心连接',
        'icon': '🏭',
        'fields': [
            {'key': 'CONTAINER_CENTER_URL', 'label': '服务地址', 'type': 'text', 'placeholder': 'http://localhost:5002'},
            {'key': 'CONTAINER_CENTER_SECRET', 'label': '连接密钥', 'type': 'password', 'placeholder': '', 'sensitive': True},
        ],
        'test': {
            'label': '测试容器中心连接',
            'action': 'container_center'
        }
    }
}


def _get_env_values() -> Dict[str, str]:
    """获取当前所有环境变量值"""
    values = {}
    for category, schema in CONFIG_SCHEMA.items():
        for field in schema.get('fields', []):
            key = field['key']
            values[key] = os.getenv(key, field.get('default', ''))
    return values


@config_center_bp.route('/')
def index():
    """配置中心首页"""
    return render_template('config_center.html')


@config_center_bp.route('/schema')
def get_schema():
    """获取配置schema定义"""
    return jsonify({
        'code': 0,
        'data': CONFIG_SCHEMA
    })


@config_center_bp.route('/values')
def get_values():
    """获取当前所有配置值"""
    try:
        values = _get_env_values()
        json_config = _load_json_config()
        values.update(json_config.get('env_overrides', {}))
        return jsonify({
            'code': 0,
            'data': values
        })
    except Exception as e:
        logger.error(f"获取配置值失败: {e}")
        return jsonify({'code': 500, 'message': str(e)})


@config_center_bp.route('/save', methods=['POST'])
def save_config():
    """保存配置"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 400, 'message': '请求数据为空'})

        env_updates = {}
        for key, value in data.items():
            if value is not None:
                env_updates[key] = str(value)

        updated = _update_env_file(env_updates)

        json_config = _load_json_config()
        json_config['env_overrides'] = env_updates
        json_config['updated_at'] = datetime.now().isoformat()
        _save_json_config(json_config)

        return jsonify({
            'code': 0,
            'message': f'配置保存成功，已更新 {updated} 项',
            'updated_count': updated
        })
    except Exception as e:
        logger.error(f"保存配置失败: {e}")
        return jsonify({'code': 500, 'message': str(e)})


@config_center_bp.route('/test/mysql', methods=['POST'])
def test_mysql_connection():
    """测试MySQL数据库连接"""
    try:
        data = request.get_json() or {}
        host = data.get('MYSQL_HOST', os.getenv('MYSQL_HOST', 'localhost'))
        port = int(data.get('MYSQL_PORT', os.getenv('MYSQL_PORT', '3306')))
        user = data.get('MYSQL_USER', os.getenv('MYSQL_USER', 'root'))
        password = data.get('MYSQL_PASSWORD', os.getenv('MYSQL_PASSWORD', ''))
        database = data.get('MYSQL_DATABASE', os.getenv('MYSQL_DATABASE', 'production_tracking'))

        try:
            from core.db import get_direct_connection
            conn = get_direct_connection(
                host=host, port=port, user=user,
                password=password, database=database,
                connect_timeout=REQUEST_TIMEOUT_FAST
            )
            conn.close()
            return jsonify({'code': 0, 'message': '✅ 数据库连接成功'})
        except ImportError:
            return jsonify({'code': 0, 'message': '⚠️ pymysql 未安装，无法测试连接'})
        except Exception as e:
            return jsonify({'code': 500, 'message': f'❌ 连接失败: {str(e)}'})
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})


@config_center_bp.route('/test/warehouse', methods=['POST'])
def test_warehouse_connection():
    """测试仓库API连接"""
    try:
        data = request.get_json() or {}
        api_url = data.get('WAREHOUSE_API_URL', os.getenv('WAREHOUSE_API_URL', ''))
        api_key = data.get('WAREHOUSE_API_KEY', os.getenv('WAREHOUSE_API_KEY', ''))

        if not api_url:
            return jsonify({'code': 400, 'message': '⚠️ 请先配置仓库API地址'})

        try:
            headers = {'Content-Type': 'application/json'}
            if api_key:
                headers['Authorization'] = f'Bearer {api_key}'
            resp = requests.get(f'{api_url}/health', headers=headers, timeout=REQUEST_TIMEOUT_FAST)
            if resp.status_code == 200:
                return jsonify({'code': 0, 'message': f'✅ 仓库API连接成功 (HTTP {resp.status_code})'})
            else:
                return jsonify({'code': 500, 'message': f'⚠️ 仓库返回状态码: HTTP {resp.status_code}'})
        except ImportError:
            return jsonify({'code': 0, 'message': '⚠️ requests 未安装，无法测试连接'})
        except requests.exceptions.ConnectionError:
            return jsonify({'code': 500, 'message': '❌ 无法连接仓库服务，请检查地址是否正确'})
        except requests.exceptions.Timeout:
            return jsonify({'code': 500, 'message': '❌ 连接超时'})
        except Exception as e:
            return jsonify({'code': 500, 'message': f'❌ 连接失败: {str(e)}'})
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})


@config_center_bp.route('/test/container_center', methods=['POST'])
def test_container_center_connection():
    """测试容器中心连接"""
    try:
        data = request.get_json() or {}
        base_url = data.get('CONTAINER_CENTER_URL', os.getenv('CONTAINER_CENTER_URL', 'http://localhost:5002'))
        secret = data.get('CONTAINER_CENTER_SECRET', os.getenv('CONTAINER_CENTER_SECRET', ''))

        from container_center.client import ContainerCenterClient
        client = ContainerCenterClient(base_url=base_url, secret=secret, connect_timeout=REQUEST_TIMEOUT_FAST, read_timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10')))
        resp = client._request('GET', '/health')

        databases = resp.get('data', {}).get('databases', [])
        db_count = len(databases)
        return jsonify({'code': 0, 'message': f'✅ 容器中心连接成功，{db_count} 个数据库', 'data': resp.get('data')})
    except ImportError:
        return jsonify({'code': 0, 'message': '⚠️ container_center 模块未安装'})
    except requests.exceptions.ConnectionError:
        return jsonify({'code': 500, 'message': '❌ 无法连接容器中心，请检查地址是否正确'})
    except requests.exceptions.Timeout:
        return jsonify({'code': 500, 'message': '❌ 连接超时'})
    except Exception as e:
        return jsonify({'code': 500, 'message': f'❌ 连接失败: {str(e)}'})


@config_center_bp.route('/config-file')
def get_config_file_content():
    """获取.env配置文件原始内容（仅显示敏感字段掩码）"""
    try:
        if not os.path.exists(ENV_FILE):
            return jsonify({'code': 0, 'data': '', 'message': '.env 文件不存在'})

        with open(ENV_FILE, 'r', encoding='utf-8') as f:
            content = f.read()

        masked_lines = []
        for line in content.split('\n'):
            if '=' in line and not line.strip().startswith('#'):
                key, _, value = line.partition('=')
                key = key.strip()
                if any(s in key.upper() for s in ['SECRET', 'PASSWORD', 'KEY', 'TOKEN', 'AES']):
                    if value.strip():
                        value = value.strip()[:4] + '*' * (len(value.strip()) - 4) if len(value.strip()) > 4 else '****'
                masked_lines.append(f'{key}={value}')
            else:
                masked_lines.append(line)

        return jsonify({'code': 0, 'data': '\n'.join(masked_lines)})
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})


@config_center_bp.route('/container-config')
def get_container_business_config():
    """获取容器中心业务配置（操作员、工序、数据类型）"""
    try:
        from container_config import container_config
        config_dict = container_config.to_dict()
        notification = container_config.get_notification_config().__dict__
        return jsonify({
            'code': 0,
            'data': {
                'operators': config_dict.get('operators', {}),
                'processes': config_dict.get('processes', {}),
                'data_types': config_dict.get('data_types', {}),
                'notification': notification
            }
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})


@config_center_bp.route('/container-config/operators', methods=['POST'])
def add_container_operator():
    """添加操作员"""
    try:
        data = request.get_json()
        from container_config import container_config, OperatorConfig
        op = OperatorConfig(
            id=data.get('id'),
            name=data.get('name'),
            role=data.get('role', '工人'),
            department=data.get('department', ''),
            enabled=data.get('enabled', True)
        )
        if container_config.add_operator(op):
            return jsonify({'code': 0, 'message': '操作员添加成功'})
        return jsonify({'code': 400, 'message': '操作员ID已存在'})
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})


@config_center_bp.route('/container-config/operators/<operator_id>', methods=['PUT'])
def update_container_operator(operator_id):
    """更新操作员"""
    try:
        data = request.get_json()
        from container_config import container_config
        if container_config.update_operator(operator_id, **data):
            return jsonify({'code': 0, 'message': '操作员更新成功'})
        return jsonify({'code': 404, 'message': '操作员不存在'})
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})


@config_center_bp.route('/container-config/operators/<operator_id>', methods=['DELETE'])
def delete_container_operator(operator_id):
    """删除操作员"""
    try:
        from container_config import container_config
        if container_config.remove_operator(operator_id):
            return jsonify({'code': 0, 'message': '操作员删除成功'})
        return jsonify({'code': 404, 'message': '操作员不存在'})
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})


@config_center_bp.route('/container-config/processes', methods=['POST'])
def add_container_process():
    """添加工序"""
    try:
        data = request.get_json()
        from container_config import container_config, ProcessConfig
        proc = ProcessConfig(
            id=data.get('id'),
            name=data.get('name'),
            code=data.get('code'),
            sequence=int(data.get('sequence', 0)),
            enabled=data.get('enabled', True),
            quality_check_required=data.get('quality_check_required', False)
        )
        if container_config.add_process(proc):
            return jsonify({'code': 0, 'message': '工序添加成功'})
        return jsonify({'code': 400, 'message': '工序ID已存在'})
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})


@config_center_bp.route('/container-config/processes/<process_id>', methods=['PUT'])
def update_container_process(process_id):
    """更新工序"""
    try:
        data = request.get_json()
        from container_config import container_config
        if container_config.update_process(process_id, **data):
            return jsonify({'code': 0, 'message': '工序更新成功'})
        return jsonify({'code': 404, 'message': '工序不存在'})
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})


@config_center_bp.route('/container-config/notification', methods=['PUT'])
def update_notification_config():
    """更新通知配置"""
    try:
        data = request.get_json()
        from container_config import container_config
        container_config.update_notification_config(**data)
        return jsonify({'code': 0, 'message': '通知配置更新成功'})
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})
