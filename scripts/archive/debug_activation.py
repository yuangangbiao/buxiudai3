#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试激活问题的脚本
"""
import os
import sys
import json

def debug_activation():
    print("=" * 60)
    print("激活问题调试")
    print("=" * 60)

    # 1. 检查 sys.frozen
    is_frozen = getattr(sys, 'frozen', False)
    print(f"\n[1] 运行模式: {'打包模式' if is_frozen else '开发模式'}")

    # 2. 检查 APP_DIR
    if is_frozen:
        app_dir = os.path.dirname(sys.executable)
    else:
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print(f"[2] APP_DIR: {app_dir}")

    # 3. 尝试导入模块
    try:
        from security.machine_fingerprint import MachineFingerprint
        print(f"[3] MachineFingerprint 导入: OK")
    except Exception as e:
        print(f"[3] MachineFingerprint 导入: FAIL - {e}")
        return

    # 4. 生成当前指纹
    try:
        current_fp = MachineFingerprint.generate()
        print(f"[4] 当前指纹: {current_fp}")
        print(f"    短指纹: {current_fp[:8].upper()}")
    except Exception as e:
        print(f"[4] 指纹生成: FAIL - {e}")
        return

    # 5. 检查 MachineFingerprint 的存储目录
    try:
        fp_cache_path = MachineFingerprint._get_cache_path()
        print(f"[5] 指纹缓存路径: {fp_cache_path}")
        print(f"    缓存存在: {os.path.exists(fp_cache_path)}")
    except Exception as e:
        print(f"[5] 指纹缓存路径: FAIL - {e}")

    # 6. 检查 LicenseBinding 的存储目录
    try:
        from security.license_binding import LicenseBinding
        storage_dir = LicenseBinding._get_storage_dir()
        binding_path = LicenseBinding._get_binding_path()
        salt_path = LicenseBinding._get_salt_path()

        print(f"[6] LicenseBinding 存储目录: {storage_dir}")
        print(f"    绑定文件路径: {binding_path}")
        print(f"    盐文件路径: {salt_path}")
        print(f"    绑定文件存在: {os.path.exists(binding_path)}")
        print(f"    盐文件存在: {os.path.exists(salt_path)}")
    except Exception as e:
        print(f"[6] LicenseBinding: FAIL - {e}")
        return

    # 7. 尝试加载绑定
    try:
        binding = LicenseBinding.load_binding()
        if binding:
            stored_fp = binding.get('fingerprint', '')
            print(f"[7] 绑定指纹: {stored_fp}")
            print(f"    指纹匹配: {stored_fp == current_fp}")
        else:
            print(f"[7] 未找到绑定文件")
    except Exception as e:
        print(f"[7] 绑定加载: FAIL - {e}")

    # 8. 检查 license_tool 模块
    try:
        from security.license_tool import check_activation
        status = check_activation()
        print(f"\n[8] check_activation() 结果:")
        print(f"    is_activated: {status.get('is_activated')}")
        print(f"    message: {status.get('message')}")
    except Exception as e:
        print(f"[8] check_activation: FAIL - {e}")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    debug_activation()
