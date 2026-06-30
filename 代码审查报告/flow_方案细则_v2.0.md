# 不锈钢网带跟单系统 v3.0 — 架构方案
> 版本: 2.3 | 日期: 2026-05-30 | 审计: ✅

---

## 一、系统拓扑

```
桌面端(排产) ──POST──► 容器中心 :5002 ──► container_center MySQL
                            │
手机报工 ──GET/POST──► 报工程序 :5008 ──┘
                            │
管理后台 ──────────► 调度中心 :5003 ── 微信Bot推送
                            │
                 ◄── Sync Bridge :8008
                 
库存系统 ◄────► 库存API :5010 ──► inventory_db MySQL
  ↑ 入库(生产/采购/外协)  ↑ 出库(发货/领料)
  └── 流程引擎自动调用 ────┘
```

## 二、服务清单

| 服务 | 端口 | 文件 | 数据库 |
|------|------|------|--------|
| 报工程序 | 5008 | `app.py` | container_center |
| 容器中心 | 5002 | `container_center_api.py` | container_center |
| 调度中心 | 5003 | `standalone_dispatch_server.py` | container_center |
| 库存管理 | 5010 | `inventory_api_server.py` | inventory_db |
| Sync Bridge | 8008 | `sync_bridge_server.py` | — |
| 可视化大屏 | 5000 | `dashboard_server.py` | — |
| 人脸扫描 | 5009 | `face_server.py` | — (独立服务) |

## 三、UI 布局 (server_launcher.py)

```
┌─────────────┐ ┌─────────────┐
│  报工程序   │ │  容器中心   │
│    5008     │ │    5002     │
├─────────────┤ ├─────────────┤
│  调度中心   │ │  库存管理   │
│    5003     │ │    5010     │
├─────────────┤ ├─────────────┤
│ Sync Bridge │ │  可视化大屏 │
│    8008     │ │    5000     │
└─────────────┘ └─────────────┘

─── 独立服务 ───
  ┌─────────────┐
  │  人脸扫描   │
  │    5009     │
  └─────────────┘
```

## 四、流程引擎

| flow_type | 步数 | 触发 | 联动 |
|-----------|------|------|------|
| `production` | 8 | 桌面/默认 | 报工→质检→**入库** |
| `material_purchase` | 5 | 桌面/维修 | 到货→**入库**→领料→**出库** |
| `quality` | 4 | 桌面质检 | 放行→**入库** |
| `repair` | 5 | 微信报修 | 维修(记配件)→完工 |
| `outsource` | 8 | 桌面外协 | 回厂→**入库** |

流程判定: `flow_type` 字段 > `product_flow_map` > 默认 `production`

### 生产流程 (8步)
```
工单发布 → 排产制定 → 排产确认 → 生产执行 → 质检审核(并行)
→ 报工完成 → 完工入库 → 发货
```

### 物料采购 (5步)
```
物料申请 → 任务确认 → 回复采购期限 → 入库通知 → 物料出库
```

### 独立质检 (4步)
```
接收质检任务 → 检测结果判断 → 审核放行 → 入库
```

### 设备维修 (5步)
```
设备报修 → 接单确认 → 维修执行(记配件文本) → 验收测试 → 完工
```

### 外协加工 (8步)
```
外协发单 → 外协确认 → 外协生产 → 外协质检 → 外协回厂
→ 质检审核(并行) → 入库 → 发货
```

## 五、数据库

### container_center (流程/报工/调度)

| 表 | 行 | 说明 |
|----|-----|------|
| `process_records` | 1 | 流程记录(flow_type, steps, status) |
| `product_flow_map` | 13 | 产品映射(deprecated) |
| `enterprise_structure` | 1 | 企业架构(部门/人员) |
| `data_packages` | 3 | 工单任务队列 |
| `tbl_documents` | 1 | 文档存储 |

### inventory_db (库存)

| 表 | 行 | 说明 |
|----|-----|------|
| `products` | 55 | 产品主数据 |
| `inventory` | 220 | 库存明细 |
| `inventory_transactions` | 5 | 出入库流水 |
| `warehouses` | 4 | 仓库 |
| `categories` | 35 | 分类 |
| `suppliers` | 12 | 供应商 |

## 六、存储层

| 配置 | 值 |
|------|-----|
| 存储类型 | `mysql` |
| MySQLStorage | `构想文件/wechat_container数据库MySQL迁移方案/mysql_storage.py` |
| PREFIX | `''` |
| 数据库 | `container_center` |
| 密码 | `.env → MYSQL_PASSWORD` |

## 七、依赖 (requirements.txt)

| 包 | 版本 | 用途 |
|----|------|------|
| `flask` | 3.1.x | Web |
| `pymysql` | 1.2.x | MySQL |
| `requests` | 2.34.x | HTTP |
| `python-dotenv` | 1.2.x | .env |
| `APScheduler` | 3.11.x | 定时 |
| `PyJWT` | 2.13.x | 认证 |
| `cryptography` | 48.x | 加密 |
| `Pillow` | 12.2.x | 图像 |
| `pytest` | 9.0.x | 测试 |

## 八、环境变量 (.env 关键项)

| 变量 | 值 |
|------|-----|
| `CONTAINER_STORAGE_TYPE` | `mysql` |
| `CONTAINER_MYSQL_DATABASE` | `container_center` |
| `MYSQL_HOST` | `127.0.0.1` |
| `CONTAINER_CENTER_URL` | `http://127.0.0.1:5002` |
| `DISPATCH_CENTER_URL` | `http://127.0.0.1:5003` |
| `INVENTORY_API_URL` | `http://127.0.0.1:5010` |
| `FLASK_PORT` | `5008` |

## 九、测试

```
pytest → 1319 passed, 11 skipped
coverage → 50.08%
```

## 十、变更记录

| 日期 | 变更 |
|------|------|
| 05-29 | SQLite→MySQL 迁移, PREFIX='' |
| 05-29 | 表格机器人 sys.path 清除 |
| 05-29 | 全局硬编码/环境变量审计修复 |
| 05-30 | MySQL 标准化建表 |
| 05-30 | 5种流程引擎 |
| 05-30 | 操作员启动加载+云端推送 |
| 05-30 | 依赖版本对齐 |
| 05-30 | 库存管理加入架构+UI |
| 05-30 | 人脸扫描独立服务 |
