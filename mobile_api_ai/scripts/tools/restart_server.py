#!/usr/bin/env python3
"""Clean restart: kill Python processes, clear pycache, start server"""
import os, sys, signal, subprocess, time, shutil

try:
    import psutil
except ImportError:
    psutil = None

if os.name == 'nt':
    subprocess.run(['taskkill', '/f', '/fi', 'WINDOWTITLE eq app.py'],
                   capture_output=True, shell=True)
    if psutil:
        for proc in psutil.process_iter(['pid', 'connections']):
            try:
                for conn in proc.connections():
                    if conn.status == 'LISTEN' and conn.laddr.port == 5000:
                        os.kill(proc.pid, signal.SIGTERM)
            except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
                pass
    else:
        r = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
        for line in r.stdout.split('\n'):
            if ':5000' in line and 'LISTENING' in line:
                parts = line.strip().split()
                if parts and parts[-1].isdigit():
                    subprocess.run(['taskkill', '/PID', parts[-1], '/F'],
                                   capture_output=True)
else:
    if psutil:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.cmdline() or []
                if any('app.py' in str(c) for c in cmdline) and 'python' in proc.name().lower():
                    os.kill(proc.pid, signal.SIGTERM)
            except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
                pass
    else:
        subprocess.run(['pkill', '-f', 'python.*app.py'], capture_output=True)

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for dirpath, dirnames, _ in os.walk(project_root):
    if '__pycache__' in dirnames:
        shutil.rmtree(os.path.join(dirpath, '__pycache__'), ignore_errors=True)

time.sleep(1)

subprocess.Popen(
    [sys.executable, 'app.py'],
    cwd=project_root,
    env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

time.sleep(3)
print(f'SERVER STARTED from {project_root}')
