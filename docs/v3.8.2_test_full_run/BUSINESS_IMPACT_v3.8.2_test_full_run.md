# 业务影响报告 - v3.8.2 全量测试重跑

## 1. 用户场景对比

| # | 用户角色 | 改善前（痛点） | 改善后（价值） |
|---|---------|---------------|---------------|
| 1 | 开发者 | 跑全量 pytest 看到 241 个 collection error，分不清是配置问题还是代码 bug，调试 1 小时无头绪 | 全量 4208 tests 可收集，0 collection error，能直接看到具体 failed 列表（230 个） |
| 2 | 测试工程师 | 修改一个测试可能让 5 个不相干测试失败（services.* 跨目录污染），难以定位根因 | 单跑通过率高（unit/core 853/885 = 96.4%），可放心本地调试 |
| 3 | 运维/DevOps | 不知道 pytest 是否能用于 CI/CD，因为一次都跑不完（241 collection error 致 pytest 立即 exit） | 1 小时 10 分可跑完全量，CI 可设置超时 2 小时覆盖，未来可配 `--maxfail=10 -x` 快速失败 |

## 2. 业务能力新增

> 按业务流分类（生产/质检/物料/外协/报修/监控 等）

| 业务流 | 新增/优化功能 | 影响范围 |
|--------|--------------|---------|
| 测试基础设施 | conftest_helpers.py v3.8.1 统一清理模式 | 所有 conftest.py |
| 测试基础设施 | pytest_collection_modifyitems 钩子（collection 后清理 sys.modules） | 跨目录测试隔离 |
| 测试基础设施 | pytest_pycollect_makemodule 钩子（每个模块收集前清理） | 单文件 sys.modules 污染 |
| 代码质量 | H5/H6 测试对齐源码（now/now_str/today_str、_allocate_material_code） | 测试与实际功能一致 |
| CI/CD | 4208 tests 可在 1h10m 内完成 | 部署前可执行完整回归 |

## 3. 不变更部分

> 防回归保护清单（哪些保持原样，行为零变更）

| # | 模块/功能 | 保护措施 | 验证方式 |
|---|----------|---------|---------|
| 1 | conftest.py 业务 fixture（db_session / login_as / admin_page） | 保持原 stub 行为，pytest.skip 包装 | 验证仍调用 pytest.skip |
| 2 | tests/conftest.py 第 24-30 行 SERVICES 端口常量 | 数值未改动 | 对比 git diff |
| 3 | tests/conftest.py setup_test_environment fixture | env var setdefault 逻辑保留 | teardown 还原原值 |
| 4 | 业务代码（models / services / core）零修改 | 只改测试代码和 conftest_helpers | git diff 业务代码 = 0 |
| 5 | pyproject.toml pythonpath = [".."] 配置 | 未变更 | 验证 pytest 仍能收集 |
| 6 | pytest.ini 配置 | 未变更 | 验证行为一致 |

## 4. 一句话总结

> 本次改动让 pytest 全量从"241 collection error 无法跑"变为"1h10m 跑完 4208 测试，通过 3660 个"，使 CI/CD 集成从不可能变为可行；测试基础设施（conftest_helpers）从零散实现升级为统一清理模式。
