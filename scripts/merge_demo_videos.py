#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
合并 3 个 PART 视频为最终 .mp4
使用 imageio-ffmpeg 提供的 ffmpeg 二进制
输出:H.264 视频 + AAC 音频(标准 mp4 格式,兼容性最佳)
"""
import sys
import subprocess
from pathlib import Path
from datetime import datetime
import imageio_ffmpeg

VIDEO_DIR = Path(r"d:\yuan\不锈钢网带跟单3.0\docs\demo_videos")
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

# 按顺序的 PART 文件名
PARTS = [
    "演示视频_不锈钢3.0_客户演示_PART1_9of14_前6分钟.webm",
    "演示视频_不锈钢3.0_客户演示_PART2_10to13_4张.webm",
    "演示视频_不锈钢3.0_客户演示_PART3_slide14_20260614_153246.webm",
]


def main() -> int:
    # 验证所有 PART 文件存在
    missing = [p for p in PARTS if not (VIDEO_DIR / p).exists()]
    if missing:
        print(f"[ERROR] 缺失文件: {missing}")
        return 1

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_path = VIDEO_DIR / f"演示视频_不锈钢3.0_客户演示_FINAL_{timestamp}.mp4"

    # 创建 concat 文件列表
    list_path = VIDEO_DIR / "concat_list.txt"
    with open(list_path, "w", encoding="utf-8") as f:
        for p in PARTS:
            # ffmpeg concat 格式:file 'filename'
            f.write(f"file '{p}'\n")

    print("=" * 60)
    print("合并 3 个 PART 视频 → 最终 .mp4")
    print("=" * 60)
    print(f"FFmpeg: {FFMPEG}")
    print(f"输出: {final_path.name}")
    for i, p in enumerate(PARTS, 1):
        size = (VIDEO_DIR / p).stat().st_size / 1024 / 1024
        print(f"  PART{i}: {p} ({size:.2f} MB)")
    print("=" * 60)

    # ffmpeg concat + 转码为 mp4
    cmd = [
        FFMPEG,
        "-y",                              # 覆盖输出
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_path),
        "-c:v", "libx264",                 # H.264 视频
        "-preset", "fast",                 # 编码速度
        "-crf", "20",                      # 质量(18-23 推荐)
        "-c:a", "aac",                     # AAC 音频
        "-b:a", "128k",
        "-movflags", "+faststart",         # 优化网络播放
        str(final_path),
    ]
    print("\n执行 ffmpeg ...")
    print(" ".join(cmd))
    print()

    result = subprocess.run(cmd, capture_output=True, text=True)

    # 清理临时文件
    list_path.unlink(missing_ok=True)

    if result.returncode != 0:
        print(f"[ERROR] ffmpeg 返回 {result.returncode}")
        print("STDERR (最后 50 行):")
        for line in result.stderr.splitlines()[-50:]:
            print(line)
        return 2

    if not final_path.exists():
        print("[ERROR] 输出文件未生成")
        return 3

    size_mb = final_path.stat().st_size / 1024 / 1024
    print("=" * 60)
    print(f"✅ 最终视频生成成功")
    print(f"   文件: {final_path}")
    print(f"   大小: {size_mb:.2f} MB")
    print(f"   格式: MP4 (H.264 + AAC)")
    print(f"   兼容: Chrome/Edge/VLC/微信/QQ/PPT")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
