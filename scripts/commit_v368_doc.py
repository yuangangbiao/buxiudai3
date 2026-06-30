"""[v3.7.7] 提交修正后的 v3.6.8 ACCEPTANCE"""
import subprocess

# Add the file
r = subprocess.run(['git', 'add', 'docs/v3.6.8/ACCEPTANCE_P2_v3.6.8.md'],
                   capture_output=True, text=True)
print('add:', r.returncode)

# Commit (avoid shell escape issues)
msg = '''docs(v3.6.8): P2 修复验收修正 (92->76 数字校准 + scope 拆出记录)

[v3.7.7 审计修正] v3.7.7 22:30 审计发现:
- 原声称 92 str__call 替换 实际是 76 处（68 新增 + 8 新增）
- commit 2599c47d 含 3745 行 web 化骨架，已拆为 b40e6a2b

修正后真实情况:
- P2-5/6: _core.py +44/-11 (commit 2ee7a125)
- P2-2/3/7: desktop_web/server.py (commit b40e6a2b)

整体完成度: 70->89 分'''

# 用 stdin 传 commit message 避免引号问题
r = subprocess.run(['git', 'commit', '-F', '-'],
                   input=msg, capture_output=True, text=True)
print('commit return:', r.returncode)
if r.returncode == 0:
    print(r.stdout[:300])
else:
    print('stderr:', r.stderr[:500])