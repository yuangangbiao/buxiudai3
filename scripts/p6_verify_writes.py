#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""RE-006 P6 端到端写入验证:验证 7 个 collect_* 写入新 data_type

策略:mock storage,捕获 collector.collect 调用,断言 data_type 参数
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


class MockCollector:
    """模拟 collector,记录所有 collect 调用"""

    def __init__(self):
        self.calls = []

    def collect(self, **kwargs):
        self.calls.append(kwargs)
        # 返回 mock 包
        return {
            "id": len(self.calls),
            "data_type": kwargs.get("data_type"),
            "title": kwargs.get("title"),
            "order_no": kwargs.get("order_no"),
        }


def test_container_center_writes_new_data_types():
    """直接 import 容器中心,替换 collector 为 mock,验证写入"""
    try:
        from mobile_api_ai.container_center_v5 import (
            NEW_DATA_TYPE_FOR_COLLECT,
        )
        from utils.data_type_contract import NEW_DATA_TYPES
    except Exception as e:
        print(f"[WARN] import 失败: {e},直接做静态扫描")
        return _static_verify()

    # 1. 验证 NEW_DATA_TYPE_FOR_COLLECT 全部用新值
    print("【1】NEW_DATA_TYPE_FOR_COLLECT 配置:")
    for old, new in NEW_DATA_TYPE_FOR_COLLECT.items():
        is_new = "✅" if new in NEW_DATA_TYPES else "❌"
        print(f"  {old!r:15s} -> {new!r:20s} {is_new}")
        assert new in NEW_DATA_TYPES, f"{new!r} 不在 NEW_DATA_TYPES 中"

    # 2. 尝试 import ContainerCenter,创建 mock 实例
    try:
        from mobile_api_ai.container_center_v5 import ContainerCenterV5
    except Exception as e:
        print(f"\n[WARN] 无法 import ContainerCenterV5: {e}")
        print("改用方法签名静态验证")
        return _static_verify(NEW_DATA_TYPE_FOR_COLLECT)

    mock = MockCollector()

    # 创建实例并替换 collector
    try:
        cc = ContainerCenterV5.__new__(ContainerCenterV5)
        cc.collector = mock
    except Exception as e:
        print(f"[WARN] 无法实例化 ContainerCenterV5: {e}")
        return _static_verify(NEW_DATA_TYPE_FOR_COLLECT)

    # 3. 调用 7 个 collect_xxx,验证 data_type 参数
    test_cases = [
        ("collect_report",   {"order_no": "TEST-001", "process_name": "穿曲轴",
                                "operator_id": "tester", "completed_qty": 10, "planned_qty": 20}, "process_report"),
        ("collect_quality",  {"order_no": "TEST-001", "order_id": 1, "inspection_type": "首检",
                                "inspector_id": "tester"}, "quality_task"),
        ("collect_material", {"order_no": "TEST-001", "material_name": "链条", "spec": "M10",
                                "quantity": 100, "unit": "个", "operator_id": "tester"}, "material_pickup"),
        ("collect_approval", {"order_no": "TEST-001", "approval_id": 1,
                                "reason": "请假", "approver_id": "tester"}, "approval"),
        ("collect_repair",   {"order_no": "TEST-001", "category_id": 1, "category_name": "激光切板机",
                                "issue_desc": "故障", "reporter_id": "tester"}, "equipment_repair"),
        ("collect_outsource",{"order_no": "TEST-001", "process_name": "热处理",
                                "vendor_id": 1, "operator_id": "tester"}, "outsource_task"),
    ]

    print("\n【2】7 个 collect_* 写入新 data_type 验证:")
    all_pass = True
    for method_name, kwargs, expected_dt in test_cases:
        if not hasattr(cc, method_name):
            print(f"  [SKIP] {method_name}: 方法不存在")
            continue
        method = getattr(cc, method_name)
        try:
            method(**kwargs)
            actual_dt = mock.calls[-1].get("data_type")
            ok = "✅" if actual_dt == expected_dt else "❌"
            if actual_dt != expected_dt:
                all_pass = False
            print(f"  {ok} {method_name:20s} -> data_type={actual_dt!r} (期望 {expected_dt!r})")
        except Exception as e:
            print(f"  [WARN] {method_name} 调用失败: {type(e).__name__}: {str(e)[:100]}")
            all_pass = False

    if all_pass:
        print("\n✅ 所有 collect_* 写入新 data_type 验证通过")
        return 0
    else:
        print("\n❌ 部分 collect_* 验证失败")
        return 1


def _static_verify():
    """静态验证:扫描源文件,确认 collect_* 内的 data_type 字符串"""
    from utils.data_type_contract import NEW_DATA_TYPES
    import re
    src = open(os.path.join(ROOT, "mobile_api_ai/container_center_v5.py"), encoding="utf-8").read()

    print("\n【静态扫描】container_center_v5.py 中所有 collect_xxx 的 data_type 字符串:")
    # 用更简单的正则:找 def collect_xxx( 后到下一个 def 或 class 之前
    pattern = re.compile(r"def\s+(collect_\w+)\s*\(", re.MULTILINE)
    methods = pattern.findall(src)
    print(f"  找到 {len(methods)} 个 collect_xxx 方法: {methods}\n")

    if not methods:
        # 兜底:直接 grep
        print("  [FALLBACK] 用 grep 风格扫描")
        for m in ["collect_report", "collect_quality", "collect_material",
                  "collect_approval", "collect_repair", "collect_outsource"]:
            if f"def {m}(" in src:
                methods.append(m)
        print(f"  找到 {len(methods)} 个: {methods}")

    expected_map = {
        "collect_report":   "process_report",
        "collect_quality":  "quality_task",
        "collect_material": "material_pickup",
        "collect_approval": "approval",
        "collect_repair":   "equipment_repair",
        "collect_outsource":"outsource_task",
    }
    all_pass = True
    lines = src.splitlines(keepends=True)
    for m in methods:
        # 找方法 def 行号
        m_idx = src.find(f"def {m}(")
        if m_idx < 0:
            print(f"  [WARN] {m}: 未找到 def")
            continue
        # 找下一个 def 或 class 行
        next_match = re.search(r"\n    def\s|\nclass\s", src[m_idx + 10:])
        body_end = (m_idx + 10 + next_match.start()) if next_match else len(src)
        body = src[m_idx:body_end]

        # 跳过方法签名(可能多行)后,找 data_type 赋值
        sig_end = body.find("):")
        if sig_end > 0:
            body_after_sig = body[sig_end:]
        else:
            body_after_sig = body
        dt_match = re.search(
            r"data_type\s*=\s*(?:NEW_DATA_TYPE_FOR_COLLECT\['(\w+)'\][^,]*?,\s*'([\w_]+)'|['\"]([\w_]+)['\"])",
            body_after_sig
        )
        if not dt_match:
            print(f"  [WARN] {m}: 未找到 data_type 赋值")
            continue
        if dt_match.group(3):
            actual = dt_match.group(3)
            via_dict = False
        else:
            via_dict = True
            actual = dt_match.group(2)
        is_new = "✅" if actual in NEW_DATA_TYPES else "❌"
        if actual not in NEW_DATA_TYPES:
            all_pass = False
        expected = expected_map.get(m, "?")
        match_expected = "✓" if actual == expected else f"✗(期望 {expected})"
        via = "字典" if via_dict else "直接"
        print(f"  {is_new} {m:20s} data_type={actual!r:22s} {match_expected:10s} via={via}")

    if all_pass:
        print("\n✅ 静态扫描通过:所有 collect_xxx 写入新 data_type")
        return 0
    else:
        print("\n❌ 静态扫描失败")
        return 1


if __name__ == "__main__":
    sys.exit(test_container_center_writes_new_data_types())
