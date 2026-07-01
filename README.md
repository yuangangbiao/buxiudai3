# 不锈钢网带跟单系统 v3.0

不锈钢网带跟单系统的全栈服务端，包含移动端 API、调度中心、容器管理、库存管理、企业微信机器人等模块。

## 核心组件

| 组件 | 端口 | 说明 |
|------|------|------|
| `mobile_api_ai/container_center_api.py` | 5002 | 容器中心 API（订单/工序/质检 CRUD、outbox worker） |
| `mobile_api_ai/standalone_dispatch_server.py` | 5003 | 调度中心（流程推进、报工同步、企业微信机器人、outbox consumer、cloud poller） |
| `mobile_api_ai/inventory_api_server.py` | 5010 | 库存管理 API（出入库、盘点、调拨、报表） |

### 已废弃（v3.8.1）
- ~~`mobile_api_ai/app.py`~~ → 功能已合并到 `standalone_dispatch_server.py`
- ~~`mobile_api_ai/wechat_server.py`~~ → 功能已合并到 `standalone_dispatch_server.py`（sync_bp + wechat_work_bot_bp）

### 共用逻辑层

- `api/step_status_helper.py` — 流程/工序状态计算真值源，三端（手机端/桌面端/调度中心）共用
- `api/decorators.py` — API 鉴权、限流装饰器
- `container_center_v5.py` — 容器中心核心业务层
- `storage/` — 数据存储抽象层（MySQL + SQLite 混合存储）

## 功能特性

### 移动端 API (5002)
- ✅ 工序任务分页查询
- ✅ 扫码报工详情
- ✅ 流程详情与推进
- ✅ QA 任务分配与管理
- ✅ 数据包状态跟踪

### 调度中心 (5003)
- ✅ 流程节点推进/驳回
- ✅ 流程匹配规则配置
- ✅ 操作员管理
- ✅ 报修记录管理
- ✅ 消息模板配置
- ✅ 系统配置管理

### 库存管理系统 (5010)

### 服务器端
- ✅ MySQL数据库支持
- ✅ RESTful API接口
- ✅ 库存查询与管理
- ✅ 出入库操作
- ✅ 统计分析
- ✅ 低库存预警
- ✅ 数据备份
- ✅ 通知消息处理
- ✅ 打印功能

### 客户端
- ✅ 连接远程服务器
- ✅ 库存列表查看
- ✅ 统计信息展示
- ✅ 出入库流水查询
- ✅ 通知消息处理
- ✅ 配置文件支持

### 配置器
- ✅ 统一配置界面
- ✅ 服务器配置
- ✅ 客户端配置
- ✅ 数据库配置
- ✅ 配置文件导出

## 快速开始

### 服务器端

1. **运行配置器**
   ```
   双击: 启动配置器.bat
   ```

2. **配置数据库和服务器**
   - 设置数据库连接信息
   - 设置服务器监听地址（建议 0.0.0.0）
   - 设置API密钥

3. **启动服务器**
   ```
   双击: 启动库存服务器.bat
   ```

### 客户端

1. **获取服务器IP地址**

2. **配置客户端**
   ```
   双击: 启动配置器.bat
   ```
   在「客户端配置」标签页设置服务器地址

3. **启动客户端**
   ```
   双击: 启动库存客户端.bat
   ```

## 文件说明

### 核心程序

| 文件 | 说明 |
|------|------|
| `inventory_server.py` | API服务器程序 |
| `inventory_client.py` | 客户端程序 |
| `inventory_configurator.py` | 配置器程序 |
| `inventory_db_complete.py` | 数据库操作模块 |
| `inventory_print.py` | 打印模块 |
| `inventory_backup.py` | 备份模块 |

### 启动脚本

| 文件 | 说明 |
|------|------|
| `启动库存服务器.bat` | 启动API服务器 |
| `启动库存客户端.bat` | 启动客户端 |
| `启动配置器.bat` | 启动配置器 |
| `启动库存管理系统.bat` | 启动原服务端GUI |

### 文档

| 文件 | 说明 |
|------|------|
| `部署说明.md` | 详细部署指南 |
| `README.md` | 本文件 |

## 系统要求

- Python 3.8+
- MySQL 5.7+ 或 MariaDB 10.2+
- Windows 7+ (推荐 Windows 10/11)

## 依赖库

```
flask
requests
pymysql
```

## 配置说明

### 服务器配置 (inventory_server_config.json)

```json
{
    "host": "0.0.0.0",
    "port": 8080,
    "api_key": "your_api_key"
}
```

### 客户端配置 (inventory_client_config.json)

```json
{
    "server_url": "http://192.168.1.100:8080",
    "api_key": "your_api_key",
    "auto_refresh": true,
    "refresh_interval": 60
}
```

## 详细文档

请查看 `部署说明.md` 获取：
- 详细部署步骤
- API接口文档
- 常见问题解答
- 安全建议

## 项目结构

```
不锈钢网带跟单3.0/
├── inventory_server.py          # API服务器
├── inventory_client.py          # 客户端
├── inventory_configurator.py    # 配置器
├── inventory_db_complete.py     # 数据库模块
├── inventory_print.py           # 打印模块
├── inventory_backup.py          # 备份模块
├── inventory_manager_complete.py # 服务端GUI
├── db_config.py                 # 数据库配置
├── 启动库存服务器.bat
├── 启动库存客户端.bat
├── 启动配置器.bat
├── 启动库存管理系统.bat
├── 部署说明.md
├── README.md
└── requirements.txt
```

## 注意事项

1. 服务器和客户端的API密钥必须一致
2. 服务器监听地址设为 `0.0.0.0` 可让局域网访问
3. 请确保防火墙开放对应端口
4. 定期备份数据库数据
5. 妥善保管API密钥

## 许可证

本项目为不锈钢网带跟单系统的配套组件。

## 技术支持

如有问题，请参考 `部署说明.md` 中的常见问题章节。
