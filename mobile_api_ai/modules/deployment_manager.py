#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""部署回滚模块 - 含配置版本管理、自动回滚、部署状态追踪"""

import os
import sys
import json
import time
import shutil
import hashlib
import logging
import subprocess
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime
from pathlib import Path
from threading import Lock
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DeploymentRecord:
    """部署记录"""
    version: str
    deployed_at: str
    deployed_by: str
    status: str
    backup_path: str
    changes: List[str] = field(default_factory=list)
    error: Optional[str] = None
    rollback_from: Optional[str] = None


@dataclass
class ConfigSnapshot:
    """配置快照"""
    version: str
    created_at: str
    files: Dict[str, str] = field(default_factory=dict)
    checksum: str = ""


class DeploymentManager:
    """
    部署管理器（含回滚功能）

    功能特性:
    - 部署前自动备份
    - 配置版本管理
    - 回滚功能
    - 部署状态追踪
    - 部署验证
    """

    def __init__(
        self,
        backup_dir: str = '_backups',
        config_dir: str = '_config',
        deploy_dir: str = '_deploy',
        max_backups: int = 10
    ):
        """
        初始化部署管理器

        Args:
            backup_dir: 备份存储目录
            config_dir: 配置文件目录
            deploy_dir: 部署目录
            max_backups: 最大备份保留数量
        """
        self.backup_dir = Path(backup_dir)
        self.config_dir = Path(config_dir)
        self.deploy_dir = Path(deploy_dir)
        self.max_backups = max_backups

        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.deploy_dir.mkdir(parents=True, exist_ok=True)

        self._current_version = None
        self._deployment_history: List[DeploymentRecord] = []
        self._lock = Lock()

        self._load_history()
        self._detect_current_version()

        logger.info(
            f"DeploymentManager initialized: "
            f"backup_dir={backup_dir}, max_backups={max_backups}"
        )

    def _detect_current_version(self):
        """检测当前版本"""
        version_file = self.deploy_dir / 'current_version.txt'
        if version_file.exists():
            self._current_version = version_file.read_text().strip()

        if not self._current_version:
            self._current_version = self._generate_version('initial')
            self._save_current_version()

    def _generate_version(self, prefix: str = 'v') -> str:
        """生成版本号"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{prefix}{timestamp}"

    def _save_current_version(self):
        """保存当前版本号"""
        version_file = self.deploy_dir / 'current_version.txt'
        version_file.write_text(self._current_version)

    def _load_history(self):
        """加载部署历史"""
        history_file = self.deploy_dir / 'deployment_history.json'
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    history_data = json.load(f)
                    self._deployment_history = [
                        DeploymentRecord(**record) for record in history_data
                    ]
            except Exception as e:
                logger.warning(f"加载部署历史失败: {e}")

    def _save_history(self):
        """保存部署历史"""
        history_file = self.deploy_dir / 'deployment_history.json'
        try:
            with open(history_file, 'w', encoding='utf-8') as f:
                history_data = [
                    {
                        'version': r.version,
                        'deployed_at': r.deployed_at,
                        'deployed_by': r.deployed_by,
                        'status': r.status,
                        'backup_path': r.backup_path,
                        'changes': r.changes,
                        'error': r.error,
                        'rollback_from': r.rollback_from
                    }
                    for r in self._deployment_history[-50:]
                ]
                json.dump(history_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存部署历史失败: {e}")

    def _calculate_checksum(self, content: str) -> str:
        """计算内容校验和"""
        return hashlib.sha256(content.encode()).hexdigest()

    def _backup_config_files(self, backup_path: Path) -> Dict[str, str]:
        """
        备份配置文件

        Returns:
            文件路径和校验和的映射
        """
        checksums = {}
        config_files = list(self.config_dir.glob('*.py'))

        for config_file in config_files:
            if config_file.is_file():
                dest_file = backup_path / 'configs' / config_file.name
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(config_file, dest_file)
                checksums[str(config_file)] = self._calculate_checksum(dest_file.read_text())

        return checksums

    def _restore_config_files(self, backup_path: Path):
        """恢复配置文件"""
        backup_configs = backup_path / 'configs'
        if not backup_configs.exists():
            raise FileNotFoundError(f"备份配置目录不存在: {backup_configs}")

        for config_file in backup_configs.iterdir():
            if config_file.is_file():
                dest_file = self.config_dir / config_file.name
                shutil.copy2(config_file, dest_file)
                logger.info(f"恢复配置文件: {config_file.name}")

    def create_backup(self, version: Optional[str] = None) -> str:
        """
        创建备份

        Args:
            version: 版本号（可选）

        Returns:
            备份路径
        """
        if version is None:
            version = self._current_version

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = self.backup_dir / f"{version}_{timestamp}"

        backup_path.mkdir(parents=True, exist_ok=True)
        (backup_path / 'configs').mkdir(exist_ok=True)

        checksums = self._backup_config_files(backup_path)

        metadata = {
            'version': version,
            'created_at': datetime.now().isoformat(),
            'checksums': checksums
        }

        metadata_file = backup_path / 'metadata.json'
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        logger.info(f"创建备份: {backup_path}")
        return str(backup_path)

    def deploy(
        self,
        deploy_func: Callable,
        version: Optional[str] = None,
        deployed_by: str = 'system',
        changes: Optional[List[str]] = None,
        rollback_func: Optional[Callable] = None,
        pre_deploy_verify: Optional[Callable] = None,
        post_deploy验证: Optional[Callable] = None
    ) -> DeploymentRecord:
        """
        执行部署（带回滚）

        Args:
            deploy_func: 部署函数
            version: 版本号
            deployed_by: 部署人
            changes: 变更列表
            rollback_func: 回滚函数（可选）
            pre_deploy_verify: 部署前验证函数
            post_deploy验证: 部署后验证函数

        Returns:
            DeploymentRecord: 部署记录
        """
        if version is None:
            version = self._generate_version()

        record = DeploymentRecord(
            version=version,
            deployed_at=datetime.now().isoformat(),
            deployed_by=deployed_by,
            status='pending',
            backup_path='',
            changes=changes or []
        )

        with self._lock:
            try:
                logger.info(f"开始部署: {version}")

                if pre_deploy_verify:
                    logger.info("执行部署前验证...")
                    if not pre_deploy_verify():
                        raise Exception("部署前验证失败")

                backup_path = self.create_backup(version)
                record.backup_path = backup_path
                logger.info(f"配置备份完成: {backup_path}")

                logger.info(f"执行部署函数...")
                deploy_func()

                if post_deploy验证:
                    logger.info("执行部署后验证...")
                    if not post_deploy验证():
                        raise Exception("部署后验证失败")

                self._current_version = version
                self._save_current_version()

                record.status = 'success'
                logger.info(f"部署成功: {version}")

            except Exception as e:
                record.status = 'failed'
                record.error = str(e)
                logger.error(f"部署失败: {e}")

                if rollback_func:
                    logger.info("执行自动回滚...")
                    try:
                        rollback_func()
                        record.rollback_from = version
                        logger.info("自动回滚完成")
                    except Exception as rollback_error:
                        logger.error(f"回滚失败: {rollback_error}")
                        record.error = f"{record.error}; 回滚也失败: {rollback_error}"

                elif record.backup_path:
                    logger.info("执行配置回滚...")
                    try:
                        self._restore_from_backup(Path(record.backup_path))
                        record.rollback_from = version
                        logger.info("配置回滚完成")
                    except Exception as restore_error:
                        logger.error(f"配置回滚失败: {restore_error}")
                        record.error = f"{record.error}; 配置回滚也失败: {restore_error}"

            finally:
                self._deployment_history.append(record)
                self._save_history()
                self._cleanup_old_backups()

        return record

    def _restore_from_backup(self, backup_path: Path):
        """从备份恢复"""
        if not backup_path.exists():
            raise FileNotFoundError(f"备份不存在: {backup_path}")

        self._restore_config_files(backup_path)
        logger.info(f"已从备份恢复: {backup_path}")

    def rollback(self, target_version: Optional[str] = None) -> DeploymentRecord:
        """
        回滚到指定版本

        Args:
            target_version: 目标版本（默认回滚到上一个版本）

        Returns:
            DeploymentRecord: 回滚记录
        """
        with self._lock:
            if target_version is None:
                successful_deploys = [
                    r for r in self._deployment_history
                    if r.status == 'success' and r.rollback_from is None
                ]
                if len(successful_deploys) < 2:
                    raise Exception("没有可回滚的版本")

                target_record = successful_deploys[-2]
                target_version = target_record.version
            else:
                target_records = [
                    r for r in self._deployment_history
                    if r.version == target_version and r.status == 'success'
                ]
                if not target_records:
                    raise Exception(f"版本不存在或未部署成功: {target_version}")
                target_record = target_records[0]

            backup_path = Path(target_record.backup_path)
            if not backup_path.exists():
                raise FileNotFoundError(f"备份不存在: {backup_path}")

            logger.info(f"开始回滚到版本: {target_version}")

            try:
                self._restore_config_files(backup_path)

                rollback_record = DeploymentRecord(
                    version=self._generate_version('rollback_'),
                    deployed_at=datetime.now().isoformat(),
                    deployed_by='system',
                    status='success',
                    backup_path=str(backup_path),
                    changes=[f"回滚到版本 {target_version}"],
                    rollback_from=target_version
                )

                self._current_version = target_version
                self._save_current_version()

                self._deployment_history.append(rollback_record)
                self._save_history()

                logger.info(f"回滚成功: {target_version}")
                return rollback_record

            except Exception as e:
                logger.error(f"回滚失败: {e}")
                raise

    def _cleanup_old_backups(self):
        """清理旧备份"""
        backups = sorted(
            self.backup_dir.iterdir(),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )

        for backup in backups[self.max_backups:]:
            try:
                shutil.rmtree(backup)
                logger.info(f"删除旧备份: {backup}")
            except Exception as e:
                logger.warning(f"删除旧备份失败: {backup}, {e}")

    def get_deployment_history(self, limit: int = 10) -> List[DeploymentRecord]:
        """获取部署历史"""
        return self._deployment_history[-limit:]

    def get_current_version(self) -> str:
        """获取当前版本"""
        return self._current_version

    def get_backup_list(self) -> List[Dict[str, Any]]:
        """获取备份列表"""
        backups = []
        for backup_dir in self.backup_dir.iterdir():
            if backup_dir.is_dir():
                metadata_file = backup_dir / 'metadata.json'
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                            backups.append({
                                'path': str(backup_dir),
                                'version': metadata.get('version'),
                                'created_at': metadata.get('created_at'),
                                'size': sum(
                                    f.stat().st_size
                                    for f in backup_dir.rglob('*')
                                    if f.is_file()
                                )
                            })
                    except Exception as e:
                        logger.warning(f"读取备份元数据失败: {backup_dir}, {e}")

        return sorted(backups, key=lambda x: x.get('created_at', ''), reverse=True)

    def verify_backup(self, backup_path: str) -> bool:
        """
        验证备份完整性

        Args:
            backup_path: 备份路径

        Returns:
            bool: 是否完整
        """
        backup_dir = Path(backup_path)
        if not backup_dir.exists():
            return False

        metadata_file = backup_dir / 'metadata.json'
        if not metadata_file.exists():
            return False

        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            checksums = metadata.get('checksums', {})
            for file_path, expected_checksum in checksums.items():
                file_name = Path(file_path).name
                actual_file = backup_dir / 'configs' / file_name

                if not actual_file.exists():
                    logger.warning(f"备份文件缺失: {file_name}")
                    return False

                actual_checksum = self._calculate_checksum(actual_file.read_text())
                if actual_checksum != expected_checksum:
                    logger.warning(f"备份文件校验失败: {file_name}")
                    return False

            return True

        except Exception as e:
            logger.error(f"验证备份失败: {e}")
            return False


class DeploymentError(Exception):
    """部署异常"""
    pass


_global_deployment_manager = None


def init_deployment_manager(**kwargs) -> DeploymentManager:
    """初始化全局部署管理器"""
    global _global_deployment_manager
    _global_deployment_manager = DeploymentManager(**kwargs)
    return _global_deployment_manager


def get_deployment_manager() -> DeploymentManager:
    """获取全局部署管理器"""
    global _global_deployment_manager
    if _global_deployment_manager is None:
        _global_deployment_manager = DeploymentManager()
    return _global_deployment_manager
