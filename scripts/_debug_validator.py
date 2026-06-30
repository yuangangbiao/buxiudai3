"""调试 validator 测试异常匹配"""
import sys
sys.path.insert(0, r'd:\yuan\不锈钢网带跟单3.0')

from core.exceptions import ValidationException
from utils.validators import CommonValidators
import re

print("=== 测试 CommonValidators.required ===")
try:
    CommonValidators.required(None, "customer_name")
except ValidationException as e:
    print(f"type(e): {type(e)}")
    print(f"str(e): '{str(e)}'")
    print(f"repr(e): '{repr(e)}'")
    print(f"e.args: {e.args}")
    print(f"e.message: '{e.message}'")
    print(f"e.field: '{e.field}'")
    pattern = "不能为空"
    msg = str(e)
    match_result = re.search(pattern, msg)
    print(f"\nre.search('{pattern}', '{msg}'): {match_result}")

    pattern2 = "customer_name不能为空"
    match2 = re.search(pattern2, msg)
    print(f"re.search('{pattern2}', '{msg}'): {match2}")

print("\n=== 直接检查异常 ===")
exc = ValidationException("customer_name不能为空", field="customer_name")
print(f"exc.__str__(): '{exc.__str__()}'")
print(f"str(exc): '{str(exc)}'")
print(f"exc.args: {exc.args}")

print("\n=== 测试 pytest.raises 的 match 用法 ===")
# pytest 用 re.search 匹配
# 确认异常本身的格式
try:
    raise ValidationException("customer_name不能为空", field="customer_name")
except ValidationException as e:
    msg = str(e)
    print(f"Raised exception str: '{msg}'")
    print(f"re.search('不能为空', msg): {bool(re.search('不能为空', msg))}")
    print(f"re.search('customer_name不能为空', msg): {bool(re.search('customer_name不能为空', msg))}")
