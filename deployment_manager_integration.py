# -*- coding: utf-8 -*-
"""
部署管理器主系统集成模块

为主系统提供配置版本管理、自动备份回滚能力
基于 mobile_api_ai/modules/deployment_manager.py 封装
"""

import os
import json
import shutil
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class DeploymentError(Exception):
    """部署异常"""
    pass


class RollbackError(Exception):
    """回滚异常"""
    pass


@dataclass
class ConfigVersion:
    """配置版本"""
    version: str
    timestamp: str
    description: str
    config_path: str
    checksum: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConfigBackup:
    """配置备份"""

    def __init__(
        self,
        backup_dir: Optional[Path] = None,
        max_backups: int = 10
    ):
        """
        初始化配置备份

        Args:
            backup_dir: 备份目录路径
            max_backups: 最大保留备份数
        """
        if backup_dir:
            self.backup_dir = Path(backup_dir)
        else:
            self.backup_dir = Path(__file__).parent / 'config_backups'

        self.max_backups = max_backups
        self._ensure_backup_dir()

    def _ensure_backup_dir(self) -> None:
        """确保备份目录存在"""
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(
        self,
        config_path: Path,
        version: str,
        description: str = ""
    ) -> ConfigVersion:
        """
        创建配置备份

        Args:
            config_path: 配置文件路径
            version: 版本号
            description: 描述

        Returns:
            配置版本信息
        """
        config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        from data_integrity_integration import get_data_integrity
        integrity = get_data_integrity()
        checksum = integrity.compute_file_checksum(config_path)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{config_path.stem}_{version}_{timestamp}{config_path.suffix}"
        backup_path = self.backup_dir / backup_name

        shutil.copy2(config_path, backup_path)

        config_version = ConfigVersion(
            version=version,
            timestamp=timestamp,
            description=description,
            config_path=str(backup_path),
            checksum=checksum
        )

        self._save_version_info(config_version)
        self._cleanup_old_backups()

        logger.info(f"配置备份创建成功: {backup_path}")
        return config_version

    def restore_backup(
        self,
        version: str,
        target_path: Optional[Path] = None
    ) -> bool:
        """
        恢复配置备份

        Args:
            version: 版本号
            target_path: 目标路径，默认覆盖原文件

        Returns:
            是否恢复成功
        """
        version_info = self._load_version_info(version)

        if not version_info:
            raise RollbackError(f"未找到版本: {version}")

        backup_path = Path(version_info.config_path)
        if not backup_path.exists():
            raise RollbackError(f"备份文件不存在: {backup_path}")

        if target_path:
            shutil.copy2(backup_path, target_path)
            logger.info(f"配置恢复成功: {backup_path} -> {target_path}")
        else:
            original_path = Path(version_info.config_path).name
            shutil.copy2(backup_path, original_path)
            logger.info(f"配置恢复成功: {backup_path}")

        return True

    def list_backups(self) -> List[ConfigVersion]:
        """列出所有备份"""
        versions_file = self.backup_dir / 'versions.json'

        if not versions_file.exists():
            return []

        try:
            with open(versions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return [
                ConfigVersion(**v) if isinstance(v, dict) else v
                for v in data.get('versions', [])
            ]
        except Exception as e:
            logger.error(f"读取版本信息失败: {e}")
            return []

    def _save_version_info(self, version_info: ConfigVersion) -> None:
        """保存版本信息"""
        versions_file = self.backup_dir / 'versions.json'

        versions = []
        if versions_file.exists():
            try:
                with open(versions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                versions = data.get('versions', [])
            except Exception:
                pass

        versions.insert(0, version_info.__dict__)

        with open(versions_file, 'w', encoding='utf-8') as f:
            json.dump({'versions': versions}, f, indent=2, ensure_ascii=False)

    def _load_version_info(self, version: str) -> Optional[ConfigVersion]:
        """加载版本信息"""
        backups = self.list_backups()

        for backup in backups:
            if backup.version == version:
                return backup

        return None

    def _cleanup_old_backups(self) -> None:
        """清理旧备份"""
        backups = self.list_backups()

        if len(backups) > self.max_backups:
            for old_backup in backups[self.max_backups:]:
                try:
                    backup_path = Path(old_backup.config_path)
                    if backup_path.exists():
                        backup_path.unlink()
                    logger.info(f"清理旧备份: {backup_path}")
                except Exception as e:
                    logger.warning(f"清理备份失败: {old_backup.config_path}, {e}")


class DeploymentManager:
    """部署管理器"""

    def __init__(
        self,
        app_name: str = "steel_belt_system",
        config_dir: Optional[Path] = None,
        backup_dir: Optional[Path] = None
    ):
        """
        初始化部署管理器

        Args:
            app_name: 应用名称
            config_dir: 配置目录
            backup_dir: 备份目录
        """
        self.app_name = app_name

        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            self.config_dir = Path(__file__).parent / 'data'

        self.backup = ConfigBackup(backup_dir)

        self._deployments: Dict[str, dict] = {}
        self._load_deployments()

    def _load_deployments(self) -> None:
        """加载部署记录"""
        deployments_file = self.config_dir / 'deployments.json'

        if deployments_file.exists():
            try:
                with open(deployments_file, 'r', encoding='utf-8') as f:
                    self._deployments = json.load(f)
            except Exception as e:
                logger.warning(f"加载部署记录失败: {e}")

    def _save_deployments(self) -> None:
        """保存部署记录"""
        deployments_file = self.config_dir / 'deployments.json'

        try:
            with open(deployments_file, 'w', encoding='utf-8') as f:
                json.dump(self._deployments, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存部署记录失败: {e}")

    def deploy(
        self,
        version: str,
        description: str = "",
        config_files: Optional[List[str]] = None
    ) -> bool:
        """
        执行部署

        Args:
            version: 版本号
            description: 描述
            config_files: 需要备份的配置文件列表

        Returns:
            是否部署成功
        """
        if version in self._deployments:
            logger.warning(f"版本已存在: {version}")
            return False

        deployment = {
            'version': version,
            'timestamp': datetime.now().isoformat(),
            'description': description,
            'status': 'deployed',
            'backups': []
        }

        if config_files:
            for config_file in config_files:
                config_path = Path(config_file)
                if config_path.exists():
                    try:
                        backup_info = self.backup.create_backup(
                            config_path,
                            version,
                            f"{self.app_name} - {description}"
                        )
                        deployment['backups'].append({
                            'file': str(config_path),
                            'backup_path': backup_info.config_path,
                            'checksum': backup_info.checksum
                        })
                    except Exception as e:
                        logger.error(f"备份配置文件失败: {config_file}, {e}")

        self._deployments[version] = deployment
        self._save_deployments()

        logger.info(f"部署成功: {version}")
        return True

    def rollback(self, version: str) -> bool:
        """
        回滚到指定版本

        Args:
            version: 版本号

        Returns:
            是否回滚成功
        """
        if version not in self._deployments:
            raise RollbackError(f"版本不存在: {version}")

        deployment = self._deployments[version]

        for backup_info in deployment.get('backups', []):
            try:
                self.backup.restore_backup(version, Path(backup_info['file']))
            except Exception as e:
                logger.error(f"恢复配置文件失败: {backup_info['file']}, {e}")
                raise RollbackError(f"回滚失败: {e}")

        deployment['status'] = 'rolled_back'
        deployment['rollback_time'] = datetime.now().isoformat()
        self._save_deployments()

        logger.info(f"回滚成功: {version}")
        return True

    def get_deployment(self, version: str) -> Optional[dict]:
        """获取部署信息"""
        return self._deployments.get(version)

    def list_deployments(self) -> List[dict]:
        """列出所有部署"""
        return list(self._deployments.values())

    def get_current_version(self) -> Optional[str]:
        """获取当前版本"""
        for version, deployment in self._deployments.items():
            if deployment.get('status') == 'deployed':
                return version
        return None


_deployment_manager_instance = None


def get_deployment_manager(
    app_name: str = "steel_belt_system"
) -> DeploymentManager:
    """获取部署管理器单例"""
    global _deployment_manager_instance
    if _deployment_manager_instance is None:
        _deployment_manager_instance = DeploymentManager(app_name=app_name)
    return _deployment_manager_instance


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    manager = get_deployment_manager()

    print("=" * 60)
    print("部署管理器集成模块测试")
    print("=" * 60)

    print("\n--- 部署测试 ---")
    version = "v1.0.0"
    manager.deploy(
        version=version,
        description="初始版本",
        config_files=[]
    )
    print(f"部署: {version} - 成功")

    print("\n--- 列出部署 ---")
    for dep in manager.list_deployments():
        print(f"  {dep['version']} - {dep['description']} - {dep['status']}")

    print("\n--- 获取当前版本 ---")
    current = manager.get_current_version()
    print(f"当前版本: {current}")

    print("\n--- 备份目录 ---")
    print(f"备份目录: {manager.backup.backup_dir}")

    print("\n" + "=" * 60)
