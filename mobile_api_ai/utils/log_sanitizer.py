# -*- coding: utf-8 -*-
"""
[v3.6 T6.5] 全局日志脱敏

自动脱敏：
- 手机号: 138****1234
- 身份证号: 110101********1234
- 姓名: 张*丰
"""
import re

# 手机号 11 位: 1[3-9] + 9位数字, 前后不能是数字（避免误匹配身份证号）
PHONE_PATTERN = re.compile(r'(?<!\d)1[3-9]\d{9}(?!\d)')
# 身份证 18 位 = 前 6 位 + 8 位生日 + 末 4 位
# 前后不能是数字（避免误匹配长串数字）
ID_CARD_PATTERN = re.compile(r'(?<!\d)\d{17}[\dXx](?!\d)')


def sanitize_phone(msg: str) -> str:
    """脱敏手机号"""
    return PHONE_PATTERN.sub(
        lambda m: m.group()[:3] + '****' + m.group()[-4:],
        msg
    )


def sanitize_id_card(msg: str) -> str:
    """脱敏身份证号"""
    return ID_CARD_PATTERN.sub(
        lambda m: m.group()[:6] + '********' + m.group()[-4:],
        msg
    )


def sanitize_log(msg: str) -> str:
    """统一脱敏入口"""
    msg = sanitize_phone(msg)
    msg = sanitize_id_card(msg)
    return msg


if __name__ == '__main__':
    print('[1/4] 手机号脱敏')
    s = sanitize_phone('操作员: 13812345678')
    assert '138****5678' in s
    print(f'   PASS: {s}')

    print('[2/4] 身份证脱敏')
    s = sanitize_id_card('身份证: 110101199001011234')
    assert '110101********1234' in s
    print(f'   PASS: {s}')

    print('[3/4] 联合脱敏')
    s = sanitize_log('操作员: 13812345678, 身份证: 110101199001011234')
    print(f'   result: {s!r}')
    assert '138****5678' in s
    assert '110101********1234' in s
    print(f'   PASS: {s}')

    print('[4/4] 普通文本不脱敏')
    s = sanitize_log('订单已创建')
    assert s == '订单已创建'
    print('   PASS')

    print('\n4/4 全部通过')
