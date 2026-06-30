# -*- coding: utf-8 -*-
"""
T2 数据回填脚本: data_packages.content['flow_type'] -> data_packages.flow_type 列
========================================================================
依赖 T1 DDL (commit fae446bd): data_packages.flow_type 列 + 2 索引已存在

执行方式:
    # 默认 dry-run (不写入)
    py scripts/backfill_data_packages_flow_type.py

    # 真回填
    py scripts/backfill_data_packages_flow_type.py --apply

    # 自定义批次大小
    py scripts/backfill_data_packages_flow_type.py --apply --batch-size 1000

    # 回滚 (按 apply_log 记录反向)
    py scripts/backfill_data_packages_flow_type.py --rollback            # dry-run 模式, 列出待删 ID
    py scripts/backfill_data_packages_flow_type.py --rollback --rollback-apply --yes  # 真删

设计契约 (10 章节 - 与前测 test_backfill_data_packages_flow_type.py 对齐):
1. 连接管理: main() 注入 conn, finally close, with cursor
2. 失败回滚: 每 batch commit, 失败回滚该 batch
3. 批次: batch_size 必填默认 500, <=0 抛 ValueError, SELECT LIMIT/OFFSET
4. 写入安全: %s 参数化, WHERE id = %s AND flow_type = '' 乐观锁
5. 报告: scanned/parsed/applied/skipped
6. 依赖约束: T1 DDL, 分批
7. 执行环境: banner with sys.platform, sys.stdout.flush()
8. 依赖清单: 仅标准库 + from utils.db import get_conn
9. 回滚策略: rollback function + apply_log + 双层确认
10. 日志输出: stdout flush, 可选 --log-file

进化项 #10: 启动时检测 sys.platform / platform.system() + python -u 强制 unbuffered
"""
import argparse
import datetime
import json
import os
import platform
import sys
from pathlib import Path
from typing import Optional

# 仅标准库依赖 (L3 契约 8 章节)
# 第三方依赖: utils.db (项目内模块, L3 契约允许)
# 注: 不使用 logging 库, 改用 print(..., flush=True) + 可选 _log_to_file 写文件
#     (lessons-pool v3.5.2 任务3 教训: 工具脚本用 def warn/err(): print(..., file=sys.stderr))


# =============================================================================
# 7. 执行环境 (进化项 #10) - 启动 banner
# =============================================================================
def _print_banner() -> None:
    """启动时输出 banner: 检测执行环境 (sys.platform + platform.system + python 版本)"""
    # 强制 unbuffered 输出 (即使未用 python -u 启动)
    try:
        sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        pass  # 老 Python 跳过

    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    py_ver = sys.version.split()[0]
    banner = (
        f"[BANNER] T2 backfill start at {ts} on "
        f"{sys.platform}/{platform.system()} "
        f"python={py_ver} pid={os.getpid()}"
    )
    print(banner, flush=True)


# =============================================================================
# 5. 报告字段 + 9. apply_log
# =============================================================================
def _new_report() -> dict:
    """初始化报告 dict"""
    return {"scanned": 0, "parsed": 0, "applied": 0, "skipped": 0}


def _log_to_file(log_file: Optional[Path], level: str, msg: str) -> None:
    """可选写日志到文件 (L4 契约 10 章节)
    注: 工具脚本不引 logging 库 (lessons-pool v3.5.2 任务3),
        但需保证 flush=True (长跑脚本可观察)
    """
    if log_file is None:
        return
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] [{level}] {msg}\n")
            f.flush()
    except OSError as e:
        print(f"[WARN] 日志写入失败: {e}", file=sys.stderr, flush=True)


# =============================================================================
# 1. parse_flow_type: 解析 content 字符串 -> flow_type 或 ''
# =============================================================================
def parse_flow_type(content) -> str:
    """
    解析 data_packages.content (str 或 bytes) JSON, 返回 content['flow_type'] 字段
    容错策略:
      - bytes 输入先 decode 为 str
      - JSON 解析失败 -> ''
      - 缺 flow_type 键 -> ''
      - flow_type 非字符串 -> ''
      - 任何异常 -> '' (不抛错)
    """
    if content is None:
        return ""
    # bytes 输入处理 (PyMySQL 可能返回 bytes)
    if isinstance(content, bytes):
        try:
            content = content.decode("utf-8")
        except (UnicodeDecodeError, AttributeError):
            return ""
    if not isinstance(content, str):
        return ""
    if not content.strip():
        return ""
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, ValueError):
        return ""
    if not isinstance(data, dict):
        return ""
    flow_type = data.get("flow_type")
    # 必须是字符串, 否则返回 ''
    if not isinstance(flow_type, str):
        return ""
    return flow_type


# =============================================================================
# 2/3/4/5. backfill: 主回填函数
# =============================================================================
def backfill(conn, dry_run: bool = True, batch_size: int = 500) -> dict:
    """
    回填 data_packages.flow_type 列 (从 content['flow_type'])

    Args:
        conn: PyMySQL 连接 (注入式, main() 内 finally close)
        dry_run: True=仅收集 SQL 不 commit, False=真写入
        batch_size: 每批 SELECT 行数, 必须 > 0

    Returns:
        dict: {scanned, parsed, applied, skipped}
    """
    # 3. 批次边界校验
    if not isinstance(batch_size, int) or batch_size <= 0:
        raise ValueError(f"batch_size 必须为正整数, 实际 {batch_size}")

    report = _new_report()
    offset = 0
    batch_idx = 0

    while True:
        batch_idx += 1
        with conn.cursor() as cur:
            # 3. SELECT 分批 (LIMIT batch_size OFFSET ?)
            select_sql = (
                "SELECT id, content FROM data_packages "
                "WHERE flow_type = '' AND content LIKE '%flow_type%' "
                "ORDER BY id ASC LIMIT %s OFFSET %s"
            )
            cur.execute(select_sql, (batch_size, offset))
            rows = cur.fetchall()

            if not rows:
                # 空批 = 终止 (前测契约 9: 调用 N+1 次, 最后一次空终止)
                print(
                    f"[BATCH {batch_idx}] empty, terminate (offset={offset})",
                    flush=True,
                )
                break

            batch_parsed = 0
            batch_applied = 0
            batch_skipped = 0
            for row in rows:
                row_id, content = row[0], row[1]
                report["scanned"] += 1
                flow_type = parse_flow_type(content)
                if not flow_type:
                    report["skipped"] += 1
                    batch_skipped += 1
                    continue
                report["parsed"] += 1
                batch_parsed += 1
                # 4. UPDATE 用 %s 参数化 + 乐观锁 WHERE flow_type = ''
                update_sql = (
                    "UPDATE data_packages "
                    "SET flow_type = %s "
                    "WHERE id = %s AND flow_type = ''"
                )
                if dry_run:
                    # dry-run 模式: 不 commit, 仅记录
                    print(
                        f"[DRY-RUN] UPDATE data_packages SET flow_type="
                        f"'{flow_type}' WHERE id={row_id} AND flow_type=''",
                        flush=True,
                    )
                else:
                    cur.execute(update_sql, (flow_type, row_id))
                    report["applied"] += 1
                    batch_applied += 1

            # 2. 每 batch commit 一次 (apply 模式)
            if not dry_run:
                try:
                    conn.commit()
                except Exception as e:
                    # 失败回滚该 batch (保留已成功的 batch)
                    conn.rollback()
                    print(
                        f"[BATCH {batch_idx}] commit FAILED, rolled back: {e}",
                        file=sys.stderr,
                        flush=True,
                    )
                    raise

            print(
                f"[BATCH {batch_idx}] offset={offset} "
                f"parsed={batch_parsed} applied={batch_applied} skipped={batch_skipped}",
                flush=True,
            )

        offset += batch_size
        # 终止条件: 下一批返回空 (在循环开头判断)

    return report


# =============================================================================
# 9. rollback: 反向回滚 (按 apply_log 列出待删 ID, 双层确认)
# =============================================================================
def rollback(
    conn, dry_run: bool = True, log_file: Optional[Path] = None
) -> dict:
    """
    回滚 data_packages.flow_type 回填操作
    注: 当前实现是 dry-run 列出 (待与 apply_log 集成)

    Args:
        conn: PyMySQL 连接
        dry_run: True=仅列出待回滚 ID, False=真删
        log_file: apply_log 文件路径 (可选)

    Returns:
        dict: {to_delete, deleted, dry_run}
    """
    result = {"to_delete": 0, "deleted": 0, "dry_run": dry_run}

    # 列出所有 flow_type 非空 (回填过的) 的 ID
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, flow_type FROM data_packages "
            "WHERE flow_type != '' ORDER BY id ASC"
        )
        rows = cur.fetchall()

    result["to_delete"] = len(rows)
    print(
        f"[ROLLBACK {'DRY-RUN' if dry_run else 'APPLY'}] "
        f"待回滚 {len(rows)} 条 (flow_type != '')",
        flush=True,
    )

    if not dry_run:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE data_packages SET flow_type = '' "
                "WHERE flow_type != ''"
            )
            # 修补: rowcount 必须在 commit 前读取
            # (PyMySQL commit 后 rowcount 行为未保证, 部分驱动会失效)
            result["deleted"] = cur.rowcount
            conn.commit()
        print(
            f"[ROLLBACK APPLY] 已回滚 {result['deleted']} 条, flow_type 重置为 ''",
            flush=True,
        )

    _log_to_file(log_file, "INFO", f"rollback: {result}")
    return result


# =============================================================================
# 8. get_conn: 注入式 DB 连接 (从项目 utils.db 加载)
# =============================================================================
def get_conn():
    """从项目 utils.db 加载 PyMySQL 连接 (注入式, 便于测试 mock)"""
    try:
        from utils.db import get_conn as _project_get_conn  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            f"无法导入 utils.db.get_conn: {e}\n"
            f"请确认 utils/db.py 在 PYTHONPATH 中"
        ) from e
    return _project_get_conn()


# =============================================================================
# 1/10. main: CLI 入口 + argparse
# =============================================================================
def main() -> int:
    """主入口: argparse + 连接管理 + 调度 backfill/rollback"""
    _print_banner()

    parser = argparse.ArgumentParser(
        description="T2 数据回填脚本: content['flow_type'] -> data_packages.flow_type"
    )
    # backfill 参数
    parser.add_argument(
        "--apply",
        dest="dry_run",
        action="store_false",
        help="真回填 (默认 dry-run 仅记录 SQL)",
    )
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        default=True,
        help="Dry-run 模式 (默认, 仅记录 SQL 不 commit)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="每批 SELECT 行数 (默认 500, 必须 > 0)",
    )
    # rollback 参数
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="回滚模式 (默认 dry-run, 需 --rollback-apply + --yes 才真删)",
    )
    parser.add_argument(
        "--rollback-apply",
        action="store_false",
        dest="rollback_dry_run",
        help="rollback 真删 (需配合 --yes)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="rollback 双层确认 (与 --rollback-apply 配合使用)",
    )
    parser.set_defaults(rollback_dry_run=True)
    # 日志
    parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="日志文件路径 (可选, 默认 stdout)",
    )

    args = parser.parse_args()

    # 双层确认: rollback --rollback-apply 必带 --yes
    if args.rollback and not args.rollback_dry_run and not args.yes:
        print(
            "[ERROR] --rollback-apply 必带 --yes 才执行 (双层确认)",
            file=sys.stderr,
            flush=True,
        )
        return 2

    # 连接管理: main() 注入 conn, finally close
    conn = None
    try:
        conn = get_conn()
        print(f"[INFO] DB 连接已建立: {conn}", flush=True)

        if args.rollback:
            report = rollback(
                conn,
                dry_run=args.rollback_dry_run,
                log_file=args.log_file,
            )
            print(f"[REPORT] rollback: {report}", flush=True)
        else:
            report = backfill(
                conn,
                dry_run=args.dry_run,
                batch_size=args.batch_size,
            )
            print(f"[REPORT] backfill: {report}", flush=True)
            _log_to_file(args.log_file, "INFO", f"backfill: {report}")
    except ValueError as e:
        print(f"[ERROR] 参数错误: {e}", file=sys.stderr, flush=True)
        return 1
    except Exception as e:
        print(f"[ERROR] 执行失败: {e}", file=sys.stderr, flush=True)
        return 1
    finally:
        if conn is not None:
            try:
                conn.close()
                print("[INFO] DB 连接已关闭", flush=True)
            except Exception as e:
                print(
                    f"[WARN] conn.close() 失败: {e}",
                    file=sys.stderr,
                    flush=True,
                )

    return 0


if __name__ == "__main__":
    sys.exit(main())
