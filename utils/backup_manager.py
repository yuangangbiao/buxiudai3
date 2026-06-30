# -*- coding: utf-8 -*-
"""
数据备份管理模块
"""
import os
import shutil
import datetime
import threading
import json
import time
import tkinter as tk
from tkinter import filedialog, messagebox
from config import DB_PATH, BASE_DIR

# 备份配置文件路径
BACKUP_CONFIG_FILE = os.path.join(BASE_DIR, "data", "backup_config.json")

# 默认备份配置
DEFAULT_BACKUP_CONFIG = {
    "enabled": False,
    "interval": 24,  # 备份间隔（小时）
    "backup_dir": os.path.join(BASE_DIR, "data", "backups"),
    "keep_days": 7  # 保留备份天数
}

class BackupManager:
    """备份管理器"""
    
    def __init__(self):
        self.config = self._load_config()
        self._backup_thread = None
        self._stop_event = threading.Event()
        self._last_backup_time = None
    
    def _load_config(self):
        """加载备份配置"""
        if os.path.exists(BACKUP_CONFIG_FILE):
            try:
                with open(BACKUP_CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载备份配置失败: {e}")
        return DEFAULT_BACKUP_CONFIG
    
    def _save_config(self):
        """保存备份配置"""
        try:
            # 确保data目录存在
            os.makedirs(os.path.dirname(BACKUP_CONFIG_FILE), exist_ok=True)
            with open(BACKUP_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存备份配置失败: {e}")
    
    def get_config(self):
        """获取备份配置"""
        return self.config
    
    def update_config(self, config):
        """更新备份配置"""
        self.config.update(config)
        self._save_config()
        # 如果启用了备份，重启备份线程
        if self.config["enabled"]:
            self.start_backup_service()
    
    def start_backup_service(self):
        """启动备份服务"""
        if not self.config["enabled"]:
            return
        
        if self._backup_thread and self._backup_thread.is_alive():
            self._stop_event.set()
            self._backup_thread.join(timeout=5)
        
        self._stop_event.clear()
        self._backup_thread = threading.Thread(target=self._backup_loop, daemon=True)
        self._backup_thread.start()
    
    def _backup_loop(self):
        """备份循环"""
        while not self._stop_event.is_set():
            # 检查是否需要备份
            if self._should_backup():
                self.perform_backup()
                self._last_backup_time = datetime.datetime.now()
            
            # 等待指定间隔
            for _ in range(self.config["interval"] * 60 * 60):
                if self._stop_event.is_set():
                    break
                time.sleep(1)
    
    def _should_backup(self):
        """检查是否需要备份"""
        if not self._last_backup_time:
            return True
        
        time_diff = datetime.datetime.now() - self._last_backup_time
        return time_diff.total_seconds() >= self.config["interval"] * 3600
    
    def perform_backup(self):
        """执行备份"""
        try:
            # 确保备份目录存在
            backup_dir = self.config["backup_dir"]
            os.makedirs(backup_dir, exist_ok=True)
            
            # 生成备份文件名
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(backup_dir, f"steel_belt_{timestamp}.db")
            
            # 复制数据库文件
            shutil.copy2(DB_PATH, backup_file)
            
            # 清理过期备份
            self._cleanup_old_backups()
            
            print(f"备份成功: {backup_file}")
            return True
        except Exception as e:
            print(f"备份失败: {e}")
            return False
    
    def _cleanup_old_backups(self):
        """清理过期备份"""
        try:
            backup_dir = self.config["backup_dir"]
            keep_days = self.config["keep_days"]
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=keep_days)
            
            for filename in os.listdir(backup_dir):
                if filename.endswith(".db"):
                    file_path = os.path.join(backup_dir, filename)
                    file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_mtime < cutoff_date:
                        os.remove(file_path)
                        print(f"清理过期备份: {filename}")
        except Exception as e:
            print(f"清理过期备份失败: {e}")
    
    def restore_from_backup(self, backup_file):
        """从备份恢复"""
        try:
            # 检查备份文件是否存在
            if not os.path.exists(backup_file):
                raise FileNotFoundError(f"备份文件不存在: {backup_file}")
            
            # 复制备份文件到数据库路径
            shutil.copy2(backup_file, DB_PATH)
            return True
        except Exception as e:
            print(f"恢复备份失败: {e}")
            return False
    
    def get_backup_files(self):
        """获取备份文件列表"""
        try:
            backup_dir = self.config["backup_dir"]
            if not os.path.exists(backup_dir):
                return []
            
            backup_files = []
            for filename in os.listdir(backup_dir):
                if filename.endswith(".db"):
                    file_path = os.path.join(backup_dir, filename)
                    file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                    backup_files.append({
                        "filename": filename,
                        "path": file_path,
                        "mtime": file_mtime
                    })
            
            # 按修改时间倒序排序
            backup_files.sort(key=lambda x: x["mtime"], reverse=True)
            return backup_files
        except Exception as e:
            print(f"获取备份文件列表失败: {e}")
            return []

# 全局备份管理器实例
backup_manager = BackupManager()