# DESIGN_消除裸except.md — 架构设计方案

> 编制日期：2026-05-21
> 关联任务：改进计划 Phase 1（代码质量）

## 一、现状分析

### 1.1 问题说明

`except:`（裸 except）会捕获包括 `SystemExit`、`KeyboardInterrupt` 在内的所有异常，可能导致：
- 无法通过 Ctrl+C 中断程序
- 静默吞掉关键错误信号
- 排除错（如 `except:` 覆盖了本该冒泡的编程错误）

### 1.2 调研范围

**范围 A — 核心业务文件**（25 个文件，约 52 处出现），排除：
- `scripts/` — 一次性调试脚本
- `mobile_api_ai/scripts/tools/` — 运维工具
- `打包脚本/` — 部署打包脚本
- `mobile_api_ai/云端部署包/` — 备份包
- `inventory_*.py` — 已归档的旧版文件

### 1.3 核心文件清单

| # | 文件 | 出现次数 |
|---|------|---------|
| 1 | `main.py` | 3 |
| 2 | `core/error_handler.py` | 1 |
| 3 | `views/process_view.py` | 2 |
| 4 | `views/quality_rule_view.py` | 1 |
| 5 | `views/dialogs/rule_dialogs.py` | 2 |
| 6 | `views/dialogs/base.py` | 1 |
| 7 | `views/material_prep_view.py` | 2 |
| 8 | `views/shipment_view.py` | 1 |
| 9 | `views/production_view.py` | 2 |
| 10 | `views/process_calc_rule_view.py` | 4 |
| 11 | `views/orders/new_order_dialog.py` | 12 |
| 12 | `views/orders/confirm.py` | 2 |
| 13 | `views/finished_product_stats_view.py` | 1 |
| 14 | `views/dashboard/dashboard_server.py` | 2 |
| 15 | `models/quality_rule.py` | 3 |
| 16 | `models/order.py` | 2 |
| 17 | `models/production.py` | 1 |
| 18 | `models/process_calc_rule.py` | 4 |
| 19 | `models/alert.py` | 3 |
| 20 | `services/order_service.py` | 1 |
| 21 | `updater.py` | 5 |
| 22 | `utils/excel_utils.py` | 2 |
| 23 | `utils/app_init.py` | 1 |
| 24 | `utils/window_manager.py` | 1 |
| 25 | `start_services.py` | 1 |
| 26 | `mobile_api_ai/dispatch_center.py` | 1 |
| 27 | `mobile_api_ai/sync_bridge.py` | 1 |

## 二、分类替换策略

### 2.1 模式分类

所有裸 `except:` 可归纳为 3 种模式：

#### 模式 A — JSON/日期解析回退（~20 处）
典型：
```python
try:
    extra = json.loads(extra_str)
except:       # ← 裸 except
    extra = {}
```

**替换方案**：`except Exception:`，保持回退逻辑不变。
**理由**：解析失败是正常控制流，回退到默认值是预期行为。

#### 模式 B — GUI/资源操作容错（~16 处）
典型：
```python
try:
    win.destroy()
except:       # ← 裸 except
    pass
```

**替换方案**：`except Exception:`，保持 pass 不变。
**理由**：窗口关闭、pack 操作等可能在组件已销毁时失败，容错是合理的。

#### 模式 C — messagebox 回退（~5 处）
典型：
```python
try:
    messagebox.showerror("错误", msg)
except:       # ← 裸 except
    print(msg)
```

**替换方案**：`except Exception:`，保持 print 不变。
**理由**：tkinter 在非 GUI 线程或已关闭时抛异常，print 回退是合理设计。

### 2.2 替换规则

```
# 规则 1：所有情况
except:  →  except Exception:

# 规则 2：有明确预期异常类型的改用窄类型
例如：
  float(data)  →  except (ValueError, TypeError):
  json.loads() →  except (json.JSONDecodeError, TypeError):
```

### 2.3 例外处理

以下 2 处建议改用更具体的异常类型：

| 位置 | 当前 | 建议 |
|------|------|------|
| `process_view.py:811` `float(data.get(...))` | `except:` + `alert()` | `except (ValueError, TypeError):` |
| `models/quality_rule.py:375` `float(measured_str)` | `except:` + `measured = 0` | `except (ValueError, TypeError):` |
| `models/process_calc_rule.py:274` `float(val)` | `except:` + `val = 0` | `except (ValueError, TypeError):` |
| `models/process_calc_rule.py:352` `float(val)` | `except:` + `return 0.0` | `except (ValueError, TypeError):` |

## 三、风险控制

### 3.1 不改动的范围
- 不修改 `except` 块体内部的逻辑
- 不加 `logger`（这是另一个 P0 任务）
- 不重构 try 块结构
- 不改动 `mobile_api_ai/wechat_server.py`（云端专用，禁止本地修改）

### 3.2 验证方案
1. 每个修改文件用 `python -m py_compile` 验证编译
2. 核心模块（main.py、process_view.py、models/）至少编译通过

## 四、执行方案

### 选项 1 — 手动逐文件修改
逐个打开每个文件，定位并替换。安全但耗时（约 1.5h）。

### 选项 2 — Python 脚本批量替换
编写脚本对指定文件列表做正则替换 `except:` → `except Exception:`。
然后逐一 review 替换结果。高效（约 15min 脚本 + 20min review）。

### 选项 3 — 混合模式
先用脚本批量替换全部文件，再手动处理 4 处需窄化异常类型的特例。

**推荐：选项 3**。脚本保证一致性，人工处理保证精确性。
