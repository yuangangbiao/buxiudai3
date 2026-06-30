#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
录屏 PART2: 后 5 张幻灯片(10-14)
使用 ?start=10 URL 参数跳过前 9 张
总时长: 5 张 × 45s = 3.75 分钟
"""
import sys
import time
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright

WORK_DIR = Path(r"d:\yuan\不锈钢网带跟单3.0")
HTML_FILE = WORK_DIR / "docs" / "演示视频_不锈钢3.0_客户演示.html"
VIDEO_DIR = WORK_DIR / "docs" / "demo_videos"

START_SLIDE = 10  # 1-indexed: 第 10 张
END_SLIDE = 14    # 1-indexed: 第 14 张
SLIDE_DURATION = 45
INIT_WAIT = 5
FINAL_WAIT = 3
TOTAL_SLIDES = END_SLIDE - START_SLIDE + 1  # 5


def main() -> int:
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_path = VIDEO_DIR / f"演示视频_不锈钢3.0_客户演示_PART2_10to14_{timestamp}.webm"

    print("=" * 60)
    print(f"录屏 PART2: 幻灯片 {START_SLIDE}-{END_SLIDE} (共 {TOTAL_SLIDES} 张)")
    print("=" * 60)
    print(f"HTML: {HTML_FILE}")
    print(f"输出: {video_path}")
    print(f"时长: {TOTAL_SLIDES} 张 × {SLIDE_DURATION}s = ~{TOTAL_SLIDES * SLIDE_DURATION / 60:.1f} 分钟")
    print("=" * 60)

    with sync_playwright() as p:
        page = None
        context = None
        browser = None
        try:
            print("[1/4] 启动 Chromium headless ...", flush=True)
            browser = p.chromium.launch(
                headless=True,
                chromium_sandbox=False,
                args=[
                    "--no-sandbox",
                    "--disable-gpu",
                    "--disable-dev-shm-usage",
                    "--disable-extensions",
                    "--disable-software-rasterizer",
                    "--disable-features=Translate,BackForwardCache,AcceleratedVideoDecodeLinuxGL,UseDXGI,UseSkiaRenderer",
                    "--disable-accelerated-2d-canvas",
                    "--in-process-gpu",
                    "--single-process",  # 关键: 单进程,避免子进程触发沙箱
                    "--disable-background-networking",
                    "--disable-component-update",
                    "--disable-default-apps",
                ],
            )
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                device_scale_factor=1,
                record_video_dir=str(VIDEO_DIR),
                record_video_size={"width": 1920, "height": 1080},
            )
            page = context.new_page()

            url = f"file:///{HTML_FILE.as_posix()}?start={START_SLIDE}"
            print(f"[2/4] 加载 HTML (start={START_SLIDE}) ...", flush=True)
            page.goto(url)
            page.wait_for_load_state("networkidle", timeout=30000)
            print(f"       等待 {INIT_WAIT}s 让动画初始化 ...", flush=True)
            time.sleep(INIT_WAIT)

            print(f"[3/4] 开始录屏 — 翻页 {TOTAL_SLIDES - 1} 次", flush=True)
            for i in range(TOTAL_SLIDES - 1):
                print(f"       [{i+1:2d}/{TOTAL_SLIDES-1}] 等待 {SLIDE_DURATION}s ...", flush=True)
                time.sleep(SLIDE_DURATION)
                page.keyboard.press("ArrowRight")
                time.sleep(0.5)
            print(f"       最后一页等待 {SLIDE_DURATION + FINAL_WAIT}s ...", flush=True)
            time.sleep(SLIDE_DURATION + FINAL_WAIT)
        finally:
            print(f"[4/4] 关闭浏览器 ...", flush=True)
            if page:
                try: page.close()
                except: pass
            if context:
                try: context.close()
                except: pass
            if browser:
                try: browser.close()
                except: pass

    video_files = sorted(VIDEO_DIR.glob("*.webm"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not video_files:
        print("[ERROR] 未找到视频文件")
        return 2
    latest = video_files[0]
    if latest != video_path:
        latest.rename(video_path)

    size_mb = video_path.stat().st_size / 1024 / 1024
    print("=" * 60)
    print(f"✅ PART2 录屏完成")
    print(f"   文件: {video_path}")
    print(f"   大小: {size_mb:.2f} MB")
    print(f"   包含: 幻灯片 {START_SLIDE}-{END_SLIDE}")
    print("=" * 60)
    print("\n💡 合并 PART1 + PART2:")
    print(f"   PART1: 演示视频_不锈钢3.0_客户演示_PART1_9of14_前6分钟.webm (4.13MB)")
    print(f"   PART2: {video_path.name}")
    print("   合并方法: VLC 打开多个文件 → 转换/保存 → 选择 '拼接'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
