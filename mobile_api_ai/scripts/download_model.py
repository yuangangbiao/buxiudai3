# -*- coding: utf-8 -*-
"""
INSIGHTFACE buffalo_l Model Download Script
"""
import os
import sys
import urllib.request
import zipfile
from pathlib import Path

MODEL_URL = "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip"
MODEL_NAME = "buffalo_l"

BASE_DIR = Path(__file__).parent.parent
MODEL_DIR = BASE_DIR / "models" / MODEL_NAME

def download_progress(block_num, block_size, total_size):
    """Show download progress"""
    downloaded = block_num * block_size
    percent = min(100, downloaded * 100 / total_size) if total_size > 0 else 0
    print(f"\rDownloading: {percent:.1f}% ({downloaded/1024/1024:.1f}MB / {total_size/1024/1024:.1f}MB)", end='', flush=True)

def main():
    print("=" * 60)
    print("INSIGHTFACE buffalo_l Model Download Tool")
    print("=" * 60)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = MODEL_DIR / f"{MODEL_NAME}.zip"

    if zip_path.exists():
        print(f"\nFound existing zip: {zip_path}")
        response = input("Redownload? (y/N): ").strip().lower()
        if response != 'y':
            print("Skip download, extract existing...")
        else:
            zip_path.unlink()
    else:
        print(f"\nDownloading model...")
        print(f"URL: {MODEL_URL}")
        print(f"Saving to: {zip_path}")

        try:
            urllib.request.urlretrieve(MODEL_URL, zip_path, download_progress)
            print(f"\n\nDownload completed!")
        except Exception as e:
            print(f"\n\nDownload failed: {e}")
            return 1

    print(f"\nExtracting model...")

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(MODEL_DIR)

        print(f"Extraction completed!")
        print(f"\nModel location: {MODEL_DIR}")

        print("\nModel files:")
        for item in sorted(MODEL_DIR.rglob("*")):
            if item.is_file():
                size_mb = item.stat().st_size / 1024 / 1024
                print(f"  - {item.name} ({size_mb:.2f}MB)")

    except Exception as e:
        print(f"\nExtraction failed: {e}")
        return 1

    print("\nVerifying model files...")

    required_files = ["buffalo_l.json", "det_10g.onnx", "w600k_r50.onnx"]
    all_exist = True

    for file_name in required_files:
        file_path = MODEL_DIR / file_name
        if file_path.exists():
            size_mb = file_path.stat().st_size / 1024 / 1024
            print(f"  [OK] {file_name} ({size_mb:.2f}MB)")
        else:
            print(f"  [MISSING] {file_name}")
            all_exist = False

    subdir = MODEL_DIR / "2d106det"
    if subdir.exists():
        onnx_file = subdir / "2d106det.onnx"
        if onnx_file.exists():
            size_mb = onnx_file.stat().st_size / 1024 / 1024
            print(f"  [OK] 2d106det/2d106det.onnx ({size_mb:.2f}MB)")

    print("")
    print("=" * 60)
    if all_exist:
        print("Model ready!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Install dependencies: pip install insightface onnxruntime-gpu")
        print("2. Configure model path (see deployment plan)")
    else:
        print("Model verification failed!")
        print("=" * 60)
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
