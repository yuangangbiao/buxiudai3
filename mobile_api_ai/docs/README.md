# 文档目录

## 核心架构文档

| 文档 | 说明 |
|------|------|
| [ARCHITECTURE_v3.6.md](ARCHITECTURE_v3.6.md) | **系统架构总览** |
| [TASK_TABLE_SPEC.md](TASK_TABLE_SPEC.md) | **任务表结构规范** |
| [调度中心稳定性加固.md](调度中心稳定性加固.md) | 调度中心稳定性方案 |

## 功能文档

| 文档 | 说明 |
|------|------|
| [维修完成功能说明.md](维修完成功能说明.md) | 维修模块功能说明 |
| [集成测试方案_启动前安全网.md](集成测试方案_启动前安全网.md) | 集成测试方案 |

## 技术规范

| 文档 | 说明 |
|------|------|
| [MySQLStorage_API参考.md](MySQLStorage_API参考.md) | MySQL 存储层 API |
| [HTTP客户端调用规范.md](HTTP客户端调用规范.md) | HTTP 调用规范 |
| [API_VERSIONING_PLAN.md](API_VERSIONING_PLAN.md) | API 版本管理规范 |
| [交互架构设计.md](交互架构设计.md) | 前后端交互架构 |
| [database_indexes_mysql.sql](database_indexes_mysql.sql) | 数据库索引规范 |

## 部署运维

| 文档 | 说明 |
|------|------|
| [单用户部署指南.md](单用户部署指南.md) | 单机部署指南 |
| [INSIGHTFACE部署方案.md](INSIGHTFACE部署方案.md) | 人脸识别部署 |
| [deploy/](deploy/) | 部署指南目录 |

## 数据库迁移

| 文档 | 说明 |
|------|------|
| [migrations/](migrations/) | 数据库迁移脚本目录 |

## 进行中项目文档

| 目录 | 说明 |
|------|------|
| [chengsheng_sync/](chengsheng_sync/) | 成升同步设计文档 |
| [内存数据持久化治理/](内存数据持久化治理/) | 内存数据持久化文档 |
| [微信文件保存/](微信文件保存/) | 微信文件保存文档 |
| [code_quality_scan/](code_quality_scan/) | 代码质量扫描文档 |

## 归档目录

| 目录 | 说明 |
|------|------|
| [archive/](archive/) | 历史文档归档 |
| [迁移计划/](迁移计划/) | 迁移计划文档 |
| [代码审查报告/](../代码审查报告/) | 代码审查报告归档 |

---

## v3.6 重大更新 (2026-06-20)

1. **统一任务表结构**：拆分 `data_packages`，按任务类型建立独立表
2. **新增表**：`repair_records`, `outsource_records`, `schedule_records`
3. **工序代码规范**：统一使用 P/M/Q/R/O 前缀
4. **API 规范化**：所有任务 API 读写独立表
5. **文档清理**：归档过期文档，统一文档结构

详见 [ARCHITECTURE_v3.6.md](ARCHITECTURE_v3.6.md)
