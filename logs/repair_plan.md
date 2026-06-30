# 手机报工服务器 (5008) 错误维修方案

## 测试时间
2026-06-15 09:19:44

## 测试结果汇总

### 通过项目 (6项)
1. ✅ 首页访问 - HTTP 200
2. ✅ API健康检查 - HTTP 200
3. ✅ 数据库连接 - 正常 (db: ok)
4. ✅ 页面结构 - HTML/Script/Style 完整
5. ✅ 考勤数据 API - HTTP 200
6. ✅ 质检数据 API - HTTP 200

### 失败项目 (2项)
1. ❌ **订单列表 API** - HTTP 404
2. ❌ **物料数据 API** - HTTP 404

### 警告项目 (1项)
1. ⚠️ **服务状态异常** - degraded (bot: error)

---

## 错误详情与维修方案

### 错误 1: 订单列表 API 返回 404

**问题描述**
- 端点: `GET /api/orders`
- 状态码: 404 Not Found
- 影响: 无法获取订单列表数据

**可能原因**
1. 路由未注册或路径错误
2. 路由定义在错误的 Blueprint 中
3. 权限问题导致拒绝访问

**维修方案**
```python
# 1. 检查路由注册 (在 mobile_api_ai/app.py 中)
# 确保存在类似以下的路由定义:
@app.route('/api/orders', methods=['GET'])
def get_orders():
    # 实现订单列表逻辑
    pass

# 2. 如果路由在其他 Blueprint 中，需要确保正确注册
from routes.orders import orders_bp
app.register_blueprint(orders_bp, url_prefix='/api')

# 3. 检查路由冲突或覆盖问题
```

**检查步骤**
```bash
# 查看所有注册的路由
curl http://localhost:5008/api/orders -v

# 检查日志文件
cat logs/mobile_api.log | grep -i order
```

---

### 错误 2: 物料数据 API 返回 404

**问题描述**
- 端点: `GET /api/material`
- 状态码: 404 Not Found
- 影响: 无法获取物料数据

**可能原因**
1. 路由未注册
2. 路由路径不正确 (可能是 /api/materials 或 /api/material_list)
3. 需要认证但未提供 token

**维修方案**
```python
# 1. 检查路由定义
@app.route('/api/material', methods=['GET'])
# 或
@app.route('/api/materials', methods=['GET'])
def get_materials():
    # 实现物料数据获取逻辑
    pass

# 2. 如果需要认证
from functools import wraps

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'No token'}), 401
        # 验证 token
        return f(*args, **kwargs)
    return decorated

@app.route('/api/material', methods=['GET'])
@require_auth
def get_materials():
    pass
```

**检查步骤**
```bash
# 查看所有 API 路由
curl http://localhost:5008/api/ -v

# 检查物料相关日志
cat logs/mobile_api.log | grep -i material
```

---

### 错误 3: 服务状态异常 (degraded)

**问题描述**
- 健康检查状态: `degraded`
- 组件状态:
  - bot: error ❌
  - db: ok ✅

**影响**
- Bot 功能不可用，可能影响自动报工或消息通知

**可能原因**
1. 企业微信 Bot 配置缺失或错误
2. API Key 未设置
3. Bot 服务未启动
4. 网络连接问题

**维修方案**

```python
# 1. 检查环境变量配置
import os
WECHAT_CLOUD_API_KEY = os.environ.get('WECHAT_CLOUD_API_KEY')

if not WECHAT_CLOUD_API_KEY:
    print("警告: WECHAT_CLOUD_API_KEY 未设置")

# 2. 在 .env 文件中配置
WECHAT_CLOUD_API_KEY=your_api_key_here

# 3. 检查 Bot 服务状态
# 在 health check 中添加更详细的诊断
@app.route('/api/health')
def health_check():
    bot_status = check_bot_health()
    return jsonify({
        'status': 'ok' if bot_status == 'ok' else 'degraded',
        'components': {
            'bot': bot_status,
            'db': 'ok'  # 假设 db 正常
        }
    })

def check_bot_health():
    try:
        # 尝试连接 Bot 服务
        response = requests.get('https://api.weixin.qq.com/cgi-bin/getcallbackip')
        return 'ok' if response.status_code == 200 else 'error'
    except:
        return 'error'
```

**检查步骤**
```bash
# 1. 检查环境变量
echo $WECHAT_CLOUD_API_KEY

# 2. 测试 Bot API 连通性
curl https://api.weixin.qq.com/cgi-bin/getcallbackip

# 3. 查看 Bot 相关日志
cat logs/mobile_api.log | grep -i bot
cat logs/mobile_api.log | grep -i wechat
```

---

## 优先修复建议

### 🔴 高优先级 (影响核心功能)

1. **修复订单列表 API**
   - 文件: `mobile_api_ai/app.py` 或 `mobile_api_ai/routes/orders.py`
   - 操作: 添加或修复 `/api/orders` 路由

2. **修复物料数据 API**
   - 文件: `mobile_api_ai/app.py` 或 `mobile_api_ai/routes/materials.py`
   - 操作: 添加或修复 `/api/material` 路由

### 🟡 中优先级 (影响部分功能)

3. **修复 Bot 服务**
   - 文件: `.env`
   - 操作: 配置 `WECHAT_CLOUD_API_KEY`

---

## 测试验证

修复后，请运行以下命令验证:

```bash
# 1. 测试订单列表 API
curl http://localhost:5008/api/orders

# 2. 测试物料数据 API
curl http://localhost:5008/api/material

# 3. 重新运行完整测试
python comprehensive_test.py
```

---

## 相关文件

- 测试报告: `logs/comprehensive_test_report.txt`
- 服务器日志: `logs/mobile_api.log`
- 配置文件: `d:\yuan\不锈钢网带跟单3.0\.env`

---

## 下一步行动

1. 检查 `mobile_api_ai/app.py` 中的路由定义
2. 确认所有必需的路由都已注册
3. 配置企业微信 API Key
4. 重新启动服务器
5. 运行测试验证修复效果

---

**报告生成时间**: 2026-06-15 09:20:00
**测试工具**: Python requests + BeautifulSoup
**测试覆盖**: HTTP连接、API端点、页面结构、组件健康检查
