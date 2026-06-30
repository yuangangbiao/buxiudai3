#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
不锈钢 3.0 客户演示 - HTML 自动录屏脚本

技术栈：Playwright + headless Chromium
输出：.webm 视频（VP8 + Opus），Chrome/VLC/微信可直接播放
视窗：1920x1080 (16:9)
时长：每张幻灯片 60 秒，14 张共 ~14 分钟

用法：
    & "C:/Users/lenovo/AppData/Local/Python/bin/python.exe" scripts/record_demo_video.py
"""
import os
import sys
import time
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright

WORK_DIR = Path(r"d:\yuan\不锈钢网带跟单3.0")
HTML_FILE = WORK_DIR / "docs" / "演示视频_不锈钢3.0_客户演示.html"
VIDEO_DIR = WORK_DIR / "docs" / "demo_videos"

# 每张幻灯片停留秒数（45s = 14 张 × 45s = 10.5 分钟,落在 10-15 分钟预算下沿）
SLIDE_DURATION = 45
SLIDE_COUNT = 14
# 启动等待（HTML 加载+字体+动画初始化）
INIT_WAIT = 5
# 最后一页额外停留（避免录屏结束在切换瞬间）
FINAL_WAIT = 3


def main() -> int:
    if not HTML_FILE.exists():
        print(f"[ERROR] HTML not found: {HTML_FILE}")
        return 1

    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_path = VIDEO_DIR / f"演示视频_不锈钢3.0_客户演示_{timestamp}.webm"

    print("=" * 60)
    print("不锈钢 3.0 客户演示 - 自动录屏")
    print("=" * 60)
    print(f"HTML 文件: {HTML_FILE}")
    print(f"视频输出: {video_path}")
    print(f"幻灯片数: {SLIDE_COUNT} 张 × {SLIDE_DURATION} 秒 = ~{SLIDE_COUNT * SLIDE_DURATION / 60:.1f} 分钟")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    with sync_playwright() as p:
        page = None
        context = None
        browser = None
        try:
            print("[1/4] 启动 Chromium headless ...", flush=True)
            browser = p.chromium.launch(
                headless=True,
                chromium_sandbox=False,  # 关键: 禁用 chromium 内部沙箱,避免拦截系统文件访问
                args=[
                    "--no-sandbox",
                    "--disable-gpu",
                    "--disable-dev-shm-usage",
                    "--disable-extensions",
                    "--disable-software-rasterizer",
                    "--disable-features=Translate,BackForwardCache,AcceleratedVideoDecodeLinuxGL",
                    "--disable-accelerated-2d-canvas",
                    "--in-process-gpu",
                ],
            )
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                device_scale_factor=1,
                record_video_dir=str(VIDEO_DIR),
                record_video_size={"width": 1920, "height": 1080},
            )
            page = context.new_page()

            print(f"[2/4] 加载 HTML: {HTML_FILE.name}", flush=True)
            page.goto(f"file:///{HTML_FILE.as_posix()}")
            page.wait_for_load_state("networkidle", timeout=30000)
            print(f"       等待 {INIT_WAIT}s 让动画初始化 ...", flush=True)
            time.sleep(INIT_WAIT)

            total_duration = INIT_WAIT
            print(f"[3/4] 开始录屏 — 翻页 14 张幻灯片,每张 {SLIDE_DURATION}s", flush=True)
            for i in range(SLIDE_COUNT - 1):
                print(f"       [{i+1:2d}/{SLIDE_COUNT}] 等待 {SLIDE_DURATION}s ... (累计 {total_duration}s)", flush=True)
                time.sleep(SLIDE_DURATION)
                page.keyboard.press("ArrowRight")
                time.sleep(0.5)  # 翻页过渡
                total_duration += SLIDE_DURATION

            # 最后一页
            print(f"       [{SLIDE_COUNT:2d}/{SLIDE_COUNT}] 最后一页等待 {SLIDE_DURATION + FINAL_WAIT}s ... (累计 {total_duration + SLIDE_DURATION + FINAL_WAIT}s)", flush=True)
            time.sleep(SLIDE_DURATION + FINAL_WAIT)
        finally:
            print(f"[4/4] 关闭浏览器,保存视频 ...", flush=True)
            if page:
                try:
                    page.close()
                except Exception as e:
                    print(f"[WARN] page.close 失败: {e}", flush=True)
            if context:
                try:
                    context.close()
                except Exception as e:
                    print(f"[WARN] context.close 失败: {e}", flush=True)
            if browser:
                try:
                    browser.close()
                except Exception as e:
                    print(f"[WARN] browser.close 失败: {e}", flush=True)

    # 查找最新录屏文件
    video_files = sorted(VIDEO_DIR.glob("*.webm"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not video_files:
        print("[ERROR] 未找到录屏文件")
        return 2

    latest = video_files[0]
    # 重命名为目标文件名
    if latest != video_path:
        latest.rename(video_path)

    size_mb = video_path.stat().st_size / 1024 / 1024
    print("=" * 60)
    print(f"✅ 录屏完成")
    print(f"   文件: {video_path}")
    print(f"   大小: {size_mb:.2f} MB")
    print(f"   时长: ~{SLIDE_COUNT * SLIDE_DURATION / 60:.1f} 分钟")
    print("=" * 60)
    print("\n💡 播放方式:")
    print("   1. Chrome/Edge 直接双击打开")
    print("   2. VLC: 右键 → 用 VLC 播放")
    print("   3. 转 .mp4: VLC 菜单 媒体→转换/保存 (Ctrl+R)")
    print(f"\n   完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
