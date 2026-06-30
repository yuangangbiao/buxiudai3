# -*- coding: utf-8 -*-
"""
许可证绑定存储模块
管理机器指纹与许可证的绑定关系
"""

import os
import sys
import json
import hashlib
import logging
import socket
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class LicenseBinding:
    """
    许可证绑定管理器
    将机器指纹与许可证信息绑定存储
    """

    BINDING_FILE_NAME = ".license_binding"
    SALT_FILE_NAME = ".license_salt"

    @classmethod
    def _get_storage_dir(cls) -> str:
        """获取存储目录"""
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
                return d
            except Exception:
                continue

        return app_dir

    @classmethod
    def _get_binding_path(cls) -> str:
        """获取绑定文件路径"""
        return os.path.join(cls._get_storage_dir(), cls.BINDING_FILE_NAME)

    @classmethod
    def _get_salt_path(cls) -> str:
        """获取盐值文件路径"""
        return os.path.join(cls._get_storage_dir(), cls.SALT_FILE_NAME)

    @classmethod
    def _generate_salt(cls) -> str:
        """生成随机盐值"""
        import secrets
        return secrets.token_hex(16)

    @classmethod
    def _load_salt(cls) -> str:
        """加载或生成盐值"""
        salt_path = cls._get_salt_path()

        if os.path.exists(salt_path):
            try:
                with open(salt_path, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except Exception:
                pass

        salt = cls._generate_salt()
        try:
            with open(salt_path, "w", encoding="utf-8") as f:
                f.write(salt)
        except Exception:
            pass

        return salt

    @classmethod
    def _encrypt_data(cls, data: str, salt: str) -> str:
        """简单加密存储数据"""
        key = hashlib.sha256((data + salt).encode()).hexdigest()
        return key[:32] + data + key[32:]

    @classmethod
    def _decrypt_data(cls, encrypted: str, salt: str) -> Optional[str]:
        """解密数据"""
        if len(encrypted) < 65:
            return None
        key = hashlib.sha256((encrypted[32:-32] + salt).encode()).hexdigest()
        if encrypted[:32] != key[:32] or encrypted[-32:] != key[32:]:
            return None
        return encrypted[32:-32]

    @classmethod
    def save_binding(cls, fingerprint: str, license_key: str, customer_name: str = "") -> bool:
        """
        保存许可证绑定

        Args:
            fingerprint: 机器指纹
            license_key: 许可证密钥
            customer_name: 客户名称

        Returns:
            是否保存成功
        """
        try:
            salt = cls._load_salt()

            binding_data = {
                "fingerprint": fingerprint,
                "license_key": license_key,
                "customer_name": customer_name,
                "bound_at": datetime.now().isoformat(),
                "machine_name": socket.gethostname() if hasattr(socket, 'gethostname') else "UNKNOWN",
            }

            json_data = json.dumps(binding_data, ensure_ascii=False)
            encrypted = cls._encrypt_data(json_data, salt)

            binding_path = cls._get_binding_path()
            with open(binding_path, "w", encoding="utf-8") as f:
                f.write(encrypted)

            logger.info(f"[LICENSE] 绑定信息已保存，机器指纹: {fingerprint[:8]}...")
            return True

        except Exception as e:
            logger.error(f"[LICENSE] 保存绑定信息失败: {e}")
            return False

    @classmethod
    def load_binding(cls) -> Optional[dict]:
        """
        加载许可证绑定

        Returns:
            绑定信息字典，如果不存在则返回None
        """
        try:
            binding_path = cls._get_binding_path()

            if not os.path.exists(binding_path):
                return None

            salt = cls._load_salt()

            with open(binding_path, "r", encoding="utf-8") as f:
                encrypted = f.read()

            json_data = cls._decrypt_data(encrypted, salt)
            if not json_data:
                logger.warning("[LICENSE] 绑定信息解密失败，可能被篡改")
                return None

            binding_data = json.loads(json_data)
            return binding_data

        except Exception as e:
            logger.error(f"[LICENSE] 加载绑定信息失败: {e}")
            return None

    @classmethod
    def verify_binding(cls, fingerprint: str) -> bool:
        """
        验证机器指纹是否与绑定信息匹配

        Args:
            fingerprint: 当前机器指纹

        Returns:
            是否匹配
        """
        binding = cls.load_binding()

        if not binding:
            return False

        stored_fingerprint = binding.get("fingerprint", "")

        if stored_fingerprint == fingerprint:
            logger.info("[LICENSE] 机器指纹验证通过")
            return True
        else:
            logger.warning(f"[LICENSE] 机器指纹不匹配: 存储={stored_fingerprint[:8]}..., 当前={fingerprint[:8]}...")
            return False

    @classmethod
    def clear_binding(cls) -> bool:
        """
        清除绑定信息（用于重新激活）

        Returns:
            是否清除成功
        """
        try:
            binding_path = cls._get_binding_path()

            if os.path.exists(binding_path):
                os.remove(binding_path)
                logger.info("[LICENSE] 绑定信息已清除")

            return True

        except Exception as e:
            logger.error(f"[LICENSE] 清除绑定信息失败: {e}")
            return False


if __name__ == "__main__":
    import socket

    print("=" * 60)
    print("许可证绑定测试")
    print("=" * 60)

    from machine_fingerprint import MachineFingerprint

    fp = MachineFingerprint.generate()
    print(f"机器指纹: {fp}")
    print(f"短指纹: {fp[:8].upper()}")

    print("\n--- 保存绑定 ---")
    result = LicenseBinding.save_binding(
        fingerprint=fp,
        license_key="SB-DEMO-0001-0002-0003",
        customer_name="测试客户"
    )
    print(f"保存结果: {result}")

    print("\n--- 加载绑定 ---")
    binding = LicenseBinding.load_binding()
    print(f"绑定信息: {binding}")

    print("\n--- 验证绑定 ---")
    verify_result = LicenseBinding.verify_binding(fp)
    print(f"验证结果: {verify_result}")

    print("=" * 60)