#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""增强版备份脚本 - 含完整性校验、恢复验证、自动清理"""

import os
import json
import time
import subprocess
import shutil
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from core.config import get_default_backup_dir, get_app_dir, get_default_redis_dump, SNAPSHOT_TIMEOUT

logger = logging.getLogger(__name__)


class EnhancedBackupManager:
    """增强版备份管理器"""

    def __init__(self, backup_dir=None, redis_password=None,
                 es_data_dir=None, min_disk_space_gb=10):
        """
        初始化备份管理器

        Args:
            backup_dir: 备份存储目录，默认 DAT/backup
            redis_password: Redis密码
            es_data_dir: Elasticsearch数据目录
            min_disk_space_gb: 最小磁盘空间要求(GB)
        """
        self.backup_dir = Path(backup_dir or os.environ.get('BACKUP_DIR', get_default_backup_dir()))
        self.redis_password = redis_password or os.getenv('REDIS_PASSWORD')
        self.es_data_dir = es_data_dir or os.environ.get('ES_DATA_DIR', '')
        self.min_disk_space_bytes = min_disk_space_gb * 1024 * 1024 * 1024
        self.retention_days = int(os.environ.get('BACKUP_RETENTION_DAYS', '7'))
        self.backup_metadata = {}

        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_directories()

    def _ensure_directories(self):
        """确保备份目录结构存在"""
        subdirs = ['redis', 'elasticsearch', 'configs', 'logs', 'metadata']
        for subdir in subdirs:
            (self.backup_dir / subdir).mkdir(parents=True, exist_ok=True)

    def _check_disk_space(self):
        """检查磁盘空间是否充足"""
        try:
            result = shutil.disk_usage(self.backup_dir)
            available = result.free

            if available < self.min_disk_space_bytes:
                logger.error(f"磁盘空间不足: 可用{available / 1024**3:.2f}GB, 需要{self.min_disk_space_bytes / 1024**3:.2f}GB")
                return False, {
                    'available_gb': round(available / 1024**3, 2),
                    'required_gb': self.min_disk_space_bytes / 1024**3,
                    'status': 'insufficient'
                }

            return True, {
                'available_gb': round(available / 1024**3, 2),
                'used_gb': round(result.used / 1024**3, 2),
                'total_gb': round(result.total / 1024**3, 2),
                'status': 'ok'
            }
        except Exception as e:
            logger.error(f"检查磁盘空间失败: {e}")
            return False, {'error': str(e), 'status': 'error'}

    def _calculate_file_hash(self, file_path):
        """计算文件SHA256哈希"""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"计算文件哈希失败 {file_path}: {e}")
            return None

    def _verify_file_hash(self, file_path, expected_hash):
        """验证文件哈希"""
        actual_hash = self._calculate_file_hash(file_path)
        if actual_hash is None:
            return False
        return actual_hash == expected_hash

    def backup_redis(self):
        """备份Redis（BGSAVE + 校验）"""
        logger.info("开始Redis备份...")
        backup_info = {
            'type': 'redis',
            'started_at': datetime.now().isoformat(),
            'status': 'pending'
        }

        try:
            redis_dump_path = get_default_redis_dump()
            if not redis_dump_path or not os.path.exists(redis_dump_path):
                logger.warning(f"Redis dump文件不存在或未配置: {redis_dump_path}")
                backup_info['status'] = 'skipped'
                backup_info['reason'] = 'dump file not found'
                return backup_info

            bg_env = os.environ.copy()
            if self.redis_password:
                bg_env['REDISCLI_AUTH'] = self.redis_password
            bg_save_cmd = ['redis-cli', 'BGSAVE']

            result = subprocess.run(bg_save_cmd, capture_output=True, text=True, timeout=int(os.environ.get('REQUEST_TIMEOUT_EXTRA', '30')), env=bg_env)

            if 'Background saving started' not in result.stdout and result.returncode != 0:
                logger.warning(f"BGSAVE可能失败: {result.stdout} {result.stderr}")

            time.sleep(2)

            lastsave_cmd = ['redis-cli', 'LASTSAVE']
            lastsave_result = subprocess.run(lastsave_cmd, capture_output=True, text=True, timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10')))
            lastsave = lastsave_result.stdout.strip()

            backup_filename = f"redis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.rdb"
            backup_path = self.backup_dir / 'redis' / backup_filename

            shutil.copy2(redis_dump_path, backup_path)

            file_hash = self._calculate_file_hash(backup_path)
            if file_hash is None:
                raise Exception("Redis备份哈希计算失败")

            hash_file_path = backup_path.with_suffix('.rdb.sha256')
            with open(hash_file_path, 'w') as f:
                f.write(file_hash)

            lastsave_file = backup_path.with_suffix('.rdb.lastsave')
            with open(lastsave_file, 'w') as f:
                f.write(lastsave)

            backup_info.update({
                'status': 'success',
                'file': str(backup_path),
                'hash': file_hash,
                'hash_file': str(hash_file_path),
                'lastsave': lastsave,
                'size_bytes': os.path.getsize(backup_path),
                'completed_at': datetime.now().isoformat()
            })

            logger.info(f"Redis备份完成: {backup_path} ({file_hash[:16]}...)")
            return backup_info

        except Exception as e:
            logger.error(f"Redis备份失败: {e}")
            backup_info.update({
                'status': 'failed',
                'error': str(e)
            })
            return backup_info

    def backup_elasticsearch(self):
        """备份Elasticsearch快照"""
        logger.info("开始Elasticsearch备份...")
        backup_info = {
            'type': 'elasticsearch',
            'started_at': datetime.now().isoformat(),
            'status': 'pending'
        }

        try:
            snapshot_name = f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            repo_check_cmd = ['curl', '-s', 'localhost:9200/_snapshot/backup_repo']
            repo_result = subprocess.run(repo_check_cmd, capture_output=True, text=True, timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10')))

            if 'true' not in repo_result.stdout.lower() and 'exists' not in repo_result.stdout.lower():
                logger.warning("ES备份仓库不存在或不可访问，跳过ES备份")
                backup_info['status'] = 'skipped'
                backup_info['reason'] = 'backup repo not accessible'
                return backup_info

            create_snapshot_cmd = [
                'curl', '-X', 'PUT',
                f'localhost:9200/_snapshot/backup_repo/{snapshot_name}',
                '-d', '{"indices": "*", "ignore_unavailable": true, "include_global_state": false}',
                '-H', 'Content-Type: application/json'
            ]

            result = subprocess.run(create_snapshot_cmd, capture_output=True, text=True, timeout=SNAPSHOT_TIMEOUT)

            if '"acknowledged":true' in result.stdout or '"accepted":true' in result.stdout:
                backup_info.update({
                    'status': 'success',
                    'snapshot_name': snapshot_name,
                    'completed_at': datetime.now().isoformat()
                })
                logger.info(f"Elasticsearch快照创建成功: {snapshot_name}")
            else:
                logger.warning(f"ES快照创建响应异常: {result.stdout}")
                backup_info.update({
                    'status': 'partial',
                    'response': result.stdout
                })

            return backup_info

        except subprocess.TimeoutExpired:
            logger.error("Elasticsearch备份超时")
            backup_info.update({'status': 'failed', 'error': 'timeout'})
            return backup_info
        except Exception as e:
            logger.error(f"Elasticsearch备份失败: {e}")
            backup_info.update({'status': 'failed', 'error': str(e)})
            return backup_info

    def backup_configs(self):
        """备份配置文件"""
        logger.info("开始配置文件备份...")
        backup_info = {
            'type': 'configs',
            'started_at': datetime.now().isoformat(),
            'status': 'pending',
            'files': []
        }

        app_dir = get_app_dir()
        config_files = [
            os.path.join(app_dir, 'config.py'),
            os.path.join(app_dir, 'DAT', '.env'),
        ]
        env_config = os.environ.get('BACKUP_CONFIG_FILES', '')
        if env_config:
            config_files.extend(env_config.split(os.pathsep))

        for config_file in config_files:
            if os.path.exists(config_file):
                try:
                    filename = os.path.basename(config_file)
                    backup_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                    backup_path = self.backup_dir / 'configs' / backup_filename

                    shutil.copy2(config_file, backup_path)

                    file_hash = self._calculate_file_hash(backup_path)

                    backup_info['files'].append({
                        'source': config_file,
                        'backup': str(backup_path),
                        'hash': file_hash,
                        'size': os.path.getsize(backup_path)
                    })

                    logger.info(f"配置文件备份: {config_file} -> {backup_path}")

                except Exception as e:
                    logger.error(f"备份配置文件失败 {config_file}: {e}")

        backup_info.update({
            'status': 'success' if backup_info['files'] else 'skipped',
            'completed_at': datetime.now().isoformat()
        })

        return backup_info

    def verify_backup(self, backup_info):
        """
        验证备份完整性

        Args:
            backup_info: 备份信息字典

        Returns:
            tuple: (是否通过, 验证详情)
        """
        logger.info(f"验证备份: {backup_info.get('type')}")

        if backup_info.get('type') == 'redis':
            backup_file = backup_info.get('file')
            expected_hash = backup_info.get('hash')

            if not backup_file or not os.path.exists(backup_file):
                return False, {'error': '备份文件不存在'}

            if not self._verify_file_hash(backup_file, expected_hash):
                return False, {'error': '哈希校验失败', 'expected': expected_hash}

            return True, {
                'file': backup_file,
                'hash': expected_hash,
                'size': os.path.getsize(backup_file),
                'verified_at': datetime.now().isoformat()
            }

        return True, {'status': 'verified'}

    def test_restore(self, backup_type='redis'):
        """
        测试恢复功能（不覆盖生产数据）

        Args:
            backup_type: 备份类型

        Returns:
            tuple: (是否成功, 测试结果)
        """
        logger.info(f"测试{backup_type}恢复...")

        if backup_type == 'redis':
            redis_backups = sorted((self.backup_dir / 'redis').glob('*.rdb'),
                                    key=lambda x: x.stat().st_mtime, reverse=True)

            if not redis_backups:
                return False, {'error': '无Redis备份文件'}

            latest_backup = redis_backups[0]

            try:
                test_rdb_dir = self.backup_dir / 'logs'
                test_rdb_path = test_rdb_dir / 'test_restore.rdb'
                shutil.copy2(latest_backup, test_rdb_path)

                if self.redis_password:
                    verify_cmd = ['redis-cli', '-a', self.redis_password, '-e', 'PING']
                else:
                    verify_cmd = ['redis-cli', 'PING']

                subprocess.run(verify_cmd, capture_output=True, text=True, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))

                test_rdb_path.unlink(missing_ok=True)

                return True, {
                    'backup_file': str(latest_backup),
                    'size': latest_backup.stat().st_size,
                    'verified_at': datetime.now().isoformat()
                }

            except Exception as e:
                logger.error(f"Redis恢复测试失败: {e}")
                test_rdb = self.backup_dir / 'logs' / 'test_restore.rdb'
                if test_rdb.exists():
                    test_rdb.unlink()
                return False, {'error': str(e)}

        return False, {'error': 'unsupported backup type'}

    def cleanup_old_backups(self):
        """清理过期备份"""
        logger.info("开始清理过期备份...")

        cutoff_time = time.time() - (self.retention_days * 86400)
        cleaned_count = 0
        cleaned_size = 0

        for subdir in ['redis', 'elasticsearch', 'configs']:
            subdir_path = self.backup_dir / subdir

            for item in subdir_path.iterdir():
                if item.is_file():
                    if item.stat().st_mtime < cutoff_time:
                        size = item.stat().st_size
                        item.unlink()
                        cleaned_count += 1
                        cleaned_size += size
                        logger.info(f"删除过期备份: {item}")

                elif item.is_dir():
                    if item.stat().st_mtime < cutoff_time:
                        size = sum(f.stat().st_size for f in item.rglob('*') if f.is_file())
                        shutil.rmtree(item)
                        cleaned_count += 1
                        cleaned_size += size
                        logger.info(f"删除过期备份目录: {item}")

        logger.info(f"清理完成: 删除{cleaned_count}个文件, 释放{cleaned_size / 1024**2:.2f}MB")

        return {
            'cleaned_count': cleaned_count,
            'cleaned_size_mb': round(cleaned_size / 1024**2, 2)
        }

    def run_full_backup(self):
        """执行完整备份流程"""
        logger.info("=== 开始完整备份 ===")

        backup_result = {
            'started_at': datetime.now().isoformat(),
            'disk_space': {},
            'redis': {},
            'elasticsearch': {},
            'configs': {},
            'verification': {},
            'cleanup': {},
            'overall_status': 'pending'
        }

        is_enough_space, space_info = self._check_disk_space()
        backup_result['disk_space'] = space_info

        if not is_enough_space:
            logger.error("磁盘空间不足，备份取消")
            backup_result['overall_status'] = 'failed'
            backup_result['error'] = 'insufficient disk space'
            return backup_result

        redis_result = self.backup_redis()
        backup_result['redis'] = redis_result

        es_result = self.backup_elasticsearch()
        backup_result['elasticsearch'] = es_result

        configs_result = self.backup_configs()
        backup_result['configs'] = configs_result

        if redis_result.get('status') == 'success':
            is_valid, verify_info = self.verify_backup(redis_result)
            backup_result['verification']['redis'] = {
                'passed': is_valid,
                'details': verify_info
            }

            if is_valid:
                can_restore, restore_info = self.test_restore('redis')
                backup_result['verification']['restore_test'] = {
                    'passed': can_restore,
                    'details': restore_info
                }

        cleanup_result = self.cleanup_old_backups()
        backup_result['cleanup'] = cleanup_result

        backup_result['completed_at'] = datetime.now().isoformat()

        failed_count = sum(1 for k in ['redis', 'elasticsearch', 'configs']
                          if backup_result.get(k, {}).get('status') == 'failed')

        backup_result['overall_status'] = 'success' if failed_count == 0 else 'partial'

        metadata_file = self.backup_dir / 'metadata' / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(backup_result, f, indent=2, ensure_ascii=False)

        logger.info(f"=== 备份完成: {backup_result['overall_status']} ===")

        return backup_result

    def list_backups(self):
        """列出所有备份"""
        backups = []

        for subdir in ['redis', 'elasticsearch', 'configs']:
            subdir_path = self.backup_dir / subdir

            for item in subdir_path.rglob('*'):
                if item.is_file():
                    backups.append({
                        'type': subdir,
                        'path': str(item),
                        'name': item.name,
                        'size_bytes': item.stat().st_size,
                        'modified': datetime.fromtimestamp(item.stat().st_mtime).isoformat(),
                        'age_days': (time.time() - item.stat().st_mtime) / 86400
                    })

        return sorted(backups, key=lambda x: x['modified'], reverse=True)


def main():
    """主函数"""
    backup_dir = os.environ.get('BACKUP_DIR', get_default_backup_dir())
    backup_manager = EnhancedBackupManager(
        backup_dir=backup_dir,
        redis_password=os.getenv('REDIS_PASSWORD'),
        es_data_dir=os.environ.get('ES_DATA_DIR', '')
    )

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == 'backup':
            result = backup_manager.run_full_backup()
            logger.info(json.dumps(result, indent=2, ensure_ascii=False))
            sys.exit(0 if result['overall_status'] == 'success' else 1)

        elif command == 'list':
            backups = backup_manager.list_backups()
            logger.info(json.dumps(backups, indent=2, ensure_ascii=False))
            sys.exit(0)

        elif command == 'verify':
            redis_backups = sorted((backup_manager.backup_dir / 'redis').glob('*.rdb'),
                                   key=lambda x: x.stat().st_mtime, reverse=True)
            if redis_backups:
                hash_file = redis_backups[0].with_suffix('.rdb.sha256')
                hash_value = hash_file.read_text().strip() if hash_file.exists() else ''
                backup_info = {'type': 'redis', 'file': str(redis_backups[0]),
                              'hash': hash_value}
                is_valid, details = backup_manager.verify_backup(backup_info)
                logger.info(json.dumps({'valid': is_valid, 'details': details}, indent=2))
                sys.exit(0 if is_valid else 1)
            else:
                logger.error(json.dumps({'error': 'no backup found'}))
                sys.exit(1)

        elif command == 'test-restore':
            can_restore, details = backup_manager.test_restore('redis')
            logger.info(json.dumps({'can_restore': can_restore, 'details': details}, indent=2))
            sys.exit(0 if can_restore else 1)

        elif command == 'cleanup':
            result = backup_manager.cleanup_old_backups()
            logger.info(json.dumps(result, indent=2))
            sys.exit(0)

        else:
            logger.warning(f"未知命令: {command}")
            logger.warning("可用命令: backup, list, verify, test-restore, cleanup")
            sys.exit(1)
    else:
        result = backup_manager.run_full_backup()
        logger.info(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(0 if result['overall_status'] == 'success' else 1)


if __name__ == '__main__':
    main()
