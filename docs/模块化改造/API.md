# API.md（5002 容器中心 API 文档）

> 文档版本：v1.0（2026-06-13）
> 适用：5002 容器中心 HTTP API
> Base URL：`http://localhost:5002`

---

## 一、API 列表

| 路径 | 方法 | 用途 | 鉴权 |
|------|------|------|------|
| `/api/health` | GET | 健康检查 | 无 |
| `/api/orders/<order_no>` | GET | 查询订单 | API Key |
| `/api/process_sub_step` | POST | 创建报工子步骤 | API Key |
| `/api/process_sub_steps/<order_no>/<process_code>` | GET | 查询工序子步骤 | API Key |
| `/api/process_sub_steps/<order_no>` | GET | 查询订单所有子步骤 | API Key |
| `/api/process_sub_step_summary/<order_no>` | GET | 报工汇总 | API Key |
| `/api/process_sub_step/summary_by_order/<order_no>` | GET | 报工汇总（同上）| API Key |
| **`/api/process_sub_steps/mirror`** | **POST** | **8008 镜像写入** | **IP 白名单** |

---

## 二、API 详细说明

### 2.1 `/api/process_sub_steps/mirror`（8008 镜像写入）

**用途**：8008 sync_bridge 在写 steel_belt.process_sub_steps 后，回写本路由同步到镜像表。

**鉴权**：
- IP 白名单：`127.0.0.1`, `::1`, `localhost`
- 共享密钥：`X-Mirror-Secret: <MIRROR_SHARED_SECRET>`（环境变量）

**请求**：

```json
POST /api/process_sub_steps/mirror
Content-Type: application/json
X-Trace-Id: <自动生成>

{
  "uuid": "abc-123-def-456",
  "process_id": "P001",
  "process_record_id": "P001",
  "order_no": "ORD-20260613-001",
  "step_name": "入库",
  "batch_no": "STK-20260613-ABC123",
  "quantity": 100.50,
  "qualified_qty": 100.00,
  "operator": "张三",
  "operator_id": "OP-001",
  "wechat_userid": "userid@corp",
  "equipment_name": "1号机",
  "remark": "正常入库",
  "record_date": "2026-06-13",
  "source": "sync_bridge",
  "overtime_hours": 0,
  "synced": 1,
  "synced_at": "2026-06-13 10:00:00",
  "created_at": "2026-06-13 10:00:00"
}
```

**响应（成功）**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "mirror_uuid": "abc-123-def-456"
  }
}
```

**响应（失败）**：

| 状态码 | code | message | 原因 |
|--------|------|---------|------|
| 400 | 1001 | 缺少必填字段 uuid/order_no | 字段缺失 |
| 403 | 6001 | 镜像路由鉴权失败 | IP 不在白名单 / 密钥错误 |
| 500 | 1501 | 数据库错误 | DB 写入失败 |

---

### 2.2 `/api/orders/<order_no>`

**用途**：查询订单信息。

**鉴权**：API Key（`X-API-Key` header）

**请求**：

```
GET /api/orders/ORD-20260613-001
X-API-Key: <your_key>
```

**响应（成功）**：

```json
{
  "code": 0,
  "data": {
    "order_no": "ORD-20260613-001",
    "customer_name": "客户A",
    "product_name": "产品1",
    "quantity": 1000.00,
    "status": "confirmed",
    "plan_start": "2026-06-15 00:00:00",
    "plan_end": "2026-06-30 00:00:00",
    "is_deleted": 0,
    "_source": "etl",
    "_synced_at": "2026-06-13 10:00:00"
  }
}
```

**响应（失败）**：

| 状态码 | code | message | 原因 |
|--------|------|---------|------|
| 404 | 2001 | 订单不存在 | order_no 不存在 |
| 500 | 1501 | 数据库错误 | DB 查询失败 |

---

### 2.3 `/api/process_sub_step`

**用途**：创建报工子步骤（分批入库/发货）。

**鉴权**：API Key

**请求**：

```json
POST /api/process_sub_step
Content-Type: application/json
X-API-Key: <your_key>

{
  "order_no": "ORD-20260613-001",
  "step_name": "入库",
  "quantity": 100.50,
  "operator": "张三",
  "remark": "正常入库",
  "qualified_qty": 100.00
}
```

**响应（成功）**：

```json
{
  "code": 0,
  "message": "子步骤已创建",
  "data": {
    "sub_step_id": "abc-123-def-456",
    "batch_no": "STK-20260613-ABC123"
  }
}
```

**响应（失败）**：

| 状态码 | code | message | 原因 |
|--------|------|---------|------|
| 400 | 2001 | 订单不存在或已删除 | F4 校验 |
| 400 | 3004 | 工序名称非法 | F5 白名单 |
| 400 | 3003 | 报工数量非法 | F12 Decimal 校验 |
| 500 | 1501 | 数据库错误 | DB 写入失败 |

---

## 三、错误码字典

详见 `mobile_api_ai/utils/error_codes.py` 和 `docs/模块化改造/ERROR_CODES.md`。

| 类别 | 区间 | 含义 |
|------|------|------|
| 0 | 0 | 成功 |
| 1xxx | 1001-1599 | 通用错误（参数/权限/系统）|
| 2xxx | 2001-2599 | 订单错误 |
| 3xxx | 3001-3599 | 报工错误 |
| 4xxx | 4001-4599 | 排产错误 |
| 5xxx | 5001-5599 | 同步错误 |
| 6xxx | 6001-6599 | 容器/镜像错误 |
| 9xxx | 9001-9599 | 业务自定义 |

---

## 四、统一响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

---

## 五、版本

- v1.0（2026-06-13）：初始版本，覆盖 8 个 API

---

## 六、参考

- [ERROR_CODES.md](./ERROR_CODES.md) - 错误码字典
- [BACKUP.md](./BACKUP.md) - 备份恢复
- [RUNBOOK.md](./RUNBOOK.md) - 运维操作
