# CONSENSUS_消除裸except.md — 共识确认

> 编制日期：2026-05-21

## 需求描述

将核心业务文件中的裸 `except:` 全部替换为 `except Exception:`，消除潜在的安全风险（捕获 SystemExit、KeyboardInterrupt 等）。

## 技术方案

### 替换策略
- **批量替换**：使用 Python 脚本对 27 个核心文件中的 `except:` 进行正则替换
- **精确调整**：对 4 处 float 解析改用 `except (ValueError, TypeError):`
- **不动逻辑**：不修改 except 块体内部代码，不加 logger

### 范围确认
- **范围 A** — 27 个核心业务文件，约 52 处
- **排除**：scripts/、打包脚本/、云端部署包/、归档的旧版文件

## 验收标准

1. 所有核心业务文件 `except:` → `except Exception:` 或具体类型
2. 所有修改文件 `python -m py_compile` 通过
3. 不改变现有业务逻辑
4. 4 处特例使用了更精确的异常类型

## 任务边界
- **不做**：不加 logger 日志（单独 P0 任务）
- **不做**：不修改 except 块体逻辑
- **不做**：不改动一次性脚本和归档文件
