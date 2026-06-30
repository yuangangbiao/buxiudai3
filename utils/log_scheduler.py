# -*- coding: utf-8 -*-
"""
日志清理调度器 - 定期清理过期日志
每天凌晨3点自动执行清理任务
"""
import threading
import time
from datetime import datetime, timedelta
from models.operation_log import OperationLogDAO

class LogCleanupScheduler:
    """日志清理调度器"""
    
    def __init__(self):
        self.running = False
        self.thread = None
    
    def _cleanup_task(self):
        """清理任务"""
        while self.running:
            now = datetime.now()
            
            # 检查是否到凌晨3点
            if now.hour == 3 and now.minute == 0:
                print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] 开始执行日志清理任务...")
                try:
                    deleted = OperationLogDAO.clean_expired_logs()
                    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] 日志清理完成，删除 {deleted} 条过期记录")
                except Exception as e:
                    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] 日志清理失败: {e}")
                
                # 等待1分钟，避免重复执行
                time.sleep(60)
            
            # 每分钟检查一次
            time.sleep(60)
    
    def start(self):
        """启动调度器"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._cleanup_task, daemon=True)
            self.thread.start()
            print("[LogScheduler] 日志清理调度器已启动")
    
    def stop(self):
        """停止调度器"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("[LogScheduler] 日志清理调度器已停止")

# 全局调度器实例
log_scheduler = LogCleanupScheduler()

def start_log_cleanup_scheduler():
    """启动日志清理调度器"""
    log_scheduler.start()

def stop_log_cleanup_scheduler():
    """停止日志清理调度器"""
    log_scheduler.stop()