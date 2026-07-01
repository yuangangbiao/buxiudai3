# MySQLStorage API 参考

> 文件: `storage/mysql_storage.py`  
> 数据库: `container_center` (MySQL)  
> 更新日期: 2026-05-30

---

## 考勤管理

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `get_attendance` | `worker: str, date: str` | `Dict/None` | 查某人某天签到记录 |
| `get_attendance_by_date` | `date: str` | `List[Dict]` | 查某天所有人签到列表（看板用） |
| `upsert_attendance` | `worker, date, check_in, check_out, status` | `int` | 签到/签退，有则更新无则新建 |

**表**: `attendance`

---

## 工人管理

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `get_all_workers` | — | `List[Dict]` | 取所有在职操作员 |
| `get_worker` | `worker_id: str` | `Dict/None` | 按 enterprise_id 查操作员 |
| `save_worker` | `worker: Dict` | `int` | 新增操作员 |
| `delete_worker` | `username: str` | `int` | 软删除（标记 inactive） |

**表**: `workers`

---

## 子步骤（分批报工）

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `get_sub_steps_by_process` | `order_no: str` | `List[Dict]` | 按订单号查所有子步骤 |
| `save_sub_step` | `record: Dict` | `int` | 记录一次分批报工 |
| `get_sub_step_summary` | `order_no: str` | `List[Dict]` | 按工序汇总累计完成量 |
| `get_last_sub_step` | `order_no: str` | `Dict/None` | 取最近一次子步骤 |

**表**: `process_sub_steps`

---

## 数据包管理

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `save_package` | `package: Dict` | `int` | 新增数据包 |
| `get_packages` | `limit, **filters` | `List[Dict]` | 条件查询数据包列表 |
| `get_package` | `pkg_id: str` | `Dict/None` | 按 ID 取单个数据包 |
| `update_package` | `pkg_id, pkg_dict` | `int` | 更新数据包任意字段 |
| `update_package_status` | `pkg_id, status, remark` | `int` | 快捷改状态 |
| `delete_package` | `pkg_id: str` | `int` | 删除数据包 |
| `cleanup_expired_packages` | `retention_days=30` | `int` | 清理过期已完成数据包 |

**表**: `data_packages`

---

## 回传记录

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `save_return_record` | `package_id, return_data, analyzed, write_back_cmd` | `int` | 记录操作员回传的报工/质检数据 |

**表**: `return_records`

---

## 企业架构

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `load_enterprise_structure` | — | `Dict` | 加载企业架构（部门+用户） |
| `save_enterprise_structure` | `data: Dict` | `int` | 保存企业架构 |

**表**: `enterprise_structure`

---

## 工序记录

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `get_all_process_records` | — | `List[Dict]` | 取所有工序记录 |
| `get_process_record` | `record_id` | `Dict/None` | 按 ID 取工序记录 |
| `get_process_records` | `search, limit` | `List[Dict]` | 条件查询工序记录 |
| `get_process_records_by_work_order` | `order_no` | `List[Dict]` | 按工单号查工序 |
| `save_process_record` | `record` | `int` | 新增工序记录 |

**表**: `process_records`

---

## 日志 / 审计

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `save_data_flow_log` | `log: Dict` | `int` | 记录数据流事件（创建→分发→确认→完成） |
| `log_sync` | `action, package_id, detail` | `int` | 同步操作日志 |

**表**: `data_flow_logs`, `sync_logs`

---

## 连接管理

| 方法 | 说明 |
|------|------|
| `connect()` | 初始化连接池 + 建表 + 种子数据 |
| `disconnect()` | 关闭连接池 |
| `health_check()` | 健康检查 `SELECT 1` |
| `execute(sql, params)` | 执行任意 SQL，返回影响行数 |
| `fetch_one(sql, params)` | 查询单行 |
| `fetch_all(sql, params)` | 查询多行 |
| `insert(table, data)` | 插入一行（自动建列） |
| `update(table, data, where, where_params)` | 条件更新 |
