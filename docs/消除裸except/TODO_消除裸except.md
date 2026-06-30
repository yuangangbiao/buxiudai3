# TODO_消除裸except.md — 待办事项

## 已完成（无需处理）

| 事项 | 说明 |
|------|------|
| 27 个核心文件裸 except 替换 | ✅ 已全部替换为 `except Exception:` 或 `except (ValueError, TypeError):` |
| 编译验证 | ✅ 全部通过 |

## 建议后续关注

| 优先级 | 事项 | 说明 |
|--------|------|------|
| 低 | 在 except 块中添加 `logger.exception()` | 如果后续追加日志记录，搜索 `except Exception:` 即可找到所有需加日志的位置 |
| 低 | 云端同步 | 检查云端部署包是否需要同步此修改（本地 dispatch_center.py 已改） |

> 注意：`wechat_server.py` 云端专用，禁止本地修改，不在本次任务范围内。
