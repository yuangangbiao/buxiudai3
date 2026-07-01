# -*- coding: utf-8 -*-
"""
INSIGHTFACE All Models Batch Download Script
"""
import os
import sys
import urllib.request
import zipfile
from pathlib import Path

# 所有模型及其下载信息
MODELS = {
    "buffalo_l": {
        "url": "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip",
        "description": "高精度版本（推荐用于考勤）",
        "size": "275 MB"
    },
    "buffalo_m": {
        "url": "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_m.zip",
        "description": "中等精度，平衡性能",
        "size": "263 MB"
    },
    "buffalo_s": {
        "url": "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_s.zip",
        "description": "快速版本，适合移动端",
        "size": "122 MB"
    },
    "buffalo_sc": {
        "url": "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_sc.zip",
        "description": "紧凑版本，仅检测",
        "size": "14.3 MB"
    },
    "antelopev2": {
        "url": "https://github.com/deepinsight/insightface/releases/download/v0.7/antelopev2.zip",
        "description": "高级版，ResNet100识别",
        "size": "344 MB"
    }
}

# INSIGHTFACE v0.7 独立模型
SINGLE_MODELS = {
    "inswapper_128": {
        "url": "https://github.com/deepinsight/insightface/releases/download/v0.7/inswapper_128.onnx",
        "description": "换脸模型",
        "size": "529 MB"
    },
    "scrfd_person_2.5g": {
        "url": "https://github.com/deepinsight/insightface/releases/download/v0.7/scrfd_person_2.5g.onnx",
        "description": "人体检测模型",
        "size": "3.54 MB"
    }
}

BASE_DIR = Path(__file__).parent.parent
MODEL_DIR = BASE_DIR / "models"

def download_file(url, dest_path, show_progress=True):
    """Download a single file with progress"""
    def progress_hook(block_num, block_size, total_size):
        if show_progress and total_size > 0:
            downloaded = block_num * block_size
            percent = min(100, downloaded * 100 / total_size)
            speed = downloaded / 1024 / 1024  # MB
            print(f"\r  [{percent:6.2f}%] {speed:6.2f} MB/s", end='', flush=True)

    try:
        print(f"\n  Downloading: {url.split('/')[-1]}")
        urllib.request.urlretrieve(url, dest_path, progress_hook)
        print()  # New line after progress
        return True
    except Exception as e:
        print(f"\n  ❌ Download failed: {e}")
        return False

def extract_zip(zip_path, extract_to):
    """Extract zip file"""
    try:
        print(f"  Extracting to: {extract_to}")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        print(f"  ✅ Extracted successfully")
        return True
    except Exception as e:
        print(f"  ❌ Extraction failed: {e}")
        return False

def verify_model(model_dir, model_name):
    """Verify model files"""
    print(f"\n  Verifying {model_name} files...")

    # Check for expected files
    required_patterns = {
        "buffalo_l": ["buffalo_l.json", "det_10g.onnx", "w600k_r50.onnx"],
        "buffalo_m": ["buffalo_m.json", "det_2.5g.onnx", "w600k_r50.onnx"],
        "buffalo_s": ["buffalo_s.json", "det_500m.onnx", "w600k_mbf.onnx"],
        "buffalo_sc": ["buffalo_sc.json", "det_500m.onnx"],
        "antelopev2": ["antelopev2.json", "scrfd_10g_bnkps.onnx", "w600k_r50.onnx"]
    }

    patterns = required_patterns.get(model_name, [])

    if not patterns:
        print(f"  ⚠️  No verification patterns for {model_name}")
        return True

    all_exist = True
    for pattern in patterns:
        found = any(f.name == pattern for f in model_dir.rglob("*") if f.is_file())
        status = "✅" if found else "❌"
        print(f"    {status} {pattern}")
        if not found:
            all_exist = False

    return all_exist

def download_all_models():
    """Download all model packages"""
    print("=" * 80)
    print("INSIGHTFACE All Models Batch Download")
    print("=" * 80)
    print(f"\nTarget directory: {MODEL_DIR}")
    print(f"Total packages to download: {len(MODELS)}")

    # Create directory
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    # Display model information
    print("\n" + "-" * 80)
    print("Models to download:")
    print("-" * 80)
    for i, (name, info) in enumerate(MODELS.items(), 1):
        print(f"  {i}. {name:15s} - {info['description']:30s} ({info['size']})")
    print("-" * 80)

    # Ask for confirmation
    response = input("\nContinue with download? (Y/n): ").strip().lower()
    if response and response != 'y':
        print("Download cancelled.")
        return 0

    # Download each model
    success_count = 0
    total_size_mb = 0

    for model_name, info in MODELS.items():
        print(f"\n{'='*80}")
        print(f"[{success_count + 1}/{len(MODELS)}] Downloading {model_name}")
        print(f"{'='*80}")
        print(f"Description: {info['description']}")
        print(f"Size: {info['size']}")

        model_path = MODEL_DIR / model_name
        zip_path = MODEL_DIR / f"{model_name}.zip"

        # Check if already downloaded
        if model_path.exists() and any(model_path.iterdir()):
            print(f"\n⚠️  Model already exists at {model_path}")
            response = input("  Re-download? (y/N): ").strip().lower()
            if response != 'y':
                print("  ⏭️  Skipping...")
                success_count += 1
                continue
            else:
                # Clean up existing files
                import shutil
                shutil.rmtree(model_path)
                model_path.mkdir(parents=True, exist_ok=True)

        # Create model directory
        model_path.mkdir(parents=True, exist_ok=True)

        # Download zip file
        print(f"\n📥 Downloading...")
        if not download_file(info['url'], zip_path):
            print(f"❌ Failed to download {model_name}")
            continue

        # Extract zip file
        print(f"\n📦 Extracting...")
        if not extract_zip(zip_path, model_path):
            print(f"❌ Failed to extract {model_name}")
            continue

        # Verify model
        if not verify_model(model_path, model_name):
            print(f"⚠️  Model verification incomplete for {model_name}")

        # Clean up zip file
        print(f"\n🧹 Cleaning up zip file...")
        try:
            zip_path.unlink()
            print(f"  ✅ Zip file removed")
        except:
            pass

        success_count += 1
        size_mb = float(info['size'].replace(' MB', ''))
        total_size_mb += size_mb

        print(f"\n✅ {model_name} downloaded successfully!")

    # Download single models (.onnx files)
    print(f"\n\n{'='*80}")
    print("Downloading additional ONNX models")
    print(f"{'='*80}")

    for model_name, info in SINGLE_MODELS.items():
        onnx_path = MODEL_DIR / f"{model_name}.onnx"

        if onnx_path.exists():
            print(f"\n⏭️  {model_name}.onnx already exists, skipping...")
            continue

        print(f"\n📥 Downloading {model_name}.onnx...")
        if download_file(info['url'], onnx_path):
            print(f"✅ {model_name}.onnx downloaded successfully!")
            success_count += 1
        else:
            print(f"❌ Failed to download {model_name}.onnx")

    # Summary
    print(f"\n\n{'='*80}")
    print("Download Summary")
    print(f"{'='*80}")
    print(f"✅ Successfully downloaded: {success_count}/{len(MODELS) + len(SINGLE_MODELS)} packages")
    print(f"💾 Total size: ~{total_size_mb:.0f} MB")
    print(f"📁 Location: {MODEL_DIR}")

    # List all downloaded models
    print(f"\n{'='*80}")
    print("Downloaded Models:")
    print(f"{'='*80}")
    for item in sorted(MODEL_DIR.iterdir()):
        if item.is_dir():
            file_count = len(list(item.rglob("*.onnx")))
            print(f"  📁 {item.name}/ ({file_count} .onnx files)")
        elif item.suffix == ".onnx":
            size_mb = item.stat().st_size / 1024 / 1024
            print(f"  📄 {item.name} ({size_mb:.2f} MB)")

    print(f"\n{'='*80}")
    print("✅ All models download completed!")
    print(f"{'='*80}")
    print("\nNext steps:")
    print("1. Install dependencies: pip install insightface onnxruntime-gpu")
    print("2. Configure model path in your application")
    print("3. Test the models with example scripts")

    return 0 if success_count == len(MODELS) + len(SINGLE_MODELS) else 1

if __name__ == "__main__":
    sys.exit(download_all_models())
