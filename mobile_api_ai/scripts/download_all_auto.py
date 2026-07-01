# -*- coding: utf-8 -*-
"""
INSIGHTFACE All Models Auto Download Script (No Interaction)
"""
import os
import sys
import urllib.request
import zipfile
from pathlib import Path

# 所有模型
MODELS = {
    "buffalo_l": {
        "url": "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip",
        "description": "High precision (recommended)"
    },
    "buffalo_m": {
        "url": "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_m.zip",
        "description": "Medium precision"
    },
    "buffalo_s": {
        "url": "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_s.zip",
        "description": "Fast version"
    },
    "buffalo_sc": {
        "url": "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_sc.zip",
        "description": "Compact version"
    },
    "antelopev2": {
        "url": "https://github.com/deepinsight/insightface/releases/download/v0.7/antelopev2.zip",
        "description": "Advanced version"
    }
}

BASE_DIR = Path(__file__).parent.parent
MODEL_DIR = BASE_DIR / "models"

def download_progress(block_num, block_size, total_size):
    """Show download progress"""
    downloaded = block_num * block_size
    percent = min(100, downloaded * 100 / total_size) if total_size > 0 else 0
    speed_mb = downloaded / 1024 / 1024 / max(1, block_num) if block_num > 0 else 0
    print(f"\r  Progress: {percent:6.2f}% | Speed: {speed_mb:6.2f} MB/s | Downloaded: {downloaded/1024/1024:.2f} MB", end='', flush=True)

def download_model(model_name, info):
    """Download and extract a single model"""
    print(f"\n{'='*70}")
    print(f"Downloading: {model_name}")
    print(f"Description: {info['description']}")
    print(f"{'='*70}")

    model_path = MODEL_DIR / model_name
    zip_path = MODEL_DIR / f"{model_name}.zip"

    # Create directories
    model_path.mkdir(parents=True, exist_ok=True)

    # Check if already downloaded
    if model_path.exists() and any(model_path.iterdir()):
        print(f"  Model already exists at {model_path}")
        print(f"  Skipping download...")
        return True

    # Download
    print(f"\n  Downloading from: {info['url']}")
    try:
        urllib.request.urlretrieve(info['url'], zip_path, download_progress)
        print(f"\n  ✅ Download completed!")
    except Exception as e:
        print(f"\n  ❌ Download failed: {e}")
        return False

    # Extract
    print(f"\n  Extracting to: {model_path}")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(model_path)
        print(f"  ✅ Extraction completed!")

        # Clean up zip
        zip_path.unlink()
        print(f"  ✅ Zip file removed!")
    except Exception as e:
        print(f"  ❌ Extraction failed: {e}")
        return False

    # Verify
    print(f"\n  Verifying model files...")
    onnx_files = list(model_path.rglob("*.onnx"))
    json_files = list(model_path.rglob("*.json"))

    if onnx_files:
        print(f"  ✅ Found {len(onnx_files)} .onnx files:")
        for f in onnx_files:
            size_mb = f.stat().st_size / 1024 / 1024
            print(f"     - {f.name} ({size_mb:.2f} MB)")
    else:
        print(f"  ⚠️  No .onnx files found")

    if json_files:
        print(f"  ✅ Found {len(json_files)} .json files:")
        for f in json_files:
            print(f"     - {f.name}")

    print(f"\n  ✅ {model_name} ready!")
    return True

def main():
    print("=" * 70)
    print("INSIGHTFACE All Models Auto Download")
    print("=" * 70)
    print(f"\nTarget: {MODEL_DIR}")
    print(f"Models: {len(MODELS)}")

    # Create directory
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    # Download all models
    success = 0
    for i, (model_name, info) in enumerate(MODELS.items(), 1):
        print(f"\n\n[{i}/{len(MODELS)}] Processing {model_name}...")
        if download_model(model_name, info):
            success += 1
        else:
            print(f"  ⚠️  Failed to download {model_name}")

    # Summary
    print(f"\n\n{'='*70}")
    print("Download Summary")
    print(f"{'='*70}")
    print(f"✅ Success: {success}/{len(MODELS)}")

    if success == len(MODELS):
        print(f"\n🎉 All models downloaded successfully!")
        print(f"\nTotal models downloaded:")
        for item in sorted(MODEL_DIR.iterdir()):
            if item.is_dir():
                onnx_count = len(list(item.rglob("*.onnx")))
                total_size = sum(f.stat().st_size for f in item.rglob("*.onnx")) / 1024 / 1024
                print(f"  📁 {item.name}/ ({onnx_count} files, {total_size:.2f} MB)")

        print(f"\n{'='*70}")
        print("Next steps:")
        print("1. Install dependencies: pip install insightface onnxruntime-gpu")
        print("2. Configure model path in your application")
        print("3. Test with: python -c 'from insightface.app import FaceAnalysis; app=FaceAnalysis(name=\"buffalo_l\"); app.prepare(ctx_id=0)'")
        print(f"{'='*70}")

        return 0
    else:
        print(f"\n⚠️  Some models failed to download")
        print(f"Please check your network connection and try again")
        return 1

if __name__ == "__main__":
    sys.exit(main())
