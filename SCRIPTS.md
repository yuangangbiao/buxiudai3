# 脚本管理规范

## 目录结构

```
根目录/
├── scripts/          长期业务脚本（永久保留）
├── tools/            一次性工具（用完即删）
├── archive/          归档旧版和废弃脚本（定期清理）
├── _test/           临时手动测试（≤7天删除）
├── tests/            正式测试代码（永久保留）
├── models/           数据模型
├── core/             核心模块
├── mobile_api_ai/   移动端API服务
└── docs/            文档
```

## 脚本分类

| 目录 | 含义 | 保留时间 | 示例 |
|------|------|---------|------|
| `scripts/` | 长期使用的业务脚本 | 永久 | `publish_wo.py`、`sync_order.py` |
| `tools/` | 一次性诊断/调试工具 | **≤30天** | `find_missing_orders.py`、`diag_db.py` |
| `archive/` | 旧版本/废弃脚本 | **≤1年** | `fix_r13_b0_v2.py`（归档后） |
| `_test/` | 临时手动测试 | **≤7天** | `test_order_api.py`、`check_response.py` |
| `tests/` | 正式测试代码 | 永久 | `test_dispatch.py`、`e2e_login_test.py` |

## 命名规则

### ✅ 推荐命名

```
<动词>_<名词>.py
```

示例：
- `publish_work_order.py` — 发布工单
- `sync_order_to_mysql.py` — 同步订单到MySQL
- `find_missing_processes.py` — 查找缺失工序
- `backup_container_db.py` — 备份容器数据库

### ❌ 禁止使用的前缀

| 前缀 | 原因 | 正确做法 |
|------|------|---------|
| `diag_*.py` | 诊断脚本，应用完即删 | `diagnose_<问题>.py`，完成后删除 |
| `debug_*.py` | 调试脚本，应用完即删 | `debug_<功能>.py`，完成后删除 |
| `fix_*.py` | 临时修复，应用完即删 | `fix_<问题>.py`，完成后删除 |
| `check_*.py` | 检查脚本，应用完即删 | `check_<目标>.py`，完成后删除 |
| `verify_*.py` | 验证脚本，应用完即删 | `verify_<目标>.py`，完成后删除 |
| `*_v2.py` | 版本文件，完成后删除旧版 | 只保留最终版，旧版归档 |
| `*_test.py` | 测试脚本，完成后删除 | 正式测试放 `tests/` 目录 |
| `*_e2e.py` | E2E测试，完成后删除 | 正式测试放 `tests/e2e/` |
| `probe_*.py` | 探测脚本，应用完即删 | `probe_<目标>.py`，完成后删除 |
| `scan_*.py` | 扫描脚本，应用完即删 | `scan_<目标>.py`，完成后删除 |

## 生命周期管理

### 一次性工具（tools/）

```
创建 → 使用 → 判断是否保留
         ↓
    ┌─ 会再用？→ 移到 scripts/，重命名
    ↓
    └─ 不会用？→ 删除
```

### 版本迭代

```
v1.py → v2.py → v3.py（最终版）
           ↓
         归档（只保留 v3）
```

### 诊断/调试脚本

```
创建（放在 tools/） → 使用 → 删除
```

## 定期清理

### 每周

- 检查 `tools/` 目录，删除超过 30 天未使用的脚本

### 每月

- 检查 `_test/` 目录，删除超过 7 天未使用的脚本

### 每半年

- 检查 `archive/` 目录，删除超过 1 年的归档脚本

## 违规处理

如果发现违反规范的脚本，立即处理：

1. `diag_`、`debug_`、`fix_` 等前缀 → 移到 `tools/` 或删除
2. `*_v2/v3/v4.py` 旧版本 → 只保留最终版，其余归档或删除
3. 散落在根目录的临时脚本 → 按用途分类到对应目录

## 违反规范的示例

```bash
# ❌ 错误：根目录散落临时脚本
根目录/diag_order_status.py
根目录/fix_order_bug.py
根目录/check_mysql.py

# ✅ 正确：按用途分类
tools/diagnose_order_status.py    # 诊断工具
tools/fix_order_bug.py           # 临时修复
scripts/check_mysql.py          # 长期检查工具
```

## 快速参考

```
问自己：这个脚本以后还会用到吗？

如果"是"：
  └─ 会长期用？→ 移到 scripts/
  └─ 只会用一两次？→ 留在 tools/，用完删除

如果"否"：
  └─ 有参考价值？→ 归档到 archive/
  └─ 没有参考价值？→ 直接删除
```
