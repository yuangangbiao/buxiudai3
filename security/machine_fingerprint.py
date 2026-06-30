# -*- coding: utf-8 -*-
"""
机器指纹生成模块
用于生成唯一标识一台电脑的指纹
支持缓存以加快启动速度
"""

import hashlib
import platform
import socket
import getpass
import subprocess
import uuid
import os
import json


class MachineFingerprint:
    CACHE_FILE_NAME = ".fingerprint_cache"

    @staticmethod
    def _get_cache_path() -> str:
        if getattr(sys, 'frozen', False):
            app_dir = os.path.dirname(sys.executable)
        else:
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(app_dir, MachineFingerprint.CACHE_FILE_NAME)

    @classmethod
    def _load_cache(cls) -> dict:
        cache_path = cls._get_cache_path()
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    @classmethod
    def _save_cache(cls, data: dict) -> bool:
        cache_path = cls._get_cache_path()
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    @staticmethod
    def get_cpu_id(use_cache: bool = True) -> str:
        if use_cache:
            cache = MachineFingerprint._load_cache()
            if cache and 'cpu_id' in cache:
                return cache['cpu_id']
        cpu_id = MachineFingerprint._get_cpu_id_uncached()
        return cpu_id

    @staticmethod
    def get_disk_serial(use_cache: bool = True) -> str:
        if use_cache:
            cache = MachineFingerprint._load_cache()
            if cache and 'disk_serial' in cache:
                return cache['disk_serial']
        disk_serial = MachineFingerprint._get_disk_serial_uncached()
        return disk_serial

    @staticmethod
    def get_motherboard_serial(use_cache: bool = True) -> str:
        if use_cache:
            cache = MachineFingerprint._load_cache()
            if cache and 'motherboard_serial' in cache:
                return cache['motherboard_serial']
        mb_serial = MachineFingerprint._get_motherboard_serial_uncached()
        return mb_serial

    @staticmethod
    def get_bios_serial(use_cache: bool = True) -> str:
        if use_cache:
            cache = MachineFingerprint._load_cache()
            if cache and 'bios_serial' in cache:
                return cache['bios_serial']
        bios_serial = MachineFingerprint._get_bios_serial_uncached()
        return bios_serial

    @staticmethod
    def _get_cpu_id_uncached() -> str:
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

    @staticmethod
    def _get_disk_serial_uncached() -> str:
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

    @staticmethod
    def _get_motherboard_serial_uncached() -> str:
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

    @staticmethod
    def _get_bios_serial_uncached() -> str:
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

    @staticmethod
    def get_mac_address() -> str:
        try:
            mac = uuid.uuid1().hex[-12:]
            return mac
        except Exception:
            pass
        return "MAC_UNKNOWN"

    @staticmethod
    def get_machine_name() -> str:
        try:
            return socket.gethostname()
        except Exception:
            return "HOST_UNKNOWN"

    @classmethod
    def generate(cls, use_cache: bool = True) -> str:
        components = [
            cls.get_cpu_id(use_cache),
            cls.get_disk_serial(use_cache),
            cls.get_motherboard_serial(use_cache),
            cls.get_bios_serial(use_cache),
        ]

        combined = "|".join(components)
        fingerprint = hashlib.sha256(combined.encode('utf-8')).hexdigest()

        if use_cache:
            cache_data = {
                "cpu_id": components[0],
                "disk_serial": components[1],
                "motherboard_serial": components[2],
                "bios_serial": components[3],
                "fingerprint": fingerprint,
            }
            cls._save_cache(cache_data)

        return fingerprint

    @classmethod
    def generate_short(cls, use_cache: bool = True) -> str:
        full = cls.generate(use_cache)
        return full[:8].upper()

    @classmethod
    def get_info(cls) -> dict:
        return {
            "fingerprint": cls.generate(use_cache=True),
            "fingerprint_short": cls.generate_short(use_cache=True),
            "cpu_id": cls.get_cpu_id(use_cache=True),
            "disk_serial": cls.get_disk_serial(use_cache=True),
            "motherboard_serial": cls.get_motherboard_serial(use_cache=True),
            "bios_serial": cls.get_bios_serial(use_cache=True),
            "machine_name": cls.get_machine_name(),
        }

    @classmethod
    def clear_cache(cls) -> bool:
        cache_path = cls._get_cache_path()
        if os.path.exists(cache_path):
            try:
                os.remove(cache_path)
                return True
            except Exception:
                return False
        return True


import sys

if __name__ == "__main__":
    print("=" * 60)
    print("机器指纹信息")
    print("=" * 60)

    info = MachineFingerprint.get_info()

    for key, value in info.items():
        print(f"{key}: {value}")

    print("=" * 60)
    print(f"完整指纹: {info['fingerprint']}")
    print(f"短指纹: {info['fingerprint_short']}")
    print("=" * 60)
