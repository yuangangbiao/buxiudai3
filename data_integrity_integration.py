# -*- coding: utf-8 -*-
"""
数据完整性校验模块

为主系统提供数据完整性校验能力
基于 mobile_api_ai/modules/data_integrity.py 封装
"""

import os
import hashlib
import logging
import json
from typing import Optional, Union, Callable
from pathlib import Path

logger = logging.getLogger(__name__)


class IntegrityError(Exception):
    """数据完整性校验异常"""
    pass


class ChecksumType:
    """校验和类型"""
    MD5 = "md5"
    SHA1 = "sha1"
    SHA256 = "sha256"
    SHA512 = "sha512"


class DataIntegrity:
    """数据完整性校验器"""

    def __init__(self, default_algorithm: str = ChecksumType.SHA256):
        """
        初始化校验器

        Args:
            default_algorithm: 默认校验算法
        """
        self.default_algorithm = default_algorithm
        self._supported_algorithms = [
            ChecksumType.MD5,
            ChecksumType.SHA1,
            ChecksumType.SHA256,
            ChecksumType.SHA512
        ]

    def compute_checksum(
        self,
        data: Union[str, bytes],
        algorithm: Optional[str] = None
    ) -> str:
        """
        计算数据的校验和

        Args:
            data: 数据（字符串或字节）
            algorithm: 校验算法，默认使用配置的算法

        Returns:
            校验和十六进制字符串
        """
        algorithm = algorithm or self.default_algorithm

        if algorithm not in self._supported_algorithms:
            raise ValueError(f"不支持的校验算法: {algorithm}")

        if isinstance(data, str):
            data = data.encode('utf-8')

        if algorithm == ChecksumType.MD5:
            return hashlib.md5(data).hexdigest()
        elif algorithm == ChecksumType.SHA1:
            return hashlib.sha1(data).hexdigest()
        elif algorithm == ChecksumType.SHA256:
            return hashlib.sha256(data).hexdigest()
        elif algorithm == ChecksumType.SHA512:
            return hashlib.sha512(data).hexdigest()

    def compute_file_checksum(
        self,
        file_path: Union[str, Path],
        algorithm: Optional[str] = None,
        chunk_size: int = 8192
    ) -> str:
        """
        计算文件的校验和

        Args:
            file_path: 文件路径
            algorithm: 校验算法
            chunk_size: 每次读取的块大小

        Returns:
            校验和十六进制字符串
        """
        algorithm = algorithm or self.default_algorithm

        if algorithm not in self._supported_algorithms:
            raise ValueError(f"不支持的校验算法: {algorithm}")

        if algorithm == ChecksumType.MD5:
            hasher = hashlib.md5()
        elif algorithm == ChecksumType.SHA1:
            hasher = hashlib.sha1()
        elif algorithm == ChecksumType.SHA256:
            hasher = hashlib.sha256()
        elif algorithm == ChecksumType.SHA512:
            hasher = hashlib.sha512()

        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        with open(file_path, 'rb') as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)

        return hasher.hexdigest()

    def verify_checksum(
        self,
        data: Union[str, bytes],
        expected_checksum: str,
        algorithm: Optional[str] = None
    ) -> bool:
        """
        验证数据校验和

        Args:
            data: 数据
            expected_checksum: 期望的校验和
            algorithm: 校验算法

        Returns:
            是否匹配
        """
        computed = self.compute_checksum(data, algorithm)
        matches = computed.lower() == expected_checksum.lower()

        if not matches:
            logger.warning(
                f"校验和不匹配: 期望={expected_checksum}, "
                f"实际={computed}"
            )

        return matches

    def verify_file_checksum(
        self,
        file_path: Union[str, Path],
        expected_checksum: str,
        algorithm: Optional[str] = None
    ) -> bool:
        """
        验证文件校验和

        Args:
            file_path: 文件路径
            expected_checksum: 期望的校验和
            algorithm: 校验算法

        Returns:
            是否匹配
        """
        try:
            computed = self.compute_file_checksum(file_path, algorithm)
            matches = computed.lower() == expected_checksum.lower()

            if matches:
                logger.info(f"文件校验通过: {file_path}")
            else:
                logger.error(
                    f"文件校验失败: {file_path}, "
                    f"期望={expected_checksum}, 实际={computed}"
                )

            return matches

        except Exception as e:
            logger.error(f"文件校验异常: {file_path}, {e}")
            return False

    def compute_directory_checksum(
        self,
        directory: Union[str, Path],
        algorithm: Optional[str] = None,
        exclude_patterns: Optional[list] = None
    ) -> str:
        """
        计算目录的校验和（基于所有文件的校验和）

        Args:
            directory: 目录路径
            algorithm: 校验算法
            exclude_patterns: 排除的文件模式列表

        Returns:
            目录校验和
        """
        import fnmatch

        directory = Path(directory)

        if not directory.exists() or not directory.is_dir():
            raise NotADirectoryError(f"目录不存在: {directory}")

        algorithm = algorithm or self.default_algorithm
        exclude_patterns = exclude_patterns or []

        file_checksums = []

        for file_path in sorted(directory.rglob('*')):
            if file_path.is_file():
                relative_path = file_path.relative_to(directory)

                should_exclude = False
                for pattern in exclude_patterns:
                    if fnmatch.fnmatch(str(relative_path), pattern):
                        should_exclude = True
                        break

                if not should_exclude:
                    try:
                        file_checksum = self.compute_file_checksum(
                            file_path, algorithm
                        )
                        file_checksums.append(
                            f"{relative_path}:{file_checksum}"
                        )
                    except Exception as e:
                        logger.warning(f"计算文件校验和失败: {file_path}, {e}")

        combined = '\n'.join(file_checksums).encode('utf-8')
        return self.compute_checksum(combined, algorithm)


class BackupIntegrityChecker:
    """备份完整性检查器"""

    def __init__(self, data_dir: Optional[Union[str, Path]] = None):
        """
        初始化检查器

        Args:
            data_dir: 数据目录路径
        """
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = Path(__file__).parent / 'data'

        self.integrity = DataIntegrity()

    def compute_manifest_checksum(self, manifest: dict) -> str:
        """计算清单文件的校验和"""
        manifest_json = json.dumps(manifest, sort_keys=True, ensure_ascii=False)
        return self.integrity.compute_checksum(manifest_json)

    def verify_manifest(
        self,
        manifest: dict,
        expected_checksum: str
    ) -> bool:
        """验证清单完整性"""
        computed = self.compute_manifest_checksum(manifest)
        return computed.lower() == expected_checksum.lower()

    def scan_data_directory(
        self,
        exclude_patterns: Optional[list] = None
    ) -> dict:
        """
        扫描数据目录生成清单

        Args:
            exclude_patterns: 排除的文件模式

        Returns:
            清单字典
        """
        manifest = {
            'scan_time': self._get_timestamp(),
            'files': []
        }

        if not self.data_dir.exists():
            return manifest

        exclude_patterns = exclude_patterns or ['*.tmp', '*.log', '__pycache__']

        for file_path in self.data_dir.rglob('*'):
            if file_path.is_file():
                relative_path = file_path.relative_to(self.data_dir)

                should_exclude = False
                for pattern in exclude_patterns:
                    if pattern in str(relative_path):
                        should_exclude = True
                        break

                if not should_exclude:
                    try:
                        checksum = self.integrity.compute_file_checksum(file_path)
                        manifest['files'].append({
                            'path': str(relative_path),
                            'size': file_path.stat().st_size,
                            'checksum': checksum
                        })
                    except Exception as e:
                        logger.warning(f"扫描文件失败: {file_path}, {e}")

        manifest['file_count'] = len(manifest['files'])
        manifest['total_size'] = sum(f['size'] for f in manifest['files'])
        manifest['checksum'] = self.compute_manifest_checksum(manifest)

        return manifest

    def verify_backup_set(
        self,
        backup_dir: Union[str, Path],
        manifest: dict
    ) -> tuple:
        """
        验证备份集完整性

        Args:
            backup_dir: 备份目录
            manifest: 清单文件

        Returns:
            (是否全部通过, 错误列表)
        """
        backup_dir = Path(backup_dir)
        errors = []

        if not self.verify_manifest(manifest, manifest.get('checksum', '')):
            errors.append("清单校验失败")

        for file_entry in manifest.get('files', []):
            file_path = backup_dir / file_entry['path']

            if not file_path.exists():
                errors.append(f"文件缺失: {file_entry['path']}")
                continue

            if not self.integrity.verify_file_checksum(
                file_path,
                file_entry['checksum']
            ):
                errors.append(f"文件校验失败: {file_entry['path']}")

        return len(errors) == 0, errors

    def _get_timestamp(self) -> str:
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


_data_integrity_instance = None


def get_data_integrity(
    default_algorithm: str = ChecksumType.SHA256
) -> DataIntegrity:
    """获取数据完整性校验器单例"""
    global _data_integrity_instance
    if _data_integrity_instance is None:
        _data_integrity_instance = DataIntegrity(default_algorithm)
    return _data_integrity_instance


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    integrity = get_data_integrity()
    checker = BackupIntegrityChecker()

    print("=" * 60)
    print("数据完整性校验模块测试")
    print("=" * 60)

    print("\n--- 字符串校验和 ---")
    test_data = "Hello, World!"
    checksum = integrity.compute_checksum(test_data)
    print(f"原文: {test_data}")
    print(f"SHA256: {checksum}")
    print(f"验证: {integrity.verify_checksum(test_data, checksum)}")

    print("\n--- 文件校验和测试 ---")
    test_file = Path(__file__)
    file_checksum = integrity.compute_file_checksum(test_file)
    print(f"文件: {test_file.name}")
    print(f"校验和: {file_checksum}")
    print(f"验证: {integrity.verify_file_checksum(test_file, file_checksum)}")

    print("\n--- 目录扫描 ---")
    manifest = checker.scan_data_directory()
    print(f"文件数: {manifest['file_count']}")
    print(f"总大小: {manifest['total_size']} 字节")
    print(f"清单校验和: {manifest['checksum']}")

    print("\n" + "=" * 60)
