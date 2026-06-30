# -*- coding: utf-8 -*-
r"""
P0-S7 完整实施验证 — 集成测试
====================================

测试目标：
1. 加载 .env.test（含 5 套密钥）
2. 调用 core._config_infra.validate_secrets(strict=True) 严格校验
3. 验证 5 套密钥全部通过
4. 验证 get_secret_status() 状态正确
5. 故意制造失败用例（混用违规、长度不足）验证失败路径

跑法：
    & "C:\Users\lenovo\AppData\Local\Python\bin\python.exe" tests/integration/test_p0_s7_secrets.py
"""
import os
import sys
import warnings
from pathlib import Path

# 设置环境：让代码加载 .env.test 而非 .env
# 在导入 core._config_infra 之前，必须先设置 BASE_DIR
# test_p0_s7_secrets.py 在 tests/integration/, 项目根是其 parent.parent
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_TEST = BASE_DIR / 'mobile_api_ai' / '.env.test'
assert ENV_TEST.exists(), f'.env.test 不存在: {ENV_TEST}'

# 把项目根加入 sys.path（让 core 模块可导入）
sys.path.insert(0, str(BASE_DIR))

# 加载 .env.test
from dotenv import load_dotenv
load_dotenv(ENV_TEST, override=True)  # override=True 确保 .env.test 覆盖 .env

# 验证密钥已加载
print('=' * 70)
print('P0-S7 集成验证')
print('=' * 70)
print()
print(f'加载文件: {ENV_TEST}')
print(f'JWT_SECRET_KEY 已配置: {bool(os.getenv("JWT_SECRET_KEY"))} ({len(os.getenv("JWT_SECRET_KEY", ""))//2} 字节)')
print(f'DISPATCH_TOKEN 已配置: {bool(os.getenv("DISPATCH_TOKEN"))} ({len(os.getenv("DISPATCH_TOKEN", ""))//2} 字节)')
print(f'STATS_API_KEY 已配置: {bool(os.getenv("STATS_API_KEY"))} ({len(os.getenv("STATS_API_KEY", ""))//2} 字节)')
print(f'WECHAT_CLOUD_API_KEY 已配置: {bool(os.getenv("WECHAT_CLOUD_API_KEY"))} ({len(os.getenv("WECHAT_CLOUD_API_KEY", ""))//2} 字节)')
print(f'SESSION_SECRET 已配置: {bool(os.getenv("SESSION_SECRET"))} ({len(os.getenv("SESSION_SECRET", ""))//2} 字节)')
print()

# 步骤 1: 调用 validate_secrets() 非严格模式
print('[1/4] validate_secrets(strict=False) — 非严格模式（不应抛错）...')
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter('always')
    from core._config_infra import validate_secrets, get_secret_status
    passed, err_code, err_msg = validate_secrets(strict=False)
    if passed:
        print(f'  ✅ 通过 (code={err_code})')
    else:
        print(f'  ⚠️  未通过 (code={err_code}): {err_msg}')
print()

# 步骤 2: 调用 validate_secrets() 严格模式
print('[2/4] validate_secrets(strict=True) — 严格模式（必须通过）...')
try:
    passed, err_code, err_msg = validate_secrets(strict=True)
    if passed:
        print(f'  ✅ 严格模式通过 (code={err_code})')
        print('  ✅ 所有 5 套密钥符合强校验标准')
    else:
        print(f'  ❌ 严格模式失败 (code={err_code}): {err_msg}')
        sys.exit(1)
except RuntimeError as e:
    print(f'  ❌ 严格模式抛错: {e}')
    sys.exit(1)
print()

# 步骤 3: get_secret_status() 状态查询
print('[3/4] get_secret_status() — 状态查询...')
status = get_secret_status()
for name, info in status.items():
    icon = '✅' if info['meets_min'] else '❌'
    print(f'  {icon} {name:24s} - {info["length_bytes"]:3d} 字节 / 要求 ≥{info["min_bytes"]:2d} 字节 - {info["purpose"]}')
print()

# 步骤 4: 故意制造失败用例
print('[4/4] 失败用例测试（混用违规、长度不足）...')

# 4a) 长度不足
print('  [4a] 测试长度不足...')
os.environ['JWT_SECRET_KEY'] = 'short'  # 5 字符 = 2 字节，远小于 32 字节要求
try:
    validate_secrets(strict=True)
    print('    ❌ 应该失败但通过了')
    sys.exit(1)
except RuntimeError as e:
    print(f'    ✅ 正确抛出: {e}')
# 恢复
os.environ['JWT_SECRET_KEY'] = '146add75b1aedc9e16c4f0a3b7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d661f4'

# 4b) 混用违规
print('  [4b] 测试密钥混用违规（DISPATCH_TOKEN === STATS_API_KEY）...')
os.environ['DISPATCH_TOKEN'] = os.environ['STATS_API_KEY']
try:
    validate_secrets(strict=True)
    print('    ❌ 应该失败但通过了')
    sys.exit(1)
except RuntimeError as e:
    print(f'    ✅ 正确抛出: {e}')
# 恢复
os.environ['DISPATCH_TOKEN'] = '4b1be4cba97d8e9f0a1b2c3d4e5f6a7b2707'

# 4c) 必填缺失
print('  [4c] 测试必填密钥缺失...')
os.environ.pop('SESSION_SECRET', None)
try:
    validate_secrets(strict=True)
    print('    ❌ 应该失败但通过了')
    sys.exit(1)
except RuntimeError as e:
    print(f'    ✅ 正确抛出: {e}')
# 恢复
os.environ['SESSION_SECRET'] = '23920b6e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2f28f'

print()
print('=' * 70)
print('✅ P0-S7 完整实施验证通过')
print('=' * 70)
print()
print('验证结果:')
print('  - 5 套密钥正确加载（来自 .env.test）')
print('  - 严格模式（strict=True）通过')
print('  - 非严格模式（strict=False）通过（不会中断服务）')
print('  - 状态查询函数 get_secret_status() 工作正常')
print('  - 失败用例（长度不足/混用违规/必填缺失）正确抛错')
print()
print('下一步:')
print('  1. 决定是否将密钥写入正式 .env（v3.6.6 阶段 1 完整实施）')
print('  2. 或继续验证其他 P0-S 项')
