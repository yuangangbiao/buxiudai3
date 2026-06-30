# -*- coding: utf-8 -*-
"""
机器指纹解锁程序 - 可视化界面 (小尺寸版本)
生成唯一机器指纹，用于软件授权验证
"""

import os
import sys
import hashlib
import platform
import socket
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

APP_NAME = "机器指纹解锁工具"

VALID_CHARS = "0123456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def get_safe_hardware_id(func, fallback: str = "DEFAULT") -> str:
    """安全获取硬件ID，失败时返回默认值"""
    try:
        result = func()
        if result and result.strip() and "UNKNOWN" not in result:
            return result.strip()
    except Exception:
        pass
    return fallback


def calculate_checksum(key_base: str) -> str:
    """计算校验位"""
    total = sum(ord(c) * (i + 1) for i, c in enumerate(key_base))
    return VALID_CHARS[total % len(VALID_CHARS)]


def generate_license_key_from_fingerprint(fingerprint: str, customer_name: str = "") -> str:
    """基于指纹生成许可证密钥"""
    combined = f"{fingerprint}|{customer_name}|PERMANENT"
    hash_val = hashlib.sha256(combined.encode('utf-8')).hexdigest()

    part1 = hash_val[0:4].upper()
    part2 = hash_val[8:12].upper()
    part3 = hash_val[16:20].upper()
    part4 = hash_val[24:28].upper()

    key_base = f"{part1}{part2}{part3}{part4}"
    checksum = calculate_checksum(key_base)

    return f"YGB-{part1}-{part2}-{part3}-{part4}-{checksum}"


WINDOW_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".window_config.ini")


def save_window_config(width, height, x, y):
    """保存窗口配置"""
    try:
        with open(WINDOW_CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write(f"{width}\n{height}\n{x}\n{y}")
    except Exception:
        pass


def load_window_config():
    """加载窗口配置"""
    try:
        if os.path.exists(WINDOW_CONFIG_FILE):
            with open(WINDOW_CONFIG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if len(lines) >= 4:
                width = int(lines[0].strip())
                height = int(lines[1].strip())
                x = int(lines[2].strip())
                y = int(lines[3].strip())
                return width, height, x, y
    except Exception:
        pass
    return None, None, None, None


def get_cpu_id() -> str:
    """获取CPU ID"""
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["wmic", "cpu", "get", "ProcessorId"],
                capture_output=True, text=True, timeout=5
            )
            lines = result.stdout.strip().split("\n")
            if len(lines) >= 2:
                cpu_id = lines[-1].strip()
                if cpu_id:
                    return cpu_id
    except Exception:
        pass
    return "CPU_UNKNOWN"


def get_disk_serial() -> str:
    """获取系统盘序列号"""
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["wmic", "diskdrive", "get", "SerialNumber"],
                capture_output=True, text=True, timeout=5
            )
            lines = result.stdout.strip().split("\n")
            if len(lines) >= 2:
                serial = lines[-1].strip()
                if serial:
                    return serial
    except Exception:
        pass
    return "DISK_UNKNOWN"


def get_motherboard_serial() -> str:
    """获取主板序列号"""
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["wmic", "baseboard", "get", "SerialNumber"],
                capture_output=True, text=True, timeout=5
            )
            lines = result.stdout.strip().split("\n")
            if len(lines) >= 2:
                serial = lines[-1].strip()
                if serial and serial != "SerialNumber":
                    return serial
    except Exception:
        pass
    return "MB_UNKNOWN"


def get_bios_serial() -> str:
    """获取BIOS序列号"""
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["wmic", "bios", "get", "SerialNumber"],
                capture_output=True, text=True, timeout=5
            )
            lines = result.stdout.strip().split("\n")
            if len(lines) >= 2:
                serial = lines[-1].strip()
                if serial and serial != "SerialNumber":
                    return serial
    except Exception:
        pass
    return "BIOS_UNKNOWN"


def generate_fingerprint() -> str:
    """生成机器指纹"""
    components = [
        get_safe_hardware_id(get_cpu_id, "CPU_DEFAULT"),
        get_safe_hardware_id(get_disk_serial, "DISK_DEFAULT"),
        get_safe_hardware_id(get_motherboard_serial, "MB_DEFAULT"),
        get_safe_hardware_id(get_bios_serial, "BIOS_DEFAULT"),
    ]
    combined = "|".join(components)
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()


def generate_short_fingerprint() -> str:
    """生成短格式指纹（8位）"""
    return generate_fingerprint()[:8].upper()


def get_all_hardware_info() -> dict:
    """获取完整的硬件信息"""
    return {
        "fingerprint": generate_fingerprint(),
        "fingerprint_short": generate_short_fingerprint(),
        "cpu_id": get_cpu_id(),
        "disk_serial": get_disk_serial(),
        "motherboard_serial": get_motherboard_serial(),
        "bios_serial": get_bios_serial(),
        "machine_name": socket.gethostname(),
    }


def save_fingerprint_to_file():
    """保存指纹到本地文件"""
    fp = generate_fingerprint()
    fp_short = generate_short_fingerprint()

    security_dir = os.path.dirname(os.path.abspath(__file__))
    save_path = os.path.join(security_dir, "my_fingerprint.txt")

    with open(save_path, "w", encoding="utf-8") as f:
        f.write(f"完整指纹:\n{fp}\n\n")
        f.write(f"短指纹:\n{fp_short}\n\n")
        f.write(f"生成时间:\n{datetime.now().isoformat()}\n\n")
        f.write("\n硬件信息:\n")
        info = get_all_hardware_info()
        for k, v in info.items():
            f.write(f"  {k}: {v}\n")

    return save_path


class LicenseActivationGUI:
    """许可证激活GUI"""

    ACTIVATION_FILE = ".activation_status"

    def __init__(self):
        self.root = tk.Toplevel()
        self.root.title("许可证激活")
        self.root.geometry("160x150")
        self.root.configure(bg="#1a1a2e")
        self.root.resizable(True, True)
        self.root.transient()
        self.root.grab_set()

        self.widgets = {}
        self.font_sizes = {}

        self._center_window()
        self._setup_ui()
        self._load_status()

        self.root.bind("<Configure>", self._on_window_resize)

    def _center_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _on_window_resize(self, event):
        if event.widget == self.root:
            self._update_font_sizes()

    def _calculate_font_size(self, base_size, window_width):
        scale_factor = window_width / 160.0
        scale_factor = max(0.6, min(scale_factor, 1.5))
        new_size = int(base_size * scale_factor)
        return max(4, min(12, new_size))

    def _update_font_sizes(self):
        try:
            self.root.update_idletasks()
            window_width = self.root.winfo_width()

            for widget_key in self.widgets:
                widget = self.widgets[widget_key]
                base_size = self.font_sizes[widget_key]
                new_size = self._calculate_font_size(base_size, window_width)
                
                current_font = widget.cget("font")
                if isinstance(current_font, tuple):
                    family = current_font[0]
                    weight = current_font[2] if len(current_font) > 2 else "normal"
                    widget.config(font=(family, new_size, weight))
                else:
                    try:
                        font_parts = str(current_font).split()
                        if len(font_parts) >= 2:
                            family = font_parts[0]
                            weight = " ".join(font_parts[2:]) if len(font_parts) > 2 else "normal"
                            widget.config(font=(family, new_size, weight))
                    except Exception as e:
                        print(f"[指纹解锁] 调整字体大小失败: {e}")
        except Exception as e:
            print(f"[指纹解锁] 递归调整字体失败: {e}")

    def _setup_ui(self):
        header_frame = tk.Frame(self.root, bg="#16213e", padx=5, pady=3)
        header_frame.pack(fill=tk.X)

        key_label = tk.Label(header_frame, text="🔑",
                          font=("Microsoft YaHei", 8),
                          bg="#16213e", fg="#00d4ff")
        key_label.pack(side=tk.LEFT, padx=(0, 3))
        self.widgets["key_label"] = key_label
        self.font_sizes["key_label"] = 8

        title_frame = tk.Frame(header_frame, bg="#16213e")
        title_frame.pack(side=tk.LEFT)

        title_label = tk.Label(title_frame, text="许可证激活",
                              font=("Microsoft YaHei", 6, "bold"),
                              bg="#16213e", fg="#00d4ff")
        title_label.pack(anchor="w")
        self.widgets["title_label"] = title_label
        self.font_sizes["title_label"] = 6

        subtitle_label = tk.Label(title_frame, text="输入许可证密钥进行激活",
                                font=("Microsoft YaHei", 4),
                                bg="#16213e", fg="#4a7fa5")
        subtitle_label.pack(anchor="w")
        self.widgets["subtitle_label"] = subtitle_label
        self.font_sizes["subtitle_label"] = 4

        canvas = tk.Canvas(self.root, bg="#1a1a2e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        self.scroll_frame = tk.Frame(canvas, bg="#1a1a2e")

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=3)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=3)

        card_frame = tk.Frame(self.scroll_frame, bg="#1a1a2e")
        card_frame.pack(fill=tk.BOTH, expand=True)

        status_card = tk.Frame(card_frame, bg="#16213e")
        status_card.pack(fill=tk.X, pady=(0, 3))

        status_header = tk.Label(status_card, text="📊 当前状态",
                            font=("Microsoft YaHei", 4, "bold"),
                            bg="#16213e", fg="#00d4ff")
        status_header.pack(anchor="w", padx=5, pady=(3, 2))
        self.widgets["status_header"] = status_header
        self.font_sizes["status_header"] = 4

        self.status_label = tk.Label(status_card, text="检查中...",
                                    font=("Microsoft YaHei", 4),
                                    bg="#16213e", fg="#888888", wraplength=140, justify="left")
        self.status_label.pack(anchor="w", padx=5, pady=(0, 3))
        self.widgets["status_label"] = self.status_label
        self.font_sizes["status_label"] = 4

        input_card = tk.Frame(card_frame, bg="#16213e")
        input_card.pack(fill=tk.X, pady=(0, 3))

        input_header = tk.Label(input_card, text="🔐 激活信息",
                              font=("Microsoft YaHei", 4, "bold"),
                              bg="#16213e", fg="#00d4ff")
        input_header.pack(anchor="w", padx=5, pady=(3, 2))
        self.widgets["input_header"] = input_header
        self.font_sizes["input_header"] = 4

        input_inner = tk.Frame(input_card, bg="#16213e")
        input_inner.pack(fill=tk.X, padx=5, pady=(0, 3))

        license_key_label = tk.Label(input_inner, text="许可证密钥:",
                                    font=("Microsoft YaHei", 4),
                                    bg="#16213e", fg="#e0e0e0", width=10, anchor="w")
        license_key_label.grid(row=0, column=0, pady=2, sticky="w")
        self.widgets["license_key_label"] = license_key_label
        self.font_sizes["license_key_label"] = 4

        self.license_var = tk.StringVar()
        license_entry = ttk.Entry(input_inner, textvariable=self.license_var, width=12, font=("Consolas", 4))
        license_entry.grid(row=0, column=1, pady=2, padx=(3, 0), sticky="w")
        license_entry.focus()
        self.widgets["license_entry"] = license_entry
        self.font_sizes["license_entry"] = 4

        customer_label = tk.Label(input_inner, text="客户名称:",
                            font=("Microsoft YaHei", 4),
                            bg="#16213e", fg="#e0e0e0", width=10, anchor="w")
        customer_label.grid(row=1, column=0, pady=2, sticky="w")
        self.widgets["customer_label"] = customer_label
        self.font_sizes["customer_label"] = 4

        self.customer_var = tk.StringVar()
        customer_entry = ttk.Entry(input_inner, textvariable=self.customer_var, width=12, font=("Microsoft YaHei", 4))
        customer_entry.grid(row=1, column=1, pady=2, padx=(3, 0), sticky="w")
        self.widgets["customer_entry"] = customer_entry
        self.font_sizes["customer_entry"] = 4

        format_label = tk.Label(input_inner, text="格式: YGB-XXXX-XXXX-XXXX-XXXX",
                              font=("Microsoft YaHei", 3),
                              bg="#16213e", fg="#666666")
        format_label.grid(row=2, column=1, padx=(3, 0), sticky="w")
        self.widgets["format_label"] = format_label
        self.font_sizes["format_label"] = 3

        btn_frame = tk.Frame(card_frame, bg="#1a1a2e")
        btn_frame.pack(fill=tk.X)

        self.activate_btn = tk.Button(btn_frame, text="✅ 激活",
                                     font=("Microsoft YaHei", 4, "bold"),
                                     bg="#27ae60", fg="white",
                                     relief=tk.FLAT, cursor="hand2",
                                     padx=6, pady=2,
                                     command=self._do_activate)
        self.activate_btn.pack(side=tk.LEFT, padx=(0, 3))
        self.widgets["activate_btn"] = self.activate_btn
        self.font_sizes["activate_btn"] = 4

        self.deactivate_btn = tk.Button(btn_frame, text="❌ 解除激活",
                                       font=("Microsoft YaHei", 4),
                                       bg="#e74c3c", fg="white",
                                       relief=tk.FLAT, cursor="hand2",
                                       padx=6, pady=2,
                                       command=self._do_deactivate)
        self.deactivate_btn.pack(side=tk.LEFT, padx=(0, 3))
        self.widgets["deactivate_btn"] = self.deactivate_btn
        self.font_sizes["deactivate_btn"] = 4

        close_btn = tk.Button(btn_frame, text="关闭",
                 font=("Microsoft YaHei", 4),
                 bg="#555555", fg="white",
                 relief=tk.FLAT, cursor="hand2",
                 padx=6, pady=2,
                 command=self.root.destroy)
        close_btn.pack(side=tk.RIGHT)
        self.widgets["close_btn"] = close_btn
        self.font_sizes["close_btn"] = 4

    def _load_status(self):
        try:
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from security.license_manager import LicenseManager

            manager = LicenseManager()
            status = manager.check_activation()

            if status["is_activated"]:
                self.status_label.config(
                    text=f"✅ 已激活\n"
                         f"机器指纹: {status.get('fingerprint_short', '')}\n"
                         f"许可证: {status.get('bound_license_key', '')}\n"
                         f"客户: {status.get('bound_customer', '')}\n"
                         f"绑定时间: {status.get('bound_at', '')}",
                    fg="#27ae60"
                )
                self.license_var.set("")
                self.customer_var.set("")
            else:
                self.status_label.config(
                    text=f"❌ 未激活\n原因: {status.get('message', '未知')}\n"
                         f"当前机器指纹: {status.get('fingerprint_short', '')}",
                    fg="#e74c3c"
                )
        except Exception as e:
            self.status_label.config(text=f"状态检查失败: {str(e)}", fg="#e74c3c")

    def _do_activate(self):
        license_key = self.license_var.get().strip().upper()
        customer_name = self.customer_var.get().strip()

        if not license_key:
            messagebox.showwarning("输入错误", "请输入许可证密钥")
            return

        try:
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from security.license_manager import LicenseManager

            manager = LicenseManager()
            result = manager.activate(license_key, customer_name)

            if result["success"]:
                messagebox.showinfo("激活成功", f"许可证激活成功!\n\n机器指纹: {result.get('fingerprint_short', '')}")
                self._load_status()
                self.license_var.set("")
                self.customer_var.set("")
            else:
                messagebox.showerror("激活失败", result.get("message", "未知错误"))
        except Exception as e:
            messagebox.showerror("激活失败", str(e))

    def _do_deactivate(self):
        if not messagebox.askyesno("确认解除", "确定要解除当前激活吗？\n解除后可以重新激活到其他电脑。"):
            return

        try:
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from security.license_manager import LicenseManager

            manager = LicenseManager()
            result = manager.deactivate()

            if result["success"]:
                messagebox.showinfo("解除成功", result.get("message", "已解除激活"))
                self._load_status()
            else:
                messagebox.showerror("解除失败", result.get("message", "未知错误"))
        except Exception as e:
            messagebox.showerror("解除失败", str(e))


class FingerprintUnlockGUI:
    """机器指纹解锁工具GUI"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME}")
        self.root.minsize(300, 280)
        self.root.configure(bg="#1a1a2e")
        self.root.resizable(True, True)

        saved_width, saved_height, saved_x, saved_y = load_window_config()
        if saved_width and saved_height:
            if saved_x is not None and saved_y is not None:
                self.root.geometry(f"{saved_width}x{saved_height}+{saved_x}+{saved_y}")
            else:
                self.root.geometry(f"{saved_width}x{saved_height}")
        else:
            self.root.geometry("160x150")
            self.root.update_idletasks()
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            x = (screen_width - 160) // 2
            y = (screen_height - 150) // 2
            self.root.geometry(f"160x150+{x}+{y}")

        self.widgets = {}
        self.font_sizes = {}

        self.root.bind("<Configure>", self._on_window_config_change)

        self._setup_ui()
        self._load_fingerprint()

    def _on_window_config_change(self, event):
        if event.widget == self.root:
            self.root.update_idletasks()
            geom = self.root.geometry()
            parts = geom.split("+")
            if len(parts) == 3:
                size_part = parts[0]
                x_part = parts[1]
                y_part = parts[2]
                if "x" in size_part:
                    wh = size_part.split("x")
                    width = int(wh[0])
                    height = int(wh[1])
                    x = int(x_part)
                    y = int(y_part)
                    save_window_config(width, height, x, y)
            self._update_font_sizes()

    def _calculate_font_size(self, base_size, window_width):
        scale_factor = window_width / 160.0
        scale_factor = max(0.6, min(scale_factor, 1.5))
        new_size = int(base_size * scale_factor)
        return max(4, min(12, new_size))

    def _update_font_sizes(self):
        try:
            self.root.update_idletasks()
            window_width = self.root.winfo_width()

            for widget_key in self.widgets:
                widget = self.widgets[widget_key]
                base_size = self.font_sizes[widget_key]
                new_size = self._calculate_font_size(base_size, window_width)
                
                current_font = widget.cget("font")
                if isinstance(current_font, tuple):
                    family = current_font[0]
                    weight = current_font[2] if len(current_font) > 2 else "normal"
                    widget.config(font=(family, new_size, weight))
                else:
                    try:
                        font_parts = str(current_font).split()
                        if len(font_parts) >= 2:
                            family = font_parts[0]
                            weight = " ".join(font_parts[2:]) if len(font_parts) > 2 else "normal"
                            widget.config(font=(family, new_size, weight))
                    except Exception as e:
                        print(f"[指纹解锁] 调整字体大小失败: {e}")
        except Exception as e:
            print(f"[指纹解锁] 递归调整字体失败: {e}")

    def _setup_ui(self):
        main_container = tk.Frame(self.root, bg="#1a1a2e")
        main_container.pack(fill=tk.BOTH, expand=True)

        left_canvas = tk.Canvas(main_container, bg="#1a1a2e", highlightthickness=0)
        left_scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=left_canvas.yview)
        left_scroll_frame = tk.Frame(left_canvas, bg="#1a1a2e", width=280)

        left_scroll_frame.bind(
            "<Configure>",
            lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all"))
        )

        left_canvas.create_window((0, 0), window=left_scroll_frame, anchor="nw")
        left_canvas.configure(yscrollcommand=left_scrollbar.set)

        left_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left_scrollbar.pack(side=tk.LEFT, fill=tk.Y)

        right_frame = tk.Frame(main_container, bg="#16213e", width=150)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)
        right_frame.pack_propagate(False)

        self._setup_left_panel(left_scroll_frame)
        self._setup_right_panel(right_frame)

    def _setup_left_panel(self, parent):
        header_frame = tk.Frame(parent, bg="#16213e", padx=8, pady=6)
        header_frame.pack(fill=tk.X)

        key_icon = tk.Label(header_frame, text="🔐",
                font=("Microsoft YaHei", 12),
                bg="#16213e", fg="#00d4ff")
        key_icon.pack(side=tk.LEFT, padx=(0, 4))
        self.widgets["key_icon"] = key_icon
        self.font_sizes["key_icon"] = 12

        title_frame = tk.Frame(header_frame, bg="#16213e")
        title_frame.pack(side=tk.LEFT)

        title_label = tk.Label(title_frame, text=APP_NAME,
                font=("Microsoft YaHei", 8, "bold"),
                bg="#16213e", fg="#00d4ff")
        title_label.pack(anchor="w")
        self.widgets["title_label"] = title_label
        self.font_sizes["title_label"] = 8

        subtitle_label = tk.Label(title_frame, text="生成唯一机器标识，用于软件授权",
                font=("Microsoft YaHei", 4),
                bg="#16213e", fg="#4a7fa5")
        subtitle_label.pack(anchor="w")
        self.widgets["subtitle_label"] = subtitle_label
        self.font_sizes["subtitle_label"] = 4

        card_frame = tk.Frame(parent, bg="#1a1a2e", padx=8, pady=4)
        card_frame.pack(fill=tk.BOTH, expand=True)

        fingerprint_card = tk.Frame(card_frame, bg="#16213e", bd=0, relief=tk.FLAT)
        fingerprint_card.pack(fill=tk.X, pady=(0, 6))

        fp_header = tk.Label(fingerprint_card, text="📋 机器指纹",
                font=("Microsoft YaHei", 6, "bold"),
                bg="#16213e", fg="#00d4ff")
        fp_header.pack(anchor="w", padx=8, pady=(6, 4))
        self.widgets["fp_header"] = fp_header
        self.font_sizes["fp_header"] = 6

        self.fp_label = tk.Label(fingerprint_card, text="正在获取...",
                                 font=("Consolas", 5),
                                 bg="#16213e", fg="#00ff88", wraplength=260, justify="left")
        self.fp_label.pack(anchor="w", padx=8, pady=(0, 6))
        self.widgets["fp_label"] = self.fp_label
        self.font_sizes["fp_label"] = 5

        short_card = tk.Frame(card_frame, bg="#16213e", bd=0, relief=tk.FLAT)
        short_card.pack(fill=tk.X, pady=(0, 6))

        short_header = tk.Label(short_card, text="🔑 短指纹（8位）",
                font=("Microsoft YaHei", 6, "bold"),
                bg="#16213e", fg="#00d4ff")
        short_header.pack(anchor="w", padx=8, pady=(6, 4))
        self.widgets["short_header"] = short_header
        self.font_sizes["short_header"] = 6

        self.short_fp_label = tk.Label(short_card, text="正在获取...",
                                       font=("Consolas", 10, "bold"),
                                       bg="#16213e", fg="#ffcc00")
        self.short_fp_label.pack(anchor="w", padx=8, pady=(0, 6))
        self.widgets["short_fp_label"] = self.short_fp_label
        self.font_sizes["short_fp_label"] = 10

        activation_status_card = tk.Frame(card_frame, bg="#16213e", bd=0, relief=tk.FLAT)
        activation_status_card.pack(fill=tk.X, pady=(0, 6))

        activation_header = tk.Label(activation_status_card, text="📊 许可证状态",
                font=("Microsoft YaHei", 6, "bold"),
                bg="#16213e", fg="#00d4ff")
        activation_header.pack(anchor="w", padx=8, pady=(6, 4))
        self.widgets["activation_header"] = activation_header
        self.font_sizes["activation_header"] = 6

        self.activation_label = tk.Label(activation_status_card, text="检查中...",
                                         font=("Microsoft YaHei", 5),
                                         bg="#16213e", fg="#888888", wraplength=260, justify="left")
        self.activation_label.pack(anchor="w", padx=8, pady=(0, 6))
        self.widgets["activation_label"] = self.activation_label
        self.font_sizes["activation_label"] = 5

        hardware_card = tk.Frame(card_frame, bg="#16213e", bd=0, relief=tk.FLAT)
        hardware_card.pack(fill=tk.X, pady=(0, 6))

        hw_header = tk.Label(hardware_card, text="🖥️ 硬件信息",
                font=("Microsoft YaHei", 6, "bold"),
                bg="#16213e", fg="#00d4ff")
        hw_header.pack(anchor="w", padx=8, pady=(6, 4))
        self.widgets["hw_header"] = hw_header
        self.font_sizes["hw_header"] = 6

        info_frame = tk.Frame(hardware_card, bg="#16213e")
        info_frame.pack(fill=tk.X, padx=8, pady=(0, 6))

        self.info_labels = {}
        info_items = [
            ("cpu_id", "CPU ID"),
            ("disk_serial", "系统盘序列号"),
            ("motherboard_serial", "主板序列号"),
            ("bios_serial", "BIOS序列号"),
            ("machine_name", "计算机名"),
        ]

        for i, (key, label_text) in enumerate(info_items):
            item_frame = tk.Frame(info_frame, bg="#16213e")
            item_frame.grid(row=i, column=0, padx=2, pady=3, sticky="w")

            tk.Label(item_frame, text=f"{label_text}:",
                    font=("Microsoft YaHei", 4),
                    bg="#16213e", fg="#888888", width=16, anchor="w").grid(row=0, column=0, sticky="w")

            value_label = tk.Label(item_frame, text="获取中...",
                                   font=("Consolas", 4),
                                   bg="#16213e", fg="#e0e0e0", anchor="w")
            value_label.grid(row=0, column=1, sticky="w")
            self.info_labels[key] = value_label

        button_card = tk.Frame(card_frame, bg="#16213e", bd=0, relief=tk.FLAT)
        button_card.pack(fill=tk.X, pady=(0, 6))

        btn_frame = tk.Frame(button_card, bg="#16213e")
        btn_frame.pack(fill=tk.X, padx=8, pady=6)

        self.save_btn = tk.Button(btn_frame, text="💾 保存指纹",
                                  font=("Microsoft YaHei", 5),
                                  bg="#27ae60", fg="white",
                                  relief=tk.FLAT, cursor="hand2",
                                  padx=6, pady=3,
                                  command=self._save_fingerprint)
        self.save_btn.pack(side=tk.LEFT, padx=(0, 3))
        self.widgets["save_btn"] = self.save_btn
        self.font_sizes["save_btn"] = 5

        self.refresh_btn = tk.Button(btn_frame, text="🔄 刷新",
                                     font=("Microsoft YaHei", 5),
                                     bg="#3498db", fg="white",
                                     relief=tk.FLAT, cursor="hand2",
                                     padx=6, pady=3,
                                     command=self._load_fingerprint)
        self.refresh_btn.pack(side=tk.LEFT, padx=(0, 3))
        self.widgets["refresh_btn"] = self.refresh_btn
        self.font_sizes["refresh_btn"] = 5

        self.copy_btn = tk.Button(btn_frame, text="📋 复制指纹",
                                  font=("Microsoft YaHei", 5),
                                  bg="#9b59b6", fg="white",
                                  relief=tk.FLAT, cursor="hand2",
                                  padx=6, pady=3,
                                  command=self._copy_fingerprint)
        self.copy_btn.pack(side=tk.LEFT)
        self.widgets["copy_btn"] = self.copy_btn
        self.font_sizes["copy_btn"] = 5

        activate_btn_frame = tk.Frame(button_card, bg="#16213e")
        activate_btn_frame.pack(fill=tk.X, padx=8, pady=(0, 6))

        self.activate_btn = tk.Button(activate_btn_frame, text="🔑 许可证激活",
                                     font=("Microsoft YaHei", 5, "bold"),
                                     bg="#e67e22", fg="white",
                                     relief=tk.FLAT, cursor="hand2",
                                     padx=8, pady=4,
                                     command=self._open_activation)
        self.activate_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
        self.widgets["activate_btn"] = self.activate_btn
        self.font_sizes["activate_btn"] = 5

        self.gen_key_btn = tk.Button(activate_btn_frame, text="🔐 生成密钥",
                                     font=("Microsoft YaHei", 5, "bold"),
                                     bg="#27ae60", fg="white",
                                     relief=tk.FLAT, cursor="hand2",
                                     padx=8, pady=4,
                                     command=self._generate_key)
        self.gen_key_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.widgets["gen_key_btn"] = self.gen_key_btn
        self.font_sizes["gen_key_btn"] = 5

        self.gen_key_result = tk.Label(button_card, text="",
                                      font=("Consolas", 4),
                                      bg="#16213e", fg="#00ff88")
        self.gen_key_result.pack(anchor="w", padx=8, pady=(2, 0))
        self.widgets["gen_key_result"] = self.gen_key_result
        self.font_sizes["gen_key_result"] = 4

        status_frame = tk.Frame(card_frame, bg="#16213e", bd=0, relief=tk.FLAT)
        status_frame.pack(fill=tk.X)

        self.status_label = tk.Label(status_frame, text="",
                                     font=("Microsoft YaHei", 4),
                                     bg="#16213e", fg="#888888")
        self.status_label.pack(anchor="w", padx=8, pady=6)
        self.widgets["status_label"] = self.status_label
        self.font_sizes["status_label"] = 4

    def _setup_right_panel(self, parent):
        guide_header = tk.Label(parent, text="📖 使用说明",
                font=("Microsoft YaHei", 7, "bold"),
                bg="#16213e", fg="#00d4ff")
        guide_header.pack(anchor="w", padx=8, pady=(8, 6))
        self.widgets["guide_header"] = guide_header
        self.font_sizes["guide_header"] = 7

        guide_text = """【机器指纹】
机器指纹是通过获取电脑硬件信息生成的唯一标识符，用于软件授权。
【指纹组成】
• CPU ID
• 硬盘序列号
• 主板序列号
• BIOS序列号
【使用方法】
1. 查看指纹：打开软件自动显示当前机器指纹
2. 保存指纹：点击"保存指纹"按钮保存到文件
3. 复制指纹：点击"复制指纹"按钮复制到剪贴板
4. 刷新指纹：点击"刷新"按钮重新获取硬件信息
【生成密钥】
点击"生成密钥"按钮，基于当前机器指纹直接生成许可证密钥
【许可证激活】
1. 将机器指纹或密钥发送给销售人员
2. 销售人员提供激活码（如需）
3. 点击"许可证激活"按钮
4. 输入密钥完成激活
【密钥格式】
YGB-XXXX-XXXX-XXXX-XXXX-X
(最后一位为校验位)"""

        guide_label = tk.Label(parent, text=guide_text,
                font=("Microsoft YaHei", 4),
                bg="#16213e", fg="#cccccc", wraplength=130,
                justify="left", anchor="nw")
        guide_label.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self.widgets["guide_label"] = guide_label
        self.font_sizes["guide_label"] = 4

    def _load_fingerprint(self):
        self.status_label.config(text="正在获取硬件信息...", fg="#888888")
        self.root.update()

        try:
            info = get_all_hardware_info()

            self.fp_label.config(text=info['fingerprint'])
            self.short_fp_label.config(text=info['fingerprint_short'])

            for key, label in self.info_labels.items():
                label.config(text=info.get(key, "未知"))

            self.status_label.config(text=f"获取成功 - {datetime.now().strftime('%H:%M:%S')}", fg="#27ae60")

            self._load_activation_status()
        except Exception as e:
            self.status_label.config(text=f"获取失败: {str(e)}", fg="#e74c3c")

    def _load_activation_status(self):
        try:
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from security.license_manager import LicenseManager

            manager = LicenseManager()
            status = manager.check_activation()

            if status["is_activated"]:
                self.activation_label.config(
                    text=f"✅ 已激活\n"
                         f"许可证: {status.get('bound_license_key', '')}\n"
                         f"客户: {status.get('bound_customer', '')}\n"
                         f"绑定时间: {status.get('bound_at', '')}",
                    fg="#27ae60"
                )
                self.activate_btn.config(text="🔑 已激活 (点击修改)", bg="#27ae60")
            else:
                self.activation_label.config(
                    text=f"❌ 未激活\n原因: {status.get('message', '未知')}",
                    fg="#e74c3c"
                )
                self.activate_btn.config(text="🔑 许可证激活", bg="#e67e22")
        except Exception as e:
            self.activation_label.config(text=f"状态检查失败: {str(e)}", fg="#e74c3c")

    def _save_fingerprint(self):
        try:
            save_path = save_fingerprint_to_file()
            self.status_label.config(text=f"已保存到: {save_path}", fg="#27ae60")
            messagebox.showinfo("保存成功", f"指纹已保存到:\n{save_path}")
        except Exception as e:
            self.status_label.config(text=f"保存失败: {str(e)}", fg="#e74c3c")
            messagebox.showerror("保存失败", str(e))

    def _copy_fingerprint(self):
        try:
            fp = generate_fingerprint()
            self.root.clipboard_clear()
            self.root.clipboard_append(fp)
            self.status_label.config(text="已复制到剪贴板!", fg="#27ae60")
            messagebox.showinfo("复制成功", "完整指纹已复制到剪贴板")
        except Exception as e:
            self.status_label.config(text=f"复制失败: {str(e)}", fg="#e74c3c")
            messagebox.showerror("复制失败", str(e))

    def _generate_key(self):
        """基于当前指纹生成许可证密钥"""
        try:
            fp = generate_fingerprint()
            key = generate_license_key_from_fingerprint(fp, "")
            self.gen_key_result.config(text=f"✅ {key}", fg="#27ae60")
            self.root.clipboard_clear()
            self.root.clipboard_append(key)
            messagebox.showinfo("生成成功", f"许可证密钥已生成并复制到剪贴板:\n\n{key}")
        except Exception as e:
            self.gen_key_result.config(text=f"❌ 生成失败: {str(e)}", fg="#e74c3c")

    def _open_activation(self):
        LicenseActivationGUI()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    gui = FingerprintUnlockGUI()
    gui.run()