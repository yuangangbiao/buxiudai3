# tools/ 目录规范

## 用途

存放**一次性工具脚本**——诊断、调试、临时修复、临时数据处理等。

用完即删，不得长期保留。

## 命名规范

### 允许的命名方式

```
<用途>_<说明>.py
```

示例：
```
find_missing_orders.py          # 查找缺失的订单
patch_empty_process_code.py     # 修补空工序编码
diag_database_connection.py     # 诊断数据库连接
```

### 禁止的命名前缀

```
diag_*.py      ← 诊断脚本，完成后删除
debug_*.py     ← 调试脚本，完成后删除
fix_*.py       ← 临时修复，完成后删除
check_*.py     ← 检查脚本，完成后删除
verify_*.py    ← 验证脚本，完成后删除
*_v2.py        ← 版本文件，完成后删除旧版
*_test.py      ← 测试脚本，完成后删除
*_debug.py     ← 调试脚本，完成后删除
probe_*.py     ← 探测脚本，完成后删除
scan_*.py      ← 扫描脚本，完成后删除
e2e_*.py       ← E2E测试，完成后删除
```

## 使用流程

### 1. 创建工具

在 `tools/` 下创建脚本，命名清晰：

```bash
# 正确
python tools/diag_order_missing.py

# 错误 - 不要用禁用前缀
python tools/diag_order_missing.py  # ✓ 可以
python tools/check_order.py          # ✗ 不要用 check_ 前缀
```

### 2. 使用完成后

```bash
# 判断是否需要保留
# 问自己：这个脚本以后还会用到吗？

# 如果否 → 删除
rm tools/diag_order_missing.py

# 如果是 → 移到 scripts/ 目录
mv tools/diag_order_missing.py scripts/
```

### 3. 长期使用的工具

如果某个工具经常用到，移到 `scripts/` 目录，并重命名为正式命名：

```
tools/temp_diag.py  →  scripts/diagnose_order.py
```

## 禁止事项

- ❌ 禁止在 `tools/` 目录留下超过 30 天的脚本
- ❌ 禁止将正式业务脚本放在 `tools/` 目录
- ❌ 禁止将 `tools/` 目录下的脚本复制为 `tools/diag_xxx_v2.py` 这种形式

## 当前目录

此目录用于临时工具，完成任务后请清理。
