# 安装说明

依赖统一管理在 **根目录 `requirements.txt`**（`d:\yuan\不锈钢网带跟单3.0\requirements.txt`）。

## 生产环境安装

```bash
# 在项目根目录执行
pip install -r requirements.txt
```

## 环境变量配置

创建 `.env` 文件：

```env
# JWT认证（必须）
JWT_SECRET_KEY=your-secret-key-here

# 数据库
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your-password
MYSQL_DATABASE=steel_belt

# CORS跨域
CORS_ALLOWED_ORIGINS=http://localhost:5000,http://localhost:3000

# Flask调试（生产环境设为false）
FLASK_DEBUG=false

# 微信相关
WECHAT_WORK_BOT_TOKEN=your-token
WECHAT_WORK_AES_KEY=your-aes-key
WECHAT_WORK_CORP_ID=your-corp-id
WECHAT_WORK_AGENT_ID=your-agent-id

# 阿里云通义千问
DASHSCOPE_API_KEY=your-api-key

# 容器中心
CONTAINER_CENTER_URL=http://localhost:5002
CONTAINER_CENTER_SECRET=your-secret
```

## 依赖版本锁定

```bash
# 生成锁定文件
pip freeze > requirements-lock.txt
```
