# PERFORMANCE_BASELINE.md（性能基线）

> 文档版本：v1.1（2026-06-13 修订）
> 采集工具：collect_baseline.py
> 样本数：10/端点

---

## ⚠️ 重要说明

**当前状态**：`collect_baseline.py` 已运行，但**服务未启动**（5008/5003/8008 端口均未监听），所有端点返回连接超时（~2050ms），**数据无效**。

**真实基线待采集**：需先启动 mobile_api_ai 服务，再次运行 `collect_baseline.py`。

**审计结论**：性能基线数据**缺失**，需在实施模块化改造前**真实采集**。

---

## 一、基线数据（待采集 - 模板）

| 端点 | 描述 | AVG (ms) | P50 (ms) | P95 (ms) | MAX (ms) |
|------|------|----------|----------|----------|----------|
| `/api/all-process-tasks?page=1&size=50` | 工序任务列表 | ⬜ 待填 | ⬜ 待填 | ⬜ 待填 | ⬜ 待填 |
| `/api/perf/stats` | 性能统计 | ⬜ 待填 | ⬜ 待填 | ⬜ 待填 | ⬜ 待填 |
| `/api/process_sub_step` | 报工提交 | ⬜ 待填 | ⬜ 待填 | ⬜ 待填 | ⬜ 待填 |
| `/api/scan-info?order_no=WO-001` | 扫码查询 | ⬜ 待填 | ⬜ 待填 | ⬜ 待填 | ⬜ 待填 |

---

## 二、采集步骤

### 2.1 启动服务

```bash
# 1. 启动 mobile_api_ai 服务
cd D:\yuan\不锈钢网带跟单3.0\mobile_api_ai
python app.py

# 或使用启动脚本
.\start_mobile_api.bat

# 2. 确认端口监听
netstat -an | findstr 5008
# 应输出: TCP    0.0.0.0:5008    ...    LISTENING
```

### 2.2 启动依赖服务

| 服务 | 端口 | 启动命令 |
|------|------|----------|
| mobile_api_ai | 5008 | `python app.py` |
| 调度中心 | 5003 | `cd dispatch_center && python _core.py` |
| Sync Bridge | 8008 | `python sync_bridge.py` |
| 容器中心 | 5002 | `python container_center_api.py` |

### 2.3 运行采集

```bash
# 在项目根目录
cd D:\yuan\不锈钢网带跟单3.0
python collect_baseline.py

# 输出: docs/模块化改造/PERFORMANCE_BASELINE.md
```

### 2.4 验证数据有效性

采集完成后，检查：
- ✅ AVG < 1000ms（正常服务应 < 500ms）
- ✅ P95 < 2000ms
- ✅ MAX < 5000ms

若 AVG > 1000ms 或 P95 > 2000ms，说明采集时服务未正常响应，需检查服务状态后重采。

---

## 三、性能目标（参考值）

| 端点 | 当前基线 | 目标 | 提升 |
|------|----------|------|------|
| 工序任务列表 | ⬜ 待填 | < 50ms | - |
| 报工提交 | ⬜ 待填 | < 80ms | - |
| 扫码查询 | ⬜ 待填 | < 50ms | - |

**目标来源**：方案中的"30-50% 提升"目标，需在采集基线后计算实际目标值。

---

## 四、采集说明

- **环境**：开发环境，CPU/Memory 正常
- **数据量**：1000 条 process_records
- **数据库**：本地 MySQL
- **缓存**：已启用（TTL=10s）

---

## 五、改造后对比模板

实施模块化改造后，**再次采集**并填充下表：

| 端点 | 改造前 | 改造后 | 提升 |
|------|--------|--------|------|
| 工序任务列表 | ⬜ | ⬜ | ⬜ |
| 报工提交 | ⬜ | ⬜ | ⬜ |
| 扫码查询 | ⬜ | ⬜ | ⬜ |

---

## 六、参考

- [ARCHITECT_全面模块化改造.md](./ARCHITECT_全面模块化改造.md)
- [DAL_DESIGN.md](./DAL_DESIGN.md)
- collect_baseline.py
