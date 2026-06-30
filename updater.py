# -*- coding: utf-8 -*-
"""
程序升级模块 - 支持增量升级包
"""
import os
import sys
import shutil
import json
import logging
import zipfile
from tkinter import messagebox, Toplevel, Label, Button, Frame, Text, Scrollbar, scrolledtext
from datetime import datetime

logger = logging.getLogger(__name__)

UPGRADE_DIR = "升级包"
UPDATES_DIR = "updates"

def get_local_version():
    """获取本地版本"""
    try:
        from version import VERSION
        return VERSION
    except ImportError:
        try:
            from config import APP_VERSION
            return APP_VERSION
        except Exception:
            return "0.0.0"

def get_upgrade_package_info():
    """获取升级包信息"""
    possible_base = []

    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        possible_base.append(exe_dir)
        possible_base.append(getattr(sys, '_MEIPASS', exe_dir))
    else:
        possible_base.append(os.path.dirname(os.path.abspath(__file__)))

    for base_dir in possible_base:
        upgrade_base = os.path.join(base_dir, UPGRADE_DIR)
        if os.path.exists(upgrade_base):
            break
    else:
        return None

    for item in sorted(os.listdir(upgrade_base), reverse=True):
        upgrade_path = os.path.join(upgrade_base, item)
        info_file = os.path.join(upgrade_path, "upgrade_info.json")

        if os.path.isdir(upgrade_path) and os.path.exists(info_file):
            try:
                with open(info_file, 'r', encoding='utf-8') as f:
                    info = json.load(f)

                files_dir = os.path.join(upgrade_path, "files")
                if os.path.exists(files_dir):
                    files = []
                    for root, dirs, filenames in os.walk(files_dir):
                        for filename in filenames:
                            if filename.endswith('.py'):
                                rel_path = os.path.relpath(os.path.join(root, filename), files_dir)
                                files.append(rel_path)
                    info['files'] = files
                    info['upgrade_path'] = upgrade_path
                    return info
            except Exception as e:
                logger.warning(f"读取升级包信息失败: {item}, {e}")
                continue

    return None

def apply_upgrade():
    """执行升级"""
    info = get_upgrade_package_info()
    if not info:
        return False, "未找到升级包"

    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    upgrade_path = info.get('upgrade_path', '')
    files_dir = os.path.join(upgrade_path, "files")

    if not os.path.exists(files_dir):
        return False, "升级包文件目录不存在"

    upgraded_files = []
    failed_files = []

    for rel_path in info.get('files', []):
        src_file = os.path.join(files_dir, rel_path)
        dst_file = os.path.join(base_dir, rel_path)

        if not os.path.exists(src_file):
            continue

        try:
            dst_dir = os.path.dirname(dst_file)
            if not os.path.exists(dst_dir):
                os.makedirs(dst_dir, exist_ok=True)

            shutil.copy2(src_file, dst_file)
            upgraded_files.append(rel_path)
            logger.info(f"[升级] 已更新: {rel_path}")
        except Exception as e:
            failed_files.append((rel_path, str(e)))
            logger.error(f"[升级] 更新失败: {rel_path}, {e}")

    clean_pycache(base_dir)

    if failed_files:
        msg = f"部分文件更新失败:\n" + "\n".join([f"  {f[0]}: {f[1]}" for f in failed_files])
        return False, msg

    try:
        shutil.rmtree(upgrade_path)
        logger.info(f"[升级] 升级包已清理: {upgrade_path}")
    except Exception:
        pass

    return True, f"成功更新 {len(upgraded_files)} 个文件"

def clean_pycache(base_dir):
    """清理Python缓存"""
    cleaned = 0
    for root, dirs, files in os.walk(base_dir):
        if '__pycache__' in dirs:
            pycache_path = os.path.join(root, '__pycache__')
            try:
                shutil.rmtree(pycache_path)
                cleaned += 1
            except Exception:
                pass
    if cleaned > 0:
        logger.info(f"[升级] 清理了 {cleaned} 个 __pycache__ 目录")
    return cleaned

def check_for_updates():
    """检查更新"""
    local_ver = get_local_version()
    upgrade_info = get_upgrade_package_info()

    result = {
        "has_update": False,
        "local_version": local_ver,
        "new_version": local_ver,
        "changes": "",
        "files_count": 0
    }

    if upgrade_info:
        result["has_update"] = True
        result["new_version"] = upgrade_info.get("version", "未知")
        result["changes"] = upgrade_info.get("description", "")
        result["files_count"] = len(upgrade_info.get("files", []))
        result["upgrade_info"] = upgrade_info

    return result

def show_update_dialog(parent):
    """显示更新对话框"""
    check_result = check_for_updates()

    if not check_result["has_update"]:
        messagebox.showinfo("检查更新", f"当前版本: v{check_result['local_version']}\n\n已是最新版本！")
        return

    info = check_result.get("upgrade_info", {})

    dialog = Toplevel(parent)
    dialog.title("发现新版本")
    dialog.geometry("550x400")
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()

    try:
        from config import COLORS
        bg_color = COLORS.get("bg_main", "#f5f5f5")
    except Exception:
        bg_color = "#f5f5f5"

    dialog.configure(bg=bg_color)

    content = Frame(dialog, bg=bg_color, padx=30, pady=20)
    content.pack(fill="both", expand=True)

    Label(content, text="发现新版本", font=("微软雅黑", 16, "bold"),
          bg=bg_color, fg="#2196F3").pack(pady=(0, 10))

    Label(content, text=f"当前版本: v{check_result['local_version']}",
          font=("微软雅黑", 10), bg=bg_color, fg="#666").pack(pady=2)
    Label(content, text=f"新版本: v{check_result['new_version']}",
          font=("微软雅黑", 12, "bold"), bg=bg_color, fg="#4CAF50").pack(pady=2)

    Label(content, text="更新内容:",
          font=("微软雅黑", 10, "bold"), bg=bg_color).pack(pady=(15, 5), anchor="w")

    text_frame = Frame(content, bg=bg_color)
    text_frame.pack(fill="both", expand=True, pady=5)

    text = scrolledtext.ScrolledText(text_frame, height=8, font=("微软雅黑", 9),
                                      wrap="word", bg="white", padx=10, pady=10)
    text.insert("1.0", check_result["changes"] or "常规修复和优化")
    text.config(state="disabled")
    text.pack(side="left", fill="both", expand=True)

    Label(content, text=f"包含 {check_result['files_count']} 个文件",
          font=("微软雅黑", 9), bg=bg_color, fg="#999").pack(pady=(5, 0))

    btn_frame = Frame(content, bg=bg_color)
    btn_frame.pack(fill="x", pady=(15, 0))

    def do_update():
        dialog.destroy()
        success, msg = apply_upgrade()
        if success:
            messagebox.showinfo("升级成功", f"{msg}\n\n请重启程序以应用更改。")
        else:
            messagebox.showerror("升级失败", msg)

    Button(btn_frame, text="立即升级", font=("微软雅黑", 10),
           bg="#2196F3", fg="white", width=15, command=do_update).pack(side="left", padx=5)
    Button(btn_frame, text="暂不升级", font=("微软雅黑", 10),
           bg="#f0f0f0", width=12, command=dialog.destroy).pack(side="right", padx=5)

def auto_check_on_startup(parent):
    """启动时自动检查更新"""
    result = check_for_updates()
    if result["has_update"]:
        dialog = Toplevel(parent)
        dialog.title("自动更新提示")
        dialog.geometry("450x300")
        dialog.resizable(False, False)
        dialog.transient(parent)
        dialog.grab_set()

        try:
            from config import COLORS
            bg_color = COLORS.get("bg_main", "#f5f5f5")
        except Exception:
            bg_color = "#f5f5f5"

        dialog.configure(bg=bg_color)

        content = Frame(dialog, bg=bg_color, padx=30, pady=20)
        content.pack(fill="both", expand=True)

        Label(content, text="检测到新版本", font=("微软雅黑", 16, "bold"),
              bg=bg_color, fg="#FF9800").pack(pady=(0, 15))

        Label(content, text=f"发现新版本 v{result['new_version']}",
              font=("微软雅黑", 12), bg=bg_color, fg="#333").pack(pady=5)

        Label(content, text=f"当前版本 v{result['local_version']}",
              font=("微软雅黑", 10), bg=bg_color, fg="#666").pack()

        info_text = result.get("changes", "") or "包含多项修复和优化"
        text = Text(content, height=6, font=("微软雅黑", 9), wrap="word",
                    bg="white", padx=10, pady=10)
        text.insert("1.0", info_text)
        text.config(state="disabled")
        text.pack(fill="both", expand=True, pady=15)

        btn_frame = Frame(content, bg=bg_color)
        btn_frame.pack(fill="x")

        def do_update():
            dialog.destroy()
            success, msg = apply_upgrade()
            if success:
                messagebox.showinfo("升级成功", f"{msg}\n\n请重启程序。")
            else:
                messagebox.showerror("升级失败", msg)

        Button(btn_frame, text="立即更新", font=("微软雅黑", 10),
               bg="#4CAF50", fg="white", width=12, command=do_update).pack(side="left", padx=5)
        Button(btn_frame, text="下次再说", font=("微软雅黑", 10),
               bg="#f0f0f0", width=12, command=dialog.destroy).pack(side="right", padx=5)

def init_updater():
    """初始化升级模块"""
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    upgrade_base = os.path.join(base_dir, UPGRADE_DIR)

    if not os.path.exists(upgrade_base):
        os.makedirs(upgrade_base, exist_ok=True)

    logger.info(f"[升级] 初始化完成, 升级包目录: {upgrade_base}")
