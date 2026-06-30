# Mock使用规范

> 版本: v1.0
> 创建时间: 2026-06-15
> 适用范围: 不锈钢网带跟单3.0项目

---

## 一、Mock原则

### 1.1 必须Mock的场景

| 场景 | 原因 | Mock方式 |
|------|------|---------|
| 数据库操作 | 隔离测试，防止污染主数据 | @patch 或 fixture |
| 外部API调用 | 依赖不可控网络 | @patch |
| 文件系统操作 | 隔离测试环境 | tmp_path fixture |
| 时间相关函数 | 测试结果应可复现 | freezegun 或 @patch |
| 随机数生成 | 测试结果应可复现 | @patch |

### 1.2 不需要Mock的场景

- 纯函数计算（无副作用）
- 内存中的数据结构操作
- 单元测试范围内的计算逻辑

---

## 二、数据库Mock

### 2.1 推荐方式：类级fixture

```python
# -*- coding: utf-8 -*-
"""
models/order.py 测试
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest
from unittest.mock import patch, MagicMock


class TestOrderDAO:
    """OrderDAO 测试"""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """自动Mock数据库连接"""
        self.mock_cursor = MagicMock()
        self.mock_conn = MagicMock()

        # 设置cursor的context manager
        self.mock_conn.cursor.return_value.__enter__.return_value = self.mock_cursor
        self.mock_conn.cursor.return_value.__exit__.return_value = None

        # Mock get_connection
        self.get_conn_patch = patch('models.order.get_connection', return_value=self.mock_conn)
        self.get_conn_patch.start()

        yield

        self.get_conn_patch.stop()
```

### 2.2 装饰器方式

```python
@patch('models.order.get_connection')
def test_create_order(self, mock_get_conn):
    """测试创建订单"""
    mock_conn = MagicMock()
    mock_get_conn.return_value = mock_conn

    # 设置cursor
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.cursor.return_value.__exit__.return_value = None

    # 测试代码
    from models.order import OrderDAO
    dao = OrderDAO()
    result = dao.create({'name': 'Test'})

    assert result['id'] == 1
```

### 2.3 常见错误

```python
# ❌ 错误：未Mock cursor
mock_conn = MagicMock()
# mock_conn.cursor() 返回的不是 MagicMock

# ✅ 正确：Mock cursor
mock_conn = MagicMock()
mock_cursor = MagicMock()
mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
mock_conn.cursor.return_value.__exit__.return_value = None
```

---

## 三、数据库Mock示例

### 3.1 查询操作Mock

```python
def test_get_order_by_id(self):
    """测试按ID查询订单"""
    self.mock_cursor.fetchone.return_value = {
        'id': 1,
        'name': 'Test Order',
        'status': 'pending'
    }

    from models.order import get_order_by_id
    result = get_order_by_id(1)

    assert result['id'] == 1
    assert result['name'] == 'Test Order'
```

### 3.2 插入操作Mock

```python
def test_create_order(self):
    """测试创建订单"""
    self.mock_cursor.lastrowid = 123

    from models.order import create_order
    result = create_order({'name': 'New Order'})

    assert result['id'] == 123
    self.mock_cursor.execute.assert_called_once()
```

### 3.3 更新操作Mock

```python
def test_update_order_status(self):
    """测试更新订单状态"""
    self.mock_cursor.rowcount = 1

    from models.order import update_status
    result = update_status(1, 'completed')

    assert result is True
```

### 3.4 分页查询Mock

```python
def test_get_orders_paginated(self):
    """测试分页查询"""
    self.mock_cursor.fetchall.return_value = [
        {'id': 1, 'name': 'Order 1'},
        {'id': 2, 'name': 'Order 2'},
    ]
    self.mock_cursor.fetchone.return_value = {'count': 50}

    from models.order import get_orders_paginated
    result = get_orders_paginated(page=1, page_size=10)

    assert len(result['data']) == 2
    assert result['total'] == 50
```

---

## 四、External API Mock

### 4.1 HTTP请求Mock

```python
@patch('urllib.request.urlopen')
def test_wechat_push(self, mock_urlopen):
    """测试微信推送"""
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"errcode": 0, "errmsg": "ok"}'
    mock_urlopen.return_value.__enter__.return_value = mock_response

    from services.wechat import push_message
    result = push_message('test_token', 'openid', 'content')

    assert result['errcode'] == 0
```

### 4.2 请求工厂Mock

```python
@patch('services.inventory_notifier._do_http_request')
def test_inventory_notify(self, mock_http):
    """测试库存通知"""
    mock_http.return_value = b'{"status": "success"}'

    from services.inventory_notifier import notify_stock_change
    result = notify_stock_change({'item_id': 1, 'qty': 100})

    assert result['status'] == 'success'
```

---

## 五、时间Mock

### 5.1 使用freezegun

```python
from freezegun import freeze_time

@freeze_time("2024-01-15 12:00:00")
def test_order_due_date(self):
    """测试订单到期日期计算"""
    from models.order import calculate_due_date
    result = calculate_due_date('2024-01-10')
    assert result == '2024-01-17'
```

### 5.2 使用patch

```python
@patch('time.time')
@patch('time.strftime')
def test_log_timestamp(self, mock_strftime, mock_time):
    """测试日志时间戳"""
    mock_time.return_value = 1705310400  # 2024-01-15 12:00:00
    mock_strftime.return_value = '2024-01-15 12:00:00'

    from utils.logger import log_action
    result = log_action('test')

    assert '2024-01-15' in result
```

---

## 六、文件系统Mock

### 6.1 使用tmp_path

```python
def test_export_excel(self, tmp_path):
    """测试Excel导出"""
    from utils.excel import export_to_excel

    output_file = tmp_path / "test.xlsx"
    result = export_to_excel([{'id': 1, 'name': 'Test'}], str(output_file))

    assert output_file.exists()
    assert result is True
```

### 6.2 Mock文件系统

```python
@patch('builtins.open', create=True)
@patch('os.path.exists', return_value=True)
def test_read_config(self, mock_exists, mock_open):
    """测试读取配置文件"""
    mock_open.return_value.__enter__.return_value.read.return_value = '{"key": "value"}'

    from utils.config import read_config
    result = read_config('test.json')

    assert result['key'] == 'value'
```

---

## 七、Mock最佳实践

### 7.1 Mock范围

```python
# ❌ 错误：Mock范围过大
@patch('models.order')  # Mock了整个模块

# ✅ 正确：Mock具体函数
@patch('models.order.get_connection')
```

### 7.2 Mock返回值

```python
# ❌ 错误：返回值不完整
mock_cursor.fetchall.return_value = [{'id': 1}]

# ✅ 正确：返回完整数据结构
mock_cursor.fetchall.return_value = [
    {'id': 1, 'name': 'Order 1', 'status': 'pending', 'created_at': '2024-01-01'}
]
```

### 7.3 Mock清理

```python
# ❌ 错误：未清理Mock
def test_something(self):
    patcher = patch('models.order.get_connection')
    patcher.start()
    # 测试代码

# ✅ 正确：使用fixture清理
@pytest.fixture(autouse=True)
def setup_mocks(self):
    self.patcher = patch('models.order.get_connection')
    self.patcher.start()
    yield
    self.patcher.stop()
```

---

## 八、常见问题

### 8.1 Mock不生效

**原因**: Mock路径错误

```python
# ❌ 错误：Mock路径不正确
@patch('get_connection')  # 应该用完整路径

# ✅ 正确：Mock完整导入路径
@patch('models.order.get_connection')
```

### 8.2 Mock后数据库仍被修改

**原因**: 数据库连接未真正Mock

```python
# ❌ 错误：只Mock了函数，未Mock返回值
@patch('models.order.get_connection')
def test_something(self, mock_get_conn):
    # mock_get_conn 未设置 return_value

# ✅ 正确：设置完整Mock
@patch('models.order.get_connection')
def test_something(self, mock_get_conn):
    mock_conn = MagicMock()
    mock_get_conn.return_value = mock_conn
```

### 8.3 Mock对象属性访问报错

**原因**: 未正确设置MagicMock

```python
# ❌ 错误：直接访问属性
mock_conn.cursor().execute()  # cursor()返回MagicMock，但没有正确配置

# ✅ 正确：配置context manager
mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
mock_conn.cursor.return_value.__exit__.return_value = None
```

---

## 九、Mock模板

### 9.1 标准测试文件模板

```python
# -*- coding: utf-8 -*-
"""
{模块名}.py 完整单元测试

覆盖模块:
- {类名/函数名1}
- {类名/函数名2}
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest
from unittest.mock import patch, MagicMock


class Test{模块名}:
    """测试类"""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """自动Mock数据库"""
        self.mock_cursor = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_conn.cursor.return_value.__enter__.return_value = self.mock_cursor
        self.mock_conn.cursor.return_value.__exit__.return_value = None

        self.get_conn_patch = patch('{模块路径}.get_connection', return_value=self.mock_conn)
        self.get_conn_patch.start()
        yield
        self.get_conn_patch.stop()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

---

**最后更新**: 2026-06-15
**维护人**: AI助手
