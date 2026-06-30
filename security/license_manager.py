# -*- coding: utf-8 -*-
"""
许可证管理器
软件加密锁定核心管理模块
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class LicenseManager:
    """
    许可证管理器
    负责许可证的验证、激活和管理
    """

    ACTIVATION_FILE = ".activation_status"
    LICENSE_KEY_PREFIX = "YGB-"
    VALID_CHARS = "0123456789ABCDEFGHJKLMNPQRSTUVWXYZ"

    def __init__(self):
        self.fingerprint = None
        self.binding = None
        self.activation_status = None

    def _get_status_path(self) -> str:
        """获取状态文件路径（使用与LicenseBinding相同的存储策略）"""
        if getattr(sys, 'frozen', False):
            app_dir = os.path.dirname(sys.executable)
        else:
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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
                return os.path.join(d, self.ACTIVATION_FILE)
            except Exception:
                continue

        return os.path.join(app_dir, self.ACTIVATION_FILE)

    def check_activation(self) -> dict:
        """
        检查激活状态

        Returns:
            状态字典
        """
        try:
            from .machine_fingerprint import MachineFingerprint
            from .license_binding import LicenseBinding
        except ImportError:
            from security.machine_fingerprint import MachineFingerprint
            from security.license_binding import LicenseBinding

        self.fingerprint = MachineFingerprint.generate()

        binding = LicenseBinding.load_binding()

        status = {
            "is_activated": False,
            "fingerprint": self.fingerprint,
            "fingerprint_short": self.fingerprint[:8].upper(),
            "bound_license_key": None,
            "bound_customer": None,
            "bound_at": None,
            "message": "未激活",
        }

        if binding:
            stored_fp = binding.get("fingerprint", "")

            if stored_fp == self.fingerprint:
                status["is_activated"] = True
                status["bound_license_key"] = binding.get("license_key", "")[:16] + "****"
                status["bound_customer"] = binding.get("customer_name", "")
                status["bound_at"] = binding.get("bound_at", "")
                status["message"] = "已激活"
            else:
                status["message"] = "机器指纹不匹配（可能已被复制到其他电脑）"

        self.activation_status = status
        return status

    def activate(self, license_key: str, customer_name: str = "") -> dict:
        """
        激活许可证

        Args:
            license_key: 许可证密钥
            customer_name: 客户名称

        Returns:
            激活结果
        """
        try:
            from .machine_fingerprint import MachineFingerprint
            from .license_binding import LicenseBinding
        except ImportError:
            from security.machine_fingerprint import MachineFingerprint
            from security.license_binding import LicenseBinding

        result = {
            "success": False,
            "message": "",
        }

        if not self._validate_license_key_format(license_key):
            result["message"] = "许可证密钥格式无效，应为: YGB-XXXX-XXXX-XXXX-XXXX-C"
            return result

        if not self._verify_checksum(license_key):
            result["message"] = "许可证密钥校验失败，可能已损坏"
            return result

        fingerprint = MachineFingerprint.generate()

        if LicenseBinding.save_binding(fingerprint, license_key, customer_name):
            self.fingerprint = fingerprint
            result["success"] = True
            result["message"] = "激活成功"
            result["fingerprint"] = fingerprint
            result["fingerprint_short"] = fingerprint[:8].upper()

            logger.info(f"[LICENSE] 许可证激活成功: {license_key[:16]}****")
        else:
            result["message"] = "激活失败，请联系技术支持"

        return result

    def deactivate(self) -> dict:
        """
        解除激活（用于换电脑等情况）

        Returns:
            解除结果
        """
        try:
            from .license_binding import LicenseBinding
        except ImportError:
            from security.license_binding import LicenseBinding

        result = {
            "success": False,
            "message": "",
        }

        if LicenseBinding.clear_binding():
            result["success"] = True
            result["message"] = "已解除激活，可以重新激活"
            logger.info("[LICENSE] 解除激活成功")
        else:
            result["message"] = "解除激活失败"

        return result

    def verify(self) -> bool:
        """
        验证许可证是否有效（用于启动时检查）

        Returns:
            是否有效
        """
        status = self.check_activation()
        return status.get("is_activated", False)

    def get_activation_info(self) -> dict:
        """
        获取激活信息摘要

        Returns:
            激活信息
        """
        if not self.activation_status:
            self.check_activation()

        return {
            "已激活": "是" if self.activation_status.get("is_activated") else "否",
            "机器指纹": self.activation_status.get("fingerprint_short", ""),
            "许可证": self.activation_status.get("bound_license_key", "无"),
            "客户": self.activation_status.get("bound_customer", "无"),
            "绑定时间": self.activation_status.get("bound_at", "无"),
            "状态": self.activation_status.get("message", ""),
        }

    @staticmethod
    def _validate_license_key_format(key: str) -> bool:
        """
        验证许可证密钥格式
        格式: YGB-XXXX-XXXX-XXXX-XXXX-C (6段带校验位)
        """
        if not key:
            return False

        key = key.strip().upper()

        if not key.startswith(LicenseManager.LICENSE_KEY_PREFIX):
            return False

        parts = key.split("-")
        if len(parts) != 6:
            return False

        for i, part in enumerate(parts):
            if i == 0:
                if part != "YGB":
                    return False
                continue
            if i == 5:
                if len(part) != 1:
                    return False
                if part not in LicenseManager.VALID_CHARS:
                    return False
                continue
            if len(part) != 4:
                return False
            if not all(c in LicenseManager.VALID_CHARS for c in part):
                return False

        return True

    @staticmethod
    def _calculate_checksum(key_base: str) -> str:
        """计算校验位"""
        total = sum(ord(c) * (i + 1) for i, c in enumerate(key_base))
        return LicenseManager.VALID_CHARS[total % len(LicenseManager.VALID_CHARS)]

    @staticmethod
    def _verify_checksum(key: str) -> bool:
        """验证密钥校验位"""
        parts = key.strip().upper().split("-")
        if len(parts) != 6:
            return False
        key_base = f"{parts[1]}{parts[2]}{parts[3]}{parts[4]}"
        expected = LicenseManager._calculate_checksum(key_base)
        return parts[5] == expected

    @staticmethod
    def generate_trial_key() -> str:
        """
        生成试用密钥（用于测试）
        注意: 此方法已废弃，试用密钥现由生成器统一管理
        """
        import secrets
        key_parts = []
        for _ in range(4):
            part = ""
            for _ in range(4):
                part += secrets.choice(LicenseManager.VALID_CHARS)
            key_parts.append(part)
        key_base_str = "".join(key_parts)
        checksum = LicenseManager._calculate_checksum(key_base_str)
        return f"YGB-{key_parts[0]}-{key_parts[1]}-{key_parts[2]}-{key_parts[3]}-{checksum}"

    @staticmethod
    def print_activation_guide():
        """打印激活指南"""
        guide = """
╔════════════════════════════════════════════════════════════════╗
║                      软件激活指南                               ║
╠════════════════════════════════════════════════════════════════╣
║                                                                ║
║  【许可证密钥格式】                                             ║
║    YGB-XXXX-XXXX-XXXX-XXXX-C                                  ║
║    示例: YGB-A1B2-C3D4-E5F6-G7H8-J                           ║
║                                                                ║
║  【激活步骤】                                                   ║
║    1. 联系销售人员获取许可证密钥                                 ║
║    2. 打开软件激活界面                                           ║
║    3. 输入许可证密钥                                             ║
║    4. 点击激活按钮                                               ║
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
    print("=" * 60)
    print("许可证管理器测试")
    print("=" * 60)

    mgr = LicenseManager()

    print("\n--- 检查激活状态 ---")
    status = mgr.check_activation()
    for k, v in status.items():
        print(f"  {k}: {v}")

    print("\n--- 激活信息摘要 ---")
    info = mgr.get_activation_info()
    for k, v in info.items():
        print(f"  {k}: {v}")

    print("\n--- 许可证格式验证 ---")
    test_keys = [
        "SB-A1B2-C3D4-E5F6-G7H8",
        "SB-1234-5678-9ABC-DEF0",
        "INVALID-KEY",
        "sb-a1b2-c3d4-e5f6-g7h8",
    ]
    for key in test_keys:
        result = LicenseManager._validate_license_key_format(key)
        print(f"  {key}: {'✓ 有效' if result else '✗ 无效'}")

    print("\n--- 试用密钥生成 ---")
    trial_key = LicenseManager.generate_trial_key()
    print(f"  生成的试用密钥: {trial_key}")

    print("\n--- 激活指南 ---")
    LicenseManager.print_activation_guide()

    print("\n--- 测试激活（仅演示）---")
    demo_result = mgr.activate(
        license_key="SB-A1B2-C3D4-E5F6-G7H8",
        customer_name="测试公司"
    )
    print(f"  激活结果: {demo_result}")

    print("\n--- 再次检查状态 ---")
    status = mgr.check_activation()
    print(f"  已激活: {status.get('is_activated')}")
    print(f"  状态消息: {status.get('message')}")

    print("=" * 60)