#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""录屏第 14 张(CTA) - 1 张 × 60s = 1 分钟"""
import sys
import time
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright

WORK_DIR = Path(r"d:\yuan\不锈钢网带跟单3.0")
HTML_FILE = WORK_DIR / "docs" / "演示视频_不锈钢3.0_客户演示.html"
VIDEO_DIR = WORK_DIR / "docs" / "demo_videos"

START_SLIDE = 14
DURATION = 60  # 60 秒


def main() -> int:
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_path = VIDEO_DIR / f"演示视频_不锈钢3.0_客户演示_PART3_slide14_{timestamp}.webm"

    print(f"录屏第 14 张(CTA), 60 秒")
    print(f"输出: {video_path}")

    with sync_playwright() as p:
        page = context = browser = None
        try:
            browser = p.chromium.launch(
                headless=True,
                chromium_sandbox=False,
                args=[
                    "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
                    "--disable-extensions", "--disable-software-rasterizer",
                    "--disable-features=Translate,BackForwardCache,AcceleratedVideoDecodeLinuxGL",
                    "--disable-accelerated-2d-canvas", "--in-process-gpu",
                    "--single-process", "--disable-background-networking",
                    "--disable-component-update", "--disable-default-apps",
                ],
            )
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                record_video_dir=str(VIDEO_DIR),
                record_video_size={"width": 1920, "height": 1080},
            )
            page = context.new_page()
            url = f"file:///{HTML_FILE.as_posix()}?start={START_SLIDE}"
            print(f"加载 {url}")
            page.goto(url)
            page.wait_for_load_state("networkidle", timeout=30000)
            time.sleep(5)
            print(f"等待 {DURATION}s 录屏")
            time.sleep(DURATION)
        finally:
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
        print("[ERROR] 未找到视频")
        return 2
    latest = video_files[0]
    if latest != video_path:
        latest.rename(video_path)
    size_mb = video_path.stat().st_size / 1024 / 1024
    print(f"✅ 完成: {video_path} ({size_mb:.2f}MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
