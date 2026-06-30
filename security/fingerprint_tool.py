# -*- coding: utf-8 -*-
"""
机器指纹生成模块 - 独立运行版
用于生成唯一标识一台电脑的指纹
"""

import hashlib
import platform
import socket
import getpass
import subprocess
import uuid
import os


def get_cpu_id() -> str:
    """获取CPU ID"""
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["wmic", "cpu", "get", "ProcessorId"],
                capture_output=True, text=True, timeout=5
            )
            lines = result.stdout.strip().split("\n")
            if len(lines) >= 2:
                cpu_id = lines[-1].strip()
                if cpu_id:
                    return cpu_id
    except Exception:
        pass
    return "CPU_UNKNOWN"


def get_disk_serial() -> str:
    """获取系统盘序列号"""
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["wmic", "diskdrive", "get", "SerialNumber"],
                capture_output=True, text=True, timeout=5
            )
            lines = result.stdout.strip().split("\n")
            if len(lines) >= 2:
                serial = lines[-1].strip()
                if serial:
                    return serial
    except Exception:
        pass
    return "DISK_UNKNOWN"


def get_motherboard_serial() -> str:
    """获取主板序列号"""
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["wmic", "baseboard", "get", "SerialNumber"],
                capture_output=True, text=True, timeout=5
            )
            lines = result.stdout.strip().split("\n")
            if len(lines) >= 2:
                serial = lines[-1].strip()
                if serial and serial != "SerialNumber":
                    return serial
    except Exception:
        pass
    return "MB_UNKNOWN"


def get_bios_serial() -> str:
    """获取BIOS序列号"""
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["wmic", "bios", "get", "SerialNumber"],
                capture_output=True, text=True, timeout=5
            )
            lines = result.stdout.strip().split("\n")
            if len(lines) >= 2:
                serial = lines[-1].strip()
                if serial and serial != "SerialNumber":
                    return serial
    except Exception:
        pass
    return "BIOS_UNKNOWN"


def generate_fingerprint() -> str:
    """
    生成机器指纹
    组合多种硬件特征，通过SHA256生成唯一标识
    """
    components = [
        get_cpu_id(),
        get_disk_serial(),
        get_motherboard_serial(),
        get_bios_serial(),
    ]

    combined = "|".join(components)
    fingerprint = hashlib.sha256(combined.encode('utf-8')).hexdigest()

    return fingerprint


def generate_short_fingerprint() -> str:
    """
    生成短格式指纹（8位）
    用于显示和识别
    """
    full = generate_fingerprint()
    return full[:8].upper()


def get_all_hardware_info() -> dict:
    """
    获取完整的硬件信息
    用于调试和诊断
    """
    return {
        "fingerprint": generate_fingerprint(),
        "fingerprint_short": generate_short_fingerprint(),
        "cpu_id": get_cpu_id(),
        "disk_serial": get_disk_serial(),
        "motherboard_serial": get_motherboard_serial(),
        "bios_serial": get_bios_serial(),
        "machine_name": socket.gethostname(),
    }


def save_fingerprint_to_file():
    """保存指纹到本地文件"""
    fp = generate_fingerprint()
    fp_short = generate_short_fingerprint()

    save_path = os.path.join(os.path.dirname(__file__), "my_fingerprint.txt")
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(f"完整指纹:\n{fp}\n\n")
        f.write(f"短指纹:\n{fp_short}\n\n")
        f.write(f"生成时间:\n{datetime.now().isoformat()}\n\n")
        f.write("\n硬件信息:\n")
        info = get_all_hardware_info()
        for k, v in info.items():
            f.write(f"  {k}: {v}\n")

    print(f"指纹已保存到: {save_path}")
    return fp, fp_short


if __name__ == "__main__":
    from datetime import datetime

    print("=" * 60)
    print("机器指纹信息")
    print("=" * 60)

    info = get_all_hardware_info()

    for key, value in info.items():
        print(f"{key}: {value}")

    print("=" * 60)
    print(f"完整指纹: {info['fingerprint']}")
    print(f"短指纹: {info['fingerprint_short']}")
    print("=" * 60)

    # 询问是否保存
    save = input("\n是否保存指纹到文件? (y/n): ").strip().lower()
    if save == 'y':
        save_fingerprint_to_file()
        print("已保存!")

    input("\n按回车键退出...")