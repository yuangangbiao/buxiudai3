"""检查 PID 14320 的具体脚本"""
import subprocess
result = subprocess.run(
    ['wmic', 'process', 'where', 'processid=14320', 'get', 'commandline', '/format:list'],
    capture_output=True, text=True, timeout=10
)
print(result.stdout)
print(result.stderr[:500] if result.stderr else '')
