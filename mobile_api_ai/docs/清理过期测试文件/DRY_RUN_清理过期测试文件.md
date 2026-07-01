# Dry-Run 报告 - 清理过期测试文件

> **生成时间**: 2026-06-23 23:44
> **基准日**: 2026-06-20
> **执行策略**: 全面清理

---

## 一、待清理文件汇总

| 序号 | 路径 | 数量 | 大小 |
|------|------|------|------|
| 1 | `mobile_api_ai/*.log`（根目录） | 39 | 0.23 MB |
| 2 | `mobile_api_ai/logs/*.log`（根目录） | 41 | ~3.4 MB |
| 3 | `mobile_api_ai/logs/inventory_api/2026-05-27~06-12.log` | 13 | ~1.6 MB |
| 4 | `mobile_api_ai/logs/inventory_api/2026-06-14 21-3x.log` | 6 | ~16 KB |
| 5 | `mobile_api_ai/logs/cloud_relay/2026-06-06.log` | 1 | 850 B |
| 6 | `mobile_api_ai/logs/container_api/2026-05-15.log` | 1 | 25 KB |
| 7 | `mobile_api_ai/logs/wechat_cloud/2026-05-15~06-10.log` | 5 | ~2 MB |
| 8 | `mobile_api_ai/logs/wechat_server/2026-05-14~06-17 15-22-48.log` | 12 | ~13.2 MB |
| 9 | `logs/*.log`（项目根，含 5 个子目录） | 75,542 | 138.44 MB |
| **合计** | — | **75,660** | **~155.4 MB** |

注：因数量较大，序号 9 的 75,542 个文件未在文档中列出（见后续 PowerShell 命令逐批执行）。

---

## 二、保留文件清单（核验通过）

| 路径 | 大小 | 修改时间 | 保留理由 |
|------|------|---------|---------|
| `mobile_api_ai/modules/DAT/audit_log/audit_20260614.log` | 1.9 MB | 2026-06-14 22:59 | **业务审计数据**（订单状态变更） |
| `mobile_api_ai/modules/DAT/audit_log/audit_20260615.log` | 100 KB | 2026-06-15 14:11 | 业务审计 |
| `mobile_api_ai/modules/DAT/audit_log/audit_20260617.log` | 4 KB | 2026-06-17 18:39 | 业务审计 |
| `mobile_api_ai/modules/DAT/audit_log/audit_20260619.log` | 132 KB | 2026-06-19 23:12 | 业务审计 |
| `mobile_api_ai/modules/DAT/audit_log/audit_20260620.log` | 29 KB | 2026-06-20 23:58 | 业务审计（基准日） |
| `mobile_api_ai/modules/DAT/audit_log/audit_20260621.log` | 94 KB | 2026-06-21 11:36 | 业务审计 |
| `mobile_api_ai/modules/DAT/audit_log/audit_20260623.log` | 1.3 KB | 2026-06-23 23:41 | 业务审计（最新） |
| `mobile_api_ai/logs/bridge_err.log` | 64 MB | 2026-06-20 11:56 | ≥06-20 基准日，保留 |
| `mobile_api_ai/logs/dispatch_callers.log` | 2 KB | 2026-06-23 23:41 | **当前正在写入**，必须保留 |
| `scripts/test_ux_xiaoxi.log` | 6.8 KB | 2026-06-23 14:25 | 用户产品体验测试输出（今天） |
| `.trae/logs/pytest_p7.log` | 42 KB | 2026-06-09 22:55 | pytest 历史日志（白名单） |
| `.coveragerc` | 98 B | — | coverage 配置文件 |
| `tests/logs/.gitkeep` | 0 B | — | 测试日志目录占位 |

**保留文件总数：13 个**

---

## 三、清理命令（计划执行）

### Step 1: 清理 mobile_api_ai/ 根目录 .log（39 个）
```powershell
Get-ChildItem -Path "d:\yuan\不锈钢网带跟单3.0\mobile_api_ai" -Filter "*.log" -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -lt (Get-Date "2026-06-20") } | Remove-Item -Force
```

### Step 2: 清理 mobile_api_ai/logs/ 过期日志（约 79 个）
```powershell
Get-ChildItem -Path "d:\yuan\不锈钢网带跟单3.0\mobile_api_ai\logs" -Filter "*.log" -Recurse -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -lt (Get-Date "2026-06-20") } | Remove-Item -Force
```

### Step 3: 清理项目根 logs/ 全部（75,542 个）
```powershell
Get-ChildItem -Path "d:\yuan\不锈钢网带跟单3.0\logs" -Filter "*.log" -Recurse -ErrorAction SilentlyContinue | Remove-Item -Force
```

### Step 4: 复核保留文件未被误删
```powershell
Get-ChildItem -Path "d:\yuan\不锈钢网带跟单3.0\mobile_api_ai\modules\DAT\audit_log" -ErrorAction SilentlyContinue | Measure-Object | Select-Object Count
```

---

## 四、风险与回滚

### 4.1 风险评估
- **风险等级**：低（删除操作不可逆，但保留文件已通过核验）
- **数据丢失风险**：0（仅删除日志文件，未涉及业务数据、代码、配置）
- **误删风险**：低（保留文件已逐项核验）

### 4.2 回滚策略
- 不可回滚（已删除）
- 缓解：保留文件清单已固化在本文档，可作为审计凭证
- 业务审计数据保护：modules/DAT/audit_log/ 全部 7 个文件未列入清理范围

---

**用户已确认执行。进入 Step 1-3 分批清理。**
