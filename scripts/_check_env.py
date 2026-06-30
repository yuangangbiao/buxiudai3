import subprocess

r = subprocess.run(['powershell', '-NoProfile', '-Command',
    "(Get-WmiObject Win32_Process -Filter 'ProcessId=20972').CommandLine"],
    capture_output=True, text=True, encoding='utf-8')
print('CMDLINE:')
print(r.stdout)
print('STDERR:', r.stderr[:300])
