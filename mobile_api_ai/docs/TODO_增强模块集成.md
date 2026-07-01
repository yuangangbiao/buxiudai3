# 增强模块集成 - 待办事项清单

## 环境配置

### 1. 安装增强模块依赖（如果重新部署新环境）
```bash
pip install redis>=4.5.0 elasticsearch>=8.0.0 psutil>=5.9.0
pip install ntplib>=0.4.0 msgpack>=1.0.0 prometheus-client>=0.17.0
```

### 2. 数据库/中间件配置（按需启用）
| 服务 | 用途 | 是否必需 | 配置方式 |
|------|------|----------|----------|
| **Redis** | 队列管理、熔断器 | 可选（无Redis自动降级） | 环境变量 REDIS_HOST/REDIS_PORT |
| **Elasticsearch** | 审计日志存储 | 可选 | 环境变量 ES_HOSTS |
| **NTP服务** | 时钟同步 | 可选 | Windows 已内置时间同步 |

## 生产部署

### 打包部署
```bash
# 在项目根目录运行
一键打包.bat
```
- 生成的 exe 在 `dist/WeChatBotServer.exe`
- DAT 配置文件在 `dist/DAT/`

### 环境变量配置
在 `DAT/.env` 中添加（可选）：
```env
# 备份配置
BACKUP_DIR=./DAT/backup
BACKUP_RETENTION_DAYS=7

# Redis（可选）
REDIS_HOST=localhost
REDIS_PORT=6379
```

## 待验证项

- [ ] 在服务器上运行 exe，检查增强模块是否正确加载
- [ ] 测试熔断器保护（模拟连续失败场景）
- [ ] 测试队列管理（配置 Redis 后验证消息排队）
- [ ] 测试状态监控 API：
  - `GET /api/sync/circuit/status`
  - `POST /api/sync/circuit/reset`
  - `GET /api/sync/queue/status`
  - `GET /api/sync/queue/stats`

## 已知限制

1. **QueueManager**：需要 Redis 服务才可激活完整功能，无 Redis 时自动跳过
2. **ES备份**：需要 Elasticsearch 和 curl 命令，当前环境未安装
3. **增强备份**：备份目录默认为 `DAT/backup`，可通过 `BACKUP_DIR` 环境变量修改
4. **熔断器参数**：当前阈值在 wechat_server.py 初始化时硬编码，后续可迁移到配置
