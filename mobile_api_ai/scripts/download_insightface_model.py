# -*- coding: utf-8 -*-
"""
INSIGHTFACE buffalo_l 模型下载脚本
"""
import os
import sys
import urllib.request
import zipfile
from pathlib import Path

# 模型下载URL
MODEL_URL = "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip"
MODEL_NAME = "buffalo_l"

# 目标目录
BASE_DIR = Path(__file__).parent
MODEL_DIR = BASE_DIR / "models" / MODEL_NAME

def download_progress(block_num, block_size, total_size):
    """显示下载进度"""
    downloaded = block_num * block_size
    percent = min(100, downloaded * 100 / total_size)
    if total_size > 0:
        print(f"\r下载进度: {percent:.1f}% ({downloaded/1024/1024:.1f}MB / {total_size/1024/1024:.1f}MB)", end='', flush=True)

def download_model():
    """下载并解压模型"""
    print(f"=" * 60)
    print(f"INSIGHTFACE buffalo_l 模型下载工具")
    print(f"=" * 60)

    # 创建目录
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = MODEL_DIR / f"{MODEL_NAME}.zip"

    # 检查是否已下载
    if zip_path.exists():
        print(f"\n发现已下载的压缩包: {zip_path}")
        response = input("是否重新下载？(y/N): ").strip().lower()
        if response != 'y':
            print("跳过下载，直接解压...")
            return zip_path

    print(f"\n开始下载模型...")
    print(f"下载地址: {MODEL_URL}")
    print(f"保存位置: {zip_path}")

    try:
        # 下载文件（使用 urllib 而非 curl）
        urllib.request.urlretrieve(MODEL_URL, zip_path, download_progress)
        print(f"\n\n✅ 模型下载完成！")
        return zip_path
    except Exception as e:
        print(f"\n\n❌ 下载失败: {e}")
        if zip_path.exists():
            zip_path.unlink()
        return None

def extract_model(zip_path):
    """解压模型文件"""
    print(f"\n开始解压模型...")

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # 解压到 models/buffalo_l/ 目录
            zip_ref.extractall(MODEL_DIR)

        print(f"✅ 模型解压完成！")
        print(f"\n模型文件位置: {MODEL_DIR}")

        # 列出解压后的文件
        print("\n模型文件列表:")
        for item in sorted(MODEL_DIR.rglob("*")):
            if item.is_file():
                size_mb = item.stat().st_size / 1024 / 1024
                print(f"  - {item.name} ({size_mb:.2f}MB)")

        return True
    except Exception as e:
        print(f"\n❌ 解压失败: {e}")
        return False

def verify_model():
    """验证模型文件"""
    print("\n验证模型文件...")

    required_files = [
        "buffalo_l.json",
        "det_10g.onnx",
        "w600k_r50.onnx",
    ]

    all_exist = True
    for file_name in required_files:
        file_path = MODEL_DIR / file_name
        if file_path.exists():
            size_mb = file_path.stat().st_size / 1024 / 1024
            print(f"  ✅ {file_name} ({size_mb:.2f}MB)")
        else:
            print(f"  ❌ {file_name} (未找到)")
            all_exist = False

    # 检查子目录
    subdir = MODEL_DIR / "2d106det"
    if subdir.exists():
        onnx_file = subdir / "2d106det.onnx"
        if onnx_file.exists():
            size_mb = onnx_file.stat().st_size / 1024 / 1024
            print(f"  ✅ 2d106det/2d106det.onnx ({size_mb:.2f}MB)")

    return all_exist

def main():
    print("\n" + "=" * 60)
    print("INSIGHTFACE buffalo_l 模型下载工具")
    print("=" * 60)
    print(f"\n目标目录: {MODEL_DIR}")

    # 检查是否已有完整模型
    if verify_model():
        print("\n✅ 模型已完整存在，无需重新下载！")
        return 0

    # 下载模型
    zip_path = download_model()
    if not zip_path:
        return 1

    # 解压模型
    if not extract_model(zip_path):
        return 1

    # 验证模型
    if verify_model():
        print("\n" + "=" * 60)
        print("✅ 模型准备完成！")
        print("=" * 60)
        print(f"\n模型位置: {MODEL_DIR}")
        print("\n下一步：")
        print("1. 安装依赖: pip install insightface onnxruntime-gpu")
        print("2. 运行测试脚本验证模型")
    else:
        print("\n❌ 模型验证失败，请检查网络连接后重试！")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
