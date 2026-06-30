"""B0 端到端验证: R12 register_process bug 修复
R13 任务 18 端到端: register_process('audit_test_001', 'PAUDIT01', 99)
→ PROCESS_CODES['audit_test_001'] 应为 'PAUDIT01'
"""
import sys
sys.path.insert(0, r'd:\yuan\不锈钢网带跟单3.0')

from core.config import register_process, unregister_process, reset_custom_processes, PROCESS_CODES
from utils.data_type_contract import _PROCESS_CODE_TO_TYPE

reset_custom_processes()

print('=== 端到端测试 1: R13 任务 18 指定验证 ===')
code = register_process('audit_test_001', 'PAUDIT01', 99)
print(f'  register_process("audit_test_001", "PAUDIT01", 99) → {code}')
assert code == 'PAUDIT01', f'期望 PAUDIT01, 实际 {code}'
assert PROCESS_CODES.get('audit_test_001') == 'PAUDIT01', \
    f'BUG: PROCESS_CODES["audit_test_001"]={PROCESS_CODES.get("audit_test_001")}, 期望 PAUDIT01'
print(f'  ✓ PROCESS_CODES["audit_test_001"] = {PROCESS_CODES["audit_test_001"]}')
print(f'  ✓ _PROCESS_CODE_TO_TYPE["PAUDIT01"] = {_PROCESS_CODE_TO_TYPE.get("PAUDIT01")}')

print()
print('=== 端到端测试 2: 大小写敏感 (B0 新修) ===')
code_a = register_process('A')
code_b = register_process('B')
print(f'  register_process("A") → {code_a}')
print(f'  register_process("B") → {code_b}')
from core.config import get_process_seq
assert get_process_seq('A') == 17, f'get_process_seq("A")={get_process_seq("A")}, 期望 17'
assert get_process_seq('B') == 18, f'get_process_seq("B")={get_process_seq("B")}, 期望 18'
print(f'  ✓ get_process_seq("A") = 17')
print(f'  ✓ get_process_seq("B") = 18')

print()
print('=== 端到端测试 3: 幂等 (T5-2) ===')
code_again = register_process('A')
assert code_again == code_a, f'幂等失败: {code_again} != {code_a}'
print(f'  ✓ 重复 register_process("A") → {code_again} (幂等)')

print()
print('=== 端到端测试 4: unregister 回滚 ===')
assert unregister_process('A') is True
assert 'A' not in PROCESS_CODES
print(f'  ✓ unregister_process("A") → True, PROCESS_CODES 已移除')

print()
print('=== 端到端测试 5: DB 持久化核查 ===')
import pymysql, os
from dotenv import load_dotenv
load_dotenv(dotenv_path=r'd:\yuan\不锈钢网带跟单3.0\.env')
c = pymysql.connect(host='127.0.0.1', user='root', password='88888888', database='steel_belt')
cur = c.cursor()
cur.execute("SELECT name, process_code, category FROM process_code_registry WHERE name IN ('audit_test_001', 'B', 'A')")
rows = cur.fetchall()
for r in rows:
    print(f'  DB: {r}')
cur.close()
c.close()

# 清理
print()
print('=== 清理 ===')
unregister_process('audit_test_001')
unregister_process('B')
c = pymysql.connect(host='127.0.0.1', user='root', password='88888888', database='steel_belt')
cur = c.cursor()
cur.execute("DELETE FROM process_code_registry WHERE name IN ('audit_test_001', 'B', 'A')")
c.commit()
print(f'  DB 已清理 {cur.rowcount} 条')
cur.close()
c.close()

print()
print('========== B0 端到端 5/5 通过 ==========')
