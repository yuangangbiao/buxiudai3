# 不锈钢网带跟单系统 - 代码编写规范

**版本**: v1.0
**创建日期**: 2026-05-01
**基于**: 代码审查发现的问题

---

## 一、安全规范 (CRITICAL)

### 1.1 敏感信息管理 - 最高优先级

#### 禁止事项
```python
# ❌ 禁止在代码中硬编码密码
"password": "88888888"
"password": os.getenv('MYSQL_PASSWORD', '88888888')  # 默认值即为硬编码

# ❌ 禁止在代码中硬编码API密钥
"api_key": "steel_belt_inventory_key_2024"
headers = {'X-API-Key': 'your-secret-key'}

# ❌ 禁止在注释或文档中记录密码
# 连接信息：root / 88888888

# ❌ 禁止将密码写入SQL语句
CREATE USER 'root'@'%' IDENTIFIED BY '88888888';
```

#### 正确做法
```python
# ✅ 所有敏感信息必须从环境变量读取，不提供默认值
import os

# 数据库配置
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
if not MYSQL_PASSWORD:
    raise ValueError("MYSQL_PASSWORD 环境变量未设置")

# API密钥配置
API_KEY = os.getenv('INVENTORY_API_KEY', '')
if not API_KEY:
    raise ValueError("INVENTORY_API_KEY 环境变量未设置")

# 配置使用时
config = {
    "password": MYSQL_PASSWORD,
    "api_key": API_KEY,
}
```

#### .env 文件模板
```bash
# .env.example - 提交到版本控制
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DATABASE=steel_belt

INVENTORY_API_KEY=
WECHAT_API_KEY=
ALIYUN_API_KEY=
REDIS_PASSWORD=
```

```bash
# .env - 不提交到版本控制
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_secure_password_here
MYSQL_DATABASE=steel_belt

INVENTORY_API_KEY=your_inventory_api_key
WECHAT_API_KEY=your_wechat_api_key
ALIYUN_API_KEY=your_aliyun_api_key
REDIS_PASSWORD=your_redis_password
```

---

### 1.2 Git 安全
```bash
# .gitignore 必须包含
.env
*.pyc
__pycache__/
*.log
config/local_*.py
```

---

## 二、配置管理规范

### 2.1 配置分类

| 配置类型 | 管理方式 | 示例 |
|---------|---------|------|
| 环境相关 | 环境变量 | MYSQL_HOST, PORT |
| 敏感信息 | .env文件 | PASSWORD, API_KEY |
| 业务常量 | config.py | COLORS, FONTS, STATUS |
| 用户偏好 | JSON文件 | settings.json, window_config.json |

### 2.2 硬编码阈值 - 禁止模式

```python
# ❌ 禁止硬编码阈值
STOCK_WARNING_THRESHOLD = 50  # 库存预警
MAX_CONNECTIONS = 5          # 连接池
TIMEOUT_SECONDS = 30         # 超时时间
```

#### 正确做法
```python
# ✅ 从环境变量或配置文件读取
import os

STOCK_WARNING_THRESHOLD = int(os.getenv('STOCK_WARNING_THRESHOLD', 50))

# 或使用配置对象
from config import APP_CONFIG
STOCK_WARNING_THRESHOLD = APP_CONFIG.get('stock_warning_threshold', 50)
```

### 2.3 路径管理规范

#### 禁止模式
```python
# ❌ 禁止分散的路径硬编码
WINDOW_CONFIG_FILE = os.path.join(os.path.dirname(__file__), "..", "window_config.json")
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'settings.json')

# ❌ 禁止重复的 sys.path 操作
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
```

#### 正确做法
```python
# ✅ 在 config.py 中统一管理所有路径
import os
from pathlib import Path

def safe_path(path):
    """返回安全的中文路径"""
    return str(Path(path))

BASE_DIR = safe_path(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_DIR = os.path.join(BASE_DIR, "config")

# 导出统一的路径访问函数
def get_config_path(filename):
    """获取配置文件路径"""
    return os.path.join(CONFIG_DIR, filename)

def get_data_path(filename):
    """获取数据文件路径"""
    return os.path.join(DATA_DIR, filename)

def get_window_config_path():
    """获取窗口配置文件路径"""
    return os.path.join(DATA_DIR, "window_config.json")
```

```python
# ✅ 所有模块统一导入路径
from config import BASE_DIR, DATA_DIR, CONFIG_DIR, get_config_path, get_data_path

# 使用
config_file = get_window_config_path()
settings_file = os.path.join(DATA_DIR, "settings.json")
```

---

## 三、数据库操作规范

### 3.1 连接管理 - Context Manager 模式

```python
# ✅ 正确使用 context manager
from contextlib import contextmanager
from models.database import get_connection

@contextmanager
def get_db_cursor():
    """数据库操作的统一入口

    使用方式:
        with get_db_cursor() as (cursor, conn):
            cursor.execute("SELECT ...")
            conn.commit()
    """
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        yield cursor, conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        conn.close()
```

#### 使用示例
```python
# ✅ 标准用法
def get_order(order_id):
    with get_db_cursor() as (cursor, conn):
        cursor.execute("SELECT * FROM orders WHERE id=%s", (order_id,))
        return cursor.fetchone()

def create_order(data):
    with get_db_cursor() as (cursor, conn):
        cursor.execute("""
            INSERT INTO orders (order_no, customer_name, ...)
            VALUES (%s, %s, ...)
        """, (data['order_no'], data['customer_name'], ...))
        conn.commit()
        return cursor.lastrowid
```

### 3.2 禁止模式
```python
# ❌ 禁止不规范的资源管理
cursor = conn.cursor()
try:
    # 操作
finally:
    cursor.close()
    conn.close()  # conn.close() 应该在 finally 中确保执行

# ❌ 禁止分开关闭
cursor.close()
conn.close()  # 如果中间出错，conn 不会关闭
```

### 3.3 异常处理规范

```python
# ❌ 禁止裸 except
except:
    pass

# ❌ 禁止空的 except
except Exception:
    pass

# ✅ 正确做法：记录或重新抛出
except Exception as e:
    logger.error(f"数据库操作失败: {e}")
    raise  # 或 return error_result
```

---

## 四、代码规范

### 4.1 sys.path 管理

```python
# ❌ 禁止在每个文件中重复 sys.path 操作
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ✅ 只在入口文件中设置一次
# main.py 或 app.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 其他模块直接 import
from models import OrderDAO
from utils import helpers
```

### 4.2 日志规范

```python
# ❌ 禁止使用 print 调试
print("[DB] MySQL连接成功")
print(f"Order created: {order_id}")

# ✅ 使用日志系统
import logging
logger = logging.getLogger(__name__)

logger.info("[DB] MySQL连接成功")
logger.info(f"Order created: {order_id}")
logger.warning(f"库存不足: {material_name}")
logger.error(f"数据库错误: {e}")
```

### 4.3 颜色和样式管理

```python
# ❌ 禁止硬编码颜色
tk.Frame(root, bg="#1E3A5F")
tk.Label(root, fg="#FFD700")

# ✅ 使用 config.COLORS
from config import COLORS
tk.Frame(root, bg=COLORS["primary"])
tk.Label(root, fg=COLORS["warning"])
```

### 4.4 异常处理完整模式
```python
# ✅ 完整的异常处理
try:
    result = some_operation()
except ValueError as e:
    logger.warning(f"无效输入: {e}")
    return None, str(e)
except ConnectionError as e:
    logger.error(f"连接失败: {e}")
    raise  # 需要上层处理
except Exception as e:
    logger.exception(f"未知错误: {e}")  # 使用 logger.exception 自动包含 traceback
    return None, "系统错误"
```

---

## 五、重复代码治理

### 5.1 公共 DAO 方法抽取

```python
# ✅ models/base.py - 公共 DAO 基类
from contextlib import contextmanager
from models.database import get_connection

class BaseDAO:
    """所有 DAO 的基类"""

    @staticmethod
    @contextmanager
    def db_cursor():
        """统一的数据库连接管理"""
        conn = get_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            yield cursor, conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
            conn.close()

    @classmethod
    def find_by_id(cls, table, id):
        with cls.db_cursor() as (cursor, conn):
            cursor.execute(f"SELECT * FROM {table} WHERE id=%s", (id,))
            return cursor.fetchone()

    @classmethod
    def find_all(cls, table, where="1=1", params=()):
        with cls.db_cursor() as (cursor, conn):
            cursor.execute(f"SELECT * FROM {table} WHERE {where}", params)
            return cursor.fetchall()
```

```python
# ✅ 使用基类
from models.base import BaseDAO

class OrderDAO(BaseDAO):
    @staticmethod
    def create(data):
        with OrderDAO.db_cursor() as (cursor, conn):
            cursor.execute("""
                INSERT INTO orders (order_no, ...)
                VALUES (%s, ...)
            """, (data['order_no'], ...))
            return cursor.lastrowid
```

### 5.2 状态变更统一处理

```python
# ✅ 使用 EventBus 统一处理状态变更
from core.event_bus import EventBus, Events

# 发布事件
EventBus.publish(Events.ORDER_STATUS_CHANGED, {
    'order_id': order_id,
    'from_status': old_status,
    'to_status': new_status,
    'operator': operator
})

# 统一的事件处理器
@EventBus.subscribe(Events.ORDER_STATUS_CHANGED)
def on_order_status_changed(event, data):
    log_status_change("orders", data['order_id'],
                      data['from_status'], data['to_status'],
                      data.get('operator'))
    log_order_action(data['order_id'], get_order_no(data['order_id']),
                     "STATUS_CHANGE", data.get('operator', '系统'))
```

---

## 六、配置检查清单

### 6.1 新增代码检查

```markdown
代码提交前检查：

□ 是否有新的硬编码密码？ (搜索 "password":")
□ 是否有新的 API 密钥？ (搜索 "api_key":")
□ 是否有新的硬编码阈值？ (搜索 THRESHOLD, MAX_, TIMEOUT)
□ 是否使用了新的硬编码路径？ (搜索 os.path.join 配合字符串字面量)
□ 是否有新的硬编码颜色？ (搜索 #[0-9A-F]{6})
□ 是否使用了 print 而非 logger？
□ 是否有裸露的 except: 语句？
□ 是否有可以抽取为公共方法的重复代码？
```

### 6.2 配置项归属判断

```python
# 问自己：这个值是否会因环境而改变？
#   是 → 环境变量
#   是，且包含密码/密钥 → .env 文件
#   否，但可能被用户调整 → 配置文件 (settings.json)
#   否，且是业务常量 → constants.py / config.py
```

---

## 七、违规示例与正确对照

| 分类 | 违规代码 | 正确代码 |
|-----|---------|---------|
| 密码 | `"password": "88888888"` | `"password": os.getenv('MYSQL_PASSWORD', '')` |
| API密钥 | `"api_key": "steel_belt_key"` | `"api_key": os.getenv('INVENTORY_API_KEY', '')` |
| 阈值 | `MAX_CONN = 5` | `MAX_CONN = int(os.getenv('MYSQL_POOL_SIZE', 20))` |
| 路径 | `os.path.join(__file__, "..", "config")` | `from config import get_config_path` |
| 颜色 | `bg="#1E3A5F"` | `bg=COLORS["primary"]` |
| 日志 | `print("[INFO] done")` | `logger.info("done")` |
| 异常 | `except: pass` | `except Exception as e: logger.error(e)` |
| 路径 | `sys.path.insert(...)` | `from config import BASE_DIR` |

---

## 八、服务架构规范 (CRITICAL)

### 8.1 微信服务部署原则

#### 核心规则
```python
# ❌ 禁止在本地服务器启动微信相关服务
# 不允许在服务器本地运行任何微信相关进程或服务
# 包括但不限于：
# - WeChat Enterprise API
# - WeChat Work (企业微信) 本地服务
# - 任何微信相关的本地守护进程
```

#### 正确架构
```python
# ✅ 微信服务必须部署在云端
# 服务访问方式：
# 1. 通过 REST API 调用云端微信服务
# 2. 使用 Webhook 接收微信事件通知
# 3. 通过消息队列异步处理微信消息

# 配置示例
WECHAT_API_BASE_URL = os.getenv('WECHAT_API_BASE_URL', '')  # 云端微信服务地址
WECHAT_WEBHOOK_TOKEN = os.getenv('WECHAT_WEBHOOK_TOKEN', '')

# 调用云端微信服务
import requests

def send_wechat_message(to_user, content):
    response = requests.post(
        f"{WECHAT_API_BASE_URL}/api/message/send",
        json={
            "to_user": to_user,
            "content": content
        },
        headers={
            "Authorization": f"Bearer {WECHAT_WEBHOOK_TOKEN}"
        }
    )
    return response.json()
```

#### 部署要求
| 服务类型 | 部署位置 | 说明 |
|---------|---------|------|
| 微信 API 服务 | 云端服务器 | 企业微信或个人微信 API |
| 微信消息处理 | 云端服务 | 接收并处理微信事件 |
| 本地客户端 | 本地服务器 | 仅调用云端 API，不本地处理微信逻辑 |

### 8.2 架构检查清单
```markdown
代码提交前检查：

□ 是否在本地启动了任何微信服务？
□ 微信相关逻辑是否通过 API 调用云端服务？
□ 是否存在本地的微信守护进程或后台服务？
□ 所有微信集成是否使用远程 API 调用？
```

---

## 十、架构决策记录 (ADR)

### 10.1 DataSource 层引入时机

#### 决策
**当前不引入 DataSource 层**，保持现有 `storage_layer.py` 的 `BaseStorage` 抽象不变。

#### 原因
- SQLite 单连接场景不需要连接池
- storage_layer.py 已通过 `BaseStorage` 抽象实现了 SQLite ↔ Redis 的后端切换
- 再加一层 DataSource 增加复杂度，收益有限

#### 引入条件
当以下任一情况发生时，再引入 DataSource 层：
- 需要 MySQL 连接池管理
- 需要读写分离
- 需要自动重连机制

#### 预期架构
```
BaseStorage (业务抽象) → DataSource (连接管理) → 实际数据库
```

#### 参考
- storage_layer.py: BaseStorage / SqliteStorage / RedisStorage
- 讨论时间: 2026-05-14

---

## 九、持续更新

本规范基于代码审查发现的问题制定，随着项目发展，将持续更新。

**更新记录**：
- v1.2 (2026-05-14): 新增架构决策记录，DataSource 层引入时机
- v1.1 (2026-05-14): 新增服务架构规范，禁止本地启动微信服务
- v1.0 (2026-05-01): 初始版本，基于代码审查问题制定
