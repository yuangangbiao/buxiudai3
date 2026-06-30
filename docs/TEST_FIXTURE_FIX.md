# Pytest Fixture 污染修复

## 核心问题

测试单独运行通过，批量运行失败 → **Fixture 污染**

## 三条铁律

### 1. 禁止模块级导入
```python
# ❌ 错误：导入时绑定，不受 mock 影响
from models.order_log import OrderLogDAO

# ✅ 正确：在 fixture 中导入
@pytest.fixture
def setup(self):
    from models.order_log import OrderLogDAO
    self.OrderLogDAO = OrderLogDAO
```

### 2. Patch 必须清理
```python
# ❌ 错误：忘记 stop()
def _patch(self):
    p = patch('models.database.get_connection')
    p.start()
    return p  # 没有 stop()

# ✅ 正确：用 contextmanager
@contextmanager
def _patch(self):
    p = patch('models.database.get_connection')
    p.start()
    try:
        yield
    finally:
        p.stop()  # 关键

def test_xxx(self):
    with self._patch():
        from models.order import OrderDAO
        result = OrderDAO().get_by_id(1)
    # with 结束后自动清理
```

### 3. 删除模块前先 Patch
```python
# ❌ 错误：先删后 patch
del sys.modules['models.order']
patch('models.database.get_connection').start()

# ✅ 正确：先 patch 后删除
patch('models.database.get_connection').start()
del sys.modules['models.order']
```

## 修复清单

| 文件 | 问题 | 方案 |
|------|------|------|
| `test_order_log.py` | 13 failed | fixture 中删除+重导入+缓存引用 |
| `test_shipment.py` | 18 failed | contextmanager 清理 |
| `test_order_dao_complete.py` | 污染其他测试 | 添加 `models.order_log` patch |
| `test_quality_dao_complete.py` | 误删模块 | 移除 `models.shipment` 删除 |

## 调试方法

```bash
# 定位污染源：逐个加文件
pytest test_a.py test_order_log.py
pytest test_b.py test_order_log.py
# 找到哪个文件导致失败
```

## 结果

- 修复前：109 failed
- 修复后：**7 failed**（与污染无关）
- 通过：3104 passed
