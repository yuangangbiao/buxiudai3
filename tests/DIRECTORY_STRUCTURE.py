# -*- coding: utf-8 -*-
"""
tests/ 目录结构 + 测试体系协调方案

============================================================
重要：本文件是 tests 目录的"地图" + 多 conftest 协调规范
============================================================

【目录职责划分】

| 目录             | 职责                                        | 数量    | 维护者 |
|------------------|---------------------------------------------|---------|--------|
| tests/unit/      | 单元测试（函数/方法级，Mock 外部依赖）       | 150+    | 后端   |
| tests/e2e/       | 端到端测试（业务流，真实服务）               | 13 文件 | 全栈   |
| tests/integration/ | 跨服务集成（5001/5003/5008 数据一致性）     | 8 文件  | 架构   |
| tests/modular/   | 模块化测试（中间层服务、容器监听等）         | 8 文件  | 后端   |
| tests/manual/    | 手工测试（HTTP / Playwright 验证）           | 5 文件  | QA     |
| tests/L1_smoke/  | 冒烟测试（核心流程，5分钟内完成）             | TBD     | 全栈   |
| tests/L2_modules/ | 模块浏览器测试（单功能 UI 验证）              | TBD     | 前端   |
| tests/L3_integration/ | 跨服务性能 + 集成                          | TBD     | 架构   |
| tests/L4_scenarios/ | 业务场景测试（紧急/多用户/外勤）             | TBD     | PM     |
| tests/core/      | 测试框架核心（fixtures/工具/配置）           | 14 文件 | 全栈   |
| tests/fixtures/  | 测试数据工厂（用户/订单/清理）               | 4 文件  | 全栈   |
| tests/pages/     | Page Object（Page Object 模式）              | TBD     | 前端   |

【conftest 加载顺序与命名空间】

pytest 按以下顺序加载 conftest.py（外层先于内层）：

1. tests/conftest.py                  ← 全局 fixtures（服务/DB/worker 隔离）
2. tests/e2e/conftest.py              ← e2e 特有 fixtures（重置 DB / 启动服务）
3. tests/unit/conftest.py             ← unit 特有 fixtures（mock 环境）
4. tests/unit/utils/conftest.py       ← utils 单元测试特有 fixtures
5. tests/integration/conftest.py      ← 集成测试特有 fixtures
6. tests/L*/conftest.py               ← 浏览器测试层级 fixtures（如有）

【协调原则】

1. 全局 fixtures 必须在 tests/conftest.py 中定义
2. 子目录的 conftest.py 不得重复定义同名 fixture
3. 子目录需要扩展时用 from ..conftest import xxx
4. fixture 命名空间用前缀区分：db_, api_, browser_, page_

【L1/L2/L3/L4 与已有体系的关系】

| 新层级    | 已有体系       | 关系     | 说明                          |
|-----------|----------------|----------|-------------------------------|
| L1_smoke  | e2e + manual   | 互补     | 自动化冒烟（e2e 手工，l1 自动）|
| L2_modules | e2e + manual   | 补充     | 浏览器视角的模块验证           |
| L3_integration | integration  | 强化     | 性能 + 一致性                  |
| L4_scenarios | manual       | 自动化   | 业务场景从手工 → 自动          |

【L2/L3 补充 vs 已有 e2e 的边界】

已有 tests/e2e/ (13 文件) 覆盖：
- 认证、订单、工艺、排产、报工、质检、发货、成本、同步、并发、指标
- 主要从 API 视角

L2_modules 补充（浏览器视角）：
- 桌面端 UI 流程验证（Playwright 模拟真实点击）
- 移动端 H5 验证（mobile viewport）
- 权限/安全验证（CSRF、XSS、SQL 注入）

不重复！e2e 是 API，L2 是 UI。

【修改 conftest 时的强制规则】

1. 修改前先 grep -r "fixture_name" tests/ 确认无冲突
2. 新增 fixture 默认 scope='function'，避免跨用例污染
3. fixture 间依赖用 yield 传递，不传全局变量
4. 命名遵循 snake_case + 功能前缀

【联系方式】

如有冲突：架构组（小圣）+ QA（小贺）联合 review
"""
__docformat__ = 'restructuredtext'
