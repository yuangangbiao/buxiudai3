# -*- coding: utf-8 -*-
"""
独立许可证管理器 - 独立运行版
软件加密锁定核心管理模块
"""

import os
import sys
import json
import hashlib
import logging
from datetime import datetime
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BINDING_FILE_NAME = ".license_binding"
SALT_FILE_NAME = ".license_salt"
LICENSE_KEY_PREFIX = "YGB-"
VALID_CHARS = "0123456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def _get_app_dir():
    """获取应用目录"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _get_storage_dir():
    """获取存储目录"""
    app_dir = _get_app_dir()

    dirs_to_try = [
        app_dir,
        os.path.join(os.environ.get("APPDATA", ""), "SteelBeltLicense"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "SteelBeltLicense"),
    ]

    for d in dirs_to_try:
        try:
            os.makedirs(d, exist_ok=True)
            test_file = os.path.join(d, ".write_test")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            return d
        except Exception:
            continue

    return app_dir


def _get_binding_path():
    """获取绑定文件路径"""
    return os.path.join(_get_storage_dir(), BINDING_FILE_NAME)


def _get_salt_path():
    """获取盐值文件路径"""
    return os.path.join(_get_storage_dir(), SALT_FILE_NAME)


def _generate_salt():
    """生成随机盐值"""
    import secrets
    return secrets.token_hex(16)


def _load_salt():
    """加载或生成盐值"""
    salt_path = _get_salt_path()

    if os.path.exists(salt_path):
        try:
            with open(salt_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass

    salt = _generate_salt()
    try:
        with open(salt_path, "w", encoding="utf-8") as f:
            f.write(salt)
    except Exception:
        pass

    return salt


def _encrypt_data(data: str, salt: str) -> str:
    """简单加密存储数据"""
    key = hashlib.sha256((data + salt).encode()).hexdigest()
    return key[:32] + data + key[32:]


def _decrypt_data(encrypted: str, salt: str) -> Optional[str]:
    """解密数据"""
    if len(encrypted) < 65:
        return None
    key = hashlib.sha256((encrypted[32:-32] + salt).encode()).hexdigest()
    if encrypted[:32] != key[:32] or encrypted[-32:] != key[32:]:
        return None
    return encrypted[32:-32]


def _get_cpu_id():
    """获取CPU ID"""
    try:
        import subprocess
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


def _get_disk_serial():
    """获取系统盘序列号"""
    try:
        import subprocess
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


def _get_motherboard_serial():
    """获取主板序列号"""
    try:
        import subprocess
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


def _get_bios_serial():
    """获取BIOS序列号"""
    try:
        import subprocess
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
    生成机器指纹（使用缓存加速）
    """
    try:
        from .machine_fingerprint import MachineFingerprint
        return MachineFingerprint.generate(use_cache=True)
    except ImportError:
        from security.machine_fingerprint import MachineFingerprint
        return MachineFingerprint.generate(use_cache=True)


def save_binding(fingerprint: str, license_key: str, customer_name: str = "") -> bool:
    """
    保存许可证绑定
    """
    try:
        salt = _load_salt()

        binding_data = {
            "fingerprint": fingerprint,
            "license_key": license_key,
            "customer_name": customer_name,
            "bound_at": datetime.now().isoformat(),
        }

        json_data = json.dumps(binding_data, ensure_ascii=False)
        encrypted = _encrypt_data(json_data, salt)

        binding_path = _get_binding_path()
        with open(binding_path, "w", encoding="utf-8") as f:
            f.write(encrypted)

        logger.info(f"[LICENSE] 绑定信息已保存")
        return True

    except Exception as e:
        logger.error(f"[LICENSE] 保存绑定信息失败: {e}")
        return False


def load_binding() -> Optional[dict]:
    """
    加载许可证绑定
    """
    try:
        binding_path = _get_binding_path()

        if not os.path.exists(binding_path):
            return None

        salt = _load_salt()

        with open(binding_path, "r", encoding="utf-8") as f:
            encrypted = f.read()

        json_data = _decrypt_data(encrypted, salt)
        if not json_data:
            logger.warning("[LICENSE] 绑定信息解密失败，可能被篡改")
            return None

        binding_data = json.loads(json_data)
        return binding_data

    except Exception as e:
        logger.error(f"[LICENSE] 加载绑定信息失败: {e}")
        return None


def verify_binding(fingerprint: str) -> bool:
    """
    验证机器指纹是否与绑定信息匹配
    """
    binding = load_binding()

    if not binding:
        return False

    stored_fingerprint = binding.get("fingerprint", "")

    if stored_fingerprint == fingerprint:
        logger.info("[LICENSE] 机器指纹验证通过")
        return True
    else:
        logger.warning(f"[LICENSE] 机器指纹不匹配")
        return False


def clear_binding() -> bool:
    """
    清除绑定信息
    """
    try:
        binding_path = _get_binding_path()

        if os.path.exists(binding_path):
            os.remove(binding_path)
            logger.info("[LICENSE] 绑定信息已清除")

        return True

    except Exception as e:
        logger.error(f"[LICENSE] 清除绑定信息失败: {e}")
        return False


def validate_license_key_format(key: str) -> bool:
    """
    验证许可证密钥格式
    格式: YGB-XXXX-XXXX-XXXX-XXXX-C (6段带校验位)
    """
    if not key:
        return False

    key = key.strip().upper()

    if not key.startswith(LICENSE_KEY_PREFIX):
        return False

    parts = key.split("-")
    if len(parts) != 6:
        return False

    # 检查第一段
    if parts[0] != "YGB":
        return False

    # 检查中间4段必须是4个字符的字母数字
    for i in range(1, 5):
        if len(parts[i]) != 4:
            return False
        if not all(c in VALID_CHARS for c in parts[i]):
            return False

    # 检查校验位
    if len(parts[5]) != 1:
        return False
    if parts[5] not in VALID_CHARS:
        return False

    return True


def calculate_checksum(key_base: str) -> str:
    """计算校验位"""
    total = sum(ord(c) * (i + 1) for i, c in enumerate(key_base))
    return VALID_CHARS[total % len(VALID_CHARS)]


def verify_checksum(key: str) -> bool:
    """验证密钥校验位"""
    parts = key.strip().upper().split("-")
    if len(parts) != 6:
        return False
    key_base = f"{parts[1]}{parts[2]}{parts[3]}{parts[4]}"
    expected = calculate_checksum(key_base)
    return parts[5] == expected


def check_activation():
    """
    检查激活状态
    """
    fingerprint = generate_fingerprint()

    binding = load_binding()

    status = {
        "is_activated": False,
        "fingerprint": fingerprint,
        "fingerprint_short": fingerprint[:8].upper(),
        "bound_license_key": None,
        "bound_customer": None,
        "bound_at": None,
        "message": "未激活",
    }

    if binding:
        stored_fp = binding.get("fingerprint", "")

        if stored_fp == fingerprint:
            status["is_activated"] = True
            status["bound_license_key"] = binding.get("license_key", "")[:16] + "****"
            status["bound_customer"] = binding.get("customer_name", "")
            status["bound_at"] = binding.get("bound_at", "")
            status["message"] = "已激活"
        else:
            status["message"] = "机器指纹不匹配（可能已被复制到其他电脑）"

    return status


def activate(license_key: str, customer_name: str = "") -> dict:
    """
    激活许可证
    """
    result = {
        "success": False,
        "message": "",
    }

    if not validate_license_key_format(license_key):
        result["message"] = "许可证密钥格式无效，应为: YGB-XXXX-XXXX-XXXX-XXXX-C"
        return result

    if not verify_checksum(license_key):
        result["message"] = "许可证密钥校验失败，可能已损坏"
        return result

    fingerprint = generate_fingerprint()

    if save_binding(fingerprint, license_key, customer_name):
        result["success"] = True
        result["message"] = "激活成功"
        result["fingerprint"] = fingerprint
        result["fingerprint_short"] = fingerprint[:8].upper()

        logger.info(f"[LICENSE] 许可证激活成功")
    else:
        result["message"] = "激活失败，请联系技术支持"

    return result


def deactivate() -> dict:
    """
    解除激活
    """
    result = {
        "success": False,
        "message": "",
    }

    if clear_binding():
        result["success"] = True
        result["message"] = "已解除激活，可以重新激活"
        logger.info("[LICENSE] 解除激活成功")
    else:
        result["message"] = "解除激活失败"

    return result


def print_activation_guide():
    """打印激活指南"""
    guide = """
╔════════════════════════════════════════════════════════════════╗
║                      软件激活指南                               ║
╠════════════════════════════════════════════════════════════════╣
║                                                                ║
║  【许可证密钥格式】                                             ║
║    SB-XXXX-XXXX-XXXX-XXXX                                      ║
║    示例: SB-A1B2-C3D4-E5F6-G7H8                               ║
║                                                                ║
║  【激活步骤】                                                   ║
║    1. 联系销售人员获取许可证密钥                                 ║
║    2. 在下方输入许可证密钥                                       ║
║    3. 系统将自动完成激活                                         ║
║                                                                ║
║  【注意事项】                                                   ║
║    - 每个许可证只能绑定一台电脑                                  ║
║    - 更换电脑需要先解除激活                                       ║
║    - 激活失败请联系技术支持                                       ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
    """
    print(guide)


if __name__ == "__main__":
    import socket

    print("=" * 60)
    print("       不锈钢网带跟单系统 - 许可证管理工具")
    print("=" * 60)

    # 显示激活状态
    print("\n--- 当前激活状态 ---")
    status = check_activation()
    print(f"  激活状态: {status['message']}")
    print(f"  机器指纹: {status['fingerprint_short']}")

    if status['is_activated']:
        print(f"  许可证: {status['bound_license_key']}")
        print(f"  客户: {status['bound_customer']}")
        print(f"  绑定时间: {status['bound_at']}")

        print("\n--- 选择操作 ---")
        print("  1. 解除激活（换电脑用）")
        print("  2. 查看机器指纹")
        print("  3. 退出")

        choice = input("\n请选择 (1-3): ").strip()

        if choice == "1":
            confirm = input("确认解除激活? (y/n): ").strip().lower()
            if confirm == 'y':
                result = deactivate()
                print(f"  结果: {result['message']}")
        elif choice == "2":
            print(f"\n  完整指纹: {status['fingerprint']}")
        else:
            print("\n退出")

    else:
        print("\n--- 激活操作 ---")
        print_activation_guide()

        print(f"\n  您的机器指纹: {status['fingerprint_short']}")
        print(f"  (完整指纹: {status['fingerprint']})")

        print("\n  请将以上指纹提供给销售人员获取激活密钥")

        license_key = input("\n请输入许可证密钥 (SB-XXXX-XXXX-XXXX-XXXX): ").strip()
        customer_name = input("请输入客户名称 (可选): ").strip()

        if license_key:
            result = activate(license_key, customer_name)
            print(f"\n  激活结果: {result['message']}")

            if result['success']:
                print(f"  机器指纹: {result['fingerprint_short']}")

    print("\n" + "=" * 60)
    input("\n按回车键退出...")