# -*- coding: utf-8 -*-
"""
缓存覆盖率静态分析器 — 扫所有 Flask 路由，统计哪些接口用了缓存、哪些没用。

输出:
    - 控制台表格（按文件分组）
    - JSON 报告 cache_audit_report.json
    - Markdown 报告 cache_audit_report.md

使用方法:
    python scripts/tools/cache_audit_static.py
    python scripts/tools/cache_audit_static.py --target mobile_api_ai
"""
import os
import re
import json
import argparse
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_TARGET = ROOT / "mobile_api_ai"

ROUTE_PATTERN = re.compile(
    r"@app\.route\((?P<rule>[^)]+)\)|@bp\.route\((?P<rule2>[^)]+)\)",
    re.MULTILINE,
)

CACHE_PATTERNS = [
    (r"cache\.(get|set|delete|incr|expire|get_many|set_many|clear_pattern)\s*\(", "Redis cache"),
    (r"redis_cache\.(get|set|delete|incr|expire)\s*\(", "Redis cache (alias)"),
    (r"from cache import", "import cache"),
    (r"_ssot_cache_(get|set)\s*\(", "_ssot_cache"),
    (r"_customer_group_cache", "_customer_group_cache"),
    (r"_operators_cache", "_operators_cache"),
    (r"_pd_cache", "_pd_cache"),
    (r"_processes_cache", "_processes_cache"),
    (r"_mirror_auth_warn_cache", "_mirror_auth_warn_cache"),
    (r"_dedup_cache", "_dedup_cache"),
    (r"_PROCESS_TASKS_CACHE", "_PROCESS_TASKS_CACHE"),
    (r"_SCHEDULE_LIST_CACHE", "_SCHEDULE_LIST_CACHE"),
    (r"warmup_cache|async_warmup_cache", "cache_warmup"),
]


def normalize_rule(route_text: str) -> str:
    rule = route_text.strip()
    if rule.startswith(("'", '"')):
        rule = rule[1:]
    if rule.endswith((",", "'", '"')):
        rule = rule.rstrip("',\"")
    return rule.strip()


def extract_route_block(source: str, start_pos: int) -> tuple:
    """从 @app.route 位置往后找函数定义 body"""
    sub = source[start_pos:]
    lines = sub.split("\n")
    block_lines = []
    in_block = False
    for i, line in enumerate(lines):
        if i > 0 and (line.strip().startswith("@app.route") or line.strip().startswith("@bp.route")):
            break
        if line.strip().startswith("def "):
            in_block = True
        if in_block:
            block_lines.append(line)
        if in_block and len(block_lines) > 80:
            break
    return "\n".join(block_lines)


def detect_cache_usage(block: str) -> list:
    used = []
    for pattern, label in CACHE_PATTERNS:
        if re.search(pattern, block):
            if label not in used:
                used.append(label)
    return used


def classify_endpoint(method: str, rule: str, has_cache: bool) -> str:
    """根据 HTTP 方法和路径判断接口类型"""
    if method != "GET":
        return "write"
    cacheable_substrings = [
        "/list", "/detail", "/status", "/summary", "/count",
        "/config", "/dict", "/template", "/rule",
        "/process", "/operator", "/material", "/order",
        "/all-process", "/tasks", "/health", "/status",
    ]
    if any(s in rule.lower() for s in cacheable_substrings):
        return "cacheable_get" if not has_cache else "cached"
    return "static_or_dynamic"


def scan_file(filepath: Path) -> list:
    """扫单个 .py 文件"""
    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception:
        return []

    results = []
    for m in ROUTE_PATTERN.finditer(text):
        raw = m.group("rule") or m.group("rule2")
        rule = normalize_rule(raw)

        methods_match = re.search(r"methods\s*=\s*\[([^\]]+)\]", rule)
        if methods_match:
            methods = [x.strip().strip("'\"") for x in methods_match.group(1).split(",")]
            rule_clean = re.sub(r",\s*methods\s*=\s*\[[^\]]+\]", "", rule).strip()
        else:
            methods = ["GET"]
            rule_clean = rule

        block = extract_route_block(text, m.end())
        used = detect_cache_usage(block)
        category = classify_endpoint(methods[0], rule_clean, bool(used))

        line_no = text[: m.start()].count("\n") + 1
        results.append({
            "file": str(filepath.relative_to(ROOT)).replace("\\", "/"),
            "line": line_no,
            "methods": methods,
            "rule": rule_clean,
            "cache_used": used,
            "category": category,
        })
    return results


def scan_target(target_dir: Path) -> list:
    all_results = []
    for py in target_dir.rglob("*.py"):
        if "__pycache__" in py.parts or ".bak" in py.name or ",cover" in py.name:
            continue
        if py.name in ("cache.py", "cache_warmup.py", "rate_limiter.py"):
            continue
        all_results.extend(scan_file(py))
    return all_results


def print_table(results: list):
    by_file = {}
    for r in results:
        by_file.setdefault(r["file"], []).append(r)

    print("\n" + "=" * 100)
    print(f" 缓存覆盖审计报告 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 100)

    total = len(results)
    cached = sum(1 for r in results if r["cache_used"])
    cacheable_no_cache = sum(1 for r in results
                              if r["category"] == "cacheable_get" and not r["cache_used"])
    print(f"\n总接口数: {total}")
    print(f"已用缓存: {cached}  ({cached * 100 // max(total, 1)}%)")
    print(f"可缓存但未缓存: {cacheable_no_cache}")

    for f, items in sorted(by_file.items()):
        cached_in_file = sum(1 for x in items if x["cache_used"])
        print(f"\n  📄 {f}  ({cached_in_file}/{len(items)} 用缓存)")
        print(f"  {'─' * 90}")
        for r in items:
            mark = "✅" if r["cache_used"] else ("⚠️ " if r["category"] == "cacheable_get" else "  ")
            methods = "/".join(r["methods"])
            cache_label = " | ".join(r["cache_used"]) if r["cache_used"] else "-"
            print(f"  {mark} {methods:6s} {r['rule'][:60]:60s} [{cache_label}]")


def write_json(results: list, target: Path):
    out = target / "cache_audit_report.json"
    out.write_text(
        json.dumps({"generated_at": datetime.now().isoformat(),
                    "total": len(results),
                    "results": results},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n✅ JSON 报告: {out}")


def write_markdown(results: list, target: Path):
    out = target / "cache_audit_report.md"
    total = len(results)
    cached = sum(1 for r in results if r["cache_used"])
    cacheable_no_cache = [r for r in results
                          if r["category"] == "cacheable_get" and not r["cache_used"]]

    lines = [
        f"# 缓存覆盖审计报告",
        f"",
        f"- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"- 总接口数: **{total}**",
        f"- 已用缓存: **{cached}** ({cached * 100 // max(total, 1)}%)",
        f"- 可缓存但未缓存: **{len(cacheable_no_cache)}**",
        f"",
        f"## 高优先级: 可缓存但未缓存的接口",
        f"",
        f"| 文件 | 行号 | 方法 | 路径 |",
        f"|------|------|------|------|",
    ]
    for r in sorted(cacheable_no_cache, key=lambda x: (x["file"], x["line"])):
        lines.append(f"| {r['file']} | {r['line']} | {','.join(r['methods'])} | `{r['rule']}` |")

    lines.append("")
    lines.append("## 所有接口详情")
    lines.append("")
    lines.append("| 文件 | 行号 | 方法 | 路径 | 已用缓存 |")
    lines.append("|------|------|------|------|---------|")
    for r in sorted(results, key=lambda x: (x["file"], x["line"])):
        cache_label = "<br>".join(r["cache_used"]) if r["cache_used"] else "-"
        lines.append(f"| {r['file']} | {r['line']} | {','.join(r['methods'])} | `{r['rule']}` | {cache_label} |")

    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"✅ Markdown 报告: {out}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    if not args.target.exists():
        print(f"❌ 目标目录不存在: {args.target}")
        return

    out_dir = args.out or args.target
    results = scan_target(args.target)
    print_table(results)
    write_json(results, out_dir)
    write_markdown(results, out_dir)


if __name__ == "__main__":
    main()
