# -*- coding: utf-8 -*-
"""
许可证激活算法可视化软件
用于生成和验证许可证密钥
"""

import os
import sys
import hashlib
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import random
import string

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

APP_NAME = "许可证激活算法工具"

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


def generate_fingerprint() -> str:
    """生成机器指纹"""
    import subprocess
    import platform

    def get_cpu_id():
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["wmic", "cpu", "get", "ProcessorId"],
                    capture_output=True, text=True, timeout=5
                )
                lines = result.stdout.strip().split("\n")
                if len(lines) >= 2:
                    return lines[-1].strip()
        except Exception:
            pass
        return "CPU_UNKNOWN"

    def get_disk_serial():
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["wmic", "diskdrive", "get", "SerialNumber"],
                    capture_output=True, text=True, timeout=5
                )
                lines = result.stdout.strip().split("\n")
                if len(lines) >= 2:
                    return lines[-1].strip()
        except Exception:
            pass
        return "DISK_UNKNOWN"

    def get_motherboard_serial():
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["wmic", "baseboard", "get", "SerialNumber"],
                    capture_output=True, text=True, timeout=5
                )
                lines = result.stdout.strip().split("\n")
                if len(lines) >= 2:
                    return lines[-1].strip()
        except Exception:
            pass
        return "MB_UNKNOWN"

    def get_bios_serial():
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["wmic", "bios", "get", "SerialNumber"],
                    capture_output=True, text=True, timeout=5
                )
                lines = result.stdout.strip().split("\n")
                if len(lines) >= 2:
                    return lines[-1].strip()
        except Exception:
            pass
        return "BIOS_UNKNOWN"

    components = [
        get_safe_hardware_id(get_cpu_id, "CPU_DEFAULT"),
        get_safe_hardware_id(get_disk_serial, "DISK_DEFAULT"),
        get_safe_hardware_id(get_motherboard_serial, "MB_DEFAULT"),
        get_safe_hardware_id(get_bios_serial, "BIOS_DEFAULT"),
    ]
    combined = "|".join(components)
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()


def calculate_checksum(key_base: str) -> str:
    """计算校验位"""
    total = sum(ord(c) * (i + 1) for i, c in enumerate(key_base))
    return VALID_CHARS[total % len(VALID_CHARS)]


def generate_license_key(fingerprint: str, customer_name: str = "", valid_days: int = 0) -> str:
    """
    基于指纹生成许可证密钥
    valid_days: 有效天数，0表示永久
    """
    if valid_days > 0:
        combined = f"{fingerprint}|{customer_name}|DAYS:{valid_days}"
    else:
        combined = f"{fingerprint}|{customer_name}|PERMANENT"
    hash_val = hashlib.sha256(combined.encode('utf-8')).hexdigest()

    part1 = hash_val[0:4].upper()
    part2 = hash_val[8:12].upper()
    part3 = hash_val[16:20].upper()
    part4 = hash_val[24:28].upper()

    key_base = f"{part1}{part2}{part3}{part4}"
    checksum = calculate_checksum(key_base)

    return f"YGB-{part1}-{part2}-{part3}-{part4}-{checksum}"


def validate_license_key_format(key: str) -> bool:
    """验证许可证密钥格式"""
    if not key:
        return False
    key = key.strip().upper()
    if not key.startswith("YGB-"):
        return False
    parts = key.split("-")
    if len(parts) != 6:
        return False
    for i, part in enumerate(parts):
        if i == 0:
            if part != "YGB":
                return False
        elif i == 5:
            if len(part) != 1:
                return False
            if part not in VALID_CHARS:
                return False
        else:
            if len(part) != 4:
                return False
            if not all(c in VALID_CHARS for c in part):
                return False
    return True


def verify_license_key(key: str, fingerprint: str, customer_name: str = "", valid_days: int = 0) -> dict:
    """验证许可证密钥"""
    if not validate_license_key_format(key):
        return {"valid": False, "message": "密钥格式无效"}

    key = key.strip().upper()
    parts = key.split("-")
    key_base = f"{parts[1]}{parts[2]}{parts[3]}{parts[4]}"
    expected_checksum = calculate_checksum(key_base)

    if parts[5] != expected_checksum:
        return {"valid": False, "message": "密钥校验失败"}

    expected_key = generate_license_key(fingerprint, customer_name, valid_days)

    if key == expected_key.upper():
        return {"valid": True, "message": "密钥有效", "match": True, "valid_days": valid_days}
    else:
        return {"valid": True, "message": "密钥格式正确但与当前指纹不匹配", "match": False}


def get_log_path():
    """获取许可证记录文件路径"""
    security_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(security_dir, "license_generated_records.txt")


def get_computer_log_path():
    """获取电脑记录文件路径"""
    security_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(security_dir, "computer_records.txt")


def save_license_record(key: str, fingerprint: str, customer_name: str, success: bool):
    """保存许可证生成记录"""
    try:
        log_path = get_log_path()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(log_path, "a", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write(f"生成时间: {timestamp}\n")
            f.write(f"许可证密钥: {key}\n")
            f.write(f"机器指纹: {fingerprint}\n")
            f.write(f"短指纹: {fingerprint[:8].upper()}\n")
            f.write(f"客户名称: {customer_name or '未填写'}\n")
            f.write(f"生成结果: {'成功' if success else '失败'}\n")
            f.write("=" * 60 + "\n\n")

        return log_path
    except Exception:
        return None


def save_computer_record(fingerprint: str, customer_name: str, key: str = ""):
    """保存电脑记录"""
    try:
        log_path = get_computer_log_path()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        existing_records = load_computer_records()

        if fingerprint.upper() in existing_records.upper():
            return None

        with open(log_path, "a", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write(f"首次记录时间: {timestamp}\n")
            f.write(f"机器指纹: {fingerprint}\n")
            f.write(f"短指纹: {fingerprint[:8].upper()}\n")
            f.write(f"客户名称: {customer_name or '未填写'}\n")
            if key:
                f.write(f"生成的许可证: {key}\n")
            f.write("=" * 60 + "\n\n")

        return log_path
    except Exception:
        return None


def load_computer_records():
    """加载电脑记录"""
    try:
        log_path = get_computer_log_path()
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""
    except Exception:
        return ""


def load_license_records():
    """加载许可证记录"""
    try:
        log_path = get_log_path()
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""
    except Exception:
        return ""


class LicenseGeneratorGUI:
    """许可证生成器GUI主窗口"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME}")
        self.root.geometry("550x650")
        self.root.minsize(500, 550)
        self.root.configure(bg="#1a1a2e")
        self.root.resizable(True, True)

        self.fingerprint = ""
        self.use_custom_fingerprint = tk.BooleanVar(value=False)
        self.custom_fingerprint = tk.StringVar(value="")
        self.custom_fp_entry = None
        self.generated_keys = []

        self._setup_ui()
        self._load_fingerprint()

    def _setup_ui(self):
        header_frame = tk.Frame(self.root, bg="#16213e", padx=15, pady=10)
        header_frame.pack(fill=tk.X)

        tk.Label(header_frame, text="🔐",
                font=("Microsoft YaHei", 24),
                bg="#16213e", fg="#00d4ff").pack(side=tk.LEFT, padx=(0, 8))

        title_frame = tk.Frame(header_frame, bg="#16213e")
        title_frame.pack(side=tk.LEFT)

        tk.Label(title_frame, text=APP_NAME,
                font=("Microsoft YaHei", 16, "bold"),
                bg="#16213e", fg="#00d4ff").pack(anchor="w")

        tk.Label(title_frame, text="生成和验证许可证密钥",
                font=("Microsoft YaHei", 9),
                bg="#16213e", fg="#4a7fa5").pack(anchor="w")

        main_canvas = tk.Canvas(self.root, bg="#1a1a2e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=main_canvas.yview)
        scrollable_frame = tk.Frame(main_canvas, bg="#1a1a2e")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )
        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        main_canvas.pack(fill=tk.BOTH, expand=True)

        card_frame = tk.Frame(scrollable_frame, bg="#1a1a2e", padx=15, pady=8)
        card_frame.pack(fill=tk.BOTH, expand=True)

        fp_card = tk.Frame(card_frame, bg="#16213e")
        fp_card.pack(fill=tk.X, pady=(0, 10))

        tk.Label(fp_card, text="🔑 当前机器指纹",
                font=("Microsoft YaHei", 12, "bold"),
                bg="#16213e", fg="#00d4ff").pack(anchor="w", padx=15, pady=(10, 3))

        self.fp_label = tk.Label(fp_card, text="获取中...",
                               font=("Consolas", 9),
                               bg="#16213e", fg="#00ff88", wraplength=500, justify="left")
        self.fp_label.pack(anchor="w", padx=15, pady=(0, 3))

        self.fp_short_label = tk.Label(fp_card, text="",
                                      font=("Consolas", 12, "bold"),
                                      bg="#16213e", fg="#ffcc00")
        self.fp_short_label.pack(anchor="w", padx=15, pady=(0, 10))

        custom_fp_frame = tk.Frame(card_frame, bg="#16213e")
        custom_fp_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(custom_fp_frame, text="📝 自定义机器指纹",
                font=("Microsoft YaHei", 12, "bold"),
                bg="#16213e", fg="#00d4ff").pack(anchor="w", padx=15, pady=(10, 5))

        custom_fp_inner = tk.Frame(custom_fp_frame, bg="#16213e")
        custom_fp_inner.pack(fill=tk.X, padx=15, pady=(0, 10))

        tk.Checkbutton(custom_fp_inner, text="使用自定义指纹",
                      variable=self.use_custom_fingerprint,
                      font=("Microsoft YaHei", 9),
                      bg="#16213e", fg="#e0e0e0",
                      selectcolor="#16213e", activebackground="#16213e",
                      command=self._toggle_custom_fp).grid(row=0, column=0, columnspan=2, pady=3, sticky="w")

        tk.Label(custom_fp_inner, text="指纹:",
                font=("Microsoft YaHei", 9),
                bg="#16213e", fg="#e0e0e0", width=10, anchor="w").grid(row=1, column=0, pady=6, sticky="w")

        custom_fp_entry = ttk.Entry(custom_fp_inner, textvariable=self.custom_fingerprint, width=35, font=("Consolas", 9))
        custom_fp_entry.grid(row=1, column=1, pady=6, padx=(8, 0), sticky="w")
        self.custom_fp_entry = custom_fp_entry
        custom_fp_entry.config(state=tk.DISABLED)

        tk.Button(custom_fp_inner, text="📋 粘贴",
                 font=("Microsoft YaHei", 9),
                 bg="#3498db", fg="white",
                 relief=tk.FLAT, cursor="hand2",
                 padx=10, pady=3,
                 command=self._paste_fingerprint).grid(row=1, column=2, pady=6, padx=(8, 0))

        tk.Button(custom_fp_inner, text="🔄 清空",
                 font=("Microsoft YaHei", 9),
                 bg="#e74c3c", fg="white",
                 relief=tk.FLAT, cursor="hand2",
                 padx=10, pady=3,
                 command=lambda: self.custom_fingerprint.set("")).grid(row=1, column=3, pady=6, padx=(3, 0))

        generate_card = tk.Frame(card_frame, bg="#16213e")
        generate_card.pack(fill=tk.X, pady=(0, 10))

        tk.Label(generate_card, text="📝 生成许可证密钥",
                font=("Microsoft YaHei", 12, "bold"),
                bg="#16213e", fg="#00d4ff").pack(anchor="w", padx=15, pady=(10, 5))

        gen_inner = tk.Frame(generate_card, bg="#16213e")
        gen_inner.pack(fill=tk.X, padx=15, pady=(0, 10))

        tk.Label(gen_inner, text="客户名称:",
                font=("Microsoft YaHei", 9),
                bg="#16213e", fg="#e0e0e0", width=10, anchor="w").grid(row=0, column=0, pady=6, sticky="w")

        self.customer_var = tk.StringVar()
        customer_entry = ttk.Entry(gen_inner, textvariable=self.customer_var, width=28, font=("Microsoft YaHei", 10))
        customer_entry.grid(row=0, column=1, pady=6, padx=(8, 0), sticky="w")

        tk.Label(gen_inner, text="有效天数:",
                font=("Microsoft YaHei", 9),
                bg="#16213e", fg="#e0e0e0", width=10, anchor="w").grid(row=1, column=0, pady=6, sticky="w")

        self.valid_days_var = tk.StringVar(value="0")
        valid_days_entry = ttk.Entry(gen_inner, textvariable=self.valid_days_var, width=28, font=("Microsoft YaHei", 10))
        valid_days_entry.grid(row=1, column=1, pady=6, padx=(8, 0), sticky="w")

        tk.Label(gen_inner, text="(填0表示永久)",
                font=("Microsoft YaHei", 7),
                bg="#16213e", fg="#666666").grid(row=2, column=1, padx=(8, 0), sticky="w")

        tk.Button(gen_inner, text="🎯 生成密钥",
                 font=("Microsoft YaHei", 11, "bold"),
                 bg="#27ae60", fg="white",
                 relief=tk.FLAT, cursor="hand2",
                 padx=15, pady=6,
                 command=self._generate_key).grid(row=3, column=0, columnspan=2, pady=8, sticky="ew")

        self.gen_result_label = tk.Label(generate_card, text="",
                                        font=("Consolas", 10, "bold"),
                                        bg="#16213e", fg="#00ff88", wraplength=500, justify="left")
        self.gen_result_label.pack(anchor="w", padx=15, pady=(0, 10))

        verify_card = tk.Frame(card_frame, bg="#16213e")
        verify_card.pack(fill=tk.X, pady=(0, 10))

        tk.Label(verify_card, text="✅ 验证许可证密钥",
                font=("Microsoft YaHei", 12, "bold"),
                bg="#16213e", fg="#00d4ff").pack(anchor="w", padx=15, pady=(10, 5))

        ver_inner = tk.Frame(verify_card, bg="#16213e")
        ver_inner.pack(fill=tk.X, padx=15, pady=(0, 10))

        tk.Label(ver_inner, text="许可证密钥:",
                font=("Microsoft YaHei", 9),
                bg="#16213e", fg="#e0e0e0", width=10, anchor="w").grid(row=0, column=0, pady=6, sticky="w")

        self.verify_key_var = tk.StringVar()
        verify_entry = ttk.Entry(ver_inner, textvariable=self.verify_key_var, width=30, font=("Consolas", 10))
        verify_entry.grid(row=0, column=1, pady=6, padx=(8, 0), sticky="w")

        tk.Label(ver_inner, text="客户名称:",
                font=("Microsoft YaHei", 9),
                bg="#16213e", fg="#e0e0e0", width=10, anchor="w").grid(row=1, column=0, pady=6, sticky="w")

        self.verify_customer_var = tk.StringVar()
        verify_cust_entry = ttk.Entry(ver_inner, textvariable=self.verify_customer_var, width=28, font=("Microsoft YaHei", 10))
        verify_cust_entry.grid(row=1, column=1, pady=6, padx=(8, 0), sticky="w")

        tk.Button(ver_inner, text="🔍 验证密钥",
                 font=("Microsoft YaHei", 11, "bold"),
                 bg="#3498db", fg="white",
                 relief=tk.FLAT, cursor="hand2",
                 padx=15, pady=6,
                 command=self._verify_key).grid(row=2, column=0, columnspan=2, pady=8, sticky="ew")

        self.ver_result_label = tk.Label(verify_card, text="",
                                        font=("Microsoft YaHei", 10),
                                        bg="#16213e", fg="#888888", wraplength=500, justify="left")
        self.ver_result_label.pack(anchor="w", padx=15, pady=(0, 10))

        history_card = tk.Frame(card_frame, bg="#16213e")
        history_card.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        tk.Label(history_card, text="📋 本次生成的密钥历史",
                font=("Microsoft YaHei", 12, "bold"),
                bg="#16213e", fg="#00d4ff").pack(anchor="w", padx=15, pady=(10, 5))

        list_frame = tk.Frame(history_card, bg="#1a1a2e")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

        self.history_listbox = tk.Listbox(list_frame, font=("Consolas", 9),
                                         bg="#1a1a2e", fg="#00ff88",
                                         selectbackground="#3498db", selectforeground="white",
                                         relief=tk.FLAT, height=6)
        self.history_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        history_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.history_listbox.yview)
        history_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.history_listbox.configure(yscrollcommand=history_scroll.set)

        btn_row = tk.Frame(history_card, bg="#16213e")
        btn_row.pack(fill=tk.X, padx=15, pady=(0, 10))

        tk.Button(btn_row, text="📋 复制选中密钥",
                 font=("Microsoft YaHei", 9),
                 bg="#9b59b6", fg="white",
                 relief=tk.FLAT, cursor="hand2",
                 padx=12, pady=4,
                 command=self._copy_selected).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(btn_row, text="🗑️ 清空历史",
                 font=("Microsoft YaHei", 9),
                 bg="#e74c3c", fg="white",
                 relief=tk.FLAT, cursor="hand2",
                 padx=12, pady=4,
                 command=self._clear_history).pack(side=tk.LEFT, padx=(8, 0))

        tk.Button(btn_row, text="📂 查看记录",
                 font=("Microsoft YaHei", 9),
                 bg="#1abc9c", fg="white",
                 relief=tk.FLAT, cursor="hand2",
                 padx=12, pady=4,
                 command=self._view_records).pack(side=tk.RIGHT, padx=(0, 5))

        tk.Button(btn_row, text="💻 电脑记录",
                 font=("Microsoft YaHei", 9),
                 bg="#9b59b6", fg="white",
                 relief=tk.FLAT, cursor="hand2",
                 padx=12, pady=4,
                 command=self._view_computer_records).pack(side=tk.RIGHT)

        info_card = tk.Frame(card_frame, bg="#16213e")
        info_card.pack(fill=tk.X)

        tk.Label(info_card, text="ℹ️ 算法说明",
                font=("Microsoft YaHei", 12, "bold"),
                bg="#16213e", fg="#00d4ff").pack(anchor="w", padx=15, pady=(10, 5))

        algo_text = """密钥生成算法:
1. 获取机器指纹 (SHA256: CPU ID + 磁盘序列号 + 主板序列号 + BIOS序列号)
2. 组合指纹 + 客户名称 + PERMANENT (永久密钥)
3. 使用 SHA256 生成哈希值
4. 格式: YGB-XXXX-XXXX-XXXX-XXXX-C (含校验位)

密钥验证算法:
1. 检查格式是否符合 YGB-XXXX-XXXX-XXXX-XXXX-C (6段)
2. 校验校验位是否正确
3. 使用相同算法重新生成密钥
4. 比较两个密钥是否匹配"""

        tk.Label(info_card, text=algo_text,
                font=("Consolas", 8),
                bg="#16213e", fg="#888888", wraplength=480, justify="left").pack(anchor="w", padx=15, pady=(0, 10))

    def _load_fingerprint(self):
        try:
            self.fingerprint = generate_fingerprint()
            self.fp_label.config(text=self.fingerprint)
            self.fp_short_label.config(text=f"短指纹: {self.fingerprint[:8].upper()}")
        except Exception as e:
            self.fp_label.config(text=f"获取失败: {str(e)}")

    def _generate_key(self):
        customer_name = self.customer_var.get().strip()

        try:
            valid_days = int(self.valid_days_var.get().strip())
        except ValueError:
            messagebox.showerror("错误", "有效天数必须是数字")
            return

        if self.use_custom_fingerprint.get():
            fp = self.custom_fingerprint.get().strip()
            if not fp:
                messagebox.showerror("错误", "请输入自定义指纹")
                return
        else:
            if not self.fingerprint:
                messagebox.showerror("错误", "机器指纹获取失败")
                return
            fp = self.fingerprint

        try:
            key = generate_license_key(fp, customer_name, valid_days)
            timestamp = datetime.now().strftime("%H:%M:%S")
            expiry_info = f" (永久)" if valid_days == 0 else f" (有效期: {valid_days}天)"
            display = f"[{timestamp}] {key}{expiry_info}"
            if customer_name:
                display += f" ({customer_name})"

            self.generated_keys.append((key, customer_name))
            self.history_listbox.insert(tk.END, display)
            self.gen_result_label.config(text=f"✅ 生成成功: {key}", fg="#27ae60")

            save_license_record(key, fp, customer_name, True)
            save_computer_record(fp, customer_name, key)

            self.root.clipboard_clear()
            self.root.clipboard_append(key)
            messagebox.showinfo("生成成功", f"许可证密钥已生成并复制到剪贴板:\n\n{key}\n\n已自动保存到记录文件")
        except Exception as e:
            self.gen_result_label.config(text=f"❌ 生成失败: {str(e)}", fg="#e74c3c")

    def _verify_key(self):
        key = self.verify_key_var.get().strip().upper()
        customer_name = self.verify_customer_var.get().strip()

        if not key:
            messagebox.showwarning("输入错误", "请输入许可证密钥")
            return

        if not validate_license_key_format(key):
            self.ver_result_label.config(text="❌ 格式无效，应为: YGB-XXXX-XXXX-XXXX-XXXX", fg="#e74c3c")
            return

        if self.use_custom_fingerprint.get():
            fp = self.custom_fingerprint.get().strip()
            if not fp:
                self.ver_result_label.config(text="❌ 请输入自定义指纹", fg="#e74c3c")
                return
        else:
            if not self.fingerprint:
                self.ver_result_label.config(text="❌ 机器指纹获取失败", fg="#e74c3c")
                return
            fp = self.fingerprint

        try:
            result = verify_license_key(key, fp, customer_name)

            if result["valid"] and result["match"]:
                self.ver_result_label.config(
                    text=f"✅ 密钥有效!\n与指纹匹配",
                    fg="#27ae60"
                )
            elif result["valid"] and not result["match"]:
                self.ver_result_label.config(
                    text=f"⚠️ 密钥格式正确但与指纹不匹配\n可能用于其他机器",
                    fg="#f39c12"
                )
            else:
                self.ver_result_label.config(text=f"❌ {result['message']}", fg="#e74c3c")
        except Exception as e:
            self.ver_result_label.config(text=f"❌ 验证失败: {str(e)}", fg="#e74c3c")

    def _toggle_custom_fp(self):
        """切换是否使用自定义指纹"""
        if self.use_custom_fingerprint.get():
            self.custom_fp_entry.config(state=tk.NORMAL)
        else:
            self.custom_fp_entry.config(state=tk.DISABLED)
            self.custom_fingerprint.set("")

    def _paste_fingerprint(self):
        """从剪贴板粘贴指纹"""
        try:
            clipboard_text = self.root.clipboard_get()
            self.custom_fingerprint.set(clipboard_text.strip())
        except Exception as e:
            messagebox.showwarning("粘贴失败", "无法从剪贴板获取内容")

    def _copy_selected(self):
        selection = self.history_listbox.curselection()
        if not selection:
            messagebox.showwarning("选择错误", "请先选择要复制的密钥")
            return

        index = selection[0]
        key = self.generated_keys[index][0]

        self.root.clipboard_clear()
        self.root.clipboard_append(key)
        messagebox.showinfo("复制成功", f"已复制:\n{key}")

    def _view_records(self):
        """查看许可证生成记录"""
        records = load_license_records()
        if not records:
            messagebox.showinfo("记录查看", "暂无许可证生成记录")
            return

        records_window = tk.Toplevel(self.root)
        records_window.title("许可证生成记录")
        records_window.geometry("600x500")
        records_window.configure(bg="#1a1a2e")

        tk.Label(records_window, text="📋 许可证生成记录",
                font=("Microsoft YaHei", 14, "bold"),
                bg="#16213e", fg="#00d4ff").pack(fill=tk.X, padx=20, pady=15)

        text_frame = tk.Frame(records_window, bg="#1a1a2e")
        text_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))

        text_widget = tk.Text(text_frame, font=("Consolas", 10),
                            bg="#16213e", fg="#00ff88",
                            relief=tk.FLAT, wrap=tk.WORD)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.configure(yscrollcommand=scrollbar.set)

        text_widget.insert(tk.END, records)
        text_widget.config(state=tk.DISABLED)

        tk.Button(records_window, text="关闭",
                 font=("Microsoft YaHei", 11),
                 bg="#555555", fg="white",
                 relief=tk.FLAT, cursor="hand2",
                 padx=20, pady=8,
                 command=records_window.destroy).pack(pady=(0, 15))

    def _view_computer_records(self):
        """查看电脑记录"""
        records = load_computer_records()
        if not records:
            messagebox.showinfo("记录查看", "暂无电脑记录\n\n首次生成许可证时会自动记录电脑信息")
            return

        records_window = tk.Toplevel(self.root)
        records_window.title("电脑记录")
        records_window.geometry("650x550")
        records_window.configure(bg="#1a1a2e")

        tk.Label(records_window, text="💻 已记录的使用电脑",
                font=("Microsoft YaHei", 14, "bold"),
                bg="#16213e", fg="#00d4ff").pack(fill=tk.X, padx=20, pady=15)

        text_frame = tk.Frame(records_window, bg="#1a1a2e")
        text_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))

        text_widget = tk.Text(text_frame, font=("Consolas", 10),
                            bg="#16213e", fg="#00ff88",
                            relief=tk.FLAT, wrap=tk.WORD)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.configure(yscrollcommand=scrollbar.set)

        text_widget.insert(tk.END, records)
        text_widget.config(state=tk.DISABLED)

        tk.Button(records_window, text="关闭",
                 font=("Microsoft YaHei", 11),
                 bg="#555555", fg="white",
                 relief=tk.FLAT, cursor="hand2",
                 padx=20, pady=8,
                 command=records_window.destroy).pack(pady=(0, 15))

    def _clear_history(self):
        self.generated_keys = []
        self.history_listbox.delete(0, tk.END)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    gui = LicenseGeneratorGUI()
    gui.run()
