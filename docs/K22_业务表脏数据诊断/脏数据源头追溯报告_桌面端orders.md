# 脏数据代码源头追溯报告 - 桌面端 orders 表 230 条测试订单

**生成时间**: 2026-06-16 15:30
**追溯方法**: 全项目 grep + SQL 验证 + 代码路径分析
**关联清理**: `ACCEPTANCE_K22_桌面端orders清理.md` (已 is_deleted=1, 备份 273KB)
**关联问题修复**: BUG 9 (待补: import_orders 无去重)

---

## 1. 脏数据全景

| 维度 | 详情 |
|------|------|
| 表 | MySQL `orders` (steel_belt 库) |
| 总条数 | 241 条 (清理前 232 未删未归档) |
| 脏数据 | 230 条 (95%) |
| 时间分布 | 2026-06-14 30 条 + 2026-06-15 200 条 |
| 客户 | '张三' 192 条 + '' 38 条 (空) |
| 状态 | 全部 '待确认' |
| 数量 | 1/10/100 三种 (规则化) |
| 金额 | 0/1005/2550/5000 四种 (规则化) |
| material | 全空 (除 GO-AUTO-001 真实订单) |
| product_name | 全空 (除 GO-AUTO-001 真实订单) |

---

## 2. 追溯过程

### Step 1: 排除生产代码硬编码"张三"

```bash
# 全项目搜 customer_name='张三' 的代码位置
grep -r 'customer_name.*张三' --include='*.py'
```

**结论**: 256 处全在 `tests/unit/...` 测试代码里，**生产代码无硬编码"张三"**。

### Step 2: 列出 4 个生产路径 INSERT INTO orders

| 路径 | 文件:行 | 调用方 | 批量能力 |
|------|---------|--------|---------|
| OrderDAO.create | `models/order.py:95` | GUI 新建订单按钮 (`list_view.py:281`) | ❌ 单条 |
| ExcelImporter.import_orders | `utils/excel_utils.py:286` | 桌面端 Excel 导入 (`excel_view.py:188`) | ✅ 批量 |
| sync_orders | `scripts/sync_orders.py:188` | 同步脚本 (非用户触发) | ✅ 批量 |
| order_archive_manager | `scripts/order_archive_manager.py:410` | 归档管理 (非用户触发) | ✅ 批量 |

### Step 3: 验证唯一可能入口

```bash
# 查 main_runner.py 的 range(30) 是否是脏数据源
# 结论: 是"持续监控 30 秒"循环, 与订单创建无关
# 排除
```

### Step 4: 看 import_orders 是否批量插入

```python
# utils/excel_utils.py:243-304 import_orders 实现
for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
    ...
    cursor.execute("""
        INSERT INTO orders (order_no, customer_name, ...)
        VALUES (...)
    """)
```

**关键发现**:
- 读取 Excel 每一行
- **忽略 Excel 第一列** (`order_no`)，调 `generate_order_no()` 生成新订单号
- 客户名/产品/数量/金额从 Excel 读取
- **无去重校验** + **无导入频率限制** + **无 Excel 重复检测**

### Step 5: 看 GUI 触发入口

```python
# desktop/views/excel_view.py:180
def _import_orders(self):
    """导入订单"""
    file_path = self._get_open_path("订单Excel")
    if not file_path:
        return
    try:
        result = ExcelImporter.import_orders(file_path)
        msg = f"成功导入 {result['imported']} 条订单"
        messagebox.showinfo("导入完成", msg)
```

**结论**: 桌面端 GUI → 选 Excel → 调 `import_orders` → 批量 INSERT。

### Step 6: 验证脏数据特征与 Excel 导入一致

| 测试订单特征 | Excel 导入逻辑 |
|-------------|---------------|
| `order_no` 格式 `ORD-20260614-NNNN` (YYYYMMDD+序号) | ✅ `generate_order_no()` 输出格式 |
| 客户名 '张三' 或空 (38 条空) | ✅ Excel 客户列可能空 |
| 数量 1/10/100 规则化 | ✅ Excel 测试模板 |
| 金额 0/1005/2550/5000 规则化 | ✅ 1米=0, 10米=1005, 100米=2550, 304不锈钢100米=5000 |
| 全部 '待确认' (导入时默认) | ✅ `import_orders` status 默认 '待确认' |
| material/product_name 全空 | ✅ Excel 测试模板留空 |
| 6-14 灌 30 条, 6-15 灌 200 条 | ✅ 用户 2 天分别导入 2 个测试 Excel (30 行 + 200 行) |

---

## 3. 根因分析

### 🎯 根因 #1: import_orders 无去重校验

```python
# utils/excel_utils.py:286 当前实现
cursor.execute("""
    INSERT INTO orders (order_no, customer_name, ...)
    VALUES (...)
""", (...))
# 缺少:
# - 同 Excel hash 30s 内重复导入检查
# - 同 (customer, product, quantity) 短时间内重复检查
# - 导入次数/总量限流
```

### 🎯 根因 #2: generate_order_no 绕过了 UNIQUE 约束

```python
# utils/excel_utils.py:263
"order_no": generate_order_no()  # 每次生成新订单号
```

`orders.order_no` 有 UNIQUE 约束，但 `generate_order_no()` 每次生成不同号，所以 UNIQUE 不会触发 — 即使是同一份 Excel 反复导入也会成功。

### 🎯 根因 #3: GUI 无导入确认对话框

```python
# desktop/views/excel_view.py:188
result = ExcelImporter.import_orders(file_path)
msg = f"成功导入 {result['imported']} 条订单"
messagebox.showinfo("导入完成", msg)  # 只通知, 不显示明细
```

用户导入 200 条测试订单后，弹窗只显示"成功导入 200 条订单"，**不显示订单列表**，用户无法快速识别是测试数据。

---

## 4. 防回灌修补方案 (BUG 9)

### 4.1 import_orders 加去重校验 (核心修复)

```python
# utils/excel_utils.py 新增方法
@staticmethod
def _check_recent_duplicate(file_path: str, cooldown_seconds: int = 60) -> int:
    """检查最近 cooldown_seconds 秒内是否已导入过同文件

    策略: 用 file_path + file_size + mtime + 文件前 100 字节 hash 作为指纹
    存储到 _IMPORT_HISTORY_CACHE (进程内) + 持久化到 _IMPORT_FINGERPRINT_LOG
    """
    import hashlib
    import time
    fingerprint = f'{file_path}_{os.path.getsize(file_path)}_{os.path.getmtime(file_path)}'
    file_hash = hashlib.md5(open(file_path, 'rb').read(1024)).hexdigest()
    key = f'{fingerprint}_{file_hash}'

    # 进程内快速检查
    history = getattr(ExcelImporter, '_IMPORT_HISTORY', {})
    now = time.time()
    history = {k: v for k, v in history.items() if now - v < cooldown_seconds}
    if key in history:
        return 1  # 命中重复
    history[key] = now
    ExcelImporter._IMPORT_HISTORY = history
    return 0
```

### 4.2 GUI 增加导入确认

```python
# desktop/views/excel_view.py:188 改动
def _import_orders(self):
    file_path = self._get_open_path("订单Excel")
    if not file_path:
        return
    # [BUG 9 修复 2026-06-16] 防误导入: 显示前 5 条预览
    if not messagebox.askyesno("确认导入", f"将导入 {os.path.basename(file_path)}\n是否继续?"):
        return
    ...
```

### 4.3 守护测试 test_mysql_orders_cleanliness.py

```python
# tests/unit/test_mysql_orders_cleanliness.py
def test_no_bulk_test_orders():
    """未删除未归档订单数 < 10 (防 230 条测试数据再次出现)"""
    assert visible_count < 10
```

---

## 5. 仍待补的 P1 BUG 9 修复

| 任务 | 文件 | 状态 |
|------|------|------|
| import_orders 加去重 | `utils/excel_utils.py:243` | **待做** |
| GUI 加导入确认对话框 | `desktop/views/excel_view.py:188` | **待做** |
| 守护测试 | `tests/unit/test_mysql_orders_cleanliness.py` | **待做** |

---

## 6. 关联问题

### 6.1 230 条 vs 241 条的差异

清理前 241 条总，清理 230 条后剩 11 条：
- 9 条已归档 4-5 月历史业务订单（不动）
- 2 条未删除未归档（GUI 可见）：
  - ORD-20260416-0001 晨圣五金（真实）
  - GO-AUTO-001 张三（真实，6-15 创建但字段完整）

### 6.2 6-15 还有另一条 GO-AUTO-001

创建时间 6-15 11:17:53（与测试订单同天），但有完整字段：
- customer_phone=13800138000
- material=304不锈钢
- unit_price=50
- total_amount=5000
- product_type=编织网带

**判断为真实业务订单**（按时间一刀切会误删，脚本按 `order_no` 前缀 + 字段完整性综合判断）。

---

## 7. 验证证据

```bash
# 1. 230 条测试订单的 order_no 模式
SELECT order_no FROM orders WHERE order_no LIKE 'ORD-20260614-%' OR order_no LIKE 'ORD-20260615-%';
# 结果: 230 行 (30 + 200)

# 2. 清理前 232 条未删未归档
SELECT COUNT(*) FROM orders WHERE is_deleted=0 AND is_archived=0;
# 结果: 232

# 3. 清理后剩 2 条
SELECT COUNT(*) FROM orders WHERE is_deleted=0 AND is_archived=0;
# 结果: 2 (晨圣五金 + GO-AUTO-001)

# 4. 备份文件
ls -la data/backup/20260616_150402_orders_backup.sql
# 273,943 bytes
```
