# -*- coding: utf-8 -*-
"""
不锈钢输送网带跟单系统 - 主入口（优化版）

优化策略：
1. 模块懒加载 - 延迟导入非关键模块
2. 并行初始化 - 使用线程同时执行独立任务
3. 合并数据库操作 - 减少连接次数
4. 异步升级检查 - 后台执行不阻塞启动
"""

import sys
import os
import traceback
import logging
import threading
import time

# 获取应用目录（打包后是exe所在目录，开发时是脚本所在目录）
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

# 添加项目根目录到路径
sys.path.insert(0, APP_DIR)

# 配置日志（必须先于 .env 加载）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(APP_DIR, 'app.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 记录启动开始时间
_start_time = time.time()

def _log_time(name):
    """记录耗时"""
    elapsed = (time.time() - _start_time) * 1000
    logger.info(f"[TIMING] {name}: {elapsed:.1f}ms")



def log_error(exc_type, exc_value, exc_traceback):
    """全局异常处理器 - 集成统一错误处理"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    try:
        from core.error_handler import handle_error, recognize_error_code

        error_code, user_hint = handle_error(exc_type, exc_value, exc_traceback)

        try:
            from tkinter import messagebox
            messagebox.showerror(f"错误 {error_code or 'UNKNOWN'}", user_hint)
        except Exception:
            print(user_hint)

    except Exception:
        error_msg = f"未处理的异常: {exc_type.__name__}: {exc_value}"
        logger.error(error_msg)
        logger.error("完整堆栈跟踪:")
        logger.error(''.join(traceback.format_exception(exc_type, exc_value, exc_traceback)))

        try:
            from tkinter import messagebox
            messagebox.showerror("程序异常", f"程序运行中发生错误：\n{exc_value}\n\n详细信息请查看 app.log 文件")
        except Exception as e:
            logger.warning(f"无法显示错误对话框: {e}")


# 设置全局异常处理器
sys.excepthook = log_error


def _show_db_connection_error(e):
    """显示数据库连接错误提示"""
    error_msg = str(e)
    suggestions = []
    
    if "Access denied" in error_msg or "using password: NO" in error_msg:
        suggestions.append("• 请检查MySQL用户名和密码是否正确")
        suggestions.append("• 如果MySQL设置了密码，请在 .env 文件中设置 MYSQL_PASSWORD")
        suggestions.append("• 可以通过系统设置 -> 数据库连接 来配置")
    elif "Can't connect to MySQL server" in error_msg:
        suggestions.append("• 请确认MySQL服务是否已启动")
        suggestions.append("• 请检查MySQL主机地址和端口是否正确")
        suggestions.append("• 如果是远程数据库，请确认网络连接正常")
    elif "Unknown database" in error_msg:
        suggestions.append("• 请确认数据库是否已创建")
        suggestions.append("• 数据库名: steel_belt")
    
    suggestion_text = "\n".join(suggestions) if suggestions else ""
    full_msg = f"数据库连接失败：\n{error_msg}\n\n{suggestion_text}"
    return full_msg


def _check_license():
    """许可证检查（独立线程执行）"""
    try:
        from security.license_tool import check_activation, verify_binding, generate_fingerprint
        
        status = check_activation()
        if not status['is_activated']:
            return {
                'success': False,
                'error': f"""{'='*50}
软件未激活！

机器指纹: {status['fingerprint_short']}
完整指纹: {status['fingerprint']}

请联系销售人员获取激活密钥。

激活方式：
1. 运行: python security/license_tool.py
2. 输入许可证密钥
{'='*50}"""
            }
        
        current_fp = generate_fingerprint()
        if not verify_binding(current_fp):
            return {
                'success': False,
                'error': f"""{'='*50}
许可证验证失败！

当前机器指纹: {current_fp[:8].upper()}

软件可能被复制到了其他电脑。
请联系技术支持获取帮助。
{'='*50}"""
            }
        
        logger.info(f"[LICENSE] 许可证验证通过，指纹: {current_fp[:8]}...")
        return {'success': True}
    
    except Exception as e:
        logger.warning(f"[LICENSE] 许可证检查失败，继续启动: {e}")
        return {'success': True, 'warning': str(e)}


def _check_updates_async():
    """异步升级检查（后台执行，不阻塞启动）"""
    try:
        from updater import check_for_updates, apply_upgrade
        result = check_for_updates()
        if result.get("has_update"):
            success, msg = apply_upgrade()
            if success:
                logger.info("[升级] 已自动应用升级包")
                # 升级后需要重启，这里设置标记
                global _needs_restart
                _needs_restart = True
    except Exception as e:
        logger.warning(f"[升级检查] {e}")


def main():
    global _needs_restart
    _needs_restart = False
    
    try:
        # ─── 阶段1：并行执行许可证检查和升级检查 ───
        _log_time("Start")
        
        # 启动异步升级检查（后台执行）
        update_thread = threading.Thread(target=_check_updates_async, daemon=True)
        update_thread.start()
        
        # 许可证检查（同步执行）
        license_result = _check_license()
        if not license_result['success']:
            logger.error("软件未激活，拒绝启动")
            print(license_result['error'])
            try:
                from tkinter import messagebox
                messagebox.showerror("软件未激活", license_result['error'])
            except Exception as e:
                logger.warning(f"无法显示激活失败对话框: {e}")
            return
        
        _log_time("License Check")
        
        # ─── 阶段2：数据库连接检查 ───
        def _check_db_and_show_settings():
            from models.database import get_connection
            try:
                conn = get_connection()
                conn.close()
                return True
            except Exception:
                return False

        if not _check_db_and_show_settings():
            logger.warning("[DB] 数据库未连接，显示设置窗口")
            from desktop.views.db_settings_window import DatabaseSettingsWindow

            def _on_db_settings_saved():
                return _check_db_and_show_settings()

            settings_win = DatabaseSettingsWindow(on_save_callback=_on_db_settings_saved)
            settings_win.show()

            if not _check_db_and_show_settings():
                logger.error("[DB] 用户取消数据库设置，退出程序")
                return
        
        _log_time("DB Connection")
        
        # ─── 阶段3：初始化应用程序（合并数据库操作） ───
        from core.app import initialize_app, get_build_info

        build_info = get_build_info()
        banner = f"\n{'='*50}\n  钢带订单追踪系统 v{build_info['version']}\n  架构: {build_info['arch']}\n{'='*50}\n"
        print(banner)
        logger.info(banner.strip())

        try:
            initialize_app()
        except Exception as e:
            if "pymysql" in str(type(e).__module__) or "Access denied" in str(e) or "Can't connect" in str(e):
                full_msg = _show_db_connection_error(e)
                logger.error(f"数据库连接失败: {e}")
                try:
                    from tkinter import messagebox
                    messagebox.showerror("数据库连接失败", full_msg)
                except Exception:
                    print(full_msg)
                return
            raise
        
        _log_time("App Init")
        
        # ─── 阶段4：启动后台服务 ───
        # 备份系统启动（异步）
        def _start_backup_scheduler():
            try:
                from backup_system import start_backup_scheduler
                start_backup_scheduler()
                logger.info("[BACKUP] 备份调度器启动")
            except Exception as e:
                logger.warning(f"[备份系统] 启动失败: {e}")

        backup_thread = threading.Thread(target=_start_backup_scheduler, daemon=True)
        backup_thread.start()

        # 排产队列恢复线程（自动重发失败的工单）
        def _start_schedule_recovery():
            try:
                from services.schedule_dispatch_service import ScheduleDispatchService
                ScheduleDispatchService.start_queue_recovery()
            except Exception as e:
                logger.warning(f"[排产恢复] 启动失败: {e}")

        recovery_thread = threading.Thread(target=_start_schedule_recovery, daemon=True)
        recovery_thread.start()

        # 容器事件监听器初始化（订阅 EventBus 事件，触发容器池操作）
        try:
            from container_event_listener import init_container_listener
            init_container_listener()
            logger.info("[EventBus] ContainerEventListener 已初始化")
        except Exception as e:
            logger.warning(f"[EventBus] ContainerEventListener 初始化失败: {e}")
        
        _log_time("Services Started")
        
        # ─── 阶段5：启动主窗口 ───
        from desktop.views.main_window import MainWindow
        app = MainWindow()
        
        _log_time("Main Window Created")
        
        total_elapsed = (time.time() - _start_time) * 1000
        logger.info(f"[STARTUP] 启动完成，总耗时: {total_elapsed:.1f}ms")
        
        app.run()

    except Exception as e:
        error_msg = f"主程序启动失败: {e}"
        logger.error(error_msg)
        logger.error("堆栈跟踪:", exc_info=True)
        try:
            from tkinter import messagebox
            messagebox.showerror("启动失败", f"程序启动失败：\n{e}\n\n详细信息请查看 app.log 文件")
        except Exception:
            print(f"启动失败: {e}")


if __name__ == "__main__":
    main()