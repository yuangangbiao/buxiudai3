# Docker Compose 部署指南 (v3.7.9)

> **创建日期**: 2026-06-25
> **版本**: v3.7.9
> **目标**: 一键拉起 MySQL + 5003 调度中心 + 5008 报工 + Redis 全套基础环境

---

## 1. 架构概览

```
┌────────────────────────────────────────────────────────────┐
│                     Docker Compose Stack                    │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   api (5008)  │  │dispatch(5003)│  │  mysql:8.0   │     │
│  │   app.py      │  │standalone_   │  │ steel_belt   │     │
│  │   报工系统     │  │dispatch_     │  │ container_   │     │
│  │               │  │server.py     │  │   center     │     │
│  └──────┬────────┘  └──────┬────────┘  └──────┬───────┘     │
│         │                  │                   │             │
│         └──────────────────┼───────────────────┘             │
│                            │                                 │
│                  ┌─────────▼──────────┐                     │
│                  │   redis:7-alpine   │                     │
│                  └────────────────────┘                     │
└────────────────────────────────────────────────────────────┘
```

**新增服务 (v3.7.9)**:
- `dispatch` (5003) — 调度中心,启用 `DISPATCH_CENTER_USE_DB=1`,数据写入 `container_center.dispatch_center_tasks` 表

---

## 2. 快速启动

### 2.1 前置条件

- Docker Desktop 4.x+ (含 docker compose v2)
- 项目根目录 `.env` 文件(从 `.env.example` 复制)

```bash
cp .env.example .env
# 编辑 .env 填入 MYSQL_ROOT_PASSWORD, MYSQL_PASSWORD, JWT_SECRET_KEY
```

### 2.2 启动全部服务

```bash
cd mobile_api_ai
docker compose up -d --build
```

### 2.3 仅启动 MySQL + 5003 (本任务范围)

```bash
cd mobile_api_ai
docker compose up -d mysql redis dispatch
```

### 2.4 验证

```bash
# 检查容器状态
docker compose ps

# 查看 5003 日志
docker compose logs -f dispatch

# 健康检查
curl http://localhost:5003/api/dispatch-center/forward-to-cloud \
    -X POST -H "Content-Type: application/json" \
    -d '{"action":"ping"}'

# 验证 MySQL 表已建
docker compose exec mysql mysql -usteel_belt -p${MYSQL_PASSWORD} \
    -e "USE container_center; SHOW TABLES; DESCRIBE dispatch_center_tasks;"
```

---

## 3. 关键配置说明

### 3.1 `DISPATCH_CENTER_USE_DB`

| 值 | 行为 | 适用场景 |
|---|------|---------|
| `0`(默认) | 内存 Dict 存储 | 单元测试、单进程 demo |
| `1` | MySQL 持久化,DB 异常 fallback 内存 | 生产环境、集成测试 |

Docker 部署强制设为 `1` 以保证数据持久化。

### 3.2 `init.sql` 自动建表

MySQL 容器首次启动时,`init.sql` 会自动:
1. 创建 `container_center` 库
2. 创建 `dispatch_center_tasks` 表 (v3.7.8 引入)

其他业务表(orders, process_records, data_packages 等)由 `utils/auto_schema.py` 在应用启动时自动创建(`IF NOT EXISTS`)。

### 3.3 `command` 覆盖

`docker-compose.yml` 通过 `command` 字段覆盖 Dockerfile 默认启动:
- `api` 服务: `python app.py` (5008 报工)
- `dispatch` 服务: `python standalone_dispatch_server.py` (5003 调度中心)

---

## 4. 集成测试启用 (下一刀)

启动 5003 + MySQL 后,可启用 `tests/integration/test_publisher_e2e.py` 中 4 个 skipped 测试:

```bash
# 1. 启动基础环境
cd mobile_api_ai && docker compose up -d mysql redis dispatch

# 2. 跑集成测试
& "C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe" \
    -m pytest tests/integration/test_publisher_e2e.py -v
```

预期结果: 4 个 skipped 测试变为 PASSED。

---

## 5. 故障排查

| 现象 | 原因 | 解决 |
|------|------|------|
| dispatch 容器反复重启 | `init.sql` 缺 dispatch_center_tasks 表 | 检查 `./init.sql` 是否挂载到 `/docker-entrypoint-initdb.d/` |
| healthcheck 失败 | 5003 未真正启动或路由未注册 | `docker compose logs dispatch` 看启动日志 |
| `pymysql.err.OperationalError: (2003, ...)` | mysql 容器未就绪 | `docker compose ps` 确认 mysql healthy |
| `ModuleNotFoundError: dbutils` | requirements.txt 缺包 | 重建镜像 `docker compose build --no-cache dispatch` |
| `ModuleNotFoundError: waitress` | 缺 WSGI 服务器 | 重建镜像 `docker compose build --no-cache dispatch` |

---

## 6. 升级路径

| 版本 | 变更 |
|------|------|
| v3.7.8 | publisher.py 双轨化 (DB 模式 + 内存 fallback) |
| **v3.7.9** | **docker-compose 集成 5003 + MySQL 容器** |
| v3.8.0 (规划) | container_center_v5 SQLite 收敛到 MySQL |

---

## 7. 文件清单

| 文件 | 状态 | 说明 |
|------|:----:|------|
| `mobile_api_ai/docker-compose.yml` | 修改 | 新增 dispatch 服务 + mysql/redis 复用 |
| `mobile_api_ai/init.sql` | 新增 | 容器首次启动建库 + dispatch_center_tasks |
| `requirements.txt` | 修改 | 增补 dbutils (连接池) + waitress (WSGI) |
| `.env.example` | 修改 | 增补 DISPATCH_CENTER_USE_DB 等环境变量 |
| `docs/v3.7.9/ACCEPTANCE_v3.7.9_docker.md` | 新增 | 完成度报告 |

---

**最后更新**: 2026-06-25
**维护人**: AI 助手
