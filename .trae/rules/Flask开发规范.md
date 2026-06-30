# Flask开发规范

> 版本: v1.0
> 创建时间: 2026-06-15
> 适用范围: 不锈钢网带跟单3.0项目 Flask相关开发

---

## 一、before_request 闭包变量问题

### 1.1 问题描述

在 Flask 的 `before_request` 装饰器函数中，使用 `global` 关键字声明变量会导致 `NameError`。

**错误示例**：
```python
def create_app():
    app = Flask(__name__)

    _operators_warmed_up = False  # 在函数外部定义

    @app.before_request
    def _warmup_on_first_request():
        global _operators_warmed_up  # ❌ NameError: name '_operators_warmed_up' is not defined
        if not _operators_warmed_up:
            ...
```

**原因**：`before_request` 是 Flask 内部的回调函数，它不认识 `global` 关键字声明的变量。

### 1.2 正确做法

使用字典或列表代替全局变量：

```python
def create_app():
    app = Flask(__name__)

    _warmup_state = {'done': False}  # ✅ 用字典包装

    @app.before_request
    def _warmup_on_first_request():
        if not _warmup_state['done']:  # ✅ 字典在闭包内可以直接访问
            ...
            _warmup_state['done'] = True
```

### 1.3 原理说明

| 方式 | 说明 |
|------|------|
| `global` 关键字 | 声明使用全局命名空间的变量，但 `before_request` 回调函数无法正确解析 |
| 字典/列表 | 闭包（closure）可以捕获外部作用域的可变对象（如字典、列表），从而实现状态保持 |

---

## 二、Flask 应用初始化顺序

### 2.1 推荐顺序

```python
def create_app():
    # 1. 创建应用实例
    app = Flask(__name__)

    # 2. 配置
    app.config['TEMPLATES_AUTO_RELOAD'] = True

    # 3. 初始化扩展（CORS、限流等）
    init_cors(app, ...)
    limiter.init_app(app)

    # 4. 注册钩子（before_request、after_request）
    @app.before_request
    def before():
        ...

    # 5. 注册蓝图
    app.register_blueprint(xxx_bp)

    # 6. 注册路由
    @app.route('/api/xxx')
    def api_xxx():
        ...

    return app
```

### 2.2 常见错误

- ❌ 在 `create_app()` 外部定义变量，然后在 `before_request` 中使用 `global`
- ❌ 在注册蓝图之前使用蓝图中的变量
- ❌ 在应用创建之前注册路由

---

## 三、延迟预热模式

### 3.1 问题背景

MySQL 首次连接建立较慢（约 2-3 秒），如果在服务器启动时预热，可能因连接超时失败。

### 3.2 解决方案

将预热逻辑移到首次请求时执行：

```python
def create_app():
    app = Flask(__name__)

    # 预热状态
    _warmup_state = {'done': False}

    @app.before_request
    def _warmup_on_first_request():
        if not _warmup_state['done']:
            try:
                # 执行预热（如加载操作员、初始化连接等）
                warmup_operators()
                _warmup_state['done'] = True
            except Exception as e:
                logger.warning(f'预热失败: {e}')

    return app
```

### 3.3 注意事项

- 预热操作应设置超时，避免阻塞请求
- 预热失败不应影响正常请求处理
- 可添加日志便于排查

---

## 四、缓存机制设计

### 4.1 进程内缓存

适用于单进程应用（如 Flask 单进程部署）：

```python
# 模块级缓存变量
_PROCESS_TASKS_CACHE = {
    'data': None,
    'time': 0,
    'ttl': 10,  # TTL 10秒
}

def get_cache():
    now = time.time()
    if _PROCESS_TASKS_CACHE['data'] is not None:
        if now - _PROCESS_TASKS_CACHE['time'] < _PROCESS_TASKS_CACHE['ttl']:
            return _PROCESS_TASKS_CACHE['data']
    return None

def set_cache(data):
    _PROCESS_TASKS_CACHE['data'] = data
    _PROCESS_TASKS_CACHE['time'] = time.time()
```

### 4.2 缓存失效策略

| 场景 | 策略 |
|------|------|
| 写操作后 | 调用清除缓存函数 |
| 定时失效 | 设置合理的 TTL |
| 主动刷新 | 提供刷新接口 |

```python
# 清除缓存示例
def clear_schedule_cache():
    _SCHEDULE_LIST_CACHE['data'] = None
    _SCHEDULE_LIST_CACHE['time'] = 0

# 在写操作后调用
@app.route('/api/schedule/publish', methods=['POST'])
def publish():
    ...
    clear_schedule_cache()  # 清除缓存
    return success()
```

### 4.3 缓存规则设计

```python
# 无筛选条件时使用缓存
if not filter_order_no and not status_filter and page == 1 and page_size == 20:
    cached = get_cache()
    if cached:
        return cached

# 有筛选条件时禁用缓存，保证准确性
data = query_database(...)
set_cache(data)
return data
```

---

## 五、常见错误排查

### 5.1 NameError in before_request

**错误**：`NameError: name 'xxx' is not defined`

**原因**：在 `before_request` 中使用了 `global` 关键字

**解决**：使用字典或列表包装变量

### 5.2 缓存不生效

**原因**：
1. 多进程部署导致每个进程独立缓存
2. 缓存键设计不合理
3. TTL 设置过长

**解决**：
1. 考虑使用 Redis 等外部缓存
2. 合理设计缓存键
3. 根据业务调整 TTL

### 5.3 预热失败导致服务不可用

**原因**：预热逻辑放在 `create_app()` 中，且未捕获异常

**解决**：
1. 使用延迟预热（首次请求时）
2. 预热逻辑添加 try-except
3. 预热失败不应阻止服务启动

---

## 六、最佳实践清单

- [ ] `before_request` 中使用字典代替 `global` 变量
- [ ] 预热逻辑放在首次请求时执行
- [ ] 预热/缓存操作添加异常处理
- [ ] 写操作后清除相关缓存
- [ ] 缓存操作添加日志（debug级别）
- [ ] 敏感信息（如连接密码）不写入日志

---

**最后更新**: 2026-06-15
**维护人**: AI助手
