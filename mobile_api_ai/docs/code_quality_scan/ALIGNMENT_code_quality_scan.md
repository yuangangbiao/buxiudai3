# ALIGNMENT - 全项目代码质量扫描与整改方案

## 1. 项目上下文

### 项目概况
- **项目名**: `mobile_api_ai/` - 不锈钢网带移动报工/调度系统
- **技术栈**: Python Flask + SQLite/MySQL + 企业微信API
- **代码规模**: 大量 Python 文件（入口、服务、模块、脚本、测试等）
- **运行环境**: 云端部署 + 本地开发

### 已有规范文档
- `dispatch_center_refresh.md` - 调度中心页面刷新规范
- `jgs7.md` - 技术执行规范（安全规范、代码规范、shell规范等）
- `业务领域概念定义.md` - 业务流程概念定义

### 已完成的代码质量工作（参考现有审计报告）
| 问题类型 | 修复状态 | 备注 |
|---------|---------|------|
| 密码硬编码 "88888888" | ✅ 已清零 | 全目录零匹配 |
| debug=True 残留 | ✅ 已清零 | 仅审计脚本中有引用 |
| location.reload() | ✅ 已清零 | 全项目零匹配 |

## 2. 本次扫描范围

- **目录**: `d:\yuan\不锈钢网带跟单3.0\mobile_api_ai/`
- **扫描类型**: Python 源码 + JavaScript 前端
- **排除**: `node_modules/`, `.git/`, `__pycache__/`, 归档备份

## 3. 扫描结果汇总

### 3.1 P0 - 安全问题（CRITICAL）

#### [P0-01] 裸 `except:` 语句
| 文件 | 行号 | 代码片段 |
|------|------|---------|
| dispatch_center.py | 343 | `except:` |
| dispatch_center.py | 1758 | `except:` |

- **影响**: 静默吞异常，可能导致难以排查的运行时错误
- **整改要求**: 改为 `except Exception as e:` 并记录日志

#### [P0-02] API_KEY 管理（已符合规范）
- `WECHAT_CLOUD_API_KEY` 从环境变量读取 ✅
- `cloud_config.json` 中存储 `api_key` ✅
- 未硬编码在源码中 ✅

### 3.2 P1 - 代码质量问题（HIGH）

#### [P1-01] `print()` 残留 - 100 处
| 分类 | 文件 | 数量 | 说明 |
|------|------|------|------|
| **生产路径** | dispatch_center.py | ~18处 | 云端轮询器初始化、去重等生产路径 |
| **生产路径** | wechat_server.py | ~4处 | 启动banner（合规使用） |
| **生产路径** | sync_bridge_server.py | ~2处 | 启动banner |
| **测试/调试** | storage_layer.py | ~15处 | `if __name__ == '__main__'` 块中 |
| **测试/调试** | tests/*.py | ~30处 | 测试脚本 |
| **测试/调试** | scripts/tools/*.py | ~20处 | 工具脚本 |
| **调试文件** | debug_compare5.py | ~20处 | 一次性调试文件 |

- **整改优先级**: 生产路径中的 print() 必须改为 logger

#### [P1-02] `sys.path.insert()` 泛滥 - 60 处
| 分类 | 数量 | 说明 |
|------|------|------|
| 入口/服务文件 | ~12处 | dispatch_center.py, app.py, wechat_server.py 等 |
| 工具脚本（scripts/tools/） | ~10处 | 各独立脚本 |
| 测试文件（tests/） | ~10处 | 各测试文件 |
| 一次性脚本 | ~15处 | scripts/check/, scripts/test_*.py 等 |
| 调试文件 | ~13处 | _verify*.py, debug_*.py 等 |

- **规范要求**: 仅在入口文件（如 `config.py` 或 `app.py`）中设置一次，其他模块通过 `from config import BASE_DIR` 导入
- **整改范围**: 仅限生产代码的入口文件；脚本/测试文件可保留但需统一模式

#### [P1-03] 阈值默认值分散 - 60+ 处
| 环境变量KEY | 默认值 | 使用文件数 |
|------------|--------|-----------|
| `REQUEST_TIMEOUT_FAST` | '5' | ~12处 |
| `REQUEST_TIMEOUT_NORMAL` | '10' | ~18处 |
| `REQUEST_TIMEOUT_LONG` | '15' 或 '30' | ~8处 |
| `REQUEST_TIMEOUT_QUICK` | '3' | ~5处 |
| `REQUEST_TIMEOUT_EXTRA` | '30' | ~2处 |
| `SOCKET_CONNECT_TIMEOUT` | '5' | ~4处 |
| 直接硬编码 `connect_timeout=3` | 3 | ~8处 |

- **问题**: 6 种以上不同的 timeout 变量名，默认值不统一
- **整改要求**: 所有阈值默认值统一在 `config.py` 中定义

#### [P1-04] 端口硬编码
| 文件 | 行号 | 内容 |
|------|------|------|
| start_debug.py | 19 | `port=5008` |
| run_app.py | 10 | `port=5008` |
| modules/health_checker.py | 429 | `redis_port=6379` |

- **整改要求**: 端口从环境变量或 config.py 读取，提供默认值但标注来源

#### [P1-05] 中文硬编码路径
| 文件 | 行号 | 内容 |
|------|------|------|
| tests/test_collect.py | 2 | `r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai'` |
| tests/test_api_internal.py | 2 | `r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai'` |
| tests/test_api_internal2.py | 2 | `r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai'` |
| scripts/test_template_render.py | 3 | `r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai'` |
| _check_routes.py | 3 | `r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\云端部署包'` |

- **问题**: 硬编码了含中文的绝对路径，其他机器无法运行
- **整改要求**: 使用 `os.path.dirname(os.path.abspath(__file__))` 推导

#### [P1-06] 测试/调试文件散落根目录
| 文件 | 用途 |
|------|------|
| debug_compare5.py | 一次性调试 |
| debug_start.py | 调试启动 |
| _verify_step2.py, _verify_step3.py, _verify_step4.py | 验证脚本 |
| _verify_fix.py, _bootstrap_check.py, _check_routes.py | 辅助脚本 |
| __test_import.py, __test_redis.py | 测试 |

- **整改要求**: 根目录下保留的调试/验证文件应清理或归入 `scripts/tools/`

### 3.3 P2 - 规范性问题（MEDIUM）

#### [P2-01] 调度中心刷新规范（dispatch_center_refresh.md）
- `location.reload()`: ✅ 已清零
- 需验证每个操作函数末尾是否调用了对应的 `loadXXX()`/`refreshXXX()` 函数
- **检查命令**: 可运行 `dispatch_center_refresh.md` 中的检查脚本验证

#### [P2-02] `except: pass` 裸异常处理
- 已确认裸 `except:` 有 2 处，需检查是否有 `except: pass` 组合

#### [P2-03] 代码侵入式中文路径
- `scripts/ledger_query.py`, `scripts/create_smartsheet_table.py` 等使用了 `LEDGER_DIR` 硬编码中文路径

## 4. 整改优先级矩阵

| 优先级 | 问题ID | 影响范围 | 整改难度 | 修复后收益 |
|--------|--------|---------|---------|-----------|
| P0 | P0-01 裸 except | 运行时安全 | 低 | 避免静默异常 |
| P1 | P1-01 print→logger | 生产日志 | 中 | 日志规范化 |
| P1 | P1-02 sys.path统一 | 构建/部署 | 高 | 代码可维护性 |
| P1 | P1-03 阈值集中 | 配置管理 | 中 | 统一配置入口 |
| P1 | P1-04 端口管理 | 部署配置 | 低 | 端口可配置 |
| P1 | P1-05 中文路径 | 跨机运行 | 低 | 兼容性 |
| P1 | P1-06 文件清理 | 项目整洁 | 低 | 目录结构清晰 |
| P2 | P2-01 刷新规范 | 前端可靠性 | 中 | UI状态同步 |

## 5. 验收标准

1. ✅ 所有 P0 问题修复，安全漏洞清零
2. ✅ 生产代码中 print() 全部替换为 logger
3. ✅ 入口文件 sys.path 集中管理，非入口文件不再 import sys 做 path 操作
4. ✅ 所有阈值默认值在 config.py 中统一定义
5. ✅ 端口值从 config.py 或环境变量读取
6. ✅ 中文路径硬编码消除
7. ✅ 根目录调试文件清理或归位
