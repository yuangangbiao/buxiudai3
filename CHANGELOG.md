# Changelog

所有重要变更均记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/),
版本号遵循 [Semantic Versioning](https://semver.org/spec/v2.0.0.html)。

## [Unreleased]

### Added
- CHANGELOG.md 建立 (@M1.4-Q1)
- P2: `/api/all-process-tasks` 添加分页（page/size 参数，不传参时向后兼容全量）(@2026-06-09)
- P3: `api/step_status_helper.py` 添加调用方清单 + 演进历史（Changelog）(@2026-06-09)

### Fixed
- P1a: 清理 ORD-202604210002 下 8 条脏 sub_steps（qty=0 AND operator 为空）(@2026-06-09)
- P1b: 补分配 2 条 pending QA 任务给苑岗彪（data_packages target_operator）(@2026-06-09)
- 修复 14 处 self-OR 模式漏洞（`record.get('key','') or record.get('key','')`）(@2026-06-09)
- 修复 22 处重复 dict key（同一 dict 内相同 key 后值覆盖前值）(@2026-06-09)

### Changed
- `.gitignore` 审计与完善：补充 `.pytest_cache/`、`.mypy_cache/`、`.coverage`、`htmlcov/`、`venv/`、`.trae/`、`代码审查报告/`、`instance/` 等条目 (@M1.5-Q1)
- 提取 `compute_step_statuses` / `compute_sub_step_statuses` 到共享的 `api/step_status_helper.py`，三端（手机端/桌面端/调度中心）统一真值源 (@2026-06-09)

## [3.0.0] - 2026-05-26

### Added
- `dispatch_center.py` 全部 100 个路由函数添加标准 docstring（含 Args/Returns 说明）(@M1.3-Q1/Q2/Q3)
- `dispatch_center.py` 前 100 个公有函数添加类型标注 (@M1.1-Q1, @M1.2-Q1)
- `dispatch_center.py` 后台调度器模块：`SchedulerController` 基类 + 定时任务统一管理器

### Changed
- 代码可维护性显著提升：docstring + 类型标注覆盖全部路由处理函数

## [2.0.0] - 2026-05-25

### Added
- MySQL 存储层完整测试覆盖：`test_storage_mysql.py` (23 条用例) (@M0.7-Q1, @M0.8-Q1)
- 核心 API 功能测试覆盖 16 个接口：`test_api_core.py` (16 条用例) (@M0.9-Q1)
- 辅助 API 功能测试覆盖 26 个接口：`test_api_aux.py` (26 条用例) (@M0.10-Q1)
- `api/decorators.py` 函数测试覆盖 (@M0.5-Q1)
- pytest 配置完善：coverage 配置 (`--cov-fail-under=40`)、超时处理、ini 配置 (@M0.11-Q1)
- 测试文档完善 (@M0.12-Q1)

### Removed
- 清理临时文件与未使用的测试产物 (@M0.15-Q1)

## [1.0.0] - 2026-05-24

### Added
- `core` 包 10 个文件添加类型标注 (type hints) (@M0.1-Q1)
- `core` 包 import 整理与规范化 (@M0.2-Q1)
- pytest 测试框架搭建：`pyproject.toml`、`conftest.py` 配置 (@M0.3-Q1, @M0.6-Q1)
- `api/decorators.py` 所有函数添加标准 docstring (@M0.4-Q1)
- 测试环境配置：`pyproject.toml` 测试路径、覆盖率、超时配置 (@M0.6-Q1)

### Changed
- 替换 `sys.path.insert` 为统一 `pythonpath` 配置
- 统一日志记录方式：`print` 改为 `logger` 调用

[Unreleased]: https://github.com/user/repo/compare/v3.0.0...HEAD
[3.0.0]: https://github.com/user/repo/compare/v2.0.0...v3.0.0
[2.0.0]: https://github.com/user/repo/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/user/repo/releases/tag/v1.0.0
