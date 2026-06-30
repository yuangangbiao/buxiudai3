
import sys
sys.path.insert(0, '.')

print('=== MachineFingerprint.generate() ===')
from security.machine_fingerprint import MachineFingerprint
fp1 = MachineFingerprint.generate()
print('完整指纹:', fp1)
print('短指纹:', fp1[:8].upper())

print('\n=== license_tool.generate_fingerprint() ===')
from security import license_tool
fp2 = license_tool.generate_fingerprint()
print('完整指纹:', fp2)
print('短指纹:', fp2[:8].upper())

print('\n=== fingerprint_unlock_gui_small.py ===')
# 测试一下fingerprint_unlock_gui_small里的生成方式
import hashlib
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
                cpu_id = lines[-1].strip()
                if cpu_id:
                    return cpu_id
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
                serial = lines[-1].strip()
                if serial:
                    return serial
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
                serial = lines[-1].strip()
                if serial and serial != "SerialNumber":
                    return serial
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
                serial = lines[-1].strip()
                if serial and serial != "SerialNumber":
                    return serial
    except Exception:
        pass
    return "BIOS_UNKNOWN"

print('硬件信息：')
cpu = get_cpu_id()
disk = get_disk_serial()
mb = get_motherboard_serial()
bios = get_bios_serial()
print('CPU:', repr(cpu))
print('Disk:', repr(disk))
print('MB:', repr(mb))
print('BIOS:', repr(bios))

combined = "|".join([cpu, disk, mb, bios])
print('\nCombined:', repr(combined))

fp3 = hashlib.sha256(combined.encode('utf-8')).hexdigest()
print('Hash result:', fp3)
print('Short:', fp3[:8].upper())

print('\n=== 对比 ===')
print('MachineFingerprint:', fp1[:8].upper())
print('license_tool:', fp2[:8].upper())
print('Manual:', fp3[:8].upper())
print('Saved (from file): 7930B1D5')
