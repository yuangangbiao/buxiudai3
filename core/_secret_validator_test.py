# -*- coding: utf-8 -*-
r"""
P0-S7 试运行模块 — 密钥生成 + 强校验
====================================

设计目标：
1. 不修改现有 core/_config_infra.py（避免污染）
2. 不修改现有 .env（避免影响其他服务）
3. 生成 5 套独立密钥并校验
4. 校验失败立即报错
5. 校验通过输出报告（不实际写入任何文件）

试运行模式（不重启服务、不写 .env、不动其他模块）：
    & "C:\Users\lenovo\AppData\Local\Python\bin\python.exe" -m core._secret_validator_test

退出码：
    0 = 全部通过
    1 = 密钥长度不足
    2 = 密钥两两相等（混用违规）
    3 = 必填密钥缺失
"""
import os
import sys
import secrets
import string
from pathlib import Path

# 5 套独立密钥定义（与 v3.6.6 设计一致）
SECRET_KEYS = {
    'JWT_SECRET_KEY':       {'min_bytes': 32, 'purpose': 'JWT 签名密钥 (5003/5008 共享)'},
    'DISPATCH_TOKEN':       {'min_bytes': 16, 'purpose': '5003 内部服务 token (dispatch ↔ container/inventory)'},
    'STATS_API_KEY':        {'min_bytes': 16, 'purpose': '智能表格统计推送 API Key (5003 ↔ 云端 5004)'},
    'WECHAT_CLOUD_API_KEY': {'min_bytes': 16, 'purpose': '微信云端 API Key (5003 ↔ 云端 5006)'},
    'SESSION_SECRET':       {'min_bytes': 16, 'purpose': '调度中心操作员登录态加密'},
}


def _generate_hex_key(num_bytes: int) -> str:
    """生成 hex 编码的随机密钥（用 secrets 模块，符合密码学安全）"""
    return secrets.token_hex(num_bytes)


def generate_all_keys() -> dict:
    """生成 5 套独立密钥（不写入 .env，仅返回）"""
    return {
        name: _generate_hex_key(spec['min_bytes'])
        for name, spec in SECRET_KEYS.items()
    }


def validate_keys(keys: dict) -> tuple:
    """
    强校验 5 套密钥

    Returns:
        (passed: bool, error_code: int, error_message: str)
    """
    # 1) 必填检查
    for name in SECRET_KEYS:
        if name not in keys or not keys[name]:
            return False, 3, f'必填密钥缺失: {name}'

    # 2) 长度检查
    for name, spec in SECRET_KEYS.items():
        expected_len = spec['min_bytes'] * 2  # hex 字符串 = 字节数 * 2
        actual_len = len(keys[name])
        if actual_len < expected_len:
            return False, 1, (
                f'密钥长度不足: {name} '
                f'(需要 ≥{spec["min_bytes"]} 字节 / {expected_len} hex, '
                f'实际 {actual_len // 2} 字节 / {actual_len} hex)'
            )

    # 3) 两两不等检查（防止密钥混用违规）
    names = list(keys.keys())
    for i, n1 in enumerate(names):
        for n2 in names[i + 1:]:
            if keys[n1] == keys[n2]:
                return False, 2, f'密钥混用违规: {n1} === {n2}（必须独立生成）'

    return True, 0, ''


def main():
    print('=' * 70)
    print('P0-S7 试运行 — 5 套独立密钥生成 + 强校验')
    print('=' * 70)
    print()

    # 步骤 1: 生成密钥
    print('[1/3] 生成 5 套独立密钥...')
    keys = generate_all_keys()
    for name, val in keys.items():
        spec = SECRET_KEYS[name]
        # 只显示前 8 字符 + 长度
        masked = val[:8] + '...' + val[-4:]
        print(f'  ✓ {name:24s} = {masked:30s} ({len(val)} hex / {len(val)//2} 字节) — {spec["purpose"]}')
    print()

    # 步骤 2: 强校验
    print('[2/3] 强校验（长度 + 两两不等）...')
    passed, err_code, err_msg = validate_keys(keys)
    if not passed:
        print(f'  ✗ 校验失败: {err_msg}')
        print(f'  退出码: {err_code}')
        return err_code
    print('  ✓ 长度校验通过（所有密钥 ≥ 最低要求）')
    print('  ✓ 独立性校验通过（5 套密钥两两不等）')
    print()

    # 步骤 3: 输出试运行报告
    print('[3/3] 试运行报告')
    print('-' * 70)
    print(f'密钥总数:   {len(keys)}')
    print(f'生成方式:   secrets.token_hex (密码学安全)')
    print(f'校验结果:   ✅ 通过')
    print(f'退出码:     0')
    print()
    print('⚠️  试运行模式说明:')
    print('  - 未写入 .env（避免影响其他服务）')
    print('  - 未修改 core/_config_infra.py（避免污染）')
    print('  - 上述密钥仅在内存中生成，进程退出后失效')
    print()
    print('✅ P0-S7 试运行成功 — 密钥生成 + 强校验逻辑验证通过')
    print()
    print('下一步:')
    print('  1. 用户确认试运行结果')
    print('  2. 备份现有 .env → 写入新密钥')
    print('  3. 在 _config_infra.py 中集成强校验')
    print('  4. 跑 M1 阶段 1 验收')
    return 0


if __name__ == '__main__':
    sys.exit(main())
