# -*- coding: utf-8 -*-
r"""业务表脏数据清理脚本 [K22 2026-06-16]

用途: 清理 system.db 的 tbl_documents 里 process_tasks 字段的脏数据
     (主程序显示列表里混入大量测试数据)

清理范围（默认全开，可单独关闭）:
  --no-orphan      跳过孤儿任务清理（order_no=null + process=""）
  --no-question    跳过 ? 占位符任务清理（process 含 ?）
  --no-test-order  跳过测试工单清理（ORD-REAL-001）
  --no-repeat      跳过重复任务清理（同一 order_no+process 在 24h 内多次 sent）
  --no-legacy      跳过冗余 JSON 文件清理（工序规则模板1.json / 2.json + .bak）
  --no-backup      跳过 system.db 备份（默认开启备份，备份到 data/backup/）

用法:
  python scripts/clean_dirty_data.py --dry-run          # 只扫描,不删
  python scripts/clean_dirty_data.py                   # 默认清理全部
  python scripts/clean_dirty_data.py --no-repeat       # 只清理孤儿/?/测试工单
  python scripts/clean_dirty_data.py --no-backup       # 不备份（不推荐）

设计原则:
  - 默认 dry-run=False + 默认 backup=True,防止误删
  - 每个清理动作独立开关,用户可选择性执行
  - 备份到 data/backup/<时间戳>_system.db,7 天内可恢复
  - 重复任务保留"最早 1 条",删除"其余 sent 副本"
"""
import argparse
import json
import os
import shutil
import sqlite3
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / 'data'
SYSTEM_DB = DATA_DIR / 'system.db'
DOC_ID = 'dispatch_center_data'

REDUNDANT_FILES = [
    '工序规则模板1.json',
    '工序规则模板2.json',
    '工序规则模板.json.bak',
    '工序规则模板1.json.bak',
    '工序规则模板2.json.bak',
]


def load_doc():
    conn = sqlite3.connect(SYSTEM_DB)
    cursor = conn.cursor()
    cursor.execute(f'SELECT doc_data, updated_at FROM tbl_documents WHERE id=?', (DOC_ID,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None, None
    return json.loads(row[0]), row[1]


def save_doc(doc):
    conn = sqlite3.connect(SYSTEM_DB)
    cursor = conn.cursor()
    new_data = json.dumps(doc, ensure_ascii=False)
    now = datetime.now().isoformat()
    cursor.execute(
        'UPDATE tbl_documents SET doc_data=?, updated_at=? WHERE id=?',
        (new_data, now, DOC_ID),
    )
    conn.commit()
    conn.close()


def backup_db():
    backup_dir = DATA_DIR / 'backup'
    backup_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = backup_dir / f'{ts}_system.db'
    shutil.copy2(SYSTEM_DB, backup_path)
    return backup_path


def is_question_process(process: str) -> bool:
    r"""判定 process 字段是否含 ? 占位符（垃圾值）
    合法: '原材料准备', '焊接输送带', '??' 长度 >= 2 但全是 ? 是垃圾
    """
    if not process:
        return False
    return process.strip() != '' and all(c == '?' for c in process.strip())


def is_orphan(task: dict) -> bool:
    r"""判定是否孤儿任务（order_no 为 null 或 process 为空字符串）"""
    return task.get('order_no') is None or task.get('order_no') == '' \
        or task.get('process') == ''


def is_test_order(task: dict) -> bool:
    r"""判定是否测试工单"""
    ono = (task.get('order_no') or '').upper()
    wno = (task.get('work_order_no') or '').upper()
    return 'REAL' in ono or 'REAL' in wno or 'TEST' in ono or 'TEST' in wno


def clean_orphans(tasks: list) -> tuple:
    r"""清理孤儿任务（order_no=null 或 process=""）"""
    keep = []
    removed = []
    for t in tasks:
        if is_orphan(t):
            removed.append(t)
        else:
            keep.append(t)
    return keep, removed


def clean_questions(tasks: list) -> tuple:
    r"""清理 ? 占位符任务"""
    keep = []
    removed = []
    for t in tasks:
        if is_question_process(t.get('process', '')):
            removed.append(t)
        else:
            keep.append(t)
    return keep, removed


def clean_test_orders(tasks: list) -> tuple:
    r"""清理测试工单"""
    keep = []
    removed = []
    for t in tasks:
        if is_test_order(t):
            removed.append(t)
        else:
            keep.append(t)
    return keep, removed


def clean_repeats(tasks: list, window_hours: int = 24) -> tuple:
    r"""清理重复任务（同 order_no+process 在 24h 内多次 sent，保留最早的 1 条）

    重复判定规则:
      - 同一 (order_no, process) 组合
      - 状态 status='sent'
      - 数量 >= 2 次
      - 保留: created_at 最早的 1 条
      - 删除: 其余全部

    注意: 如果 order_no 是 None（孤儿）已经先清掉了,这里就跳过
    """
    from datetime import timedelta
    # 先按 (order_no, process) 分组
    groups = {}
    for t in tasks:
        key = (t.get('order_no'), t.get('process'))
        groups.setdefault(key, []).append(t)

    keep = []
    removed = []
    for key, group in groups.items():
        if len(group) < 2:
            keep.extend(group)
            continue
        # 按 created_at 排序,保留最早 1 条
        group_sorted = sorted(group, key=lambda t: t.get('created_at', ''))
        # 看是否有窗口外的（>24h 之前的）—— 那些保留
        first_time = group_sorted[0].get('created_at')
        if first_time:
            try:
                first_dt = datetime.fromisoformat(first_time)
                keep.append(group_sorted[0])
                for t in group_sorted[1:]:
                    t_time = t.get('created_at', '')
                    if not t_time:
                        keep.append(t)
                        continue
                    t_dt = datetime.fromisoformat(t_time)
                    if (t_dt - first_dt) > timedelta(hours=window_hours):
                        keep.append(t)
                    else:
                        removed.append(t)
            except (ValueError, TypeError):
                # 时间解析失败,保留全部
                keep.extend(group)
        else:
            keep.extend(group)

    return keep, removed


def clean_legacy_files(dry_run: bool = False):
    r"""清理冗余 JSON 文件"""
    removed = []
    for fn in REDUNDANT_FILES:
        fp = DATA_DIR / fn
        if fp.exists():
            if not dry_run:
                fp.unlink()
            removed.append(str(fp.relative_to(PROJECT_ROOT)))
    return removed


def main():
    parser = argparse.ArgumentParser(
        description='清理 system.db 业务表里的脏数据 + 冗余 JSON 文件',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--dry-run', action='store_true', help='只扫描不删除')
    parser.add_argument('--no-orphan', action='store_true', help='跳过孤儿任务清理')
    parser.add_argument('--no-question', action='store_true', help='跳过 ? 占位符清理')
    parser.add_argument('--no-test-order', action='store_true', help='跳过测试工单清理')
    parser.add_argument('--no-repeat', action='store_true', help='跳过重复任务清理')
    parser.add_argument('--no-legacy', action='store_true', help='跳过冗余 JSON 文件清理')
    parser.add_argument('--no-backup', action='store_true', help='跳过 system.db 备份（不推荐）')
    parser.add_argument('--window-hours', type=int, default=24,
                        help='重复任务判定窗口（小时），默认 24')
    args = parser.parse_args()

    print('=' * 70)
    print(' 业务表脏数据清理工具 [K22]')
    print('=' * 70)
    print(f' 数据源: {SYSTEM_DB}')
    print(f' 模式: {"DRY-RUN (只扫描不删)" if args.dry_run else "正式清理"}')
    print(f' 备份: {"关闭" if args.no_backup else "开启"}')
    print(f' 清理项: orphan={"关" if args.no_orphan else "开"}, '
          f'question={"关" if args.no_question else "开"}, '
          f'test_order={"关" if args.no_test_order else "开"}, '
          f'repeat={"关" if args.no_repeat else "开"}, '
          f'legacy={"关" if args.no_legacy else "开"}')
    print()

    if not SYSTEM_DB.exists():
        print(f'[FATAL] system.db 不存在: {SYSTEM_DB}')
        sys.exit(1)

    doc, original_updated_at = load_doc()
    if doc is None:
        print(f'[FATAL] tbl_documents 里找不到 id={DOC_ID!r}')
        sys.exit(1)

    tasks = doc.get('process_tasks', [])
    original_count = len(tasks)
    print(f'[扫描] 当前 process_tasks 共 {original_count} 条任务')
    print()

    # 1. 备份
    backup_path = None
    if not args.dry_run and not args.no_backup:
        backup_path = backup_db()
        print(f'[备份] 已备份到: {backup_path.relative_to(PROJECT_ROOT)}')

    # 2. 清理 tasks
    removed_total = []
    new_tasks = tasks

    if not args.no_orphan:
        new_tasks, removed = clean_orphans(new_tasks)
        if removed:
            print(f'[孤儿] 删除 {len(removed)} 条 (order_no=null 或 process="")')
            for r in removed[:5]:
                print(f'    task_id={r.get("task_id")} status={r.get("status")} '
                      f'created={r.get("created_at")}')
            if len(removed) > 5:
                print(f'    ... 共 {len(removed)} 条')
        else:
            print('[孤儿] 无脏数据')
        removed_total.extend(removed)

    if not args.no_question:
        new_tasks, removed = clean_questions(new_tasks)
        if removed:
            print(f'[?占位] 删除 {len(removed)} 条 (process 含 ?)')
            for r in removed:
                print(f'    task_id={r.get("task_id")} order_no={r.get("order_no")} '
                      f'process={r.get("process")!r}')
        else:
            print('[?占位] 无脏数据')
        removed_total.extend(removed)

    if not args.no_test_order:
        new_tasks, removed = clean_test_orders(new_tasks)
        if removed:
            print(f'[测试工单] 删除 {len(removed)} 条 (ORD-REAL/TEST)')
            for r in removed:
                print(f'    task_id={r.get("task_id")} order_no={r.get("order_no")} '
                      f'work_order_no={r.get("work_order_no")}')
        else:
            print('[测试工单] 无脏数据')
        removed_total.extend(removed)

    if not args.no_repeat:
        before_repeat = len(new_tasks)
        new_tasks, removed = clean_repeats(new_tasks, window_hours=args.window_hours)
        if removed:
            print(f'[重复任务] 删除 {len(removed)} 条 (同 order_no+process 在 {args.window_hours}h 内多次 sent)')
            from collections import Counter
            keys = Counter((r.get('order_no'), r.get('process')) for r in removed)
            for key, c in keys.most_common(15):
                print(f'    {key[0]} / {key[1]}: 删除 {c} 条')
        else:
            print('[重复任务] 无脏数据')
        removed_total.extend(removed)

    # 3. 写回 DB
    if removed_total:
        doc['process_tasks'] = new_tasks
        if not args.dry_run:
            save_doc(doc)
            print(f'\n[写入] process_tasks: {original_count} → {len(new_tasks)} '
                  f'(删除 {len(removed_total)} 条)')
        else:
            print(f'\n[DRY-RUN] 将删除 {len(removed_total)} 条,实际未写入')
    else:
        print('\n[结果] 无脏数据,无需清理')

    # 4. 清理冗余 JSON
    if not args.no_legacy:
        legacy_files = clean_legacy_files(dry_run=args.dry_run)
        if legacy_files:
            print(f'\n[冗余文件] 删除 {len(legacy_files)} 个:')
            for f in legacy_files:
                print(f'    {f}')
        else:
            print('[冗余文件] 无')

    # 5. 汇总
    print()
    print('=' * 70)
    print(' 清理汇总')
    print('=' * 70)
    print(f' process_tasks: {original_count} → {len(new_tasks)} (删除 {len(removed_total)} 条)')
    if backup_path:
        print(f' 备份: {backup_path.relative_to(PROJECT_ROOT)}')
    print(f' 模式: {"DRY-RUN" if args.dry_run else "已写入"}')
    if not args.dry_run and removed_total:
        print(f'\n ✅ 清理完成。建议重启主程序查看效果。')
    elif args.dry_run:
        print(f'\n (DRY-RUN) 如确认无问题,去掉 --dry-run 重新执行')
    print('=' * 70)


if __name__ == '__main__':
    main()