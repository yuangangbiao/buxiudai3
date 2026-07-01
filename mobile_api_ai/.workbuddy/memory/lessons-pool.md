# 经验池 - lessons-pool

> 记录项目中踩过的坑，下次遇到类似问题可直接照搬答案。
> 格式：`日期 | 功能 | 阶段 | 问题 | 根因 | 建议 | 状态`

---

## 🟡 模式级（已合并）

### L1: 删除死代码包前必须全文 grep 所有注册入口
- **日期**: 2026-06-20
- **功能**: F22 行动项 3 硬迁移 (container_center/api/ 包删除)
- **阶段**: Phase 4 编码实施
- **问题**: 删除 `container_center/api/` 死代码包时，连带删除了 `configs.py` 里的 `/configs/alert_rules` 配置路由。`ContainerCenterClient.get_alert_rules / update_alert_rules` 实际依赖此端点，硬迁移后这两个方法立即 404。
- **根因**: 仅 grep `register_alert_routes` 字符串（0 命中），未检查 `configs.py` 中的其他注册函数 `register_config_routes`（同 Blueprint 包内，但搜索关键词不一致）。
- **建议**: 删整个包前，搜索包内**所有文件**的所有 `register_*_routes` / `create_*_bp` / `init_*_bp` 调用，确认无任何 import 链引用。
- **状态**: 已合并至 Skill 6.1 清单第 10+ 行（待办）

### L2: 硬迁移"不兜底依赖"必须配套新建完整端点
- **日期**: 2026-06-20
- **功能**: F22 行动项 3 硬迁移 (5002/5003 告警 API 合并)
- **阶段**: Phase 2 方案设计
- **问题**: 软迁移策略（5003 优先 + 5002 回退）被认为"反模式"——掩盖 5003 服务可用性问题，且 mock 数据从未被生产消费。用户拍板"直接迁移，不兜底依赖"。
- **根因**: 软迁移的"回退到 mock 数据"等同于"用假数据掩盖真实故障"，违反反虚高规范。
- **建议**: 硬迁移 = 直接删除 mock + 客户端直接抛异常（不静默回退）。生产部署必须保证依赖服务先于调用方可用。
- **状态**: 已固化至 BUG_REPORT.md D2 决策日志

### L3: Phase 7 路由基线脚本的 bp_name / BP_PREFIXES 不匹配
- **日期**: 2026-06-20
- **功能**: F22 Phase 7 路由基线对比脚本
- **阶段**: Phase 6 悲观审计
- **问题**: 路由装饰器 `@dispatch_center_bp.route(...)` 用的是**变量名**，但 `Blueprint('dispatch_center', ...)` 注册的 url_prefix 是**字符串名**。`BP_PREFIXES.get('dispatch_center_bp', '')` 永远找不到 → 所有 Blueprint 路由的 prefix 都丢了。
- **根因**: 路由变量的命名约定 `xxx_bp`（如 `dispatch_center_bp`）vs Blueprint 第一个参数（不带 `_bp`）不统一。
- **建议**: 提取 bp_name 时自动剥离 `_bp` / `_blueprint` 后缀再查 BP_PREFIXES。已修复 [check_route_baseline.py:50-58](../../../scripts/tools/check_route_baseline.py)。
- **状态**: 已修复 + commit fc0cc938

### L4: 中文路径下 git 命令行为异常
- **日期**: 2026-06-20
- **功能**: F22 A7 commit
- **阶段**: Phase 7 零回归
- **问题**: 项目路径 `d:\yuan\不锈钢网带跟单3.0` 含中文。`git add mobile_api_ai/container_center/api/` 在 PowerShell 下未把 7 个文件加到 index，导致 commit 4 只改了 1 个文件。同时 `git restore --source HEAD file` 在中文路径下行为也异常，可能覆盖未保存的改动。
- **根因**: PowerShell + 中文路径 + git 三方交互的边界 case（具体原因未深查，可能与编码转换相关）。
- **建议**:
  - 涉及中文路径的 git 操作，先 `git status --short` 确认文件已 staged
  - 用 `git rm -r --cached` 显式 stage 删除操作（比 `git add` 删除目录更可靠）
  - 重要操作前用 `git stash` 保存工作区，避免误覆盖
- **状态**: 已规避（commit 时手动验证 stat）

### L5: 静态分析脚本不能完全替代运行时测试
- **日期**: 2026-06-20
- **功能**: F22 A5 端到端测试
- **阶段**: Phase 5 测试覆盖
- **问题**: 项目级 `core.config` 模块不在 sys.path 中，导致 pytest 加载 `container_center_api.py` 时 `ModuleNotFoundError`。无法跑真实集成测试，只能用 AST 静态分析 + Mock session 模拟。
- **根因**: `core.config` 是项目专有模块，但不在 `__init__.py` 标准包中，pytest 找不到。
- **建议**:
  - 静态分析（AST 解析 + 文本 grep）作为最低门槛验证
  - Mock session 模拟 HTTP 调用作为补充
  - 真实 e2e 测试需在项目专用虚拟环境跑（不在通用 Python 环境）
- **状态**: 已纳入静态验证脚本 [static_check_alert_callers.py](../../../scripts/tools/static_check_alert_callers.py)

---

## ⚪ 知识级（项目约定）

### K1: `/api/dispatch-center/*` 路由前缀约定
- 所有"调度中心"对外 API 必须挂在 `dispatch_center_bp` Blueprint 上，前缀 `/api/dispatch-center`
- 包括：告警 API (/alerts/*)、同步 API (/sync/*)、违规 API (/violations/*)、配置 API (/configs/*)
- 创建新调度中心 API 时参考 [_core.py L1417](file:///D:/yuan/%E4%B8%8D%E9%94%90%E9%92%A2%E7%BD%91%E5%B8%A6%E8%B7%9F%E5%8D%953.0/mobile_api_ai/dispatch_center/_core.py) 的 Blueprint 定义

### K2: 容器中心 5002 端口仅保留最小 API
- 硬迁移后，5002 仅保留 `/api/v4/operators` / `/api/v4/work_order` 等必要 API
- **禁止**新增 `/api/v4/*` 路由（除非走 L1 流程先确认 Blueprint 注册路径）
- 所有告警/配置/同步 API 必须在 5003 端口实现

### K3: 死代码识别清单（历史已删除）
- ✅ `container_center/api/` 整个包（7 文件，2026-06-20 删除）
- 候选：`commands/` 下的命令实现（按需检查）

---

## 统计

| 类别 | 数量 | 最近一次更新 |
|------|:----:|-------------|
| 🟡 模式级 | 5 | 2026-06-20 |
| ⚪ 知识级 | 3 | 2026-06-20 |
| 🔴 规则级 | 0 | - |

**触发合并的条件**: ≥5 条或 ≥30 天 → 提示合并到 add-feature Skill 主清单。
当前状态: 🟡 模式级已 5 条，**建议合并到 Skill Phase 6.1 第 10+ 行**。