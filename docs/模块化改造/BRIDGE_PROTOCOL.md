# BRIDGE_PROTOCOL.md（8008 桥接协议）

> 文档版本：v1.0（2026-06-13）

---

## 一、概述

8008 Sync Bridge 是手机端、容器中心、调度中心等内部服务与 steel_belt 数据库之间的桥接服务。

### 1.1 角色

| 角色 | 端口 | 用途 |
|------|------|------|
| Sync Bridge | 8008 | 内部桥接（仅内部服务调用） |
| 调度中心 | 5003 | 企业微信消息总线（**只发微信**） |
| Sync Client | - | 各服务的桥接客户端 |

### 1.2 调用关系

```
手机端(5008) ─┐
容器中心(5002) ─┤──> Sync Bridge(8008) ──> steel_belt
库存管理(5010) ─┤
调度中心(5003) ─┘ (仅接收 5003 的微信消息)

云端(5006) ─> 调度中心(5003) [禁止调 8008]
```

---

## 二、API 协议

### 2.1 统一请求格式

```json
POST /api/sync/{action}
Content-Type: application/json
{
  "order_no": "WO-001",
  "data": { ... },
  "timestamp": 1234567890
}
```

### 2.2 统一响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

### 2.3 错误码

| 范围 | 类别 |
|------|------|
| 0 | 成功 |
| 1600-1699 | 同步错误（详见 ERROR_CODES.md） |

---

## 三、核心接口

### 3.1 报工同步 `/api/sync/sub-step-report`

**用途**：手机端扫码报工同步到 steel_belt

**请求**：
```json
{
  "order_no": "WO-001",
  "step_name": "P01",
  "batch_no": "B001",
  "quantity": 10.5,
  "qualified_qty": 10.0,
  "operator": "张三",
  "operator_id": 100,
  "wechat_userid": "zhangsan",
  "equipment_name": "织机1",
  "remark": "",
  "overtime_hours": 0
}
```

**响应**：
```json
{
  "code": 0,
  "message": "success",
  "data": { "sub_step_id": 12345 }
}
```

### 3.2 状态变更 `/api/sync/status-change`

**用途**：订单/工序状态变更同步

**请求**：
```json
{
  "order_no": "WO-001",
  "new_status": "in_production",
  "operator": "李四"
}
```

### 3.3 质检上报 `/api/sync/quality-report`

**用途**：质检结果同步

**请求**：
```json
{
  "order_no": "WO-001",
  "result": "qualified",
  "defect_description": "",
  "inspector": "王五"
}
```

### 3.4 健康检查 `/health`

**用途**：服务健康检查

**响应**：
```json
{
  "code": 0,
  "data": {
    "status": "healthy",
    "db": "connected",
    "uptime": 12345
  }
}
```

---

## 四、降级队列

### 4.1 触发条件

- steel_belt 写入失败
- 网络超时
- 数据库锁等待

### 4.2 降级流程

```
[同步请求] → 8008 → steel_belt
            ↓ (失败)
         outbox 队列（落盘）
            ↓
         后台线程重试
            ↓ (成功)
         删除队列项
```

### 4.3 监控

| 指标 | 阈值 | 告警 |
|------|------|------|
| 队列长度 | > 100 | WARNING |
| 队列长度 | > 1000 | ERROR |
| 重试次数 | > 5 | WARNING |
| 队列堆积时间 | > 1 小时 | ERROR |

---

## 五、安全

### 5.1 鉴权

- 内部服务调用：共享密钥（`X-Bridge-Token` header）
- 外部调用：禁止

### 5.2 限流

- 单服务：100 QPS
- 全局：500 QPS

### 5.3 日志

- 请求/响应：DEBUG 级别
- 错误：ERROR 级别
- 慢请求：WARNING 级别

---

## 六、部署

### 6.1 启动

```bash
python sync_bridge.py
# 监听 8008 端口
```

### 6.2 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SYNC_BRIDGE_PORT` | 8008 | 监听端口 |
| `SYNC_BRIDGE_LOG_LEVEL` | INFO | 日志级别 |
| `STEELBELT_DB_HOST` | 127.0.0.1 | steel_belt 主机 |
| `OUTBOX_DIR` | /tmp/sync_outbox | 降级队列目录 |

---

## 七、参考

- [DAL_DESIGN.md](./DAL_DESIGN.md)
- [ERROR_CODES.md](./ERROR_CODES.md)
- [FALLBACK.md](./FALLBACK.md)
